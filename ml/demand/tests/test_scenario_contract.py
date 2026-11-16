"""Structural design-contract checks. No API, business evaluator, fit or data IO."""
import copy
import json
import unittest
from pathlib import Path
import jsonschema

ROOT=Path(__file__).resolve().parents[1]


class ScenarioContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=json.loads((ROOT/'v2/contracts/scenarios.v1.json').read_text(encoding='utf-8'))
        cls.validator=jsonschema.Draft202012Validator(cls.contract['request_schema'],format_checker=jsonschema.FormatChecker())

    def request(self):return copy.deepcopy(self.contract['examples']['requests'][0])
    def invalid(self,value):self.assertTrue(list(self.validator.iter_errors(value)))

    def test_schemas_are_valid_and_endpoints_not_claimed_implemented(self):
        for name in ['request_schema','response_schema']:jsonschema.Draft202012Validator.check_schema(self.contract[name])
        jsonschema.Draft202012Validator.check_schema(self.contract['response_policy']['error_schema'])
        self.assertTrue(all(e['implemented'] is False for e in self.contract['proposed_endpoints']))
        self.assertEqual(self.contract['status'],'DESIGN_READY_IMPLEMENTATION_PENDING')

    def test_documented_requests_are_well_formed(self):
        for value in self.contract['examples']['requests']:self.validator.validate(value)

    def test_ids_cannot_be_strings_booleans_or_nonpositive(self):
        for value in ['28',True,0,-1,1.5]:
            r=self.request();r['productId']=value;self.invalid(r)

    def test_target_features_paths_and_legacy_price_modes_not_accepted(self):
        for name,value in [('target_ventas_mes',20),('features',{}),('modelPath','../model'),('role','ADMIN')]:
            r=self.request();r[name]=value;self.invalid(r)
        r=self.request();r['changes']['prices']={'mode':'PRICE2'};self.invalid(r)

    def test_price_change_requires_both_prices_and_date(self):
        r=copy.deepcopy(self.contract['examples']['requests'][1]);del r['changes']['prices']['wholesalePriceBs'];self.invalid(r)
        for amount in [150,0,-1,'0.00','-1','NaN','1e3','1,20']:
            r=copy.deepcopy(self.contract['examples']['requests'][1]);r['changes']['prices']['retailPriceBs']=amount;self.invalid(r)

    def test_keep_cannot_smuggle_an_override(self):
        r=self.request();r['changes']['prices']['retailPriceBs']='1.00';self.invalid(r)

    def test_quote_requires_positive_decimal_and_offset_date(self):
        for value in ['0','0.000000','-1','Infinity',10]:
            r=self.request();r['changes']['quote']={'mode':'SET_HYPOTHETICAL_QUOTE','bsPerUsd':value,'observedAt':'2026-03-31T12:00:00-04:00'};self.invalid(r)
        r=copy.deepcopy(self.contract['examples']['requests'][2]);r['changes']['quote']['observedAt']='2026-03-31T12:00:00';self.invalid(r)

    def test_history_is_three_complete_months_and_integer_units(self):
        rows=[{'month':m,'retailUnits':0,'wholesaleUnits':2,'unknownModeUnits':0,'complete':True} for m in ['2026-01','2026-02','2026-03']]
        r=self.request();r['changes']['history']={'mode':'REPLACE_SYNTHETIC_HISTORY','months':rows};self.validator.validate(r)
        for rows2 in [rows[:2],[{**rows[0],'retailUnits':-1},*rows[1:]],[{**rows[0],'retailUnits':.5},*rows[1:]],[{**rows[0],'complete':False},*rows[1:]]]:
            r['changes']['history']['months']=rows2;self.invalid(r)
        # Chronological order and arithmetic are semantic backend rules SC02+, not claimed implemented here.

    def test_import_cost_requires_explicit_per_unit_components(self):
        r=copy.deepcopy(self.contract['examples']['requests'][2]);del r['changes']['cost']['freightPerUnitBs'];self.invalid(r)

    def test_logistics_shape_bounds_and_ids(self):
        r=self.request();r['changes']['logistics']={'mode':'SET_LOGISTICS_PLAN','supplierLeadTimeDays':10,'internalRestockDays':2,'plannedOrderAt':'2026-04-01T00:00:00-04:00','pendingShipments':[{'shipmentId':'fixture-1','pendingUnits':8,'reservedAfterHorizonUnits':0,'expectedArrivalAt':'2026-04-12T00:00:00-04:00'}]};self.validator.validate(r)
        r['changes']['logistics']['supplierLeadTimeDays']=-1;self.invalid(r)

    def test_rules_assign_unimplemented_semantics_to_backend(self):
        rules=self.contract['domain_rules'];self.assertEqual(len({r['id'] for r in rules}),len(rules))
        self.assertTrue(all(r['enforcement']=='BACKEND_REQUIRED_NOT_IMPLEMENTED_BY_JSON_SCHEMA' for r in rules))
        self.assertEqual({'SC'+str(i).zfill(2) for i in range(1,22)},{r['id'] for r in rules})
        self.assertIn('Erika',self.contract['owners']['backend_and_ml_service'])
        self.assertIn('Ross',self.contract['owners']['frontend_and_dataset'])


if __name__=='__main__':unittest.main()
