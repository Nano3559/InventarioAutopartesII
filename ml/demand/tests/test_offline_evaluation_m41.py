"""M41-01 only. Test rows are independent of every released dataset."""

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import unittest

from v2.offline_evaluation import evaluate


FIXTURE = Path(__file__).parent / "fixtures" / "m41_evaluation.json"


class OfflineEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cohort = json.loads(FIXTURE.read_bytes())

    def test_metrics_match_hand_calculations(self):
        summary = evaluate(self.cohort)["summary"]
        self.assertEqual((summary["total"], summary["eligible"], summary["covered"],
                          summary["abstained"], summary["ineligible"]), (6, 5, 4, 1, 1))
        self.assertEqual(summary["coverage"], 4 / 5)
        metrics = summary["metrics"]
        self.assertEqual(metrics["n"], 4)
        self.assertEqual(metrics["observedUnits"], 28)
        self.assertEqual(metrics["mae"], 94 / 4)
        self.assertEqual(metrics["rmse"], math.sqrt(8108 / 4))
        self.assertEqual(metrics["signedBias"], 90 / 4)
        self.assertEqual(metrics["wape"], 94 / 28)
        self.assertAlmostEqual(metrics["p90AbsoluteError"], 63.6)
        self.assertAlmostEqual(metrics["p95AbsoluteError"], 76.8)

    def test_pairs_share_the_denominator_and_skip_missing_and_abstentions(self):
        paired = evaluate(self.cohort)["summary"]["paired"]
        self.assertEqual(paired["n"], 2)
        self.assertEqual(paired["model"]["observedUnits"], 18)
        self.assertEqual(paired["baseline"]["observedUnits"], 18)
        self.assertEqual(paired["model"]["mae"], 1)
        self.assertEqual(paired["baseline"]["mae"], 2.5)
        self.assertEqual(paired["deltaMae"], -1.5)

    def test_row_errors_and_abstention_remain_explicit(self):
        rows = {r["familyId"]: r for r in evaluate(self.cohort)["rows"]}
        for family, error in (("f-exact", 0), ("f-over", 2), ("f-under", -2), ("f-extreme", 90)):
            self.assertEqual(rows[family]["signedError"], error)
            self.assertEqual(rows[family]["absoluteError"], abs(error))
        for family in ("f-abstain", "f-ineligible"):
            for field in ("forecast", "signedError", "absoluteError"):
                self.assertIsNone(rows[family][field])
        self.assertEqual(rows["f-abstain"]["abstentionReason"], "OUT_OF_DOMAIN")
        self.assertEqual(rows["f-exact"]["modelId"], self.cohort["modelId"])

    def test_groups_include_missing_labels_and_handle_empty_denominators(self):
        groups = evaluate(self.cohort)["groups"]
        self.assertEqual(len(groups), 7)
        product = {r["value"]: r for r in groups["productId"]}
        self.assertEqual(product[3]["coverage"], 0)
        self.assertEqual(product[3]["abstained"], 1)
        self.assertIsNone(product[3]["metrics"]["mae"])
        self.assertIsNone(product[4]["coverage"])
        self.assertIsNone(product[2]["paired"]["deltaMae"])
        volumes = {r["value"]: r for r in groups["volume"]}
        self.assertEqual(volumes["LOW"]["coverage"], 2 / 3)
        self.assertEqual(volumes[None]["total"], 3)
        self.assertEqual(groups["availability"][0]["value"], "AVAILABLE")
        self.assertEqual(groups["intermittency"][0]["value"], "INTERMITTENT")
        self.assertEqual(groups["locationId"][0]["total"], 6)
        self.assertEqual(groups["targetMonth"][0]["total"], 5)
        self.assertEqual(groups["incident"][0]["value"], "EXTREME")

    def test_observed_zero_and_forecast_zero_are_valid_but_wape_is_undefined(self):
        self.cohort["rows"] = [next(r for r in self.cohort["rows"] if r["familyId"] == "f-over")]
        error = evaluate(self.cohort)["summary"]["metrics"]
        self.assertEqual(error["mae"], 2)
        self.assertIsNone(error["wape"])
        self.cohort["rows"][0]["forecast"] = 0
        summary = evaluate(self.cohort)["summary"]
        self.assertEqual(summary["coverage"], 1)
        self.assertEqual(summary["metrics"]["mae"], 0)
        self.assertIsNone(summary["metrics"]["wape"])

    def test_empty_cohort_has_null_metrics_and_coverage(self):
        self.cohort["rows"] = []
        result = evaluate(self.cohort)
        self.assertEqual(result["summary"]["eligible"], 0)
        self.assertIsNone(result["summary"]["metrics"]["p95AbsoluteError"])
        self.assertIsNone(result["summary"]["coverage"])
        self.assertTrue(all(not items for items in result["groups"].values()))

    def test_order_independence_fingerprint_and_no_input_mutation(self):
        preserved = deepcopy(self.cohort)
        report = evaluate(self.cohort)
        self.assertEqual(self.cohort, preserved)
        self.cohort["rows"].reverse()
        self.assertEqual(report, evaluate(self.cohort))
        self.assertEqual([r["targetMonth"] for r in report["rows"]],
                         sorted(r["targetMonth"] for r in report["rows"]))
        report["rows"][0]["provenance"].clear()
        self.assertEqual(list(reversed(self.cohort["rows"])), preserved["rows"])

    def test_duplicate_row_rejected_even_when_prediction_differs(self):
        duplicate = deepcopy(self.cohort["rows"][0])
        duplicate["forecast"] = 1
        self.cohort["rows"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            evaluate(self.cohort)

    def test_schema_and_values_fail_closed(self):
        for key, value in (("observed", True), ("forecast", -1), ("forecast", float("nan")),
                           ("forecast", float("inf")), ("productId", "2"), ("targetMonth", "2027-13"),
                           ("forecast", None), ("realizedStockoutFeature", 2), ("status", "ABSTAINED")):
            with self.subTest(key=key, value=value):
                invalid = deepcopy(self.cohort)
                invalid["rows"][0][key] = value
                with self.assertRaises(ValueError):
                    evaluate(invalid)
        self.cohort["schema"] = "unknown"
        with self.assertRaises(ValueError):
            evaluate(self.cohort)

    def test_temporal_guards(self):
        for key, value in (("cutoffAt", "2027-01-01T00:00:00"),
                           ("cutoffAt", "2027-01-02T00:00:00-04:00"),
                           ("observedAt", "2027-01-31T23:59:59-04:00"),
                           ("issuedAt", "2027-01-01T04:00:01Z"),
                           ("baselineIssuedAt", "2027-01-02T00:00:00-04:00"),
                           ("classifiedAt", "2027-02-01T00:00:00-04:00")):
            with self.subTest(key=key):
                invalid = deepcopy(self.cohort)
                invalid["rows"][1][key] = value
                with self.assertRaises(ValueError):
                    evaluate(invalid)

    def test_frozen_partition_and_unapproved_future_input_rejected(self):
        for key, value in (("kind", "TEST"), ("datasetVersion", "4.0.0"), ("kind", "AUTHORIZED_FUTURE")):
            with self.subTest(key=key):
                invalid = deepcopy(self.cohort)
                invalid[key] = value
                with self.assertRaises(ValueError):
                    evaluate(invalid)
        future = dict(self.cohort, kind="AUTHORIZED_FUTURE", datasetVersion="future-cohort", authorizationRef="fixture-approval")
        self.assertEqual(evaluate(future)["summary"]["eligible"], 5)
        future["rows"][0]["targetMonth"] = "2026-10"
        with self.assertRaisesRegex(ValueError, "after the frozen TEST"):
            evaluate(future)

    def test_provenance_requires_pinned_source_references(self):
        projection = [{k: v for k, v in row.items() if k != "provenance"} for row in self.cohort["rows"]]
        raw = json.dumps(projection, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.cohort["sources"]["fixture-evidence"])
        invalid = deepcopy(self.cohort)
        invalid["rows"][0]["provenance"]["observed"] = "unregistered"
        with self.assertRaisesRegex(ValueError, "source reference"):
            evaluate(invalid)
        self.cohort["sources"]["fixture-evidence"] = "invalid"
        with self.assertRaisesRegex(ValueError, "Invalid sources"):
            evaluate(self.cohort)


if __name__ == "__main__":
    unittest.main()
