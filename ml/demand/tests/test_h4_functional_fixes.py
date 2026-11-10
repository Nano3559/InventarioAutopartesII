"""T15: regresiones de D01/D02/D03 sin reentrenar V1 ni evaluar TEST oficial."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from sklearn.ensemble import RandomForestRegressor
from streamlit.testing.v1 import AppTest

from demand_engine import create_session
from demand_runtime import create_runtime, V1_BINARY_SHA256
from simulator_inputs import HERE, SCENARIOS, InputError, load_reference
from ui_runtime import ObservationJournal, issue_forecast
from ui_panels import close_current_month


def sequence(session, scenario, pair=(1, 5), interleave=False, count=12):
    session.select(*pair)
    session.apply_scenario(scenario)
    result = []
    for _ in range(count):
        session.select(*pair)
        value = session.generate_observed()
        assert session.generate_observed() == value
        result.append(value)
        session.close_month()
        session.advance_month()
        if interleave:
            session.select(2, 6)
            session.generate_observed()
            session.close_month()
            session.advance_month()
    return result


class PairRandomnessTests(unittest.TestCase):
    def test_interleaving_other_pair_does_not_change_any_scenario(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                single = sequence(create_session(), scenario)
                interleaved = sequence(create_session(), scenario, interleave=True)
                self.assertEqual(single, interleaved)

    def test_selection_order_does_not_change_pair_stream(self):
        first, second = create_session(), create_session()
        first.select(2, 6)
        first.generate_observed()
        self.assertEqual(sequence(first, "NORMAL"), sequence(second, "NORMAL"))

    def test_seed_and_pair_determine_distinct_stable_streams(self):
        a, b = create_session(seed=42), create_session(seed=42)
        self.assertNotEqual(a.session_id, b.session_id)
        self.assertEqual(sequence(a, "NORMAL"), sequence(b, "NORMAL"))
        self.assertNotEqual(sequence(create_session(seed=42), "NORMAL"), sequence(create_session(seed=43), "NORMAL"))
        x, y = create_session(), create_session()
        x.select(1, 5); y.select(2, 6)
        self.assertIsNot(x._pairs[(1, 5)].rng, y._pairs[(2, 6)].rng)
        self.assertNotEqual(x._pairs[(1, 5)].rng.getstate(), y._pairs[(2, 6)].rng.getstate())

    def test_reset_restores_all_pair_sequences(self):
        session = create_session()
        first = sequence(session, "NORMAL", interleave=True)
        session.reset()
        self.assertEqual(first, sequence(session, "NORMAL", interleave=True))

    def test_generation_and_closing_do_not_mutate_other_pair(self):
        session = create_session()
        session.select(1, 5)
        saved = deepcopy(session._pairs[(1, 5)])
        session.select(2, 6)
        session.generate_observed(); session.close_month(); session.advance_month()
        current = session._pairs[(1, 5)]
        self.assertEqual(current.rng.getstate(), saved.rng.getstate())
        self.assertEqual(current.closed, saved.closed)
        self.assertEqual(current.open_month, saved.open_month)


class MonthClosureTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_session()
        self.engine.select(1, 5)

    def test_incomplete_close_rejects_without_mutating_state_or_rng(self):
        self.engine.set_manual_observed(10)
        before = deepcopy(self.engine.status())
        rng_before = self.engine._pairs[(1, 5)].rng.getstate()
        for incomplete in (False, None, 1, "true"):
            with self.subTest(complete=incomplete):
                with self.assertRaisesRegex(InputError, "MES INCOMPLETO"):
                    self.engine.close_month(complete=incomplete)
                self.assertEqual(self.engine.status(), before)
                self.assertEqual(self.engine._pairs[(1, 5)].rng.getstate(), rng_before)
                with self.assertRaises(InputError):
                    self.engine.advance_month()

    def test_missing_observed_never_fabricates_zero(self):
        with self.assertRaises(InputError):
            self.engine.close_month(complete=True)
        self.assertIsNone(self.engine.pending_observed())
        self.assertEqual(self.engine.closed_months(), ())
        self.assertEqual(self.engine.status()["open_month"], "2026-10")

    def test_complete_manual_zero_is_valid_and_advance_is_explicit(self):
        self.engine.set_manual_observed(0)
        self.engine.close_month(complete=True)
        self.assertEqual(self.engine.status()["open_month"], "2026-10")
        self.engine.advance_month()
        self.assertEqual(self.engine.status()["open_month"], "2026-11")
        self.assertEqual(dict(self.engine.history_series())["2026-10"], 0)

    def test_new_product_can_close_observed_despite_inference_abstention(self):
        self.engine.apply_scenario("PRODUCTO NUEVO")
        self.assertEqual(self.engine.history_status(), "HISTORIAL INSUFICIENTE")
        self.engine.set_manual_observed(7)
        self.engine.close_month(complete=True)
        self.engine.advance_month()
        self.assertEqual(dict(self.engine.history_series()), {"2026-10": 7})

    def test_journal_contradiction_rejects_before_engine_write(self):
        store = ObservationJournal()
        forecast = issue_forecast(load_reference(), 1, 5, "2026-10", None, None)
        store.issue(forecast)
        store.reveal(forecast.key, 8)
        self.engine.set_manual_observed(9)
        before = deepcopy(self.engine.status())
        with self.assertRaises(InputError):
            close_current_month(self.engine, store, forecast.key, complete=True)
        self.assertEqual(self.engine.status(), before)
        self.assertFalse(store.closed)

    def test_missing_emission_rejects_before_engine_write(self):
        self.engine.set_manual_observed(9)
        with self.assertRaises(InputError):
            close_current_month(self.engine, ObservationJournal(), (1, 5, "2026-10"), complete=True)
        self.assertFalse(self.engine.is_closed("2026-10"))
        self.assertEqual(self.engine.pending_observed(), 9)


class NormalStreamlitFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protected = json.loads((HERE.parent.parent/"docs/H4/tareas_erika/tarea_15/evidence/integrity_before.json").read_text())

    @classmethod
    def tearDownClass(cls):
        for name, expected in cls.protected.items():
            if hashlib.sha256((HERE.parent.parent/name).read_bytes()).hexdigest() != expected:
                raise AssertionError("Archivo protegido alterado: "+name)

    def app(self):
        result = AppTest.from_file(str(HERE/"streamlit_app.py"), default_timeout=30).run()
        self.assertFalse(result.exception)
        return result

    def button(self, app, label):
        return next(b for b in app.button if b.label == label)

    def activate(self, app):
        app.text_input(key="v1_activation_reason").set_value("T15: activación explícita de la referencia V1").run()
        self.button(app, "ACTIVAR V1 CONGELADA").click().run()
        self.assertFalse(app.exception)
        return app.session_state["h4_runtime"]

    def manual_pending(self):
        app = self.app()
        self.button(app, "REGISTRAR ABSTENCIÓN").click().run()
        app.number_input(key="observed_1_5_2026-10").set_value(10).run()
        return app

    def test_manual_incomplete_disables_both_close_routes(self):
        app = self.manual_pending()
        engine = app.session_state["demand_session"]
        journal = app.session_state["observation_journal"]
        self.assertFalse(app.checkbox(key="closed_1_5_2026-10").value)
        self.assertTrue(self.button(app, "REGISTRAR OBSERVADO").disabled)
        self.assertTrue(self.button(app, "AVANZAR MES").disabled)
        self.assertTrue(any("MES INCOMPLETO" in m.value for m in app.info))
        app.run()
        self.assertEqual(engine.status()["open_month"], "2026-10")
        self.assertEqual(engine.closed_months(), ())
        self.assertFalse(journal.closed)
        self.assertEqual(journal.revealed[(1, 5, "2026-10")], 10)

    def test_manual_confirmation_allows_close_and_advance(self):
        app = self.manual_pending()
        app.checkbox(key="closed_1_5_2026-10").check().run()
        self.assertFalse(self.button(app, "AVANZAR MES").disabled)
        self.button(app, "AVANZAR MES").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["demand_session"].status()["open_month"], "2026-11")
        self.assertEqual(app.session_state["observation_journal"].closed[(1, 5, "2026-10")].observed, 10)

    def test_explicit_manual_register_closes_without_advancing(self):
        app = self.manual_pending()
        app.checkbox(key="closed_1_5_2026-10").check().run()
        self.button(app, "REGISTRAR OBSERVADO").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.session_state["demand_session"].is_closed("2026-10"))
        self.assertEqual(app.session_state["demand_session"].status()["open_month"], "2026-10")
        self.assertEqual(app.number_input(key="closed_observed_1_5_2026-10").value, 10)
        self.assertTrue(app.number_input(key="closed_observed_1_5_2026-10").disabled)

    def test_generated_month_is_complete_without_manual_confirmation(self):
        app = self.app()
        self.button(app, "REGISTRAR ABSTENCIÓN").click().run()
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        self.assertEqual(app.session_state["demand_session"].observation_source(), "GENERATED")
        self.assertFalse(self.button(app, "AVANZAR MES").disabled)
        self.button(app, "AVANZAR MES").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["demand_session"].status()["open_month"], "2026-11")

    def test_normal_v1_activation_real_inference_and_rollback(self):
        with patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("fit prohibido")) as fit:
            app = self.app()
            self.assertIsNone(app.session_state["h4_runtime"].get_active_model())
            self.assertTrue(self.button(app, "ACTIVAR V1 CONGELADA").disabled)
            runtime = self.activate(app)
            self.assertEqual(runtime.get_active_model()["artifact_hash"], V1_BINARY_SHA256)
            self.assertEqual(runtime.events[-1]["action"], "ACTIVATE_V1")
            self.assertTrue(self.button(app, "ACTIVAR V1 CONGELADA").disabled)
            self.button(app, "PREDECIR").click().run()
            self.assertFalse(app.exception)
            forecast = app.session_state["observation_journal"].pending[(1, 5, "2026-10")]
            self.assertIsInstance(forecast.prediction, float)
            self.button(app, "GENERAR SIGUIENTE MES").click().run()
            self.button(app, "AVANZAR MES").click().run()
            closed = deepcopy(app.session_state["observation_journal"].closed)
            app.text_input(key="candidate_decision_reason").set_value("Volver a SIN ACTIVE, T15").run()
            self.button(app, "ROLLBACK LOCAL").click().run()
            self.assertFalse(app.exception)
            self.assertIsNone(runtime.get_active_model())
            self.assertEqual(app.session_state["observation_journal"].closed, closed)
            self.assertTrue(self.button(app, "PREDECIR").disabled)
            self.assertTrue(self.button(app, "PROMOVER CANDIDATE").disabled)
            fit.assert_not_called()
            self.evidence = dict(activation=runtime.events[0], rollback=runtime.events[-1],
                                 forecast=forecast.__dict__, fit_calls=fit.call_count,
                                 closed_count=len(closed), final_active=runtime.get_active_model())

    def test_activation_is_local_and_reset_requires_new_action(self):
        app, other = self.app(), self.app()
        runtime = self.activate(app)
        self.assertIsNone(other.session_state["h4_runtime"].get_active_model())
        self.button(app, "RESTABLECER EDICIÓN").click().run()
        self.assertFalse(app.exception)
        self.assertIsNot(app.session_state["h4_runtime"], runtime)
        self.assertIsNone(app.session_state["h4_runtime"].get_active_model())
        self.assertEqual(app.text_input(key="v1_activation_reason").value, "")

    def test_v1_verification_failure_preserves_inactive_state(self):
        app = self.app()
        runtime = app.session_state["h4_runtime"]
        with patch.object(runtime, "_load_verified", side_effect=InputError("fixture de rechazo")):
            self.activate(app)
        self.assertIsNone(runtime.get_active_model())
        self.assertFalse(runtime.events)
        self.assertTrue(any("No se pudo verificar" in m.value for m in app.error))

    def test_imported_approval_cannot_change_candidate_promotion_policy(self):
        app = self.app()
        runtime = self.activate(app)
        active = runtime.get_active_model()
        with self.assertRaises(InputError):
            runtime.promote_candidate({"decision": "APROBADO", "PROMOVER": True})
        self.assertEqual(runtime.get_active_model(), active)
        self.assertTrue(self.button(app, "PROMOVER CANDIDATE").disabled)
