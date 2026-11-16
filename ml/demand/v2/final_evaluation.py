"""One final TEST event for a preaccepted artifact. No fitting or selection."""
import csv
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd

from v2.alternatives import AlternativeForecaster
from v2.experiments import TARGET, KEYS, align_targets, score_predictions, group_scores
from v2.preprocessing import DemandPreprocessor, load_feature_partition, read_context, validate_frame, validate_cohort
from v2.structure import ROOT, sha256_file
from v2.validate_build import canonical_hash

VERSION = "final-test-2.1-1"


def write_new(path, document):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(document, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def destination(root):
    return Path(root) / "reports/v2/2.1.0/expanded-20261115-01/final_test"


def read_selection(root):
    path = Path(root) / "v2/contracts/selection.v2_1.json"
    selection = json.loads(path.read_text(encoding="utf-8"))
    if selection["evaluation_version"] != VERSION or selection["accepted_candidate"] != "absolute_forest-d4":
        raise ValueError("Different accepted selection")
    if selection["user_accepted"] is not True or selection["test_authorization"] != "ONE_FINAL_EVALUATION_NO_RETRAINING":
        raise PermissionError("No final-test authorization")
    if selection["prediction_policy"] != dict(version="NONNEGATIVE_V1", nonfinite="REJECT_ALL_NO_SUBSET", negative="CLIP_ZERO", rounding="NONE"):
        raise ValueError("Policy changed")
    if selection["evaluation_implementation_sha256"] != sha256_file(Path(__file__)):
        raise ValueError("Final evaluation implementation changed")
    for name, digest in selection["input_hashes"].items():
        file = (Path(root) / name).resolve()
        if not file.is_relative_to(Path(root).resolve()) or sha256_file(file) != digest:
            raise ValueError("Frozen input changed: " + name)
    return selection, sha256_file(path)


def load_accepted_model(root, selection):
    from hashlib import sha256
    path = Path(root) / selection["artifact"]
    data = path.read_bytes()
    if sha256(data).hexdigest() != selection["artifact_sha256"]:
        raise ValueError("Artifact changed")
    model = joblib.load(BytesIO(data))  # Deserialize exactly the verified bytes.
    if type(model) is not AlternativeForecaster or model.spec != selection["model_spec"]:
        raise ValueError("Not the accepted forecaster")
    state = model.preprocessor_.to_state()
    if state["sha256"] != selection["preprocessing_state_sha256"] or state["state"]["train_window"] != ["2025-01", "2026-03"]:
        raise ValueError("Preprocessing changed or refitted")
    if state["state"]["fit_rows"] != 2520 or state["state"]["columns"] != selection["features"]:
        raise ValueError("Different preprocessing cohort or features")
    if model.train_end_ != "2026-03" or any(k[2] > "2026-03" for k in model.history_):
        raise ValueError("Model includes later training history")
    if model.model_.get_params() != selection["regressor_parameters"]:
        raise ValueError("Regressor parameters changed")
    return model


def reserve(root, selection, selection_sha256):
    dest = destination(root)
    dest.mkdir(parents=True, exist_ok=False)  # One shared guard for the whole build.
    write_new(dest / "evaluation_started.json", dict(status="CONSUMED_BEFORE_TEST_ACCESS",
        selection_id=selection["selection_id"], selection_sha256=selection_sha256,
        artifact_sha256=selection["artifact_sha256"], started_at=datetime.now(timezone.utc).isoformat(),
        retry_policy="DO_NOT_DELETE_OR_RETRY_AFTER_FAILURE_OR_CRASH"))
    return dest


def load_test_once(root):
    X = load_feature_partition("TEST", root=root)
    spec, plan, fields, source, _, manifest = read_context(root)
    _, months = validate_frame(X, fields)
    if set(months) != {"2026-07", "2026-08", "2026-09"} or len(X) != 504:
        raise ValueError("Unexpected TEST partition")
    validate_cohort(X, months, manifest)
    keys, values = [], []
    with (source / "dataset_supervisado.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if not "2026-07" <= row["mes_objetivo"] <= "2026-09":
                continue
            if not row[TARGET].isdigit():
                raise ValueError("Invalid target")
            keys.append((int(row["productId"]), int(row["locationId"]), row["mes_objetivo"]))
            values.append(int(row[TARGET]))
    if sha256_file(source / "dataset_supervisado.csv") != spec["csv_sha256"]:
        raise ValueError("CSV changed during read")
    y = pd.Series(values, index=pd.MultiIndex.from_tuples(keys, names=KEYS), name=TARGET)
    return X, align_targets(X, y)


def evaluate_reserved(root, selection, model, dest, selection_sha256):
    before = model.preprocessor_.to_state()
    X, y = load_test_once(root)
    write_new(dest / "prediction_started.json", dict(model_predict_calls=1, features_rows=len(X),
        test_labels_loaded=True, at=datetime.now(timezone.utc).isoformat()))
    raw = np.asarray(model.predict(X), dtype=float)  # The only TEST predict call.
    if raw.ndim != 1 or len(raw) != len(y) or not np.isfinite(raw).all():
        raise ValueError("Incomplete or invalid predictions: keep failed event consumed")
    pred = np.maximum(raw, 0)
    baseline = X.ventas_mes_anterior.to_numpy(dtype=float)
    score = score_predictions(y, raw)
    base_score = score_predictions(y, baseline)
    if score["status"] != "OK" or base_score["status"] != "OK":
        raise ValueError("Invalid final metrics")
    groups = group_scores(X, y, raw, model.rotation_)
    baseline_groups = group_scores(X, y, baseline, model.rotation_)
    months = []
    for month in ["2026-07", "2026-08", "2026-09"]:
        indices = np.flatnonzero(X.mes_objetivo.to_numpy() == month)
        months.append(dict(month=month, model=score_predictions(y.iloc[indices], raw[indices]), baseline=score_predictions(y.iloc[indices], baseline[indices])))
    difference = pred - y.to_numpy()
    after = model.preprocessor_.to_state()
    if before != after or sha256_file(Path(root) / selection["artifact"]) != selection["artifact_sha256"]:
        raise ValueError("Frozen model or preprocessing mutated")
    result = dict(status="FINAL_TEST_EVALUATED_ONCE_NOT_ACTIVE", selection_id=selection["selection_id"],
        selection_sha256=selection_sha256, artifact_sha256=selection["artifact_sha256"],
        dataset_version="2.1.0", build_id="expanded-20261115-01", origin="SYNTHETIC",
        period=["2026-07", "2026-09"], rows=len(X), model_fit_calls=0, preprocessing_fit_calls=0,
        model_predict_calls=1, test_loader_calls=1, model_metrics=score, baseline_metrics=base_score,
        mae_reduction_vs_baseline_percent=100 * (1 - score["mae"] / base_score["mae"]) if base_score["mae"] else None,
        by_month=months, groups=groups, baseline_groups=baseline_groups,
        tail=dict(p95_absolute_error=float(np.quantile(np.abs(difference), .95)),
                  max_absolute_error=float(np.max(np.abs(difference))),
                  abs_error_gt20=int((np.abs(difference) > 20).sum()), abs_error_gt40=int((np.abs(difference) > 40).sum())),
        totals=dict(observed=int(y.sum()), predicted=float(pred.sum()), signed_bias=float(difference.mean()),
                    aggregate_difference_percent=100 * (float(pred.sum()) / int(y.sum()) - 1) if y.sum() else None),
        preprocessing_state_unchanged=True, active_model_changed=False, commercial_accuracy_certified=False,
        selection_changed_after_test=False, validation_reused_for_selection=True,
        interpretation="Held-out temporal block of this same synthetic generator, not real-company validation or unseen mechanisms.",
        horizon="ONE_MONTH_ROLLING_CLOSED_HISTORY_NO_REFIT_NOT_THREE_MONTHS_FROM_JUNE",
        completed_at=datetime.now(timezone.utc).isoformat())
    write_new(dest / "result.json", result)
    with (dest / "predictions.csv").open("x", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow([*KEYS, TARGET, "prediction_raw", "prediction_policy", "baseline_lag1", "absolute_error", "baseline_absolute_error"])
        for i, key in enumerate(X.index):
            writer.writerow([*key, int(y.iloc[i]), float(raw[i]), float(pred[i]), float(baseline[i]), float(abs(difference[i])), float(abs(baseline[i]-y.iloc[i]))])
    write_new(dest / "verification.json", dict(artifact_sha256_after=sha256_file(Path(root) / selection["artifact"]),
        preprocessing_state_sha256_before=before["sha256"], preprocessing_state_sha256_after=after["sha256"],
        row_keys_sha256=canonical_hash([list(k) for k in X.index]), test_labels_sha256=canonical_hash(y.tolist()),
        model_fit_calls=0, model_predict_calls=1, result_sha256=sha256_file(dest / "result.json")))
    return result


def evaluate(root=ROOT):
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    root = Path(root).resolve()
    if destination(root).exists():
        raise FileExistsError("TEST already reserved or evaluated for this build. No retry.")
    selection, digest = read_selection(root)
    dest = None
    with patch.object(AlternativeForecaster, "fit", side_effect=AssertionError("Final TEST forbids fit")), \
         patch.object(DemandPreprocessor, "fit", side_effect=AssertionError("Final TEST forbids fit")), \
         patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("Final TEST forbids fit")), \
         patch.object(StandardScaler, "fit", side_effect=AssertionError("Final TEST forbids fit")):
        model = load_accepted_model(root, selection)
        dest = reserve(root, selection, digest)
        try:
            write_new(dest / "selection_frozen.json", selection)
            return dest, evaluate_reserved(root, selection, model, dest, digest)
        except BaseException as exc:
            write_new(dest / "failure.json", dict(status="FAILED_TEST_EVENT_CONSUMED_NO_AUTO_RETRY", type=type(exc).__name__, reason=str(exc)))
            raise
