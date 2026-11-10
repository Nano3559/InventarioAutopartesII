"""R30: baseline y LR REFERENCE, sin capacidad de activación o entrenamiento.

No carga tablas de targets. Solo admite los bytes del LR auditado, contrastados
con huellas independientes. El resultado es una emisión puntual, no métricas.
"""
from copy import deepcopy
import csv
import hashlib
from importlib.metadata import version
import io
import json
import math
from pathlib import Path
import threading
import uuid

from demand_runtime import V1_BINARY_SHA256
from lifecycle_registry import bind_service, digest
from session_trace import utc_now
from simulator_inputs import FEATURE_NAMES, HERE, MAX_UI_QUANTITY, InputError, parse_month, validate_quantity
from ui_runtime import model_info

# Referencias independientes: snapshots protegidos T10/T19 y experimento congelado.
_LR_PATH = HERE / "models/linear_regression_candidate.joblib"
_LR_BINARY_SHA256 = "55c7f1e152b485fc75150b506da541897948e4920aaabe95248aa433ff9dcbb8"
_EXPERIMENTS_PATH = HERE / "reports/experiments.csv"
_EXPERIMENTS_SHA256 = "1db9f324731f3c06fd16d2058e496e59a0c0df91ce888962b8644d6c876726a8"
LR_EXPERIMENT_ID = "EXP-LINEARREGRESSION-20261109T033229156232Z"
LR_VERSION = "LR-REFERENCE-" + LR_EXPERIMENT_ID
BASELINE_RULE_SHA256 = digest(dict(rule="prediction=ventas_mes_anterior", version="LAG1-1"))


def lr_metadata():
    return dict(name="LinearRegression", version=LR_VERSION, role="REFERENCE",
                artifact_hash=_LR_BINARY_SHA256, origin="SIMULACION",
                feature_names=list(FEATURE_NAMES), trained_through="2026-03",
                experiment_id=LR_EXPERIMENT_ID, promotable=False)


def _verified_sources():
    raw = Path(_LR_PATH).read_bytes()
    registry = Path(_EXPERIMENTS_PATH).read_bytes()
    if (hashlib.sha256(raw).hexdigest() != _LR_BINARY_SHA256
            or hashlib.sha256(registry).hexdigest() != _EXPERIMENTS_SHA256):
        raise InputError("REFERENCE_NO_VERIFICADA")
    matches = [r for r in csv.DictReader(io.StringIO(registry.decode("utf-8")))
               if r["experiment_id"] == LR_EXPERIMENT_ID]
    if len(matches) != 1:
        raise InputError("REFERENCE_INCOMPATIBLE")
    record = matches[0]
    if (record["model"] != "LINEARREGRESSION" or record["train_range"] != "2025-01..2026-03"
            or record["features"].split("|") != list(FEATURE_NAMES)
            or record["target"] != "target_ventas_mes" or record["seed"] != "42"):
        raise InputError("REFERENCE_INCOMPATIBLE")
    return raw, record


def _validate_payload(payload, record):
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from ml_pipeline import TrainStandardizer
    if (not isinstance(payload, dict) or payload.get("schema") != "h4-linear-regression-1"
            or payload.get("model") != "LINEARREGRESSION"
            or payload.get("feature_names") != list(FEATURE_NAMES)
            or payload.get("target") != "target_ventas_mes"
            or payload.get("trained_through") != "2026-03"
            or payload.get("train_range") != record["train_range"]
            or payload.get("dataset_version") != record["dataset_version"]
            or payload.get("dataset_hash") != record["dataset_hash"]
            or payload.get("catalog_hash") != record["catalog_hash"] or payload.get("seed") != 42):
        raise InputError("REFERENCE_INCOMPATIBLE")
    registered = json.loads(record["parameters"])
    if (payload.get("role") not in (None, "CANDIDATE")
            or payload.get("coef") != registered.pop("coef")
            or payload.get("intercept") != registered.pop("intercept")
            or payload.get("parameters") != registered):
        raise InputError("REFERENCE_INCOMPATIBLE")
    if any(payload.get("versions", {}).get(name) != version(name)
           for name in ("numpy", "pandas", "scikit-learn", "scipy", "joblib")):
        raise InputError("REFERENCE_INCOMPATIBLE")
    scaler, model = payload.get("scaler"), payload.get("estimator")
    if (type(scaler) is not TrainStandardizer or type(model) is not LinearRegression
            or getattr(model, "n_features_in_", None) != 5
            or list(getattr(model, "feature_names_in_", ())) != list(FEATURE_NAMES)
            or list(getattr(scaler, "mean_", ())) == []
            or list(scaler.mean_.index) != list(FEATURE_NAMES)
            or list(scaler.scale_.index) != list(FEATURE_NAMES)):
        raise InputError("REFERENCE_INCOMPATIBLE")
    for key, series in (("scaler_mean", scaler.mean_), ("scaler_scale", scaler.scale_)):
        if (not np.isfinite(series.to_numpy()).all()
                or series.to_dict() != payload.get(key)
                or (key == "scaler_scale" and (series <= 0).any())):
            raise InputError("REFERENCE_INCOMPATIBLE")
    if (np.asarray(model.coef_).shape != (5,) or not np.isfinite(model.coef_).all()
            or not np.array_equal(model.coef_, payload.get("coef"))
            or not math.isfinite(float(model.intercept_)) or model.intercept_ != payload.get("intercept")
            or model.get_params() != payload.get("parameters")):
        raise InputError("REFERENCE_INCOMPATIBLE")
    return scaler, model


