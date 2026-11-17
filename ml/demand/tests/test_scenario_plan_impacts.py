"""E05-01: identity-based plan traces against the frozen calendar runtime."""
import copy
import unittest
from unittest.mock import patch

from v2 import calendar2026_runtime as runtime
from v2.scenario_data import canonical
from tests.test_calendar2026 import request


class ScenarioPlanImpactTests(unittest.TestCase):
    def setUp(self):
        self.engine = runtime.engine()
        self.payload = request()
        self.payload['baseSnapshotId'] = 'calendar-2026-53-6-november'
        self.snapshot = self.engine.get_snapshot(self.payload['baseSnapshotId'])
        for key in ('productId', 'locationId', 'targetMonth'):
            self.payload[key] = self.snapshot[key]
        self.original = canonical(runtime.release()[1])

    def tearDown(self):
        self.assertEqual(canonical(runtime.release()[1]), self.original)

    def shipment(self, identity, units, day):
        return {'shipmentId': identity, 'pendingUnits': units, 'reservedAfterHorizonUnits': 0,
                'expectedArrivalAt': f'2026-11-{day:02d}T00:00:00-04:00'}

    def order(self, identity, units=10, reserved=0, due='2026-11-10'):
        return {'orderId': identity, 'mode': 'POR_MENOR', 'outstandingUnits': units,
                'reservedUnits': reserved, 'dueAt': due + 'T00:00:00-04:00'}

    def fixture(self, shipments=None, orders=None):
        # Input-side fixtures only; published snapshots and artifacts stay untouched.
        if shipments is not None:
            self.snapshot['shipments'] = [dict(shipment_id=s['shipmentId'], pending_units_at_cutoff=s['pendingUnits'],
                reserved_after_horizon_units=s['reservedAfterHorizonUnits'], expected_arrival_at=s['expectedArrivalAt']) for s in shipments]
        if orders is not None:
            self.snapshot['orders'] = [dict(order_id=o['orderId'], sale_mode=o['mode'],
                outstanding_units_at_cutoff=o['outstandingUnits'], reserved_units_at_cutoff=o['reservedUnits'],
                due_at=o['dueAt']) for o in orders]
        prepared, _, _ = self.engine.prepare(self.payload, self.snapshot)
        self.snapshot['features'] = prepared['features']

    def logistics(self, shipments):
        base = self.engine.state(self.snapshot)
        self.payload['changes']['logistics'] = {'mode': 'SET_LOGISTICS_PLAN',
            'supplierLeadTimeDays': base['supplierDays'], 'internalRestockDays': base['internalDays'],
            'plannedOrderAt': base['orderAt'].isoformat(), 'pendingShipments': shipments}

    def prepare(self):
        frozen = canonical(self.snapshot)
        result = self.engine.prepare(self.payload, self.snapshot)
        self.assertEqual(canonical(self.snapshot), frozen)
        fields = [i['field'] for i in result[1]]
        self.assertEqual(len(fields), len(set(fields)), 'Duplicate scalar impacts')
        self.assertTrue(all(i['before'] != i['after'] for i in result[1]), 'False unchanged impact')
        return result

    def preview(self):
        with patch.object(self.engine, 'get_snapshot', return_value=copy.deepcopy(self.snapshot)):
            return runtime.preview(self.payload)

    def test_delete_all_shipments_preserves_numeric_result_and_explains_inputs(self):
        self.logistics([])
        out, impacts, _ = self.prepare()
        self.assertEqual(out['features']['entradas_plan_horizonte_unidades'], 0)
        self.assertEqual(out['features']['dias_hasta_primera_entrada_plan'], '')
        removed = next(i for i in impacts if i['field'].endswith('.pendingUnits'))
        self.assertEqual((removed['before'], removed['after']), (50, None))
        self.assertEqual((removed['role'], removed['effectStatus']), ('DERIVED_MODEL_FEATURE', 'USED'))
        self.assertIn('eliminado', removed['explanation'])
        self.assertIn('entradas_plan_horizonte_unidades', removed['explanation'])
        first = self.preview()
        self.assertAlmostEqual(first['baseline']['salesUnits'], 87.17)
        self.assertAlmostEqual(first['scenario']['salesUnits'], 86.57)
        self.assertAlmostEqual(first['deltaSalesUnits'], -0.60)
        self.assertEqual(first['baseline'], runtime.preview(request())['baseline'])

    def test_delete_one_of_many_matches_identity_not_position(self):
        a, b = self.shipment('a', 50, 10), self.shipment('b', 20, 20)
        self.fixture(shipments=[a, b]); self.logistics([b])
        out, impacts, _ = self.prepare()
        self.assertEqual(out['features']['entradas_plan_horizonte_unidades'], 20)
        self.assertEqual(out['features']['dias_hasta_primera_entrada_plan'], 19)
        self.assertEqual(len(impacts), 4)
        self.assertTrue(all(i['after'] is None and '(a)' in i['explanation'] for i in impacts))

    def test_modify_shipment_quantity(self):
        a = self.shipment('a', 50, 10)
        self.fixture(shipments=[a]); self.logistics([dict(a, pendingUnits=40)])
        out, impacts, _ = self.prepare()
        self.assertEqual(out['features']['entradas_plan_horizonte_unidades'], 40)
        self.assertEqual(len(impacts), 1)
        self.assertEqual((impacts[0]['before'], impacts[0]['after']), (50, 40))
        self.assertEqual(impacts[0]['role'], 'DERIVED_MODEL_FEATURE')

    def test_modify_first_arrival_date(self):
        a = self.shipment('a', 50, 10)
        self.fixture(shipments=[a]); self.logistics([dict(a, expectedArrivalAt='2026-11-12T00:00:00-04:00')])
        out, impacts, _ = self.prepare()
        self.assertEqual(out['features']['dias_hasta_primera_entrada_plan'], 11)
        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0]['effectStatus'], 'USED')
        self.assertIn('dias_hasta_primera_entrada_plan', impacts[0]['explanation'])

    def test_add_shipment(self):
        a, b = self.shipment('a', 50, 10), self.shipment('b', 20, 20)
        self.fixture(shipments=[a]); self.logistics([b, a])
        out, impacts, _ = self.prepare()
        self.assertEqual(out['features']['entradas_plan_horizonte_unidades'], 70)
        self.assertEqual(len(impacts), 4)
        self.assertTrue(all(i['before'] is None and '(b)' in i['explanation'] for i in impacts))

    def test_reordered_shipments_and_orders_have_no_impacts(self):
        a, b = self.shipment('a', 50, 10), self.shipment('b', 20, 20)
        x, y = self.order('x'), self.order('y', due='2026-12-10')
        self.fixture(shipments=[b, a], orders=[y, x]); self.logistics([a, b])
        self.payload['changes']['orders'] = {'mode': 'REPLACE_OPEN_ORDER_PLAN', 'orders': [x, y]}
        out, impacts, _ = self.prepare()
        self.assertEqual(out['features'], self.snapshot['features'])
        self.assertEqual(impacts, [])
        self.assertEqual(self.preview()['deltaSalesUnits'], 0)

    def test_keep_has_no_impacts(self):
        self.assertEqual(self.prepare()[1], [])
        self.assertEqual(self.preview()['deltaSalesUnits'], 0)

    def test_repeated_requests_and_permutations_have_deterministic_traces(self):
        self.fixture(shipments=[])
        a, b = self.shipment('a', 20, 10), self.shipment('b', 30, 20)
        self.logistics([b, a]); first = self.preview(); second = self.preview()
        self.assertEqual(first['impacts'], second['impacts'])
        self.assertEqual(first['scenario'], second['scenario'])
        self.logistics([a, b]); third = self.preview()
        self.assertEqual(first['impacts'], third['impacts'])
        self.assertEqual(first['scenario'], third['scenario'])

    def test_orders_added_modified_deleted_by_identity(self):
        x, y = self.order('x'), self.order('y', reserved=2, due='2026-12-10')
        self.fixture(orders=[x, y])
        self.payload['changes']['orders'] = {'mode': 'REPLACE_OPEN_ORDER_PLAN', 'orders': [dict(y, reservedUnits=3), self.order('z', 5)]}
        out, impacts, _ = self.prepare()
        self.assertEqual(out['features']['compromisos_por_menor_horizonte_unidades'], 5)
        self.assertEqual(out['features']['reservas_posteriores_unidades'], 3)
        self.assertEqual(len(impacts), 11)  # x removed (5), y changed (1), z added (5).
        self.assertEqual(sum(i['field'].endswith('.reservedUnits') and i['before'] == 2 and i['after'] == 3 for i in impacts), 1)
        self.assertTrue(any(i['role'] == 'DERIVED_MODEL_FEATURE' and 'reservas_posteriores_unidades' in i['explanation'] for i in impacts))

    def test_delete_all_orders(self):
        self.fixture(orders=[self.order('x')])
        self.payload['changes']['orders'] = {'mode': 'REPLACE_OPEN_ORDER_PLAN', 'orders': []}
        out, impacts, _ = self.prepare()
        self.assertEqual(out['features']['compromisos_por_menor_horizonte_unidades'], 0)
        self.assertEqual(len(impacts), 5)
        self.assertTrue(all(i['after'] is None for i in impacts))

    def test_reserved_within_horizon_is_replenishment_only(self):
        x = self.order('x', reserved=2)
        self.fixture(orders=[x])
        self.payload['changes']['orders'] = {'mode': 'REPLACE_OPEN_ORDER_PLAN', 'orders': [dict(x, reservedUnits=3)]}
        _, impacts, _ = self.prepare()
        self.assertEqual(len(impacts), 1)
        self.assertEqual((impacts[0]['role'], impacts[0]['effectStatus']), ('REPLENISHMENT_ONLY', 'NOT_USED_BY_SELECTED_MODEL'))
        self.assertEqual(self.preview()['deltaSalesUnits'], 0)

    def test_later_shipments_and_nonfirst_dates_do_not_claim_model_changes(self):
        a, b = self.shipment('a', 50, 10), self.shipment('b', 20, 20)
        self.fixture(shipments=[a, b]); self.logistics([a, dict(b, expectedArrivalAt='2026-11-21T00:00:00-04:00')])
        _, impacts, _ = self.prepare()
        self.assertEqual(impacts[0]['role'], 'VALIDATION_ONLY')
        self.assertEqual(self.preview()['deltaSalesUnits'], 0)
        self.logistics([a, b, dict(self.shipment('late', 10, 20), expectedArrivalAt='2026-12-10T00:00:00-04:00')])
        self.assertTrue(all(i['effectStatus'] == 'NOT_USED_BY_SELECTED_MODEL' for i in self.prepare()[1]))

    def test_move_shipment_outside_horizon_traces_removed_model_supply(self):
        a = self.shipment('a', 50, 10)
        self.fixture(shipments=[a]); self.logistics([dict(a, expectedArrivalAt='2026-12-10T00:00:00-04:00')])
        out, impacts, _ = self.prepare()
        self.assertEqual(out['features']['entradas_plan_horizonte_unidades'], 0)
        self.assertEqual(impacts[0]['role'], 'DERIVED_MODEL_FEATURE')

    def test_abstention_remains_null_with_deletion(self):
        self.logistics([])
        self.payload['changes']['stock'] = {'mode': 'SET_SELLABLE_STOCK', 'sellablePhysicalUnits': 10000}
        result = self.preview()
        self.assertEqual(result['scenario']['status'], 'OUT_OF_DOMAIN')
        self.assertIsNone(result['scenario']['salesUnits'])
        self.assertIsNone(result['deltaSalesUnits'])
        self.assertTrue(any(i['after'] is None for i in result['impacts']))


if __name__ == '__main__':
    unittest.main()
