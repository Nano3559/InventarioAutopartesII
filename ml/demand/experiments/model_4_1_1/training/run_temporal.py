"""Four predeclared RF configurations on expanding folds within TRAIN."""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import sys
from time import perf_counter

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from threadpoolctl import threadpool_limits

EXPERIMENT = Path(__file__).resolve().parents[1]
DEMAND = EXPERIMENT.parents[1]
sys.path[:0] = [str(EXPERIMENT), str(DEMAND)]
from features.lag_features import DERIVED, LAGS, lag_features  # noqa: E402
from v2.scenario_data import FEATURES, NUMERIC, TARGET, frame  # noqa: E402

BUILD = DEMAND / "data/repuestopro_v2/4.0.0/calendar-20261116-01"
PERIOD = ["2025-02", "2026-04"]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verified_csv(name, checksums):
    data = (BUILD / name).read_bytes()
    if digest(data) != checksums[name]:
        raise ValueError(f"Fingerprint mismatch: {name}")
    return csv.DictReader(io.StringIO(data.decode("utf-8")))


def offset(month, delta):
    year, number = map(int, month.split("-"))
    index = year * 12 + number - 1 + delta
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def cutoff(month):
    return datetime.fromisoformat(month + "-01T00:00:00-04:00")


def same_pair(row, other):
    return all(row[key] == other[key] for key in ("productId", "locationId"))


def load_train(config):
    checksums = config["sha256"]
    split = (BUILD / "split_manifest.json").read_bytes()
    if (digest(split) != checksums["split_manifest.json"] or config["partition"] != "TRAIN"
            or config["period"] != PERIOD or json.loads(split)["splits"]["TRAIN"] != PERIOD):
        raise ValueError("Unexpected TRAIN scope")
    rows, families = {}, {}
    for row in verified_csv("dataset_supervisado.csv", checksums):
        if row["realization_id"] != "TRAIN":
            continue
        month, sid = row["mes_objetivo"], row["scenario_id"]
        scope = (month, row["productId"], row["locationId"])
        family = row["scenario_family_id"]
        if (not PERIOD[0] <= month <= PERIOD[1] or sid in rows or not family
                or row["quality_status"] != "ELIGIBLE_SYNTHETIC"
                or datetime.fromisoformat(row["feature_cutoff_at"]) != cutoff(month)
                or families.setdefault(family, scope) != scope):
            raise ValueError("Invalid TRAIN row or family")
        rows[sid] = row
    if len(rows) != 5040 or len(families) != 2520:
        raise ValueError("Unexpected TRAIN size")

    histories = defaultdict(dict)
    for history in verified_csv("closed_history_monthly.csv", checksums):
        sid = history["scenario_id"]
        if sid not in rows:
            continue
        row = rows[sid]
        month, target = history["mes"], row["mes_objetivo"]
        available = datetime.fromisoformat(history["available_at"])
        if (not same_pair(row, history) or history["source_snapshot_id"] != row["history_snapshot_id"]
                or month in histories[sid] or history["mes_completo"] != "True"
                or not cutoff(offset(month, 1)) <= available <= cutoff(target)):
            raise ValueError("Ineligible or duplicate lag observation")
        observed = int(history["unidades_vendidas_brutas"])
        if observed < 0:
            raise ValueError("Negative observed sales")
        histories[sid][month] = observed
    for sid, row in rows.items():
        months = [offset(row["mes_objetivo"], -lag) for lag in (3, 2, 1)]
        if set(histories[sid]) != set(months) or any(
            float(row[key]) != histories[sid][month] for key, month in zip(LAGS, months)
        ):
            raise ValueError("Published lags differ from source observations")

    label_dates = {}
    for outcome in verified_csv("base_mensual.csv", checksums):
        sid = outcome["scenario_id"]
        if sid not in rows:
            continue
        row = rows[sid]
        month = row["mes_objetivo"]
        if (sid in label_dates or not same_pair(row, outcome) or outcome["mes_objetivo"] != month
                or outcome["outcome_complete"] != "True" or outcome[TARGET] != row[TARGET]):
            raise ValueError("Outcome and supervised label mismatch")
        available = datetime.fromisoformat(outcome["outcome_available_at"])
        if available < cutoff(offset(month, 1)):
            raise ValueError("Label available before closing")
        label_dates[sid] = available
    if set(label_dates) != set(rows):
        raise ValueError("Missing TRAIN outcomes")
    return list(rows.values()), label_dates


