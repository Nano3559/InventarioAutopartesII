"""Parámetros aprendidos solo de fixtures TRAIN, ningún modelo supervisado."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.exceptions import NotFittedError

from v2.preprocessing import (RAW,CONTEXT,GROUPS,DemandPreprocessor,load_feature_partition,read_context,validate_frame,validate_cohort)
from v2.validate_build import canonical_hash,cutoff,month_offset
from v2.structure import ROOT


def fixture(start="2025-01",months=15):
    rows=[]
    for i in range(months):
        month=month_offset(start,i);number=int(month[-2:])
        days=(cutoff(month)-cutoff(month_offset(month,-1))).days
        observed=0 if i%5==0 else days//2 if i%3==0 else days
        r=dict(mes_objetivo=month,ventas_mes_anterior=i+2,ventas_hace_2_meses=i+3,ventas_hace_3_meses=i+4,
            mes_sin=math.sin(2*math.pi*number/12),mes_cos=math.cos(2*math.pi*number/12),
            proporcion_por_mayor_mes_anterior=.1*(i%3+1),cobertura_modalidad_mes_anterior=.6+.1*(i%3),
            precio_menor_cierre_anterior_bs=120+2*i,precio_mayor_cierre_anterior_bs=100+2*i,
            variacion_precio_menor_conocida=.001*(i+1),variacion_precio_mayor_conocida=.001*(i+1),
            tipo_cambio_bs_usd_conocido=10+.1*i,variacion_tipo_cambio_ultimo_mes=.002*(i+1),
            antiguedad_tipo_cambio_dias=[0,2,7,30][i%4],
            dias_sin_stock_mes_anterior=min(i%4,observed) if observed else None,
            cobertura_stock_mes_anterior=observed/days,categoryId=i%3+1)
        if i==3:r["proporcion_por_mayor_mes_anterior"]=None
        if i==5:r["precio_mayor_cierre_anterior_bs"]=r["variacion_precio_mayor_conocida"]=None
        if i==8:r["tipo_cambio_bs_usd_conocido"]=r["variacion_tipo_cambio_ultimo_mes"]=r["antiguedad_tipo_cambio_dias"]=None
        if i==7:r["categoryId"]=None
        rows.append(r)
    return pd.DataFrame(rows,columns=[*RAW,CONTEXT])


class PreprocessingTests(unittest.TestCase):
    def setUp(self):self.train=fixture()

    def test_six_groups_have_fixed_meaning_and_output_names(self):
        shapes=[]
        for group,size in GROUPS.items():
            p=DemandPreprocessor(group,"random_forest").fit(self.train)
            matrix=p.transform(self.train)
            self.assertEqual(p.to_state()["state"]["columns"],list(RAW[:size]))
            self.assertEqual(matrix.shape[1],len(p.get_feature_names_out()))
            self.assertEqual(len(set(p.get_feature_names_out())),matrix.shape[1])
            shapes.append(matrix.shape[1])
        self.assertEqual(shapes,[5,9,17,23,26,30])

    def test_default_is_unfitted_and_transform_requires_fit(self):
        p=DemandPreprocessor()
        with self.assertRaises(NotFittedError):p.transform(self.train)
        self.assertNotIn("_state_",vars(p))

    def test_scaler_uses_only_imputed_training_numeric_values(self):
        p=DemandPreprocessor().fit(self.train);s=p.to_state()["state"]
        raw=self.train[s["numeric_columns"]].to_numpy(dtype=float)
        expected=np.where(np.isnan(raw),np.nanmedian(raw,axis=0),raw)
        np.testing.assert_allclose(s["means"],expected.mean(axis=0))
        np.testing.assert_allclose(s["scales"],expected.std(axis=0))
        transformed=p.transform(self.train)
        np.testing.assert_allclose(transformed[:,:16].mean(axis=0),0,atol=1e-12)
        np.testing.assert_allclose(transformed[:,:16].std(axis=0),1,atol=1e-12)

    def test_forest_preserves_known_numeric_scale(self):
        p=DemandPreprocessor(model_kind="random_forest").fit(self.train)
        transformed=p.transform(self.train);s=p.to_state()["state"]
        self.assertIsNone(s["means"]);self.assertIsNone(s["scales"])
        self.assertEqual(transformed[0,0],2)
        self.assertEqual(transformed[0,7],120)

    def test_median_imputation_has_explicit_fixed_missing_indicators(self):
        p=DemandPreprocessor(model_kind="random_forest").fit(self.train);s=p.to_state()["state"]
        transformed=p.transform(self.train);names=list(p.get_feature_names_out())
        index=names.index("proporcion_por_mayor_mes_anterior")
        expected=self.train["proporcion_por_mayor_mes_anterior"].median()
        self.assertEqual(transformed[3,index],expected)
        self.assertEqual(transformed[3,names.index("missing::proporcion_por_mayor_mes_anterior")],1)
        self.assertEqual(len(s["indicator_columns"]),10)
        self.assertTrue(set(np.unique(transformed[:,16:26]))<={0,1})

    def test_missing_not_seen_during_fit_still_has_fixed_indicator(self):
        p=DemandPreprocessor().fit(self.train);names=list(p.get_feature_names_out())
        validation=fixture("2026-04",3);validation.loc[0,"variacion_precio_menor_conocida"]=None
        matrix=p.transform(validation)
        self.assertEqual(matrix[0,names.index("missing::variacion_precio_menor_conocida")],1)
        self.assertEqual(matrix.shape[1],len(names))

    def test_unknown_and_missing_categories_use_reserved_bucket_without_scaling(self):
        p=DemandPreprocessor().fit(self.train);names=list(p.get_feature_names_out())
        future=fixture("2026-07",3);future.loc[0,"categoryId"]=999;future.loc[1,"categoryId"]=None
        matrix=p.transform(future);unknown=names.index("categoryId::UNKNOWN")
        self.assertEqual(matrix[0,unknown],1);self.assertEqual(matrix[1,unknown],1)
        self.assertTrue(set(np.unique(matrix[:,26:]))<={0,1})
        self.assertTrue(np.all(matrix[:,26:].sum(axis=1)==1))
        self.assertNotIn("categoryId::999",names)

    def test_validation_and_test_transform_cannot_change_parameters(self):
        p=DemandPreprocessor().fit(self.train);before=p.to_state()
        for start in ["2026-04","2026-07"]:
            future=fixture(start,3);future["precio_menor_cierre_anterior_bs"]+=100000
            future.loc[0,"categoryId"]=999
            self.assertTrue(np.isfinite(p.transform(future)).all())
            self.assertEqual(p.to_state(),before)

    def test_fit_rejects_validation_test_and_combined_partitions(self):
        for data in [fixture("2026-04",3),fixture("2026-07",3),pd.concat([self.train,fixture("2026-04",3)])]:
            p=DemandPreprocessor()
            with self.assertRaises(ValueError):p.fit(data)
            self.assertNotIn("_state_",vars(p))

    def test_fold_instances_do_not_share_state_or_accept_their_validation_months(self):
        first=DemandPreprocessor(train_end="2025-06").fit(fixture(months=6))
        second=DemandPreprocessor(train_end="2025-09").fit(fixture(months=9))
        self.assertNotEqual(first.to_state()["state"]["means"],second.to_state()["state"]["means"])
        with self.assertRaises(ValueError):DemandPreprocessor(train_end="2025-06").fit(fixture("2025-07",3))
        with self.assertRaises(ValueError):DemandPreprocessor(train_start="2026-07",train_end="2026-09").fit(fixture("2026-07",3))

    def test_refit_and_incomplete_months_are_rejected(self):
        p=DemandPreprocessor().fit(self.train);before=p.to_state()
        with self.assertRaises(ValueError):p.fit(self.train)
        self.assertEqual(p.to_state(),before)
        with self.assertRaises(ValueError):DemandPreprocessor().fit(self.train.iloc[:-1])
        with self.assertRaises(ValueError):DemandPreprocessor().fit(self.train.iloc[:0])

    def test_targets_ids_hidden_fields_and_duplicate_columns_are_not_inputs(self):
        for name in ["target_ventas_mes","productId","locationId","scenario_id","latent_demand_units","feature_cutoff_at"]:
            bad=self.train.copy();bad[name]=1
            with self.subTest(name=name),self.assertRaises(ValueError):DemandPreprocessor().fit(bad)
        bad=pd.concat([self.train,self.train[["mes_sin"]]],axis=1)
        with self.assertRaises(ValueError):DemandPreprocessor().fit(bad)

    def test_order_independence_is_by_names_not_positions(self):
        p=DemandPreprocessor().fit(self.train)
        np.testing.assert_array_equal(p.transform(self.train),p.transform(self.train[self.train.columns[::-1]]))
        with self.assertRaises(ValueError):p.transform(self.train.drop(columns=["categoryId"]))

    def test_all_missing_or_constant_selected_column_requires_review(self):
        for mode in ["all_missing","constant"]:
            bad=self.train.copy();bad["proporcion_por_mayor_mes_anterior"]=None if mode=="all_missing" else .1
            with self.subTest(mode=mode),self.assertRaises(ValueError):DemandPreprocessor().fit(bad)
        # Un grupo menor explícito puede funcionar sin esa variable opcional.
        p=DemandPreprocessor("expanded_baseline_v1_features").fit(bad)
        self.assertEqual(p.transform(bad).shape[1],5)

    def test_invalid_numeric_and_ordinal_category_inputs_are_rejected(self):
        for name,value in [("precio_menor_cierre_anterior_bs",float("inf")),("ventas_mes_anterior",True),
            ("ventas_hace_2_meses",1.5),("tipo_cambio_bs_usd_conocido",0),("categoryId",2.5),
            ("ventas_hace_3_meses","3"),("mes_sin",None)]:
            bad=self.train.copy();bad[name]=bad[name].astype(object);bad.loc[0,name]=value
            with self.subTest(name=name),self.assertRaises(ValueError):DemandPreprocessor().fit(bad)

    def test_business_and_calendar_constraints_are_not_silently_repaired(self):
        for name,value in [("mes_sin",0),("precio_mayor_cierre_anterior_bs",999),
            ("proporcion_por_mayor_mes_anterior",.99),("dias_sin_stock_mes_anterior",1)]:
            bad=self.train.copy();bad.loc[0,name]=value
            with self.subTest(name=name),self.assertRaises(ValueError):DemandPreprocessor().fit(bad)

    def test_y_is_ignored_even_when_it_cannot_be_read(self):
        class Poison:
            def __array__(self,*args,**kwargs):raise AssertionError("y accessed")
            def __iter__(self):raise AssertionError("y accessed")
        first=DemandPreprocessor().fit(self.train,y=Poison())
        second=DemandPreprocessor().fit(self.train)
        self.assertEqual(first.to_state(),second.to_state())
        np.testing.assert_allclose(DemandPreprocessor().fit_transform(self.train,Poison()),first.transform(self.train))

    def test_serialization_roundtrip_is_independent_of_repository_reads(self):
        p=DemandPreprocessor().fit(self.train);state=p.to_state()
        serialized=json.loads(json.dumps(state,allow_nan=False))
        restored=DemandPreprocessor.from_state(serialized,expected_sha256=state["sha256"])
        with patch("v2.preprocessing.read_context",side_effect=AssertionError("repository read forbidden")):
            np.testing.assert_array_equal(p.transform(self.train),restored.transform(self.train))
        self.assertEqual(list(p.get_feature_names_out()),list(restored.get_feature_names_out()))
        state["state"]["medians"][0]=999
        self.assertNotEqual(state,p.to_state())

    def test_corrupted_state_is_rejected_including_recomputed_hash(self):
        p=DemandPreprocessor().fit(self.train)
        for field,value in [("columns",["target_ventas_mes"]),("scales",[0]*16),("y_used",True)]:
            state=p.to_state();state["state"][field]=value;state["sha256"]=canonical_hash(state["state"])
            with self.subTest(field=field),self.assertRaises(ValueError):DemandPreprocessor.from_state(state)
        state=p.to_state();state["state"]["medians"][0]=999
        with self.assertRaises(ValueError):DemandPreprocessor.from_state(state)

    def test_clone_is_unfitted_and_pipeline_transform_is_compatible(self):
        from sklearn.pipeline import Pipeline
        p=DemandPreprocessor().fit(self.train);cloned=clone(p)
        self.assertEqual(cloned.get_params(),p.get_params())
        with self.assertRaises(NotFittedError):cloned.transform(self.train)
        pipeline=Pipeline([("preprocessing",DemandPreprocessor())])
        np.testing.assert_allclose(pipeline.fit_transform(self.train),p.transform(self.train))

    def test_empty_inference_batch_has_stable_shape(self):
        p=DemandPreprocessor().fit(self.train)
        self.assertEqual(p.transform(self.train.iloc[:0]).shape,(0,len(p.get_feature_names_out())))

    def test_real_dataset_loader_checks_partition_without_fitting_it(self):
        train=load_feature_partition("TRAIN");validation=load_feature_partition("VALIDATION");fold=load_feature_partition("TRAIN",fold_id="F1")
        self.assertEqual((len(train),len(validation),len(fold)),(2520,504,1008))
        self.assertEqual(set(train),set(RAW)|{CONTEXT})
        self.assertFalse(train.attrs["labels_processed"])
        self.assertLess(train[CONTEXT].max(),validation[CONTEXT].min())
        self.assertLessEqual(fold[CONTEXT].max(),"2025-06")
        with self.assertRaises(ValueError):load_feature_partition("ANY")
        with self.assertRaises(ValueError):load_feature_partition("TEST",fold_id="F1")

    def test_loading_real_features_and_fixture_preprocessing_never_fit_regressors(self):
        from sklearn.linear_model import LinearRegression
        from sklearn.ensemble import RandomForestRegressor
        with patch.object(LinearRegression,"fit",side_effect=AssertionError("model training forbidden")),patch.object(RandomForestRegressor,"fit",side_effect=AssertionError("model training forbidden")):
            actual=load_feature_partition("TRAIN")
            self.assertEqual(len(actual),2520)
            matrix=DemandPreprocessor().fit_transform(self.train)
            self.assertEqual(matrix.shape,(15,30))

    def test_actual_dataset_features_pass_domain_checks_without_learning_parameters(self):
        fields=read_context(ROOT)[2]
        for part in ["TRAIN","VALIDATION"]:
            frame=load_feature_partition(part)
            data,months=validate_frame(frame,fields)
            self.assertEqual(len(months),len(frame))
            self.assertEqual(set(data),set(RAW))

    def test_loader_rejects_changed_dataset_bytes_before_reading_rows(self):
        import shutil
        spec=json.loads((ROOT/"v2/contracts/preprocessing.v2_1.json").read_text(encoding="utf-8"))
        relative=spec["input_build"]["relative_path"]
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp",prefix="adapter-integrity-") as tmp:
            root=Path(tmp)
            for name in ["v2/contracts/preprocessing.v2_1.json","v2/contracts/experiments.v2_1.json",relative+"/manifest.json",relative+"/schema.json",relative+"/dataset_supervisado.csv"]:
                dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
            with (root/relative/"dataset_supervisado.csv").open("a",encoding="utf-8") as f:f.write("corrupted\n")
            with self.assertRaises(ValueError):load_feature_partition("TRAIN",root=root)

    def test_fixture_fit_provenance_does_not_claim_to_be_the_real_training_partition(self):
        p=DemandPreprocessor().fit(self.train);state=p.to_state()["state"]
        self.assertEqual(state["fit_rows"],15)
        self.assertIn("CALLER_FRAME",state["fit_frame_origin"])
        self.assertEqual(len(state["fit_frame_sha256"]),64)
        self.assertIn("schema_binding_build_manifest_sha256",state)
        altered=self.train.copy();altered.loc[0,"ventas_hace_2_meses"]+=1
        other=DemandPreprocessor().fit(altered).to_state()["state"]
        self.assertNotEqual(other["fit_frame_sha256"],state["fit_frame_sha256"])

    def test_automatic_approved_prefixes_work_with_cloned_pipeline_folds(self):
        p=DemandPreprocessor()
        for count,end in [(6,"2025-06"),(9,"2025-09"),(12,"2025-12"),(15,"2026-03")]:
            fitted=clone(p).fit(fixture(months=count));s=fitted.to_state()["state"]
            self.assertEqual(s["train_window"],["2025-01",end])
            self.assertEqual(s["configured_window"],["2025-01","2026-03"])
            self.assertEqual(s["fit_rows"],count)

    def test_real_loader_preserves_row_identity_outside_feature_columns(self):
        frame=load_feature_partition("TRAIN",fold_id="F1")
        self.assertEqual(list(frame.index.names),["productId","locationId",CONTEXT])
        self.assertFalse(frame.index.has_duplicates)
        self.assertEqual(frame.index[0],(1,5,"2025-01"))
        self.assertNotIn("productId",frame.columns)
        manifest=read_context(ROOT)[5]
        self.assertEqual(len(validate_cohort(frame,list(frame[CONTEXT]),manifest)),64)

    def test_random_row_split_or_incomplete_real_cohort_fails_before_statistics_fit(self):
        frame=load_feature_partition("TRAIN",fold_id="F1")
        for broken in [frame.iloc[1:],frame.iloc[::2]]:
            with patch("v2.preprocessing.StandardScaler.fit",side_effect=AssertionError("No statistics fit before cohort check")):
                with self.assertRaises(ValueError):DemandPreprocessor().fit(broken)

    def test_month_index_and_context_cannot_disagree(self):
        frame=load_feature_partition("TRAIN",fold_id="F1")
        months=list(frame[CONTEXT]);months[0]="2025-02"
        with self.assertRaises(ValueError):validate_cohort(frame,months,read_context(ROOT)[5])


if __name__=="__main__":unittest.main()
