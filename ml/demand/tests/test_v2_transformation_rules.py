"""Valida diseño y trazabilidad sin transformar RAW o entrenar."""
import hashlib
import json
from pathlib import Path
import unittest
from v2.structure import ROOT

class TransformationRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy=json.loads((ROOT/'v2/contracts/retail_transformations.v2.json').read_text(encoding='utf-8'))
    def test_specification_does_not_claim_execution_or_enable_automotive(self):
        self.assertEqual(self.policy['status'],'DESIGN_DEFINED_NOT_EXECUTED')
        self.assertFalse(any(self.policy['execution'].values()))
        self.assertEqual(set(self.policy['sources']),{'m5_walmart','corporacion_favorita'})
        self.assertEqual(self.policy['owner'],'ROSS')
    def test_windows_are_chronological_inside_complete_calendar_months(self):
        for source in self.policy['sources'].values():
            full=source['complete_calendar_months'];ref=source['reference_estimation_window'];cmp=source['descriptive_comparison_window']
            self.assertLessEqual(full['start'],ref['start'])
            self.assertLessEqual(ref['start'],ref['end'])
            self.assertLess(ref['end'],cmp['start'])
            self.assertLessEqual(cmp['start'],cmp['end'])
            self.assertLessEqual(cmp['end'],full['end'])
        self.assertEqual(self.policy['sources']['m5_walmart']['complete_calendar_months'],{'start':'2011-02','end':'2016-04'})
        self.assertEqual(self.policy['sources']['corporacion_favorita']['complete_calendar_months']['end'],'2017-07')
    def test_pinned_snapshots_and_frozen_contracts_match(self):
        for source,identity in self.policy['source_identity'].items():
            manifest=json.loads((ROOT.parents[1]/identity['manifest_path']).read_text(encoding='utf-8'))
            self.assertEqual(identity['snapshot_id'],manifest['snapshot_id'])
            self.assertEqual(identity['inventory_sha256'],manifest['inventory_sha256'])
            self.assertEqual(identity['files'],[{k:f[k] for k in ['relative_path','sha256']} for f in manifest['files']])
        for name,expected in self.policy['frozen_references'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected)
    def test_m5_shared_prefix_and_unlabelled_favorita_inputs_are_excluded(self):
        m5=self.policy['sources']['m5_walmart'];fav=self.policy['sources']['corporacion_favorita']
        self.assertEqual(m5['selected_sales_file'],'sales_train_evaluation.csv')
        self.assertEqual(m5['excluded_sales_file'],'sales_train_validation.csv')
        self.assertEqual(fav['selected_sales_file'],'train.csv.7z')
        self.assertEqual(set(fav['exclude_from_sales']),{'test.csv.7z','sample_submission.csv.7z'})
    def test_patterns_have_single_source_distinct_ids_and_limits(self):
        patterns=self.policy['selected_patterns'];self.assertEqual(len(patterns),len({p['id'] for p in patterns}))
        for pattern in patterns:
            self.assertIn(pattern['source'],self.policy['sources'])
            self.assertTrue(pattern['limit'])
            self.assertIn(pattern['decision'],['SELECTED_REFERENCE','DIAGNOSTIC_ONLY'])
        self.assertEqual(sum(p['decision']=='SELECTED_REFERENCE' for p in patterns),8)
        self.assertEqual(self.policy['sources']['corporacion_favorita']['promotion']['values'],['TRUE','FALSE','UNKNOWN'])
