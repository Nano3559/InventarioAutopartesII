"""Server-side snapshots for V2 administrator API. No TEST or training."""
import unittest
from unittest.mock import patch
import json
import jsonschema

import admin_prediction_v2 as admin
from v2.inference_v2_2 import FrozenDemandInference, InferenceError
from v2.structure import ROOT


class AdminV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = FrozenDemandInference()

    def setUp(self):
        self.provider = patch.object(admin, "FrozenDemandInference", return_value=self.runtime)
        self.provider.start()
        self.addCleanup(self.provider.stop)

    def test_catalog_uses_only_approved_products_and_months(self):
        r = admin.query({"action":"catalog"})
        self.assertEqual(len(r["products"]), 56)
        self.assertEqual({x["id"] for x in r["locations"]}, {5, 6, 7})
        self.assertEqual(r["availableTargetMonths"], ["2026-04", "2026-05", "2026-06"])
        self.assertEqual(r["version"], "V2.2.0")

    def test_default_snapshot_is_june_and_history_is_only_previous_months(self):
        r = admin.query({"productId":20,"locationId":5})
        self.assertEqual(r["prediction"], 0)
        self.assertEqual(r["targetMonth"], "2026-06")
        self.assertEqual(r["baseline"], 2)
        self.assertEqual([x["month"] for x in r["history"]], ["2026-03", "2026-04", "2026-05"])
        self.assertEqual(r["artifactSha256"], self.runtime.selection["artifact_sha256"])

    def test_explicit_snapshot_matches_and_bad_snapshot_never_predicts(self):
        req = self.runtime.request_for(20, 5, "2026-04")
        good = {k:req[k] for k in ["productId","locationId","targetMonth","historySnapshotId"]}
        self.assertEqual(admin.query(good)["prediction"], self.runtime.predict(req)["prediction"])
        with patch.object(self.runtime.model,"predict",side_effect=AssertionError("Do not predict")):
            with self.assertRaises(InferenceError) as error:
                admin.query({**good,"historySnapshotId":"different"})
            self.assertEqual(error.exception.code,"SNAPSHOT_MISMATCH")

    def test_test_period_and_unknown_entities_never_predict(self):
        with patch.object(self.runtime.model,"predict",side_effect=AssertionError("Never predict TEST")):
            for request,code in [({"productId":20,"locationId":5,"targetMonth":"2026-07"},"UNAVAILABLE_REQUIRED_FEATURE"),({"productId":59,"locationId":5},"UNKNOWN_ENTITY")]:
                with self.subTest(request=request),self.assertRaises(InferenceError) as error:
                    admin.query(request)
                self.assertEqual(error.exception.code,code)

    def test_invalid_payloads_rejected(self):
        for request in [[],{}, {"productId":True,"locationId":5},{"productId":20,"locationId":5,"target_ventas_mes":100},{"productId":20,"locationId":5,"model":"V1"},{"action":"catalog","extra":True},{"productId":20,"locationId":5,"historySnapshotId":"x"}]:
            with self.subTest(request=request),self.assertRaises(InferenceError):
                admin.query(request)

    def test_v1_is_not_used_as_fallback(self):
        with patch("admin_prediction.query",side_effect=AssertionError("V1 forbidden")):
            self.assertEqual(admin.query({"productId":20,"locationId":5})["version"],"V2.2.0")

    def test_public_api_schema_matches_adapter_and_rejects_extra_features(self):
        contract=json.loads((ROOT/"v2/contracts/admin_api.v2_2.json").read_text())
        request={"productId":20,"locationId":5}
        jsonschema.validate(request,contract["request_schema"])
        jsonschema.validate(admin.query(request),contract["success_response_schema"])
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({**request,"features":{}},contract["request_schema"])


if __name__ == "__main__":
    unittest.main()
