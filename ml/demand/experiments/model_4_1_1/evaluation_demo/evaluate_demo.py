"""Prepare, emit, and score the fixed historical DEMO cohort in separate processes."""

import argparse
import hashlib
import io
import itertools
import json
import platform
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from threadpoolctl import threadpool_limits

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent / "comparator"))
from model_loader import (  # noqa: E402
    DEMAND, EXPERIMENT, EXPERIMENT_SHA256, RELEASE_PATH, RELEASE_SHA256, check_pipeline, checked_bytes,
)
from features.lag_features import DERIVED, LAGS, lag_features  # noqa: E402
from v2.scenario_data import FEATURES, NUMERIC, frame  # noqa: E402

BUILD = DEMAND / "data/repuestopro_v2/4.0.0/calendar-20261116-01"
MONTHS = ["2026-08", "2026-09", "2026-10"]
STORES = [5, 6, 7]
ID = "scenario_id"
PAIR = ["productId", "locationId"]
TARGET = "target_ventas_mes"
METHODS = ("4.0.0", "4.1.1 D", "Lag1")
MATCH = "family-DEMO-52-7-2026-08-BASE"
EXPECTED_TEST_MATCHES = ["family-TEST-27-5-2026-08-BASE", "family-TEST-27-5-2026-08-COST_ONLY"]
CONTAINERS = {
    "dataset_supervisado.csv": "b6535038e4be2d1308ce82fcc1581aa90e38df27994aeb83a1313657f13aa476",
    "base_mensual.csv": "becbf279cc0c06bb708b4464d60d6627db3898ebed00d9538ded95a674d36a6c",
    "closed_history_monthly.csv": "43f42d1646168cc7791fba158276c9c4497c791d4cec8c064afd2cd01176f2be",
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2) + "\n").encode()


def sealed(name, value):
    data = encoded(value)
    path = OUT / name
    with path.open("xb") as stream:
        stream.write(data)
    path.chmod(stat.S_IREAD)
    return sha(data)


def read_sealed(name, expected):
    return json.loads(checked_bytes(OUT / name, expected))


def now():
    return datetime.now(timezone.utc).isoformat()


def sources():
    return (json.loads(checked_bytes(RELEASE_PATH, RELEASE_SHA256)),
            json.loads(checked_bytes(EXPERIMENT / "evaluation/temporal-01.json", EXPERIMENT_SHA256)))


def source_csv(name, columns):
    # Column projection is explicit. Mixed-source containers are authenticated in memory.
    return pd.read_csv(io.BytesIO(checked_bytes(BUILD / name, CONTAINERS[name])),
                       usecols=columns, keep_default_na=False, dtype=str)


