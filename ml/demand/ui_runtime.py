"""Adaptador de Ross para el runtime local de Erika. No entrena ni carga pickle."""
import hashlib
import importlib.util
import math
import re
import sys
import uuid
from copy import deepcopy
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from session_trace import append_revision, utc_now

from simulator_inputs import FEATURE_NAMES, HERE, InputError, MAX_UI_QUANTITY, SCENARIOS, parse_month, validate_quantity


ORIGIN = "SIMULACION"


def checked_number(value):
    if (type(value) not in (int, float) or abs(value) > MAX_UI_QUANTITY
            or not math.isfinite(value)):
        raise InputError("Salida numérica inválida o fuera del rango técnico de la interfaz.")
    return float(value)


@dataclass(frozen=True)
class ModelInfo:
    name: str
    version: str
    artifact_hash: str
    trained_through: str

    @property
    def label(self):
        return f"{self.name} · {self.version} · {self.artifact_hash[:8]}"


def model_info(value):
    if not isinstance(value, dict):
        raise InputError("El runtime no devolvió metadatos de modelo válidos.")
    for field in ("name", "version"):
        if not isinstance(value.get(field), str) or not 0 < len(value[field].strip()) <= 120:
            raise InputError("Nombre o versión de modelo inválidos.")
    digest = value.get("artifact_hash")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise InputError("Falta la huella SHA256 del conjunto modelo y preprocesador.")
    if value.get("origin") != ORIGIN or value.get("feature_names") != list(FEATURE_NAMES):
        raise InputError("Modelo incompatible: origen o contrato de cinco features distintos.")
    parse_month(value.get("trained_through"))
    return ModelInfo(value["name"], value["version"], digest, value["trained_through"])


