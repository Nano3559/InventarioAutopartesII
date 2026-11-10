"""Tarea 11: ejecución explícita autorizada; no forma parte de test discovery.

Promueve V1 real en memoria, valida Streamlit y revierte al finalizar.
No entrena ni calcula métricas TEST. Evidencias fuera de reports congelados.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid
from unittest.mock import patch

from sklearn.ensemble import RandomForestRegressor
from streamlit.testing.v1 import AppTest
from demand_runtime import create_runtime, V1_BINARY_SHA256, V1_NORMALIZED_SHA256
from simulator_inputs import HERE, FEATURE_NAMES, SCENARIOS, content_sha256
from ui_runtime import model_info

ROOT = HERE.parent.parent
OUT = ROOT / "docs/H4/tareas_erika/tarea_11/evidence"


def button(app, label):
    return next(b for b in app.button if b.label == label)


def run():
    OUT.mkdir(exist_ok=True)
    baseline = json.loads((ROOT / "docs/H4/tareas_erika/tarea_10/evidence/integrity_before.json").read_text())
    before = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in baseline}
    assert before == baseline, "Integridad previa fallida: no activar"
    data = HERE / "data/escenarios_v1_1"
    manifest = json.loads((data / "manifest.json").read_text())
    assert all(content_sha256((data / n).read_bytes()) == h for n, h in manifest["hashes"].items())
    selection = json.loads((HERE / "reports/v1_selection_manifest.json").read_text())
    test = json.loads((HERE / "reports/v1_test_evaluation.json").read_text())
    assert test["status"] == "TEST_EVALUATED_COMPLETED"
    assert test["selection_id"] == selection["selection_id"]
    assert test["artifact"]["sha256"] == V1_NORMALIZED_SHA256
    runtime = create_runtime()
    # Verificar compatibilidad e hiperparámetros antes de promover.
    _, estimator = runtime._load_verified(HERE / "models/random_forest_candidate.joblib",
                                          V1_BINARY_SHA256, V1_NORMALIZED_SHA256, "V1")
    assert all(estimator.get_params()[k] == v for k, v in selection["hyperparameters"].items())
    result = dict(activation_id="ACT-V1-" + uuid.uuid4().hex,
                  date_utc=datetime.now(timezone.utc).isoformat(),
                  selection_id=selection["selection_id"], before=runtime.get_active_model(),
                  scope="SESSION_MEMORY_ONLY", protected_before=before, scenarios=[])
    def checkpoint():
        (OUT / "activation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    reason = "Tarea 11: promoción real autorizada por el usuario; validación controlada AppTest"
    try:
        with patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("FIT PROHIBIDO")) as fit:
            result["promoted"] = runtime.promote_v1(reason)
            model_info(result["promoted"])
            result["events"] = runtime.events
            checkpoint()
            app = AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=30)
            app.session_state["h4_runtime"] = runtime
            app.run()
            assert not app.exception
            assert app.session_state["demand_session"].status()["open_month"] == "2026-10"
            with patch.object(runtime, "predict", wraps=runtime.predict) as predict:
                button(app, "PREDECIR").click().run()
                assert not app.exception and predict.call_count == 1
                features = predict.call_args.args[0]
                assert tuple(features) == FEATURE_NAMES
                journal = app.session_state["observation_journal"]
                forecast = next(iter(journal.pending.values()))
                assert forecast.prediction is not None
                assert forecast.model.artifact_hash == V1_BINARY_SHA256
                app.run()
                assert predict.call_count == 1 and len(journal.pending) == 1
                button(app, "PREDECIR").click().run()
                assert predict.call_count == 2 and len(journal.pending) == 1
                forecast = next(iter(journal.pending.values()))
                result["example"] = asdict(forecast)
                result["example_features"] = features
                result["no_automatic_or_duplicate_forecast"] = True
            button(app, "GENERAR SIGUIENTE MES").click().run()
            observed = app.session_state["demand_session"].pending_observed()
            assert observed is not None
            button(app, "AVANZAR MES").click().run()
            assert not app.exception
            assert app.session_state["demand_session"].status()["open_month"] == "2026-11"
            assert len(journal.closed) == 1
            closed = journal.closed[forecast.key]
            result["simulated_observed"] = observed
            result["closed"] = asdict(closed)
            result["rollback"] = runtime.rollback("Fin de validación principal: restaurar ausencia de ACTIVE")
            assert runtime.get_active_model() is None and journal.closed[forecast.key] == closed
            result["events"] = runtime.events
            button(app, "RESTABLECER EDICIÓN").click().run()
            assert not app.exception and app.session_state["h4_runtime"] is not runtime
            assert app.session_state["h4_runtime"].get_active_model() is None
            assert not app.session_state["observation_journal"].closed
            result["reset_inactive"] = True
            # Sesiones separadas para cada escenario; promociones reales locales.
            for scenario in SCENARIOS:
                provider = create_runtime()
                provider.promote_v1(reason + ": " + scenario)
                try:
                    view = AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=30)
                    view.session_state["h4_runtime"] = provider
                    view.run()
                    view.selectbox[3].set_value(scenario).run()
                    assert not view.exception
                    assert view.session_state["demand_session"].status()["scenario"] == scenario
                    if scenario == "PRODUCTO NUEVO":
                        assert button(view, "PREDECIR").disabled
                        button(view, "REGISTRAR ABSTENCIÓN").click().run()
                    else:
                        button(view, "PREDECIR").click().run()
                    row = next(iter(view.session_state["observation_journal"].pending.values()))
                    if scenario == "PRODUCTO NUEVO":
                        assert row.prediction is None and row.reason.startswith("HISTORIAL INSUFICIENTE:")
                        result["abstention"] = asdict(row)
                    else:
                        assert row.prediction is not None and row.model.artifact_hash == V1_BINARY_SHA256
                    button(view, "GENERAR SIGUIENTE MES").click().run()
                    button(view, "AVANZAR MES").click().run()
                    assert not view.exception
                    assert view.session_state["demand_session"].status()["open_month"] == "2026-11"
                    result["scenarios"].append(dict(scenario=scenario, forecast=asdict(row), events=provider.events))
                finally:
                    provider.rollback("Cerrar sesión aislada de escenario")
                    if result["scenarios"] and result["scenarios"][-1]["scenario"] == scenario:
                        result["scenarios"][-1]["events"] = provider.events
            fit.assert_not_called()
            result["fit_calls"] = fit.call_count
            result["status"] = "VALIDATED_AND_ROLLED_BACK"
    finally:
        if runtime.get_active_model() is not None:
            runtime.rollback("Cierre seguro de validación")
        result["after"] = runtime.get_active_model()
        result["protected_after"] = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in baseline}
        result["integrity_unchanged"] = before == result["protected_after"]
        checkpoint()
    assert result["integrity_unchanged"]
    print(json.dumps(dict(status=result["status"], activation_id=result["activation_id"],
                          prediction=result["example"]["prediction"], scenarios=len(result["scenarios"]))))


if __name__ == "__main__":
    run()
