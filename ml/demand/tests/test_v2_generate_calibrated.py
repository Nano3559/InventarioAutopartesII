"""Pruebas de mecanismos y fixture de cuatro meses, sin build o catálogo completo."""
import copy
from datetime import timedelta
import json
import math
import unittest
from unittest.mock import patch
from v2.generate_calibrated import inputs,simulate,build
from v2.retail_mechanisms import Mechanisms,validate_prices,money
from v2.generate import month_start
from v2.validate_build import canonical_hash,instant

class CalibratedGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.args=inputs()
    def runtime(self,mutate=None):
        calibration=copy.deepcopy(self.args[-2]);recipe=copy.deepcopy(self.args[-1])
        if mutate:mutate(calibration,recipe)
        return Mechanisms(calibration,recipe,[5,6,7])
    def fixture(self,price_probability=None):
        config,legacy,schema,catalog,prep,calibration,recipe=copy.deepcopy(self.args)
        pid=catalog['included_product_ids'][0];sid=next(s['id'] for s in catalog['locations'] if s['type']=='TIENDA')
        catalog['included_product_ids']=[pid];catalog['locations']=[s for s in catalog['locations'] if s['id']==sid]
        config['profiles']=[{'name':'MIXED','weight':1.}]
        if price_probability is not None:
            calibration['parameters']['weekly_price_change_probability']['value']=price_probability
            calibration['parameters']['conditional_up_share']['value']=1.
        return config,legacy,schema,catalog,prep,calibration,recipe
    def test_loader_pins_accepted_configuration_without_simulation(self):
        self.assertEqual(self.args[-1]['generator_version'],'retail-reference-generator-1.0.0')
        self.assertIsNone(self.args[-1]['dataset_version'])
        self.assertFalse(self.args[-1]['publication_authorized'])
        with patch('v2.generate_calibrated.sha256_file',return_value='0'*64):
            with self.assertRaises(ValueError):inputs()
    def test_build_is_disabled_before_any_filesystem_work(self):
        with patch('pathlib.Path.mkdir',side_effect=AssertionError('No crear carpetas')):
            with self.assertRaises(PermissionError):build('not-authorized')
    def test_weekly_price_is_available_only_at_week_close(self):
        def forced(c,r):
            c['parameters']['weekly_price_change_probability']['value']=1.
            c['parameters']['conditional_up_share']['value']=1.
        rt=self.runtime(forced);close=rt.first_week+timedelta(days=7)
        self.assertEqual(rt.price_state(1,5,close-timedelta(microseconds=1)),(1.,[]))
        factor,events=rt.price_state(1,5,close)
        self.assertAlmostEqual(factor,1+rt.magnitude)
        self.assertEqual(instant(events[0]['available_at']),close)
    def test_no_event_probability_does_not_change_price(self):
        rt=self.runtime(lambda c,r:c['parameters']['weekly_price_change_probability'].update(value=0))
        self.assertEqual(rt.price_state(1,5,month_start(12)),(1.,[]))
    def test_horizon_and_future_week_requests_do_not_change_history(self):
        rt=self.runtime();at=month_start(4);first=rt.price_state(1,5,at)
        rt.price_state(1,5,month_start(24));self.assertEqual(first,rt.price_state(1,5,at))
        with self.assertRaises(ValueError):rt.price_state(1,5,at.replace(tzinfo=None))
    def test_probabilities_bool_nonfinite_and_negative_price_are_rejected(self):
        for value in [-1,1.1,True,float('nan')]:
            with self.assertRaises(ValueError):self.runtime(lambda c,r:c['parameters']['weekly_price_change_probability'].update(value=value))
        for value in [0,1,1.5,float('inf')]:
            with self.assertRaises(ValueError):self.runtime(lambda c,r:c['parameters']['conditional_absolute_price_change'].update(value=value))
    def test_cost_and_commercial_price_order_is_never_silently_fixed(self):
        self.assertEqual(validate_prices(120,108,80),(120,108,80))
        for prices in [(120,150,80),(120,75,80),(0,0,0),(120,-1,80)]:
            with self.assertRaises(ValueError):validate_prices(*prices)
        self.assertEqual(money(1.005),1.01)
    def test_large_calendar_measure_uses_positive_normalized_mechanism(self):
        rt=self.runtime(lambda c,r:c['parameters']['calendar_amplitude']['reference_quantiles'].update(p50=7.83))
        values=[rt.seasonal_factor(m) for m in range(1,13)]
        self.assertTrue(all(v>0 and math.isfinite(v) for v in values))
        self.assertAlmostEqual(sum(values)/12,1.)
    def test_store_factors_are_positive_normalized_and_not_external_ids(self):
        rt=self.runtime();self.assertEqual(set(rt.store_factors),{5,6,7})
        self.assertAlmostEqual(sum(rt.store_factors.values())/3,1.)
        self.assertEqual(len(set(rt.store_factors.values())),3)
        with self.assertRaises(ValueError):self.runtime(lambda c,r:c['parameters']['store_volume_factor']['reference_quantiles'].update(p10=0))
    def test_bursts_change_synthetic_minor_count_not_mode_or_absence(self):
        for case,multiplier in [('P95',2.8),('P99',4.)]:
            rt=self.runtime(lambda c,r:r.update(burst_cycle=[case]))
            count,audit=rt.retail_quantity(2,1,5,0)
            self.assertEqual(count,math.ceil(2*multiplier));self.assertEqual(audit['mode'],'POR_MENOR')
            self.assertEqual(rt.retail_quantity(0,1,5,0)[0],0)
    def test_unidentified_elasticity_and_promotion_are_not_activated(self):
        for name in ['price_elasticity','promotion_daily_probability','bolivian_exchange_rate_stock_modalities_cost_lead_time']:
            with self.assertRaises(ValueError):self.runtime(lambda c,r:c['parameters'][name].update(value=.1))
    def test_reduced_fixture_preserves_stock_transit_target_and_lags(self):
        args=self.fixture();before=canonical_hash(args)
        bundle=simulate(*args,months=4)
        self.assertEqual(len(bundle['base']),4);self.assertEqual(len(bundle['supervised']),1)
        self.assertEqual(canonical_hash(args),before)
        self.assertEqual(canonical_hash(bundle),canonical_hash(simulate(*args,months=4)))
        for row,ledger in zip(bundle['base'],bundle['ledger']):
            self.assertEqual(ledger['opening_stock']+ledger['received_units']-ledger['sold_units'],ledger['closing_stock'])
            self.assertEqual(ledger['transit_opening']+ledger['sent_units']-ledger['received_units'],ledger['transit_closing'])
            self.assertGreaterEqual(ledger['closing_stock'],0)
            self.assertEqual(row['unidades_vendidas_brutas'],row['unidades_por_menor']+row['unidades_por_mayor']+row['unidades_modalidad_desconocida'])
        row=bundle['supervised'][0]
        self.assertEqual(row['target_ventas_mes'],bundle['base'][3]['unidades_vendidas_brutas'])
        self.assertEqual(row['ventas_mes_anterior'],bundle['base'][2]['unidades_vendidas_brutas'])
        self.assertEqual(row['ventas_hace_3_meses'],bundle['base'][0]['unidades_vendidas_brutas'])
    def test_reduced_fixture_future_horizon_cannot_rewrite_past(self):
        args=self.fixture();a=simulate(*args,months=4);b=simulate(*args,months=5)
        self.assertEqual(a['base'],b['base'][:4])
        self.assertEqual(a['supervised'],b['supervised'][:1])
    def test_no_causal_price_demand_effect_is_invented(self):
        a=simulate(*self.fixture(0),months=4);b=simulate(*self.fixture(1),months=4)
        self.assertNotEqual([r['precio_menor_cierre_bs'] for r in a['base']],[r['precio_menor_cierre_bs'] for r in b['base']])
        self.assertEqual([r['unidades_vendidas_brutas'] for r in a['base']],[r['unidades_vendidas_brutas'] for r in b['base']])
        self.assertTrue(all(r['price_effect_on_demand']==0 for r in a['calibration_audit']))

    def test_partial_receipts_and_unexpected_orders_remain_physical(self):
        for profile in ['PARTIAL_LATE','UNEXPECTED','LOW']:
            args=list(self.fixture());args[0]['profiles']=[{'name':profile,'weight':1.}]
            b=simulate(*args,months=4)
            self.assertEqual(len({r['receipt_id'] for r in b['receipts']}),len(b['receipts']))
            for row in b['daily']:
                self.assertEqual(row['opening_stock']+row['received_units']-row['sold_units'],row['closing_stock'])
                self.assertGreaterEqual(row['closing_stock'],0)
            for shipment in b['shipments']:
                received=sum(r['quantity'] for r in b['receipts'] if r['shipment_id']==shipment['shipment_id'])
                self.assertEqual(shipment['received_units'],received)
                self.assertEqual(shipment['sent_units']-received,shipment['pending_units'])
            for row in b['calibration_audit']:
                self.assertGreater(instant(row['audit_available_at']),instant(row['feature_cutoff_at']))
                if not row['minor_order_present']:
                    self.assertFalse(row['burst_applied'])
                    self.assertEqual(row['calibrated_minor_requested_units'],0)
    def test_observed_target_does_not_include_unfulfilled_orders(self):
        args=list(self.fixture());args[0]['profiles']=[{'name':'PARTIAL_LATE','weight':1.}]
        b=simulate(*args,months=4)
        self.assertTrue(any(o['unmet_units']>0 for o in b['orders']))
        for month in b['base']:
            orders=[o for o in b['orders'] if o['mes']==month['mes']]
            self.assertEqual(month['unidades_vendidas_brutas'],sum(o['fulfilled_units'] for o in orders))
