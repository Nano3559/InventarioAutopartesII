"""Integración con targets alineados. Dobles sin aprendizaje, no regresores."""
import copy
import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from v2.preprocessing import RAW,CONTEXT
from v2.structure import ROOT,sha256_file
from v2.validate_build import month_offset
from v2.experiments import (TARGET,KEYS,align_targets,load_xy,candidates,make_pipeline,
    score_predictions,choose,_comparison_logic as comparison_logic,prepare_run,execute_experiments,
    rotation_reference,_publish_tracking)


class FixtureStore:
    def __init__(self,plan,baseline_exact=False,tradeoff=False):
        self.plan=plan;self.calls=[];self.baseline_exact=baseline_exact;self.tradeoff=tradeoff

    def load(self,partition,fold_id=None):
        if partition=="TEST":raise AssertionError("TEST forbidden")
        t=self.plan["temporal_validation"]
        if fold_id:
            f=next(x for x in t["folds"] if x["id"]==fold_id);a,b=f["train" if partition=="TRAIN" else "validation"]
        else:a,b=t["outer_train" if partition=="TRAIN" else "outer_validation"]
        self.calls.append((partition,fold_id));rows=[];keys=[];values=[];m=a
        while m<=b:
            for p,s in [(1,5),(2,6)]:
                row={name:0 for name in RAW};row.update(mes_objetivo=m,ventas_mes_anterior=p+1 if self.baseline_exact else 0 if self.tradeoff and p==1 else 3 if self.tradeoff else 1,
                    cobertura_stock_mes_anterior=1,cobertura_modalidad_mes_anterior=1,proporcion_por_mayor_mes_anterior=p-1,categoryId=p)
                rows.append(row);keys.append((p,s,m));values.append(p+1)
            m=month_offset(m,1)
        index=pd.MultiIndex.from_tuples(keys,names=KEYS)
        X=pd.DataFrame(rows,index=index);y=pd.Series(values,index=index,name=TARGET)
        # A propósito se entrega y en otro orden para comprobar la alineación.
        return X,y.iloc[::-1]


class RecordingDouble:
    """fit registra claves. predict devuelve una constante, no aprende de y."""
    def __init__(self,candidate,events,mode="OK"):
        self.candidate=candidate;self.events=events;self.mode=mode;self.ready=False

    def fit(self,X,y):
        assert X.index.equals(y.index)
        assert y.tolist()==[k[0]+1 for k in X.index]
        self.events.append(dict(candidate=self.candidate["candidate_id"],months=sorted(set(X[CONTEXT])),rows=len(X)))
        self.ready=True;return self

    def predict(self,X):
        assert self.ready
        if self.mode=="FAIL":raise ValueError("controlled prediction failure")
        if self.mode=="NAN":return np.full(len(X),np.nan)
        return np.full(len(X),2.0)


class ExperimentIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads((ROOT/"v2/contracts/experiments.v2_1.json").read_text(encoding="utf-8"))

    def setUp(self):
        from sklearn.linear_model import LinearRegression
        from sklearn.ensemble import RandomForestRegressor
        for model in [LinearRegression,RandomForestRegressor]:
            self.enterContext(patch.object(model,"fit",side_effect=AssertionError("Real model training forbidden")))

    def test_loader_has_exact_X_y_identity_without_label_in_features(self):
        for part,fold,n in [("TRAIN",None,2520),("VALIDATION",None,504),("TRAIN","F1",1008),("VALIDATION","F1",504)]:
            X,y=load_xy(part,fold_id=fold)
            self.assertEqual(len(X),n);self.assertTrue(X.index.equals(y.index))
            self.assertEqual(set(X),set(RAW)|{CONTEXT});self.assertNotIn(TARGET,X)
            self.assertTrue((y>=0).all())

    def test_loader_does_not_access_test_targets_even_before_other_loaders(self):
        with patch("v2.experiments.load_feature_partition",side_effect=AssertionError("must reject before reading")):
            with self.assertRaises(ValueError):load_xy("TEST")

    def test_shuffled_targets_are_reindexed_by_identity_not_position(self):
        X,y=FixtureStore(self.plan).load("TRAIN")
        aligned=align_targets(X,y)
        self.assertEqual(aligned.tolist(),[k[0]+1 for k in X.index])
        self.assertTrue(aligned.index.equals(X.index))

    def test_missing_extra_or_duplicate_targets_are_rejected(self):
        X,y=FixtureStore(self.plan).load("TRAIN")
        for bad in [y.iloc[1:],pd.concat([y,y.iloc[:1]])]:
            with self.assertRaises(ValueError):align_targets(X,bad)
        extra=y.copy();tuples=list(extra.index);tuples[0]=(999,5,"2025-01");extra.index=pd.MultiIndex.from_tuples(tuples,names=KEYS)
        with self.assertRaises(ValueError):align_targets(X,extra)

    def test_invalid_targets_are_rejected_without_filling_or_rounding(self):
        X,y=FixtureStore(self.plan).load("TRAIN")
        for bad in [-1,.5,float("nan"),True]:
            changed=y.astype(object).copy();changed.iloc[0]=bad
            with self.subTest(value=bad),self.assertRaises(ValueError):align_targets(X,changed)

    def test_candidates_and_real_pipeline_factory_are_unfitted(self):
        grid=candidates(self.plan)
        self.assertEqual(len(grid),30);self.assertEqual(len({c["candidate_id"] for c in grid}),30)
        for candidate in [grid[0],next(c for c in grid if c["model"]=="random_forest")]:
            pipe=make_pipeline(candidate)
            self.assertFalse(hasattr(pipe.named_steps["preprocessing"],"_fitted_"))
            self.assertEqual(pipe.named_steps["preprocessing"].model_kind,candidate["model"])
        bad=copy.deepcopy(grid[0]);bad["parameters"]["fit_intercept"]=False
        with self.assertRaises(ValueError):make_pipeline(bad)

    def test_metrics_have_units_no_accuracy_and_undefined_constant_r2(self):
        score=score_predictions([0,2,4],[0,2,3])
        self.assertAlmostEqual(score["mae"],1/3);self.assertAlmostEqual(score["rmse"],np.sqrt(1/3));self.assertAlmostEqual(score["r2"],.875)
        constant=score_predictions([0,0],[0,1]);self.assertIsNone(constant["r2"]);self.assertEqual(constant["r2_status"],"CONSTANT_TARGET")
        self.assertIsNone(score_predictions([1],[1])["r2"])
        self.assertNotIn("accuracy",score)

    def test_negative_predictions_are_clipped_but_targets_and_raw_metrics_remain(self):
        y=np.array([0,2]);before=y.copy();score=score_predictions(y,[-3,2])
        self.assertEqual(score["mae"],0);self.assertEqual(score["negative_raw_predictions"],1)
        self.assertEqual(score["raw_metrics"]["mae"],1.5)
        np.testing.assert_array_equal(y,before)

    def test_nonfinite_or_wrong_shape_does_not_score_favorable_subset(self):
        for predictions in [[1,np.nan],[1,np.inf],[[1],[2]],[True,False]]:
            score=score_predictions([1,2],predictions)
            self.assertNotEqual(score["status"],"OK");self.assertIsNone(score["mae"])
        self.assertEqual(score_predictions([1,2],[1,np.nan])["abstentions"],1)

    def test_very_large_finite_error_does_not_emit_nan_or_infinite_json(self):
        score=score_predictions([1,2],[1e200,1e200])
        self.assertTrue(np.isfinite(score["mae"]));self.assertTrue(np.isfinite(score["rmse"]))
        json.dumps(score,allow_nan=False)

    def test_invalid_metric_targets_are_not_silently_coerced(self):
        for y in [[True,False],[0,-1],[0,.5],[0,np.nan],[0,1+2j]]:
            with self.subTest(y=y),self.assertRaises(ValueError):score_predictions(y,[0,1])

    def test_control_flow_fits_only_doubles_102_times_and_never_loads_test(self):
        store=FixtureStore(self.plan);events=[];objects=[]
        def factory(c):
            obj=RecordingDouble(c,events);objects.append(obj);return obj
        before=candidates(self.plan)
        result=comparison_logic(self.plan,store.load,factory)
        self.assertEqual(result["fit_attempts"],102);self.assertEqual(len(events),102)
        self.assertEqual(len({id(o) for o in objects}),102)
        self.assertEqual(len(result["records"]),103)
        self.assertTrue(all(r["pipeline"] is None for r in result["records"] if r["fold_id"]!="OUTER"))
        self.assertFalse(result["test_loaded"]);self.assertTrue(all(p!="TEST" for p,_ in store.calls))
        self.assertEqual(result["selection"]["model"],"linear_regression")
        self.assertFalse(result["selection"]["active_model_changed"])
        self.assertEqual(candidates(self.plan),before)

    def test_same_fixture_rows_are_used_for_all_outer_candidates(self):
        store=FixtureStore(self.plan);events=[]
        result=comparison_logic(self.plan,store.load,lambda c:RecordingDouble(c,events))
        outer=[r for r in result["records"] if r["fold_id"]=="OUTER"]
        self.assertEqual(len(outer),13)
        self.assertEqual({r["score"]["rows_requested"] for r in outer},{6})
        self.assertEqual({r["score"]["abstentions"] for r in outer},{0})

    def test_failed_cv_configuration_is_not_averaged_over_remaining_successes(self):
        store=FixtureStore(self.plan);events=[]
        result=comparison_logic(self.plan,store.load,lambda c:RecordingDouble(c,events,"NAN" if c["model"]=="random_forest" and c["parameters"]["min_samples_leaf"]==2 else "OK"))
        failed=[s for s in result["cv_summaries"] if s["score"]["status"]!="OK"]
        self.assertEqual(len(failed),12)
        self.assertTrue(all(s["score"]["mae"] is None for s in failed))
        self.assertEqual(result["selection"]["model"],"linear_regression")

    def test_baseline_is_retained_when_it_is_best(self):
        store=FixtureStore(self.plan,baseline_exact=True);events=[]
        result=comparison_logic(self.plan,store.load,lambda c:RecordingDouble(c,events))
        self.assertEqual(result["selection"]["status"],"BASELINE_RETAINED")
        self.assertEqual(result["selection"]["model"],"baseline")

    def test_better_global_error_with_worse_group_requires_review(self):
        store=FixtureStore(self.plan,tradeoff=True);events=[]
        result=comparison_logic(self.plan,store.load,lambda c:RecordingDouble(c,events))
        self.assertEqual(result["selection"]["status"],"REVIEW_REQUIRED")
        self.assertTrue(any(r.startswith("GROUP_TRADEOFF") for r in result["selection"]["review_reasons"]))

    def test_ties_choose_simpler_features_and_forest_configuration(self):
        store=FixtureStore(self.plan);events=[]
        result=comparison_logic(self.plan,store.load,lambda c:RecordingDouble(c,events))
        self.assertEqual(len(result["winner"]["candidate"]["columns"]),5)
        forests=[r for r in result["records"] if r["fold_id"]=="OUTER" and r["candidate"]["model"]=="random_forest"]
        self.assertTrue(all(r["candidate"]["parameters"]["max_depth"]==4 and r["candidate"]["parameters"]["min_samples_leaf"]==5 for r in forests))

    def test_rotation_reference_is_derived_only_from_training_labels(self):
        X,y=FixtureStore(self.plan).load("TRAIN");ref=rotation_reference(X,y)
        self.assertEqual(set(ref.values()),{"HIGH"})
        self.assertEqual(len(ref),2)

    def test_execution_guard_rejects_before_loading_targets_or_creating_models(self):
        with patch("v2.experiments.load_xy",side_effect=AssertionError("No target load")),patch("v2.experiments.make_pipeline",side_effect=AssertionError("No model construction")):
            with self.assertRaises(PermissionError):execute_experiments("not-authorized-test")
        self.assertFalse((ROOT/"models/v2/not-authorized-test").exists())

    def test_dry_run_is_only_metadata_and_checks_hashes_without_any_fit(self):
        runner=json.loads((ROOT/"v2/contracts/runner.v2_1.json").read_text(encoding="utf-8"))
        preprocessing=json.loads((ROOT/"v2/contracts/preprocessing.v2_1.json").read_text(encoding="utf-8"))
        relative=preprocessing["input_build"]["relative_path"]
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp",prefix="runner-plan-") as tmp:
            root=Path(tmp)
            names=["v2/contracts/runner.v2_1.json","v2/contracts/preprocessing.v2_1.json","v2/contracts/experiments.v2_1.json","v2/preprocessing.py",relative+"/manifest.json",relative+"/schema.json",relative+"/dataset_supervisado.csv"]
            for name in names:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
            with patch("v2.experiments.make_pipeline",side_effect=AssertionError("dry run must not construct models")),patch("v2.preprocessing.StandardScaler.fit",side_effect=AssertionError("no real preprocessing fit")):
                path,result=prepare_run("first",root=root)
            self.assertEqual(result["actual_model_fit_count"],0);self.assertEqual(result["actual_predict_calls"],0)
            self.assertEqual(result["planned_fit_count"],102);self.assertEqual(len(result["slices"]),8)
            self.assertTrue(all(s["index_equal"] for s in result["slices"]))
            self.assertFalse(list(root.rglob("experiments.csv")));self.assertFalse(list(root.rglob("*.joblib")))
            self.assertFalse(result["test_targets_loaded"])
            with self.assertRaises(FileExistsError):prepare_run("first",root=root)

    def test_tracking_uses_only_temporary_v2_fixture_log_and_rejects_duplicate_run(self):
        store=FixtureStore(self.plan);events=[];result=comparison_logic(self.plan,store.load,lambda c:RecordingDouble(c,events))
        summary=dict(csv_sha256="fixture",artifact_sha256=None,selection=result["selection"])
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp",prefix="tracking-fixture-") as tmp:
            root=Path(tmp);_publish_tracking(root,self.plan,"fake-run",summary,result["records"])
            target=root/self.plan["tracking"]["path"];before=target.read_bytes()
            with target.open(encoding="utf-8",newline="") as f:rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),103);self.assertTrue(all(r["run_id"]=="fake-run" for r in rows))
            with self.assertRaises(FileExistsError):_publish_tracking(root,self.plan,"fake-run",summary,result["records"])
            self.assertEqual(target.read_bytes(),before)
            self.assertFalse(target.with_name(target.name+".lock").exists())
            bad=copy.deepcopy(self.plan);bad["tracking"]["path"]="reports/experiments.csv"
            with self.assertRaises(ValueError):_publish_tracking(root,bad,"other",summary,result["records"])


if __name__=="__main__":unittest.main()
