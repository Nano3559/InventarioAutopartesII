"""R49: evidencia local append-only. No carga modelos ni restaura ACTIVE.

La cabeza y el inventario se anclan en esta instancia, no en JSON importados.
No existe constructor de recuperación desde disco. La cadena detecta cambios
respecto a ese ancla; no pretende ser una firma frente al dueño del equipo.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import uuid

from simulator_inputs import HERE, InputError

DEFAULT_ROOT = HERE / "lifecycle"


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class LifecycleRegistry:
    """Registro de una DemandSession; solo mantiene evidencia y sus anclas."""

    def __init__(self, session_id, output_root=None):
        if not isinstance(session_id, str) or not re.fullmatch(r"[a-f0-9]{32}", session_id):
            raise InputError("Sesión de registro inválida.")
        root = Path(DEFAULT_ROOT if output_root is None else output_root).resolve()
        for name in ("data", "models", "reports", "candidates", "decisions"):
            protected = (HERE / name).resolve()
            if root == protected or protected in root.parents or root in protected.parents:
                raise InputError("Registro dentro de un área protegida.")
        self.session_id = session_id
        self.folder = root / session_id
        self.folder.mkdir(parents=True, exist_ok=False)
        self._head = "0" * 64
        self._files = []
        self._keys = {}
        self._lock = threading.RLock()

    def bind(self, product_id, location_id):
        if any(type(v) is not int or v <= 0 for v in (product_id, location_id)):
            raise InputError("Par de registro inválido.")
        return LifecycleBinding(self, (product_id, location_id))

    def records(self, pair=None):
        """Lectura verificada; no admite registros ni anclas proporcionados por JSON."""
        with self._lock:
            if sorted(p.name for p in self.folder.iterdir()) != sorted(self._files):
                raise InputError("Inventario del registro alterado.")
            previous = "0" * 64
            rows = []
            for index, name in enumerate(self._files, 1):
                raw = (self.folder / name).read_bytes()
                record = json.loads(raw)
                claimed = record.pop("event_sha256")
                if (raw != canonical(dict(record, event_sha256=claimed))
                        or digest(record) != claimed or record["previous_sha256"] != previous
                        or record["sequence"] != index or record["session_id"] != self.session_id):
                    raise InputError("Cadena del registro alterada.")
                previous = claimed
                rows.append(dict(record, event_sha256=claimed))
            if previous != self._head:
                raise InputError("La cadena no coincide con el ancla de memoria.")
            if pair is not None:
                rows = [r for r in rows if (r["product_id"], r["location_id"]) == pair
                        or any((p["product_id"], p["location_id"]) == pair
                               for p in r.get("affected_contexts", []))]
            return deepcopy(rows)

    def _append(self, pair, event_type, key, payload):
        with self._lock:
            self.records()  # Nunca continuar silenciosamente una cadena corrupta.
            identity = (*pair, event_type, key)
            signature = digest(payload)
            if identity in self._keys:
                old_signature, record = self._keys[identity]
                if old_signature != signature:
                    raise InputError("Evento idempotente con contenido contradictorio.")
                return deepcopy(record)
            record = dict(schema="h4-model-lifecycle-1", id="EVT-" + uuid.uuid4().hex,
                          sequence=len(self._files) + 1,
                          timestamp=datetime.now(timezone.utc).isoformat(),
                          session_id=self.session_id, product_id=pair[0], location_id=pair[1],
                          type=event_type, previous_sha256=self._head, **deepcopy(payload))
            record["event_sha256"] = digest(record)
            name = f"{record['sequence']:08d}-{record['id']}.json"
            # Exclusivo y fsync antes de confirmar el evento en memoria.
            try:
                with (self.folder / name).open("xb") as handle:
                    handle.write(canonical(record))
                    handle.flush()
                    os.fsync(handle.fileno())
            except Exception:
                # Si quedó un fichero parcial, el inventario impedirá continuar.
                raise InputError("No se pudo conservar la evidencia local.") from None
            self._files.append(name)
            self._head = record["event_sha256"]
            self._keys[identity] = (signature, deepcopy(record))
            return deepcopy(record)

    def verify_sources(self):
        for record in self.records():
            source = record.get("source")
            if source and hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest() != source["sha256"]:
                raise InputError("Fuente del registro alterada.")
        return True


class LifecycleBinding:
    """Contexto de evidencia; no tiene métodos ni referencias de activación."""

    def __init__(self, registry, pair):
        self.registry, self.pair = registry, pair

    @property
    def session_id(self):
        return self.registry.session_id

    def emit(self, event_type, *, key, model=None, state_before=None, state_after=None,
             previous_reference=None, active_before=None, active_after=None,
             data_sha256=None, reason, result, source=None, affects_active=False, **details):
        for value in ((model or {}).get("artifact_hash"), data_sha256,
                      (source or {}).get("sha256")):
            if value is not None and not re.fullmatch(r"[a-f0-9]{64}", value):
                raise InputError("Huella de registro inválida.")
        return self.registry._append(self.pair, event_type, key, dict(
            model=model, artifact_hash=(model or {}).get("artifact_hash"),
            state_before=state_before, state_after=state_after,
            previous_reference=previous_reference, active_before=active_before,
            active_after=active_after, data_sha256=data_sha256,
            reason=reason, result=result, source=source, affects_active=affects_active, **details))


def bind_service(service, binding):
    """No permite reutilizar un servicio entre sesiones o pares distintos."""
    if not isinstance(binding, LifecycleBinding):
        raise InputError("El registro requiere un contexto local, no JSON.")
    old = service._lifecycle
    if old and (old.registry is not binding.registry or old.pair != binding.pair):
        raise InputError("Servicio vinculado a otro contexto.")
    if getattr(service, "session_id", binding.session_id) != binding.session_id:
        raise InputError("Servicio de otra sesión.")
    service._lifecycle = binding


def source_reference(identifier, path, expected_sha256=None):
    path = Path(path).resolve()
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected_sha256 is not None and actual != expected_sha256:
        raise InputError("La fuente no coincide con el registro de confianza.")
    return dict(id=identifier, path=str(path), sha256=actual)
