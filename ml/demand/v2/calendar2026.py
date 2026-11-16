"""Versioned offline calendar 4.0.0: closed history to Oct 2026, Nov inference.

Reuses the pinned simulator mechanics, never edits old builds or reads old TEST.
The DEMO realization is separate from TRAIN/VALIDATION/TEST and never used to fit.
"""
import argparse
from collections import Counter
import copy
import csv
from datetime import datetime, timezone, timedelta
import importlib.util
import json
import math
from pathlib import Path
import shutil
import time

from .scenario_data import ROOT, FEATURES, NUMERIC, TARGET, sha, frame

VERSION = '4.0.0'
BUILD_ID = 'calendar-20261116-01'
RUN_ID = 'calendar-model-20261116-01'
BUILD = ROOT / 'data/repuestopro_v2' / VERSION / BUILD_ID
REPORT = ROOT / 'reports/v2' / VERSION / RUN_ID
SPLITS = {'TRAIN': ['2025-02', '2026-04'], 'VALIDATION': ['2026-05', '2026-07'],
          'TEST': ['2026-08', '2026-10'], 'DEMO': ['2025-02', '2026-10']}
FORECAST_MONTH = '2026-11'


def private_module(name, filename):
    spec = importlib.util.spec_from_file_location('v2.' + name, ROOT / 'v2' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def simulator():
    engine = private_module('_calendar2026_generator', 'generate_scenarios_v1.py')
    original_rng = engine.rng
    engine.rng = lambda *keys: original_rng('calendar-4.0.0', *keys)
    def month(i):
        n = 2024 * 12 + 10 + i  # November 2024, 24 closed months to October 2026.
        return f'{n // 12:04d}-{n % 12 + 1:02d}'
    engine.month = month
    return engine


def write_json(path, value):
    with Path(path).open('x', encoding='utf8') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')


def generate():
    if BUILD.exists(): raise FileExistsError('Do not overwrite a dataset')
    temp = ROOT / 'tmp' / BUILD_ID
    temp.mkdir(parents=True, exist_ok=False)
    engine = simulator()
    recipe = engine.dependencies()
    recipe = copy.deepcopy(recipe)
    recipe.update(dataset_version=VERSION, generator_version='calendar-generator-1.0.0',
                  period=['2024-11', '2026-10'], warmup=['2024-11', '2025-01'], splits=SPLITS,
                  world_policy='Independent fresh calendar RNG worlds. DEMO is never used in model selection or scoring. November has no generated outcome.')
    tables, dictionary = engine.simulate(recipe, recorded_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
    engine.write_tables(temp, tables, dictionary)
    schema = copy.deepcopy(dictionary)
    schema.update(dataset_version=VERSION, status='GENERATED_SYNTHETIC', no_dataset_generated=False)
    write_json(temp/'schema.json', schema)
    write_json(temp/'catalog_reference.json', json.loads((ROOT/recipe['catalog']['path']).read_text(encoding='utf8')))
    write_json(temp/'recipe.json', recipe)
    write_json(temp/'split_manifest.json', {'splits':SPLITS,'warmup':recipe['warmup'],'random_split':False,'test_status':'SEALED','forecast_month':FORECAST_MONTH,'world_policy':recipe['world_policy']})
    write_json(temp/'manifest.json', {'dataset_version':VERSION,'build_id':BUILD_ID,'seed':42,
        'origin':'ACADEMIC_SYNTHETIC_NOT_REAL_SALES','history_end':'2026-10','forecast_month':FORECAST_MONTH,
        'future_target_generated':False,'generator':{'path':'v2/calendar2026.py','sha256':sha(__file__)},
        'reused_engine':{'path':'v2/generate_scenarios_v1.py','sha256':sha(ROOT/'v2/generate_scenarios_v1.py')},
        'dependencies':{k:recipe[k] for k in ('dictionary','sources','catalog','calibration','base_calibration')},
        'counts':{k:len(v) for k,v in tables.items()},'automotive':'EXCLUDED_LICENSE_PENDING',
        'deployment_history':'DEMO BASE outcomes only, independent from all evaluation partitions',
        'stock_scope':'Independent monthly academic stock scenarios, not a certified continuous commercial inventory ledger'})
    from .validate_scenarios_v1 import validate
    result = validate(temp)
    if not result['valid']: raise ValueError(result['errors'][:10])
    write_json(temp/'validation.json', result)
    files = sorted(temp.iterdir())
    with (temp/'checksums.sha256').open('x',encoding='ascii') as f:
        f.write(''.join(f'{sha(p)}  {p.name}\n' for p in files if p.is_file()))
    BUILD.parent.mkdir(parents=True, exist_ok=True)
    temp.rename(BUILD)
    print(json.dumps({'build':str(BUILD),'validation':result}),flush=True)


def verify():
    for line in (BUILD/'checksums.sha256').read_text().splitlines():
        digest,name=line.split(None,1)
        if sha(BUILD/name.strip()) != digest: raise ValueError('DATASET_INTEGRITY')


def records(partition):
    if partition not in ('TRAIN','VALIDATION','DEMO'): raise PermissionError('TEST_IS_SEALED')
    with (BUILD/'dataset_supervisado.csv').open(encoding='utf8',newline='') as f:
        return [r for r in csv.DictReader(f) if r['realization_id']==partition]


def deployment_snapshots():
    selected={r['scenario_id']:r for r in records('DEMO') if r['scenario_id'].endswith('-BASE')}
    catalog=json.loads((BUILD/'catalog_reference.json').read_text(encoding='utf8'))
    products={p['id']:p for p in catalog['products']}; locations={p['id']:p for p in catalog['locations']}
    outcomes={}; history={}; closing={}
    def read(name):
        with (BUILD/(name+'.csv')).open(encoding='utf8',newline='') as f:
            yield from (r for r in csv.DictReader(f) if r['scenario_id'] in selected)
    for r in read('base_mensual'):
        outcomes[r['scenario_id']]=r
    for r in read('daily_ledger'):
        closing[r['scenario_id']]=int(r['closing_units'])
    for r in read('closed_history_monthly'):
        history.setdefault(r['scenario_id'],[]).append(r)
    raw={}
    mapping={'price_plan_events':'prices','exchange_quote_events':'quote','cost_plan_events':'cost','opening_stock_snapshot':'stock','open_order_plan':'orders','pending_shipment_plan':'shipments','logistics_policy':'logistics'}
    for table,key in mapping.items():
        for r in read(table):
            bucket=raw.setdefault(r['scenario_id'],{'prices':[],'orders':[],'shipments':[]})
            if key in ('prices','orders','shipments'): bucket[key].append(r)
            else: bucket[key]=r
    snapshots={}
    for row in selected.values():
        if row['mes_objetivo']!='2026-10': continue
        pid,lid=int(row['productId']),int(row['locationId']); sid=row['scenario_id']
        all_rows=sorted((r for r in selected.values() if r['productId']==row['productId'] and r['locationId']==row['locationId']),key=lambda r:r['mes_objetivo'])
        display=[]
        for r in all_rows:
            if r['mes_objetivo']<'2026-01': continue
            o=outcomes[r['scenario_id']]
            # Modality totals are obtained from the same daily generator outcome,
            # via the following month's closed history; October is reconstructed
            # from daily BASE fulfilment using that world's deterministic mechanism.
            nxt=next((n for n in all_rows if n['mes_objetivo']>r['mes_objetivo']),None)
            h=next((h for h in history[nxt['scenario_id']] if h['mes']==r['mes_objetivo']),None) if nxt else None
            if h:
                retail,wholesale=int(h['unidades_por_menor']),int(h['unidades_por_mayor'])
            else:
                engine=simulator(); i=(2026*12+9)-(2024*12+10)
                profile=engine.rng('profile',pid,lid)
                level=profile.choice([4,12,35,90]); occurrence_offset=profile.choice([0,.25,.6])
                # The exact October channel totals are exported by the generator
                # in its closed-history rows for TEST/other worlds, not reused.
                # Replay this DEMO month's known daily demand with published inputs.
                recipe=json.loads((BUILD/'recipe.json').read_text())
                basecal=json.loads((ROOT/recipe['base_calibration']['path']).read_text())
                def find(n,k):
                    if isinstance(n,dict):
                        if k in n:return n[k]
                        for v in n.values():
                            x=find(v,k)
                            if x is not None:return x
                    return None
                occurrence=find(basecal,'occurrence_probability')
                if occurrence is None:occurrence=1-find(basecal,'zero_probability')
                a,b=engine.demand_stream(pid,lid,'DEMO',i,level,min(.95,occurrence+occurrence_offset))
                plan=raw[sid]; incoming=sum(int(s['pending_units_at_cutoff']) for s in plan['shipments'])
                arrival=1 if not plan['shipments'] else (engine.start(plan['shipments'][0]['expected_arrival_at'][:7]) if False else datetime.fromisoformat(plan['shipments'][0]['expected_arrival_at'])).day
                shocks=[engine.rng('price-rounding',pid,lid,'DEMO',i,j).random() for j in range(len(a))]
                result=engine.fulfil(a,b,int(plan['stock']['sellable_physical_units']),arrival,incoming,rounding_shocks=shocks)
                retail,wholesale=result['retail'],result['wholesale']
            if retail+wholesale!=int(o['target_ventas_mes']): raise ValueError('DEPLOYMENT_HISTORY_MISMATCH')
            display.append({'month':r['mes_objetivo'],'retailUnits':retail,'wholesaleUnits':wholesale,'unknownModeUnits':0,'units':retail+wholesale})
        last=display[-1]; tail=display[-3:]
        s=copy.deepcopy(raw[sid]); base_id=f'calendar-2026-{pid}-{lid}-november'
        cutoff='2026-11-01T00:00:00-04:00'; end='2026-12-01T00:00:00-04:00'
        s.update(baseSnapshotId=base_id,productId=pid,locationId=lid,productName=products[pid]['name'],locationName=locations[lid]['name'],targetMonth=FORECAST_MONTH,
                 features={k:row[k] for k in FEATURES},displayHistory=display,
                 history=[{'mes':h['month'],'unidades_por_menor':h['retailUnits'],'unidades_por_mayor':h['wholesaleUnits'],'unidades_modalidad_desconocida':0} for h in tail])
        for p in s['prices']:p.update(effective_from=cutoff,effective_to=end)
        s['cost']['effective_from']=cutoff
        s['stock'].update(sellable_physical_units=closing[sid],snapshot_at=cutoff)
        s['orders']=[]
        # Explicit November supply assumptions, known at cutoff. No receipts or sales outcome.
        s['shipments']=[{'shipment_id':base_id+'-incoming','pending_units_at_cutoff':50,'reserved_after_horizon_units':0,'expected_arrival_at':'2026-11-10T00:00:00-04:00'}]
        s['logistics']['planned_order_at']=cutoff
        f=s['features']; f.update(ventas_mes_anterior=last['units'],ventas_hace_2_meses=tail[-2]['units'],ventas_hace_3_meses=tail[-3]['units'],
            proporcion_por_mayor_mes_anterior=last['wholesaleUnits']/last['units'] if last['units'] else '',mes_sin=math.sin(2*math.pi*11/12),mes_cos=math.cos(2*math.pi*11/12),
            dias_sin_stock_mes_anterior=int(outcomes[sid]['actual_stockout_days']),variacion_precio_menor_plan_ponderada=0,variacion_precio_mayor_plan_ponderada=0,dias_vigencia_nuevo_precio_plan=0,
            stock_vendible_al_corte_unidades=closing[sid],reservas_posteriores_unidades=0,compromisos_por_menor_horizonte_unidades=0,compromisos_por_mayor_horizonte_unidades=0,
            entradas_plan_horizonte_unidades=50,dias_hasta_primera_entrada_plan=9)
        snapshots[base_id]=s
    if len(snapshots)!=168:raise ValueError('Incomplete deployment catalog')
    return snapshots


def train():
    import joblib,numpy as np,platform,sklearn
    from .train_scenarios import pipeline,metrics
    verify()
    model_dir=ROOT/'models/v2'/RUN_ID
    if REPORT.exists() or model_dir.exists():raise FileExistsError('Do not overwrite experiment')
    a,b=records('TRAIN'),records('VALIDATION'); X,V=frame(a),frame(b)
    y=np.array([float(r[TARGET]) for r in a]); yv=np.array([float(r[TARGET]) for r in b])
    counts=Counter(r['scenario_family_id'] for r in a); weights=np.array([1/counts[r['scenario_family_id']] for r in a])
    baseline=np.array([float(r['ventas_mes_anterior']) for r in b]); results=[{'name':'baseline',**metrics(yv,baseline)}]; fitted={}
    for kind in ('linear','forest_squared','forest_absolute'):
        model=pipeline(kind); start=time.perf_counter(); model.fit(X,y,**{model.steps[-1][0]+'__sample_weight':weights})
        result={'name':kind,**metrics(yv,np.maximum(0,model.predict(V))),'seconds':time.perf_counter()-start}
        results.append(result); fitted[kind]=model; print(json.dumps(result),flush=True)
    winner=min(results,key=lambda r:(r['mae'],r['rmse'],results.index(r)))
    if winner['name']=='baseline':raise ValueError('BASELINE_WINS_DO_NOT_ACTIVATE')
    model=fitted[winner['name']]; REPORT.mkdir(parents=True); model_dir.mkdir(parents=True)
    artifact=model_dir/'model.joblib';joblib.dump(model,artifact)
    write_json(REPORT/'snapshots.json',deployment_snapshots())
    release={'releaseId':RUN_ID,'datasetVersion':VERSION,'modelVersion':RUN_ID,'policyVersion':'SCENARIO_NONNEGATIVE_1','modelKind':winner['name'],
        'artifact':artifact.relative_to(ROOT).as_posix(),'artifactSha256':sha(artifact),'snapshots':(REPORT/'snapshots.json').relative_to(ROOT).as_posix(),'snapshotsSha256':sha(REPORT/'snapshots.json'),
        'datasetManifestSha256':sha(BUILD/'manifest.json'),'features':FEATURES,'bounds':{k:[float(X[k].min()),float(X[k].max())] for k in NUMERIC},
        'metrics':{'partition':'VALIDATION','origin':'SYNTHETIC',**{k:winner[k] for k in ('mae','rmse','r2')}},'experiments':results,'baseline':metrics(yv,baseline),
        'trainRows':len(a),'validationRows':len(b),'selectedUsing':'VALIDATION_MAE_RMSE_SIMPLICITY','testScored':False,'forecastMonth':FORECAST_MONTH,'historyEnd':'2026-10','seed':42,
        'origin':'ACADEMIC_SYNTHETIC_NOT_REAL_SALES','versions':{'python':platform.python_version(),'sklearn':sklearn.__version__},'recordedAt':datetime.now(timezone.utc).isoformat()}
    write_json(REPORT/'release.json',release)
    with (REPORT/'experiments.csv').open('x',encoding='utf8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['name','mae','rmse','r2','seconds']);writer.writeheader();writer.writerows(results)
    print(json.dumps({'winner':winner,'releaseSha256':sha(REPORT/'release.json')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['generate','train']);args=parser.parse_args()
    generate() if args.action=='generate' else train()
