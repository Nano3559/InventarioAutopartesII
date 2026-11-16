"""Paired review from frozen VALIDATION reports only. No fit or data loader."""
from pathlib import Path
import csv
import hashlib
import json
import math

import numpy as np

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "v2/contracts/preprocessing.v2_1.json").is_file())
REPO = ROOT.parents[1]
WORK = Path(__file__).parent
RUN = ROOT / "reports/v2/2.1.0/expanded-20261115-01/runs/alternatives-20261115-01"
DEST = RUN / "candidate-review-20261115-01"
IDS = ["lag1", "previous_squared_forest", "absolute_forest-d4", "low_median_routing"]
SEVEN = [3, 15, 17, 20, 32, 43, 50]


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


folders = {n: ROOT / n for n in ["data", "models", "reports", "candidates", "decisions", "lifecycle"]}
folders.update(raw=ROOT / "sources/external_raw", manifests=ROOT / "sources/manifests")
before = {n: {p.relative_to(REPO).as_posix(): sha(p) for p in d.rglob("*") if p.is_file()} for n, d in folders.items()}
before["md_paths"] = sorted(p.relative_to(REPO).as_posix() for p in (REPO / "docs").rglob("*.md"))
(WORK / "before.json").write_text(json.dumps(before, indent=2), encoding="utf-8")
summary = json.loads((RUN / "comparison.json").read_text(encoding="utf-8"))
payload = json.loads((RUN / "validation_predictions.json").read_text(encoding="utf-8"))
old_diag = ROOT / "reports/v2/2.1.0/expanded-20261115-01/runs/training-20261115-01/diagnosis-20261115-01/validation_row_errors.csv"
with old_diag.open(encoding="utf-8", newline="") as f:
    context = {(int(r["productId"]), int(r["locationId"]), r["mes_objetivo"]): r for r in csv.DictReader(f)}
keys = [tuple(k) for k in payload["keys"]]
assert len(keys) == len(set(keys)) == 504 and set(keys) == set(context)
assert all("2026-04" <= k[2] <= "2026-06" for k in keys)
y = np.asarray(payload["observed"], dtype=float)
pred = {name: np.maximum(payload["predictions"][name], 0) for name in IDS}
errors = {name: np.abs(p - y) for name, p in pred.items()}
checks = []


def check(name, condition):
    assert condition, name
    checks.append(dict(name=name, passed=True))


def metrics(mask):
    results = {}
    for name in IDS:
        e = errors[name][mask]
        signed = pred[name][mask] - y[mask]
        results[name] = dict(rows=int(mask.sum()), mae=float(e.mean()), rmse=float(np.sqrt(np.mean(e ** 2))),
                             median_absolute_error=float(np.median(e)), p90=float(np.quantile(e, .9)),
                             p95=float(np.quantile(e, .95)), max_error=float(e.max()),
                             signed_bias=float(signed.mean()), observed_units=float(y[mask].sum()),
                             predicted_units=float(pred[name][mask].sum()),
                             abs_error_gt20=int((e > 20).sum()), abs_error_gt40=int((e > 40).sum()))
    return results


all_mask = np.ones(len(keys), dtype=bool)
overall = metrics(all_mask)
for name in IDS:
    frozen = next(r for r in summary["outer"] if r["spec"]["id"] == name)
    check("Frozen MAE/RMSE reproduced: " + name,
          abs(overall[name]["mae"] - frozen["score"]["mae"]) < 1e-12 and
          abs(overall[name]["rmse"] - frozen["score"]["rmse"]) < 1e-12)

products = []
for product in sorted(set(k[0] for k in keys)):
    mask = np.array([k[0] == product for k in keys])
    m = metrics(mask)
    products.append(dict(productId=product, metrics=m,
        absolute_worse_than_baseline=m["absolute_forest-d4"]["mae"] > m["lag1"]["mae"] + 1e-9,
        routing_worse_than_baseline=m["low_median_routing"]["mae"] > m["lag1"]["mae"] + 1e-9))
check("Seven outstanding products exactly reproduced", [p["productId"] for p in products if p["absolute_worse_than_baseline"]] == SEVEN)
row_details = []
for i, key in enumerate(keys):
    c = context[key]
    check_key = float(c["observed"])
    assert check_key == y[i]
    row = dict(productId=key[0], locationId=key[1], month=key[2], observed=int(y[i]),
               lag1=float(c["ventas_mes_anterior"]), lag2=float(c["ventas_hace_2_meses"]), lag3=float(c["ventas_hace_3_meses"]),
               rotation_train=c["rotation_train"],
               known_wholesale_requested_at_cutoff=int(c["known_wholesale_requested_units_at_cutoff"]),
               wholesale_fulfilled_posthoc=int(c["fulfilled_wholesale_units_posthoc"]),
               predicted={name: float(pred[name][i]) for name in IDS},
               absolute_errors={name: float(errors[name][i]) for name in IDS})
    row_details.append(row)