def _usable_prediction(raw):
    if type(raw) not in (float, int) or not math.isfinite(raw) or abs(raw) > MAX_UI_QUANTITY:
        return dict(prediction=None, raw_prediction=None, reason="SALIDA_NO_VALIDA")
    if raw < 0:
        return dict(prediction=None, raw_prediction=float(raw), reason="PREDICCION_NEGATIVA")
    return dict(prediction=float(raw), raw_prediction=float(raw), reason="")


def _check_feature_contract(features):
    if not isinstance(features, dict) or tuple(features) != FEATURE_NAMES:
        raise InputError("DATOS INCOMPLETOS")
    for name in FEATURE_NAMES[:3]:
        if features[name] is None:
            raise InputError("HISTORIAL INSUFICIENTE")
        validate_quantity(features[name])
    sine, cosine = [features[k] for k in FEATURE_NAMES[3:]]
    if (any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1 for v in (sine, cosine))
            or not any(abs(sine-math.sin(2*math.pi*m/12)) < 1e-10
                       and abs(cosine-math.cos(2*math.pi*m/12)) < 1e-10 for m in range(12))):
        raise InputError("DATOS INCOMPLETOS")


def _safe_feature_snapshot(features):
    if not isinstance(features, dict):
        return None
    result = {}
    for index, (key, value) in enumerate(features.items()):
        name = key if type(key) is str else f"INVALID_KEY_{index}"
        if value is None or type(value) in (bool, int, str) or (type(value) is float and math.isfinite(value)):
            result[name] = value
        else:
            result[name] = dict(status="INVALID_VALUE", type=type(value).__name__)
    return result


class LinearRegressionReference:
    """Objeto local de solo inferencia; no ofrece get_active_model ni promoción."""
    def __init__(self):
        self._loaded = None

    def predict(self, features):
        _check_feature_contract(features)
        raw, record = _verified_sources()  # Verificar también antes de reutilizar la carga.
        if self._loaded is None:
            import joblib
            self._loaded = _validate_payload(joblib.load(io.BytesIO(raw)), record)
        import pandas as pd
        scaler, model = self._loaded
        frame = pd.DataFrame([[features[k] for k in FEATURE_NAMES]], columns=FEATURE_NAMES)
        values = model.predict(scaler.transform(frame))
        if len(values) != 1:
            raise InputError("SALIDA_NO_VALIDA")
        return _usable_prediction(float(values[0]))