def prepare():
    release, experiment = sources()
    require(release["features"] == FEATURES and release["datasetVersion"] == "4.0.0", "Unexpected schema")
    manifest = json.loads(checked_bytes(BUILD / "manifest.json", release["datasetManifestSha256"]))
    catalog_bytes = (BUILD / "catalog_reference.json").read_bytes()
    checks = {line.split()[1]: line.split()[0] for line in (BUILD / "checksums.sha256").read_text().splitlines()}
    require(sha(catalog_bytes) == checks["catalog_reference.json"], "Catalog integrity")
    catalog = json.loads(catalog_bytes)
    ids = sorted(catalog["included_product_ids"])
    require(len(ids) == 56 and sorted(row["id"] for row in catalog["locations"]) == STORES, "Unexpected catalog")
    columns = [ID, *PAIR, "mes_objetivo", "realization_id", "scenario_family_id",
               "feature_cutoff_at", "history_snapshot_id", "quality_status", *FEATURES]
    table = source_csv("dataset_supervisado.csv", columns)
    cohort = table[table.realization_id.eq("DEMO") & table[ID].str.endswith("-BASE")
                   & table.mes_objetivo.isin(MONTHS)].copy()
    cohort[PAIR] = cohort[PAIR].astype(int)
    cohort = cohort.sort_values(["mes_objetivo", *PAIR])
    keys = list(zip(cohort.mes_objetivo, cohort.productId, cohort.locationId))
    require(keys == list(itertools.product(MONTHS, ids, STORES)), "Expected exact 56 x 3 x 3 population")
    expected_family = ("family-DEMO-" + cohort.productId.astype(str) + "-"
                       + cohort.locationId.astype(str) + "-" + cohort.mes_objetivo)
    require((cohort[ID] == expected_family + "-BASE").all()
            and (cohort.scenario_family_id == expected_family).all()
            and (cohort.history_snapshot_id == expected_family).all()
            and (cohort.feature_cutoff_at == cohort.mes_objetivo + "-01T00:00:00-04:00").all()
            and cohort.quality_status.eq("ELIGIBLE_SYNTHETIC").all(), "Unexpected cohort identity or cutoff")
    # The previous audit recorded the exact input/label collision. Reconfirm only its X projection here.
    columns_numeric = [k for k in FEATURES if k != "categoryId"]
    all_inputs = table.set_index(ID)
    recorded_match = all_inputs.loc[[MATCH, *EXPECTED_TEST_MATCHES], FEATURES].to_dict("records")
    projections = frame(recorded_match)
    require(projections.iloc[0].equals(projections.iloc[1]) and projections.iloc[0].equals(projections.iloc[2]),
            "Expected previously audited input collision")

    history = source_csv("closed_history_monthly.csv", [ID, *PAIR, "mes", "available_at", "mes_completo",
                                                        "source_snapshot_id", "unidades_vendidas_brutas"])
    history = history[history[ID].isin(cohort[ID])]
    merged = history.merge(cohort[[ID, *PAIR, "mes_objetivo", "feature_cutoff_at", "history_snapshot_id", *LAGS]],
                           on=ID, validate="many_to_one", suffixes=("_source", "_target"))
    require(len(merged) == 1512 and not merged.duplicated([ID, "mes"]).any()
            and merged.groupby(ID).size().eq(3).all(), "Missing or repeated history")
    for col in PAIR:
        require(merged[f"{col}_source"].astype(int).eq(merged[f"{col}_target"]).all(), "History pair mismatch")
    available = pd.to_datetime(merged.available_at, utc=True)
    month_ends = pd.to_datetime((pd.PeriodIndex(merged.mes, freq="M") + 1).astype(str)
                                + "-01T00:00:00-04:00", utc=True)
    require((available >= month_ends).all() and (available <= pd.to_datetime(merged.feature_cutoff_at, utc=True)).all()
            and merged.mes_completo.eq("True").all() and merged.source_snapshot_id.eq(merged.history_snapshot_id).all(),
            "Unavailable closed history")
    for delta, feature in zip((3, 2, 1), LAGS):
        expected = (pd.PeriodIndex(merged.mes_objetivo, freq="M") - delta).astype(str)
        matching = merged.loc[merged.mes == expected]
        require(len(matching) == 504 and matching[feature].astype(float).eq(matching.unidades_vendidas_brutas.astype(float)).all(),
                f"Wrong closed lag: {feature}")

    temporal = {}
    for name in ("price_plan_events.csv", "opening_stock_snapshot.csv", "open_order_plan.csv",
                 "pending_shipment_plan.csv", "logistics_policy.csv"):
        events = pd.read_csv(io.BytesIO(checked_bytes(BUILD / name, checks[name])),
                             usecols=[ID, *PAIR, "available_at"], dtype=str)
        events = events[events[ID].isin(cohort[ID])].merge(cohort[[ID, *PAIR, "feature_cutoff_at"]],
                                                           on=ID, validate="many_to_one", suffixes=("_source", "_target"))
        require((pd.to_datetime(events.available_at, utc=True) <= pd.to_datetime(events.feature_cutoff_at, utc=True)).all()
                and all(events[f"{p}_source"].astype(int).eq(events[f"{p}_target"]).all() for p in PAIR),
                f"Unavailable or incompatible plan: {name}")
        temporal[name] = len(events)
    require(temporal["opening_stock_snapshot.csv"] == temporal["logistics_policy.csv"] == 504
            and temporal["price_plan_events.csv"] == 504, "Missing BASE stock, logistics or price")
    starter = cohort[[ID, *PAIR, "mes_objetivo", "feature_cutoff_at", *FEATURES]].to_dict("records")
    require(all(r[feature] != "" for r in starter for feature in LAGS), "Lag missing")
    numeric = frame(starter)
    require(all(numeric[k].dropna().between(lo, hi).all() for k, (lo, hi) in release["bounds"].items())
            and set(release["bounds"]) == set(columns_numeric), "Unexpected BASE eligibility")
    ordered = cohort[ID].tolist()
    high_products = [int(i) for i in experiment["folds"][-1]["highProducts"]]
    manifest_out = {"createdAt": now(), "datasetVersion": release["datasetVersion"], "build": manifest["build_id"],
                    "datasetManifestSha256": release["datasetManifestSha256"], "officialReleaseSha256": RELEASE_SHA256,
                    "experimentRecordSha256": EXPERIMENT_SHA256, "months": MONTHS, "rows": len(ordered),
                    "inclusion": {"realization": "DEMO", "suffix": "-BASE", "stores": STORES, "products": ids},
                    "canonicalOrder": ["mes_objetivo asc", "productId asc (int)", "locationId asc (int)"],
                    "rowIds": ordered, "rowIdsSha256": sha(encoded(ordered)), "inputFields": FEATURES,
                    "sensitivityExclusion": MATCH, "previousAuditTestMatch": EXPECTED_TEST_MATCHES,
                    "previousAuditMatchIncludesLabel": True, "closedHistoryRowsVerified": len(merged),
                    "cutoffEventsChecked": temporal, "highVariabilityProductIds": high_products,
                    "highVariabilitySource": "temporal-01 last-fold TRAIN prefixes, 75th-percentile threshold",
                    "inputSha256": sealed("inputs_without_outcomes.json", starter)}
    manifest_sha = sealed("cohort_manifest.json", manifest_out)
    print("cohort_manifest.json", manifest_sha)


