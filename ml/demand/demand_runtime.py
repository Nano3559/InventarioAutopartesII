"""Inferencia local H4. La confianza procede del código, nunca de uploads.

No hay ACTIVE global ni persistencia de promociones. Cada sesión comienza
inactiva; reconectar o restablecer descarta sus promociones locales.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import uuid
from pathlib import Path

from simulator_inputs import FEATURE_NAMES, HERE, MAX_UI_QUANTITY, InputError, content_sha256, parse_month

# Referencia independiente del fichero cargado, fijada tras la auditoría H4-10.
# Cambiarla requiere revisión de código; los manifiestos congelados no se editan.
V1_BINARY_SHA256 = "fb0d8d81ba2558101a232ff616bff14fe0b95d6a13dfa24d60a8dce4b4e81d3e"
V1_NORMALIZED_SHA256 = "3e3cf6d1ef75567a69ff6f604bcb2a93f629f6d0fa503bdf734f3c6118c03883"
V1_MANIFEST_SHA256 = "41a10f4d196979cfff67410b21bf8ae527f6547aeca413e58811b4be920935f6"


class DemandRuntime:
    """Proveedor por sesión; validación previa y sustitución atómica local."""

    def __init__(self):
        self._active = None
        self._previous = []
        self._events = []
        self._reference_checks = {}
        self._lifecycle = None
        self._audit_before = None

    def bind_lifecycle(self, binding):
        from lifecycle_registry import bind_service, source_reference, LifecycleBinding
        if not isinstance(binding, LifecycleBinding):
            raise InputError("El registro requiere un contexto local, no JSON.")
        if self._lifecycle is not None:
            bind_service(self, binding)
            return
        # Disponibilidad verificada sin deserializar ni activar el estimador.
        path = HERE / "models/random_forest_candidate.joblib"
        raw = path.read_bytes()
        manifest_path = HERE / "reports/v1_selection_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (hashlib.sha256(raw).hexdigest() != V1_BINARY_SHA256
                or content_sha256(raw) != V1_NORMALIZED_SHA256
                or manifest.get("status") != "SELECTED_FROZEN_NOT_ACTIVE"
                or manifest.get("active") is not False
                or manifest.get("artifact", {}).get("sha256") != V1_NORMALIZED_SHA256
                or manifest.get("contract", {}).get("features") != list(FEATURE_NAMES)):
            raise InputError("V1 disponible no verificada.")
        binding.emit("V1_AVAILABLE", key="V1", model=dict(name="RandomForestRegressor",
                     version="V1", artifact_hash=V1_BINARY_SHA256), state_before="UNREGISTERED",
                     state_after="AVAILABLE", reason="Referencia congelada verificada; no activa.",
                     result="VERIFIED", normalized_sha256=V1_NORMALIZED_SHA256,
                     source=source_reference("V1_SELECTION_MANIFEST", manifest_path, V1_MANIFEST_SHA256))
        binding.emit("RUNTIME_CONNECTED", key=uuid.uuid4().hex, model=self.get_active_model(),
                     active_after=self.get_active_model(), state_after="ACTIVE" if self._active else "INACTIVE",
                     reason="Conexión local observada ahora; no reconstruye activaciones previas.", result="CONNECTED",
                     affects_active=True)
        bind_service(self, binding)

    def get_active_model(self):
        return deepcopy(self._active[0]) if self._active else None

    @property
    def events(self):
        return deepcopy(self._events)

    def export_references(self):
        """Solo metadatos verificados; no estimadores ni autoridad de restauración."""
        for reference in (self._active, *self._previous):
            if reference is not None:
                metadata = reference[0]
                check = self._reference_checks.get(metadata["artifact_hash"])
                if check is None or check[0] != metadata or not check[1]():
                    raise InputError("Referencia de exportación no verificable.")
        return deepcopy(dict(active=self.get_active_model(),
            previous_references=[r[0] if r else None for r in self._previous],
            runtime_events=self.events, verification="VERIFIED_LOCAL_REFERENCES"))

    def _load_verified(self, path, binary_hash, normalized_hash, version):
        # Solo el llamador de confianza interno establece hashes y ruta.
        raw = Path(path).read_bytes()
        if (hashlib.sha256(raw).hexdigest() != binary_hash
                or content_sha256(raw) != normalized_hash):
            raise InputError("ARTEFACTO NO VERIFICADO.")
        import joblib
        import sklearn
        # Cargar exactamente los bytes verificados evita un cambio entre hash/load.
        payload = joblib.load(io.BytesIO(raw))
        if not isinstance(payload, dict):
            raise InputError("ARTEFACTO INCOMPATIBLE.")
        if (payload.get("schema") != "h4-random-forest-1"
                or payload.get("role") != "CANDIDATE"
                or payload.get("model") != "RANDOMFOREST"
                or payload.get("feature_names") != list(FEATURE_NAMES)
                or payload.get("target") != "target_ventas_mes"
                or payload.get("scaler") is not None
                or payload.get("versions", {}).get("scikit-learn") != sklearn.__version__):
            raise InputError("ARTEFACTO INCOMPATIBLE.")
        estimator = payload.get("estimator")
        from sklearn.ensemble import RandomForestRegressor
        if (not isinstance(estimator, RandomForestRegressor)
                or getattr(estimator, "n_features_in_", None) != 5
                or list(getattr(estimator, "feature_names_in_", ())) != list(FEATURE_NAMES)):
            raise InputError("ESTIMADOR INCOMPATIBLE.")
        if any(estimator.get_params().get(k) != v for k, v in payload.get("parameters", {}).items()):
            raise InputError("PARÁMETROS INCOMPATIBLES.")
        parse_month(payload.get("trained_through"))
        metadata = dict(name="RandomForestRegressor", version=version,
                        artifact_hash=binary_hash, trained_through=payload["trained_through"],
                        origin="SIMULACION", feature_names=list(FEATURE_NAMES), role="ACTIVE")
        return metadata, estimator

    def promote_v1(self, reason):
        """Alias histórico de T10; conserva el evento usado por sus pruebas."""
        return self._select_v1(reason, action="PROMOTE")

    def activate_v1(self, reason):
        """Activa la referencia V1 ya seleccionada; no promueve candidatos nuevos."""
        return self._select_v1(reason, action="ACTIVATE_V1")

    def _select_v1(self, reason, *, action):
        if not isinstance(reason, str) or not reason.strip():
            raise InputError("La promoción requiere un motivo.")
        manifest = json.loads((HERE / "reports/v1_selection_manifest.json").read_text(encoding="utf-8"))
        if (manifest.get("status") != "SELECTED_FROZEN_NOT_ACTIVE"
                or manifest.get("active") is not False
                or manifest.get("artifact", {}).get("sha256") != V1_NORMALIZED_SHA256
                or manifest.get("contract", {}).get("features") != list(FEATURE_NAMES)):
            raise InputError("MANIFIESTO INCOMPATIBLE.")
        candidate = self._load_verified(HERE / "models/random_forest_candidate.joblib",
                                        V1_BINARY_SHA256, V1_NORMALIZED_SHA256, "V1")
        path = HERE / "models/random_forest_candidate.joblib"
        expected_hash = V1_BINARY_SHA256
        saved = (self._active, list(self._previous), dict(self._reference_checks))
        try:
            self._replace_active(candidate, lambda: hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash)
            self._record(action, reason)
        except Exception:
            self._active, self._previous, self._reference_checks = saved
            self._audit_before = None
            raise
        return self.get_active_model()

    def _replace_active(self, reference, verifier):
        """Transición interna de referencias ya verificadas; sin selector de política."""
        self._audit_before = self.get_active_model()
        self._reference_checks[reference[0]["artifact_hash"]] = (deepcopy(reference[0]), verifier)
        self._previous.append(self._active)
        self._active = reference

    def promote_candidate(self, *args, **kwargs):
        """Bloqueo incondicional: reportes o configuración no autorizan promoción."""
        reason = "PROMOCIÓN BLOQUEADA: falta un protocolo de elegibilidad previamente aprobado."
        self._record("PROMOTION_BLOCKED", reason)
        raise InputError(reason)

    def rollback(self, reason):
        if not isinstance(reason, str) or not reason.strip() or not self._previous:
            raise InputError("Reversión sin referencia anterior o motivo.")
        previous = self._previous[-1]
        if previous is not None:
            metadata = previous[0]
            check = self._reference_checks.get(metadata["artifact_hash"])
            if check is None or check[0] != metadata or not check[1]():
                raise InputError("ROLLBACK BLOQUEADO: identidad anterior no verificable.")
            if (metadata.get("feature_names") != list(FEATURE_NAMES)
                    or list(getattr(previous[1], "feature_names_in_", ())) != list(FEATURE_NAMES)):
                raise InputError("ROLLBACK BLOQUEADO: contrato anterior incompatible.")
        saved = self._active
        self._audit_before = self.get_active_model()
        self._active = self._previous.pop()
        try:
            self._record("ROLLBACK", reason)
        except Exception:
            self._previous.append(self._active)
            self._active = saved
            self._audit_before = None
            raise
        return self.get_active_model()

    def _record(self, action, reason):
        after = self.get_active_model()
        transition = action in ("PROMOTE", "ACTIVATE_V1", "PROMOTE_FIXTURE", "ROLLBACK")
        before = self._audit_before if transition else after
        if self._lifecycle:
            self._lifecycle.emit(action, key=uuid.uuid4().hex,
                model=None if action == "PROMOTION_BLOCKED" else after or before,
                state_before="ACTIVE" if before else "INACTIVE",
                state_after="ACTIVE" if after else "AVAILABLE" if transition else "INACTIVE",
                previous_reference=before, active_before=before, active_after=after,
                displaced_reference=dict(model=before, state="ARCHIVED") if transition and before else None,
                reason=reason.strip(), result="BLOCKED" if action == "PROMOTION_BLOCKED" else "COMPLETED",
                affects_active=transition,
                scope="ISOLATED_FIXTURE" if action.endswith("FIXTURE") else "LOCAL_SIMULATION")
        self._events.append(dict(action=action, reason=reason.strip(),
                                 timestamp=datetime.now(timezone.utc).isoformat(),
                                 model=self.get_active_model()))
        self._audit_before = None

    def predict(self, features):
        if self._active is None:
            return dict(prediction=None, reason="MODELO NO DISPONIBLE")
        if not isinstance(features, dict) or tuple(features) != FEATURE_NAMES:
            return dict(prediction=None, reason="DATOS INCOMPLETOS")
        values = list(features.values())
        if any(v is None for v in values[:3]):
            return dict(prediction=None, reason="HISTORIAL INSUFICIENTE")
        if any(type(v) not in (int, float) or abs(v) > MAX_UI_QUANTITY or not math.isfinite(v) for v in values):
            return dict(prediction=None, reason="DATOS INCOMPLETOS")
        if (any(v < 0 or v > MAX_UI_QUANTITY or int(v) != v for v in values[:3])
                or any(abs(v) > 1 for v in values[3:])
                or not any(abs(values[3] - math.sin(2*math.pi*m/12)) < 1e-10
                           and abs(values[4] - math.cos(2*math.pi*m/12)) < 1e-10 for m in range(12))):
            return dict(prediction=None, reason="FUERA DE COBERTURA")
        try:
            import pandas as pd
            prediction = self._active[1].predict(pd.DataFrame([values], columns=FEATURE_NAMES))
            if len(prediction) != 1:
                raise ValueError()
            value = float(prediction[0])
            if not math.isfinite(value) or abs(value) > MAX_UI_QUANTITY:
                raise ValueError()
            return dict(prediction=value, reason="")
        except Exception:
            return dict(prediction=None, reason="ABSTENCIÓN DEL MODELO")


def create_runtime():
    return DemandRuntime()
