"""Runtime consistency regressions with approved DEMO inputs only."""

import hashlib
import json
from unittest import TestCase
from unittest.mock import patch

from v2 import calendar2026_runtime as runtime
from v2.scenario_data import canonical, sha
from .test_calendar2026 import request


class RuntimeConsistencyTests(TestCase):
    def setUp(self):
        self.engine = runtime.engine()
        self.payload = request()
        self.payload["baseSnapshotId"] = "calendar-2026-53-6-november"
        self.snapshot = self.engine.get_snapshot(self.payload["baseSnapshotId"])
        for key in ("productId", "locationId", "targetMonth"):
            self.payload[key] = self.snapshot[key]
        self.payload["replenishment"].update(requested=True, safetyStockUnits=5)
        self.base = self.engine.state(self.snapshot)

    def set_prices(self, minor="108.3", major="92.055", date="2026-11-01T00:00:00-04:00"):
        self.payload["changes"]["prices"] = dict(mode="SET_PRICES", retailPriceBs=minor,
                                               wholesalePriceBs=major, effectiveAt=date)

    def no_receipts(self, stock):
        self.payload["changes"]["stock"] = dict(mode="SET_SELLABLE_STOCK", sellablePhysicalUnits=stock)
        self.payload["changes"]["logistics"] = dict(
            mode="SET_LOGISTICS_PLAN", pendingShipments=[], supplierLeadTimeDays=self.base["supplierDays"],
            internalRestockDays=self.base["internalDays"], plannedOrderAt=self.base["orderAt"].isoformat())

    def test_identical_prices_preserve_features_and_commercial_result(self):
        baseline = runtime.preview(self.payload)
        for date in ("2026-11-01T00:00:00-04:00", "2026-11-15T00:00:00-04:00"):
            with self.subTest(date=date):
                self.set_prices(date=date)
                out, impacts, _ = self.engine.prepare(self.payload, self.snapshot)
                self.assertEqual(out["features"], self.snapshot["features"])
                self.assertEqual(impacts, [])
                result = runtime.preview(self.payload)
                for field in ("baseline", "scenario", "deltaSalesUnits", "replenishment"):
                    self.assertEqual(result[field], baseline[field])
                self.assertEqual(result["scenario"]["salesUnits"], 87.17)
                self.assertEqual(result["replenishment"]["requiredUnits"], 93)
                self.assertNotEqual(result["scenarioInputSha256"], baseline["scenarioInputSha256"])
                self.assertEqual(result["scenarioInputSha256"], hashlib.sha256(canonical(self.payload)).hexdigest())

    def test_identical_prices_still_validate_amounts_and_date(self):
        for minor, date in (("108.30000", "2026-11-01T00:00:00-04:00"),
                            ("108.3", "2026-12-01T00:00:00-04:00"),
                            ("108.3", "2026-11-31T00:00:00-04:00")):
            self.set_prices(minor=minor, date=date)
            with self.subTest(minor=minor, date=date), self.assertRaisesRegex(runtime.ScenarioError, "^INVALID_INPUT$"):
                runtime.preview(self.payload)

    def test_real_retail_wholesale_and_double_changes_keep_vigencia_and_precision(self):
        retail, wholesale = "variacion_precio_menor_plan_ponderada", "variacion_precio_mayor_plan_ponderada"
        for minor, major, expected in (("108.3001", "92.055", {retail}),
                                       ("108.3", "92.0551", {wholesale}),
                                       ("113.72", "96.66", {retail, wholesale})):
            with self.subTest(minor=minor, major=major):
                self.set_prices(minor, major, "2026-11-15T00:00:00-04:00")
                out, impacts, _ = self.engine.prepare(self.payload, self.snapshot)
                self.assertEqual(out["features"]["dias_vigencia_nuevo_precio_plan"], 16)
                self.assertEqual({feature for feature in (retail, wholesale) if out["features"][feature] != 0}, expected)
                self.assertTrue(all(impact["before"] != impact["after"] for impact in impacts))
                self.assertEqual(runtime.preview(self.payload)["scenario"]["status"], "OK")

    def test_identical_stock_not_used_as_impact_and_real_change_visible(self):
        for stock in (90, 89):
            self.payload["changes"]["stock"] = dict(mode="SET_SELLABLE_STOCK", sellablePhysicalUnits=stock)
            result = runtime.preview(self.payload)
            if stock == 90:
                self.assertEqual(result["impacts"], [])
            else:
                impact, = result["impacts"]
                self.assertEqual((impact["before"], impact["after"], impact["effectStatus"]), (90, 89, "USED"))

    def test_supply_warning_only_on_published_numeric_estimate(self):
        self.no_receipts(3)
        numeric = runtime.preview(self.payload)
        self.assertGreater(numeric["scenario"]["salesUnits"], 3)
        self.assertIn("FORECAST_EXCEEDS_PLANNED_SUPPLY", numeric["warnings"])
        history = [dict(row, complete=True) for row in runtime.snapshot_view(self.payload["baseSnapshotId"])["history"]]
        history[0]["unknownModeUnits"] = 1
        self.payload["changes"]["history"] = dict(mode="REPLACE_SYNTHETIC_HISTORY", months=history)
        result = runtime.preview(self.payload)
        self.assertEqual(result["scenario"], {"status": "ABSTAINED", "salesUnits": None, "reason": "UNKNOWN_CHANNEL_MIX"})
        self.assertIsNone(result["deltaSalesUnits"])
        self.assertEqual(result["replenishment"]["status"], "INCOMPLETE")
        self.assertIsNone(result["replenishment"]["suggestedUnits"])
        self.assertNotIn("FORECAST_EXCEEDS_PLANNED_SUPPLY", result["warnings"])
        self.assertIn("QUOTE_OLDER_THAN_30_DAYS_ASSUMPTION", result["warnings"])

    def test_integrity_determinism_and_finite_guard(self):
        release, snapshots, model = runtime.release()
        before = canonical(snapshots)
        self.set_prices()
        first, second = (runtime.preview(self.payload) for _ in range(2))
        for result in (first, second):
            result.pop("recordedAt")
            json.dumps(result, allow_nan=False)
            self.assertEqual(result["contractVersion"], "demand-scenarios-1.0.0")
        self.assertEqual(first, second)
        self.assertEqual(canonical(snapshots), before)
        self.assertEqual(sha(runtime.ROOT / release["artifact"]), release["artifactSha256"])
        self.assertEqual(sha(runtime.ROOT / release["snapshots"]), release["snapshotsSha256"])
        for invalid in (float("nan"), float("inf")):
            with self.subTest(invalid=invalid), patch.object(model, "predict", return_value=[invalid]):
                with self.assertRaisesRegex(runtime.ScenarioError, "^MODEL_UNAVAILABLE$"):
                    runtime.preview(self.payload)
