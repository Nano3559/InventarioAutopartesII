"""Rutina V2-08. Preparación por defecto, ejecución supervisada deshabilitada.

La lógica de comparación se prueba con dobles que registran llamadas, sin
aprender relaciones. Nunca se carga TEST por esta rutina.
"""
import csv
from datetime import datetime,timezone
from importlib.metadata import version
import itertools
import json
import math
from pathlib import Path
import re
import sys
import time

import numpy as np
import pandas as pd

from v2.preprocessing import RAW,CONTEXT,DemandPreprocessor,load_feature_partition,read_context,validate_frame
from v2.structure import ROOT,sha256_file,token
from v2.validate_build import canonical_hash

VERSION="experiments-2.1-1"
TARGET="target_ventas_mes"
KEYS=["productId","locationId",CONTEXT]


def context(root=ROOT):
    root=Path(root).resolve()
    spec_path=root/"v2/contracts/runner.v2_1.json"
    spec=json.loads(spec_path.read_text(encoding="utf-8"))
    if spec["runner_version"]!=VERSION or spec["dataset_version"]!="2.1.0":raise ValueError("Versión de rutina inválida")
    plan_path=root/spec["experiment_contract"];pre_path=root/spec["preprocessing_contract"]
    for path in [plan_path,pre_path]:
        if not path.resolve().is_relative_to(root/"v2/contracts"):raise ValueError("Contrato fuera de V2")
    if sha256_file(plan_path)!=spec["experiment_contract_sha256"] or sha256_file(pre_path)!=spec["preprocessing_contract_sha256"]:
        raise ValueError("Contrato modificado")
    if sha256_file(root/"v2/preprocessing.py")!=spec["preprocessing_implementation_sha256"]:raise ValueError("Adaptador modificado")
    pre,plan,fields,source,_,manifest=read_context(root)
    if pre["experiment_contract_sha256"]!=spec["experiment_contract_sha256"]:raise ValueError("Adaptador y rutina usan planes distintos")
    return spec,plan,fields,source,manifest


def align_targets(X,y):
    if not isinstance(X,pd.DataFrame) or not isinstance(y,pd.Series) or y.name!=TARGET:
        raise TypeError("X debe ser DataFrame e y Series target_ventas_mes")
    for index in [X.index,y.index]:
        if not isinstance(index,pd.MultiIndex) or list(index.names)!=KEYS or index.has_duplicates:
            raise ValueError("Identidades duplicadas o inválidas")
    if set(X.index)!=set(y.index):raise ValueError("Targets faltantes o sobrantes")
    aligned=y.reindex(X.index)
    for value in aligned:
        if isinstance(value,(bool,np.bool_)) or not isinstance(value,(int,float,np.number)):
            raise ValueError("Target no numérico")
        if not math.isfinite(value) or value<0 or not float(value).is_integer():raise ValueError("Target inválido")
    if CONTEXT not in X or any(k[2]!=m for k,m in zip(X.index,X[CONTEXT])):raise ValueError("Mes y clave no coinciden")
    return aligned.copy()


def load_xy(partition,*,fold_id=None,root=ROOT):
    if partition not in ("TRAIN","VALIDATION"):raise ValueError("TEST está reservado y no se carga en comparación")
    X=load_feature_partition(partition,fold_id=fold_id,root=root)
    spec,_,fields,source,_,_=read_context(root)
    validate_frame(X,fields)
    start,end=X.attrs["window"];path=source/"dataset_supervisado.csv"
    keys=[];values=[]
    with path.open(encoding="utf-8",newline="") as f:
        for row in csv.DictReader(f):
            if not start<=row[CONTEXT]<=end:continue
            if not re.fullmatch(r"\d+",row[TARGET]):raise ValueError("Target no entero no negativo")
            keys.append((int(row["productId"]),int(row["locationId"]),row[CONTEXT]));values.append(int(row[TARGET]))
    if sha256_file(path)!=spec["csv_sha256"]:raise ValueError("CSV cambió durante la carga")
    y=pd.Series(values,index=pd.MultiIndex.from_tuples(keys,names=KEYS),name=TARGET,dtype="int64")
    return X,align_targets(X,y)


