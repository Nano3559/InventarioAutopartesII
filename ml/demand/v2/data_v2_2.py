"""Lectura acotada 2.2.0. TEST se rechaza antes de abrir archivos de datos."""
import csv
import itertools
import json
import math
from pathlib import Path
import re
import pandas as pd
from .structure import ROOT,sha256_file
from .preprocessing import RAW,GROUPS,CONTEXT,validate_frame
from .validate_build import canonical_hash,month_offset,cutoff,instant

VERSION='preprocessing-2.2-1'
KEYS=['productId','locationId',CONTEXT]
TARGET='target_ventas_mes'


def months_between(start,end):
    result=[]
    while start<=end:result.append(start);start=month_offset(start,1)
    return result


def read_context(root=ROOT):
    root=Path(root).resolve();path=root/'v2/contracts/preprocessing.v2_2.json';spec=json.loads(path.read_text(encoding='utf-8'))
    if spec['adapter_version']!=VERSION or spec['dataset_version']!='2.2.0':raise ValueError('Adaptador incompatible')
    for relative,expected in spec['frozen_helper_sha256'].items():
        target=(root/relative).resolve()
        if not target.is_relative_to(root) or sha256_file(target)!=expected:raise ValueError('Helper congelado cambió')
    plan_path=(root/spec['experiment_contract']).resolve()
    if not plan_path.is_relative_to(root/'v2/contracts') or sha256_file(plan_path)!=spec['experiment_contract_sha256']:raise ValueError('Plan alterado')
    plan=json.loads(plan_path.read_text(encoding='utf-8'))
    if plan['input_build']!=spec['input_build'] or plan['training_authorized']:raise ValueError('Plan incompatible con preparación sin entrenamiento')
    source=(root/spec['input_build']['relative_path']).resolve()
    if not source.is_relative_to(root/'data/repuestopro_v2/2.2.0'):raise ValueError('Solo build 2.2.0 fijado')
    if sha256_file(source/'manifest.json')!=spec['input_build']['manifest_sha256']:raise ValueError('Manifest cambió')
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    if manifest['dataset_version']!='2.2.0' or manifest['origin']!='SYNTHETIC':raise ValueError('Origen o versión distintos')
    if sha256_file(source/'schema.json')!=spec['schema_sha256'] or sha256_file(source/'split_manifest.json')!=spec['split_sha256']:raise ValueError('Esquema o split alterado')
    schema=json.loads((source/'schema.json').read_text(encoding='utf-8'));split=json.loads((source/'split_manifest.json').read_text(encoding='utf-8'))
    if manifest['split_design']!=split or split['random_split'] or not split['new_v2_streams']:raise ValueError('Split incompatible')
    temporal=plan['temporal_validation']
    for name,key in [('TRAIN','outer_train'),('VALIDATION','outer_validation'),('TEST','test')]:
        limits=split['sets'][name]
        if temporal[key]!=[limits['start'],limits['end']]:raise ValueError('Ventanas distintas')
    if not temporal['outer_train'][1]<temporal['outer_validation'][0]<=temporal['outer_validation'][1]<temporal['test'][0]:raise ValueError('Solapamiento temporal')
    ids=set()
    for f in temporal['folds']:
        if f['id'] in ids or f['train'][0]!=temporal['outer_train'][0] or not f['train'][1]<f['validation'][0]<=f['validation'][1]<=temporal['outer_train'][1]:raise ValueError('Fold fuera de TRAIN')
        if month_offset(f['train'][1],1)!=f['validation'][0]:raise ValueError('Fold no consecutivo')
        ids.add(f['id'])
    if spec['fit_windows']!=[temporal['outer_train']]+[f['train'] for f in temporal['folds']]:raise ValueError('Ventanas de fit distintas')
    features=[c for c in schema['columns'] if c['role']=='FEATURE']
    if tuple(c['name'] for c in features)!=RAW or tuple(spec['raw_features'])!=RAW:raise ValueError('Features diferentes')
    if {g['id'] for g in plan['feature_sets']}!=set(GROUPS):raise ValueError('Grupos incompletos')
    for g in plan['feature_sets']:
        if tuple(g['columns'])!=RAW[:GROUPS[g['id']]]:raise ValueError('Grupo no canónico')
    return spec,plan,features,source,sha256_file(path),manifest


def window_for(partition,fold_id,plan):
    if partition not in ('TRAIN','VALIDATION'):raise PermissionError('TEST_RESERVED_NOT_OPENED')
    if fold_id is None:return plan['temporal_validation']['outer_train' if partition=='TRAIN' else 'outer_validation']
    folds=[f for f in plan['temporal_validation']['folds'] if f['id']==fold_id]
    if len(folds)!=1:raise ValueError('Fold desconocido')
    return folds[0]['train' if partition=='TRAIN' else 'validation']


def parse_value(value,field):
    if value=='':
        if not field['nullable']:raise ValueError('Null obligatorio: '+field['name'])
        return None
    if field['type']=='integer':
        if not re.fullmatch(r'-?\d+',value):raise ValueError('Entero inválido')
        return int(value)
    if field['type']=='number':
        result=int(value) if re.fullmatch(r'-?\d+',value) else float(value)
        if not math.isfinite(result):raise ValueError('Número no finito')
        return result
    return value


