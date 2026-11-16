"""Verify saved final evidence only. Never load TEST or predict it again."""
import csv
from datetime import datetime
import json
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from v2 import final_evaluation as final
from v2.structure import ROOT, sha256_file


class FinalSavedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dest = final.destination(ROOT)
        cls.result = json.loads((cls.dest / "result.json").read_text(encoding="utf-8"))
        cls.selection = json.loads((cls.dest / "selection_frozen.json").read_text(encoding="utf-8"))
        with (cls.dest / "predictions.csv").open(encoding="utf-8", newline="") as f:
            cls.rows = list(csv.DictReader(f))

    def test_selection_hash_and_artifact_match_frozen_evidence(self):
        marker = json.loads((self.dest / "evaluation_started.json").read_text())
        self.assertEqual(sha256_file(ROOT / "v2/contracts/selection.v2_1.json"), marker["selection_sha256"])
        self.assertEqual(sha256_file(ROOT / self.selection["artifact"]), self.selection["artifact_sha256"])
        self.assertEqual(self.result["artifact_sha256"], marker["artifact_sha256"])
        for name, digest in self.selection["input_hashes"].items():
            self.assertEqual(sha256_file(ROOT / name), digest)

    def test_selection_precedes_started_event_and_test_completion(self):
        started = json.loads((self.dest / "evaluation_started.json").read_text())
        self.assertLessEqual(datetime.fromisoformat(self.selection["frozen_at"]), datetime.fromisoformat(started["started_at"]))
        self.assertLessEqual(datetime.fromisoformat(started["started_at"]), datetime.fromisoformat(self.result["completed_at"]))
        self.assertTrue(self.selection["user_accepted"])
        self.assertFalse(self.selection["training_allowed"])

    def test_one_loader_one_predict_zero_fits(self):
        audit = json.loads((self.dest / "execution_audit.json").read_text())
        self.assertEqual(audit["test_load_calls"], 1)
        self.assertEqual(audit["selected_model_predict_calls"], 1)
        self.assertEqual(self.result["model_fit_calls"], 0)
        self.assertEqual(self.result["preprocessing_fit_calls"], 0)
        self.assertFalse(self.result["active_model_changed"])
        self.assertFalse(self.result["selection_changed_after_test"])

    def test_saved_rows_are_complete_unique_test_months(self):
        keys = {(r["productId"], r["locationId"], r["mes_objetivo"]) for r in self.rows}
        self.assertEqual(len(keys), 504)
        self.assertEqual(len(self.rows), 504)
        for month in ["2026-07", "2026-08", "2026-09"]:
            self.assertEqual(sum(r["mes_objetivo"] == month for r in self.rows), 168)

    def test_saved_metrics_reconcile_without_model_or_test_loader(self):
        y = np.array([float(r["target_ventas_mes"]) for r in self.rows])
        for column, section in [("prediction_policy", "model_metrics"), ("baseline_lag1", "baseline_metrics")]:
            p = np.array([float(r[column]) for r in self.rows])
            self.assertAlmostEqual(mean_absolute_error(y, p), self.result[section]["mae"], places=11)
            self.assertAlmostEqual(np.sqrt(mean_squared_error(y, p)), self.result[section]["rmse"], places=11)
            self.assertAlmostEqual(r2_score(y, p), self.result[section]["r2"], places=11)
        self.assertEqual(int(y.sum()), self.result["totals"]["observed"])

    def test_prediction_policy_and_tail_counts_reconcile(self):
        raw = np.array([float(r["prediction_raw"]) for r in self.rows])
        pred = np.array([float(r["prediction_policy"]) for r in self.rows])
        np.testing.assert_array_equal(np.maximum(raw, 0), pred)
        errors = np.array([float(r["absolute_error"]) for r in self.rows])
        self.assertEqual(int((errors > 40).sum()), self.result["tail"]["abs_error_gt40"])
        self.assertAlmostEqual(errors.max(), self.result["tail"]["max_absolute_error"], places=11)

    def test_groups_and_months_have_same_full_coverage(self):
        for dimension in ["product", "store", "product_store", "rotation_train", "historical_stock_coverage", "historical_mode"]:
            self.assertEqual(sum(g["rows_requested"] for g in self.result["groups"] if g["dimension"] == dimension), 504)
        self.assertEqual(sum(m["model"]["rows_requested"] for m in self.result["by_month"]), 504)

    def test_actual_final_guard_prevents_second_access_before_any_load(self):
        before = sha256_file(self.dest / "result.json")
        with patch.object(final, "read_selection", side_effect=AssertionError("No reread")), \
             patch.object(final, "load_test_once", side_effect=AssertionError("Never access TEST again")):
            with self.assertRaises(FileExistsError):
                final.evaluate(ROOT)
        self.assertEqual(sha256_file(self.dest / "result.json"), before)


if __name__ == "__main__":
    unittest.main()