def candidates(plan):
    result=[]
    rf=plan["models"]["random_forest"]
    grid_keys=sorted(rf["grid"])
    configurations=[dict(zip(grid_keys,values)) for values in itertools.product(*(rf["grid"][k] for k in grid_keys))]
    for group in plan["feature_sets"]:
        for model,params in [("linear_regression",plan["models"]["linear_regression"]["parameters"])]+[("random_forest",{**rf["fixed"],**p}) for p in configurations]:
            key=canonical_hash([group["id"],model,params])[:24]
            result.append(dict(candidate_id="candidate-"+key,feature_set_id=group["id"],columns=list(group["columns"]),
                               model=model,parameters=dict(params)))
    return result


def make_pipeline(candidate,root=ROOT):
    """Construye objetos sin fit. Solo parámetros enumerados en el plan."""
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    _,plan,_,_,_=context(root)
    approved={c["candidate_id"]:c for c in candidates(plan)}
    if candidate["candidate_id"] not in approved or candidate!=approved[candidate["candidate_id"]]:raise ValueError("Candidato no aprobado")
    model=LinearRegression(**candidate["parameters"]) if candidate["model"]=="linear_regression" else RandomForestRegressor(**candidate["parameters"])
    return Pipeline([("preprocessing",DemandPreprocessor(candidate["feature_set_id"],candidate["model"],root=root)),("model",model)])


def _metrics(y,pred):
    with np.errstate(over="ignore",invalid="ignore",divide="ignore"):
        residual=pred-y
        if not np.isfinite(residual).all():return dict(mae=None,rmse=None,r2=None,r2_status="NUMERIC_OVERFLOW")
        scale=float(np.max(np.abs(residual))) if len(y) else 0
        mae=scale*float(np.mean(np.abs(residual)/scale)) if scale else 0.0
        rmse=scale*math.sqrt(float(np.mean((residual/scale)**2))) if scale else 0.0
        if len(y)<2:r2=None;status="INSUFFICIENT_SAMPLES"
        elif np.all(y==y[0]):r2=None;status="CONSTANT_TARGET"
        else:
            denominator=float(np.sum((y-np.mean(y))**2));ratio=float(np.sum((residual/scale)**2))*scale/denominator*scale if scale else 0
            r2=1-ratio;status="DEFINED" if math.isfinite(r2) else "NUMERIC_OVERFLOW"
            if not math.isfinite(r2):r2=None
    return dict(mae=mae,rmse=rmse,r2=r2,r2_status=status)


def score_predictions(y,predictions):
    raw_y=np.asarray(y)
    if np.iscomplexobj(raw_y) or raw_y.ndim!=1 or any(isinstance(v,(bool,np.bool_)) for v in raw_y):
        raise ValueError("Etiquetas no numéricas de unidades")
    y=raw_y.astype(float)
    if y.ndim!=1 or len(y)==0 or not np.isfinite(y).all() or np.any(y<0) or np.any(y!=np.floor(y)):
        raise ValueError("Etiquetas inválidas para unidades vendidas")
    raw=np.asarray(predictions)
    base=dict(rows_requested=len(y),rows_scored=0,abstentions=len(y),negative_raw_predictions=0,
              mae=None,rmse=None,r2=None,r2_status="INVALID_PREDICTIONS",raw_metrics=None)
    if raw.ndim!=1 or len(raw)!=len(y) or np.iscomplexobj(raw) or any(isinstance(v,(bool,np.bool_)) for v in raw):
        return {**base,"status":"INVALID_SHAPE_OR_TYPE"}
    try:raw=raw.astype(float)
    except (TypeError,ValueError):return {**base,"status":"INVALID_SHAPE_OR_TYPE"}
    finite=np.isfinite(raw);valid=int(finite.sum())
    base.update(rows_scored=valid,abstentions=len(y)-valid,negative_raw_predictions=int(np.sum(raw[finite]<0)))
    if valid!=len(y):return {**base,"status":"NONFINITE_REJECTED_NO_SUBSET_METRICS"}
    policy=np.maximum(raw,0)
    metrics=_metrics(y,policy)
    return {**base,**metrics,"status":"OK" if metrics["mae"] is not None else "NUMERIC_OVERFLOW", "raw_metrics":_metrics(y,raw)}


