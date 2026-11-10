"""Único lugar con política positiva de fixtures: nunca se importa por la app."""
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

import demand_runtime as dr
from model_comparison import ComparisonSession, archived_run, verified_bundle, statistics, ARCHIVE_RUN
from retraining import RetrainingSession
from simulator_inputs import HERE, InputError, content_sha256, load_reference
from ui_runtime import issue_forecast, ObservationJournal
from ui_analysis import parse_comparison
from . import test_demand_runtime as fixture_module
from .test_retraining import trajectory
from .test_ross_ui import FakeRuntime


class FixturePromotionRuntime(dr.DemandRuntime):
    """Revisión simulada exclusiva de unittest, sin flag en código productivo."""
    def __init__(self, fixture_root):
        super().__init__()
        self.fixture_root = Path(fixture_root).resolve()
        self.rejected = set()

    def promote_candidate(self, fixture, review):
        path = fixture.path.resolve()
        if self.fixture_root not in path.parents or path.stat().st_size > 100000:
            raise InputError("Solo artefactos pequeños generados en este fixture.")
        if review["candidate_hash"] in self.rejected:
            raise InputError("Fixture rechazado.")
        expected = dict(scope="ISOLATED_FIXTURE", candidate_hash=fixture.binary,
                        active_hash=self.get_active_model()["artifact_hash"] if self._active else None,
                        data_hash="d"*64, coverage_review=True, group_errors_review=True,
                        reproducibility_review=True, reviewer="UNITTEST_REVIEWER", decision="ELIGIBLE_FIXTURE")
        if review != expected:
            raise InputError("Revisión del fixture insuficiente o desactualizada.")
        reference = self._load_verified(path, fixture.binary, fixture.normalized, "TEST-"+fixture.binary[:8])
        expected_hash = fixture.binary
        self._replace_active(reference, lambda: hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash)
        self._record("PROMOTE_FIXTURE", "Revisión simulada aislada; no es una política real.")
        return self.get_active_model()

    def reject_fixture(self, fixture):
        self.rejected.add(fixture.binary)
        self._record("REJECT_FIXTURE", "Evidencia no elegible del fixture.")


def review_for(runtime, fixture):
    return dict(scope="ISOLATED_FIXTURE", candidate_hash=fixture.binary,
                active_hash=runtime.get_active_model()["artifact_hash"] if runtime._active else None,
                data_hash="d"*64, coverage_review=True, group_errors_review=True,
                reproducibility_review=True, reviewer="UNITTEST_REVIEWER", decision="ELIGIBLE_FIXTURE")


class ComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = HERE.parent.parent
        cls.protected = json.loads((cls.root/"docs/H4/tareas_erika/tarea_12/evidence/integrity.json").read_text())["files"]
        cls.archived = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in Path(archived_run()["folder"]).iterdir() if p.is_file()}

    @classmethod
    def tearDownClass(cls):
        for name, expected in {**cls.protected, **cls.archived}.items():
            if hashlib.sha256((cls.root/name).read_bytes()).hexdigest() != expected:
                raise AssertionError("Archivo protegido alterado: "+name)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.engine, self.journal = trajectory()
        self.training = RetrainingSession(self.engine.session_id, Path(self.temp.name)/"training")
        self.run = self.training.train(self.engine, self.journal)
        self.service = ComparisonSession(self.engine.session_id, Path(self.temp.name)/"decisions")
        self.active = FakeRuntime()

    def compare(self):
        return self.service.compare(self.active, self.training, self.run["run_id"])

    def test_same_input_metrics_no_fit_and_insufficient_evidence(self):
        with patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("fit prohibido")):
            record = self.compare()
        self.assertEqual(len(self.active.calls), 3)
        self.assertEqual(self.active.calls, [r["features"] for r in record["rows"]])
        self.assertEqual(record["period"], ["2027-07", "2027-09"])
        self.assertEqual(record["eligibility"], "INSUFFICIENT_EVIDENCE")
        self.assertFalse(record["promotion_allowed"])
        m = record["metrics"]["a"*64]
        self.assertAlmostEqual(m["MAE"], 2.5)
        self.assertAlmostEqual(m["RMSE"], np.sqrt((1.5**2+2.5**2+3.5**2)/3))
        self.assertEqual(m["coverage"], 1)
        self.assertEqual(m["n"], 3)
        self.assertIsNone(m["R2"])
        parse_comparison(json.dumps(record["ross_report"]).encode(), load_reference())

    def test_constant_target_and_abstention_metrics(self):
        rows = [dict(observed=1, predictions={"x": v}) for v in (None, 2, 2)]
        m = statistics(rows, "x")
        self.assertEqual(m["coverage"], 2/3)
        self.assertEqual(m["MAE"], 1)
        self.assertIsNone(m["R2_descriptive"])

    def test_common_rows_and_coverage(self):
        self.active.result["prediction"] = None
        record = self.compare()
        self.assertEqual(record["common_n"], 0)
        self.assertEqual(record["common_metrics"], {})
        self.assertEqual(record["metrics"]["a"*64]["coverage"], 0)

    def test_candidate_receives_identical_features(self):
        original = RandomForestRegressor.predict
        seen = []
        def predict(model, X):
            seen.extend(X.to_dict("records"))
            return original(model, X)
        with patch.object(RandomForestRegressor, "predict", new=predict):
            self.compare()
        self.assertEqual(seen, self.active.calls)

    def test_corrupt_artifact_never_deserialized(self):
        path = Path(self.run["folder"])/"candidate.joblib"
        path.write_bytes(b"unknown")
        with patch("joblib.load") as loader:
            with self.assertRaises(InputError):
                self.compare()
            loader.assert_not_called()

    def test_reserve_corruption_rejected(self):
        path = Path(self.run["folder"])/"reserved.csv"
        path.write_bytes(path.read_bytes()+b"invalid")
        with self.assertRaises(InputError):
            self.compare()

    def test_unknown_run_and_foreign_session_rejected(self):
        with self.assertRaises(InputError):
            self.service.compare(self.active, self.training, "JSON-APROBADO")
        other, _ = trajectory()
        with self.assertRaises(InputError):
            ComparisonSession(other.session_id, self.temp.name).compare(self.active, self.training, self.run["run_id"])

    def test_active_change_or_training_overlap_rejected(self):
        self.active.metadata["trained_through"] = "2027-08"
        with self.assertRaises(InputError):
            self.compare()
        self.active.metadata["trained_through"] = "2026-03"
        def changed(features):
            self.active.metadata["version"] = "CHANGED"
            return {"prediction": 1., "reason": ""}
        self.active.predict = changed
        with self.assertRaises(InputError):
            self.compare()

    def test_original_record_immutable_rejection_separate(self):
        record = self.compare()
        path = Path(self.temp.name)/"decisions"/self.engine.session_id/(record["id"]+".json")
        raw = path.read_bytes()
        rejection = self.service.reject(record["id"], "Muestra insuficiente")
        self.assertEqual(rejection["decision"], "REJECTED_FOR_PROMOTION")
        self.assertEqual(path.read_bytes(), raw)
        record["eligibility"] = "APROBADO"
        self.assertEqual(self.compare()["eligibility"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(len(list(path.parent.glob("CMP-*.json"))), 1)

    def test_json_approval_never_authorizes_production_runtime(self):
        report = self.compare()["ross_report"]
        report["decision"] = "APROBADO"
        parse_comparison(json.dumps(report).encode(), load_reference())
        runtime = dr.create_runtime()
        for input_value in (report, {"PROMOVER": True}, {"fixture_mode": True}):
            with self.assertRaisesRegex(InputError, "BLOQUEADA"):
                runtime.promote_candidate(input_value)
        self.assertIsNone(runtime.get_active_model())
        self.assertEqual(len(inspect.signature(dr.create_runtime).parameters), 0)


class FixturePolicyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.RuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.runtime = FixturePromotionRuntime(self.fixture.root)

    def test_fixture_promotion_previous_active_and_rollback(self):
        f = self.fixture
        first = self.runtime.promote_candidate(f, review_for(self.runtime, f))
        frozen = issue_forecast(load_reference(), 1, 5, "2026-10", f.features, self.runtime)
        journal = ObservationJournal()
        journal.issue(frozen)
        journal.close(frozen.key, 10)
        saved = deepcopy(journal.closed)
        # Segundo modelo pequeño en otro fichero del mismo directorio temporal.
        f.path = f.root/"models/second.joblib"
        f.payload["estimator"].random_state = 99
        f.save()
        second = self.runtime.promote_candidate(f, review_for(self.runtime, f))
        self.assertNotEqual(first["artifact_hash"], second["artifact_hash"])
        self.assertEqual(self.runtime.rollback("revertir fixture"), first)
        self.assertEqual(journal.closed, saved)
        self.assertEqual(len(self.runtime.events), 3)
        self.assertIsNone(dr.create_runtime().get_active_model())

    def test_rejected_and_insufficient_fixture_cannot_promote(self):
        review = review_for(self.runtime, self.fixture)
        review["group_errors_review"] = False
        with self.assertRaises(InputError):
            self.runtime.promote_candidate(self.fixture, review)
        self.runtime.reject_fixture(self.fixture)
        with self.assertRaises(InputError):
            self.runtime.promote_candidate(self.fixture, review_for(self.runtime, self.fixture))

    def test_fixture_policy_rejects_real_candidate(self):
        run = archived_run()
        self.fixture.path = Path(run["folder"])/"candidate.joblib"
        self.fixture.binary = run["files"]["candidate.joblib"]
        with self.assertRaises(InputError):
            self.runtime.promote_candidate(self.fixture, review_for(self.runtime, self.fixture))

    def test_rollback_rejects_changed_previous_artifact(self):
        self.runtime.promote_candidate(self.fixture, review_for(self.runtime, self.fixture))
        old_path = self.fixture.path
        self.fixture.path = self.fixture.root/"models/second.joblib"
        self.fixture.payload["created_utc"] = "different"
        self.fixture.save()
        before = self.runtime.promote_candidate(self.fixture, review_for(self.runtime, self.fixture))
        old_path.write_bytes(b"corrupt")
        with self.assertRaises(InputError):
            self.runtime.rollback("should fail")
        self.assertEqual(self.runtime.get_active_model(), before)


class ComparisonStreamlitTests(unittest.TestCase):
    def test_local_compare_reject_block_and_reset(self):
        from streamlit.testing.v1 import AppTest
        engine, journal = trajectory()
        with tempfile.TemporaryDirectory() as tmp:
            training = RetrainingSession(engine.session_id, Path(tmp)/"training")
            run = training.train(engine, journal)
            active = FakeRuntime()
            before = active.get_active_model()
            app = AppTest.from_file(str(HERE/"streamlit_app.py"), default_timeout=30)
            for k, v in dict(demand_session=engine, observation_journal=journal,
                             retraining_session=training, retraining_result=run, h4_runtime=active,
                             candidate_comparison_session=ComparisonSession(engine.session_id, Path(tmp)/"decisions")).items():
                app.session_state[k] = v
            app.run()
            button = lambda label: next(b for b in app.button if b.label == label)
            button("COMPARAR CANDIDATE").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["candidate_comparison_result"]["eligibility"], "INSUFFICIENT_EVIDENCE")
            self.assertTrue(button("PROMOVER CANDIDATE").disabled)
            app.text_input(key="candidate_decision_reason").set_value("Muestra insuficiente").run()
            button("RECHAZAR CANDIDATE").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["candidate_rejection"]["decision"], "REJECTED_FOR_PROMOTION")
            self.assertEqual(active.get_active_model(), before)
            button("RESTABLECER EDICIÓN").click().run()
            self.assertFalse(app.exception)
            self.assertNotIn("candidate_comparison_result", app.session_state)
