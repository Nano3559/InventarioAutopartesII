"""Fixtures aislados: nunca promueve ni evalúa la V1 oficial."""
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor

import demand_runtime as dr
from simulator_inputs import FEATURE_NAMES, InputError, content_sha256, load_reference
from ui_runtime import ObservationJournal, issue_forecast, discover_runtime
from demand_engine import create_session


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "models").mkdir()
        (self.root / "reports").mkdir()
        self.path = self.root / "models/random_forest_candidate.joblib"
        self.features = dict(zip(FEATURE_NAMES, [10, 9, 8, -1.0, 0.0]))
        X = pd.DataFrame([[10, 9, 8, -1, 0], [20, 18, 16, 0, 1]], columns=FEATURE_NAMES)
        estimator = RandomForestRegressor(n_estimators=2, random_state=42).fit(X, [11, 22])
        self.payload = dict(schema="h4-random-forest-1", role="CANDIDATE", model="RANDOMFOREST",
                            feature_names=list(FEATURE_NAMES), target="target_ventas_mes",
                            scaler=None, estimator=estimator, parameters={"n_estimators": 2},
                            versions={"scikit-learn": sklearn.__version__}, trained_through="2026-03")
        self.save()
        self.runtime = dr.create_runtime()

    def save(self):
        joblib.dump(self.payload, self.path)
        raw = self.path.read_bytes()
        self.binary = hashlib.sha256(raw).hexdigest()
        self.normalized = content_sha256(raw)
        (self.root / "reports/v1_selection_manifest.json").write_text(json.dumps(dict(
            status="SELECTED_FROZEN_NOT_ACTIVE", active=False,
            artifact={"sha256": self.normalized}, contract={"features": list(FEATURE_NAMES)})))

    def promote(self):
        with patch.object(dr, "HERE", self.root), patch.object(dr, "V1_BINARY_SHA256", self.binary), patch.object(dr, "V1_NORMALIZED_SHA256", self.normalized):
            return self.runtime.promote_v1("fixture aislado")

    def test_inactive_and_discovery(self):
        self.assertIsNone(self.runtime.get_active_model())
        self.assertIsNone(discover_runtime().get_active_model())
        self.assertIsNone(self.runtime.predict(self.features)["prediction"])

    def test_promotion_inference_and_rollback(self):
        before = self.path.read_bytes()
        metadata = self.promote()
        self.assertEqual(metadata["role"], "ACTIVE")
        self.assertEqual(metadata["artifact_hash"], self.binary)
        self.assertIsInstance(self.runtime.predict(self.features)["prediction"], float)
        self.assertIsNone(dr.create_runtime().get_active_model())
        self.assertIsNone(self.runtime.rollback("volver a inactivo"))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(self.runtime.events), 2)

    def test_metadata_and_events_are_copies(self):
        self.promote()
        self.runtime.get_active_model()["feature_names"].clear()
        self.runtime.events.clear()
        self.assertEqual(len(self.runtime.get_active_model()["feature_names"]), 5)
        self.assertEqual(len(self.runtime.events), 1)

    def test_unverified_never_deserialized(self):
        self.path.write_bytes(b"unknown pickle")
        with patch("joblib.load") as loader:
            with self.assertRaises(InputError):
                self.promote()
            loader.assert_not_called()
        self.assertIsNone(self.runtime.get_active_model())

    def test_binary_hash_required_even_when_normalized_matches(self):
        with patch.object(dr, "V1_BINARY_SHA256", "0" * 64), patch("joblib.load") as loader:
            with self.assertRaises(InputError):
                self.runtime._load_verified(self.path, "0"*64, self.normalized, "fixture")
            loader.assert_not_called()

    def test_incompatible_payloads(self):
        for key, value in [("role", "ACTIVE"), ("feature_names", list(reversed(FEATURE_NAMES))),
                           ("target", "other"), ("scaler", "other"), ("trained_through", "invalid"),
                           ("versions", {}), ("parameters", {"n_estimators": 999})]:
            with self.subTest(key=key):
                old = self.payload[key]
                self.payload[key] = value
                self.save()
                with self.assertRaises(InputError):
                    self.promote()
                self.assertIsNone(self.runtime.get_active_model())
                self.payload[key] = old

    def test_invalid_features_abstain(self):
        self.promote()
        for value in [None, {}, dict(reversed(list(self.features.items()))),
                      {**self.features, "target": 10}]:
            self.assertIsNone(self.runtime.predict(value)["prediction"])
        for key, value in [(FEATURE_NAMES[0], None), (FEATURE_NAMES[0], True),
                           (FEATURE_NAMES[0], -1), (FEATURE_NAMES[0], 1.5),
                           (FEATURE_NAMES[0], math.inf), (FEATURE_NAMES[3], math.nan),
                           (FEATURE_NAMES[3], 0.4)]:
            self.assertIsNone(self.runtime.predict({**self.features, key: value})["prediction"])

    def test_explicit_reason_and_failed_promotion_preserves_active(self):
        with self.assertRaises(InputError):
            self.runtime.promote_v1("")
        self.promote()
        before = self.runtime.get_active_model()
        self.path.write_bytes(b"corrupt")
        with self.assertRaises(InputError):
            self.promote()
        self.assertEqual(self.runtime.get_active_model(), before)

    def test_inference_failure_and_negative_output(self):
        self.promote()
        estimator = self.runtime._active[1]
        for output in [[math.nan], [], [float("inf")]]:
            with patch.object(estimator, "predict", return_value=output):
                self.assertIsNone(self.runtime.predict(self.features)["prediction"])
        with patch.object(estimator, "predict", return_value=[-2.0]):
            self.assertEqual(self.runtime.predict(self.features)["prediction"], -2)

    def test_monthly_integration_preserves_closed_forecast(self):
        self.promote()
        reference = load_reference()
        session = create_session(reference)
        session.select(next(iter(reference.products)), next(iter(reference.stores)))
        state = session.status()
        journal = ObservationJournal()
        forecast = issue_forecast(reference, state["product_id"], state["location_id"],
                                  state["open_month"], self.features, self.runtime)
        journal.issue(forecast)
        observed = session.generate_observed()
        journal.close(forecast.key, observed)
        session.close_month()
        session.advance_month()
        self.runtime.rollback("fin de fixture")
        self.assertEqual(journal.closed[forecast.key].forecast, forecast)
        self.assertIsNotNone(forecast.model)
        self.assertEqual(session.status()["open_month"], "2026-11")
