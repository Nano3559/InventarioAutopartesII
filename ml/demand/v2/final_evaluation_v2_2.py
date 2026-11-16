"""Accepted 2.2 artifact. A reserved, non-repeatable final TEST event, no fit."""
import csv
from datetime import datetime, timezone
from importlib.metadata import version
from io import BytesIO
import json
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from .structure import ROOT, sha256_file
from .data_v2_2 import read_context, read_prefix, KEYS, TARGET
from .preprocessing import RAW, CONTEXT, validate_frame, validate_cohort
from .preprocessing_train_v2_2 import AuthorizedPreprocessor22
from .experiments_v2_2 import load_xy
from .experiments import score_predictions, group_scores, rotation_reference
from .validate_build import canonical_hash, cutoff, instant, month_offset

VERSION = 'final-test-2.2-1'
BUILD = 'data/repuestopro_v2/2.2.0/calibrated-20261115-01'
SELECTION = 'v2/contracts/selection.v2_2.json'
FINAL = 'reports/v2/2.2.0/calibrated-20261115-01/final_test'
POLICY = dict(version='NONNEGATIVE_CONTINUOUS_1', nonfinite='REJECT_ALL_NO_SUBSET', negative='CLIP_ZERO', rounding='NONE')
ACCEPTED = 'candidate-2.2-1202b43393aac05173a4f603'