def _rank(item):
    kind=item["candidate"]["model"];p=item["candidate"]["parameters"]
    return (({"baseline":0,"linear_regression":1,"random_forest":2})[kind],len(item["candidate"]["columns"]),
            p.get("max_depth",0) or float("inf"),-p.get("min_samples_leaf",0),item["candidate"]["candidate_id"])


def choose(items,tolerance):
    valid=[i for i in items if i["score"]["status"]=="OK" and i["score"]["abstentions"]==0]
    if not valid:raise ValueError("Ningún candidato con cobertura completa")
    best=valid[0]
    for item in valid[1:]:
        a,b=item["score"]["mae"],best["score"]["mae"]
        if a<b-tolerance or abs(a-b)<=tolerance and _rank(item)<_rank(best):best=item
    return best


def rotation_reference(X,y):
    y=align_targets(X,y);out={}
    for key,group in y.groupby(level=[0,1]):
        frequency=float((group>0).mean())
        out[key]="ZERO" if frequency==0 else "LOW" if frequency<=1/3 else "MEDIUM" if frequency<=2/3 else "HIGH"
    return out


def group_scores(X,y,pred,rotation):
    result=[];labels={"product":[],"store":[],"product_store":[],"rotation_train":[],"historical_stock_coverage":[],"historical_mode":[]}
    for i,key in enumerate(X.index):
        labels["product"].append(str(key[0]));labels["store"].append(str(key[1]));labels["product_store"].append(f"{key[0]}/{key[1]}")
        labels["rotation_train"].append(rotation.get(key[:2],"UNKNOWN"))
        coverage=X.iloc[i]["cobertura_stock_mes_anterior"]
        labels["historical_stock_coverage"].append("NONE" if coverage==0 else "COMPLETE" if coverage==1 else "PARTIAL")
        p=X.iloc[i]["proporcion_por_mayor_mes_anterior"];c=X.iloc[i]["cobertura_modalidad_mes_anterior"]
        labels["historical_mode"].append("UNKNOWN_OR_PARTIAL" if pd.isna(p) or pd.isna(c) or c<1 else "RETAIL" if p==0 else "WHOLESALE" if p==1 else "MIXED")
    pred=np.asarray(pred)
    for dimension,values in labels.items():
        for name in sorted(set(values)):
            positions=np.flatnonzero(np.array(values)==name)
            result.append(dict(dimension=dimension,group=name,**score_predictions(y.iloc[positions],pred[positions])))
    return result


def _evaluate(candidate,pipeline,X,y,V,z):
    y=align_targets(X,y);z=align_targets(V,z);start=time.perf_counter();fit_seconds=0;predict_seconds=0;phase="FIT"
    try:
        pipeline.fit(X.copy(deep=True),y.copy(deep=True))
        fit_seconds=time.perf_counter()-start;start=time.perf_counter();phase="PREDICT"
        pred=pipeline.predict(V.copy(deep=True));score=score_predictions(z,pred)
        predict_seconds=time.perf_counter()-start
        phase="TRAIN_DIAGNOSTIC"
        train_score=score_predictions(y,pipeline.predict(X.copy(deep=True)))
        if train_score["status"]!="OK":score={**score,"status":"INVALID_TRAIN_DIAGNOSTIC"}
        return dict(candidate=candidate,score=score,train_score=train_score,fit_seconds=fit_seconds,
                    predict_seconds=predict_seconds,predictions=pred,pipeline=pipeline)
    except Exception as exc:
        return dict(candidate=candidate,score=dict(status="FIT_OR_PREDICT_FAILED",mae=None,rmse=None,r2=None,
            r2_status="FAILED",rows_requested=len(z),rows_scored=0,abstentions=len(z),negative_raw_predictions=0,raw_metrics=None),
            train_score=None,fit_seconds=time.perf_counter()-start if phase=="FIT" else fit_seconds,
            predict_seconds=time.perf_counter()-start if phase=="PREDICT" else predict_seconds,
            failure=type(exc).__name__+": "+str(exc),predictions=None,pipeline=None)


