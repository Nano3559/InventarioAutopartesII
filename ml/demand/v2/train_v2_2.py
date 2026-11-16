"""Entrenamiento autorizado 2.2.0: TRAIN/CV y VALIDATION, nunca TEST."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from importlib.metadata import version
import csv
import json
from pathlib import Path
import time
import numpy as np
from .structure import ROOT,sha256_file,token
from .validate_build import canonical_hash
from .experiments_v2_2 import context as prepared_context,candidates,load_xy
from .preprocessing_train_v2_2 import AuthorizedPreprocessor22
from .experiments import _evaluate,choose,rotation_reference,group_scores,score_predictions,align_targets

VERSION='training-2.2-1'


def context(root=ROOT):
    root=Path(root).resolve();p=root/'v2/contracts/training.v2_2.json';auth=json.loads(p.read_text(encoding='utf-8'))
    if not auth['model_training_authorized'] or not auth['real_preprocessing_fit_authorized'] or auth['test_allowed'] or auth['allowed_partitions']!=['TRAIN','VALIDATION']:raise PermissionError('Alcance no autorizado')
    if sha256_file(root/auth['base_plan_path'])!=auth['base_plan_sha256'] or sha256_file(root/'v2/contracts/runner.v2_2.json')!=auth['prepared_runner_sha256']:raise ValueError('Plan preparado cambió')
    for relative,expected in auth['implementations_sha256'].items():
        target=(root/relative).resolve()
        if not target.is_relative_to(root/'v2') or sha256_file(target)!=expected:raise ValueError('Implementación autorizada cambió')
    _,plan,fields,source,manifest=prepared_context(root)
    if plan['input_build']['manifest_sha256']!=auth['input_manifest_sha256'] or auth['max_fits']!=plan['execution_budget']['maximum_planned_fits']:raise ValueError('Build o presupuesto distintos')
    return auth,plan,fields,source,manifest


def factory(candidate,root=ROOT):
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor
    estimator=LinearRegression(**candidate['parameters']) if candidate['model']=='linear_regression' else RandomForestRegressor(**candidate['parameters'])
    return Pipeline([('preprocessing',AuthorizedPreprocessor22(candidate['feature_set_id'],candidate['model'],root=root)),('model',estimator)])


def compare(plan,loader,pipeline_factory,*,workers=4,evaluator=_evaluate,progress=None):
    """Paralelismo entre candidatos, instancias independientes por fold."""
    approved=candidates(plan);folds=plan['temporal_validation']['folds'];tol=plan['metrics_and_selection']['tie_numerical_tolerance']
    data={f['id']:(loader('TRAIN',fold_id=f['id']),loader('VALIDATION',fold_id=f['id'])) for f in folds}
    def cv(candidate):
        rows=[]
        for fold in folds:
            (X,y),(V,z)=data[fold['id']]
            r=evaluator(candidate,pipeline_factory(candidate),X,y,V,z)
            r.update(fold_id=fold['id'],fit_partition='TRAIN',evaluation_partition='INTERNAL_TRAIN_VALIDATION')
            r['pipeline']=None;r['predictions']=None;rows.append(r)
        valid=all(r['score']['status']=='OK' and r['score']['abstentions']==0 for r in rows)
        summary=dict(candidate=candidate,score=dict(status='OK' if valid else 'CV_FAILED',abstentions=0 if valid else 1,
                      mae=float(np.mean([r['score']['mae'] for r in rows])) if valid else None))
        return rows,summary
    by_id={};done=0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(cv,c):c['candidate_id'] for c in approved}
        for future in as_completed(futures):
            by_id[futures[future]]=future.result();done+=1
            if progress:progress('CV_CANDIDATES',done,len(approved))
    records=[];summaries=[]
    for c in approved:
        rows,s=by_id[c['candidate_id']];records.extend(rows);summaries.append(s)
    selected=[]
    for group in plan['feature_sets']:
        for kind in ['linear_regression','random_forest']:
            pool=[s for s in summaries if s['candidate']['feature_set_id']==group['id'] and s['candidate']['model']==kind and s['score']['status']=='OK']
            if pool:selected.append(choose(pool,tol)['candidate'])
    X,y=loader('TRAIN');V,z=loader('VALIDATION');y=align_targets(X,y);z=align_targets(V,z)
    rotation=rotation_reference(X,y)
    baseline_candidate=dict(candidate_id='baseline-2.2-lag1',model='baseline',feature_set_id='BASELINE_LAG1',columns=['ventas_mes_anterior'],parameters={})
    pred=V['ventas_mes_anterior'].to_numpy(dtype=float)
    baseline=dict(candidate=baseline_candidate,score=score_predictions(z,pred),train_score=score_predictions(y,X['ventas_mes_anterior'].to_numpy(dtype=float)),predictions=pred,pipeline=None,
                  fit_seconds=0.,predict_seconds=0.,fold_id='OUTER',fit_partition='NONE',evaluation_partition='VALIDATION')
    baseline['groups']=group_scores(V,z,pred,rotation)
    def outer(candidate):
        result=evaluator(candidate,pipeline_factory(candidate),X,y,V,z)
        result.update(fold_id='OUTER',fit_partition='TRAIN',evaluation_partition='VALIDATION')
        if result['score']['status']=='OK':result['groups']=group_scores(V,z,result['predictions'],rotation)
        return result
    outer_rows=[baseline];by_outer={};done=0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(outer,c):c['candidate_id'] for c in selected}
        for future in as_completed(futures):
            by_outer[futures[future]]=future.result();done+=1
            if progress:progress('OUTER_CANDIDATES',done,len(selected))
    outer_rows.extend(by_outer[c['candidate_id']] for c in selected)
    winner=choose(outer_rows,tol);reviews=[]
    if winner['candidate']['model']!='baseline':
        if winner['score']['rmse']>baseline['score']['rmse']+tol:reviews.append('RMSE_WORSE_THAN_BASELINE')
        reference={(r['dimension'],r['group']):r for r in baseline['groups']}
        for g in winner.get('groups',[]):
            b=reference[(g['dimension'],g['group'])]
            if g['mae'] is not None and b['mae'] is not None and g['mae']>b['mae']+tol:reviews.append('GROUP_TRADEOFF:'+g['dimension']+':'+g['group'])
    failed=[r for r in records+outer_rows if r['score']['status']!='OK']
    if failed:reviews.append('FAILED_CANDIDATES_REQUIRE_REVIEW')
    attempts=len(records)+len(outer_rows)-1
    if attempts>plan['execution_budget']['maximum_planned_fits']:raise ValueError('Presupuesto excedido')
    return dict(cv_records=records,cv_summaries=summaries,outer=outer_rows,winner=winner,fit_attempts=attempts,
                selection=dict(candidate_id=winner['candidate']['candidate_id'],model=winner['candidate']['model'],status='REVIEW_REQUIRED' if reviews else 'BASELINE_RETAINED' if winner['candidate']['model']=='baseline' else 'VALIDATION_CANDIDATE_NOT_FINAL',review_reasons=reviews,test_status='RESERVED_NOT_LOADED',active_model_changed=False),
                X=X,y=y,V=V,z=z,failed_candidates=len(failed),test_loaded=False)


def public(record):return {k:v for k,v in record.items() if k not in ['pipeline','predictions']}


def save_json(path,value):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')


def execute(run_id,root=ROOT):
    root=Path(root).resolve();token(run_id);auth,plan,_,source,manifest=context(root)
    if run_id!=auth['run_id']:raise PermissionError('Run no autorizado')
    report=root/'reports/v2/2.2.0'/manifest['build_id']/'runs'/run_id;models=root/'models/v2'/run_id
    for p,base in [(report,root/'reports/v2/2.2.0'),(models,root/'models/v2')]:
        if not p.resolve().is_relative_to(base) or p.exists():raise FileExistsError('Run existente o ruta inválida')
    report.mkdir(parents=True,exist_ok=False);models.mkdir(parents=True,exist_ok=False)
    save_json(report/'started.json',dict(status='RUNNING_TRAIN_VALIDATION_ONLY',authorization_sha256=sha256_file(root/'v2/contracts/training.v2_2.json'),test_allowed=False))
    start=time.perf_counter()
    def progress(phase,done,total):print(phase+' '+str(done)+'/'+str(total),flush=True)
    try:
        outcome=compare(plan,lambda part,fold_id=None:load_xy(part,fold_id=fold_id,root=root),lambda c:factory(c,root),workers=auth['parallel_candidates'],progress=progress)
        import joblib
        artifacts={}
        for row in outcome['outer']:
            if row['pipeline'] is None:continue
            key=row['candidate']['candidate_id'];path=models/(key+'.joblib');joblib.dump(row['pipeline'],path)
            state=row['pipeline'].named_steps['preprocessing'].to_state();save_json(models/(key+'.preprocessing.json'),state)
            artifacts[key]=dict(path=path.relative_to(root).as_posix(),sha256=sha256_file(path),preprocessing_sha256=state['sha256'],fit_window=state['state']['train_window'],fit_rows=state['state']['fit_rows'])
        summary=dict(runner_version=VERSION,run_id=run_id,dataset_version='2.2.0',build_id=manifest['build_id'],origin='SYNTHETIC',
          manifest_sha256=plan['input_build']['manifest_sha256'],csv_sha256=sha256_file(source/'dataset_supervisado.csv'),authorization_sha256=sha256_file(root/'v2/contracts/training.v2_2.json'),
          experiment_plan_sha256=auth['base_plan_sha256'],fit_attempts=outcome['fit_attempts'],failed_candidates=outcome['failed_candidates'],
          parallel_candidates=auth['parallel_candidates'],estimator_n_jobs=1,elapsed_seconds=time.perf_counter()-start,
          selection=outcome['selection'],cv_summaries=outcome['cv_summaries'],records=[public(r) for r in outcome['cv_records']+outcome['outer']],
          artifacts=artifacts,test_loaded=False,test_targets_loaded=False,active_api_artifact_changed=False,commercial_accuracy_certified=False,
          prediction_policy='max(raw_prediction,0), continuous units without rounding. Raw negatives and raw metrics retained.',
          environment_versions={k:version(k) for k in ['numpy','pandas','scikit-learn','joblib']})
        save_json(report/'comparison.json',summary)
        with (report/'validation_predictions.csv').open('x',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['candidate_id','productId','locationId','mes_objetivo','target','raw_prediction','prediction']);writer.writeheader()
            for row in outcome['outer']:
                if row['predictions'] is None:continue
                for key,target,raw in zip(outcome['V'].index,outcome['z'],row['predictions']):writer.writerow(dict(candidate_id=row['candidate']['candidate_id'],productId=key[0],locationId=key[1],mes_objetivo=key[2],target=int(target),raw_prediction=float(raw),prediction=max(float(raw),0)))
        save_json(models/'manifest.json',{k:summary[k] for k in ['runner_version','run_id','dataset_version','manifest_sha256','authorization_sha256','selection','artifacts','test_loaded','active_api_artifact_changed','environment_versions']})
        tracking=root/plan['tracking']['path']
        if not tracking.resolve().is_relative_to(root/'reports/v2/2.2.0') or tracking.exists():raise FileExistsError('No sobrescribir tracking previo')
        columns=plan['tracking']['columns']
        with tracking.open('x',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=columns);w.writeheader()
            for record in summary['records']:
                c=record['candidate'];score=record['score'];key=c['candidate_id'];artifact=artifacts.get(key) if record['fold_id']=='OUTER' else None
                values=dict(run_id=run_id,dataset_version='2.2.0',build_id=manifest['build_id'],dataset_sha256=summary['csv_sha256'],config_sha256=auth['base_plan_sha256'],split_sha256=sha256_file(source/'split_manifest.json'),
                  feature_set_id=c['feature_set_id'],columns_sha256=canonical_hash(c['columns']),model=c['model'],parameters_json=json.dumps(c['parameters'],sort_keys=True),preprocessing_version='preprocessing-2.2-training-1',prediction_policy_version='NONNEGATIVE_CONTINUOUS_1',
                  fit_partition=record['fit_partition'],evaluation_partition=record['evaluation_partition'],fold_id=record['fold_id'],seed=42,fit_seconds=record['fit_seconds'],predict_seconds=record['predict_seconds'],
                  python_version=__import__('platform').python_version(),sklearn_version=version('scikit-learn'),artifact_sha256=artifact['sha256'] if artifact else None,notes=score['status'])
                values.update({k:score.get(k) for k in ['mae','rmse','r2','r2_status','rows_requested','rows_scored','abstentions','negative_raw_predictions']});w.writerow(values)
        print('COMPLETED '+str(report),flush=True)
        return report,summary
    except Exception as exc:
        save_json(report/'failure.json',dict(status='FAILED_PARTIAL_NOT_PROMOTED',error=type(exc).__name__+': '+str(exc),test_loaded=False))
        raise

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);a=p.parse_args();execute(a.run_id)
