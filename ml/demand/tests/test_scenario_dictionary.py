"""R01 dictionary design checks. No dataset creation, training or database access."""
import csv
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ScenarioDictionaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=json.loads((ROOT/'v2/contracts/dataset_dictionary.scenarios.v1.json').read_text(encoding='utf-8'))
        cls.c=json.loads((ROOT/'v2/contracts/scenarios.v1.json').read_text(encoding='utf-8'))
        cls.old=json.loads((ROOT/'v2/contracts/dataset_columns.v2.json').read_text(encoding='utf-8'))

    def test_bound_to_exact_contracts_without_rewriting_reference(self):
        for name in ['contract_binding','legacy_binding']:
            b=self.d[name];self.assertEqual(hashlib.sha256((ROOT/b['path']).read_bytes()).hexdigest(),b['sha256'])
        self.assertTrue(self.d['no_dataset_generated']);self.assertEqual(self.d['dataset_version'],'NOT_ASSIGNED_NO_BUILD_CREATED')

    def test_every_primitive_contract_input_has_one_dictionary_binding(self):
        defs=self.c['request_schema']['$defs'];paths=set()
        def walk(node,path):
            if '$ref' in node:return walk(defs[node['$ref'].split('/')[-1]],path)
            if 'oneOf' in node:
                for branch in node['oneOf']:walk(branch,path)
            elif node.get('type')=='object':
                for key,value in node['properties'].items():walk(value,path+'.'+key if path else key)
            elif node.get('type')=='array':walk(node['items'],path+'[]')
            else:paths.add(path)
        walk(self.c['request_schema'],'')
        wire=self.d['request_fields'];self.assertEqual(paths,{w['path'] for w in wire});self.assertEqual(len(wire),len(paths))
        self.assertEqual(len(paths),48)
        for w in wire:
            fields=self.d['tables'][w['proposed_table']]['fields'];f=next(f for f in fields if f['name']==w['proposed_column'])
            self.assertIn(w['path'],f['request_paths']);self.assertEqual(w['role'],f['role']);self.assertEqual(w['wire_type'],f['type']['wire'])

    def test_all_definitions_have_types_units_sources_and_availability(self):
        required={'name','type','role','source_ids','availability_class','availability_rule','description','missing_policy','model_input_status','derivation','implementation_status','physical_field_claim','bounds'}
        for table in self.d['tables'].values():
            names=[f['name'] for f in table['fields']];self.assertEqual(len(names),len(set(names)))
            self.assertTrue(set(table['primary_key'])<=set(names))
            for f in table['fields']:
                with self.subTest(field=f['name']):
                    self.assertTrue(required<=set(f));self.assertIn(f['role'],self.d['roles'])
                    self.assertTrue({'logical','wire','storage','unit','nullable'}<=set(f['type']))
                    self.assertTrue(f['type']['unit']);self.assertTrue(set(f['source_ids'])<=set(self.d['sources']))
                    self.assertIn(f['availability_class'],self.d['availability_catalog'])

    def test_real_source_names_are_declared_in_actual_prisma(self):
        text=(ROOT.parents[1]/'backend/prisma/schema.prisma').read_text(encoding='utf-8')
        models={name:set(re.findall(r'^\s*(\w+)\s+\S+',body,re.M)) for name,body in re.findall(r'model\s+(\w+)\s*\{(.*?)\n\}',text,re.S)}
        for source in self.d['sources'].values():
            for physical in source['physical']:
                model,field=physical.split('.')
                self.assertIn(model,models);self.assertIn(field,models[model])

    def test_legacy_supervised_names_and_roles_are_preserved(self):
        fields=self.d['tables']['supervised_monthly']['fields']
        self.assertEqual([f['name'] for f in fields[:24]],[c['name'] for c in self.old['columns']])
        for f,c in zip(fields[:24],self.old['columns']):
            self.assertEqual(f['role'],c['role']);self.assertEqual(f['legacy_wire_type'],c['type']);self.assertEqual(f['type']['nullable'],c['nullable'])
        self.assertEqual(len(fields),43)

    def test_no_post_cutoff_outcomes_or_audit_fields_are_features(self):
        features=[f for f in self.d['tables']['supervised_monthly']['fields'] if f['role']=='FEATURE']
        self.assertEqual(len(features),33)
        for f in features:
            self.assertIn(f['availability_class'],['CUTOFF','HISTORY','PLAN','CALENDAR'])
            self.assertEqual(f['model_input_status'],'CANDIDATE_PENDING_R02_R03_E04')
        for name in ['receipt_outcomes','monthly_outcomes','replenishment_policy','decision_outputs','scenario_context']:
            self.assertFalse(any(f['role']=='FEATURE' for f in self.d['tables'][name]['fields']))

    def test_target_is_integer_gross_observed_units_after_close(self):
        f=next(f for f in self.d['tables']['supervised_monthly']['fields'] if f['role']=='TARGET')
        self.assertEqual(f['name'],'target_ventas_mes');self.assertEqual(f['type']['logical'],'integer')
        self.assertFalse(f['type']['nullable']);self.assertEqual(f['availability_class'],'OUTCOME')
        self.assertEqual(f['model_input_status'],'EXCLUDED_FROM_X')

    def test_identifiers_and_category_do_not_become_quantities(self):
        fields={f['name']:f for f in self.d['tables']['supervised_monthly']['fields']}
        for n in ['productId','locationId','scenario_id']:
            self.assertEqual(fields[n]['role'],'IDENTIFIER');self.assertEqual(fields[n]['model_input_status'],'EXCLUDED_FROM_X')
        self.assertEqual(fields['categoryId']['type']['logical'],'categorical')

    def test_economic_sources_separate_stored_landed_cost_and_import_components(self):
        fields={f['name']:f for f in self.d['tables']['cost_plan_events']['fields']}
        self.assertEqual(fields['unit_cost_usd']['type']['unit'],'USD/unidad')
        self.assertEqual(fields['unit_cost_landed_bs']['type']['unit'],'Bs/unidad')
        self.assertEqual(fields['source_percentage']['type']['unit'],'porcentaje de recargo, escala 0 a 100')
        self.assertTrue(all(f['model_input_status']=='EXCLUDED_FROM_X' for f in fields.values()))
        self.assertEqual(next(f for f in self.d['tables']['exchange_quote_events']['fields'] if f['name']=='bs_per_usd')['type']['unit'],'Bs/USD')

    def test_reference_headers_match_without_loading_observations(self):
        source=ROOT/'data/repuestopro_v2/2.2.0/calibrated-20261115-01'
        for name,expected in self.d['reference_headers'].items():
            with (source/name).open(encoding='utf-8',newline='') as f:actual=next(csv.reader(f))
            self.assertEqual(actual,expected)

    def test_all_new_features_are_candidates_not_frozen_columns(self):
        fields=[f for f in self.d['tables']['supervised_monthly']['fields'] if f.get('candidate_not_selected')]
        self.assertEqual(len(fields),16)
        self.assertTrue(all(f['frozen_2_2_exists'] is False for f in fields))

    def test_decision_quantities_and_history_quantities_are_distinct(self):
        decision={f['name']:f for f in self.d['tables']['decision_outputs']['fields']}
        self.assertEqual(decision['delta_sales_units']['type']['unit'],'unidades de repuesto, salida continua')
        self.assertNotIn('minimum',decision['delta_sales_units']['bounds'])
        self.assertEqual(decision['suggested_units']['availability_class'],'AUDIT')
        self.assertFalse(decision['suggested_units']['physical_field_claim'])


if __name__=='__main__':unittest.main()
