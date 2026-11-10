"""Comparación local sin fit. La política real de promoción siempre deniega.

Solo acepta ejecuciones de RetrainingSession o el archivo auditado de Tarea 12.
El JSON de Ross es exclusivamente una representación de resultados.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import uuid

from retraining import canonical, digest, MONTHS
from simulator_inputs import HERE, FEATURE_NAMES, InputError, offset_month, validate_quantity
from ui_runtime import active_info, checked_number, model_info
from ui_analysis import metric_values

BLOCK_REASON = "Promoción real bloqueada: no existe un protocolo de elegibilidad previamente aprobado."
ARCHIVE_SESSION = "9958a7bc0be3447e88c6b4a331b05ace"
ARCHIVE_RUN = "CAND-f3690f19436644959f2218cdc079110c"
ARCHIVE_MANIFEST_SHA256 = "556bd266c53bda5aee932ec3a359a53a43a6e1c8a690e564f2c9e8d991360b0f"


def archived_run():
    path = HERE / "candidates" / ARCHIVE_SESSION / ARCHIVE_RUN / "manifest.json"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_MANIFEST_SHA256:
        raise InputError("Manifiesto archivado no verificado.")
    run = json.loads(raw)
    # El manifiesto conserva la ruta auditada; no aceptar otra ubicación.
    if Path(run["folder"]).resolve() != path.parent.resolve():
        raise InputError("Ubicación archivada incompatible.")
    return run


def verified_bundle(run):
    """run procede de un registro de confianza, no de un formulario/upload."""
    folder = Path(run["folder"])
    expected_files = {"candidate.joblib", "incremental.json", "train.csv", "reserved.csv"}
    if set(run["files"]) != expected_files:
        raise InputError("Conjunto de archivos incompatible.")
    blobs = {name: (folder / name).read_bytes() for name in expected_files}
    if any(hashlib.sha256(blobs[name]).hexdigest() != run["files"][name] for name in expected_files):
        raise InputError("Integridad del candidato o datos inválida.")
    data = json.loads(blobs["incremental.json"])
    if (digest(data) != run["data_sha256"] or data["session_id"] != run["session_id"]
            or data["journal_id"] != run["journal_id"] or run["role"] != "CANDIDATE"
            or run["cutoff"] != "2027-06" or data["cutoff"] != run["cutoff"]
            or run["feature_names"] != list(FEATURE_NAMES)):
        raise InputError("Contrato o procedencia incompatible.")
    observations = data["observations"]
    if [r["month"] for r in observations] != list(MONTHS):
        raise InputError("Historia nueva incompleta o duplicada.")
    obs = {r["month"]: validate_quantity(r["observed"]) for r in observations}
    rows = data["train"] + data["reserved"]
    if (len(data["train"]) != 6 or len(data["reserved"]) != 3
            or [r["mes_objetivo"] for r in rows] != list(MONTHS[3:])
            or run["n_train"] != 6 or run["n_reserved"] != 3 or run["n_series"] != 1):
        raise InputError("Split incremental incompatible.")
    for row in rows:
        month = row["mes_objetivo"]
        if (row["productId"] != data["product_id"] or row["locationId"] != data["location_id"]
                or row["target_ventas_mes"] != obs[month]
                or [row[k] for k in FEATURE_NAMES[:3]] != [obs[offset_month(month, -i)] for i in (1, 2, 3)]):
            raise InputError("Datos o lags inconsistentes.")
        angle = 2 * math.pi * (int(month[5:]) - 1) / 12
        if any(abs(row[k]-v) > 1e-10 for k, v in zip(FEATURE_NAMES[3:], (math.sin(angle), math.cos(angle)))):
            raise InputError("Calendario inconsistente.")
    import pandas as pd
    for name, expected in (("train.csv", data["train"]), ("reserved.csv", data["reserved"])):
        frame = pd.read_csv(io.BytesIO(blobs[name]))
        columns = ["mes_objetivo", "productId", "locationId", *FEATURE_NAMES, "target_ventas_mes"]
        try:
            pd.testing.assert_frame_equal(frame, pd.DataFrame(expected).loc[:, columns], check_dtype=False, atol=1e-10, rtol=0)
        except AssertionError as exc:
            raise InputError("CSV y snapshot no coinciden.") from exc
    # Deserializar exclusivamente bytes ya contrastados con referencia independiente.
    import joblib
    import sklearn
    from sklearn.ensemble import RandomForestRegressor
    payload = joblib.load(io.BytesIO(blobs["candidate.joblib"]))
    if (payload.get("schema") != "h4-incremental-random-forest-1"
            or payload.get("role") != "CANDIDATE" or payload.get("version") != run["run_id"]
            or payload.get("dataset_sha256") != run["data_sha256"]
            or payload.get("feature_names") != list(FEATURE_NAMES)
            or payload.get("trained_through") != run["cutoff"]
            or payload.get("scaler") is not None or payload.get("target") != "target_ventas_mes"
            or payload.get("versions", {}).get("scikit-learn") != sklearn.__version__
            or payload.get("parameters") != run["parameters"]):
        raise InputError("Artefacto incremental incompatible.")
    estimator = payload["estimator"]
    if (not isinstance(estimator, RandomForestRegressor) or estimator.n_features_in_ != 5
            or list(estimator.feature_names_in_) != list(FEATURE_NAMES)
            or any(estimator.get_params().get(k) != v for k, v in run["parameters"].items())):
        raise InputError("Estimador incremental incompatible.")
    metadata = dict(name="RandomForestRegressor", version=run["run_id"],
                    artifact_hash=run["files"]["candidate.joblib"], trained_through=run["cutoff"],
                    origin="SIMULACION", feature_names=list(FEATURE_NAMES), role="CANDIDATE")
    model_info(metadata)
    return data, metadata, estimator


def statistics(rows, hash_value):
    pairs = [(r["observed"], r["predictions"][hash_value]) for r in rows
             if r["predictions"][hash_value] is not None]
    metrics = metric_values(pairs)
    return {**metrics, "R2_descriptive": metrics["R2"], "R2": None,
            "R2_reason": "Solo tres observaciones; R² aritmético descriptivo, sin conclusión estadística.",
            "observations": len(rows), "coverage": len(pairs)/len(rows)}


class ComparisonSession:
    def __init__(self, session_id, output_root=HERE / "decisions"):
        import re
        if not isinstance(session_id, str) or not re.fullmatch(r"[a-f0-9]{32}", session_id):
            raise InputError("Sesión de comparación inválida.")
        self.session_id = session_id
        self.output_root = Path(output_root).resolve()
        for name in ("data", "models", "reports", "candidates"):
            protected = (HERE/name).resolve()
            if self.output_root == protected or protected in self.output_root.parents or self.output_root in protected.parents:
                raise InputError("Directorio de decisiones dentro de un área protegida.")
        self._results = {}
        self._decisions = []
        self._lifecycle = None

    def bind_lifecycle(self, binding):
        from lifecycle_registry import bind_service
        bind_service(self, binding)

    def _audit_comparison(self, record):
        if self._lifecycle:
            from lifecycle_registry import source_reference
            fields = dict(model=record["candidate"], previous_reference=record["active"],
                active_before=record["active"], active_after=record["active"],
                data_sha256=record["compared_data_sha256"],
                source=source_reference(record["id"], self.output_root/self.session_id/(record["id"]+".json"), digest(record)),
                source_timestamp=record["timestamp"], period=record["period"],
                n_comparison=record["n_comparison"], state_before="CANDIDATE", state_after="CANDIDATE",
                reason=record["reason"])
            self._lifecycle.emit("MODELS_COMPARED", key=record["id"], result="COMPLETED", **fields)
            self._lifecycle.emit("INSUFFICIENT_EVIDENCE", key=record["id"], result=record["eligibility"], **fields)

    def _audit_rejection(self, record):
        if self._lifecycle:
            from lifecycle_registry import source_reference
            self._lifecycle.emit("CANDIDATE_REJECTED", key=record["id"], model=record["candidate"],
                previous_reference=record["active"], active_snapshot_available=False,
                state_before="CANDIDATE", state_after="REJECTED", data_sha256=record["compared_data_sha256"],
                source=source_reference(record["id"], self.output_root/self.session_id/(record["id"]+".json"), digest(record)),
                source_timestamp=record["timestamp"], reason=record["reason"], result=record["decision"])

    @property
    def decisions(self):
        return deepcopy(self._decisions)

    def export_evidence(self):
        from lifecycle_registry import source_reference
        records = [*self._results.values(), *self._decisions]
        return [dict(record=deepcopy(r), source=source_reference(r["id"],
            self.output_root/self.session_id/(r["id"]+".json"), digest(r))) for r in records]

    def _save(self, record):
        folder = self.output_root/self.session_id
        folder.mkdir(parents=True, exist_ok=True)
        with (folder/(record["id"]+".json")).open("xb") as handle:
            handle.write(canonical(record))

    def compare(self, runtime, training_session, run_id):
        if training_session.session_id != self.session_id:
            raise InputError("Registro de entrenamiento de otra sesión.")
        return self._compare(runtime, training_session.trusted_run(run_id))

    def compare_archived(self, runtime):
        """Único candidato histórico admitido: paquete fijado tras Tarea 12."""
        return self._compare(runtime, archived_run())

    def _compare(self, runtime, run):
        if self._lifecycle and (run["product_id"], run["location_id"]) != self._lifecycle.pair:
            raise InputError("Comparación de otro par.")
        before = runtime.get_active_model() if runtime else None
        if active_info(runtime) is None:
            raise InputError("Comparación no disponible: no hay ACTIVE en esta sesión.")
        data, candidate, estimator = verified_bundle(run)
        if before["artifact_hash"] == candidate["artifact_hash"]:
            raise InputError("ACTIVE y CANDIDATE deben ser distintos.")
        import pandas as pd
        rows = []
        for row in data["reserved"]:
            month = row["mes_objetivo"]
            if month <= before["trained_through"] or month <= candidate["trained_through"]:
                raise InputError("La comparación incluye meses de entrenamiento.")
            features = {k: row[k] for k in FEATURE_NAMES}
            result = runtime.predict(deepcopy(features))
            if not isinstance(result, dict) or set(result) != {"prediction", "reason"}:
                raise InputError("Respuesta ACTIVE incompatible.")
            active_prediction = None if result["prediction"] is None else checked_number(result["prediction"])
            try:
                values = estimator.predict(pd.DataFrame([features], columns=FEATURE_NAMES))
                candidate_prediction = checked_number(float(values[0])) if len(values) == 1 else None
            except Exception:
                candidate_prediction = None
            if runtime.get_active_model() != before:
                raise InputError("ACTIVE cambió durante la comparación.")
            rows.append(dict(productId=row["productId"], locationId=row["locationId"],
                             mes_objetivo=month, features=features, observed=row["target_ventas_mes"],
                             predictions={before["artifact_hash"]: active_prediction,
                                          candidate["artifact_hash"]: candidate_prediction}))
        key = digest(dict(active=before, candidate=candidate, rows=rows))
        if key in self._results:
            self._audit_comparison(self._results[key])
            return deepcopy(self._results[key])
        common = [row for row in rows if all(v is not None for v in row["predictions"].values())]
        reason = "INSUFFICIENT_EVIDENCE: seis filas de entrenamiento de una serie y tres observaciones reservadas. " + BLOCK_REASON
        record = dict(id="CMP-"+uuid.uuid4().hex, schema="h4-local-comparison-decision-1",
                      session_id=self.session_id, source_session_id=run["session_id"],
                      timestamp=datetime.now(timezone.utc).isoformat(), run_id=run["run_id"],
                      active=before, candidate=candidate, data_sha256=run["data_sha256"],
                      compared_data_sha256=digest(data["reserved"]), artifact_files=run["files"],
                      period=[rows[0]["mes_objetivo"], rows[-1]["mes_objetivo"]],
                      n_train=run["n_train"], n_series=run["n_series"], n_comparison=len(rows),
                      metrics={h: statistics(rows, h) for h in rows[0]["predictions"]},
                      common_metrics={h: statistics(common, h) for h in rows[0]["predictions"]} if common else {},
                      common_n=len(common), rows=rows, technical_comparison="COMPLETED",
                      eligibility="INSUFFICIENT_EVIDENCE", promotion_allowed=False, reason=reason,
                      ross_report=dict(schema_version="h4-comparison-1", origin="SIMULACION",
                                       purpose="COMPARACION_LOCAL", models=[before, candidate], rows=rows,
                                       decision="RECHAZADO", reason=reason))
        self._save(record)
        self._results[key] = deepcopy(record)
        self._audit_comparison(record)
        return deepcopy(record)

    def reject(self, comparison_id, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise InputError("El rechazo requiere motivo.")
        found = next((r for r in self._results.values() if r["id"] == comparison_id), None)
        if found is None:
            raise InputError("Comparación no registrada en esta sesión.")
        for previous in self._decisions:
            if previous["comparison_id"] == comparison_id and previous["reason"] == reason.strip():
                self._audit_rejection(previous)
                return deepcopy(previous)
        record = dict(id="DEC-"+uuid.uuid4().hex, comparison_id=comparison_id,
                      session_id=self.session_id, timestamp=datetime.now(timezone.utc).isoformat(),
                      decision="REJECTED_FOR_PROMOTION", reason=reason.strip(),
                      active=found["active"], candidate=found["candidate"],
                      compared_data_sha256=found["compared_data_sha256"])
        self._save(record)
        self._decisions.append(deepcopy(record))
        self._audit_rejection(record)
        return deepcopy(record)
