"""Gate independiente y publicación local, sin entrenar modelos."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from v2.structure import ROOT,sha256_file
from v2.generate_calibrated_v1_1 import inputs,simulate
from v2.validate_calibrated import validate_tables
from v2.build_calibrated import build,verify_checksums,make_split
from v2.validate_build import split_issues

class CalibratedBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args=inputs();cls.bundle=simulate(*cls.args)
    def validate(self,bundle):
        a=self.args
        return validate_tables(bundle,a[2],a[3],a[0],a[1],a[-1],a[-2],a[4]['scenario_design']['scenarios'])
    def modified(self,table,index,field,value):
        b={**self.bundle,table:list(self.bundle[table])};b[table][index]={**b[table][index],field:value};return b
    def test_full_catalogue_and_audited_economics_pass(self):
        r=self.validate(self.bundle);self.assertEqual(r['failures'],[])
        self.assertEqual(r['counts']['base'],4032);self.assertEqual(r['counts']['supervised'],3528)
        self.assertEqual(r['counts']['daily'],122640)
        self.assertGreater(r['administrative_price_reviews'],0)
        self.assertFalse(r['test_target_statistics_computed'])
        self.assertEqual(self.args[-1]['dataset_version'],'2.2.0')
    def test_cost_review_is_not_silent_or_a_fabricated_cost(self):
        i=next(i for i,r in enumerate(self.bundle['pricing_audit']) if r['administrative_review'])
        self.assertIn('COST_CHANGED_BY_REVIEW',self.validate(self.modified('pricing_audit',i,'cost_changed_by_review',True))['failures'])
        self.assertIn('ADMIN_PRICE_FORMULA',self.validate(self.modified('pricing_audit',i,'retail_bs',9999))['failures'])
    def test_wrong_target_and_lag_are_rejected(self):
        self.assertIn('TARGET',self.validate(self.modified('supervised',0,'target_ventas_mes',99999))['failures'])
        self.assertIn('LAG_OR_CLOCK',self.validate(self.modified('supervised',0,'ventas_mes_anterior',99999))['failures'])
    def test_event_cannot_be_known_before_week_close(self):
        e=self.bundle['price_events'][0]
        self.assertIn('WEEK_PRICE_AVAILABLE',self.validate(self.modified('price_events',0,'available_at',e['week_start']))['failures'])
    def test_split_is_temporal_and_complete(self):
        split=make_split(self.bundle['supervised']);self.assertEqual(split_issues(self.bundle['supervised'],split),[])
        self.assertEqual([split['sets'][s]['rows'] for s in ['TRAIN','VALIDATION','TEST']],[2520,504,504])
        self.assertFalse(split['training_authorized'])
    def test_existing_build_refuses_before_loading_or_simulating(self):
        parent=ROOT/'tmp/build-calibrated-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            root=Path(directory);dest=root/'data/repuestopro_v2/2.2.0/existing';dest.mkdir(parents=True)
            with patch('v2.build_calibrated.inputs',side_effect=AssertionError('No leer inputs')):
                with self.assertRaises(FileExistsError):build('existing',root)
    def test_invalid_build_id_is_rejected(self):
        with self.assertRaises(ValueError):build('../escape')
    def test_checksum_detects_tampering_and_unlisted_files(self):
        parent=ROOT/'tmp/build-calibrated-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            root=Path(directory);p=root/'a.json';p.write_text('{}')
            (root/'checksums.sha256').write_text(sha256_file(p)+'  a.json\n')
            self.assertEqual(verify_checksums(root),1)
            (root/'unknown').write_text('x')
            with self.assertRaises(ValueError):verify_checksums(root)
            (root/'unknown').unlink();p.write_text('changed')
            with self.assertRaises(ValueError):verify_checksums(root)
    def test_failed_validation_never_creates_data_destination(self):
        parent=ROOT/'tmp/build-calibrated-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            root=Path(directory)
            with patch('v2.build_calibrated.inputs',return_value=self.args),patch('v2.build_calibrated.simulate',return_value=self.bundle),patch('v2.build_calibrated.validate_tables',return_value={'failures':['INTENTIONAL_FIXTURE_FAILURE']}):
                with self.assertRaises(ValueError):build('blocked',root)
            self.assertFalse((root/'data/repuestopro_v2/2.2.0/blocked').exists())
            self.assertTrue((root/'tmp/publish-2.2.0-blocked/FAILED.json').exists())