def _comparison_logic(plan,loader,factory):
    """Núcleo en memoria. La entrada pública execute exige autorización primero.

    Tests inyectan dobles sin aprendizaje y loaders de fixtures. No escribe logs.
    """
    all_candidates=candidates(plan);tolerance=plan["metrics_and_selection"]["tie_numerical_tolerance"]
    fold_data={f["id"]:(loader("TRAIN",fold_id=f["id"]),loader("VALIDATION",fold_id=f["id"])) for f in plan["temporal_validation"]["folds"]}
    records=[];summaries=[];fit_attempts=0
    for candidate in all_candidates:
        fold_results=[]
        for fold in plan["temporal_validation"]["folds"]:
            (X,y),(V,z)=fold_data[fold["id"]]
            r=_evaluate(candidate,factory(candidate),X,y,V,z);fit_attempts+=1
            # Los modelos internos no son artefactos finales ni se retienen entre folds.
            r["pipeline"]=None;r["predictions"]=None
            r.update(fold_id=fold["id"],fit_partition="TRAIN",evaluation_partition="INTERNAL_TRAIN_VALIDATION")
            records.append(r);fold_results.append(r)
        valid=all(r["score"]["status"]=="OK" and r["score"]["abstentions"]==0 for r in fold_results)
        summaries.append(dict(candidate=candidate,score=dict(status="OK" if valid else "CV_FAILED",abstentions=0 if valid else 1,
            mae=float(np.mean([r["score"]["mae"] for r in fold_results])) if valid else None)))
    selected=[]
    for group in plan["feature_sets"]:
        for kind in ("linear_regression","random_forest"):
            pool=[s for s in summaries if s["candidate"]["feature_set_id"]==group["id"] and s["candidate"]["model"]==kind and s["score"]["status"]=="OK"]
            if pool:selected.append(choose(pool,tolerance)["candidate"])
    X,y=loader("TRAIN");V,z=loader("VALIDATION");y=align_targets(X,y);z=align_targets(V,z)
    rotation=rotation_reference(X,y)
    baseline_candidate=dict(candidate_id="baseline-lag1",model="baseline",feature_set_id="BASELINE_LAG1",columns=["ventas_mes_anterior"],parameters={})
    baseline_pred=V["ventas_mes_anterior"].to_numpy(dtype=float)
    baseline=dict(candidate=baseline_candidate,score=score_predictions(z,baseline_pred),predictions=baseline_pred,pipeline=None,
                  fit_seconds=0,predict_seconds=0,fit_partition="NONE",evaluation_partition="VALIDATION",fold_id="OUTER")
    baseline["groups"]=group_scores(V,z,baseline_pred,rotation)
    outer=[baseline]
    for candidate in selected:
        result=_evaluate(candidate,factory(candidate),X,y,V,z);fit_attempts+=1
        result.update(fit_partition="TRAIN",evaluation_partition="VALIDATION",fold_id="OUTER")
        if result["score"]["status"]=="OK":result["groups"]=group_scores(V,z,result["predictions"],rotation)
        outer.append(result)
    if fit_attempts>plan["execution_budget"]["maximum_planned_fits"]:raise ValueError("Presupuesto de ajustes excedido")
    winner=choose(outer,tolerance);review=[]
    if winner["candidate"]["model"]!="baseline":
        if winner["score"]["rmse"]>baseline["score"]["rmse"]+tolerance:review.append("RMSE_WORSE_THAN_BASELINE")
        ref={(g["dimension"],g["group"]):g for g in baseline["groups"]}
        for g in winner.get("groups",[]):
            b=ref[(g["dimension"],g["group"])]
            if g["mae"] is not None and b["mae"] is not None and g["mae"]>b["mae"]+tolerance:
                review.append("GROUP_TRADEOFF:"+g["dimension"]+":"+g["group"])
    decision=dict(candidate_id=winner["candidate"]["candidate_id"],model=winner["candidate"]["model"],
                  status="REVIEW_REQUIRED" if review else "BASELINE_RETAINED" if winner["candidate"]["model"]=="baseline" else "CANDIDATE_SELECTED_NOT_PROMOTED",
                  review_reasons=review,test_status="RESERVED_NOT_LOADED",active_model_changed=False)
    return dict(records=records+outer,cv_summaries=summaries,selection=decision,winner=winner,
                fit_attempts=fit_attempts,test_loaded=False)