def read_prefix(path,columns,first_month,end,manifest,month_column):
    pairs=sorted((p,s) for p in manifest['selected_product_ids'] for s in manifest['selected_store_ids'])
    expected=[(p,s,m) for m in months_between(first_month,end) for p,s in pairs]
    result=[]
    with Path(path).open(encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=[c['name'] for c in columns]:raise ValueError('Cabecera diferente')
        # No pedir la siguiente fila: podría pertenecer a TEST.
        for position,raw in enumerate(itertools.islice(reader,len(expected))):
            if None in raw:raise ValueError('Columna inesperada')
            row={c['name']:parse_value(raw[c['name']],c) for c in columns}
            if (row['productId'],row['locationId'],row[month_column])!=expected[position]:raise ValueError('Prefijo no ordenado o cohorte incompleta')
            result.append(row)
    if len(result)!=len(expected):raise ValueError('Prefijo incompleto')
    return result


def load_records(partition,*,fold_id=None,root=ROOT):
    if partition not in ('TRAIN','VALIDATION'):raise PermissionError('TEST_RESERVED_NOT_OPENED')
    spec,plan,fields,source,_,manifest=read_context(root);start,end=window_for(partition,fold_id,plan)
    path=source/'dataset_supervisado.csv'
    if sha256_file(path)!=spec['csv_sha256']:raise ValueError('CSV alterado')
    schema=json.loads((source/'schema.json').read_text(encoding='utf-8'))
    prefix=read_prefix(path,schema['columns'],plan['temporal_validation']['outer_train'][0],end,manifest,CONTEXT)
    rows=[r for r in prefix if start<=r[CONTEXT]<=end]
    keys=[(r['productId'],r['locationId'],r[CONTEXT]) for r in rows]
    if fold_id is None:
        limits=manifest['split_design']['sets'][partition]
        if len(rows)!=limits['rows'] or canonical_hash(rows)!=limits['row_content_sha256']:raise ValueError('Hash o cantidad de la partición no coinciden')
    if sha256_file(path)!=spec['csv_sha256']:raise ValueError('CSV cambió durante lectura')
    X=pd.DataFrame([{**{c['name']:r[c['name']] for c in fields},CONTEXT:r[CONTEXT]} for r in rows],columns=[*RAW,CONTEXT])
    X.index=pd.MultiIndex.from_tuples(keys,names=KEYS)
    X.attrs.update(dataset_version='2.2.0',build_manifest_sha256=spec['input_build']['manifest_sha256'],partition=partition,fold_id=fold_id,window=[start,end],prefix_rows_parsed=len(prefix),test_rows_loaded=False)
    validate_frame(X,fields)
    return X,rows


def load_feature_partition(partition,*,fold_id=None,root=ROOT):
    return load_records(partition,fold_id=fold_id,root=root)[0]


def verify_targets_and_lags(rows,*,root=ROOT):
    spec,plan,_,source,_,manifest=read_context(root)
    if not rows or any(r[CONTEXT]>plan['temporal_validation']['outer_validation'][1] for r in rows):raise ValueError('Target fuera de TRAIN/VALIDATION')
    path=source/'base_mensual.csv'
    if sha256_file(path)!=spec['base_csv_sha256']:raise ValueError('Base alterada')
    schema=json.loads((source/'schema.json').read_text(encoding='utf-8'))
    end=max(r[CONTEXT] for r in rows)
    columns=schema['design']['supporting_tables']['base_mensual.csv']['columns']
    base=read_prefix(path,columns,schema['design']['split_design']['history_months'][0],end,manifest,'mes')
    lookup={(r['productId'],r['locationId'],r['mes']):r for r in base}
    for r in rows:
        key=(r['productId'],r['locationId'],r[CONTEXT]);actual=lookup[key]
        if r[TARGET]!=actual['unidades_vendidas_brutas']:raise ValueError('Target no corresponde a ventas observadas')
        history=[lookup[(*key[:2],month_offset(key[2],-i))] for i in [1,2,3]]
        for field,h in zip(['ventas_mes_anterior','ventas_hace_2_meses','ventas_hace_3_meses'],history):
            if r[field]!=h['unidades_vendidas_brutas'] or instant(h['ventas_disponibles_at'])>cutoff(key[2]):raise ValueError('Lag o disponibilidad inválida')
        if r['history_snapshot_id']!='history-retail-v2_2-'+canonical_hash([h['history_snapshot_id'] for h in reversed(history)])[:24]:raise ValueError('Snapshot histórico distinto')
        if instant(r['feature_cutoff_at'])!=cutoff(key[2]):raise ValueError('Corte incorrecto')
    if sha256_file(path)!=spec['base_csv_sha256']:raise ValueError('Base cambió durante lectura')
    return dict(rows_checked=len(rows),base_prefix_rows_parsed=len(base),latest_month_parsed=end,test_rows_loaded=False)
