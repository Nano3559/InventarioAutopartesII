"""Auditoría T21 adicional: AppTest normal, datos nuevos, sin ningún fit.

No pertenece al discovery ni modifica la suite. Todos los eventos/decisiones
de estas sesiones son temporales; solo se conserva evidencia resumida aquí.
"""
from copy import deepcopy
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "ml/demand/run_tests.py").is_file())
sys.path.insert(0, str(ROOT / "ml/demand"))
from streamlit.testing.v1 import AppTest
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from ml_pipeline import TrainStandardizer
from model_comparison import ComparisonSession as RealComparisonSession
from demand_runtime import V1_BINARY_SHA256
from simulator_inputs import HERE, SCENARIOS, FEATURE_NAMES, InputError, offset_month
from session_export import verify_session_export

OUT = Path(__file__).resolve().parent
if "--output-dir" in sys.argv:
    OUT = Path(sys.argv[sys.argv.index("--output-dir") + 1]).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
if any((OUT / name).exists() for name in ("flows.json", "scenario_progress.json")):
    raise SystemExit("Conservar la evidencia anterior: indique --output-dir con un destino nuevo.")


def button(app, label):
    return next(b for b in app.button if b.label == label)


def checked(app):
    assert not app.exception, [e.message for e in app.exception]
    return app


def new_app():
    return checked(AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=45).run())


def activate(app, reason):
    app.text_input(key="v1_activation_reason").set_value(reason).run()
    button(app, "ACTIVAR V1 CONGELADA").click().run()
    checked(app)
    provider = app.session_state["h4_runtime"]
    assert provider.get_active_model()["artifact_hash"] == V1_BINARY_SHA256
    return provider


def emit(app):
    if button(app, "PREDECIR").disabled:
        button(app, "REGISTRAR ABSTENCIÓN").click().run()
    else:
        button(app, "PREDECIR").click().run()
    return checked(app)


def scenario_case(scenario):
    app = new_app()
    app.selectbox(key="editor_1_5_2026-10_scenario").select(scenario).run()
    checked(app)
    engine = app.session_state["demand_session"]
    original_rng = engine._pairs[(1, 5)].rng.getstate()
    provider = activate(app, "T21: activación explícita V1 · " + scenario)
    active = provider.get_active_model()
    samples = []
    for _ in range(6):
        state = engine.status()
        month = state["open_month"]
        assert month >= "2026-10"
        emit(app)
        journal = app.session_state["observation_journal"]
        key = (1, 5, month)
        forecast = journal.pending[key]
        frozen = deepcopy(asdict(forecast))
        if scenario == "PRODUCTO NUEVO":
            assert forecast.prediction is None
        else:
            assert forecast.prediction is not None and forecast.prediction >= 0
            assert forecast.model.artifact_hash == V1_BINARY_SHA256
            assert len(forecast.features) == 5
            angle = 2 * math.pi * (int(month[5:]) - 1) / 12
            assert abs(forecast.features[3] - math.sin(angle)) < 1e-10
            assert abs(forecast.features[4] - math.cos(angle)) < 1e-10
        button(app, "GENERAR SIGUIENTE MES").click().run()
        checked(app)
        observed = engine.pending_observed()
        assert type(observed) is int and observed >= 0
        assert engine.observation_source() == "GENERATED"
        stockout = deepcopy(engine.generation_detail())
        if scenario == "STOCKOUT":
            assert observed <= stockout["availability"] and observed <= stockout["latent"]
        assert engine.generate_observed() == observed  # Idempotente, no otro draw.
        button(app, "AVANZAR MES").click().run()
        checked(app)
        assert engine.status()["open_month"] == offset_month(month, 1)
        assert journal.closed[key].observed == observed
        assert asdict(journal.closed[key].forecast) == frozen
        assert engine._pairs[(1, 5)].closed[month] == observed
        assert engine._pairs[(1, 5)].closed_sources[month] == "GENERATED"
        assert engine.recent_history()[-1] == (month, observed)
        assert provider.get_active_model() == active
        packet = app.session_state["last_session_export"]
        assert verify_session_export(packet)
        assert len(packet["records"]) == len(samples) + 1
        samples.append(dict(month=month, forecast=frozen, observed=observed,
            new_open_month=engine.status()["open_month"], next_lags=engine.lags(),
            stockout_internal_metadata=stockout, export_valid=True))

    isolation = None
    archived_comparison = None
    if scenario == "NORMAL":
        frozen_closed = deepcopy(app.session_state["observation_journal"].closed)
        app.selectbox(key="product").select(2).run(); checked(app)
        assert app.session_state["h4_runtime"].get_active_model() is None
        other_provider = activate(app, "T21: activar exclusivamente par 2/5")
        assert other_provider is not provider
        app.text_input(key="candidate_decision_reason").set_value("T21: rollback solo 2/5").run()
        button(app, "ROLLBACK LOCAL").click().run(); checked(app)
        assert other_provider.get_active_model() is None
        app.selectbox(key="product").select(1).run(); checked(app)
        assert app.session_state["h4_runtime"] is provider
        assert provider.get_active_model() == active
        assert app.session_state["observation_journal"].closed == frozen_closed
        other_app = new_app()
        assert other_app.session_state["h4_runtime"].get_active_model() is None
        assert not other_app.session_state["observation_journal"].closed
        isolation = dict(pair_switch=True, identity_recovered=True, pair_local_rollback=True,
                         history_immutable=True, other_session_inactive=True)
        # Caso archivado independiente: sus tres filas de 2027 NO son TEST inicial
        # ni observaciones producidas por los seis meses de esta sesión.
        button(app, "COMPARAR CANDIDATE").click().run(); checked(app)
        result = app.session_state["candidate_comparison_result"]
        assert result["n_comparison"] == 3 and result["eligibility"] == "INSUFFICIENT_EVIDENCE"
        assert not result["promotion_allowed"]
        assert button(app, "PROMOVER CANDIDATE").disabled
        app.text_input(key="candidate_decision_reason").set_value("T21: evidencia archivada insuficiente").run()
        button(app, "RECHAZAR CANDIDATE").click().run(); checked(app)
        assert provider.get_active_model() == active
        try:
            provider.promote_candidate({"decision": "APROBADO", "run_id": result["run_id"]})
        except InputError:
            pass
        else:
            raise AssertionError("La promoción real debe permanecer bloqueada")
        archived_comparison = dict(source="ARCHIVED_INDEPENDENT_DEMO", run_id=result["run_id"],
            period=result["period"], n=result["n_comparison"], eligibility=result["eligibility"],
            decision=app.session_state["candidate_rejection"]["decision"],
            source_session_id=result["source_session_id"], promotion_blocked=True)

    registry = app.session_state["lifecycle_registry"]
    assert registry.verify_sources()
    events_before_reset = registry.records()
    old_engine_id = engine.session_id
    button(app, "RESTABLECER EDICIÓN").click().run(); checked(app)
    fresh_engine = app.session_state["demand_session"]
    fresh_provider = app.session_state["h4_runtime"]
    assert fresh_provider is not provider and fresh_provider.get_active_model() is None
    assert fresh_engine.session_id != old_engine_id
    assert fresh_engine.status()["scenario"] == "NORMAL"
    assert fresh_engine.status()["seed"] == 42
    assert fresh_engine.status()["open_month"] == "2026-10"
    assert fresh_engine._pairs[(1, 5)].rng.getstate() == original_rng
    assert not app.session_state["observation_journal"].closed
    assert registry.records()[-1]["type"] == "RESET"
    export = app.session_state["last_session_export"]
    assert verify_session_export(export)
    assert len(export["extensions"]["h4_traceability"]["prior_sessions"]) == 1
    assert any(r["type"] == "V1_AVAILABLE" for r in app.session_state["lifecycle_registry"].records())
    # Mismo escenario y seed tras reset: mismo primer resultado, sin activar V1.
    app.selectbox(key="editor_1_5_2026-10_scenario").select(scenario).run()
    emit(app)
    button(app, "GENERAR SIGUIENTE MES").click().run(); checked(app)
    assert app.session_state["demand_session"].pending_observed() == samples[0]["observed"]
    return dict(scenario=scenario, closed_months=6, samples=samples, isolation=isolation,
        archived_comparison=archived_comparison, reset=dict(initial_clock=True, initial_seed=True,
            initial_scenario=True, new_session=True, v1_available_but_inactive=True,
            history_archived=True, rng_restored=True, first_observed_reproduced=True),
        lifecycle_events_before_reset=events_before_reset, status="PASSED")