def write_new(path, document):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(document, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def freeze(root=ROOT):
    root = Path(root).resolve()
    if (root/SELECTION).exists() or (root/FINAL).exists():
        raise FileExistsError('Selection exists. Never overwrite or unconsume TEST.')
    comparison_path = root/'reports/v2/2.2.0/calibrated-20261115-01/runs/train-2.2-20261115-01/comparison.json'
    comparison = json.loads(comparison_path.read_text(encoding='utf-8'))
    assert comparison['selection']['candidate_id'] == ACCEPTED
    artifact = comparison['artifacts'][ACCEPTED]
    model = joblib.load(BytesIO((root/artifact['path']).read_bytes()))
    state = model.named_steps['preprocessing'].to_state()
    paths = [artifact['path'], artifact['path'].replace('.joblib','.preprocessing.json'),
             comparison_path.relative_to(root).as_posix(),
             'v2/final_evaluation_v2_2.py','v2/preprocessing_train_v2_2.py','v2/preprocessing.py',
             'v2/data_v2_2.py','v2/experiments.py','v2/contracts/training.v2_2.json',
             'v2/contracts/preprocessing.v2_2.json','v2/contracts/experiments.v2_2.json',
             *[BUILD+'/'+n for n in ['manifest.json','schema.json','split_manifest.json','dataset_supervisado.csv','base_mensual.csv','catalog_reference.json','validation.json']]]
    assert sha256_file(root/artifact['path']) == artifact['sha256']
    selection = dict(evaluation_version=VERSION, selection_id='accepted-absolute-2.2-20261115-01',
        user_accepted=True, accepted_candidate=ACCEPTED,
        acceptance_evidence='User accepts current forest for H4, authorizes one TEST evaluation and administrator integration.',
        accepted_scope='SYNTHETIC_ACADEMIC_H4_ONLY', accepted_known_tradeoffs=dict(products_worse_validation=13,product_store_worse_validation=36),
        frozen_at=datetime.now(timezone.utc).isoformat(), dataset_version='2.2.0',build_id='calibrated-20261115-01',
        artifact=artifact['path'],artifact_sha256=artifact['sha256'],preprocessing_state_sha256=state['sha256'],
        features=state['state']['columns'],regressor_parameters=model.named_steps['model'].get_params(),
        input_hashes={p:sha256_file(root/p) for p in paths},
        environment={p:version(p) for p in ['scikit-learn','numpy','pandas','joblib']},
        prediction_policy=POLICY,test_authorization='ONE_FINAL_EVALUATION_NO_RETRAINING',
        training_window=['2025-01','2026-03'],training_rows=2520,
        horizon='ONE_MONTH_ROLLING_CLOSED_HISTORY_NO_REFIT',automatic_replenishment=False)
    write_new(root/SELECTION,selection)
    return selection


def read_selection(root=ROOT):
    root=Path(root).resolve();s=json.loads((root/SELECTION).read_text(encoding='utf-8'))
    if s['evaluation_version']!=VERSION or s['accepted_candidate']!=ACCEPTED or not s['user_accepted'] or s['test_authorization']!='ONE_FINAL_EVALUATION_NO_RETRAINING' or s['prediction_policy']!=POLICY:
        raise ValueError('Unaccepted selection or policy')
    for rel,digest in s['input_hashes'].items():
        p=(root/rel).resolve()
        if not p.is_relative_to(root) or sha256_file(p)!=digest:raise ValueError('Frozen input changed: '+rel)
    for p,v in s['environment'].items():
        if version(p)!=v:raise ValueError('Environment differs: '+p)
    return s,sha256_file(root/SELECTION)


def load_model(root,selection):
    p=Path(root)/selection['artifact']
    if sha256_file(p)!=selection['artifact_sha256']:raise ValueError('Artifact hash differs')
    model=joblib.load(BytesIO(p.read_bytes()))
    if type(model) is not Pipeline or list(model.named_steps)!=['preprocessing','model'] or type(model.named_steps['preprocessing']) is not AuthorizedPreprocessor22 or type(model.named_steps['model']) is not RandomForestRegressor:raise ValueError('Wrong pipeline')
    state=model.named_steps['preprocessing'].to_state()
    if state['sha256']!=selection['preprocessing_state_sha256'] or state['state']['columns']!=selection['features'] or state['state']['fit_rows']!=2520 or state['state']['train_window']!=['2025-01','2026-03'] or model.named_steps['model'].get_params()!=selection['regressor_parameters']:raise ValueError('Frozen state differs')
    return model


def load_test_once(root):
    spec,plan,fields,source,_,manifest=read_context(root)
    schema=json.loads((source/'schema.json').read_text(encoding='utf-8'))
    rows=read_prefix(source/'dataset_supervisado.csv',schema['columns'],'2025-01','2026-09',manifest,CONTEXT)
    rows=[r for r in rows if '2026-07'<=r[CONTEXT]<='2026-09']
    if len(rows)!=504 or canonical_hash(rows)!=manifest['split_design']['sets']['TEST']['row_content_sha256']:raise ValueError('TEST hash/cohort mismatch')
    base=read_prefix(source/'base_mensual.csv',schema['design']['supporting_tables']['base_mensual.csv']['columns'],'2024-10','2026-09',manifest,'mes')
    lookup={(r['productId'],r['locationId'],r['mes']):r for r in base}
    for r in rows:
        key=(r['productId'],r['locationId'],r[CONTEXT])
        if r[TARGET]!=lookup[key]['unidades_vendidas_brutas'] or instant(r['feature_cutoff_at'])!=cutoff(key[2]):raise ValueError('TEST target/cutoff differs')
        for n,name in [(1,'ventas_mes_anterior'),(2,'ventas_hace_2_meses'),(3,'ventas_hace_3_meses')]:
            h=lookup[(*key[:2],month_offset(key[2],-n))]
            if r[name]!=h['unidades_vendidas_brutas'] or instant(h['ventas_disponibles_at'])>cutoff(key[2]):raise ValueError('Invalid TEST lag')
    X=pd.DataFrame([{**{f['name']:r[f['name']] for f in fields},CONTEXT:r[CONTEXT]} for r in rows],columns=[*RAW,CONTEXT])
    X.index=pd.MultiIndex.from_tuples([(r['productId'],r['locationId'],r[CONTEXT]) for r in rows],names=KEYS)
    validate_frame(X,fields);validate_cohort(X,list(X[CONTEXT]),manifest)
    y=pd.Series([r[TARGET] for r in rows],index=X.index,name=TARGET,dtype='int64')
    for name,key in [('dataset_supervisado.csv','csv_sha256'),('base_mensual.csv','base_csv_sha256')]:
        if sha256_file(source/name)!=spec[key]:raise ValueError('Data changed during TEST')
    return X,y


def evaluate(root=ROOT):
    root=Path(root).resolve();dest=root/FINAL
    if dest.exists():raise FileExistsError('TEST consumed. Never retry or delete its reservation.')
    s,digest=read_selection(root)
    with patch.object(AuthorizedPreprocessor22,'fit',side_effect=AssertionError('No fit')),patch.object(RandomForestRegressor,'fit',side_effect=AssertionError('No fit')),patch.object(StandardScaler,'fit',side_effect=AssertionError('No fit')):
        model=load_model(root,s);Xtrain,ytrain=load_xy('TRAIN',root=root);rotation=rotation_reference(Xtrain,ytrain)
        dest.mkdir(parents=True,exist_ok=False)
        write_new(dest/'evaluation_started.json',dict(status='CONSUMED_BEFORE_TEST_ACCESS',selection_sha256=digest,artifact_sha256=s['artifact_sha256'],at=datetime.now(timezone.utc).isoformat(),retry_policy='NEVER_RETRY_AFTER_FAILURE_OR_CRASH'))
        write_new(dest/'selection_frozen.json',s)
        try:
            X,y=load_test_once(root)
            write_new(dest/'prediction_started.json',dict(model_predict_calls=1,rows=len(X)))
            before=model.named_steps['preprocessing'].to_state()
            raw=np.asarray(model.predict(X),dtype=float)  # Sole TEST predict invocation.
            if raw.shape!=(504,) or not np.isfinite(raw).all():raise ValueError('Invalid TEST predictions')
            pred=np.maximum(raw,0);base=X.ventas_mes_anterior.to_numpy(dtype=float)
            score=score_predictions(y,raw);baseline=score_predictions(y,base)
            if before!=model.named_steps['preprocessing'].to_state():raise ValueError('State mutated')
            read_selection(root)
            diff=pred-y.to_numpy()
            result=dict(status='FINAL_TEST_EVALUATED_ONCE',selection_id=s['selection_id'],selection_sha256=digest,artifact_sha256=s['artifact_sha256'],dataset_version='2.2.0',build_id=s['build_id'],origin='SYNTHETIC',period=['2026-07','2026-09'],rows=504,model_metrics=score,baseline_metrics=baseline,mae_reduction_vs_baseline_percent=100*(1-score['mae']/baseline['mae']),model_fit_calls=0,preprocessing_fit_calls=0,model_predict_calls=1,test_loader_calls=1,selection_changed_after_test=False,commercial_accuracy_certified=False,horizon=s['horizon'],groups=group_scores(X,y,raw,rotation),baseline_groups=group_scores(X,y,base,rotation),by_month=[dict(month=m,model=score_predictions(y.loc[X[CONTEXT]==m],raw[X[CONTEXT]==m]),baseline=score_predictions(y.loc[X[CONTEXT]==m],base[X[CONTEXT]==m])) for m in sorted(set(X[CONTEXT]))],tail=dict(max_absolute_error=float(abs(diff).max()),p95_absolute_error=float(np.quantile(abs(diff),.95)),abs_error_gt20=int((abs(diff)>20).sum())),totals=dict(observed=int(y.sum()),predicted=float(pred.sum()),signed_bias=float(diff.mean())),completed_at=datetime.now(timezone.utc).isoformat())
            write_new(dest/'result.json',result)
            with (dest/'predictions.csv').open('x',encoding='utf-8',newline='') as f:
                w=csv.writer(f);w.writerow([*KEYS,TARGET,'prediction_raw','prediction_policy','baseline_lag1'])
                for i,k in enumerate(X.index):w.writerow([*k,int(y.iloc[i]),float(raw[i]),float(pred[i]),float(base[i])])
            write_new(dest/'verification.json',dict(result_sha256=sha256_file(dest/'result.json'),selection_sha256=digest,artifact_sha256_after=sha256_file(root/s['artifact']),preprocessing_state_unchanged=True,model_fit_calls=0,model_predict_calls=1))
            return result
        except BaseException as exc:
            write_new(dest/'failure.json',dict(status='CONSUMED_FAILED_DO_NOT_RETRY',error_type=type(exc).__name__,reason=str(exc)))
            raise


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args()
    r=freeze() if a.freeze else evaluate()
    print(json.dumps({k:r[k] for k in (['selection_id','artifact_sha256'] if a.freeze else ['status','model_metrics','baseline_metrics'])},allow_nan=False))
