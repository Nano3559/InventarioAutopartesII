"""One-shot evaluation of the already frozen 3.0 release. Not an API command."""
import csv
from datetime import datetime, timezone
import json
import numpy as np
from .scenario_data import ROOT, BUILD, NUMERIC, TARGET, canonical, sha, frame, verify_build
from .scenario_runtime import release, EXPECTED_RELEASE_SHA256
from .train_scenarios import metrics


def evaluate():
    r, _, model = release()
    verify_build()
    directory = ROOT / 'reports/v2/3.0.0' / r['releaseId']
    lock = directory / 'final-test-attempt.json'
    selection = directory / 'selection.json'
    if lock.exists() or selection.exists():
        raise FileExistsError('Do not repeat TEST or overwrite the fixed selection')
    decision = {'selection': r['releaseId'], 'releaseSha256': EXPECTED_RELEASE_SHA256,
                'artifactSha256': r['artifactSha256'], 'policyVersion': r['policyVersion'],
                'criterion': 'VALIDATION MAE, RMSE as secondary. Simpler model on exact tie.',
                'authorization': 'User delegated completion of backend and frontend H4 tasks in current request.',
                'no_claim_of_personal_team_acceptance': True,
                'fixedBeforeOpeningTest': True, 'selectedUsingTest': False,
                'recordedAt': datetime.now(timezone.utc).isoformat()}
    with selection.open('x', encoding='utf8') as f: json.dump(decision, f, indent=2)
    with lock.open('x', encoding='utf8') as f: json.dump({'selectionSha256': sha(selection), 'evaluationStartedAt': datetime.now(timezone.utc).isoformat(), 'retryForbidden': True}, f, indent=2)
    bounds = json.loads((BUILD / 'split_manifest.json').read_text())['splits']['TEST']
    data = []
    with (BUILD / 'dataset_supervisado.csv').open(encoding='utf8', newline='') as f:
        for row in csv.DictReader(f):
            if row['realization_id'] == 'TEST' and bounds[0] <= row['mes_objetivo'] <= bounds[1]: data.append(row)
    X = frame(data); y = np.array([float(row[TARGET]) for row in data])
    prediction = np.maximum(0, model.predict(X))
    baseline = np.array([float(row['ventas_mes_anterior']) for row in data])
    covered = np.ones(len(data), dtype=bool)
    for k in NUMERIC:
        lo, hi = r['bounds'][k]; covered &= X[k].isna() | X[k].between(lo, hi)
    from collections import Counter
    families = Counter(row['scenario_family_id'] for row in data)
    if len(data) != 1008 or any(n != 2 for n in families.values()): raise ValueError('Wrong sealed TEST cohort')
    groups = []
    for k in ('productId', 'locationId'):
        for value in sorted(set(row[k] for row in data), key=int):
            mask = np.array([row[k] == value for row in data])
            groups.append({'group':k,'id':value,'model':metrics(y[mask],prediction[mask]),'baseline':metrics(y[mask],baseline[mask])})
    report = {'origin':'SYNTHETIC', 'partition':'FINAL_TEST_SAVED', 'datasetVersion':'3.0.0',
              'releaseSha256':EXPECTED_RELEASE_SHA256, 'artifactSha256':r['artifactSha256'],
              'selectionSha256':sha(selection), 'rows':len(data), 'families':len(families), 'months':bounds,
              'model':metrics(y,prediction),'baseline':metrics(y,baseline),
              'servedPolicyCoverage': {'coveredRows':int(sum(covered)), 'abstainedRows':int(sum(~covered)), 'totalRows':len(data),
                    'coveredMetrics': metrics(y[covered],prediction[covered]) if sum(covered)>1 else None},
              'groups':groups,'evaluatedOnce':True,'notUsedForRetuning':True,
              'recordedAt':datetime.now(timezone.utc).isoformat()}
    with (directory/'test-evaluation.json').open('x',encoding='utf8') as f: json.dump(report,f,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in report.items() if k!='groups'}))


if __name__ == '__main__': evaluate()
