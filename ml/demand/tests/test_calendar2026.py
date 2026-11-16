import copy
import math
from decimal import Decimal
import json
import unittest
from v2 import calendar2026_runtime as runtime
from v2.calendar2026 import BUILD, REPORT, verify
from v2.scenario_data import FEATURES, NUMERIC, frame


def request():
    caps=runtime.capabilities(); s=caps['snapshots'][0]
    return {**{k:s[k] for k in ('productId','locationId','targetMonth','baseSnapshotId')},
        'contractVersion':caps['contractVersion'],'mode':'HYPOTHETICAL_SCENARIO','clientRequestId':'calendar-unit',
        'changes':{k:{'mode':'KEEP'} for k in caps['supportedChanges']},
        'replenishment':{'requested':False,'policy':'MONTH_END_COMMITMENT_FLOOR_V1','safetyStockUnits':5,'minimumOrderUnits':0,'orderMultipleUnits':1,'reviewPeriodDays':0}}


class Calendar2026Tests(unittest.TestCase):
    def test_november_price_quote_and_quantities_use_frozen_model_and_replenishment(self):
        p=request(); p['replenishment'].update(requested=True,safetyStockUnits=100)
        s=runtime.engine().get_snapshot(p['baseSnapshotId']); b=runtime.engine().state(s)
        h=runtime.snapshot_view(p['baseSnapshotId'])['history']
        cases={
            'KEEP':{},
            'PRICE':{'prices':{'mode':'SET_PRICES','retailPriceBs':str((b['retail']*Decimal('1.10')).quantize(Decimal('.0001'))),'wholesalePriceBs':str((b['wholesale']*Decimal('1.10')).quantize(Decimal('.0001'))),'effectiveAt':'2026-11-01T00:00:00-04:00'}},
            'QUOTE':{'quote':{'mode':'SET_HYPOTHETICAL_QUOTE','bsPerUsd':'9','observedAt':'2026-11-01T00:00:00-04:00'}},
            'HISTORY':{'history':{'mode':'REPLACE_SYNTHETIC_HISTORY','months':[dict(row,retailUnits=row['retailUnits']//2,wholesaleUnits=row['wholesaleUnits']//2,complete=True) for row in h]}},
            'STOCK':{'stock':{'mode':'SET_SELLABLE_STOCK','sellablePhysicalUnits':20}},
        }
        results={}
        for name,changes in cases.items():
            with self.subTest(case=name):
                q=copy.deepcopy(p); q['changes'].update(changes)
                prepared,_,_=runtime.engine().prepare(q,s)
                result=runtime.preview(q); results[name]=result
                expected,_=runtime.engine().estimate(prepared['features'])
                self.assertEqual(result['scenario'],expected)
                self.assertEqual(result['scenario']['status'],'OK')
                self.assertEqual(result['targetMonth'],'2026-11')
                repo=result['replenishment']
                required=math.ceil(max(expected['salesUnits'],prepared['committed']))+100
                position=prepared['stock']-prepared['reservedAfter']+prepared['incoming']
                self.assertEqual(repo['requiredUnits'],required)
                self.assertEqual(repo['availablePositionUnits'],position)
                self.assertEqual(repo['suggestedUnits'],max(0,required-position))
        self.assertEqual(results['QUOTE']['scenario'],results['KEEP']['scenario'])
        self.assertEqual(results['QUOTE']['replenishment']['suggestedUnits'],results['KEEP']['replenishment']['suggestedUnits'])
        self.assertNotEqual(results['HISTORY']['scenario']['salesUnits'],results['KEEP']['scenario']['salesUnits'])
        self.assertNotEqual(results['STOCK']['replenishment']['suggestedUnits'],results['KEEP']['replenishment']['suggestedUnits'])

    def test_november_usd_cost_uses_edited_quote_without_inventing_sales_effect(self):
        p=request(); s=runtime.engine().get_snapshot(p['baseSnapshotId'])
        p['changes']['quote']={'mode':'SET_HYPOTHETICAL_QUOTE','bsPerUsd':'9','observedAt':'2026-11-01T00:00:00-04:00'}
        p['changes']['cost']={'mode':'SIMULATE_IMPORT_USD','unitCostUsd':'5','freightPerUnitBs':'2','otherPerUnitBs':'3','effectiveAt':'2026-11-01T00:00:00-04:00'}
        prepared,_,_=runtime.engine().prepare(p,s)
        self.assertEqual(prepared['cost'],Decimal('50'))
        result=runtime.preview(p)
        self.assertEqual(result['deltaSalesUnits'],0)

    def test_november_outside_range_never_invents_prediction_or_replenishment(self):
        p=request(); p['replenishment']['requested']=True
        p['changes']['stock']={'mode':'SET_SELLABLE_STOCK','sellablePhysicalUnits':10000}
        result=runtime.preview(p)
        self.assertEqual(result['scenario']['status'],'OUT_OF_DOMAIN')
        self.assertIsNone(result['scenario']['salesUnits'])
        self.assertIsNone(result['replenishment']['suggestedUnits'])
    def test_published_dataset_hashes_and_chronological_split(self):
        verify()
        split=json.loads((BUILD/'split_manifest.json').read_text())
        self.assertEqual(split['splits']['TRAIN'],['2025-02','2026-04'])
        self.assertEqual(split['splits']['VALIDATION'],['2026-05','2026-07'])
        self.assertEqual(split['splits']['TEST'],['2026-08','2026-10'])
        self.assertFalse(split['random_split'])
        self.assertEqual(split['forecast_month'],'2026-11')

    def test_all_product_store_histories_align_with_model_lags(self):
        caps=runtime.capabilities()
        self.assertEqual(len(caps['snapshots']),168)
        self.assertEqual(len({s['productId'] for s in caps['snapshots']}),56)
        self.assertEqual(len({s['locationId'] for s in caps['snapshots']}),3)
        for s in caps['snapshots']:
            self.assertEqual(s['targetMonth'],'2026-11')
            base=runtime.engine().get_snapshot(s['baseSnapshotId'])
            self.assertEqual([h['month'] for h in s['historyMonthly']],[f'2026-{i:02d}' for i in range(1,11)])
            self.assertEqual(runtime.snapshot_view(s['baseSnapshotId'])['displayHistory'],s['historyMonthly'])
            for h in s['historyMonthly']:
                self.assertGreaterEqual(h['units'],0)
                self.assertEqual(h['units'],h['retailUnits']+h['wholesaleUnits']+h['unknownModeUnits'])
            for i,key in enumerate(('ventas_mes_anterior','ventas_hace_2_meses','ventas_hace_3_meses'),1):
                self.assertEqual(int(base['features'][key]),s['historyMonthly'][-i]['units'])
            self.assertNotIn('target_ventas_mes',base['features'])
            prices=base['prices'][0]
            self.assertLessEqual(Decimal(base['cost']['unit_cost_landed_bs']),Decimal(prices['precio_mayor_bs']))
            self.assertLessEqual(Decimal(prices['precio_mayor_bs']),Decimal(prices['precio_menor_bs']))

    def test_keep_round_trip_and_reproducible_inference(self):
        p=request(); first=runtime.preview(p); second=runtime.preview(p)
        self.assertEqual(first['datasetVersion'],'4.0.0')
        self.assertEqual(first['targetMonth'],'2026-11')
        self.assertEqual(first['featureCutoffAt'],'2026-11-01T00:00:00-04:00')
        self.assertEqual(first['scenario'],second['scenario'])
        self.assertEqual(first['deltaSalesUnits'],0)
        self.assertEqual(first['metrics']['partition'],'FINAL_TEST_SAVED')

    def test_preparation_reproduces_all_published_features(self):
        for s in runtime.release()[1].values():
            p=request(); p.update({k:s[k] for k in ('productId','locationId','targetMonth','baseSnapshotId')})
            derived,_,_=runtime.engine().prepare(p,s)
            for key in FEATURES:
                a,b=derived['features'][key],s['features'][key]
                if a=='' or b=='':self.assertEqual(a,b)
                else:self.assertAlmostEqual(float(a),float(b),places=6)

    def test_rejects_future_month_and_incoherent_prices(self):
        p=request(); p['targetMonth']='2026-12'
        with self.assertRaises(runtime.ScenarioError):runtime.preview(p)
        p=request(); p['changes']['prices']={'mode':'SET_PRICES','retailPriceBs':'100','wholesalePriceBs':'200','effectiveAt':'2026-11-01T00:00:00-04:00'}
        with self.assertRaises(runtime.ScenarioError):runtime.preview(p)

    def test_final_test_was_frozen_once_and_november_is_unknown(self):
        selection=json.loads((REPORT/'selection.json').read_text())
        final=json.loads((REPORT/'test-evaluation.json').read_text())
        self.assertTrue(selection['fixedBeforeTest'])
        self.assertTrue(final['evaluatedOnce'])
        self.assertFalse(final['selectedUsingTest'])
        self.assertFalse(final['forecastTargetKnown'])
        self.assertTrue((REPORT/'final-test-attempt.json').is_file())


if __name__=='__main__':unittest.main()
