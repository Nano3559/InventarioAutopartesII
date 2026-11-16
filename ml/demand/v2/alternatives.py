"""Exploratory alternatives. TRAIN temporal folds, reused VALIDATION, never TEST."""
import copy
import json
from pathlib import Path
import time

import joblib
import numpy as np

from v2.experiments import align_targets, load_xy, score_predictions, rotation_reference, group_scores
from v2.preprocessing import DemandPreprocessor, read_context, validate_frame, validate_cohort
from v2.structure import ROOT, sha256_file, token
from v2.validate_build import month_offset, canonical_hash

VERSION = "alternatives-2.1-1"
GROUP = "expanded_with_exchange"
DERIVED = ["positive_months_last3", "zero_streak_last3", "recent_unit_change", "recent_mean_last3"]


def specifications():
    options = [dict(id=k, family=k) for k in ["lag1", "median3", "weighted_recent"]]
    options += [dict(id=f"tsb-a{a}-b{b}", family="tsb", alpha=a, beta=b) for a in [.1, .3] for b in [.1, .3]]
    for family in ["absolute_forest", "derived_forest", "residual_forest"]:
        options += [dict(id=f"{family}-d{d}", family=family, max_depth=d, min_samples_leaf=5) for d in [4, 8]]
    options.append(dict(id="low_median_routing", family="low_median_routing", max_depth=4, min_samples_leaf=2))
    return options


def derived_lags(X):
    lags = X[["ventas_mes_anterior", "ventas_hace_2_meses", "ventas_hace_3_meses"]].to_numpy(dtype=float)
    if not np.isfinite(lags).all() or np.any(lags < 0):
        raise ValueError("Invalid lag history")
    streak = (lags[:, 0] == 0).astype(float)
    streak += ((lags[:, :2] == 0).all(axis=1)).astype(float)
    streak += ((lags == 0).all(axis=1)).astype(float)
    return np.column_stack([(lags > 0).sum(axis=1), streak, lags[:, 0] - lags[:, 1], lags.mean(axis=1)])


def tsb(values, alpha, beta):
    if not values:
        raise ValueError("No history")
    p = float(values[0] > 0)
    size = float(values[0])
    for value in values[1:]:
        p += beta * (float(value > 0) - p)
        if value > 0:
            size = float(value) if size == 0 else size + alpha * (value - size)
    return p * size


