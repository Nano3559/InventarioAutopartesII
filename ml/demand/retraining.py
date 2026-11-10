"""Ensayo incremental local: cierres nuevos, corte fijo y candidato separado.

No importa el entrenador V1 ni lee sus datasets/artefactos. La reserva solo
se congela, nunca se predice ni se utiliza para seleccionar parámetros aquí.
"""
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import re
import threading
import uuid

from simulator_inputs import FEATURE_NAMES, HERE, InputError, offset_month, validate_quantity

CANDIDATES_DIR = HERE / "candidates"
MONTHS = tuple(offset_month("2026-10", i) for i in range(12))
PARAMETERS = dict(n_estimators=200, max_depth=8, min_samples_leaf=3,
                  max_features="sqrt", random_state=42, n_jobs=1)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def prepare_incremental(engine, journal):
    """Valida ambas autoridades; crea lags desde cierres, no desde emisiones."""
    snapshot = engine.export_closed()
    if snapshot["journal_id"] != journal.session_id:
        raise InputError("ENSAYO NO DISPONIBLE: diario de otra sesión.")
    pair = snapshot["product_id"], snapshot["location_id"]
    records = snapshot["records"]
    months = [r["month"] for r in records]
    if len(months) != len(set(months)):
        raise InputError("Cierres duplicados.")
    engine_rows = {r["month"]: r for r in records}
    journal_rows = {}
    for key, row in journal.closed.items():
        if key != row.forecast.key:
            raise InputError("Clave de cierre inconsistente.")
        if key[:2] == pair and key[2] >= "2026-10":
            journal_rows[key[2]] = row
    if set(engine_rows) != set(journal_rows):
        raise InputError("Cierres inconsistentes entre motor y diario.")
    for month, record in engine_rows.items():
        row = journal_rows[month]
        validate_quantity(record["observed"])
        validate_quantity(row.observed)
        if record["observed"] != row.observed or record["source"] not in ("MANUAL", "GENERATED"):
            raise InputError("Observados contradictorios o procedencia inválida.")
        if datetime.fromisoformat(row.observed_at) < datetime.fromisoformat(row.forecast.issued_at):
            raise InputError("El cierre precede a la emisión.")
    if not set(MONTHS) <= set(engine_rows):
        raise InputError("ENSAYO NO DISPONIBLE: se necesitan los 12 cierres consecutivos octubre 2026–septiembre 2027.")
    observations = [dict(engine_rows[m], issued_at=journal_rows[m].forecast.issued_at,
                         closed_at=journal_rows[m].observed_at) for m in MONTHS]
    rows, trace = [], []
    for month in MONTHS[3:]:
        lags = [engine_rows[offset_month(month, -i)]["observed"] for i in (1, 2, 3)]
        angle = 2 * math.pi * (int(month[5:]) - 1) / 12
        values = [*lags, math.sin(angle), math.cos(angle)]
        rows.append(dict(mes_objetivo=month, productId=pair[0], locationId=pair[1],
                         **dict(zip(FEATURE_NAMES, values)),
                         target_ventas_mes=engine_rows[month]["observed"]))
        forecast = journal_rows[month].forecast
        trace.append(dict(month=month, emitted_features=forecast.features,
                          reconstructed_features=values,
                          differs=forecast.features is None or any(
                              abs(a-b) > 1e-10 for a, b in zip(forecast.features, values))))
    return dict(schema="h4-incremental-data-1", origin="SIMULACION",
                session_id=snapshot["session_id"], journal_id=journal.session_id,
                product_id=pair[0], location_id=pair[1], scenario=snapshot["scenario"],
                generator_seed=snapshot["seed"], observations=observations,
                history_months=list(MONTHS[:3]), train=rows[:6], reserved=rows[6:],
                cutoff="2027-06", trace=trace, ignored_later_months=sorted(set(months)-set(MONTHS)))


