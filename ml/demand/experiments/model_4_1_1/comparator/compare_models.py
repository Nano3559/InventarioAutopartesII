"""Compare published 4.0.0 DEMO inputs locally. No outcome joins or training."""

import argparse
import json
from math import isfinite

from feature_adapter import adapt, outside_range, select_snapshot
from model_loader import load_models


def describe(snapshot):
    keys = ("baseSnapshotId", "productId", "productName", "locationId", "locationName", "targetMonth")
    return {key: snapshot[key] for key in keys}


def comparison(snapshot, release, models):
    official, expanded, unavailable = adapt(snapshot)
    outside = outside_range(snapshot, release["bounds"])
    rows = []
    for name, model in models.items():
        prediction = None
        reason = unavailable or ("OUTSIDE_TRAINING_RANGE" if outside else None)
        status = "ABSTAINED" if reason else "OK"
        if model["pipeline"] is None:
            status, reason = "UNAVAILABLE", "ARTIFACT_NOT_PERSISTED"
        elif not reason:
            x = official if name == "4.0.0" else expanded
            value = float(model["pipeline"].predict(x[model["features"]])[0])
            if not isfinite(value):
                status, reason = "ABSTAINED", "NONFINITE_PREDICTION"
            else:
                prediction = max(0.0, value)
        rows.append({"model": name, "modelId": model["id"], "sha256": model["sha256"],
                     "status": status, "reason": reason, "forecastUnits": prediction})
    base = rows[0]["forecastUnits"]
    for row in rows:
        value = row["forecastUnits"]
        delta = None if base is None or value is None else value - base
        row["signedDifferenceUnits"] = delta
        row["absoluteDifferenceUnits"] = None if delta is None else abs(delta)
        row["differencePercent"] = None if delta is None or base == 0 else 100 * delta / base
        row["observedAbsoluteError"] = None
    return {"snapshot": describe(snapshot), "cutoffAt": snapshot["targetMonth"] + "-01T00:00:00-04:00",
            "origin": "ACADEMIC_SYNTHETIC_DEMO", "observedUnits": None, "outsideFeatures": outside,
            "models": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Listar snapshots publicados")
    parser.add_argument("--product", type=int)
    parser.add_argument("--store", type=int)
    parser.add_argument("--month")
    parser.add_argument("--snapshot")
    args = parser.parse_args()
    try:
        release, snapshots, models, versions = load_models()
        if args.list:
            result = [describe(entry) for entry in snapshots.values()]
        else:
            entry = select_snapshot(snapshots, args.month, args.product, args.store, args.snapshot)
            result = {**comparison(entry, release, models), "versions": versions}
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
