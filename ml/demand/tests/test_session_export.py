"""R52: contrato compatible, evidencia coherente y cero autoridad desde JSON."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from sklearn.ensemble import RandomForestRegressor
from streamlit.testing.v1 import AppTest

from demand_engine import create_session
from demand_runtime import create_runtime, V1_BINARY_SHA256
from lifecycle_registry import LifecycleRegistry, digest
from model_comparison import ComparisonSession
from pair_contexts import bind_pair_context
from retraining import RetrainingSession
from session_export import build_session_export, verify_session_export
from simulator_inputs import HERE, InputError
from ui_runtime import ObservationJournal, issue_forecast
from .test_retraining import trajectory


def sources(seed=42):
    engine, journal = create_session(seed=seed), ObservationJournal()
    engine.bind_journal(journal.session_id)
    engine.select(1, 5)
    return engine, journal


def close(engine, journal, observed=None):
    state = engine.status()
    forecast = issue_forecast(engine._reference, state["product_id"], state["location_id"],
                              state["open_month"], None, None, "HISTORIAL INSUFICIENTE")
    journal.issue(forecast)
    if observed is None:
        observed = engine.generate_observed()
    else:
        engine.set_manual_observed(observed)
    journal.reveal(forecast.key, observed)
    engine.close_month()
    journal.close(forecast.key, observed)
    engine.advance_month()
    return observed


def trace(document):
    return document["extensions"]["h4_traceability"]


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.engine, self.journal = sources()

    def export(self, **kwargs):
        return build_session_export(self.engine, self.journal, **kwargs)

    def test_public_envelope_and_existing_records_unchanged(self):
        close(self.engine, self.journal, 0)
        packet = self.export()
        self.assertEqual(packet["schema_version"], "h4-session-1")
        self.assertEqual(packet["session_id"], self.journal.session_id)
        self.assertIsNone(packet["generator_seed"])
        self.assertEqual(packet["records"], json.loads(json.dumps([asdict(r) for r in self.journal.closed.values()])))
        self.assertEqual(trace(packet)["schema_version"], "h4-traceability-1")
        self.assertEqual(trace(packet)["engine"]["generator_seed"], 42)
        self.assertTrue(verify_session_export(packet))

    def test_real_custom_seed_and_rng_gaussian_cache_reproducible(self):
        self.engine, self.journal = sources(123)
        close(self.engine, self.journal)
        original = self.engine._pairs[(1, 5)].rng
        state = original.getstate()
        packet = self.export()
        rng = trace(packet)["engine"]["pairs"][0]["rng"]
        self.assertEqual(trace(packet)["engine"]["generator_seed"], 123)
        self.assertIsNotNone(rng["gauss_next"])
        clone = random.Random()
        clone.setstate((rng["state_version"], tuple(rng["internal_state"]), rng["gauss_next"]))
        expected = random.Random(); expected.setstate(state)
        self.assertEqual([clone.gauss(0, 1.5) for _ in range(12)], [expected.gauss(0, 1.5) for _ in range(12)])
        self.assertEqual(original.getstate(), state)

    def test_all_pairs_sources_and_clocks_stay_independent(self):
        close(self.engine, self.journal, 10)
        self.engine.select(2, 6)
        generated = close(self.engine, self.journal)
        state = deepcopy(self.engine.status())
        packet = self.export()
        pairs = trace(packet)["engine"]["pairs"]
        self.assertEqual([(p["product_id"], p["location_id"]) for p in pairs], [(1, 5), (2, 6)])
        obs = trace(packet)["observations"]
        self.assertEqual([(r["observed"], r["source"]) for r in obs], [(10, "MANUAL"), (generated, "GENERATED")])
        self.assertEqual(self.engine.status(), state)

    def test_export_does_not_change_future_simulation(self):
        a, ja = sources(7); b, jb = sources(7)
        for _ in range(4):
            build_session_export(a, ja)
            self.assertEqual(close(a, ja), close(b, jb))
        self.assertEqual(a._pairs[(1, 5)].rng.getstate(), b._pairs[(1, 5)].rng.getstate())

    def test_snapshot_has_history_to_reproduce_next_generated_month(self):
        close(self.engine, self.journal)
        packet = self.export()
        pair = trace(packet)["engine"]["pairs"][0]
        self.assertTrue(pair["reference_history_for_simulation"])
        self.assertTrue(all(r["origin"] == "HISTORICAL_SYNTHETIC_1_1_REFERENCE"
                            for r in pair["reference_history_for_simulation"]))
        rng = pair["rng"]
        replay, _ = sources()
        replay_state = replay._pairs[(1, 5)]
        replay_state.open_month = pair["calendar"]["open_month"]
        replay_state.closed = {r["month"]: r["observed"] for r in pair["closed_observations"]}
        replay_state.rng.setstate((rng["state_version"], tuple(rng["internal_state"]), rng["gauss_next"]))
        self.assertEqual(replay.generate_observed(), self.engine.generate_observed())

    def test_old_lifecycle_without_session_snapshot_is_not_fabricated(self):
        with tempfile.TemporaryDirectory() as folder:
            old_engine, _ = sources()
            old_registry = LifecycleRegistry(old_engine.session_id, Path(folder))
            provider = create_runtime()
            provider.bind_lifecycle(old_registry.bind(1, 5))
            packet = self.export(state={"lifecycle_archives": [old_registry]})
            older = trace(packet)["prior_lifecycle_only"][0]
            self.assertEqual(older["session_id"], old_engine.session_id)
            self.assertEqual(older["simulation_history"], "UNKNOWN_NOT_CAPTURED")
            self.assertEqual(older["events"][0]["type"], "V1_AVAILABLE")

    def test_latent_is_omitted_and_pending_is_not_closed(self):
        self.engine.apply_scenario("STOCKOUT")
        self.engine.generate_observed()
        packet = self.export()
        self.assertEqual(packet["records"], [])
        self.assertEqual(trace(packet)["observations"], [])
        pair = trace(packet)["engine"]["pairs"][0]
        self.assertEqual(pair["pending_observation"]["source"], "GENERATED")
        self.assertEqual(pair["cached_generated_results"][0]["classification"], "SIMULATION_DRAW_NOT_CLOSED_SALES")
        def keys(value):
            if isinstance(value, dict):
                return set(value) | set().union(*(keys(v) for v in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(v) for v in value))
            return set()
        self.assertNotIn("latent", keys(packet))

    def test_revisions_keep_superseded_and_discarded_forecasts(self):
        first = issue_forecast(self.engine._reference, 1, 5, "2026-10", None, None, "FIRST")
        self.journal.issue(first)
        self.journal.discard_pending(first.key)
        second = replace(first, reason="SECOND")
        self.journal.issue(second)
        self.engine.edit_lags(999, 888, 777)
        packet = self.export()
        revisions = trace(packet)["journal"]["revisions"]
        self.assertEqual([r["type"] for r in revisions], ["FORECAST_ISSUED", "PENDING_DISCARDED", "FORECAST_ISSUED"])
        self.assertEqual(revisions[0]["forecast"]["reason"], "FIRST")
        self.assertEqual(trace(packet)["journal"]["pending"][0]["reason"], "SECOND")
        self.assertEqual(trace(packet)["engine"]["pairs"][0]["hypothetical_lags"], [999, 888, 777])

    def test_hypotheses_do_not_become_closed_observations(self):
        self.engine.edit_lags(999, 888, 777)
        close(self.engine, self.journal, 10)
        obs = trace(self.export())["observations"]
        self.assertEqual([r["observed"] for r in obs], [10])

    def test_conflicting_closed_observation_rejected(self):
        close(self.engine, self.journal, 10)
        self.engine._pairs[(1, 5)].closed["2026-10"] = 9
        with self.assertRaises(InputError): self.export()

    def test_model_or_prediction_changed_after_closure_rejected(self):
        close(self.engine, self.journal, 10)
        key = (1, 5, "2026-10")
        row = self.journal.closed[key]
        self.journal.closed[key] = replace(row, forecast=replace(row.forecast, prediction=123.))
        with self.assertRaises(InputError): self.export()

    def test_source_changed_after_closure_rejected(self):
        close(self.engine, self.journal, 10)
        self.engine._pairs[(1, 5)].closed_sources["2026-10"] = "GENERATED"
        with self.assertRaises(InputError): self.export()

    def test_missing_old_provenance_and_revisions_remain_unknown(self):
        close(self.engine, self.journal, 10)
        self.engine._pairs[(1, 5)].closed_sources.clear()
        self.engine._revisions = []
        self.journal.revisions = []
        del self.journal.trace_started_at
        packet = self.export()
        self.assertIsNone(trace(packet)["observations"][0]["source"])
        self.assertEqual(trace(packet)["observations"][0]["provenance_status"], "UNKNOWN_NOT_RECORDED")
        self.assertIsNone(trace(packet)["journal"]["trace_started_at"])

    def test_other_session_journal_and_pair_contexts_rejected(self):
        with self.assertRaises(InputError):
            build_session_export(self.engine, ObservationJournal())
        with self.assertRaises(InputError):
            self.export(state={"pair_context_owner": "other_session"})

    def test_export_hash_tampering_and_json_cannot_activate(self):
        packet = self.export()
        trace(packet)["authorizes_model_changes"] = True
        with self.assertRaises(InputError): verify_session_export(packet)
        # Recalcular un hash solo crea datos distintos: jamás un permiso.
        trace(packet).pop("document_sha256")
        trace(packet)["document_sha256"] = digest(packet)
        self.assertTrue(verify_session_export(packet))
        provider = create_runtime()
        with self.assertRaises(InputError): provider.bind_lifecycle(packet)
        with self.assertRaises(InputError): provider.promote_candidate(packet)
        self.assertIsNone(provider.get_active_model())

    def test_snapshot_is_copy_and_no_executable_model_objects(self):
        packet = self.export()
        trace(packet)["engine"]["pairs"][0]["calendar"]["open_month"] = "2099-01"
        self.assertEqual(self.engine.status()["open_month"], "2026-10")
        self.assertNotIn("estimator", json.dumps(packet))

    def test_active_and_previous_references_are_verified(self):
        provider = create_runtime()
        provider.activate_v1("referencia explícita R52")
        state = {}
        bind_pair_context(state, self.engine.session_id, 1, 5)
        state["h4_runtime"] = provider
        with patch("joblib.load", side_effect=AssertionError("no deserializar al exportar")), patch.object(RandomForestRegressor, "fit") as fit:
            packet = self.export(state=state)
            fit.assert_not_called()
        references = trace(packet)["model_contexts"][0]["references"]
        self.assertEqual(references["active"]["artifact_hash"], V1_BINARY_SHA256)
        self.assertEqual(references["previous_references"], [None])
        metadata = provider.get_active_model()
        provider._reference_checks[V1_BINARY_SHA256] = (metadata, lambda: False)
        with self.assertRaises(InputError): self.export(state=state)

    def test_candidate_and_decisions_verified_without_training_at_export(self):
        self.engine, self.journal = trajectory()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            registry = LifecycleRegistry(self.engine.session_id, root / "events")
            binding = registry.bind(1, 5)
            provider = create_runtime(); provider.bind_lifecycle(binding)
            provider.activate_v1("comparación para exportar")
            training = RetrainingSession(self.engine.session_id, root / "training")
            training.bind_lifecycle(binding)
            run = training.train(self.engine, self.journal)
            comparison = ComparisonSession(self.engine.session_id, root / "decisions")
            comparison.bind_lifecycle(binding)
            result = comparison.compare(provider, training, run["run_id"])
            comparison.reject(result["id"], "evidencia insuficiente")
            provider.rollback("volver a inactivo")
            state = {}; bind_pair_context(state, self.engine.session_id, 1, 5)
            state.update(h4_runtime=provider, retraining_session=training, retraining_result=run,
                         candidate_comparison_session=comparison)
            with patch("joblib.load", side_effect=AssertionError("solo hashes")), patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("sin fit")):
                packet = self.export(state=state, registry=registry)
            ctx = trace(packet)["model_contexts"][0]
            self.assertEqual(ctx["current_candidate_id"], run["run_id"])
            self.assertEqual(len(ctx["decisions"]), 2)
            self.assertEqual(trace(packet)["lifecycle"]["events"][-1]["type"], "ROLLBACK")
            self.assertEqual(trace(packet)["lifecycle"]["head_sha256"], registry.records()[-1]["event_sha256"])
            (Path(run["folder"])/"manifest.json").write_text('{}')
            with self.assertRaises(InputError): self.export(state=state, registry=registry)


class ExportStreamlitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        patcher = patch("lifecycle_registry.DEFAULT_ROOT", Path(self.temp.name))
        patcher.start(); self.addCleanup(patcher.stop)

    def app(self):
        app = AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        return app

    def button(self, app, label):
        return next(b for b in app.button if b.label == label)

    def close_month(self, app):
        label = "REGISTRAR ABSTENCIÓN" if self.button(app, "PREDECIR").disabled else "PREDECIR"
        self.button(app, label).click().run()
        self.button(app, "GENERAR SIGUIENTE MES").click().run()
        self.button(app, "AVANZAR MES").click().run()
        self.assertFalse(app.exception)

    def test_download_available_without_closures_and_edits_traced(self):
        app = self.app()
        self.assertEqual(len(app.get("download_button")), 1)
        self.assertEqual(app.session_state["last_session_export"]["records"], [])
        app.number_input(key="editor_1_5_2026-10_lag1").set_value(30).run()
        self.button(app, "VALIDAR ENTRADAS").click().run()
        kinds = [r["type"] for r in trace(app.session_state["last_session_export"])["journal"]["revisions"]]
        self.assertIn("EDITOR_REVISION", kinds)
        self.assertIn("INPUTS_CONFIRMED", kinds)

    def test_reset_exports_old_evidence_separately_without_active(self):
        app = self.app()
        app.text_input(key="v1_activation_reason").set_value("activar V1 para trazabilidad").run()
        self.button(app, "ACTIVAR V1 CONGELADA").click().run()
        self.close_month(app)
        previous = deepcopy(app.session_state["last_session_export"])
        self.button(app, "RESTABLECER EDICIÓN").click().run()
        self.assertFalse(app.exception)
        packet = app.session_state["last_session_export"]
        self.assertEqual(packet["records"], [])
        prior = trace(packet)["prior_sessions"][0]
        self.assertEqual(prior["records"], previous["records"])
        self.assertEqual(trace(prior)["snapshot_phase"], "PRE_RESET_SNAPSHOT")
        self.assertEqual(trace(prior)["lifecycle"]["events"][-1]["type"], "RESET")
        self.assertIsNone(trace(packet)["model_contexts"][0]["references"]["active"])
        self.assertTrue(verify_session_export(packet))

    def test_pair_and_other_session_exports_do_not_share_models_or_observations(self):
        app, other = self.app(), self.app()
        self.close_month(app)
        app.text_input(key="v1_activation_reason").set_value("activar solo A").run()
        self.button(app, "ACTIVAR V1 CONGELADA").click().run()
        app.selectbox(key="product").select(2).run()
        contexts = trace(app.session_state["last_session_export"])["model_contexts"]
        self.assertEqual(contexts[0]["references"]["active"]["version"], "V1")
        self.assertIsNone(contexts[1]["references"]["active"])
        other.run()
        self.assertEqual(other.session_state["last_session_export"]["records"], [])
        self.assertNotEqual(other.session_state["last_session_export"]["session_id"], app.session_state["last_session_export"]["session_id"])

    def test_inconsistent_snapshot_is_quarantined_on_reset(self):
        app = self.app()
        self.close_month(app)
        app.session_state["demand_session"]._pairs[(1, 5)].closed["2026-10"] += 1
        app.run()
        self.assertNotIn("last_session_export", app.session_state)
        self.button(app, "RESTABLECER EDICIÓN").click().run()
        self.assertFalse(app.exception)
        prior = trace(app.session_state["last_session_export"])["prior_sessions"][0]
        self.assertEqual(prior["status"], "UNVERIFIED")
        self.assertIn("unverified_closed_records", prior)