def predict(manifest_sha):
    # This stage opens only sealed inputs, model manifests, feature source and artifacts.
    # In particular it never calls load_models(), which reads snapshots with displayHistory.
    manifest = read_sealed("cohort_manifest.json", manifest_sha)
    inputs = read_sealed("inputs_without_outcomes.json", manifest["inputSha256"])
    require(all(set(row) == {ID, *PAIR, "mes_objetivo", "feature_cutoff_at", *FEATURES} for row in inputs)
            and [row[ID] for row in inputs] == manifest["rowIds"], "Input allowlist or IDs changed")
    release, experiment = sources()
    versions = {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                "numpy": np.__version__, "pandas": pd.__version__, "joblib": joblib.__version__}
    require(versions == experiment["versions"] and sklearn.__version__ == release["versions"]["sklearn"]
            and versions["python"].split(".")[:2] == release["versions"]["python"].split(".")[:2],
            "Incompatible libraries")
    checked_bytes(EXPERIMENT / "features/lag_features.py", experiment["codeSha256"]["features"])
    official = joblib.load(io.BytesIO(checked_bytes(DEMAND / release["artifact"], release["artifactSha256"])))
    candidate = experiment["artifact"]
    bundle = joblib.load(io.BytesIO(checked_bytes(EXPERIMENT / candidate["file"], candidate["sha256"])))
    extensions = FEATURES + DERIVED
    require(release["modelVersion"] == "calendar-model-20261116-01" and release["features"] == FEATURES
            and experiment["winner"] == bundle["variant"] == "D" and bundle["featureOrder"] == extensions
            and bundle["status"] == "EXPERIMENTAL_NOT_ACTIVE", "Model identity or order mismatch")
    params = {**experiment["protocol"]["forest"], "random_state": experiment["protocol"]["seed"]}
    check_pipeline(official, FEATURES, params)
    check_pipeline(bundle["pipeline"], extensions, {**params, **experiment["protocol"]["regularization"]})
    base = frame(inputs)
    expanded = lag_features(base)
    require(np.isfinite(base[NUMERIC].dropna().to_numpy()).all(), "Nonfinite input")
    eligible = np.ones(len(inputs), dtype=bool)
    for key, (low, high) in release["bounds"].items():
        eligible &= (base[key].isna() | base[key].between(low, high)).to_numpy()
    values = {}
    with threadpool_limits(limits=2):
        for name, pipeline, features in [(METHODS[0], official, FEATURES), (METHODS[1], bundle["pipeline"], extensions)]:
            values[name] = np.full(len(inputs), np.nan)
            if eligible.any():
                values[name][eligible] = np.maximum(0, pipeline.predict(expanded.loc[eligible, features]))
                require(np.isfinite(values[name][eligible]).all(), f"Nonfinite estimate: {name}")
    values["Lag1"] = base[LAGS[-1]].to_numpy()
    rows = []
    for i, row in enumerate(inputs):
        emitted = {}
        for name in METHODS:
            value = values[name][i]
            emitted[name] = {"forecastUnits": float(value) if np.isfinite(value) else None,
                             "abstentionReason": None if np.isfinite(value) else "OUTSIDE_TRAINING_RANGE"}
        rows.append({ID: row[ID], "methods": emitted})
    prediction_sha = sealed("predictions.json", {
        "createdAt": now(), "cohortManifestSha256": manifest_sha, "inputSha256": manifest["inputSha256"],
        "eligibility": "Both forests share the 4.0.0 gate; Lag1 requires verified nonnegative t-1",
        "versions": versions,
        "models": {METHODS[0]: {"id": release["modelVersion"], "sha256": release["artifactSha256"]},
                   METHODS[1]: {"id": "4.1.1-temporal-01-D", "sha256": candidate["sha256"]},
                   "Lag1": {"id": "last-closed-month-t-minus-1", "sha256": None}},
        "rows": rows})
    print("predictions.json", prediction_sha)