class ReferenceComparisonSession:
    """Emisiones puntuales inmutables por DemandSession y par; no cambia modelos."""
    def __init__(self, session_id, product_id, location_id):
        self.session_id = session_id
        self.pair = (product_id, location_id)
        self._lifecycle = None
        self._lr = LinearRegressionReference()
        self._records = {}
        self._lock = threading.RLock()

    def bind_lifecycle(self, binding):
        if binding.pair != self.pair:
            raise InputError("Comparación REFERENCE de otro par.")
        bind_service(self, binding)

    def export_evidence(self):
        return deepcopy(list(self._records.values()))

    def predict(self, engine, features, runtime=None, *, complete=True):
        with self._lock:
            return self._predict(engine, features, runtime, complete=complete)

    def _predict(self, engine, features, runtime, *, complete):
        state = engine.status()
        if (engine.session_id != self.session_id
                or (state["product_id"], state["location_id"]) != self.pair):
            raise InputError("Comparación REFERENCE de otra sesión o par.")
        month = state["viewing_month"]
        baseline = dict(name="Baseline lag1", version="LAG1-1", role="BASELINE", origin="SIMULACION",
                        artifact_hash=None, rule_sha256=BASELINE_RULE_SHA256, promotable=False)
        lr = lr_metadata()
        try:
            active = runtime.get_active_model() if runtime else None
            if active is not None:
                model_info(active)
                active = {k: deepcopy(active[k]) for k in
                    ("name", "version", "artifact_hash", "trained_through", "origin", "feature_names", "role") if k in active}
        except Exception:
            active = None
        rows = [dict(id="BASELINE_LAG1", model=baseline), dict(id="LR_REFERENCE", model=lr),
                dict(id="RF_V1", model=deepcopy(active))]
        captured = _safe_feature_snapshot(features)
        order = list(captured) if captured is not None else None
        input_hash = digest(dict(values=captured, order=order))
        key = digest(dict(month=month, input_hash=input_hash, active=active,
                          scenario=state["scenario"], complete=complete is True))
        if key in self._records:
            return deepcopy(self._records[key])  # Nunca reescribir una emisión ya registrada.
        reason = ""
        try:
            if state["scenario"] == "PRODUCTO NUEVO" or state["history_status"] != "COMPLETO":
                reason = "HISTORIAL INSUFICIENTE"
            elif complete is not True:
                reason = "DATOS INCOMPLETOS"
            elif month <= engine._reference.months[-1]:
                reason = "PERIODO_NO_NUEVO"
            elif engine.is_closed(month) or (month == state["open_month"] and state["pending_observed"] is not None):
                reason = "OBSERVADO_YA_CONOCIDO"
            elif not isinstance(features, dict) or tuple(features) != FEATURE_NAMES:
                reason = "DATOS INCOMPLETOS"
            else:
                for name in FEATURE_NAMES[:3]:
                    if features[name] is None:
                        reason = "HISTORIAL INSUFICIENTE"
                        break
                    validate_quantity(features[name])
                angle = 2 * math.pi * (parse_month(month)[1] - 1) / 12
                for name, expected in zip(FEATURE_NAMES[3:], (math.sin(angle), math.cos(angle))):
                    value = features[name]
                    if type(value) not in (int, float) or not math.isfinite(value) or abs(value-expected) > 1e-10:
                        reason = "DATOS INCOMPLETOS"
        except (InputError, TypeError, ValueError, OverflowError):
            reason = "DATOS INCOMPLETOS"
        if reason:
            for row in rows:
                row.update(prediction=None, raw_prediction=None, reason=reason)
        else:
            rows[0].update(_usable_prediction(features[FEATURE_NAMES[0]]))
            try:
                rows[1].update(self._lr.predict(deepcopy(features)))
            except Exception:
                rows[1].update(prediction=None, raw_prediction=None, reason="REFERENCE_NO_DISPONIBLE")
            rows[2].update(self._predict_rf(runtime, active, features))
        result = dict(schema_version="h4-reference-comparison-1", id="REF-" + uuid.uuid4().hex,
            session_id=self.session_id, product_id=self.pair[0], location_id=self.pair[1],
            month=month, issued_at=utc_now(), origin="SIMULACION", purpose="POINT_IN_TIME_REFERENCE",
            scenario=state["scenario"], features=captured, feature_order=order, features_sha256=input_hash,
            predictions=rows, negative_policy="ABSTAIN_KEEP_RAW_NO_CLIPPING",
            metrics=None, metrics_reason="Emisión puntual; no es evaluación VALIDATION/TEST ni comparación de candidatos.")
        if self._lifecycle:
            self._lifecycle.emit("REFERENCES_PREDICTED", key=result["id"], model=lr,
                state_before="REFERENCE", state_after="REFERENCE", data_sha256=result["features_sha256"],
                reason="Baseline/LR/V1 sobre una entrada puntual, sin cambios de ACTIVE o CANDIDATE.",
                result="RECORDED", reference_prediction_id=result["id"])
        self._records[key] = deepcopy(result)
        return deepcopy(result)

    def _predict_rf(self, runtime, active, features):
        if active is None:
            return dict(prediction=None, raw_prediction=None, reason="V1_NO_ACTIVE")
        binding = getattr(runtime, "_lifecycle", None)
        if binding is None or binding.session_id != self.session_id or binding.pair != self.pair:
            return dict(prediction=None, raw_prediction=None, reason="RUNTIME_SIN_CONTEXTO_VERIFICADO")
        if (active.get("role") != "ACTIVE" or active.get("version") != "V1"
                or active.get("artifact_hash") != V1_BINARY_SHA256):
            return dict(prediction=None, raw_prediction=None, reason="V1_NO_ACTIVE")
        try:
            runtime.export_references()
            output = runtime.predict(deepcopy(features))
            if runtime.get_active_model() != active:
                return dict(prediction=None, raw_prediction=None, reason="ACTIVE_CHANGED")
            if not isinstance(output, dict) or set(output) != {"prediction", "reason"}:
                raise InputError("Salida incompatible.")
            if output["prediction"] is None:
                return dict(prediction=None, raw_prediction=None, reason="ABSTENCION_V1")
            return _usable_prediction(output["prediction"])
        except Exception:
            return dict(prediction=None, raw_prediction=None, reason="V1_NO_DISPONIBLE")
