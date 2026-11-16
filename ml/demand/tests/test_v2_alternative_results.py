"""Frozen exploratory results: no refits and no TEST evaluation."""
import json
import unittest
from unittest.mock import patch

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

from v2.alternatives import AlternativeForecaster, execute
from v2.experiments import load_xy, score_predictions
from v2.preprocessing import DemandPreprocessor
from v2.structure import ROOT, sha256_file

RUN = ROOT / "reports/v2/2.1.0/expanded-20261115-01/runs/alternatives-20261115-01"


class AlternativeResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = json.loads((RUN / "comparison.json").read_text(encoding="utf-8"))
        cls.predictions = json.loads((RUN / "validation_predictions.json").read_text(encoding="utf-8"))
        cls.plan = json.loads((RUN / "frozen_plan.json").read_text(encoding="utf-8"))
        cls.V, cls.y = load_xy("VALIDATION")

    def test_42_internal_and_9_outer_evaluations_have_complete_coverage(self):
        self.assertEqual(len(self.summary["cv"]), 42)
        self.assertEqual(len(self.summary["outer"]), 9)
        self.assertEqual(self.summary["actual_forest_fits"], 25)
        self.assertFalse(self.summary["test_loaded"])
        self.assertFalse(self.summary["active_model_changed"])
        self.assertTrue(self.summary["reused_validation"])
        for r in self.summary["cv"] + self.summary["outer"]:
            self.assertEqual(r["score"]["status"], "OK")
            self.assertEqual(r["score"]["rows_scored"], 504)
            self.assertEqual(r["score"]["abstentions"], 0)

    def test_prediction_keys_and_labels_match_validation_exactly(self):
        self.assertEqual(self.predictions["keys"], [list(k) for k in self.V.index])
        self.assertEqual(self.predictions["observed"], self.y.tolist())

    def test_all_metrics_reproduce_from_frozen_row_predictions(self):
        for row in self.summary["outer"]:
            actual = score_predictions(self.y, self.predictions["predictions"][row["spec"]["id"]])
            for name in ["mae", "rmse", "r2"]:
                self.assertAlmostEqual(actual[name], row["score"][name], places=11)

    def test_configuration_selection_used_internal_train_scores(self):
        for outer in self.summary["outer"]:
            family = outer["spec"]["family"]
            candidates = [s for s in self.plan["options"] if s["family"] == family]
            if not candidates:
                continue
            means = {s["id"]: np.mean([r["score"]["mae"] for r in self.summary["cv"] if r["spec"] == s]) for s in candidates}
            self.assertLessEqual(means[outer["spec"]["id"]], min(means.values()) + 1e-9)

    def test_all_saved_models_reload_without_any_fit(self):
        with patch.object(AlternativeForecaster, "fit", side_effect=AssertionError("No refit")), \
             patch.object(RandomForestRegressor, "fit", side_effect=AssertionError("No refit")), \
             patch.object(DemandPreprocessor, "fit", side_effect=AssertionError("No refit")):
            for row in self.summary["outer"]:
                if "artifact" not in row:
                    continue
                path = ROOT / row["artifact"]
                self.assertEqual(sha256_file(path), row["artifact_sha256"])
                model = joblib.load(path)
                np.testing.assert_array_equal(model.predict(self.V), self.predictions["predictions"][row["spec"]["id"]])
                self.assertTrue(all(k[2] <= "2026-03" for k in model.history_))

    def test_routing_uses_only_frozen_train_rotation(self):
        row = next(r for r in self.summary["outer"] if r["spec"]["family"] == "low_median_routing")
        model = joblib.load(ROOT / row["artifact"])
        mask = np.array([model.rotation_[k[:2]] in ("LOW", "ZERO") for k in self.V.index])
        pred = np.array(self.predictions["predictions"][row["spec"]["id"]])
        medians = np.median(self.V[["ventas_mes_anterior", "ventas_hace_2_meses", "ventas_hace_3_meses"]], axis=1)
        np.testing.assert_array_equal(pred[mask], medians[mask])
        previous = np.array(self.predictions["predictions"]["previous_squared_forest"])
        np.testing.assert_array_equal(pred[~mask], previous[~mask])

    def test_original_reference_scores_remain_unchanged(self):
        previous = json.loads((RUN.parent / "training-20261115-01/comparison.json").read_text(encoding="utf-8"))
        original = next(r for r in previous["records"] if r["fold_id"] == "OUTER" and r["candidate"]["candidate_id"] == previous["selection"]["candidate_id"])
        reference = next(r for r in self.summary["outer"] if r["spec"]["family"] == "previous_frozen_reference")
        self.assertEqual(original["score"], reference["score"])

    def test_frozen_plan_and_input_hashes_have_not_changed(self):
        self.assertEqual(sha256_file(RUN / "frozen_plan.json"), self.summary["plan_sha256"])
        for name, digest in self.plan["input_hashes"].items():
            self.assertEqual(sha256_file(ROOT / name), digest)
        self.assertEqual(sha256_file(ROOT / "v2/alternatives.py"), self.plan["implementation_sha256"])

    def test_same_run_cannot_overwrite_or_start_additional_fits(self):
        before = sha256_file(RUN / "comparison.json")
        with patch.object(AlternativeForecaster, "fit", side_effect=AssertionError("No additional fit")):
            with self.assertRaises(FileExistsError):
                execute("alternatives-20261115-01", ROOT / "v2/contracts/alternatives.v2_1.json")
        self.assertEqual(sha256_file(RUN / "comparison.json"), before)


if __name__ == "__main__":
    unittest.main()
