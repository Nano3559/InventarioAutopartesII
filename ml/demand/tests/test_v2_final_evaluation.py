"""One-shot guard tested with temporary fixtures. Never loads actual TEST."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v2 import final_evaluation as final
from v2.structure import ROOT, sha256_file


class FinalEvaluationGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "tmp", prefix="final-guard-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        path = self.root / "v2/contracts"
        path.mkdir(parents=True)
        self.selection = dict(evaluation_version=final.VERSION, accepted_candidate="absolute_forest-d4",
            user_accepted=True, test_authorization="ONE_FINAL_EVALUATION_NO_RETRAINING", selection_id="fixture-only",
            artifact_sha256="fixture-no-model", input_hashes={},
            prediction_policy=dict(version="NONNEGATIVE_V1", nonfinite="REJECT_ALL_NO_SUBSET", negative="CLIP_ZERO", rounding="NONE"),
            evaluation_implementation_sha256=sha256_file(Path(final.__file__)))
        self.path = path / "selection.v2_1.json"
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.selection), encoding="utf-8")

    def test_reservation_is_shared_for_entire_build(self):
        dest = final.reserve(self.root, self.selection, "fixture")
        changed = dict(self.selection, selection_id="different-id")
        with self.assertRaises(FileExistsError):
            final.reserve(self.root, changed, "different-hash")
        self.assertEqual(json.loads((dest / "evaluation_started.json").read_text())["selection_id"], "fixture-only")

    def test_success_cannot_invoke_operation_twice(self):
        with patch.object(final, "load_accepted_model", return_value=object()), \
             patch.object(final, "evaluate_reserved", return_value={"fixture": True}) as operation:
            final.evaluate(self.root)
            with self.assertRaises(FileExistsError):
                final.evaluate(self.root)
            self.assertEqual(operation.call_count, 1)

    def test_failure_remains_consumed_and_cannot_retry(self):
        with patch.object(final, "load_accepted_model", return_value=object()), \
             patch.object(final, "evaluate_reserved", side_effect=RuntimeError("fixture error")) as operation:
            with self.assertRaises(RuntimeError):
                final.evaluate(self.root)
            with self.assertRaises(FileExistsError):
                final.evaluate(self.root)
            self.assertEqual(operation.call_count, 1)
        self.assertTrue((final.destination(self.root) / "failure.json").exists())

    def test_policy_change_rejected_before_any_loader(self):
        self.selection["prediction_policy"]["rounding"] = "ROUND_INTEGER"
        self.save()
        with patch.object(final, "load_test_once", side_effect=AssertionError("No actual TEST")):
            with self.assertRaises(ValueError):
                final.evaluate(self.root)
        self.assertFalse(final.destination(self.root).exists())

    def test_missing_authorization_rejected(self):
        self.selection["user_accepted"] = False
        self.save()
        with self.assertRaises(PermissionError):
            final.read_selection(self.root)

    def test_changed_pinned_input_rejected(self):
        self.selection["input_hashes"] = {"v2/contracts/selection.v2_1.json": "0" * 64}
        self.save()
        with self.assertRaises(ValueError):
            final.read_selection(self.root)

    def test_existing_guard_rejects_before_model_or_labels(self):
        final.reserve(self.root, self.selection, "fixture")
        with patch.object(final, "read_selection", side_effect=AssertionError("No reads")), \
             patch.object(final, "load_test_once", side_effect=AssertionError("No actual TEST")):
            with self.assertRaises(FileExistsError):
                final.evaluate(self.root)


if __name__ == "__main__":
    unittest.main()
