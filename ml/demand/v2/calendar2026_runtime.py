"""Pinned 4.0.0 inference. No training, future outcomes or operational DB."""
from functools import lru_cache
import hashlib
import io
import joblib
from .calendar2026 import private_module, REPORT
from .scenario_data import ROOT, FEATURES, NUMERIC
from .scenario_runtime import ScenarioError, _read_verified_json

RELEASE_SHA='949c55733a6818bb93e97261c28f385ee3d2e3b0fcde6c42daa8dbe7d7dde00e'
METRICS_SHA='bcc14d9a7b04487ccbc8e4e7755d8353d7ad81ec168be9b37a06cadac7b91257'


@lru_cache(maxsize=1)
def release():
    r=_read_verified_json(REPORT/'release.json', RELEASE_SHA)
    if r['datasetVersion']!='4.0.0' or r['features']!=FEATURES:raise ScenarioError('INCOMPATIBLE_ARTIFACT')
    snapshots=_read_verified_json(ROOT/r['snapshots'], r['snapshotsSha256'])
    data=(ROOT/r['artifact']).read_bytes()
    if hashlib.sha256(data).hexdigest()!=r['artifactSha256']:raise ScenarioError('INCOMPATIBLE_ARTIFACT')
    return r,snapshots,joblib.load(io.BytesIO(data))


@lru_cache(maxsize=1)
def engine():
    module=private_module('_calendar2026_runtime','scenario_runtime.py')
    module.release=release
    module.ScenarioError=ScenarioError
    module.RELEASE_PATH=REPORT/'release.json'
    module.FINAL_METRICS_SHA256=METRICS_SHA
    return module


def capabilities():
    r,snapshots,_=release()
    def outside(s):return any(s['features'][k]!='' and not r['bounds'][k][0]<=float(s['features'][k])<=r['bounds'][k][1] for k in NUMERIC)
    ordered=sorted(snapshots.values(),key=lambda s:(outside(s),-s['displayHistory'][-1]['units'],s['baseSnapshotId']))
    return {'contractVersion':'demand-scenarios-1.0.0','status':'AVAILABLE','supportedChanges':engine().CHANGES,
            **engine().identity(r),'historyEnd':'2026-10','forecastMonth':'2026-11','stockTrainingMax':r['bounds']['stock_vendible_al_corte_unidades'][1],
            'snapshots':[{**{k:s[k] for k in ('baseSnapshotId','productId','locationId','targetMonth','productName','locationName')},
                          'previousMonthUnits':s['displayHistory'][-1]['units'],'historyMonthly':s['displayHistory']} for s in ordered]}


def snapshot_view(sid):
    view=engine().snapshot_view(sid)
    view['displayHistory']=engine().get_snapshot(sid)['displayHistory']
    return view


def preview(payload):
    result=engine().preview(payload)
    result['assumptions'][-1]='Dataset 4.0.0: historial sintético cerrado hasta octubre de 2026. Noviembre no tiene target conocido. Métricas finales guardadas, sin reevaluación al consultar.'
    return result
