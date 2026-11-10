"""Ensayos independientes; ninguna prueba carga o reentrena V1."""
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from demand_engine import create_session
from simulator_inputs import HERE, InputError, FEATURE_NAMES, load_reference
from ui_runtime import Forecast, ObservationJournal
from retraining import MONTHS, RetrainingSession, prepare_incremental


def trajectory(count=12, product=1, store=5):
    engine = create_session(load_reference())
    journal = ObservationJournal()
    engine.bind_journal(journal.session_id)
    engine.select(product, store)
    for i in range(count):
        month = engine.status()["open_month"]
        # Hipótesis deliberadamente distintas a los observados y predicción.
        forecast = Forecast(product, store, month, (999, 888, 777, 0., 1.),
                            12345., 999., None, "", datetime.now(timezone.utc).isoformat())
        journal.issue(forecast)
        engine.set_manual_observed(10+i)
        engine.close_month()
        journal.close(forecast.key, 10+i)
        engine.advance_month()
    return engine, journal


class RetrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protected = json.loads((HERE.parent.parent / "docs/H4/tareas_erika/tarea_10/evidence/integrity_before.json").read_text())

    @classmethod
    def tearDownClass(cls):
        for name, expected in cls.protected.items():
            if hashlib.sha256((HERE.parent.parent / name).read_bytes()).hexdigest() != expected:
                raise AssertionError("Archivo protegido alterado: " + name)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.engine, self.journal = trajectory()
        self.service = RetrainingSession(self.engine.session_id, Path(self.temp.name)/"runs")

    def test_reconstruction_ignores_predictions_and_hypothetical_lags(self):
        data = prepare_incremental(self.engine, self.journal)
        row = data["train"][0]
        self.assertEqual([row[k] for k in FEATURE_NAMES[:3]], [12, 11, 10])
        self.assertEqual(row["target_ventas_mes"], 13)
        self.assertTrue(all(r["differs"] for r in data["trace"]))
        self.assertEqual(data["history_months"], list(MONTHS[:3]))
        self.assertEqual([r["mes_objetivo"] for r in data["train"]], list(MONTHS[3:9]))
        self.assertEqual([r["mes_objetivo"] for r in data["reserved"]], list(MONTHS[9:]))

    def test_insufficient_months_never_fits(self):
        for count in (0, 3, 9, 11):
            engine, journal = trajectory(count)
            with patch.object(RandomForestRegressor, "fit") as fit:
                with self.assertRaisesRegex(InputError, "12 cierres"):
                    RetrainingSession(engine.session_id, self.temp.name).train(engine, journal)
                fit.assert_not_called()

    def test_pending_or_revealed_is_not_closed(self):
        self.engine, self.journal = trajectory(11)
        f = Forecast(1, 5, "2027-09", None, None, None, None, "ABSTENCIÓN",
                     datetime.now(timezone.utc).isoformat())
        self.journal.issue(f)
        self.engine.set_manual_observed(21)
        self.journal.reveal(f.key, 21)
        with self.assertRaises(InputError):
            prepare_incremental(self.engine, self.journal)

    def test_contradictory_observed_and_missing_closure_rejected(self):
        key = (1, 5, "2027-01")
        old = self.journal.closed[key]
        self.journal.closed[key] = replace(old, observed=old.forecast.prediction)
        with self.assertRaises(InputError):
            prepare_incremental(self.engine, self.journal)
        del self.journal.closed[key]
        with self.assertRaises(InputError):
            prepare_incremental(self.engine, self.journal)

    def test_wrong_key_and_closure_before_emission_rejected(self):
        key = (1, 5, "2027-01")
        old = self.journal.closed[key]
        self.journal.closed[key] = replace(old, observed_at="2000-01-01T00:00:00+00:00")
        with self.assertRaises(InputError):
            prepare_incremental(self.engine, self.journal)
        self.journal.closed[key] = replace(old, forecast=replace(old.forecast, product_id=2))
        with self.assertRaises(InputError):
            prepare_incremental(self.engine, self.journal)

    def test_other_session_rejected(self):
        other, journal = trajectory()
        with self.assertRaises(InputError):
            prepare_incremental(self.engine, journal)
        with self.assertRaises(InputError):
            self.service.train(other, journal)
        with self.assertRaises(InputError):
            self.engine.bind_journal(journal.session_id)

    def test_snapshot_is_copy_and_contains_no_latent(self):
        snapshot = self.engine.export_closed()
        snapshot["records"][0]["observed"] = 10000
        self.assertEqual(self.engine.export_closed()["records"][0]["observed"], 10)
        self.assertNotIn("latent", json.dumps(snapshot))

    def test_training_versioned_and_repeat_is_idempotent(self):
        original = RandomForestRegressor.fit
        captured = []
        def fit(model, X, y):
            captured.append((X.copy(), y.copy()))
            return original(model, X, y)
        with patch.object(RandomForestRegressor, "fit", new=fit):
            first = self.service.train(self.engine, self.journal)
            again = self.service.train(self.engine, self.journal)
        self.assertEqual(first, again)
        self.assertEqual(len(captured), 1)
        self.assertEqual(list(captured[0][0].columns), list(FEATURE_NAMES))
        self.assertEqual(list(captured[0][1]), list(range(13, 19)))
        self.assertEqual(first["n_train"], 6)
        self.assertEqual(first["n_reserved"], 3)
        self.assertEqual(first["n_series"], 1)
        self.assertEqual(first["role"], "CANDIDATE")
        self.assertFalse(first["promoted"])
        self.assertIsNone(first["metrics"])
        folder = Path(first["folder"])
        for name, expected in first["files"].items():
            self.assertEqual(hashlib.sha256((folder/name).read_bytes()).hexdigest(), expected)
        candidate = joblib.load(folder/"candidate.joblib")
        self.assertEqual(candidate["role"], "CANDIDATE")
        self.assertEqual(candidate["trained_through"], "2027-06")

    def test_reproducibility_and_reserve_does_not_affect_fit(self):
        first = self.service.train(self.engine, self.journal)
        # Reserva distinta, objetivos de ajuste idénticos.
        for month in MONTHS[9:]:
            self.engine._pairs[(1, 5)].closed[month] = 500
            key = (1, 5, month)
            self.journal.closed[key] = replace(self.journal.closed[key], observed=500)
        second = RetrainingSession(self.engine.session_id, Path(self.temp.name)/"other").train(self.engine, self.journal)
        a = joblib.load(Path(first["folder"])/"candidate.joblib")["estimator"]
        b = joblib.load(Path(second["folder"])/"candidate.joblib")["estimator"]
        X = pd.read_csv(Path(first["folder"])/"train.csv")[list(FEATURE_NAMES)]
        np.testing.assert_array_equal(a.predict(X), b.predict(X))
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual((Path(first["folder"])/"train.csv").read_bytes(), (Path(second["folder"])/"train.csv").read_bytes())

    def test_protected_paths_and_session_traversal_rejected(self):
        for root in (HERE, HERE/"models", HERE/"data/new", HERE/"reports/new"):
            with self.assertRaises(InputError):
                RetrainingSession(self.engine.session_id, root)
        with self.assertRaises(InputError):
            RetrainingSession("../models", self.temp.name)

    def test_other_pair_is_not_mixed(self):
        self.engine.select(2, 5)
        with self.assertRaisesRegex(InputError, "12 cierres"):
            prepare_incremental(self.engine, self.journal)
        self.engine.select(1, 5)
        self.assertEqual(len(prepare_incremental(self.engine, self.journal)["train"]), 6)

    def test_concurrent_request_is_rejected(self):
        self.service._lock.acquire()
        try:
            with self.assertRaisesRegex(InputError, "ejecución"):
                self.service.train(self.engine, self.journal)
        finally:
            self.service._lock.release()

    def test_generated_source_and_no_latent_export(self):
        engine, journal = trajectory(0)
        engine.apply_scenario("STOCKOUT")
        observed = engine.generate_observed()
        self.assertEqual(observed, engine.generate_observed())
        engine.close_month()
        record = engine.export_closed()["records"][0]
        self.assertEqual(record["source"], "GENERATED")
        self.assertEqual(record["observed"], observed)
        self.assertEqual(set(record), {"month", "observed", "source"})

    def test_unknown_source_or_duplicate_export_rejected(self):
        snapshot = self.engine.export_closed()
        snapshot["records"][0]["source"] = "PREDICTION"
        with patch.object(self.engine, "export_closed", return_value=snapshot):
            with self.assertRaises(InputError):
                prepare_incremental(self.engine, self.journal)
        snapshot = self.engine.export_closed()
        snapshot["records"].append(snapshot["records"][0])
        with patch.object(self.engine, "export_closed", return_value=snapshot):
            with self.assertRaises(InputError):
                prepare_incremental(self.engine, self.journal)