def incomplete_case():
    app = new_app(); emit(app)
    engine = app.session_state["demand_session"]
    journal = app.session_state["observation_journal"]
    app.number_input(key="observed_1_5_2026-10").set_value(10).run(); checked(app)
    app.checkbox(key="closed_1_5_2026-10").uncheck().run(); checked(app)
    assert button(app, "REGISTRAR OBSERVADO").disabled
    assert button(app, "AVANZAR MES").disabled
    before = deepcopy(engine.status()); closed_before = deepcopy(journal.closed)
    rng_before = engine._pairs[(1, 5)].rng.getstate()
    try:
        engine.close_month(complete=False)
    except InputError:
        pass
    else:
        raise AssertionError("Un mes incompleto no debe cerrar")
    app.run(); checked(app)
    assert engine.status() == before and journal.closed == closed_before
    assert engine._pairs[(1, 5)].rng.getstate() == rng_before
    app.checkbox(key="closed_1_5_2026-10").check().run()
    button(app, "AVANZAR MES").click().run(); checked(app)
    assert engine.status()["open_month"] == "2026-11"
    assert journal.closed[(1, 5, "2026-10")].observed == 10
    return dict(incomplete_rejected=True, clock_history_rng_unchanged=True,
                complete_allowed=True, manual_observed=10, status="PASSED")


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix="h4-t21-audit-") as folder, \
         patch("lifecycle_registry.DEFAULT_ROOT", Path(folder) / "events"), \
         patch("model_comparison.ComparisonSession", side_effect=lambda sid: RealComparisonSession(sid, Path(folder)/"decisions")), \
         patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("T21 no permite fit")) as rf_fit, \
         patch.object(LinearRegression, "fit", side_effect=AssertionError("T21 no permite fit")) as lr_fit, \
         patch.object(TrainStandardizer, "fit", side_effect=AssertionError("T21 no permite fit")) as scaler_fit:
        for scenario in SCENARIOS:
            results.append(scenario_case(scenario))
            (OUT / "scenario_progress.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(scenario + ": 6 cierres, reset y reproducción OK", flush=True)
        manual = incomplete_case()
        result = dict(status="PASSED", scenarios=results, scenario_closed_months=48,
            additional_manual_case=manual, rf_fit_calls=rf_fit.call_count,
            lr_fit_calls=lr_fit.call_count, scaler_fit_calls=scaler_fit.call_count,
            new_models_created=0, official_test_evaluated=False, visual_review="NOT_PERFORMED")
        assert rf_fit.call_count == lr_fit.call_count == scaler_fit.call_count == 0
        (OUT / "flows.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("T21 flows PASSED: 48 cierres, 8 escenarios, caso manual y cero fit", flush=True)


if __name__ == "__main__":
    main()