def temporal_folds(rows, label_dates, config):
    months = sorted({row["mes_objetivo"] for row in rows})
    if (months != [offset(PERIOD[0], index) for index in range(15)]
            or set(Counter(row["mes_objetivo"] for row in rows).values()) != {336}):
        raise ValueError("Insufficient contiguous TRAIN months")
    by_month = np.array([row["mes_objetivo"] for row in rows])
    seen = set()
    for size in config["fitMonths"]:
        score_months = months[size:size + config["scoreMonthsPerFold"]]
        if len(score_months) != 3 or seen.intersection(score_months):
            raise ValueError("Expected disjoint three-month score blocks")
        seen.update(score_months)
        first_cut = cutoff(score_months[0])
        fit, score = np.isin(by_month, months[:size]), np.isin(by_month, score_months)
        if any(label_dates[row["scenario_id"]] > first_cut for row, used in zip(rows, fit) if used):
            raise ValueError("Fit includes labels unavailable at first score cutoff")
        yield months[:size], score_months, fit, score


def forest(config, variant):
    chosen = config["variants"][variant]
    numeric = NUMERIC + (DERIVED if chosen["derived"] else [])
    encoder = ColumnTransformer([
        ("numeric", SimpleImputer(strategy="median", add_indicator=True), numeric),
        ("category", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["categoryId"]),
    ])
    params = {"random_state": config["seed"], **config["forest"]}
    if chosen["regularized"]:
        params.update(config["regularization"])
    return make_pipeline(encoder, RandomForestRegressor(**params))


def score(y, prediction):
    total = len(y)
    y, prediction = y[np.isfinite(prediction)], prediction[np.isfinite(prediction)]
    n = len(y)
    residual = prediction - y
    variance = float(np.sum((y - y.mean()) ** 2)) if n else 0
    return {
        "total": total, "n": n, "coverage": n / total if total else None, "abstentions": total - n,
        "mae": float(np.abs(residual).mean()) if n else None,
        "rmse": float(np.sqrt(np.square(residual).mean())) if n else None,
        "r2": 1 - float(np.square(residual).sum()) / variance if variance else None,
        "signedError": float(residual.mean()) if n else None,
    }


def subset_scores(scored):
    result = {}
    for key in ("productId", "locationId", "lag_pattern", "variability"):
        result[key] = {
            str(value): score(group["actual"].to_numpy(), group["prediction"].to_numpy())
            for value, group in scored.groupby(key)
        }
    return result


def run_fold(rows, x, y, fit, assess, config):
    xt, xv = x.loc[fit], x.loc[assess]
    fit_rows = [row for row, used in zip(rows, fit) if used]
    val_rows = [row for row, used in zip(rows, assess) if used]
    weights = family_weights(fit_rows)
    product_lags = pd.DataFrame({
        "id": [row["productId"] for row in fit_rows],
        "family": [row["scenario_family_id"] for row in fit_rows],
        "std": xt["lag3_std"].to_numpy(),
    }).drop_duplicates("family").groupby("id")["std"].median()
    high_threshold = float(product_lags.quantile(config["highVariabilityQuantile"]))
    high_products = set(product_lags[product_lags >= high_threshold].index)
    zeros = xv["lag3_zero_fraction"].to_numpy()
    labels = pd.DataFrame({
        "actual": y[assess], "productId": [r["productId"] for r in val_rows],
        "locationId": [r["locationId"] for r in val_rows],
        "lag_pattern": np.select([zeros == 1, zeros > 0], ["all_zero", "intermittent"], default="all_positive"),
        "variability": ["high" if r["productId"] in high_products else "other" for r in val_rows],
    })
    in_range = (xv[NUMERIC].isna() | ((xv[NUMERIC] >= xt[NUMERIC].min()) & (xv[NUMERIC] <= xt[NUMERIC].max()))).all(axis=1).to_numpy()
    predictions = {"lag1": xv[LAGS[-1]].to_numpy(), "ma3": xv["lag3_mean"].to_numpy()}
    times = {}
    for variant in config["variants"]:
        model = forest(config, variant)
        start = perf_counter()
        model.fit(xt, y[fit], randomforestregressor__sample_weight=weights)
        times[variant] = perf_counter() - start
        predictions[variant] = np.maximum(model.predict(xv), 0)
    records = {}
    for name, forecast in predictions.items():
        if not np.isfinite(forecast).all():
            raise ValueError(f"Nonfinite forecast: {name}")
        scored = labels.assign(prediction=forecast)
        records[name] = {
            **score(y[assess], forecast), "fitSeconds": times.get(name),
            "commonRange": score(y[assess], np.where(in_range, forecast, np.nan)),
            "groups": subset_scores(scored),
        }
    return records, labels, predictions, high_threshold, sorted(high_products)