class AlternativeForecaster:
    def __init__(self, spec):
        self.spec = copy.deepcopy(spec)

    def fit(self, X, y):
        if hasattr(self, "fitted_"):
            raise ValueError("Use fresh object per fold")
        if self.spec not in specifications():
            raise ValueError("Unregistered option")
        y = align_targets(X, y)
        contract, _, fields, _, _, manifest = read_context(ROOT)
        _, months = validate_frame(X, fields)
        if [min(months), max(months)] not in contract["fit_windows"]:
            raise ValueError("Fit outside TRAIN windows")
        validate_cohort(X, months, manifest)
        self.train_end_ = max(months)
        self.rotation_ = rotation_reference(X, y)
        self.history_ = {}
        first = min(months)
        for key, row in X[X.mes_objetivo == first].iterrows():
            pair = key[:2]
            for n in [3, 2, 1]:
                name = "ventas_mes_anterior" if n == 1 else f"ventas_hace_{n}_meses"
                self.history_[(*pair, month_offset(first, -n))] = int(row[name])
        for key, value in y.items():
            self.history_[key] = int(value)
        family = self.spec["family"]
        self.model_ = None
        self.preprocessor_ = None
        if family.endswith("forest") or family == "low_median_routing":
            from sklearn.ensemble import RandomForestRegressor
            self.preprocessor_ = DemandPreprocessor(GROUP, "random_forest").fit(X, y)
            matrix = self.preprocessor_.transform(X)
            if family == "derived_forest":
                matrix = np.column_stack([matrix, derived_lags(X)])
            target = y.to_numpy(dtype=float)
            if family == "residual_forest":
                target = target - X.ventas_mes_anterior.to_numpy(dtype=float)
            self.model_ = RandomForestRegressor(n_estimators=200, criterion="absolute_error" if family == "absolute_forest" else "squared_error",
                max_depth=self.spec["max_depth"], min_samples_leaf=self.spec["min_samples_leaf"],
                max_features=1.0, bootstrap=True, random_state=42, n_jobs=1).fit(matrix, target)
        self.fitted_ = True
        return self

    def predict(self, X):
        if not hasattr(self, "fitted_"):
            raise ValueError("Not fitted")
        _, _, fields, _, _, _ = read_context(ROOT)
        validate_frame(X, fields)
        if X.index.has_duplicates or any(m <= self.train_end_ for m in X.mes_objetivo):
            raise ValueError("Predict only later months with unique keys")
        family = self.spec["family"]
        lags = X[["ventas_mes_anterior", "ventas_hace_2_meses", "ventas_hace_3_meses"]].to_numpy(dtype=float)
        if family == "lag1":
            return lags[:, 0]
        if family == "median3":
            return np.median(lags, axis=1)
        if family == "weighted_recent":
            return lags @ np.array([.6, .3, .1])
        if family == "tsb":
            history = dict(self.history_)
            for key, row in X.iterrows():
                for n in [3, 2, 1]:
                    name = "ventas_mes_anterior" if n == 1 else f"ventas_hace_{n}_meses"
                    obs = (*key[:2], month_offset(key[2], -n))
                    value = int(row[name])
                    if obs in history and history[obs] != value:
                        raise ValueError("Conflicting closed-month history")
                    history[obs] = value
            predictions = []
            for key in X.index:
                past = sorted((m, v) for (p, s, m), v in history.items() if (p, s) == key[:2] and m < key[2])
                if not past or past[-1][0] != month_offset(key[2], -1) or any(month_offset(a[0], 1) != b[0] for a, b in zip(past, past[1:])):
                    raise ValueError("Incomplete history")
                predictions.append(tsb([v for _, v in past], self.spec["alpha"], self.spec["beta"]))
            return np.array(predictions)
        matrix = self.preprocessor_.transform(X)
        if family == "derived_forest":
            matrix = np.column_stack([matrix, derived_lags(X)])
        pred = self.model_.predict(matrix)
        if family == "residual_forest":
            pred = pred + lags[:, 0]
        if family == "low_median_routing":
            low = np.array([self.rotation_.get(k[:2]) in ("LOW", "ZERO") for k in X.index])
            pred = np.where(low, np.median(lags, axis=1), pred)
        return pred  # Clipping only in predeclared scoring/output policy.


