"""Ejemplo explícito R52: exporta simulación con V1 real, sin entrenar modelos."""
import argparse
import json
from pathlib import Path
import uuid

from demand_engine import create_session
from demand_runtime import create_runtime
from lifecycle_registry import LifecycleRegistry
from pair_contexts import bind_pair_context
from session_export import build_session_export, verify_session_export
from simulator_inputs import build_inputs
from ui_runtime import ObservationJournal, issue_forecast


def run(output):
    folder = Path(output).resolve() / ("example-" + uuid.uuid4().hex)
    folder.mkdir(parents=True, exist_ok=False)
    engine, journal = create_session(), ObservationJournal()
    engine.bind_journal(journal.session_id)
    registry = LifecycleRegistry(engine.session_id, folder / "events")
    state = {}
    for product, location in ((1, 5), (2, 6)):
        engine.select(product, location)
        bind_pair_context(state, engine.session_id, product, location)
        provider = create_runtime()
        provider.bind_lifecycle(registry.bind(product, location))
        state["h4_runtime"] = provider
        if product == 1:
            provider.activate_v1("Ejemplo R52: activar V1 solo para 1/5.")
            engine.edit_lags(4, 8, 12)
        else:
            engine.apply_scenario("STOCKOUT")
        month = engine.status()["open_month"]
        features = build_inputs(engine._reference, product, location, month, engine.lags(),
                                history=engine.recent_history(), scenario=engine.status()["scenario"])
        forecast = issue_forecast(engine._reference, product, location, month, features,
                                  provider, scenario=engine.status()["scenario"])
        journal.issue(forecast)
        if product == 1:
            observed = 10  # Entrada manual exclusivamente SIMULADA.
            engine.set_manual_observed(observed)
        else:
            observed = engine.generate_observed()
        journal.reveal(forecast.key, observed)
        engine.close_month()
        journal.close(forecast.key, observed)
        engine.advance_month()
    current = build_session_export(engine, journal, state, registry)
    engine.select(1, 5); bind_pair_context(state, engine.session_id, 1, 5)
    provider = state["h4_runtime"]
    provider.rollback("Ejemplo R52: demostrar retorno sin cambiar cierres.")
    rolled_back = build_session_export(engine, journal, state, registry)
    provider.activate_v1("Ejemplo R52: activación explícita antes del reset.")
    registry.bind(1, 5).emit("RESET", key="SESSION_RESET", state_before="LOCAL_CONTEXTS",
        state_after="INACTIVE", affects_active=True,
        affected_contexts=[dict(product_id=1, location_id=5, active_before=provider.get_active_model(), active_after=None),
                           dict(product_id=2, location_id=6, active_before=None, active_after=None)],
        reason="Ejemplo: descartar los contextos y conservar evidencia.", result="RESET")
    archived = build_session_export(engine, journal, state, registry, phase="PRE_RESET_SNAPSHOT")
    # Objetos nuevos, no hidratación desde JSON ni restauración de referencias.
    new_engine, new_journal = create_session(), ObservationJournal()
    new_engine.bind_journal(new_journal.session_id)
    new_engine.select(1, 5)
    new_registry = LifecycleRegistry(new_engine.session_id, folder / "events")
    new_provider = create_runtime()
    new_provider.bind_lifecycle(new_registry.bind(1, 5))
    new_state = {}; bind_pair_context(new_state, new_engine.session_id, 1, 5)
    new_state["h4_runtime"] = new_provider
    after_reset = build_session_export(new_engine, new_journal, new_state, new_registry, [archived])
    for name, packet in (("current.json", current), ("rollback.json", rolled_back), ("after_reset.json", after_reset)):
        assert verify_session_export(packet)
        with (folder / name).open("x", encoding="utf-8") as handle:
            json.dump(packet, handle, ensure_ascii=False, allow_nan=False, indent=2)
    assert new_provider.get_active_model() is None
    summary = dict(folder=str(folder), engine_session_id=engine.session_id, journal_session_id=journal.session_id,
        new_engine_session_id=new_engine.session_id, closed_count=len(current["records"]),
        observed_sources=[r["source"] for r in current["extensions"]["h4_traceability"]["observations"]],
        seed=current["extensions"]["h4_traceability"]["engine"]["generator_seed"],
        final_active=None, trained_models=0, schema_version="h4-session-1", extension_version="h4-traceability-1")
    with (folder / "summary.json").open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    run(parser.parse_args().output)