def prepare_run(run_id,root=ROOT):
    root=Path(root).resolve();token(run_id);spec,plan,fields,source,manifest=context(root)
    slices=[]
    for fold in [None]+[f["id"] for f in plan["temporal_validation"]["folds"]]:
        for part in ["TRAIN","VALIDATION"]:
            X,y=load_xy(part,fold_id=fold,root=root)
            slices.append(dict(partition=part,fold_id=fold,rows=len(X),first_month=X[CONTEXT].min(),last_month=X[CONTEXT].max(),
                row_keys_sha256=canonical_hash([list(k) for k in X.index]),
                aligned_targets_sha256=canonical_hash([int(v) for v in y]),index_equal=X.index.equals(y.index)))
    result=dict(runner_version=VERSION,status="DRY_RUN_READY_NOT_TRAINED",dataset_version="2.1.0",
        input_manifest_sha256=plan["input_build"]["manifest_sha256"],candidate_count=len(candidates(plan)),
        planned_fit_count=plan["execution_budget"]["maximum_planned_fits"],actual_model_fit_count=0,
        actual_preprocessing_fit_count=0,actual_predict_calls=0,actual_predictive_metrics=False,slices=slices,
        targets_loaded_for_alignment_only=True,test_targets_loaded=False,
        model_training_authorized=spec["model_training_authorized"],preprocessing_implementation_sha256=spec["preprocessing_implementation_sha256"],
        experiment_contract_sha256=spec["experiment_contract_sha256"],runner_implementation_sha256=sha256_file(Path(__file__)))
    dest=root/"reports/v2/experiment_runner"/run_id
    if not dest.resolve().is_relative_to(root/"reports/v2"):raise ValueError("Reporte fuera de V2")
    dest.mkdir(parents=True,exist_ok=False)
    with (dest/"run_plan.json").open("x",encoding="utf-8") as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
    return dest,result


def _public_record(record):
    return {k:v for k,v in record.items() if k not in ("pipeline","predictions")}


def execute_experiments(run_id,root=ROOT):
    """Ruta futura completa. El contrato actual impide entrar a cualquier fit."""
    root=Path(root).resolve();token(run_id);spec,plan,_,source,manifest=context(root)
    if spec["model_training_authorized"] is not True:raise PermissionError("Entrenamiento deshabilitado por instrucción actual. Preparar no autoriza ejecutar.")
    report=root/"reports/v2/2.1.0"/manifest["build_id"]/"runs"/run_id
    model_dir=root/"models/v2"/run_id
    for p,base in [(report,root/"reports/v2"),(model_dir,root/"models/v2")]:
        if not p.resolve().is_relative_to(base) or p.exists():raise FileExistsError("Ruta inválida o run existente")
    report.mkdir(parents=True,exist_ok=False);model_dir.mkdir(parents=True,exist_ok=False)
    try:
        outcome=_comparison_logic(plan,lambda p,fold_id=None:load_xy(p,fold_id=fold_id,root=root),lambda c:make_pipeline(c,root=root))
        winner=outcome["winner"];artifact_hash=None
        if winner["pipeline"] is not None:
            import joblib
            joblib.dump(winner["pipeline"],model_dir/"candidate.joblib")
            artifact_hash=sha256_file(model_dir/"candidate.joblib")
            state=winner["pipeline"].named_steps["preprocessing"].to_state()
            with (model_dir/"preprocessing.json").open("x",encoding="utf-8") as f:json.dump(state,f,ensure_ascii=False,allow_nan=False)
        summary=dict(runner_version=VERSION,run_id=run_id,dataset_version="2.1.0",origin="SYNTHETIC",
            manifest_sha256=plan["input_build"]["manifest_sha256"],csv_sha256=sha256_file(source/"dataset_supervisado.csv"),
            selection=outcome["selection"],fit_attempts=outcome["fit_attempts"],artifact_sha256=artifact_hash,
            cv_summaries=outcome["cv_summaries"],records=[_public_record(r) for r in outcome["records"]],
            test_loaded=False,commercial_accuracy_certified=False,created_at=datetime.now(timezone.utc).isoformat())
        with (report/"comparison.json").open("x",encoding="utf-8") as f:json.dump(summary,f,ensure_ascii=False,indent=2,allow_nan=False)
        with (model_dir/"manifest.json").open("x",encoding="utf-8") as f:json.dump({k:v for k,v in summary.items() if k not in ("records","cv_summaries")},f,ensure_ascii=False,indent=2)
        _publish_tracking(root,plan,run_id,summary,outcome["records"])
        return report,summary
    except Exception as exc:
        with (report/"failure.json").open("x",encoding="utf-8") as f:json.dump({"status":"FAILED","error":type(exc).__name__+": "+str(exc),"test_loaded":False},f)
        raise