seven_details = []
for product in SEVEN:
    group = next(p for p in products if p["productId"] == product)
    rows = [r for r in row_details if r["productId"] == product]
    worst = max(rows, key=lambda r:r["absolute_errors"]["absolute_forest-d4"])
    stores = []
    for store in [5, 6, 7]:
        mask = np.array([k[0] == product and k[1] == store for k in keys])
        stores.append(dict(locationId=store, metrics=metrics(mask)))
    seven_details.append(dict(**group, worst_absolute_candidate_row=worst, stores=stores, rows=rows))

paired_delta = errors["absolute_forest-d4"] - errors["low_median_routing"]
paired = dict(absolute_better_rows=int((paired_delta < -1e-9).sum()), routing_better_rows=int((paired_delta > 1e-9).sum()),
              tied_rows=int((np.abs(paired_delta) <= 1e-9).sum()),
              absolute_better_products=sum(p["metrics"]["absolute_forest-d4"]["mae"] < p["metrics"]["low_median_routing"]["mae"] - 1e-9 for p in products),
              routing_better_products=sum(p["metrics"]["absolute_forest-d4"]["mae"] > p["metrics"]["low_median_routing"]["mae"] + 1e-9 for p in products))
check("Paired row outcomes exhaustive", paired["absolute_better_rows"] + paired["routing_better_rows"] + paired["tied_rows"] == 504)

# Describe tails using the same union of hard rows for both models, not
# two independently cherry-picked subsets. Thresholds are diagnostic only.
hard = (errors["absolute_forest-d4"] > 40) | (errors["low_median_routing"] > 40)
union_tail = metrics(hard)
top_tail = sorted(row_details, key=lambda r:max(r["absolute_errors"]["absolute_forest-d4"], r["absolute_errors"]["low_median_routing"]), reverse=True)[:12]
tail_squared_difference = (errors["absolute_forest-d4"] ** 2 - errors["low_median_routing"] ** 2)
tail_contribution = dict(all_extra_squared_error=float(tail_squared_difference.sum()),
                         hard_union_extra_squared_error=float(tail_squared_difference[hard].sum()),
                         hard_union_rows=int(hard.sum()), thresholds_20_40="DESCRIPTIVE_ONLY_NOT_COMMERCIAL_TOLERANCE")
by_month = {m: metrics(np.array([k[2] == m for k in keys])) for m in ["2026-04", "2026-05", "2026-06"]}
by_store = {str(s): metrics(np.array([k[1] == s for k in keys])) for s in [5, 6, 7]}
by_rotation = {g: metrics(np.array([context[k]["rotation_train"] == g for k in keys])) for g in ["HIGH", "MEDIUM", "LOW", "ZERO"]}
check("Primary recommendation MAE is better in each validation month", all(m["absolute_forest-d4"]["mae"] < m["low_median_routing"]["mae"] for m in by_month.values()))
check("Primary recommendation MAE is better in each store", all(m["absolute_forest-d4"]["mae"] < m["low_median_routing"]["mae"] for m in by_store.values()))

result = dict(status="FROZEN_VALIDATION_PAIRED_REVIEW_NOT_TESTED", new_fits=0, test_loaded=False,
               overall=overall, paired=paired, seven_products=seven_details,
               all_products=products, union_tail=union_tail, tail_contribution=tail_contribution,
               top_tail_examples=top_tail, by_month=by_month, by_store=by_store, by_rotation=by_rotation,
               checks=checks, input_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in [RUN/"comparison.json", RUN/"validation_predictions.json", old_diag]},
               limitations=["Already-reused VALIDATION only. No new independent accuracy, causality or commercial guarantee.",
                            "Seven products were chosen from previous failures: descriptive focused review, not an unbiased subgroup search.",
                            "Three observations per product-store, nine per product. No significance claims.",
                            "Thresholds 20/40 and target-defined tails diagnose errors, never determine deployment routing."])
DEST.mkdir(exist_ok=False)
(DEST/"paired_review.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
with (DEST/"seven_products.csv").open("x",encoding="utf-8",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=["productId","baseline_mae","previous_mae","absolute_mae","routing_mae","absolute_max_error","routing_max_error"])
    writer.writeheader()
    for p in seven_details:
        m=p["metrics"]
        writer.writerow(dict(productId=p["productId"],baseline_mae=m["lag1"]["mae"],previous_mae=m["previous_squared_forest"]["mae"],
                             absolute_mae=m["absolute_forest-d4"]["mae"],routing_mae=m["low_median_routing"]["mae"],
                             absolute_max_error=m["absolute_forest-d4"]["max_error"],routing_max_error=m["low_median_routing"]["max_error"]))
print(json.dumps(dict(overall=overall,paired=paired,tail=tail_contribution,
                      seven=[dict(productId=p["productId"],mae={n:p["metrics"][n]["mae"] for n in IDS},worst=p["worst_absolute_candidate_row"]) for p in seven_details],
                      top_tail=top_tail[:4])))