class RetrainingStreamlitTests(unittest.TestCase):
    def test_explicit_action_candidate_reset_and_no_activation(self):
        from streamlit.testing.v1 import AppTest
        from .test_ross_ui import FakeRuntime
        with tempfile.TemporaryDirectory() as tmp:
            engine, journal = trajectory()
            service = RetrainingSession(engine.session_id, tmp)
            runtime = FakeRuntime()
            active_before = runtime.get_active_model()
            app = AppTest.from_file(str(HERE/"streamlit_app.py"), default_timeout=30)
            app.session_state["demand_session"] = engine
            app.session_state["observation_journal"] = journal
            app.session_state["retraining_session"] = service
            app.session_state["h4_runtime"] = runtime
            app.run()
            self.assertFalse(app.exception)
            self.assertFalse(list(Path(tmp).rglob("candidate.joblib")))
            button = lambda label: next(b for b in app.button if b.label == label)
            button("ENSAYAR REENTRENAMIENTO").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["retraining_result"]["n_train"], 6)
            self.assertEqual(runtime.get_active_model(), active_before)
            app.run()
            button("ENSAYAR REENTRENAMIENTO").click().run()
            self.assertEqual(len(list(Path(tmp).rglob("candidate.joblib"))), 1)
            button("RESTABLECER EDICIÓN").click().run()
            self.assertFalse(app.exception)
            self.assertNotIn("retraining_result", app.session_state)
            button("ENSAYAR REENTRENAMIENTO").click().run()
            self.assertIn("12 cierres", app.session_state["retraining_error"])
            self.assertEqual(len(list(Path(tmp).rglob("candidate.joblib"))), 1)
