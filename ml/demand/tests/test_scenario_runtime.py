import copy
from decimal import Decimal
import json
import unittest
from unittest.mock import patch
from v2 import scenario_runtime as runtime
from v2.scenario_data import rows, FEATURES


def request(s=None):
    s = s or runtime.capabilities()['snapshots'][0]
    return {k: s[k] for k in ('productId', 'locationId', 'targetMonth', 'baseSnapshotId')} | {
        'contractVersion': runtime.CONTRACT, 'mode': 'HYPOTHETICAL_SCENARIO', 'clientRequestId': 'unit-test',
        'changes': {k: {'mode': 'KEEP'} for k in runtime.CHANGES},
        'replenishment': {'requested': False, 'policy': 'MONTH_END_COMMITMENT_FLOOR_V1', 'safetyStockUnits': 5, 'minimumOrderUnits': 0, 'orderMultipleUnits': 1, 'reviewPeriodDays': 0}}


class ScenarioRuntimeTests(unittest.TestCase):
    def test_capability_ranking_uses_only_previous_closed_month(self):
        for entry in runtime.capabilities()['snapshots']:
            snapshot = runtime.get_snapshot(entry['baseSnapshotId'])
            history = max(snapshot['history'], key=lambda row: row['mes'])
            expected = sum(int(history[k]) for k in ('unidades_por_menor', 'unidades_por_mayor', 'unidades_modalidad_desconocida'))
            self.assertEqual(entry['previousMonthUnits'], expected)
            self.assertLess(history['mes'], entry['targetMonth'])
            self.assertNotIn('target_ventas_mes', entry)

    def rejected(self, p, code):
        with self.assertRaises(runtime.ScenarioError) as result: runtime.preview(p)
        self.assertEqual(result.exception.code, code)

    def test_01_keep_same_prediction(self):
        result = runtime.preview(request())
        self.assertEqual(result['deltaSalesUnits'], 0)
        self.assertEqual(result['baseline']['salesUnits'], result['scenario']['salesUnits'])

    def test_02_all_base_features_round_trip_without_outcomes(self):
        for s in runtime.release()[1].values():
            p = request(s); derived, _, _ = runtime.prepare(p, s)
            for field in FEATURES:
                a, b = derived['features'][field], s['features'][field]
                if a == '' or b == '': self.assertEqual(a, b)
                else: self.assertAlmostEqual(float(a), float(b), places=6, msg=field)

    def test_03_price_weighting_mid_month(self):
        p = request(); s = runtime.get_snapshot(p['baseSnapshotId']); b = runtime.state(s)
        p['changes']['prices'] = {'mode': 'SET_PRICES', 'retailPriceBs': str((b['retail'] * Decimal('1.25')).quantize(Decimal('.0001'))), 'wholesalePriceBs': str((b['wholesale'] * Decimal('1.25')).quantize(Decimal('.0001'))), 'effectiveAt': p['targetMonth'] + '-16T00:00:00-04:00'}
        derived, _, _ = runtime.prepare(p, s)
        days = (runtime.end_month(p['targetMonth']) - runtime.instant(p['targetMonth'] + '-01T00:00:00-04:00')).days
        self.assertAlmostEqual(derived['features']['variacion_precio_menor_plan_ponderada'], .25 * (days-15)/days)
        self.assertEqual(runtime.preview(p)['scenario']['status'], 'OK')

    def test_04_cost_below_price_at_every_interval(self):
        p = request(); p['changes']['cost'] = {'mode': 'SET_LANDED_COST_BS', 'unitCostBs': '99999999', 'effectiveAt': p['targetMonth'] + '-02T00:00:00-04:00'}
        self.rejected(p, 'INCOHERENT_PRICES')

    def test_05_no_future_quote(self):
        p = request(); p['changes']['quote'] = {'mode': 'SET_HYPOTHETICAL_QUOTE', 'bsPerUsd': '9', 'observedAt': p['targetMonth'] + '-02T00:00:00-04:00'}
        self.rejected(p, 'INVALID_QUOTE_TIME')

    def test_06_quote_does_not_invent_sales_effect(self):
        p = request(); p['changes']['quote'] = {'mode': 'SET_HYPOTHETICAL_QUOTE', 'bsPerUsd': '15', 'observedAt': p['targetMonth'] + '-01T00:00:00-04:00'}
        r = runtime.preview(p); self.assertEqual(r['deltaSalesUnits'], 0)
        self.assertTrue(all(i['effectStatus'] == 'NOT_USED_BY_SELECTED_MODEL' for i in r['impacts']))

    def test_07_import_cost_decimal(self):
        p = request(); s = runtime.get_snapshot(p['baseSnapshotId']); p['changes']['cost'] = {'mode': 'SIMULATE_IMPORT_USD', 'unitCostUsd': '1.1234', 'freightPerUnitBs': '2', 'otherPerUnitBs': '3', 'effectiveAt': p['targetMonth'] + '-01T00:00:00-04:00'}
        out, _, _ = runtime.prepare(p, s)
        self.assertEqual(out['cost'], Decimal('1.1234') * runtime.state(s)['quote'] + 5)

    def test_08_reject_negative_fractional_and_boolean_units(self):
        for value in (-1, .5, True):
            p = request(); p['changes']['stock'] = {'mode': 'SET_SELLABLE_STOCK', 'sellablePhysicalUnits': value}; self.rejected(p, 'INVALID_INPUT')

    def test_09_duplicate_and_excess_reservations(self):
        p = request(); order = {'orderId': 'o', 'mode': 'POR_MAYOR', 'outstandingUnits': 1000, 'reservedUnits': 0, 'dueAt': p['targetMonth'] + '-10T00:00:00-04:00'}
        p['changes']['orders'] = {'mode': 'REPLACE_OPEN_ORDER_PLAN', 'orders': [order, order]}; self.rejected(p, 'INVALID_ORDER_PLAN')
        p['changes']['orders']['orders'] = [{**order, 'reservedUnits': 1000}]; self.rejected(p, 'INVALID_RESERVATION')

    def test_10_reject_mismatch_and_target_injection(self):
        p = request(); p['productId'] = 999; self.rejected(p, 'SNAPSHOT_MISMATCH')
        p = request(); p['target_ventas_mes'] = 100; self.rejected(p, 'INVALID_INPUT')

    def test_11_invalid_calendar(self):
        p = request(); p['changes']['quote'] = {'mode': 'SET_HYPOTHETICAL_QUOTE', 'bsPerUsd': '9', 'observedAt': '2028-02-31T00:00:00-04:00'}; self.rejected(p, 'INVALID_INPUT')

    def test_12_history_months_exact_and_unknown_abstention(self):
        p = request(); s = runtime.snapshot_view(p['baseSnapshotId']); history = [dict(h, complete=True) for h in s['history']]
        p['changes']['history'] = {'mode': 'REPLACE_SYNTHETIC_HISTORY', 'months': history}; history[0]['month'] = '2000-01'; self.rejected(p, 'INVALID_HISTORY_WINDOW')
        history[0]['month'] = s['history'][0]['month']; history[-1]['unknownModeUnits'] = 1
        self.assertEqual(runtime.preview(p)['scenario']['reason'], 'UNKNOWN_CHANNEL_MIX')

    def test_13_new_product_abstains_without_zero_filling(self):
        p = request(); p['baseSnapshotId'] = 'unseen'; self.rejected(p, 'SNAPSHOT_MISMATCH')

    def test_14_test_partition_forbidden(self):
        with self.assertRaises(PermissionError): list(rows('TEST'))

    def test_15_monthly_floor_does_not_double_count_reservations(self):
        p = request(); p['replenishment']['requested'] = True
        out = {'orderAt': runtime.instant(p['targetMonth'] + '-01T00:00:00-04:00'), 'supplierDays': 2, 'internalDays': 1, 'committed': 18, 'stock': 9, 'reservedAfter': 0, 'reservedWithin': 3, 'incoming': 0}
        result = runtime.replenishment(p, out, {'salesUnits': 18}, p['targetMonth'])
        self.assertEqual(result['requiredUnits'], 23); self.assertEqual(result['suggestedUnits'], 14)
        p['replenishment'].update(minimumOrderUnits=20, orderMultipleUnits=6)
        self.assertEqual(runtime.replenishment(p, out, {'salesUnits': 18}, p['targetMonth'])['suggestedUnits'], 24)
        out['stock'] = 100
        self.assertEqual(runtime.replenishment(p, out, {'salesUnits': 18}, p['targetMonth'])['suggestedUnits'], 0)

    def test_16_late_order_has_no_suggestion(self):
        p = request(); p['replenishment']['requested'] = True
        out = {'orderAt': runtime.instant(p['targetMonth'] + '-01T00:00:00-04:00'), 'supplierDays': 60, 'internalDays': 0, 'committed': 0, 'stock': 0, 'reservedAfter': 0, 'reservedWithin': 0, 'incoming': 0}
        result = runtime.replenishment(p, out, {'salesUnits': 18}, p['targetMonth'])
        self.assertEqual(result['status'], 'OUTSIDE_FORECAST_HORIZON'); self.assertIsNone(result['suggestedUnits'])

    def test_17_absent_forecast_has_no_suggestion(self):
        p = request(); p['replenishment']['requested'] = True
        self.assertEqual(runtime.replenishment(p, {}, {'salesUnits': None}, p['targetMonth'])['status'], 'INCOMPLETE')

    def test_18_out_of_domain_not_false_zero(self):
        p = request(); p['changes']['stock'] = {'mode': 'SET_SELLABLE_STOCK', 'sellablePhysicalUnits': 1000000}
        r = runtime.preview(p); self.assertIsNone(r['scenario']['salesUnits']); self.assertEqual(r['scenario']['status'], 'OUT_OF_DOMAIN')

    def test_19_corrupted_release_never_deserializes(self):
        runtime.release.cache_clear()
        try:
            with patch.object(runtime, 'sha', return_value='0'*64), patch.object(runtime.joblib, 'load') as loader:
                with self.assertRaises(runtime.ScenarioError): runtime.release()
                loader.assert_not_called()
        finally: runtime.release.cache_clear()
        self.assertEqual(runtime.capabilities()['datasetVersion'], '3.0.0')

    def test_20_large_order_plan_preserves_trace_and_backlog(self):
        p = request()
        p['changes']['orders'] = {'mode': 'REPLACE_OPEN_ORDER_PLAN', 'orders': [
            {'orderId': f'order-{i}', 'mode': 'POR_MAYOR', 'outstandingUnits': 1, 'reservedUnits': 0, 'dueAt': '2028-01-01T00:00:00-04:00'} for i in range(100)]}
        r = runtime.preview(p)
        self.assertEqual(len(r['impacts']), 500)
        self.assertIn('COMMITMENT_OVERLAP_UNCERTAIN', r['warnings'])


if __name__ == '__main__': unittest.main()
