"""Explicit offline TRAIN/VALIDATION experiment. Never called by the API."""
import argparse
import csv
import json
import platform
import time
from datetime import datetime, timezone
import joblib
import numpy as np
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from .scenario_data import ROOT, BUILD, FEATURES, NUMERIC, TARGET, sha, rows, frame, verify_build, build_snapshots


def metrics(y, prediction):
    return {'mae': float(mean_absolute_error(y, prediction)),
            'rmse': float(np.sqrt(mean_squared_error(y, prediction))), 'r2': float(r2_score(y, prediction))}


def pipeline(kind):
    numeric = make_pipeline(SimpleImputer(strategy='median', add_indicator=True), StandardScaler()) if kind == 'linear' else SimpleImputer(strategy='median', add_indicator=True)
    transform = ColumnTransformer([('numeric', numeric, NUMERIC), ('category', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['categoryId'])])
    model = LinearRegression() if kind == 'linear' else RandomForestRegressor(
        n_estimators=100, criterion='absolute_error' if kind == 'forest_absolute' else 'squared_error',
        max_depth=14, min_samples_leaf=4, max_features=.9, random_state=42, n_jobs=2)
    return make_pipeline(transform, model)


def train(run_id):
    import re
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', run_id):
        raise ValueError('INVALID_RUN')
    report = ROOT / 'reports/v2/3.0.0' / run_id
    models = ROOT / 'models/v2' / run_id
    if report.exists() or models.exists():
        raise FileExistsError('Never overwrite an experiment')
    verify_build()
    train_rows, validation_rows = list(rows('TRAIN')), list(rows('VALIDATION'))
    X, V = frame(train_rows), frame(validation_rows)
    y, yv = np.array([float(r[TARGET]) for r in train_rows]), np.array([float(r[TARGET]) for r in validation_rows])
    # Each paired family has total weight one. Pairs are never split across folds.
    from collections import Counter
    counts = Counter(r['scenario_family_id'] for r in train_rows)
    weights = np.array([1 / counts[r['scenario_family_id']] for r in train_rows])
    baseline = np.array([float(r['ventas_mes_anterior']) for r in validation_rows])
    results = [{'name': 'baseline', **metrics(yv, baseline), 'seconds': 0}]
    fitted = {}
    for kind in ('linear', 'forest_squared', 'forest_absolute'):
        start = time.perf_counter()
        model = pipeline(kind)
        model.fit(X, y, **{model.steps[-1][0] + '__sample_weight': weights})
        prediction = np.maximum(0, model.predict(V))
        results.append({'name': kind, **metrics(yv, prediction), 'seconds': time.perf_counter() - start})
        fitted[kind] = model
        print(json.dumps(results[-1]), flush=True)
    winner = min(results, key=lambda r: (r['mae'], r['rmse'], results.index(r)))
    # A baseline-only winner cannot be sold as an interactive economic model.
    if winner['name'] == 'baseline':
        raise ValueError('No candidate improves the baseline; do not activate')
    selected = fitted[winner['name']]
    # Month-block expanding validation inside TRAIN, independent from VALIDATION.
    months = sorted(set(r['mes_objetivo'] for r in train_rows))
    cv = []
    for stop in (6, 9, 12):
        a = np.array([r['mes_objetivo'] in months[:stop] for r in train_rows])
        b = np.array([r['mes_objetivo'] in months[stop:stop+3] for r in train_rows])
        candidate = pipeline(winner['name'])
        candidate.fit(X.loc[a], y[a], **{candidate.steps[-1][0] + '__sample_weight': weights[a]})
        cv.append({'train_end': months[stop-1], 'validation_months': months[stop:stop+3], **metrics(y[b], np.maximum(0, candidate.predict(X.loc[b])) )})
    report.mkdir(parents=True); models.mkdir(parents=True)
    artifact = models / 'model.joblib'
    joblib.dump(selected, artifact)
    snapshots = report / 'snapshots.json'
    snapshots.write_text(json.dumps(build_snapshots(), ensure_ascii=False, allow_nan=False), encoding='utf8')
    bounds = {k: [float(X[k].min()), float(X[k].max())] for k in NUMERIC}
    predictions = np.maximum(0, selected.predict(V))
    groups = []
    for key in ('productId', 'locationId'):
        for value in sorted(set(r[key] for r in validation_rows), key=int):
            mask = np.array([r[key] == value for r in validation_rows])
            groups.append({'group': key, 'id': value, **metrics(yv[mask], predictions[mask]), 'baseline_mae': metrics(yv[mask], baseline[mask])['mae']})
    with (report / 'experiments.csv').open('x', newline='', encoding='utf8') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0])); writer.writeheader(); writer.writerows(results)
    release = {'releaseId': run_id, 'datasetVersion': '3.0.0', 'modelVersion': run_id,
        'policyVersion': 'SCENARIO_NONNEGATIVE_1', 'modelKind': winner['name'],
        'artifact': artifact.relative_to(ROOT).as_posix(), 'artifactSha256': sha(artifact),
        'snapshots': snapshots.relative_to(ROOT).as_posix(), 'snapshotsSha256': sha(snapshots),
        'datasetManifestSha256': sha(BUILD / 'manifest.json'), 'features': FEATURES,
        'bounds': bounds, 'metrics': {'partition': 'VALIDATION', 'origin': 'SYNTHETIC', **metrics(yv, predictions)},
        'baseline': metrics(yv, baseline), 'trainRows': len(X), 'validationRows': len(V),
        'trainCV': cv, 'groupMetrics': groups, 'experiments': results,
        'selectedUsing': 'VALIDATION_MAE_RMSE_SIMPLICITY', 'testScored': False,
        'origin': 'ACADEMIC_SYNTHETIC_NOT_REAL_SALES', 'seed': 42,
        'versions': {'python': platform.python_version(), 'sklearn': sklearn.__version__, 'numpy': np.__version__},
        'recordedAt': datetime.now(timezone.utc).isoformat(),
        'excluded': ['four constant candidates', 'identifiers and scenario metadata', 'target outcomes', 'FX/cost and supplier lead as unproven sales drivers'],
    }
    (report / 'release.json').write_text(json.dumps(release, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf8')
    print(json.dumps({'winner': winner, 'release': (report / 'release.json').relative_to(ROOT).as_posix(), 'releaseSha256': sha(report / 'release.json')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--run-id', required=True)
    train(parser.parse_args().run_id)