def metric(actual, prediction):
    if len(actual) == 0:
        return dict(mae=None, rmse=None, r2=None, signedError=None)
    residual = prediction - actual
    denominator = np.sum((actual - actual.mean()) ** 2)
    return dict(mae=float(np.mean(np.abs(residual))), rmse=float(np.sqrt(np.mean(residual ** 2))),
                r2=float(1 - np.sum(residual ** 2) / denominator) if denominator else None,
                signedError=float(np.mean(residual)))


def summarize(table):
    common = table.dropna(subset=list(METHODS))
    actual = common["observed"].to_numpy()
    results = {}
    for name in METHODS:
        count = int(table[name].notna().sum())
        results[name] = {**metric(actual, common[name].to_numpy()), "emitted": count,
                         "abstained": len(table) - count, "coverage": count / len(table)}
    changes = {}
    for name, reference in [(METHODS[1], METHODS[0]), (METHODS[0], "Lag1"), (METHODS[1], "Lag1")]:
        changes[f"{name} vs {reference}"] = {
            k: {"signedChange": results[name][k] - results[reference][k],
                "absoluteDifference": abs(results[name][k] - results[reference][k]),
                "relativeChangePercent": 100 * (results[name][k] / results[reference][k] - 1)
                if results[reference][k] else None}
            for k in ("mae", "rmse") if results[name][k] is not None}
    return {"total": len(table), "paired": len(common), "methods": results, "changes": changes}


def score(manifest_sha, predictions_sha):
    manifest = read_sealed("cohort_manifest.json", manifest_sha)
    inputs = read_sealed("inputs_without_outcomes.json", manifest["inputSha256"])
    predictions = read_sealed("predictions.json", predictions_sha)
    require(predictions["cohortManifestSha256"] == manifest_sha and predictions["inputSha256"] == manifest["inputSha256"]
            and [row[ID] for row in predictions["rows"]] == manifest["rowIds"], "Emissions do not match sealed cohort")
    # First label projection; occurs only after verifying sealed predictions.
    selected = source_csv("base_mensual.csv", [ID, *PAIR, "mes_objetivo", TARGET, "outcome_complete", "outcome_available_at"])
    selected = selected[selected[ID].isin(manifest["rowIds"])].set_index(ID, verify_integrity=True)
    require(len(selected) == 504 and selected.loc[MATCH, TARGET] == "0", "Unexpected labels")
    rows = []
    for source, forecast in zip(inputs, predictions["rows"]):
        row_id = source[ID]
        label = selected.loc[row_id]
        closed = (pd.Period(source["mes_objetivo"], freq="M") + 1).strftime("%Y-%m") + "-01T00:00:00-04:00"
        require(label.outcome_complete == "True" and label.outcome_available_at == closed
                and label.mes_objetivo == source["mes_objetivo"]
                and all(int(label[key]) == source[key] for key in PAIR), "Outcome identity or closure mismatch")
        y = int(label[TARGET])
        require(y >= 0 and row_id == forecast[ID], "Invalid label or alignment")
        zeros = sum(float(source[k]) == 0 for k in LAGS)
        rows.append({ID: row_id, **{key: source[key] for key in [*PAIR, "mes_objetivo"]}, "observed": y,
                     "lagPattern": "all_zero" if zeros == 3 else "intermittent" if zeros else "all_positive",
                     "variability": "high" if source["productId"] in manifest["highVariabilityProductIds"] else "other",
                     **{name: forecast["methods"][name]["forecastUnits"] for name in METHODS}})
    table = pd.DataFrame(rows)
    sensitivity = table[table[ID] != manifest["sensitivityExclusion"]]
    require(len(sensitivity) == 503, "Wrong sensitivity mask")
    result = {"createdAt": now(), "cohortManifestSha256": manifest_sha, "predictionsSha256": predictions_sha,
              "primary": summarize(table), "sensitivity": summarize(sensitivity),
              "segments": {key: {str(label): summarize(piece) for label, piece in table.groupby(key)}
                           for key in ["mes_objetivo", "locationId", "productId", "lagPattern", "variability"]},
              "observedJoin": rows}
    print("metrics.json", sealed("metrics.json", result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="stage", required=True)
    sub.add_parser("prepare")
    sub.add_parser("predict").add_argument("manifest_sha")
    score_parser = sub.add_parser("score")
    score_parser.add_argument("manifest_sha")
    score_parser.add_argument("predictions_sha")
    args = parser.parse_args()
    if args.stage == "prepare":
        prepare()
    elif args.stage == "predict":
        predict(args.manifest_sha)
    else:
        score(args.manifest_sha, args.predictions_sha)