class RetrainingSession:
    """Registro por sesión; un mismo conjunto no entrena dos veces."""

    def __init__(self, session_id, output_root=CANDIDATES_DIR):
        if not isinstance(session_id, str) or not re.fullmatch(r"[a-f0-9]{32}", session_id):
            raise InputError("Identificador de sesión inválido.")
        self.session_id = session_id
        self.output_root = Path(output_root).resolve()
        # Impedir escrituras en áreas históricas, incluso con raíz configurable.
        for protected in (HERE / "data", HERE / "models", HERE / "reports"):
            protected = protected.resolve()
            if self.output_root == protected or protected in self.output_root.parents or self.output_root in protected.parents:
                raise InputError("Destino de candidato dentro de un área protegida.")
        self._lock = threading.Lock()
        self._runs = {}
        self._lifecycle = None
        self._auditable_runs = set()

    def bind_lifecycle(self, binding):
        from lifecycle_registry import bind_service
        bind_service(self, binding)

    def _audit_run(self, run):
        if self._lifecycle:
            from lifecycle_registry import source_reference
            self._lifecycle.emit("CANDIDATE_CREATED", key=run["run_id"],
                model=dict(name="RandomForestRegressor", version=run["run_id"],
                           artifact_hash=run["files"]["candidate.joblib"]),
                state_before="ABSENT", state_after="CANDIDATE", data_sha256=run["data_sha256"],
                source=source_reference(run["run_id"], Path(run["folder"])/"manifest.json", digest(run)),
                source_timestamp=run["created_utc"], n_train=run["n_train"], n_series=run["n_series"],
                reason="Ensayo explícito con nuevos cierres; sin promoción automática.", result="CREATED")

    def trusted_run(self, run_id):
        """Solo ejecuciones creadas por esta instancia; nunca JSON importados."""
        for run in self._runs.values():
            if run["run_id"] == run_id:
                return json.loads(json.dumps(run))
        raise InputError("El candidato no pertenece al registro de esta sesión.")

    def export_runs(self):
        """Copias de los manifiestos propios; el exportador verifica sus bytes."""
        return [self.trusted_run(run["run_id"]) for run in self._runs.values()]

    def train(self, engine, journal):
        if engine.session_id != self.session_id:
            raise InputError("Entrenamiento solicitado desde otra sesión.")
        if self._lifecycle:
            state = engine.status()
            if (state["product_id"], state["location_id"]) != self._lifecycle.pair:
                raise InputError("Entrenamiento de otro par.")
        if not self._lock.acquire(blocking=False):
            raise InputError("Ya hay un ensayo en ejecución.")
        try:
            data = prepare_incremental(engine, journal)
            key = digest(dict(data={k: v for k, v in data.items() if k != "ignored_later_months"},
                              parameters=PARAMETERS))
            if key in self._runs:
                if self._runs[key]["run_id"] in self._auditable_runs:
                    self._audit_run(self._runs[key])
                return json.loads(json.dumps(self._runs[key]))
            import joblib
            import pandas as pd
            from sklearn.ensemble import RandomForestRegressor
            frame = pd.DataFrame(data["train"])
            X = frame.loc[:, list(FEATURE_NAMES)]
            y = frame["target_ventas_mes"]
            model = RandomForestRegressor(**PARAMETERS)
            model.fit(X, y)
            run_id = "CAND-" + uuid.uuid4().hex
            folder = self.output_root / self.session_id / run_id
            folder.mkdir(parents=True, exist_ok=False)
            created = datetime.now(timezone.utc).isoformat()
            versions = {name: version(name) for name in ("numpy", "pandas", "scikit-learn", "joblib")}
            versions["python"] = platform.python_version()
            artifact = dict(schema="h4-incremental-random-forest-1", role="CANDIDATE",
                            version=run_id, model="RANDOMFOREST", estimator=model, scaler=None,
                            feature_names=list(FEATURE_NAMES), target="target_ventas_mes",
                            trained_through=data["cutoff"], parameters=dict(PARAMETERS),
                            dataset_sha256=digest(data), versions=versions, created_utc=created)
            # Todos los ficheros son nuevos y exclusivos de la ejecución.
            (folder / "incremental.json").write_bytes(canonical(data))
            frame.to_csv(folder / "train.csv", index=False, lineterminator="\n")
            pd.DataFrame(data["reserved"]).to_csv(folder / "reserved.csv", index=False, lineterminator="\n")
            joblib.dump(artifact, folder / "candidate.joblib")
            files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}
            result = dict(schema="h4-retraining-run-1", run_id=run_id, role="CANDIDATE",
                          session_id=self.session_id, journal_id=journal.session_id,
                          product_id=data["product_id"], location_id=data["location_id"],
                          created_utc=created, folder=str(folder), data_sha256=digest(data),
                          files=files, parameters=dict(PARAMETERS), versions=versions,
                          feature_names=list(FEATURE_NAMES), n_train=len(X), n_series=1,
                          n_reserved=len(data["reserved"]), cutoff=data["cutoff"],
                          metrics=None, metrics_reason="Comparación reservada para Tarea 13; sin evaluación en entrenamiento.",
                          promoted=False)
            (folder / "manifest.json").write_bytes(canonical(result))
            self._runs[key] = result
            if self._lifecycle:
                self._auditable_runs.add(run_id)
            self._audit_run(result)
            return json.loads(json.dumps(result))
        finally:
            self._lock.release()