def discover_runtime():
    """Única extensión autorizada: archivo del proyecto, nunca un archivo subido."""
    source = HERE / "demand_runtime.py"
    if not source.is_file():
        return None
    spec = importlib.util.spec_from_file_location("repuestopro_demand_runtime", source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    runtime = module.create_runtime()
    if not callable(getattr(runtime, "get_active_model", None)) or not callable(getattr(runtime, "predict", None)):
        raise InputError("El runtime debe ofrecer get_active_model() y predict(features).")
    return runtime


def active_info(runtime):
    if runtime is None:
        return None
    metadata = runtime.get_active_model()
    if metadata is None:
        return None
    if not isinstance(metadata, dict) or metadata.get("role", "ACTIVE") != "ACTIVE":
        raise InputError("Solo un modelo ACTIVE puede atender la inferencia.")
    return model_info(metadata)


@dataclass(frozen=True)
class Forecast:
    product_id: int
    location_id: int
    month: str
    features: tuple | None
    prediction: float | None
    baseline: float | None
    model: ModelInfo | None
    reason: str
    issued_at: str
    scenario: str = "NO REGISTRADO"

    @property
    def key(self):
        return self.product_id, self.location_id, self.month


@dataclass(frozen=True)
class ClosedObservation:
    forecast: Forecast
    observed: int
    observed_at: str
    rotation: str = "SIN DATO"


def issue_forecast(reference, product_id, location_id, month, features, runtime, reason="", scenario="NORMAL"):
    reference.check_ids(product_id, location_id)
    parse_month(month)
    if scenario not in SCENARIOS:
        raise InputError("Escenario de seguimiento inválido.")
    info = active_info(runtime)
    values, baseline, prediction = None, None, None
    if features is not None:
        if tuple(features) != FEATURE_NAMES:
            raise InputError("El orden de features no coincide con el contrato.")
        for name in FEATURE_NAMES[:3]:
            validate_quantity(features[name])
        angle = 2 * math.pi * (int(month[5:]) - 1) / 12
        for name, expected in zip(FEATURE_NAMES[3:], (math.sin(angle), math.cos(angle))):
            if abs(checked_number(features[name]) - expected) > 1e-10:
                raise InputError("Calendario incompatible con el mes objetivo.")
        values = tuple(features.values())
        # Referencia analítica de último mes, no un modelo ML entrenado por Ross.
        baseline = float(features[FEATURE_NAMES[0]])
        if info is not None:
            if info.trained_through >= month:
                raise InputError("No se predice un mes utilizado para entrenar ACTIVE.")
            result = runtime.predict(deepcopy(features))
            if active_info(runtime) != info:
                raise InputError("ACTIVE cambió durante la inferencia. Repite con una versión estable.")
            if not isinstance(result, dict) or set(result) != {"prediction", "reason"}:
                raise InputError("Respuesta de inferencia incompatible.")
            if not isinstance(result["reason"], str):
                raise InputError("La respuesta debe distinguir predicción y motivo de abstención.")
            if result["prediction"] is not None:
                prediction = checked_number(result["prediction"])
                reason = ""
            else:
                allowed = {"HISTORIAL INSUFICIENTE", "DATOS INCOMPLETOS", "FUERA DE COBERTURA"}
                reason = result["reason"] if result["reason"] in allowed else "ABSTENCIÓN DEL MODELO"
        else:
            reason = "MODELO NO DISPONIBLE"
    if not reason and prediction is None:
        reason = "DATOS INCOMPLETOS"
    return Forecast(product_id, location_id, month, values, prediction, baseline, info,
                    reason, datetime.now(timezone.utc).isoformat(), scenario)


class ObservationJournal:
    """Estado exclusivo de una sesión. Las emisiones y cierres son inmutables."""
    def __init__(self):
        self.session_id = uuid.uuid4().hex
        self.pending = {}
        self.closed = {}
        self.revealed = {}
        self.trace_started_at = utc_now()
        self.revisions = []

    def record_edit(self, key, field, before, after, accepted=True):
        if before != after or not accepted:
            append_revision(self.revisions, "EDITOR_REVISION", key[:2], key[2],
                            field=field, before=before, after=after, accepted=accepted)

    def record_confirmation(self, key, features, error=None):
        append_revision(self.revisions, "INPUTS_CONFIRMED" if not error else "INPUTS_REJECTED",
                        key[:2], key[2], features=features, reason=error)

    def is_locked(self, key):
        return key in self.closed or key in self.revealed

    def discard_pending(self, key):
        if self.is_locked(key):
            raise InputError("El observado ya fue revelado. Cierra el mes o inicia una nueva sesión.")
        previous = self.pending.pop(key, None)
        if previous is not None:
            append_revision(self.revisions, "PENDING_DISCARDED", key[:2], key[2],
                            forecast=asdict(previous))

    def issue(self, forecast):
        if self.is_locked(forecast.key):
            raise InputError("Mes cerrado u observado revelado. Restablece la sesión para otra hipótesis.")
        self.pending[forecast.key] = forecast
        append_revision(self.revisions, "FORECAST_ISSUED", forecast.key[:2], forecast.month,
                        forecast=asdict(forecast))

    def reveal(self, key, observed):
        validate_quantity(observed)
        if key in self.closed or key not in self.pending:
            raise InputError("No hay una emisión pendiente para revelar ese observado.")
        if key in self.revealed and self.revealed[key] != observed:
            raise InputError("El observado revelado no se cambia dentro de la misma hipótesis.")
        if key not in self.revealed:
            append_revision(self.revisions, "OBSERVED_REVEALED", key[:2], key[2], observed=observed)
        self.revealed[key] = observed

    def close(self, key, observed, rotation="SIN DATO"):
        if key in self.closed:
            raise InputError("El mes ya está cerrado. No se duplica el observado.")
        if key not in self.pending:
            raise InputError("Primero emite una predicción o registra una abstención.")
        validate_quantity(observed)
        self.reveal(key, observed)
        forecast = self.pending[key]
        row = ClosedObservation(forecast, observed, datetime.now(timezone.utc).isoformat(), rotation)
        self.closed[key] = row
        del self.pending[key]
        append_revision(self.revisions, "OBSERVATION_CLOSED", key[:2], key[2],
                        observed=observed, observed_at=row.observed_at,
                        forecast=asdict(forecast))
        return row


def request_fingerprint(forecast):
    """Huella para trazabilidad de la entrada, sin incorporar el observado."""
    payload = repr((forecast.key, forecast.features, forecast.model, forecast.issued_at))
    return hashlib.sha256(payload.encode()).hexdigest()
