"""E06-01: quantity limits and advisory replenishment, without training or TEST."""
import copy
import json
import unittest

from tests.test_calendar2026 import request
from v2 import calendar2026_runtime as runtime
from v2.scenario_data import ROOT, canonical


CONTRACT = json.loads((ROOT / 'v2/contracts/scenarios.v1.json').read_text(encoding='utf8'))
MAX_UNITS = CONTRACT['request_schema']['$defs']['units']['maximum']


class ScenarioReplenishmentTests(unittest.TestCase):
    def setUp(self):
        self.engine = runtime.engine()
        self.p = request()
        self.p['replenishment']['requested'] = True
        self.out = {'orderAt': self.engine.instant('2026-11-01T00:00:00-04:00'),
                    'supplierDays': 2, 'internalDays': 1, 'committed': 18,
                    'stock': 9, 'reservedAfter': 0, 'reservedWithin': 3, 'incoming': 0}

    def calculate(self, forecast=18):
        return self.engine.replenishment(self.p, self.out, {'salesUnits': forecast}, '2026-11')

    def assert_invalid_quantity(self, callback):
        with self.assertRaises(runtime.ScenarioError) as error:
            callback()
        self.assertEqual(error.exception.code, 'INVALID_QUANTITY')

    def test_required_above_limit_rejected_inside_and_outside_horizon(self):
        self.p['replenishment']['safetyStockUnits'] = MAX_UNITS
        for supplier_days, review_days in ((2, 0), (31, 0), (2, 30)):
            with self.subTest(supplier_days=supplier_days, review_days=review_days):
                self.out['supplierDays'] = supplier_days
                self.p['replenishment']['reviewPeriodDays'] = review_days
                self.assert_invalid_quantity(self.calculate)

    def test_available_position_above_limit_rejected_before_horizon_return(self):
        self.out.update(stock=MAX_UNITS, incoming=1)
        for supplier_days in (2, 31):
            with self.subTest(supplier_days=supplier_days):
                self.out['supplierDays'] = supplier_days
                self.assert_invalid_quantity(self.calculate)

    def test_required_exactly_at_limit_is_valid_in_both_horizons(self):
        self.p['replenishment']['safetyStockUnits'] = MAX_UNITS - 18
        within = self.calculate()
        self.assertEqual(within['requiredUnits'], MAX_UNITS)
        self.assertEqual(within['suggestedUnits'], MAX_UNITS - 9)
        self.out['supplierDays'] = 31
        outside = self.calculate()
        self.assertEqual(outside['status'], 'OUTSIDE_FORECAST_HORIZON')
        self.assertEqual(outside['requiredUnits'], MAX_UNITS)
        self.assertIsNone(outside['suggestedUnits'])

    def test_suggestion_above_limit_after_pack_rounding_is_rejected(self):
        self.p['replenishment'].update(minimumOrderUnits=MAX_UNITS, orderMultipleUnits=3)
        # A permitted minimum becomes 1,000,000,002 after packing.
        self.assert_invalid_quantity(self.calculate)

    def test_suggestion_exactly_at_limit_is_valid(self):
        self.p['replenishment'].update(minimumOrderUnits=MAX_UNITS, orderMultipleUnits=1)
        self.assertEqual(self.calculate()['suggestedUnits'], MAX_UNITS)

    def test_valid_late_arrival_preserves_explanation_without_suggestion(self):
        self.out.update(supplierDays=31, internalDays=0)
        r = self.calculate()
        self.assertEqual(r['status'], 'OUTSIDE_FORECAST_HORIZON')
        self.assertEqual((r['requiredUnits'], r['availablePositionUnits'], r['rawNeedUnits']), (23, 9, 14))
        self.assertEqual(r['expectedNewOrderArrivalAt'], '2026-12-02T00:00:00-04:00')
        self.assertIsNone(r['suggestedUnits'])

    def test_no_pack_suggestion_is_invented_outside_horizon(self):
        self.out['supplierDays'] = 31
        self.p['replenishment'].update(minimumOrderUnits=MAX_UNITS, orderMultipleUnits=3)
        self.assertEqual(self.calculate()['status'], 'OUTSIDE_FORECAST_HORIZON')
        self.assertIsNone(self.calculate()['suggestedUnits'])

    def test_sufficient_insufficient_and_exact_stock(self):
        for stock, suggested in ((100, 0), (9, 14), (23, 0), (0, 23)):
            with self.subTest(stock=stock):
                self.out['stock'] = stock
                self.assertEqual(self.calculate()['suggestedUnits'], suggested)

    def test_minimum_pack_and_zero_need(self):
        self.p['replenishment'].update(minimumOrderUnits=20, orderMultipleUnits=6)
        self.assertEqual(self.calculate()['suggestedUnits'], 24)
        self.out['stock'] = 100
        self.assertEqual(self.calculate()['suggestedUnits'], 0)

    def test_absent_forecast_does_not_become_zero_even_with_large_safety(self):
        self.p['replenishment']['safetyStockUnits'] = MAX_UNITS
        r = self.calculate(forecast=None)
        self.assertEqual(r['status'], 'INCOMPLETE')
        self.assertEqual(r['warnings'], ['FORECAST_UNAVAILABLE'])
        self.assertIsNone(r['requiredUnits'])
        self.assertIsNone(r['suggestedUnits'])

    def test_not_requested_does_not_create_quantities(self):
        self.p['replenishment'].update(requested=False, safetyStockUnits=MAX_UNITS)
        r = self.calculate()
        self.assertEqual(r['status'], 'NOT_REQUESTED')
        self.assertIsNone(r['requiredUnits'])
        self.assertIsNone(r['suggestedUnits'])

    def test_calendar_limit_rejected_consistently_without_mutating_snapshot(self):
        self.p.update(baseSnapshotId='calendar-2026-53-6-november', productId=53, locationId=6)
        base = runtime.snapshot_view(self.p['baseSnapshotId'])
        frozen = canonical(runtime.release()[1])
        self.p['replenishment']['safetyStockUnits'] = MAX_UNITS
        for days in (7, 31):
            with self.subTest(days=days):
                self.p['changes']['logistics'] = {'mode': 'SET_LOGISTICS_PLAN',
                    'supplierLeadTimeDays': days, 'internalRestockDays': 0,
                    'plannedOrderAt': base['orderAt'], 'pendingShipments': base['shipments']}
                self.assert_invalid_quantity(lambda: runtime.preview(self.p))
        self.assertEqual(canonical(runtime.release()[1]), frozen)

    def test_calendar_required_exactly_at_maximum(self):
        self.p.update(baseSnapshotId='calendar-2026-53-6-november', productId=53, locationId=6)
        self.p['replenishment']['safetyStockUnits'] = MAX_UNITS - 88
        result = runtime.preview(self.p)
        self.assertAlmostEqual(result['scenario']['salesUnits'], 87.17)
        self.assertEqual(result['replenishment']['requiredUnits'], MAX_UNITS)
        self.assertEqual(result['replenishment']['suggestedUnits'], MAX_UNITS - 140)

    def test_out_of_domain_and_abstained_keep_null_replenishment(self):
        before = canonical(runtime.release()[1])
        for status in ('OUT_OF_DOMAIN', 'ABSTAINED'):
            with self.subTest(status=status):
                p = copy.deepcopy(self.p)
                if status == 'OUT_OF_DOMAIN':
                    p['changes']['stock'] = {'mode': 'SET_SELLABLE_STOCK', 'sellablePhysicalUnits': 10000}
                else:
                    history = runtime.snapshot_view(p['baseSnapshotId'])['history']
                    months = [dict(row, complete=True) for row in history]
                    months[-1]['unknownModeUnits'] = 1
                    p['changes']['history'] = {'mode': 'REPLACE_SYNTHETIC_HISTORY', 'months': months}
                result = runtime.preview(p)
                self.assertEqual(result['scenario']['status'], status)
                self.assertIsNone(result['scenario']['salesUnits'])
                self.assertEqual(result['replenishment']['status'], 'INCOMPLETE')
                self.assertIsNone(result['replenishment']['requiredUnits'])
                self.assertIsNone(result['replenishment']['suggestedUnits'])
        self.assertEqual(canonical(runtime.release()[1]), before)


if __name__ == '__main__':
    unittest.main()
