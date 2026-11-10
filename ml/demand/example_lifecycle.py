"""Ejemplo explícito R49 en directorio aislado; SIMULACIÓN, nunca TEST oficial.

Entrena un candidato nuevo de seis filas; no reentrena V1 ni promueve candidatos.
Las fechas/UUID cambian por ejecución; datos, parámetros y recorrido son fijos.
"""
import argparse
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import uuid

from demand_engine import create_session
from demand_runtime import create_runtime
from lifecycle_registry import LifecycleRegistry
from model_comparison import ComparisonSession
from retraining import RetrainingSession
from simulator_inputs import InputError, build_inputs, load_reference
from ui_runtime import ObservationJournal, issue_forecast


def run(output_root):
    root = Path(output_root).resolve() / ("example-" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    reference = load_reference()
    engine, journal = create_session(reference), ObservationJournal()
    engine.bind_journal(journal.session_id)
    engine.select(1, 5)
    registry = LifecycleRegistry(engine.session_id, root / "events")
    binding = registry.bind(1, 5)
    provider = create_runtime()
    provider.bind_lifecycle(binding)
    provider.activate_v1("Ejemplo R49: activar explícitamente V1 congelada.")
    for index, observed in enumerate(range(10, 22)):
        month = engine.status()["open_month"]
        # Historia inicial de este ensayo: tres meses NUEVOS, sin lags de TEST.
        features = None if index < 3 else build_inputs(
            reference, 1, 5, month, engine.lags(), history=engine.recent_history())
        forecast = issue_forecast(reference, 1, 5, month, features, provider,
                                  "HISTORIAL INSUFICIENTE" if features is None else "")
        journal.issue(forecast)
        engine.set_manual_observed(observed)
        engine.close_month()
        journal.close(forecast.key, observed)
        engine.advance_month()
    closed = deepcopy(journal.closed)
    training = RetrainingSession(engine.session_id, root / "candidates")
    training.bind_lifecycle(binding)
    candidate = training.train(engine, journal)
    comparison_service = ComparisonSession(engine.session_id, root / "decisions")
    comparison_service.bind_lifecycle(binding)
    comparison = comparison_service.compare(provider, training, candidate["run_id"])
    rejection = comparison_service.reject(comparison["id"], "Seis filas y tres reservas: evidencia insuficiente.")
    try:
        provider.promote_candidate({"decision": "APROBADO", "run_id": candidate["run_id"]})
    except InputError:
        pass
    else:
        raise AssertionError("La promoción real debe estar bloqueada.")
    provider.rollback("Ejemplo R49: retornar a SIN ACTIVE.")
    assert journal.closed == closed
    binding.emit("RESET", key="SESSION_RESET", state_before="LOCAL_CONTEXTS", state_after="INACTIVE",
        affected_contexts=[dict(product_id=1, location_id=5, active_before=None, active_after=None,
                                candidate_run_id=candidate["run_id"])],
        reason="Ejemplo explícito: descartar contextos, conservar evidencia.", result="RESET", affects_active=True)
    # Se descartan las referencias, no se hidrata ningún modelo desde el registro.
    provider, training, comparison_service = None, None, None
    new_provider = create_runtime()
    assert new_provider.get_active_model() is None
    assert registry.verify_sources()
    records = registry.records()
    result = dict(origin="SIMULACION", session_id=registry.session_id,
        candidate_id=candidate["run_id"], n_train=candidate["n_train"], n_series=candidate["n_series"],
        n_comparison=comparison["n_comparison"], decision=rejection["decision"],
        eligibility=comparison["eligibility"], event_types=[r["type"] for r in records],
        event_count=len(records), head_sha256=records[-1]["event_sha256"],
        registry_folder=str(registry.folder), comparison_id=comparison["id"],
        compared_data_sha256=comparison["compared_data_sha256"], metrics=comparison["metrics"],
        sources_verified=True, historical_predictions_preserved=True, final_active=None,
        closed_observations=[asdict(r) for r in journal.closed.values()])
    with (root / "summary.json").open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(dict(folder=str(root), **{k: result[k] for k in
        ("session_id", "candidate_id", "n_train", "n_comparison", "event_types", "head_sha256", "final_active")}), indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    run(parser.parse_args().output)
