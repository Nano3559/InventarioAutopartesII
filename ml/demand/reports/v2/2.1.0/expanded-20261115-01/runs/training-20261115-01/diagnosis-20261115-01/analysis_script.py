"""Post-hoc TRAIN/VALIDATION review. No fitting, TEST or policy changes."""
from pathlib import Path
import csv
import argparse
import hashlib
import json
import sys
from datetime import datetime
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "v2/contracts/preprocessing.v2_1.json").is_file())
REPO = ROOT.parents[1]
WORK = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from v2.experiments import load_xy, rotation_reference
from v2.preprocessing import DemandPreprocessor

RUN = ROOT / "reports/v2/2.1.0/expanded-20261115-01/runs/training-20261115-01"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--verify-only", action="store_true")
args = parser.parse_args()
DEST = WORK / "recomputed" if args.verify_only else RUN / "diagnosis-20261115-01"
SOURCE = ROOT / "data/repuestopro_v2/2.1.0/expanded-20261115-01"
MODEL = ROOT / "models/v2/training-20261115-01"

def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()

folders = {n: ROOT / n for n in ["data", "reports", "models", "candidates", "decisions", "lifecycle"]}
folders.update(raw=ROOT / "sources/external_raw", manifests=ROOT / "sources/manifests")
before = {k: {p.relative_to(REPO).as_posix(): sha(p) for p in d.rglob("*") if p.is_file()} for k, d in folders.items()}
before["md_paths"] = sorted(p.relative_to(REPO).as_posix() for p in (REPO / "docs").rglob("*.md"))
if not (WORK / "before.json").exists():
    (WORK / "before.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
summary = json.loads((RUN / "comparison.json").read_text(encoding="utf-8"))
assert sha(MODEL / "candidate.joblib") == summary["artifact_sha256"]

with patch.object(DemandPreprocessor, "fit", side_effect=AssertionError("No fit")), \
     patch.object(LinearRegression, "fit", side_effect=AssertionError("No fit")), \
     patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("No fit")), \
     patch.object(StandardScaler, "fit", side_effect=AssertionError("No fit")):
    T, ty = load_xy("TRAIN")
    V, vy = load_xy("VALIDATION")
    assert T.index.equals(ty.index) and V.index.equals(vy.index)
    pipeline = joblib.load(MODEL / "candidate.joblib")
    prep = pipeline.named_steps["preprocessing"]
    forest = pipeline.named_steps["model"]
    state_before = prep.to_state()
    tv = prep.transform(V)
    tt = prep.transform(T)
    pred = np.maximum(pipeline.predict(V), 0)
    assert prep.to_state() == state_before
    rotation = rotation_reference(T, ty)

    frame = pd.DataFrame(index=V.index)
    frame["observed"] = vy
    frame["baseline"] = V["ventas_mes_anterior"]
    frame["candidate"] = pred
    frame["baseline_abs_error"] = abs(frame["observed"] - frame["baseline"])
    frame["candidate_abs_error"] = abs(frame["observed"] - frame["candidate"])
    frame["error_difference"] = frame["candidate_abs_error"] - frame["baseline_abs_error"]
    frame["signed_error"] = frame["candidate"] - frame["observed"]
    frame["rotation_train"] = [rotation[k[:2]] for k in V.index]
    train_rates = ty.groupby(level=[0, 1]).apply(lambda y: float((y > 0).mean()))
    train_means = ty.groupby(level=[0, 1]).mean()
    frame["train_positive_rate"] = [train_rates[k[:2]] for k in V.index]
    frame["train_mean_units"] = [train_means[k[:2]] for k in V.index]
    frame["three_lags_zero"] = (V[["ventas_mes_anterior", "ventas_hace_2_meses", "ventas_hace_3_meses"]] == 0).all(axis=1)
    for name in ["ventas_mes_anterior", "ventas_hace_2_meses", "ventas_hace_3_meses", "cobertura_modalidad_mes_anterior", "dias_sin_stock_mes_anterior", "cobertura_stock_mes_anterior"]:
        frame[name] = V[name]

    # Event information is retrospective diagnosis only, never model input.
    frame["fulfilled_wholesale_units_posthoc"] = 0
    frame["known_wholesale_requested_units_at_cutoff"] = 0
    frame["late_known_wholesale_requested_units_posthoc"] = 0
    frame["fulfilled_retail_units_posthoc"] = 0
    order_rows = 0
    with (SOURCE / "orders.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not "2026-04" <= row["mes"] <= "2026-06":
                continue
            key = (int(row["productId"]), int(row["locationId"]), row["mes"])
            assert key in frame.index
            order_rows += 1
            if row["mode"] == "POR_MAYOR":
                frame.at[key, "fulfilled_wholesale_units_posthoc"] += int(row["fulfilled_units"])
                cutoff = datetime.fromisoformat(row["mes"] + "-01T00:00:00-04:00")
                known = datetime.fromisoformat(row["known_at"])
                column = "known_wholesale_requested_units_at_cutoff" if known <= cutoff else "late_known_wholesale_requested_units_posthoc"
                frame.at[key, column] += int(row["requested_units"])
            else:
                assert row["mode"] == "POR_MENOR"
                frame.at[key, "fulfilled_retail_units_posthoc"] += int(row["fulfilled_units"])
    assert (frame["fulfilled_wholesale_units_posthoc"] + frame["fulfilled_retail_units_posthoc"] == vy).all()

    # Each tree predicts its frozen leaf mean. No inference that simple means
    # over all TRAIN members equal bootstrap-weighted tree values.
    leaves_val = np.column_stack([tree.apply(tv) for tree in forest.estimators_])
    leaves_train = np.column_stack([tree.apply(tt) for tree in forest.estimators_])
    tree_means = np.column_stack([tree.tree_.value[leaves_val[:, i], 0, 0] for i, tree in enumerate(forest.estimators_)])
    np.testing.assert_allclose(tree_means.mean(axis=1), pred, rtol=1e-12, atol=1e-12)
    frame["positive_leaf_fraction"] = (tree_means > 0).mean(axis=1)
    frame["min_tree_leaf_prediction"] = tree_means.min(axis=1)
    frame["max_tree_leaf_prediction"] = tree_means.max(axis=1)
    mixed_shares = []
    leaf_mass_positive = []
    for j in range(len(V)):
        shares = []
        means = []
        for i in range(len(forest.estimators_)):
            peers = ty.to_numpy()[leaves_train[:, i] == leaves_val[j, i]]
            shares.append(bool(np.any(peers == 0) and np.any(peers > 0)))
            means.append(float((peers > 0).mean()))
        mixed_shares.append(float(np.mean(shares)))
        leaf_mass_positive.append(float(np.mean(means)))
    frame["mixed_zero_positive_train_leaf_fraction"] = mixed_shares
    frame["unweighted_train_peers_positive_share"] = leaf_mass_positive

    def describe(rows):
        if len(rows) == 0:
            return {"rows": 0}
        return dict(rows=len(rows), observed_units=int(rows["observed"].sum()),
                    mean_observed=float(rows["observed"].mean()), mean_prediction=float(rows["candidate"].mean()),
                    median_observed=float(rows["observed"].median()), median_prediction=float(rows["candidate"].median()),
                    baseline_mae=float(rows["baseline_abs_error"].mean()), candidate_mae=float(rows["candidate_abs_error"].mean()),
                    error_difference_sum=float(rows["error_difference"].sum()), signed_bias=float(rows["signed_error"].mean()),
                    zero_target_rows=int((rows["observed"] == 0).sum()), positive_prediction_rows=int((rows["candidate"] > 0).sum()),
                    all_three_lags_zero_rows=int(rows["three_lags_zero"].sum()),
                    mean_positive_leaf_fraction=float(rows["positive_leaf_fraction"].mean()),
                    mean_mixed_train_leaf_fraction=float(rows["mixed_zero_positive_train_leaf_fraction"].mean()))

    cohorts = {name: describe(group) for name, group in frame.groupby("rotation_train")}
    cohorts.update(zero_observed=describe(frame[frame.observed == 0]),
                   positive_observed=describe(frame[frame.observed > 0]),
                   three_lags_zero=describe(frame[frame.three_lags_zero]),
                   three_lags_zero_and_zero_observed=describe(frame[frame.three_lags_zero & (frame.observed == 0)]),
                   wholesale_fulfilled=describe(frame[frame.fulfilled_wholesale_units_posthoc > 0]),
                   no_wholesale_fulfilled=describe(frame[frame.fulfilled_wholesale_units_posthoc == 0]),
                   known_wholesale_at_cutoff=describe(frame[frame.known_wholesale_requested_units_at_cutoff > 0]),
                   unknown_or_partial_mode=describe(frame[V.proporcion_por_mayor_mes_anterior.isna() | V.cobertura_modalidad_mes_anterior.isna() | (V.cobertura_modalidad_mes_anterior < 1)]))
    cohorts["partial_mode_coverage_only"] = describe(frame[V.cobertura_modalidad_mes_anterior < 1])
    cohorts["missing_mode_share"] = describe(frame[V.proporcion_por_mayor_mes_anterior.isna()])
    cohorts["missing_mode_share"]["all_have_zero_lag1"] = bool((V.loc[V.proporcion_por_mayor_mes_anterior.isna(), "ventas_mes_anterior"] == 0).all())
    products = []
    for product, rows in frame.groupby(level="productId"):
        item = {"productId": int(product), **describe(rows),
                "rotation_groups": sorted(rows.rotation_train.unique()),
                "known_order_months": int((rows.known_wholesale_requested_units_at_cutoff > 0).sum()),
                "wholesale_months": int((rows.fulfilled_wholesale_units_posthoc > 0).sum())}
        products.append(item)
    products.sort(key=lambda x: x["candidate_mae"] - x["baseline_mae"], reverse=True)
    stores = {str(s): describe(rows) for s, rows in frame.groupby(level="locationId")}
    months = {str(m): describe(rows) for m, rows in frame.groupby(level="mes_objetivo")}
    train_reference = {}
    for name in sorted(set(rotation.values())):
        keys = [k for k in T.index if rotation[k[:2]] == name]
        labels = ty.loc[keys]
        train_reference[name] = dict(rows=len(labels), mean_units=float(labels.mean()), positive_rate=float((labels > 0).mean()))
    # Permutation is not performed. Frozen impurity importances are descriptive.
    importances = dict(zip(prep.get_feature_names_out().tolist(), forest.feature_importances_.tolist()))
    outer = [r for r in summary["records"] if r["fold_id"] == "OUTER"]
    winner = next(r for r in outer if r["candidate"]["candidate_id"] == summary["selection"]["candidate_id"])
    baseline = next(r for r in outer if r["candidate"]["model"] == "baseline")
    np.testing.assert_allclose(frame.candidate_abs_error.mean(), winner["score"]["mae"], rtol=0, atol=1e-12)
    np.testing.assert_allclose(frame.baseline_abs_error.mean(), baseline["score"]["mae"], rtol=0, atol=1e-12)
    assert sum(p["rows"] for p in products) == 504
    assert sum(p["candidate_mae"] > p["baseline_mae"] + 1e-9 for p in products) == 17
    assert frame.index.is_unique and len(frame) == 504

result = dict(status="POSTHOC_DIAGNOSIS_NOT_NEW_SELECTION", test_loaded=False, fit_calls=0,
              dataset_modified=False, input_artifact_sha256=summary["artifact_sha256"],
              months=["2026-04", "2026-06"], selected_raw_features=state_before["state"]["columns"],
              cohorts=cohorts, products=products, stores=stores, months_detail=months,
              train_rotation_reference=train_reference,
              impurity_importances_descriptive_only=importances,
              order_rows_reconciled=order_rows,
              limitations=["Post-hoc descriptive diagnosis on already-used VALIDATION, not new independent evidence.",
                           "No significance, causal price/exchange claim, policy tuning or TEST selection.",
                           "Leaf peer proportions are unweighted full-TRAIN descriptions, not bootstrap training weights.",
                           "Current observed fulfillment and late-known orders are diagnosis only, never prediction inputs."])
DEST.mkdir(exist_ok=False)
(DEST / "error_diagnosis.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
frame.reset_index().to_csv(DEST / "validation_row_errors.csv", index=False, lineterminator="\n")
frame.loc[frame.index.get_level_values("productId").isin([20, 43, 3, 32])].reset_index().to_csv(DEST / "product_examples.csv", index=False, lineterminator="\n")
print(json.dumps({"cohorts": cohorts, "products_most_worsened": products[:4], "months": months,
                  "top_importances": sorted(importances.items(), key=lambda x: x[1], reverse=True)[:6]}))
