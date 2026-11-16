"""Accepted-artifact parity on VALIDATION only. No training or TEST replay."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import jsonschema
import numpy as np

from v2.inference import FrozenDemandInference, InferenceError, validate_request, strict_request, verified
from v2.structure import ROOT


class FrozenInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = FrozenDemandInference()
        cls.contract = cls.runtime.contract
        cls.request = cls.runtime.request_for(1, 5, "2026-04")

    def test_all_504_validation_predictions_match_training_artifact_exactly(self):
        path = ROOT / "reports/v2/2.1.0/expanded-20261115-01/runs/alternatives-20261115-01/validation_predictions.json"
        frozen = json.loads(path.read_text())
        state = self.runtime.model.preprocessor_.to_state()
        for key, expected in zip(frozen["keys"], frozen["predictions"]["absolute_forest-d4"]):
            result = self.runtime.predict(self.runtime.request_for(*key))
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["prediction"], max(0, expected))
        self.assertEqual(state, self.runtime.model.preprocessor_.to_state())

    def test_response_schema_identity_and_frozen_metrics_context(self):
        result = self.runtime.predict(self.request)
        jsonschema.Draft202012Validator(self.contract["response_schema"], format_checker=jsonschema.FormatChecker()).validate(result)
        self.assertEqual(result["artifactSha256"], self.runtime.selection["artifact_sha256"])
        self.assertEqual(result["policyVersion"], "NONNEGATIVE_V1")
        self.assertEqual(result["historyCutoff"], "2026-04-01T00:00:00-04:00")
        self.assertIn("DATOS_SINTETICOS_NO_VALIDA_VENTAS_REALES", result["warnings"])

    def test_missing_or_extra_keys_and_v1_version_rejected(self):
        for value in [[], {}, {**self.request, "target_ventas_mes": 4}, {**self.request, "features": {}}, {**self.request, "contractVersion": "V1"}, {**self.request, "mode": "LIVE_FORECAST"}]:
            with self.subTest(value=value), self.assertRaises(InferenceError):
                validate_request(value)

    def test_ids_are_not_coerced_and_invalid_months_rejected(self):
        for value in [True, "1", 1.0, 0, -1, 2**32]:
            with self.subTest(value=value), self.assertRaises(InferenceError):
                validate_request({**self.request, "productId": value})
        for value in ["2026-00", "2026-13", "2026-4", "0999-01", None]:
            with self.subTest(value=value), self.assertRaises(InferenceError):
                validate_request({**self.request, "targetMonth": value})

    def test_unknown_entities_abstain_before_prediction(self):
        with patch.object(self.runtime.model, "predict", side_effect=AssertionError("No prediction")):
            for field, value in [("productId", 59), ("locationId", 999)]:
                result = self.runtime.predict({**self.request, field: value})
                self.assertEqual(result["reason"], "UNKNOWN_ENTITY")
                jsonschema.validate(result, self.contract["response_schema"])

    def test_wrong_snapshot_and_test_month_cannot_predict(self):
        with patch.object(self.runtime.model, "predict", side_effect=AssertionError("Never predict TEST")):
            for change in [{"historySnapshotId":"wrong-snapshot"}, {"targetMonth":"2026-07"}, {"targetMonth":"2026-10"}]:
                result = self.runtime.predict({**self.request, **change})
                self.assertEqual(result["status"], "ABSTAINED")
                self.assertEqual(result["reason"], "UNAVAILABLE_REQUIRED_FEATURE")

    def test_negative_output_clipped_without_rounding(self):
        for value, expected in [(-.75, 0), (1.23456789, 1.23456789)]:
            with patch.object(self.runtime.model, "predict", return_value=np.array([value])):
                self.assertEqual(self.runtime.predict(self.request)["prediction"], expected)

    def test_invalid_output_abstains_instead_of_subset_or_fallback(self):
        for value in [np.array([np.nan]), np.array([np.inf]), np.array([1, 2]), np.array([True]), np.array([1j])]:
            with patch.object(self.runtime.model, "predict", return_value=value):
                result = self.runtime.predict(self.request)
                self.assertIsNone(result["prediction"])
                self.assertEqual(result["reason"], "MODEL_UNAVAILABLE")
                json.dumps(result, allow_nan=False)

    def test_tampered_cached_features_rejected(self):
        key = (1, 5, "2026-04")
        index = self.runtime._features.index.get_loc(key)
        col = self.runtime._features.columns.get_loc("ventas_mes_anterior")
        original = self.runtime._features.iloc[index, col]
        try:
            self.runtime._features.iloc[index, col] = original + 1
            with self.assertRaises(InferenceError):
                self.runtime.predict(self.request)
        finally:
            self.runtime._features.iloc[index, col] = original

    def test_changed_model_parameters_rejected(self):
        model = self.runtime.model.model_
        old = model.max_depth
        try:
            model.max_depth = 8
            with self.assertRaises(InferenceError):
                self.runtime.predict(self.request)
        finally:
            model.max_depth = old

    def test_modified_binary_rejected_without_loading(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as temp:
            path = Path(temp) / "fake.joblib"
            path.write_bytes(b"not-a-model")
            with patch("joblib.load", side_effect=AssertionError("No deserialize")):
                with self.assertRaises(InferenceError):
                    verified(path, self.runtime.selection["artifact_sha256"])

    def test_json_rejects_duplicate_keys_and_nonfinite(self):
        for text in ['{"productId":1,"productId":2}', '{"x":NaN}', '{"x":Infinity}', 'x'*8193, '{broken']:
            with self.subTest(text=text[:40]), self.assertRaises(InferenceError):
                strict_request(text)


if __name__ == "__main__":
    unittest.main()