def _publish_tracking(root,plan,run_id,summary,records):
    """Solo V2, commit del log después de un run autorizado. Sin tocar V1."""
    import os
    target=root/plan["tracking"]["path"]
    if not target.resolve().is_relative_to(root/"reports/v2"):raise ValueError("Log fuera de V2")
    extra=["raw_mae","raw_rmse","raw_r2","raw_r2_status","evaluation_status","selection_status"]
    columns=plan["tracking"]["columns"]+extra
    lock=target.with_name(target.name+".lock");lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open("x",encoding="utf-8") as f:f.write(run_id)
    try:
        existing=[]
        if target.exists():
            with target.open(encoding="utf-8",newline="") as f:
                reader=csv.DictReader(f)
                if reader.fieldnames!=columns:raise ValueError("Header de experimentos incompatible")
                existing=list(reader)
            if any(r["run_id"]==run_id for r in existing):raise FileExistsError("Run ya registrado")
        rows=[]
        for record in records:
            c=record["candidate"];s=record["score"];raw=s.get("raw_metrics") or {}
            row={name:None for name in columns}
            row.update(run_id=run_id,dataset_version="2.1.0",build_id=plan["future_dataset_variant"]["build_id"],
                dataset_sha256=summary["csv_sha256"],config_sha256=canonical_hash(c["parameters"]),
                split_sha256=canonical_hash(plan["temporal_validation"]),feature_set_id=c["feature_set_id"],columns_sha256=canonical_hash(c["columns"]),
                model=c["model"],parameters_json=json.dumps(c["parameters"],sort_keys=True),preprocessing_version="preprocessing-2.1-1",
                prediction_policy_version=plan["prediction_policy"]["version"],fit_partition=record["fit_partition"],evaluation_partition=record["evaluation_partition"],
                fold_id=record["fold_id"],seed=42,fit_seconds=record["fit_seconds"],predict_seconds=record["predict_seconds"],
                python_version=sys.version.split()[0],sklearn_version=version("scikit-learn"),
                artifact_sha256=summary["artifact_sha256"] if c["candidate_id"]==summary["selection"]["candidate_id"] and record["fold_id"]=="OUTER" else None,
                evaluation_status=s["status"],selection_status=summary["selection"]["status"],notes=record.get("failure",""))
            for name in ["mae","rmse","r2","r2_status","rows_requested","rows_scored","abstentions","negative_raw_predictions"]:row[name]=s.get(name)
            for name in ["mae","rmse","r2"]:row["raw_"+name]=raw.get(name)
            row["raw_r2_status"]=raw.get("r2_status")
            rows.append(row)
        temporary=root/"tmp"/("tracking-"+run_id+".csv")
        if not temporary.resolve().is_relative_to(root/"tmp"):raise ValueError("Temporal fuera de V2")
        temporary.parent.mkdir(parents=True,exist_ok=True)
        with temporary.open("x",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=columns,lineterminator="\n");writer.writeheader();writer.writerows(existing+rows)
        os.replace(temporary,target)
    finally:lock.unlink()
