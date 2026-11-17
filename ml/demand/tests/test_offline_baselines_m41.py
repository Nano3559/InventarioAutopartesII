"""M41-04 checks using only independent synthetic histories."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from v2.offline_baselines import attach_to_cohort, forecast
from v2.offline_evaluation import evaluate


FIXTURES = Path(__file__).parent / "fixtures"
HISTORY = FIXTURES / "m41_baseline_histories.json"
CASES = json.loads(HISTORY.read_bytes())
SHA = hashlib.sha256(HISTORY.read_bytes()).hexdigest()


def timestamp(index):
    year, month = divmod(index, 12)
    return f"{year:04d}-{month + 1:02d}-01T00:00:00-04:00"


def request(values, *, target=2027 * 12 + 8, product=1, family="baseline-fixture"):
    rows = []
    for i, value in enumerate(values, start=target - len(values)):
        month = timestamp(i)[:7]
        rows.append({"productId": product, "locationId": 5, "month": month,
                     "observationId": "obs-" + month, "observed": value, "closureStatus": "CLOSED",
                     "complete": True, "availableAt": timestamp(i + 1), "stockAvailable": None,
                     "provenance": {"sourceId": "baseline-fixture", "sha256": SHA}})
    return {"targetMonth": timestamp(target)[:7], "cutoffAt": timestamp(target), "productId": product,
            "locationId": 5, "familyId": family, "history": rows}


class BaselineTests(unittest.TestCase):
    def assert_abstained(self, result, reason):
        self.assertEqual(result["status"], "ABSTAINED")
        self.assertIsNone(result["forecast"])
        self.assertEqual(result["abstentionReason"], reason)
        self.assertEqual(result["observationsUsed"], [])

    def test_lag1_and_moving_average(self):
        for case, lag, average in (("constant", 6, 6), ("increasing", 6, 5), ("decreasing", 2, 3)):
            with self.subTest(case=case):
                x = request(CASES[case])
                self.assertEqual(forecast(x, "lag1")["forecast"], lag)
                result = forecast(x, "moving_average", k=2)
                self.assertEqual((result["forecast"], result["parameters"]), (average, {"k": 2}))
                self.assertEqual(result["observationsUsed"], x["history"][-2:])

    def test_gap_cannot_be_replaced_or_bridged(self):
        x = request(CASES["constant"])
        x["history"].pop()
        for method, parameters in (("lag1", {}), ("moving_average", {"k": 2}),
                                   ("sba", {"alpha": .5}), ("tsb", {"alpha": .5, "beta": .5})):
            self.assert_abstained(forecast(x, method, **parameters), "MONTH_MISSING")
        x = request([9, 0, 4, 0])
        del x["history"][1]
        self.assert_abstained(forecast(x, "sba", alpha=.5), "INSUFFICIENT_POSITIVE_MONTHS")
        self.assertEqual(forecast(x, "tsb", alpha=.5, beta=.5)["forecast"], 2)

    def test_incomplete_late_unknown_and_null_last_month(self):
        for key, value, reason in (("complete", False, "MONTH_NOT_COMPLETE"),
                                   ("closureStatus", "OPEN", "MONTH_NOT_COMPLETE"),
                                   ("availableAt", "2027-09-01T04:00:01Z", "AVAILABLE_AFTER_CUTOFF"),
                                   ("availableAt", None, "AVAILABILITY_UNKNOWN"),
                                   ("observed", None, "OBSERVED_MISSING")):
            with self.subTest(key=key, value=value):
                x = request(CASES["constant"])
                x["history"][-1][key] = value
                self.assert_abstained(forecast(x, "lag1"), reason)
                self.assert_abstained(forecast(x, "moving_average", k=2), reason)

    def test_empty_short_or_all_zero_history(self):
        self.assert_abstained(forecast(request([]), "lag1"), "NO_HISTORY")
        self.assert_abstained(forecast(request([1]), "moving_average", k=2), "MONTH_MISSING")
        zeros = request(CASES["allZero"])
        self.assertEqual(forecast(zeros, "lag1")["forecast"], 0)
        self.assertEqual(forecast(zeros, "moving_average", k=3)["forecast"], 0)
        self.assert_abstained(forecast(zeros, "sba", alpha=.5), "INSUFFICIENT_POSITIVE_MONTHS")
        self.assert_abstained(forecast(zeros, "tsb", alpha=.5, beta=.5), "INSUFFICIENT_POSITIVE_MONTHS")

    def test_sba_manual_initialization_and_updates(self):
        initial = forecast(request(CASES["sbaInitialization"]), "sba", alpha=.5)
        self.assertEqual(initial["forecast"], .75 * 10 / 2)
        x = request(CASES["intermittent"])
        result = forecast(x, "sba", alpha=.5)
        self.assertAlmostEqual(result["forecast"], .75 * 7 / 2.5)
        self.assertEqual(result["observationsUsed"], x["history"])

    def test_tsb_manual_updates_and_zero_streak(self):
        x = request(CASES["intermittent"])
        result = forecast(x, "tsb", alpha=.5, beta=.5)
        self.assertEqual(result["forecast"], .296875 * 7)
        self.assertEqual(result["observationsUsed"], x["history"])
        self.assertEqual(forecast(request(CASES["tsbZeroStreak"]), "tsb", alpha=.5, beta=.5)["forecast"], .25)

    def test_seasonal_requires_exact_anchor_and_accepts_valid_zero(self):
        x = request(CASES["seasonal"])
        self.assertEqual(forecast(x, "seasonal_naive")["forecast"], 17)
        x["history"][0]["observed"] = 0
        self.assertEqual(forecast(x, "seasonal_naive")["forecast"], 0)
        x["history"][0]["availableAt"] = "2027-09-02T00:00:00-04:00"
        self.assert_abstained(forecast(x, "seasonal_naive"), "AVAILABLE_AFTER_CUTOFF")
        x["history"].pop(0)
        self.assert_abstained(forecast(x, "seasonal_naive"), "SEASONAL_ANCHOR_MISSING")

    def test_invalid_values_entities_and_dates_are_rejected(self):
        for key, value in (("productId", 2), ("locationId", 6), ("observed", -1), ("observed", True),
                           ("observed", float("nan")), ("observed", float("inf")),
                           ("month", "2027-09"), ("month", "2027-10"),
                           ("availableAt", "2027-08-02T00:00:00-04:00"),
                           ("availableAt", "2027-09-01T00:00:00"), ("provenance", {})):
            with self.subTest(key=key, value=value):
                x = request([5])
                x["history"][0][key] = value
                with self.assertRaises(ValueError):
                    forecast(x, "lag1")

    def test_duplicate_month_and_observation_id(self):
        for key in ("month", "observationId"):
            x = request([1, 2])
            x["history"][1][key] = x["history"][0][key]
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "uplicate"):
                forecast(x, "lag1")

    def test_parameter_validation(self):
        for method, params in (("moving_average", {}), ("moving_average", {"k": 0}),
                               ("moving_average", {"k": True}), ("sba", {"alpha": 0}),
                               ("tsb", {"alpha": .5}), ("tsb", {"alpha": .5, "beta": float("inf")}),
                               ("lag1", {"k": 1}), ("not-a-method", {})):
            with self.subTest(method=method, params=params), self.assertRaises(ValueError):
                forecast(request([1, 2]), method, **params)

    def test_determinism_and_independent_result_memory(self):
        x = request(CASES["intermittent"])
        original = deepcopy(x)
        result = forecast(x, "tsb", alpha=.25, beta=.5)
        self.assertEqual(x, original)
        self.assertEqual(result, forecast(dict(x, history=list(reversed(x["history"]))), "tsb", beta=.5, alpha=.25))
        result["observationsUsed"][0]["provenance"].clear()
        self.assertEqual(x, original)


class EvaluationAdapterTests(unittest.TestCase):
    def fixture(self):
        cohort = json.loads((FIXTURES / "m41_evaluation.json").read_bytes())
        cohort.pop("baselineId")
        for row in cohort["rows"]:
            row.pop("baseline", None)
            row.pop("baselineIssuedAt", None)
            row["provenance"].pop("baseline", None)
        cohort["sources"]["baseline-evidence"] = SHA
        return cohort

    def emission(self, family="f-exact", values=(0,)):
        inputs = request(values, target=2027 * 12, family=family)
        return {"result": forecast(inputs, "lag1"), "issuedAt": inputs["cutoffAt"], "sourceId": "baseline-evidence"}

    def test_pairing_in_existing_evaluator_preserves_abstention_and_zero(self):
        cohort = self.fixture()
        original = deepcopy(cohort)
        x = attach_to_cohort(cohort, [self.emission(), self.emission(family="f-under", values=())])
        result = evaluate(x)
        self.assertEqual(result["summary"]["paired"]["n"], 1)
        self.assertEqual(result["summary"]["paired"]["baseline"]["mae"], 10)
        rows = {r["familyId"]: r for r in result["rows"]}
        self.assertEqual(rows["f-exact"]["baseline"], 0)
        self.assertIsNone(rows["f-under"].get("baseline"))
        self.assertEqual(result["summary"]["coverage"], 4 / 5)
        self.assertEqual(cohort, original)

    def test_mismatch_late_issue_and_unavailable_history_are_rejected(self):
        for field, value in (("familyId", "unknown"), ("cutoffAt", "2027-01-02T00:00:00-04:00")):
            emission = self.emission()
            emission["result"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                attach_to_cohort(self.fixture(), [emission])
        for date in ("2027-01-02T00:00:00-04:00", "2026-12-31T23:59:59-04:00"):
            emission = dict(self.emission(), issuedAt=date)
            with self.subTest(date=date), self.assertRaises(ValueError):
                attach_to_cohort(self.fixture(), [emission])
        emission = self.emission()
        with self.assertRaises(ValueError):
            attach_to_cohort(self.fixture(), [emission, emission])
        with self.assertRaises(ValueError):
            attach_to_cohort(self.fixture(), [dict(emission, sourceId="unknown")])


if __name__ == "__main__":
    unittest.main()
