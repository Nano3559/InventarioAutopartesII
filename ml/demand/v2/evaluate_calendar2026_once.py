"""One final evaluation of calendar 4.0.0, with exclusive one-shot guards."""
import argparse
import csv
from datetime import datetime, timezone
import json
import joblib
import numpy as np
from .calendar2026 import BUILD, REPORT, SPLITS, verify, write_json
from .scenario_data import ROOT, NUMERIC, TARGET, frame, sha
from .train_scenarios import metrics


def evaluate(expected_sha):
    path=REPORT/'release.json'
    if sha(path)!=expected_sha:raise ValueError('Release changed before final evaluation')
    release=json.loads(path.read_text(encoding='utf8'))
    if sha(ROOT/release['artifact'])!=release['artifactSha256']:raise ValueError('Artifact changed')
    verify()
    # Exclusive claim first. Any interrupted attempt remains visible and is not retried.
    write_json(REPORT/'final-test-attempt.json',{'releaseSha256':expected_sha,'startedAt':datetime.now(timezone.utc).isoformat(),'retryForbidden':True})
    write_json(REPORT/'selection.json',{'releaseSha256':expected_sha,'artifactSha256':release['artifactSha256'],'selectedUsing':'VALIDATION_MAE_RMSE_SIMPLICITY','fixedBeforeTest':True,'forecastOutcomeAbsent':True})
    with (BUILD/'dataset_supervisado.csv').open(encoding='utf8',newline='') as f:
        data=[r for r in csv.DictReader(f) if r['realization_id']=='TEST']
    if len(data)!=1008 or sorted({r['mes_objetivo'] for r in data})!=['2026-08','2026-09','2026-10']:raise ValueError('Wrong final cohort')
    model=joblib.load(ROOT/release['artifact']); X=frame(data); y=np.array([float(r[TARGET]) for r in data])
    predicted=np.maximum(0,model.predict(X)); baseline=np.array([float(r['ventas_mes_anterior']) for r in data])
    covered=np.ones(len(data),dtype=bool)
    for key in NUMERIC:
        lo,hi=release['bounds'][key];covered &= X[key].isna()|X[key].between(lo,hi)
    groups=[]
    for key in ('productId','locationId'):
        for value in sorted({r[key] for r in data},key=int):
            mask=np.array([r[key]==value for r in data])
            groups.append({'group':key,'id':value,'model':metrics(y[mask],predicted[mask]),'baseline':metrics(y[mask],baseline[mask])})
    report={'datasetVersion':'4.0.0','partition':'FINAL_TEST_SAVED','origin':'SYNTHETIC','rows':len(data),'months':SPLITS['TEST'],
            'artifactSha256':release['artifactSha256'],'releaseSha256':expected_sha,'evaluatedOnce':True,'selectedUsingTest':False,
            'model':metrics(y,predicted),'baseline':metrics(y,baseline),'groups':groups,
            'servedPolicyCoverage':{'coveredRows':int(sum(covered)),'abstainedRows':int(sum(~covered)),'totalRows':len(data)},
            'forecastMonth':'2026-11','forecastTargetKnown':False}
    write_json(REPORT/'test-evaluation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='groups'}),flush=True)
    print(json.dumps({'testEvaluationSha256':sha(REPORT/'test-evaluation.json')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--expected-release-sha',required=True)
    evaluate(parser.parse_args().expected_release_sha)
