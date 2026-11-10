"""Auditoría optativa T14: AppTest real, candidatos temporales, sin correcciones.

No modifica modelos o datasets oficiales. Produce evidencia fuera de ellos.
La revisión visual se realiza por separado; AppTest no genera capturas.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import traceback
from unittest.mock import patch

from sklearn.ensemble import RandomForestRegressor
from streamlit.testing.v1 import AppTest
from demand_runtime import create_runtime, V1_BINARY_SHA256
from demand_engine import create_session
from retraining import RetrainingSession
from model_comparison import ComparisonSession
from simulator_inputs import HERE, SCENARIOS, InputError, load_reference


def button(app, label):
    return next(b for b in app.button if b.label == label)


def checked(app):
    assert not app.exception, [e.message for e in app.exception]
    return app


def app_with(runtime=None):
    app = AppTest.from_file(str(HERE/"streamlit_app.py"), default_timeout=45)
    if runtime is not None:
        app.session_state["h4_runtime"] = runtime
    return checked(app.run())


def emit_and_close(app, index):
    engine = app.session_state["demand_session"]
    journal = app.session_state["observation_journal"]
    state = engine.status()
    key = (state["product_id"], state["location_id"], state["open_month"])
    action = "REGISTRAR ABSTENCIÓN" if button(app, "PREDECIR").disabled else "PREDECIR"
    checked(button(app, action).click().run())
    forecast = journal.pending[key]
    if action == "PREDECIR":
        assert forecast.prediction is not None and forecast.model.artifact_hash == V1_BINARY_SHA256
    checked(button(app, "GENERAR SIGUIENTE MES").click().run())
    observed = engine.pending_observed()
    assert observed is not None
    assert button(app, "GENERAR SIGUIENTE MES").disabled
    if index % 2 == 0:
        app.checkbox(key=f"closed_{key[0]}_{key[1]}_{key[2]}").check().run()
        checked(button(app, "REGISTRAR OBSERVADO").click().run())
        assert key in journal.closed and engine.is_closed(key[2])
    checked(button(app, "AVANZAR MES").click().run())
    assert journal.closed[key].observed == observed
    assert journal.closed[key].forecast == forecast
    return dict(forecast=asdict(forecast), observed=observed,
                closed_at=journal.closed[key].observed_at,
                next_month=engine.status()["open_month"], next_lags=engine.lags())


def main_flow(tmp, gate):
    runtime = create_runtime()
    app = app_with(runtime)
    assert button(app, "PREDECIR").disabled
    checked(app.selectbox[0].set_value(2).run())
    checked(app.selectbox[1].set_value(6).run())
    assert app.session_state["demand_session"].status()["product_id"] == 2
    checked(app.selectbox[0].set_value(1).run())
    checked(app.selectbox[1].set_value(5).run())
    checked(app.selectbox[3].set_value("NORMAL").run())
    for suffix, value in (("lag3", 8), ("lag2", 10), ("lag1", 12)):
        checked(app.number_input(key=f"editor_1_5_2026-10_{suffix}").set_value(value).run())
    checked(button(app, "VALIDAR ENTRADAS").click().run())
    runtime.promote_v1("Tarea 14: validación integral temporal autorizada")
    checked(app.run())
    engine = app.session_state["demand_session"]
    service = RetrainingSession(engine.session_id, Path(tmp)/"candidates")
    decisions = ComparisonSession(engine.session_id, Path(tmp)/"decisions")
    app.session_state["retraining_session"] = service
    app.session_state["candidate_comparison_session"] = decisions
    try:
        months = [emit_and_close(app, i) for i in range(12)]
        assert engine.status()["open_month"] == "2027-10"
        journal = app.session_state["observation_journal"]
        frozen = dict(journal.closed)
        gate["training_allowed"] = True
        try:
            checked(button(app, "ENSAYAR REENTRENAMIENTO").click().run())
        finally:
            gate["training_allowed"] = False
        run = app.session_state["retraining_result"]
        assert run["n_train"] == 6 and run["n_reserved"] == 3
        assert runtime.get_active_model()["artifact_hash"] == V1_BINARY_SHA256
        checked(button(app, "COMPARAR CANDIDATE").click().run())
        comparison = app.session_state["candidate_comparison_result"]
        assert comparison["eligibility"] == "INSUFFICIENT_EVIDENCE"
        assert button(app, "PROMOVER CANDIDATE").disabled
        checked(app.text_input(key="candidate_decision_reason").set_value("Evidencia insuficiente en la validación integral").run())
        checked(button(app, "RECHAZAR CANDIDATE").click().run())
        rejection = app.session_state["candidate_rejection"]
        assert rejection["decision"] == "REJECTED_FOR_PROMOTION"
        checked(button(app, "ROLLBACK LOCAL").click().run())
        assert runtime.get_active_model() is None and journal.closed == frozen
        other = app_with()
        assert not other.session_state["observation_journal"].closed
        assert other.session_state["h4_runtime"].get_active_model() is None
        data = json.loads((Path(run["folder"])/"incremental.json").read_text(encoding="utf-8"))
        result = dict(status="PASS", months=months, candidate=run,
                      incremental_snapshot=data, comparison=comparison, rejection=rejection,
                      runtime_events=runtime.events, closed_count=len(journal.closed),
                      isolated_other_session=True, artifacts_scope="TEMPORARY_DIRECTORY")
        checked(button(app, "RESTABLECER EDICIÓN").click().run())
        assert not app.session_state["observation_journal"].closed
        assert app.session_state["h4_runtime"].get_active_model() is None
        result["reset_verified"] = True
        return result
    finally:
        if runtime.get_active_model() is not None:
            runtime.rollback("Cierre seguro de validación integral")


def scenarios():
    results = []
    for scenario in SCENARIOS:
        runtime = create_runtime()
        runtime.promote_v1("Tarea 14: escenario aislado " + scenario)
        try:
            app = app_with(runtime)
            checked(app.selectbox[3].set_value(scenario).run())
            rows = [emit_and_close(app, i) for i in range(6)]
            results.append(dict(scenario=scenario, status="PASS", months=rows))
        except Exception:
            results.append(dict(scenario=scenario, status="FAIL", error=traceback.format_exc()))
        finally:
            runtime.rollback("Fin del escenario aislado")
    return results


def diagnostics():
    """Observaciones de diferencias con la guía; no modifica la implementación."""
    reference = load_reference()
    a, b = create_session(reference), create_session(reference)
    a.select(1, 5)
    b.select(1, 5)
    a_values, b_values = [], []
    for _ in range(6):
        a_values.append(a.generate_observed())
        a.close_month()
        a.advance_month()
        b.select(2, 5)
        b.generate_observed()
        b.close_month()
        b.advance_month()
        b.select(1, 5)
        b_values.append(b.generate_observed())
        b.close_month()
        b.advance_month()
    app = app_with()
    initial = dict(active=app.session_state["h4_runtime"].get_active_model(),
                   predict_disabled=button(app, "PREDECIR").disabled,
                   buttons=[b.label for b in app.button])
    checked(button(app, "REGISTRAR ABSTENCIÓN").click().run())
    checked(app.number_input(key="observed_1_5_2026-10").set_value(10).run())
    complete = app.checkbox(key="closed_1_5_2026-10").value
    checked(button(app, "AVANZAR MES").click().run())
    return dict(initial_ui=initial,
                per_pair_rng=dict(pair1_alone=a_values, pair1_with_pair2_interleaving=b_values,
                                  independent=a_values == b_values),
                manual_close=dict(complete_checkbox=complete,
                                  closed_without_confirmation=(1, 5, "2026-10") in app.session_state["observation_journal"].closed))


def run():
    out = HERE.parent.parent/"docs/H4/tareas_erika/tarea_14/evidence"
    out.mkdir(exist_ok=True)
    result = dict(timestamp=datetime.now(timezone.utc).isoformat(), visual_review="NOT_PERFORMED_BROWSER_POLICY_STOP")
    gate = dict(training_allowed=False)
    fit_calls = []
    forbidden_fit_attempts = []
    original_fit = RandomForestRegressor.fit
    def checked_fit(model, X, y, *args, **kwargs):
        if not gate["training_allowed"]:
            forbidden_fit_attempts.append(dict(n_rows=len(X), columns=list(X.columns)))
            raise AssertionError("fit fuera del ensayo explícito de reentrenamiento")
        fit_calls.append(dict(n_rows=len(X), columns=list(X.columns), targets=list(map(int, y))))
        return original_fit(model, X, y, *args, **kwargs)
    with patch.object(RandomForestRegressor, "fit", new=checked_fit):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                result["main_flow"] = main_flow(tmp, gate)
            except Exception:
                result["main_flow"] = dict(status="FAIL", error=traceback.format_exc())
        result["scenarios"] = scenarios()
        try:
            result["diagnostics"] = diagnostics()
        except Exception:
            result["diagnostics"] = dict(status="FAIL", error=traceback.format_exc())
    result["fit_calls"] = fit_calls
    result["inference_fit_calls"] = len(forbidden_fit_attempts)
    result["forbidden_fit_attempts"] = forbidden_fit_attempts
    result["status"] = "PASS" if result["main_flow"]["status"] == "PASS" and all(s["status"] == "PASS" for s in result["scenarios"]) and not forbidden_fit_attempts else "FAIL"
    (out/"integral.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(dict(status=result["status"], main=result["main_flow"]["status"], scenarios=[(s["scenario"],s["status"]) for s in result["scenarios"]], fit_calls=fit_calls), ensure_ascii=False))


if __name__ == "__main__":
    run()
