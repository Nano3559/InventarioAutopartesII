"""Offline experiment with a fixed development-data allowlist."""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import sys

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

EXPERIMENT = Path(__file__).resolve().parents[1]
DEMAND = EXPERIMENT.parents[1]
sys.path.insert(0, str(DEMAND))
from v2.scenario_data import FEATURES, NUMERIC, TARGET, frame  # noqa: E402

BUILD = DEMAND / "data/repuestopro_v2/4.0.0/calendar-20261116-01"
RELEASE = DEMAND / "reports/v2/4.0.0/calendar-model-20261116-01/release.json"
OFFICIAL_ARTIFACT = DEMAND / "models/v2/calendar-model-20261116-01/model.joblib"
LAGS = ["ventas_hace_3_meses", "ventas_hace_2_meses", "ventas_mes_anterior"]
PERIODS = {"TRAIN": ["2025-02", "2026-04"], "VALIDATION": ["2026-05", "2026-07"]}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verified(path, expected):
    data = path.read_bytes()
    if digest(data) != expected:
        raise ValueError(f"SHA256 mismatch: {path.name}")
    return data


def development_rows(csv_bytes):
    rows = {name: [] for name in PERIODS}
    seen = set()
    families = {}
    with io.TextIOWrapper(io.BytesIO(csv_bytes), encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            part = row["realization_id"]
            if part not in PERIODS:
                continue
            month = row["mes_objetivo"]
            cutoff = month + "-01T00:00:00-04:00"
            if not PERIODS[part][0] <= month <= PERIODS[part][1] or row["feature_cutoff_at"] != cutoff:
                raise ValueError("Unexpected development month or feature cutoff")
            scope = (part, month, row["productId"], row["locationId"])
            family = row["scenario_family_id"]
            if not family or families.setdefault(family, scope) != scope or row["scenario_id"] in seen:
                raise ValueError("Duplicate scenario or family shared across scopes")
            seen.add(row["scenario_id"])
            if row["quality_status"] != "ELIGIBLE_SYNTHETIC":
                raise ValueError("Unexpected row quality")
            rows[part].append(row)
    for part, expected in (("TRAIN", 5040), ("VALIDATION", 1008)):
        if len(rows[part]) != expected:
            raise ValueError(f"Unexpected {part} row count")
    return rows["TRAIN"], rows["VALIDATION"]


def input_values(rows):
    x = frame(rows)
    y = np.array([float(row[TARGET]) for row in rows])
    if not np.isfinite(y).all() or (y < 0).any() or np.isinf(x[NUMERIC]).any().any():
        raise ValueError("Invalid development values")
    lags = x[LAGS].to_numpy()
    if not np.isfinite(lags).all() or (lags < 0).any():
        raise ValueError("Invalid lags")
    return x, y


def groups(x):
    positives = (x[LAGS] > 0).sum(axis=1).to_numpy()
    return {
        "zero_lags": positives == 0,
        "intermittent": (positives > 0) & (positives < 3),
        "all_lags_positive": positives == 3,
    }


def build_pipeline(estimator):
    transform = ColumnTransformer([
        ("numeric", SimpleImputer(strategy="median", add_indicator=True), NUMERIC),
        ("category", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["categoryId"]),
    ])
    return make_pipeline(transform, estimator)


def fit_candidates(x, y, weights, config):
    seed = config["seed"]
    hist_params = {"random_state": seed, **config["histGradientBoosting"]}
    forest = build_pipeline(RandomForestRegressor(random_state=seed, **config["randomForest"]))
    hist = build_pipeline(HistGradientBoostingRegressor(**hist_params))
    forest.fit(x, y, randomforestregressor__sample_weight=weights)
    hist.fit(x, y, histgradientboostingregressor__sample_weight=weights)

    sparse = ~groups(x)["all_lags_positive"]
    occurrence = y > 0
    if not occurrence[sparse].any() or occurrence[sparse].all():
        raise ValueError("Hurdle requires both zero and positive TRAIN targets")
    positive = sparse & occurrence
    probability = build_pipeline(HistGradientBoostingClassifier(**hist_params))
    magnitude = build_pipeline(HistGradientBoostingRegressor(**hist_params))
    probability.fit(x.loc[sparse], occurrence[sparse], histgradientboostingclassifier__sample_weight=weights[sparse])
    magnitude.fit(x.loc[positive], y[positive], histgradientboostingregressor__sample_weight=weights[positive])
    return {
        "forest_alt": {"strategy": "single", "estimators": {"regressor": forest}},
        "hist": {"strategy": "single", "estimators": {"regressor": hist}},
        "hurdle": {"strategy": "hurdle", "estimators": {"regressor": hist, "probability": probability, "magnitude": magnitude}},
        "hybrid": {"strategy": "hist_lag1", "histWeight": config["hybridHistWeight"], "estimators": {"regressor": hist}},
    }


def predict_candidate(bundle, x):
    models = bundle["estimators"]
    values = np.maximum(models["regressor"].predict(x), 0)
    if bundle["strategy"] == "hurdle":
        sparse = ~groups(x)["all_lags_positive"]
        if sparse.any():
            selected = x.loc[sparse]
            values[sparse] = models["probability"].predict_proba(selected)[:, 1] * np.maximum(models["magnitude"].predict(selected), 0)
    elif bundle["strategy"] == "hist_lag1":
        weight = bundle["histWeight"]
        values = weight * values + (1 - weight) * x[LAGS[-1]].to_numpy()
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite candidate forecast")
    return values


def metric(y, pred):
    n = len(y)
    return {
        "n": n, "mae": float(mean_absolute_error(y, pred)) if n else None,
        "rmse": float(np.sqrt(mean_squared_error(y, pred))) if n else None,
        "r2": float(r2_score(y, pred)) if n > 1 and np.ptp(y) > 0 else None,
        "signedError": float(np.mean(pred - y)) if n else None,
    }


def evaluation(y, forecasts, selection, segments, reference):
    n = int(selection.sum())
    results = {}
    for name, prediction in forecasts.items():
        results[name] = {
            **metric(y[selection], prediction[selection]),
            "total": len(y), "coverage": n / len(y), "abstentions": len(y) - n,
            "maeDeltaVsOfficial": float(np.mean(np.abs(prediction[selection] - y[selection])
                                               - np.abs(reference[selection] - y[selection]))) if n else None,
            "groups": {
                kind: {label: metric(y[selection & mask], prediction[selection & mask])
                       for label, mask in masks.items()}
                for kind, masks in segments.items()
            },
        }
    return results


def dimensions(rows, x):
    output = {"lag_pattern": groups(x)}
    for key in ("productId", "locationId", "mes_objetivo"):
        values = np.array([row[key] for row in rows])
        output[key] = {label: values == label for label in sorted(set(values))}
    return output


def main(run_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,48}", run_id):
        raise ValueError("Invalid experimental run ID")
    config_bytes = (EXPERIMENT / "configs/protocolo.json").read_bytes()
    config = json.loads(config_bytes)
    split = json.loads(verified(BUILD / "split_manifest.json", config["splitSha256"]))
    for name in PERIODS:
        if split["splits"][name] != PERIODS[name] or config[name.lower()] != PERIODS[name]:
            raise ValueError("Development split differs from fixed protocol")
    release = json.loads(verified(RELEASE, config["releaseSha256"]))
    if release["features"] != FEATURES or release["artifactSha256"] != config["artifactSha256"]:
        raise ValueError("Unexpected official provenance or feature order")
    official_bytes = verified(OFFICIAL_ARTIFACT, config["artifactSha256"])
    train, validation = development_rows(verified(BUILD / "dataset_supervisado.csv", config["datasetSha256"]))
    x, y = input_values(train)
    v, actual = input_values(validation)
    family_counts = Counter(row["scenario_family_id"] for row in train)
    weights = np.array([1 / family_counts[row["scenario_family_id"]] for row in train])
    directory = EXPERIMENT / "candidates" / run_id
    result_path = EXPERIMENT / "evaluation" / f"{run_id}.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    if result_path.exists():
        raise FileExistsError(result_path)
    directory.mkdir(parents=True)
    with threadpool_limits(limits=2):
        reference = np.maximum(joblib.load(io.BytesIO(official_bytes)).predict(v), 0)
        if not np.isfinite(reference).all():
            raise ValueError("Nonfinite official estimate")
        bundles = fit_candidates(x, y, weights, config)
        forecasts = {"official_4_0_0": reference, "lag1": v[LAGS[-1]].to_numpy(), "ma3": v[LAGS].mean(axis=1).to_numpy()}
        forecasts.update({name: predict_candidate(bundle, v) for name, bundle in bundles.items()})
    in_range = np.ones(len(v), dtype=bool)
    for name, (low, high) in release["bounds"].items():
        in_range &= (v[name].isna() | v[name].between(low, high)).to_numpy()
    segments = dimensions(validation, v)
    artifacts = {}
    for name, bundle in bundles.items():
        artifact = directory / f"{name}.joblib"
        joblib.dump(bundle, artifact, compress=3)
        artifacts[name] = {"file": artifact.relative_to(EXPERIMENT).as_posix(), "sha256": digest(artifact.read_bytes())}
    result = {
        "runId": run_id, "status": "EXPERIMENTAL_NOT_ACTIVE",
        "generatedAt": datetime.now(timezone.utc).isoformat(), "protocol": config, "protocolSha256": digest(config_bytes),
        "runnerSha256": digest(Path(__file__).read_bytes()),
        "versions": {"python": platform.python_version(), "sklearn": sklearn.__version__, "numpy": np.__version__,
                     "pandas": pd.__version__, "joblib": joblib.__version__},
        "features": FEATURES, "target": TARGET,
        "trainRows": len(train), "validationRows": len(validation), "trainFamilies": len(family_counts),
        "validationFamilies": len({row["scenario_family_id"] for row in validation}),
        "artifacts": artifacts,
        "estimator_all_validation": evaluation(actual, forecasts, np.ones(len(v), dtype=bool), segments, reference),
        "common_official_domain": evaluation(actual, forecasts, in_range, segments, reference),
    }
    with result_path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, allow_nan=False, indent=2)
    print(result_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    main(parser.parse_args().run_id)
