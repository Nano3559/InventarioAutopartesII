"""R49: evidencia verificable sin autoridad de activación ni histórico ficticio."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from sklearn.ensemble import RandomForestRegressor
from streamlit.testing.v1 import AppTest

from demand_runtime import create_runtime, V1_BINARY_SHA256
from lifecycle_registry import LifecycleRegistry, canonical, digest
from model_comparison import ComparisonSession
from retraining import RetrainingSession
from simulator_inputs import HERE, InputError
from .test_retraining import trajectory
from . import test_demand_runtime as fixture_module
from .test_model_comparison import FixturePromotionRuntime, review_for


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = LifecycleRegistry(uuid.uuid4().hex, self.root / "events")
        self.binding = self.registry.bind(1, 5)

    def emit(self, key="one", **kwargs):
        return self.binding.emit("TEST_EVIDENCE", key=key, reason="fixture de datos", result="RECORDED", **kwargs)

    def test_sequence_real_utc_dates_and_complete_fields(self):
        start = datetime.now().astimezone()
        one, two = self.emit(), self.emit("two")
        self.assertEqual([r["sequence"] for r in self.registry.records()], [1, 2])
        self.assertLessEqual(start, datetime.fromisoformat(one["timestamp"]))
        self.assertLessEqual(datetime.fromisoformat(one["timestamp"]), datetime.fromisoformat(two["timestamp"]))
        self.assertEqual(two["previous_sha256"], one["event_sha256"])
        for field in ("id", "session_id", "product_id", "location_id", "model", "artifact_hash",
                      "previous_reference", "state_before", "state_after", "data_sha256", "reason", "result"):
            self.assertIn(field, one)

    def test_idempotency_and_contradictory_same_key_rejected(self):
        self.assertEqual(self.emit(), self.emit())
        self.assertEqual(len(self.registry.records()), 1)
        with self.assertRaises(InputError):
            self.emit(state_after="CONTRADICTION")

    def test_tampering_even_recomputed_hash_fails_memory_anchor(self):
        event = self.emit()
        file = next(self.registry.folder.iterdir())
        event["result"] = "APROBADO"
        event.pop("event_sha256")
        event["event_sha256"] = digest(event)
        file.write_bytes(canonical(event))
        with self.assertRaises(InputError):
            self.registry.records()
        with self.assertRaises(InputError):
            self.emit("after corruption")

    def test_missing_or_added_file_is_detected(self):
        self.emit()
        file = next(self.registry.folder.iterdir())
        raw = file.read_bytes()
        file.unlink()
        with self.assertRaises(InputError):
            self.registry.records()
        file.write_bytes(raw)
        (self.registry.folder / "imported.json").write_text('{}')
        with self.assertRaises(InputError):
            self.registry.records()

    def test_source_hash_and_copies_are_verified(self):
        from lifecycle_registry import source_reference
        file = self.root / "source.json"
        file.write_bytes(b'{}')
        with self.assertRaises(InputError):
            source_reference("source", file, "0" * 64)
        self.emit(source=source_reference("source", file))
        self.assertTrue(self.registry.verify_sources())
        self.registry.records()[0]["reason"] = "edited copy"
        self.assertEqual(self.registry.records()[0]["reason"], "fixture de datos")
        file.write_bytes(b'{"edited":true}')
        with self.assertRaises(InputError):
            self.registry.verify_sources()

    def test_imported_evidence_is_not_activation_authority(self):
        self.emit(state_after="ACTIVE", model=dict(version="APROBADO", artifact_hash="a"*64))
        provider = create_runtime()
        imported = json.loads(json.dumps(self.registry.records()))
        with self.assertRaises(InputError):
            provider.bind_lifecycle(imported)
        with self.assertRaises(InputError):
            provider.promote_candidate(imported)
        self.assertIsNone(provider.get_active_model())
        with self.assertRaises(FileExistsError):
            LifecycleRegistry(self.registry.session_id, self.root / "events")

    def test_protected_output_and_invalid_hash_rejected(self):
        with self.assertRaises(InputError):
            LifecycleRegistry(uuid.uuid4().hex, HERE / "reports" / "unsafe")
        with self.assertRaises(InputError):
            self.emit(data_sha256="invented")

    def test_pair_and_session_isolation_and_binding_guard(self):
        provider = create_runtime()
        provider.bind_lifecycle(self.binding)
        other = LifecycleRegistry(uuid.uuid4().hex, self.root / "other")
        self.assertEqual(other.records(), [])
        self.assertEqual(self.registry.records((2, 5)), [])
        with self.assertRaises(InputError):
            provider.bind_lifecycle(self.registry.bind(2, 5))
        with self.assertRaises(InputError):
            provider.bind_lifecycle(other.bind(1, 5))

    def test_verified_v1_activation_rollback_and_no_fit(self):
        provider = create_runtime()
        with patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("fit prohibido")) as fit:
            provider.bind_lifecycle(self.binding)
            provider.bind_lifecycle(self.binding)
            provider.activate_v1("acción explícita de prueba")
            provider.rollback("retorno a inactivo")
            fit.assert_not_called()
        rows = self.registry.records()
        self.assertEqual([r["type"] for r in rows], ["V1_AVAILABLE", "RUNTIME_CONNECTED", "ACTIVATE_V1", "ROLLBACK"])
        self.assertEqual(rows[2]["artifact_hash"], V1_BINARY_SHA256)
        self.assertIsNone(rows[2]["active_before"])
        self.assertEqual(rows[3]["previous_reference"]["version"], "V1")
        self.assertIsNone(rows[3]["active_after"])
        self.assertIsNone(provider.get_active_model())

    def test_write_failure_cannot_activate_or_remove_active(self):
        provider = create_runtime()
        provider.bind_lifecycle(self.binding)
        with patch.object(self.registry, "_append", side_effect=InputError("disco no disponible")):
            with self.assertRaises(InputError):
                provider.activate_v1("debe fallar")
        self.assertIsNone(provider.get_active_model())
        provider.activate_v1("activación registrada")
        before = provider.get_active_model()
        with patch.object(self.registry, "_append", side_effect=InputError("disco no disponible")):
            with self.assertRaises(InputError):
                provider.rollback("debe conservar ACTIVE")
        self.assertEqual(provider.get_active_model(), before)
        provider.rollback("retorno registrado")
        self.assertIsNone(provider.get_active_model())

    def test_fixture_promotion_is_logged_without_production_policy(self):
        fixture = fixture_module.RuntimeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        provider = FixturePromotionRuntime(fixture.root)
        provider.bind_lifecycle(self.binding)
        provider.promote_candidate(fixture, review_for(provider, fixture))
        self.assertEqual(self.registry.records()[-1]["type"], "PROMOTE_FIXTURE")
        self.assertEqual(self.registry.records()[-1]["scope"], "ISOLATED_FIXTURE")
        provider.rollback("fixture vuelve a inactivo")
        self.assertIsNone(provider.get_active_model())
        with self.assertRaises(InputError):
            create_runtime().promote_candidate(self.registry.records())


class LifecycleCycleTests(unittest.TestCase):
    def test_candidate_comparison_rejection_block_and_sources(self):
        engine, journal = trajectory()
        closed = deepcopy(journal.closed)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            registry = LifecycleRegistry(engine.session_id, root / "events")
            binding = registry.bind(1, 5)
            provider = create_runtime()
            provider.bind_lifecycle(binding)
            provider.activate_v1("comparación simulada")
            training = RetrainingSession(engine.session_id, root / "candidates")
            training.bind_lifecycle(binding)
            run = training.train(engine, journal)
            self.assertEqual(training.train(engine, journal), run)
            service = ComparisonSession(engine.session_id, root / "decisions")
            service.bind_lifecycle(binding)
            with patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("sin ajuste al comparar")):
                comparison = service.compare(provider, training, run["run_id"])
                self.assertEqual(service.compare(provider, training, run["run_id"]), comparison)
            reject = service.reject(comparison["id"], "evidencia insuficiente")
            self.assertEqual(service.reject(comparison["id"], "evidencia insuficiente"), reject)
            with self.assertRaises(InputError):
                provider.promote_candidate({"decision": "APROBADO"})
            provider.rollback("cerrar ensayo")
            rows = registry.records()
            kinds = [r["type"] for r in rows]
            for name in ("CANDIDATE_CREATED", "MODELS_COMPARED", "INSUFFICIENT_EVIDENCE", "CANDIDATE_REJECTED", "PROMOTION_BLOCKED"):
                self.assertEqual(kinds.count(name), 1)
            event = next(r for r in rows if r["type"] == "MODELS_COMPARED")
            self.assertEqual(event["data_sha256"], comparison["compared_data_sha256"])
            self.assertEqual(event["source"]["id"], comparison["id"])
            rejected_event = next(r for r in rows if r["type"] == "CANDIDATE_REJECTED")
            self.assertFalse(rejected_event["affects_active"])
            self.assertFalse(rejected_event["active_snapshot_available"])
            self.assertEqual(rejected_event["previous_reference"], comparison["active"])
            self.assertTrue(registry.verify_sources())
            self.assertEqual(journal.closed, closed)

    def test_no_fabrication_of_candidate_creation_before_binding(self):
        engine, journal = trajectory()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            training = RetrainingSession(engine.session_id, root / "training")
            run = training.train(engine, journal)
            registry = LifecycleRegistry(engine.session_id, root / "events")
            training.bind_lifecycle(registry.bind(1, 5))
            training.train(engine, journal)
            self.assertEqual(registry.records(), [])
            self.assertEqual(run["role"], "CANDIDATE")

    def test_training_audit_failure_retries_without_refit(self):
        engine, journal = trajectory()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            registry = LifecycleRegistry(engine.session_id, root / "events")
            training = RetrainingSession(engine.session_id, root / "training")
            training.bind_lifecycle(registry.bind(1, 5))
            with patch.object(registry, "_append", side_effect=InputError("fallo de evidencia")):
                with self.assertRaises(InputError):
                    training.train(engine, journal)
            with patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("no repetir ajuste")):
                training.train(engine, journal)
            self.assertEqual([r["type"] for r in registry.records()], ["CANDIDATE_CREATED"])

    def test_source_replaced_cannot_be_registered_as_trusted_comparison(self):
        engine, journal = trajectory()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            registry = LifecycleRegistry(engine.session_id, root / "events")
            training = RetrainingSession(engine.session_id, root / "training")
            run = training.train(engine, journal)
            provider = create_runtime()
            provider.activate_v1("referencia para comparación")
            service = ComparisonSession(engine.session_id, root / "decisions")
            record = service.compare(provider, training, run["run_id"])
            service.bind_lifecycle(registry.bind(1, 5))
            path = root/"decisions"/engine.session_id/(record["id"]+".json")
            path.write_text('{}')
            with self.assertRaises(InputError):
                service.compare(provider, training, run["run_id"])
            self.assertEqual(registry.records(), [])


class LifecycleStreamlitTests(unittest.TestCase):
    def test_reruns_pairs_reset_keep_evidence_without_reactivation(self):
        with tempfile.TemporaryDirectory() as folder, patch("lifecycle_registry.DEFAULT_ROOT", Path(folder)):
            app = AppTest.from_file(str(HERE / "streamlit_app.py"), default_timeout=30).run()
            self.assertFalse(app.exception)
            button = lambda label: next(b for b in app.button if b.label == label)
            registry = app.session_state["lifecycle_registry"]
            initial = registry.records()
            app.run()
            self.assertEqual(registry.records(), initial)
            app.text_input(key="v1_activation_reason").set_value("R49 activar A").run()
            button("ACTIVAR V1 CONGELADA").click().run()
            app.selectbox(key="product").select(2).run()
            self.assertIsNone(app.session_state["h4_runtime"].get_active_model())
            self.assertFalse(any(r["type"] == "ACTIVATE_V1" for r in registry.records((2, 5))))
            app.selectbox(key="product").select(1).run()
            self.assertIsNotNone(app.session_state["h4_runtime"].get_active_model())
            button("RESTABLECER EDICIÓN").click().run()
            self.assertFalse(app.exception)
            self.assertIsNone(app.session_state["h4_runtime"].get_active_model())
            self.assertIs(app.session_state["lifecycle_archives"][0], registry)
            self.assertEqual(registry.records()[-1]["type"], "RESET")
            self.assertEqual(registry.records((2, 5))[-1]["type"], "RESET")
            self.assertNotEqual(app.session_state["lifecycle_registry"].session_id, registry.session_id)
            self.assertTrue(registry.folder.is_dir())
            before = registry.records()
            app.run()
            self.assertEqual(registry.records(), before)