def execute(run_id, contract_path):
    token(run_id)
    contract_path = Path(contract_path)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["run_id"] != run_id or contract["authorized_scope"] != "ONE_RUN_TRAIN_VALIDATION_ONLY":
        raise PermissionError("No scoped authorization")
    if contract["options"] != specifications() or contract["implementation_sha256"] != sha256_file(Path(__file__)):
        raise ValueError("Frozen options or implementation changed")
    for path, digest in contract["input_hashes"].items():
        if sha256_file(ROOT / path) != digest:
            raise ValueError("Input changed: " + path)
    report = ROOT / "reports/v2/2.1.0/expanded-20261115-01/runs" / run_id
    models = ROOT / "models/v2" / run_id
    if report.exists() or models.exists():
        raise FileExistsError("Run already reserved")
    report.mkdir(parents=True, exist_ok=False)
    models.mkdir(parents=True, exist_ok=False)
    (report / "frozen_plan.json").write_bytes(contract_path.read_bytes())
    base_plan = json.loads((ROOT / "v2/contracts/experiments.v2_1.json").read_text(encoding="utf-8"))
    fold_data = {f["id"]: (load_xy("TRAIN", fold_id=f["id"]), load_xy("VALIDATION", fold_id=f["id"])) for f in base_plan["temporal_validation"]["folds"]}
    records = []
    for spec in contract["options"]:
        for fold in base_plan["temporal_validation"]["folds"]:
            (T, y), (V, z) = fold_data[fold["id"]]
            start = time.perf_counter()
            forecaster = AlternativeForecaster(spec).fit(T, y)
            pred = forecaster.predict(V)
            score = score_predictions(z, pred)
            if score["status"] != "OK":
                raise ValueError("Candidate lacks full coverage")
            records.append(dict(spec=spec, fold=fold["id"], score=score, seconds=time.perf_counter()-start,
                                train_window=[T.mes_objetivo.min(), T.mes_objetivo.max()]))
            print(json.dumps({"id": spec["id"], "fold": fold["id"], "mae": score["mae"]}), flush=True)
    # Choose configuration per family exclusively inside TRAIN.
    selected = []
    for family in dict.fromkeys(o["family"] for o in contract["options"]):
        pool = []
        for spec in contract["options"]:
            if spec["family"] != family:
                continue
            results = [r for r in records if r["spec"] == spec]
            if len(results) != 3:
                raise ValueError("Incomplete CV")
            pool.append((float(np.mean([r["score"]["mae"] for r in results])), spec))
        best = min(x[0] for x in pool)
        tied = [s for mae, s in pool if mae <= best + 1e-9]
        selected.append(sorted(tied, key=lambda s: (s.get("max_depth", 0), s["id"]))[0])
    T, y = load_xy("TRAIN")
    V, z = load_xy("VALIDATION")
    rotation = rotation_reference(T, y)
    outer = []
    predictions = {}
    for spec in selected:
        start = time.perf_counter()
        forecaster = AlternativeForecaster(spec).fit(T, y)
        pred = forecaster.predict(V)
        score = score_predictions(z, pred)
        if score["status"] != "OK":
            raise ValueError("Invalid outer predictions")
        path = models / (spec["id"] + ".joblib")
        joblib.dump(forecaster, path)
        restored = joblib.load(path)
        np.testing.assert_array_equal(pred, restored.predict(V))
        outer.append(dict(spec=spec, score=score, groups=group_scores(V, z, pred, rotation),
                          artifact_sha256=sha256_file(path), artifact=str(path.relative_to(ROOT)),
                          seconds=time.perf_counter()-start, artifact_reload_exact=True))
        predictions[spec["id"]] = pred.tolist()
    original = joblib.load(ROOT / contract["previous_model"])
    pred = original.predict(V)
    previous = dict(spec=dict(id="previous_squared_forest", family="previous_frozen_reference"),
                    score=score_predictions(z, pred), groups=group_scores(V, z, pred, rotation), new_fit=False)
    outer.append(previous)
    predictions["previous_squared_forest"] = pred.tolist()
    summary = dict(version=VERSION, status="EXPLORATORY_COMPARISON_NO_PROMOTION", run_id=run_id,
                   dataset_origin="SYNTHETIC", test_loaded=False, active_model_changed=False,
                   reused_validation=True, fit_option_calls=len(records)+len(selected),
                   actual_forest_fits=sum(r["spec"]["family"].endswith("forest") or r["spec"]["family"]=="low_median_routing" for r in records+outer),
                   cv=records, outer=outer, plan_sha256=sha256_file(contract_path),
                   best_validation_mae_option=min(outer, key=lambda r:r["score"]["mae"])["spec"]["id"])
    (report / "comparison.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    (report / "validation_predictions.json").write_text(json.dumps(dict(keys=[list(k) for k in V.index], observed=z.tolist(), predictions=predictions), allow_nan=False), encoding="utf-8")
    (models / "manifest.json").write_text(json.dumps(dict(run_id=run_id, active=False, test_evaluated=False,
        plan_sha256=sha256_file(contract_path), implementation_sha256=sha256_file(Path(__file__)),
        artifacts={r["spec"]["id"]:r["artifact_sha256"] for r in outer if "artifact_sha256" in r}), indent=2), encoding="utf-8")
    return report, summary
