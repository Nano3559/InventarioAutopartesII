"""Checks frozen authorized results, without fitting or accessing TEST."""
import csv
import json
import unittest
from unittest.mock import patch

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from v2.experiments import load_xy, choose
from v2.preprocessing import DemandPreprocessor
from v2.structure import ROOT, sha256_file
from v2.validate_build import canonical_hash

RUN = "training-20261115-01"
REPORT = ROOT / "reports/v2/2.1.0/expanded-20261115-01/runs" / RUN
MODEL = ROOT / "models/v2" / RUN


class FrozenTrainingResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads((REPORT / "comparison.json").read_text(encoding="utf-8"))
        cls.audit = json.loads((REPORT / "execution_audit.json").read_text(encoding="utf-8"))
        cls.X, cls.y = load_xy("VALIDATION")
        assert sha256_file(MODEL / "candidate.joblib") == cls.summary["artifact_sha256"]
        cls.pipeline = joblib.load(MODEL / "candidate.joblib")

    def test_all_actual_fits_used_only_approved_train_windows(self):
        events = self.audit["fit_events"]
        models = [e for e in events if e["class"] != "DemandPreprocessor"]
        self.assertEqual(len(models), 102)
        self.assertEqual(len(events), 204)
        self.assertTrue(all(e["status"] == "PASSED" for e in events))
        self.assertTrue(all(e["window"][0] == "2025-01" and e["window"][1] <= "2026-03" for e in events))
        self.assertFalse(any(e["partition"] == "TEST" for e in self.audit["loads"]))

    def test_complete_comparison_and_no_omitted_failures(self):
        records = self.summary["records"]
        self.assertEqual(len(records), 103)
        self.assertEqual(sum(r["fold_id"] == "OUTER" for r in records), 13)
        self.assertTrue(all(r["score"]["status"] == "OK" and r["score"]["abstentions"] == 0 for r in records))
        self.assertTrue(all(r["score"]["rows_requested"] == 504 for r in records))
        self.assertFalse(self.summary["test_loaded"])
        self.assertFalse(self.summary["selection"]["active_model_changed"])

    def test_baseline_metrics_independently_recomputed_on_validation(self):
        record = next(r for r in self.summary["records"] if r["candidate"]["model"] == "baseline")
        pred = self.X["ventas_mes_anterior"].to_numpy()
        self.assertAlmostEqual(record["score"]["mae"], mean_absolute_error(self.y, pred), places=11)
        self.assertAlmostEqual(record["score"]["rmse"], np.sqrt(mean_squared_error(self.y, pred)), places=11)
        self.assertAlmostEqual(record["score"]["r2"], r2_score(self.y, pred), places=11)

    def test_selected_artifact_reproduces_validation_metrics_without_fit(self):
        with patch.object(DemandPreprocessor, "fit", side_effect=AssertionError("No refit")):
            pred = self.pipeline.predict(self.X)
        record = next(r for r in self.summary["records"] if r["fold_id"] == "OUTER" and r["candidate"]["candidate_id"] == self.summary["selection"]["candidate_id"])
        clipped = np.maximum(pred, 0)
        self.assertAlmostEqual(record["score"]["mae"], mean_absolute_error(self.y, clipped), places=11)
        self.assertAlmostEqual(record["score"]["rmse"], np.sqrt(mean_squared_error(self.y, clipped)), places=11)
        self.assertAlmostEqual(record["score"]["r2"], r2_score(self.y, clipped), places=11)

    def test_restored_preprocessing_matches_frozen_pipeline(self):
        state = json.loads((MODEL / "preprocessing.json").read_text(encoding="utf-8"))
        adapter = DemandPreprocessor.from_state(state)
        np.testing.assert_allclose(adapter.transform(self.X), self.pipeline.named_steps["preprocessing"].transform(self.X), rtol=0, atol=0)
        state = state["state"]
        self.assertEqual(state["train_window"], ["2025-01", "2026-03"])
        self.assertEqual(state["fit_rows"], 2520)
        self.assertFalse(state["y_used"])
        X, _ = load_xy("TRAIN")
        self.assertEqual(state["fit_row_keys_sha256"], canonical_hash([list(k) for k in X.index]))

    def test_winner_selected_from_validation_and_review_not_bypassed(self):
        outer = [r for r in self.summary["records"] if r["fold_id"] == "OUTER"]
        selected = choose(outer, 1e-9)
        self.assertEqual(selected["candidate"]["candidate_id"], self.summary["selection"]["candidate_id"])
        self.assertEqual(self.summary["selection"]["test_status"], "RESERVED_NOT_LOADED")
        if self.summary["selection"]["review_reasons"]:
            self.assertEqual(self.summary["selection"]["status"], "REVIEW_REQUIRED")

    def test_tracking_records_same_run_and_model_hash(self):
        path = ROOT / "reports/v2/2.1.0/expanded-20261115-01/experiments.csv"
        with path.open(encoding="utf-8", newline="") as f:
            rows = [r for r in csv.DictReader(f) if r["run_id"] == RUN]
        self.assertEqual(len(rows), 103)
        self.assertFalse(any(r["evaluation_partition"] == "TEST" for r in rows))
        hashes = [r["artifact_sha256"] for r in rows if r["artifact_sha256"]]
        self.assertEqual(hashes, [self.summary["artifact_sha256"]])

    def test_execution_permission_was_scoped_and_restored(self):
        self.assertTrue(self.audit["runner_contract_restored"])
        self.assertFalse(json.loads((ROOT / "v2/contracts/runner.v2_1.json").read_text(encoding="utf-8"))["model_training_authorized"])
        self.assertEqual(sha256_file(ROOT / "v2/contracts/runner.v2_1.json"), self.audit["runner_contract_before_sha256"])


if __name__ == "__main__":
    unittest.main()
