"""R21: referencias/candidatos por par, sin registro persistente R49/R52."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sklearn.ensemble import RandomForestRegressor
from streamlit.testing.v1 import AppTest

from demand_runtime import create_runtime, V1_BINARY_SHA256
from model_comparison import ComparisonSession
from pair_contexts import bind_pair_context, clear_pair_contexts
from retraining import RetrainingSession
from simulator_inputs import HERE, InputError
from .test_retraining import trajectory


class ContextBindingTests(unittest.TestCase):
    def test_pair_switch_restores_identity_and_candidate_decisions(self):
        state = {}
        bind_pair_context(state, "session", 1, 5)
        provider = create_runtime()
        run = {"run_id": "fixture", "product_id": 1, "location_id": 5}
        state.update(h4_runtime=provider, retraining_result=run,
                     candidate_comparison_result={"id": "comparison"},
                     candidate_rejection={"reason": "fixture"})
        bind_pair_context(state, "session", 2, 5)
        for key in ("h4_runtime", "retraining_result", "candidate_rejection", "candidate_comparison_result"):
            self.assertNotIn(key, state)
        bind_pair_context(state, "session", 1, 5)
        self.assertIs(state["h4_runtime"], provider)
        self.assertIs(state["retraining_result"], run)
        self.assertEqual(state["candidate_comparison_result"]["id"], "comparison")

    def test_new_session_owner_cannot_inherit_old_contexts(self):
        state = {}
        bind_pair_context(state, "old", 1, 5)
        state["h4_runtime"] = create_runtime()
        bind_pair_context(state, "new", 1, 5)
        self.assertNotIn("h4_runtime", state)
        self.assertEqual(list(state["pair_contexts"]), [(1, 5)])

    def test_reconnect_deletion_does_not_resurrect_saved_provider(self):
        state = {}
        bind_pair_context(state, "s", 1, 5)
        state["h4_runtime"] = create_runtime()
        bind_pair_context(state, "s", 2, 5)
        bind_pair_context(state, "s", 1, 5)
        del state["h4_runtime"]
        bind_pair_context(state, "s", 2, 5)
        bind_pair_context(state, "s", 1, 5)
        self.assertNotIn("h4_runtime", state)

    def test_clear_discards_all_references_without_touching_journal(self):
        state = {"observation_journal": object()}
        journal = state["observation_journal"]
        bind_pair_context(state, "s", 1, 5)
        state["h4_runtime"] = create_runtime()
        bind_pair_context(state, "s", 1, 6)
        clear_pair_contexts(state)
        self.assertEqual(state, {"observation_journal": journal})


class PairStreamlitTests(unittest.TestCase):
    def app(self):
        app = AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        return app

    def button(self, app, label):
        return next(b for b in app.button if b.label == label)

    def select(self, app, product=1, store=5):
        app.selectbox(key="product").select(product)
        app.selectbox(key="store").select(store).run()
        self.assertFalse(app.exception)

    def activate(self, app):
        app.text_input(key="v1_activation_reason").set_value("R21 acción explícita").run()
        self.button(app, "ACTIVAR V1 CONGELADA").click().run()
        self.assertFalse(app.exception)
        provider = app.session_state["h4_runtime"]
        self.assertEqual(provider.get_active_model()["artifact_hash"], V1_BINARY_SHA256)
        return provider

    def test_active_pair_switch_and_real_inference_without_fit(self):
        with patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("fit prohibido")) as fit:
            app = self.app()
            first = self.activate(app)
            self.button(app, "PREDECIR").click().run()
            journal = app.session_state["observation_journal"]
            pending = deepcopy(journal.pending)
            self.assertIsNotNone(pending[(1, 5, "2026-10")].prediction)
            for product, store in ((2, 5), (1, 6)):
                self.select(app, product, store)
                self.assertIsNone(app.session_state["h4_runtime"].get_active_model())
                self.assertTrue(self.button(app, "PREDECIR").disabled)
                self.assertTrue(self.button(app, "COMPARAR CANDIDATE").disabled)
            self.select(app)
            self.assertIs(app.session_state["h4_runtime"], first)
            self.assertEqual(journal.pending, pending)
            self.assertEqual(len(journal.pending), 1)  # cambiar de par no emite otra predicción
            fit.assert_not_called()

    def test_rollback_is_pair_local_and_closed_history_is_immutable(self):
        app = self.app()
        a = self.activate(app)
        self.button(app, "PREDECIR").click().run()
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        self.button(app, "AVANZAR MES").click().run()
        journal = app.session_state["observation_journal"]
        closed = deepcopy(journal.closed)
        engine = app.session_state["demand_session"]
        closures = deepcopy(engine._pairs[(1, 5)].closed)
        self.select(app, 2, 5)
        b = self.activate(app)
        app.text_input(key="candidate_decision_reason").set_value("Revertir solo B").run()
        self.button(app, "ROLLBACK LOCAL").click().run()
        self.assertFalse(app.exception)
        self.assertIsNone(b.get_active_model())
        self.select(app)
        self.assertIs(app.session_state["h4_runtime"], a)
        self.assertIsNotNone(a.get_active_model())
        self.assertEqual(journal.closed, closed)
        self.assertEqual(engine._pairs[(1, 5)].closed, closures)
        self.assertEqual([event["action"] for event in a.events], ["ACTIVATE_V1"])

    def test_reset_discards_all_pairs_and_does_not_reactivate_on_return(self):
        app = self.app()
        a = self.activate(app)
        self.select(app, 2, 5)
        b = self.activate(app)
        self.button(app, "RESTABLECER EDICIÓN").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["selected_pair_context"], (1, 5))
        self.assertIsNone(app.session_state["h4_runtime"].get_active_model())
        self.assertIsNot(app.session_state["h4_runtime"], a)
        self.select(app, 2, 5)
        self.assertIsNone(app.session_state["h4_runtime"].get_active_model())
        self.assertIsNot(app.session_state["h4_runtime"], b)
        self.assertEqual(app.text_input(key="v1_activation_reason").value, "")

    def test_reconnect_only_replaces_selected_runtime(self):
        app = self.app()
        a = self.activate(app)
        self.select(app, 2, 5)
        b = self.activate(app)
        self.button(app, "RECONECTAR RUNTIME").click().run()
        self.assertIsNot(app.session_state["h4_runtime"], b)
        self.assertIsNone(app.session_state["h4_runtime"].get_active_model())
        self.select(app)
        self.assertIs(app.session_state["h4_runtime"], a)

    def test_sessions_and_imported_approval_cannot_share_or_promote(self):
        app, other = self.app(), self.app()
        a = self.activate(app)
        self.assertIsNone(other.session_state["h4_runtime"].get_active_model())
        self.assertIsNot(app.session_state["pair_contexts"], other.session_state["pair_contexts"])
        for product in (2, 1):
            self.select(app, product)
            provider = app.session_state["h4_runtime"]
            before = provider.get_active_model()
            with self.assertRaises(InputError):
                provider.promote_candidate({"decision": "APROBADO", "PROMOVER": True})
            self.assertEqual(provider.get_active_model(), before)
            self.assertTrue(self.button(app, "PROMOVER CANDIDATE").disabled)
        self.assertIs(app.session_state["h4_runtime"], a)

    def test_train_candidate_through_ui_isolated_and_restored(self):
        engine, journal = trajectory()
        app = AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=30)
        app.session_state["demand_session"] = engine
        app.session_state["observation_journal"] = journal
        with tempfile.TemporaryDirectory() as tmp:
            with patch("retraining.RetrainingSession", side_effect=lambda sid: RetrainingSession(sid, Path(tmp))):
                app.run()
                closed = deepcopy(journal.closed)
                self.button(app, "ENSAYAR REENTRENAMIENTO").click().run()
            self.assertFalse(app.exception)
            run = app.session_state["retraining_result"]
            service = app.session_state["retraining_session"]
            self.assertEqual((run["product_id"], run["location_id"], run["n_train"]), (1, 5, 6))
            self.assertTrue(Path(run["folder"]).is_relative_to(Path(tmp)))
            self.assertIsNone(app.session_state["h4_runtime"].get_active_model())
            self.activate(app)
            with patch("model_comparison.ComparisonSession",
                       side_effect=lambda sid: ComparisonSession(sid, Path(tmp)/"decisions")):
                self.button(app, "COMPARAR CANDIDATE").click().run()
            self.assertFalse(app.exception)
            comparison = deepcopy(app.session_state["candidate_comparison_result"])
            self.assertEqual(comparison["eligibility"], "INSUFFICIENT_EVIDENCE")
            app.text_input(key="candidate_decision_reason").set_value("R21 muestra insuficiente").run()
            self.button(app, "RECHAZAR CANDIDATE").click().run()
            rejection = deepcopy(app.session_state["candidate_rejection"])
            self.select(app, 2, 5)
            self.assertNotIn("retraining_result", app.session_state)
            self.assertNotIn("retraining_session", app.session_state)
            self.assertNotIn("candidate_comparison_result", app.session_state)
            self.assertNotIn("candidate_rejection", app.session_state)
            self.assertNotIn("comparison_report", app.session_state)
            self.assertFalse(any(run["run_id"] in m.value for m in app.success))
            self.select(app)
            self.assertEqual(app.session_state["retraining_result"], run)
            self.assertIs(app.session_state["retraining_session"], service)
            self.assertEqual(app.session_state["candidate_comparison_result"], comparison)
            self.assertEqual(app.session_state["candidate_rejection"], rejection)
            self.assertEqual(service.trusted_run(run["run_id"]), run)
            self.assertEqual(journal.closed, closed)
            self.button(app, "RESTABLECER EDICIÓN").click().run()
            self.assertNotIn("retraining_result", app.session_state)
            self.select(app, 2, 5)
            self.assertNotIn("retraining_result", app.session_state)