def family_weights(rows):
    counts = Counter(row["scenario_family_id"] for row in rows)
    return np.array([1 / counts[row["scenario_family_id"]] for row in rows])


def main(run_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,48}", run_id):
        raise ValueError("Invalid run ID")
    config_bytes = (EXPERIMENT / "configs/protocolo.json").read_bytes()
    config = json.loads(config_bytes)
    rows, label_dates = load_train(config)
    x = lag_features(frame(rows))
    y = np.array([float(row[TARGET]) for row in rows])
    if not np.isfinite(y).all() or (y < 0).any() or np.isinf(x[NUMERIC].to_numpy()).any():
        raise ValueError("Invalid TRAIN values")
    windows = list(temporal_folds(rows, label_dates, config))
    if len(windows) < 3:
        raise ValueError("Not enough eligible temporal folds")
    directory = EXPERIMENT / "candidates" / run_id
    output = EXPERIMENT / "evaluation" / f"{run_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    directory.mkdir(parents=True)

    folds, pooled = [], defaultdict(list)
    with threadpool_limits(limits=2):
        for fit_months, score_months, fit, assess in windows:
            records, labels, forecasts, threshold, products = run_fold(rows, x, y, fit, assess, config)
            folds.append({"fitMonths": fit_months, "scoreMonths": score_months, "fitRows": int(fit.sum()),
                          "scoreRows": int(assess.sum()), "highThreshold": threshold, "highProducts": products,
                          "methods": records})
            print(score_months, {key: round(value["mae"], 5) for key, value in records.items()}, flush=True)
            for name, forecast in forecasts.items():
                pooled[name].append(labels.assign(prediction=forecast))
        summary = {}
        for name, pieces in pooled.items():
            actuals = pd.concat(pieces, ignore_index=True)
            values = [fold["methods"][name]["mae"] for fold in folds]
            summary[name] = {
                **score(actuals["actual"].to_numpy(), actuals["prediction"].to_numpy()),
                "meanFoldMae": float(np.mean(values)), "stdFoldMae": float(np.std(values)), "worstFoldMae": max(values),
                "foldsBetterThanA": sum(value < fold["methods"]["A"]["mae"] for value, fold in zip(values, folds)),
                "groups": subset_scores(actuals),
            }
        variants = config["variants"]
        winner = min(variants, key=lambda v: (
            summary[v]["meanFoldMae"], summary[v]["stdFoldMae"], variants[v]["derived"],
            -int(variants[v]["regularized"]), v,
        ))
        final = forest(config, winner)
        columns = FEATURES + (DERIVED if variants[winner]["derived"] else [])
        if any(available > cutoff(offset(PERIOD[1], 1)) for available in label_dates.values()):
            raise ValueError("Final TRAIN labels were not closed by the boundary")
        start = perf_counter()
        final.fit(x[columns], y, randomforestregressor__sample_weight=family_weights(rows))
        final_seconds = perf_counter() - start
    artifact = directory / "candidate.joblib"
    joblib.dump({"pipeline": final, "featureOrder": columns, "variant": winner, "status": "EXPERIMENTAL_NOT_ACTIVE"},
                artifact, compress=3)
    report = {
        "runId": run_id, "status": "EXPERIMENTAL_NOT_ACTIVE", "winner": winner,
        "recordedAt": datetime.now(timezone.utc).isoformat(), "protocol": config, "protocolSha256": digest(config_bytes),
        "codeSha256": {"runner": digest(Path(__file__).read_bytes()),
                       "features": digest((EXPERIMENT / "features/lag_features.py").read_bytes())},
        "versions": {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                     "numpy": np.__version__, "pandas": pd.__version__, "joblib": joblib.__version__},
        "trainRows": len(rows), "target": TARGET, "features": columns,
        "finalFitSeconds": final_seconds,
        "artifact": {"file": artifact.relative_to(EXPERIMENT).as_posix(), "sha256": digest(artifact.read_bytes())},
        "folds": folds, "summary": summary,
    }
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, allow_nan=False, indent=2)
    print(f"Selected experimental variant {winner}. Results: {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    main(parser.parse_args().run_id)
