"""Preparación 2.2.0 sin fit, predicciones, métricas o acceso a TEST."""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from .structure import ROOT,sha256_file,token
from .validate_build import canonical_hash
from .data_v2_2 import read_context,load_records,verify_targets_and_lags,CONTEXT,KEYS,TARGET
from .preprocessing_v2_2 import DemandPreprocessor22
from .preprocessing import validate_frame,missing
from .experiments import align_targets,candidates as enumerate_candidates

VERSION='experiments-2.2-1'


def context(root=ROOT):
    root=Path(root).resolve();p=root/'v2/contracts/runner.v2_2.json';runner=json.loads(p.read_text(encoding='utf-8'))
    if runner['runner_version']!=VERSION or runner['dataset_version']!='2.2.0' or runner['model_training_authorized']:raise ValueError('Contrato de preparación incompatible')
    for relative,expected in runner['implementations_sha256'].items():
        target=(root/relative).resolve()
        if not target.is_relative_to(root/'v2') or sha256_file(target)!=expected:raise ValueError('Implementación alterada')
    spec,plan,fields,source,_,manifest=read_context(root)
    if sha256_file(root/'v2/contracts/preprocessing.v2_2.json')!=runner['preprocessing_contract_sha256'] or spec['experiment_contract_sha256']!=runner['experiment_contract_sha256']:raise ValueError('Contratos distintos')
    return runner,plan,fields,source,manifest


def candidates(plan):
    rows=enumerate_candidates(plan)
    for row in rows:row['candidate_id']='candidate-2.2-'+canonical_hash([plan['input_build']['manifest_sha256'],row])[:24]
    if len({r['candidate_id'] for r in rows})!=len(rows):raise ValueError('Candidatos duplicados')
    return rows


def load_xy(partition,*,fold_id=None,root=ROOT):
    if partition not in ('TRAIN','VALIDATION'):raise PermissionError('TEST_RESERVED_NOT_OPENED')
    X,rows=load_records(partition,fold_id=fold_id,root=root)
    y=pd.Series([r[TARGET] for r in rows],index=X.index.copy(),name=TARGET,dtype='int64')
    aligned=align_targets(X,y)
    evidence=verify_targets_and_lags(rows,root=root)
    X.attrs['target_alignment_evidence']=evidence
    return X,aligned


def make_pipeline(candidate,root=ROOT):
    """Solo construye objetos no ajustados. No se llama desde prepare_run."""
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    _,plan,_,_,_=context(root);approved={c['candidate_id']:c for c in candidates(plan)}
    if candidate['candidate_id'] not in approved or approved[candidate['candidate_id']]!=candidate:raise ValueError('Candidato no aprobado')
    estimator=LinearRegression(**candidate['parameters']) if candidate['model']=='linear_regression' else RandomForestRegressor(**candidate['parameters'])
    return Pipeline([('preprocessing',DemandPreprocessor22(candidate['feature_set_id'],candidate['model'],root=root)),('model',estimator)])


def feature_review(X,fields):
    values,_=validate_frame(X,fields);result={}
    for field in fields:
        name=field['name'];observed=[v for v in values[name] if not missing(v)]
        result[name]=dict(nonmissing=len(observed),missing=len(X)-len(observed),unique_nonmissing=len(set(observed)),status='READY' if len(set(observed))>1 else 'REVIEW_REQUIRED_ALL_MISSING_OR_CONSTANT')
    return result


def prepare_run(run_id,root=ROOT):
    root=Path(root).resolve();token(run_id);runner,plan,fields,source,manifest=context(root)
    slices=[];reviews=[];all_candidates=candidates(plan)
    folds=[None]+[f['id'] for f in plan['temporal_validation']['folds']]
    for fold in folds:
        for part in ['TRAIN','VALIDATION']:
            X,y=load_xy(part,fold_id=fold,root=root)
            slices.append(dict(partition=part,fold_id=fold,rows=len(X),window=X.attrs['window'],prefix_rows_parsed=X.attrs['prefix_rows_parsed'],
                row_keys_sha256=canonical_hash([list(k) for k in X.index]),aligned_targets_sha256=canonical_hash([int(v) for v in y]),
                index_equal=X.index.equals(y.index),target_alignment_evidence=X.attrs['target_alignment_evidence'],test_rows_loaded=False))
            if part=='TRAIN':
                review=feature_review(X,fields);reviews.append(dict(fold_id=fold,columns=review))
                if any(v['status']!='READY' for v in review.values()):raise ValueError('Constante o faltante total en TRAIN. Revisar sin eliminar columnas silenciosamente.')
    future_fits=len(all_candidates)*len(plan['temporal_validation']['folds'])+2*len(plan['feature_sets'])
    if future_fits!=plan['execution_budget']['maximum_planned_fits']:raise ValueError('Presupuesto inconsistente')
    result=dict(status='PREPARED_READY_NOT_TRAINED',runner_version=VERSION,dataset_version='2.2.0',build_id=manifest['build_id'],manifest_sha256=plan['input_build']['manifest_sha256'],
        candidate_count=len(all_candidates),baseline='ventas_mes_anterior, no evaluado en esta tarea',future_fit_count=future_fits,
        actual_model_fits=0,actual_real_preprocessing_fits=0,predictions_computed=False,predictive_metrics_computed=False,test_rows_loaded=False,
        test_status='RESERVED_METADATA_ONLY',whole_file_hash_note='Byte hashes cover frozen files. No TEST rows, features or targets are parsed or evaluated.',slices=slices,
        preprocessing_contract_sha256=runner['preprocessing_contract_sha256'],experiment_contract_sha256=runner['experiment_contract_sha256'],
        fitted_artifacts_created=False,experiments_log_appended=False,active_api_artifact_changed=False)
    dest=root/'reports/v2/2.2.0'/manifest['build_id']/'preparation'/run_id
    if not dest.resolve().is_relative_to(root/'reports/v2/2.2.0'):raise ValueError('Destino inseguro')
    dest.mkdir(parents=True,exist_ok=False)
    for name,value in [('run_plan.json',result),('feature_review.json',reviews),('candidate_plan.json',all_candidates)]:
        with (dest/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    return dest,result


def execute_experiments(*args,**kwargs):
    raise PermissionError('TRAINING_NOT_AUTHORIZED_2_2: solo preparación en esta etapa.')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);a=p.parse_args();path,result=prepare_run(a.run_id)
    print(json.dumps({'path':str(path),'status':result['status'],'future_fits':result['future_fit_count'],'actual_fits':0,'test_rows_loaded':False},ensure_ascii=True))
