"""Reglas del contrato propuesto. No ejecuta API, generación o entrenamiento."""
import json
from pathlib import Path
import re
import unittest

from jsonschema import Draft202012Validator
from v2.structure import strict_format_checker, validate_contract

ROOT = Path(__file__).resolve().parents[1]


class PreparationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT / "v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))
        cls.schema = cls.contract["inference_design"]["request_schema"]
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)
        response_schema = cls.contract["inference_design"]["response_schema"]
        Draft202012Validator.check_schema(response_schema)
        cls.response_validator = Draft202012Validator(response_schema, format_checker=strict_format_checker())

    def request(self):
        return dict(contractVersion="v2-preparation-1", productId=1, locationId=5,
                    targetMonth="2026-12", historySnapshotId="snapshot-1")

    def test_valid_selection_is_accepted(self):
        self.validator.validate(self.request())

    def test_target_and_future_observations_are_not_client_inputs(self):
        for name in ("target_ventas_mes", "total", "stock", "unitPrice", "ventas_mes_objetivo", "exchangeRate"):
            value = self.request()
            value[name] = 100
            self.assertFalse(self.validator.is_valid(value), name)

    def test_ids_reject_boolean_string_negative_and_overflow(self):
        for name in ("productId", "locationId"):
            for bad in (True, "1", -1, 0, 1.5, None, 2147483648):
                value = self.request()
                value[name] = bad
                self.assertFalse(self.validator.is_valid(value), (name, bad))

    def test_month_requires_complete_unambiguous_calendar_month(self):
        for bad in ("0000-01", "2026-00", "2026-13", "26-12", "2026-12-01", "12/2026", "2026-1", None):
            value = self.request()
            value["targetMonth"] = bad
            self.assertFalse(self.validator.is_valid(value), bad)

    def test_snapshot_cannot_be_a_path_or_empty(self):
        for bad in ("../secret", "/tmp/data", "", "x" * 129, "a/b", "a\\b"):
            value = self.request()
            value["historySnapshotId"] = bad
            self.assertFalse(self.validator.is_valid(value), bad)

    def test_missing_context_and_wrong_contract_are_rejected(self):
        for key in self.request():
            value = self.request()
            value.pop(key)
            self.assertFalse(self.validator.is_valid(value), key)
        value = self.request()
        value["contractVersion"] = "V1"
        self.assertFalse(self.validator.is_valid(value))

    def test_all_physical_references_exist_in_current_prisma(self):
        text = (ROOT.parents[1] / "backend/prisma/schema.prisma").read_text(encoding="utf-8")
        models = {name: set(re.findall(r"^\s+(\w+)\s+", body, re.M))
                  for name, body in re.findall(r"model\s+(\w+)\s*\{([^}]+)\}", text)}
        for group in self.contract["candidate_groups"]:
            for physical in group["physical_fields"]:
                model, column = physical.split(".")
                self.assertIn(column, models[model], physical)

    def test_features_exclude_identifiers_and_target(self):
        columns = self.contract["initial_columns"]
        names = [c["name"] for c in columns]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual({c["name"] for c in columns if c["role"] == "FEATURE"},
                         {"ventas_mes_anterior", "ventas_hace_2_meses", "ventas_hace_3_meses", "mes_sin", "mes_cos"})
        self.assertEqual([c["name"] for c in columns if c["role"] == "TARGET"], ["target_ventas_mes"])
        self.assertNotIn("promedio_3_meses", names)

    def response(self):
        return dict(status="OK", contractVersion="v2-preparation-1", productId=1, locationId=5,
                    targetMonth="2026-12", issuedAt="2026-12-01T04:00:00Z", historyCutoff="2026-12-01T04:00:00Z",
                    horizonMonths=1, prediction=17.25, modelVersion="test-only", datasetVersion="test-only",
                    buildId="test-only", historySnapshotId="test-only", origin="SYNTHETIC", mode="ACADEMIC_REPLAY",
                    warnings=["DATOS_SINTETICOS_NO_VALIDA_VENTAS_REALES"], evaluationContext=None)

    def test_synthetic_result_requires_visible_origin_and_replay(self):
        value = self.response()
        self.response_validator.validate(value)
        for field, bad in (("mode", "LIVE_FORECAST"), ("warnings", [])):
            invalid = dict(value, **{field: bad})
            self.assertFalse(self.response_validator.is_valid(invalid))

    def test_negative_prediction_is_rejected_but_fractional_forecast_is_allowed(self):
        value = self.response()
        value["prediction"] = -0.1
        self.assertFalse(self.response_validator.is_valid(value))
        value["prediction"] = 0
        self.response_validator.validate(value)

    def test_success_requires_artifact_identity(self):
        for field in ("modelVersion", "datasetVersion", "buildId"):
            value = self.response()
            value[field] = None
            self.assertFalse(self.response_validator.is_valid(value), field)

    def test_abstention_never_returns_zero_as_invented_forecast(self):
        value = self.response()
        value.update(status="ABSTAINED", prediction=None, reason="INSUFFICIENT_HISTORY", modelVersion=None,
                     datasetVersion=None, buildId=None)
        self.response_validator.validate(value)
        value["prediction"] = 0
        self.assertFalse(self.response_validator.is_valid(value))

    def test_abstention_requires_reason_and_cannot_keep_old_metrics(self):
        value = self.response()
        value.update(status="ABSTAINED", prediction=None)
        self.assertFalse(self.response_validator.is_valid(value))
        value["reason"] = "MODEL_UNAVAILABLE"
        value["evaluationContext"] = dict(origin="SYNTHETIC", split="TEST", mae=2.4, rmse=3.1, r2=0.4)
        self.assertFalse(self.response_validator.is_valid(value))

    def test_metric_context_requires_source_and_allows_negative_r2(self):
        value = self.response()
        value["evaluationContext"] = dict(origin="SYNTHETIC", split="TEST", mae=2.4, rmse=3.1, r2=-0.4)
        self.response_validator.validate(value)
        value["evaluationContext"]["mae"] = -1
        self.assertFalse(self.response_validator.is_valid(value))
        value["evaluationContext"] = dict(split="TEST", mae=2.4, rmse=3.1, r2=0.4)
        self.assertFalse(self.response_validator.is_valid(value))

    def test_response_dates_require_timezone_and_valid_calendar(self):
        for bad in ("2026-12-01T00:00:00", "2026-02-30T04:00:00Z", "ayer"):
            value = self.response()
            value["historyCutoff"] = bad
            self.assertFalse(self.response_validator.is_valid(value), bad)

    def test_date_time_validation_accepts_leap_day_and_explicit_offset(self):
        value = self.response()
        for valid in ("2024-02-29T23:59:59-04:00", "2026-12-01T04:00:00.123Z", "2026-12-01T00:00:00-04:00"):
            value["historyCutoff"] = valid
            self.response_validator.validate(value)
        for bad in ("2025-02-29T00:00:00Z", "2026-12-01T24:00:00Z", "2026-12-01T00:00:00+24:00", "2026-12-01T00:00:00+00:99"):
            value["historyCutoff"] = bad
            self.assertFalse(self.response_validator.is_valid(value), bad)

    def test_source_manifest_date_check_uses_the_same_strict_validator(self):
        from jsonschema import ValidationError
        path = next((ROOT / "sources/manifests/monash_car_parts").glob("*.json"))
        value = json.loads(path.read_text(encoding="utf-8"))
        validate_contract(value, "source_manifest")
        for invalid in ("2026-11-14T12:00:00", "2026-02-30T12:00:00Z"):
            value["verified_at"] = invalid
            with self.assertRaises(ValidationError):
                validate_contract(value, "source_manifest")

    def test_success_field_list_and_schema_agree(self):
        design = self.contract["inference_design"]
        self.assertEqual(set(design["success_fields"]), set(design["response_schema"]["required"]))


if __name__ == "__main__":
    unittest.main()
