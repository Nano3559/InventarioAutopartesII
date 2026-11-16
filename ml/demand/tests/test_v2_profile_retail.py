"""Pruebas con fixtures privados, sin datasets operativos o entrenamiento."""
import contextlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from v2.profile_retail import Stats, inputs, archive_stream, profile_m5, profile_favorita
from v2.structure import ROOT

class RetailProfileTests(unittest.TestCase):
    def setUp(self):
        parent=ROOT/'tmp/profile-retail-20261115-01';parent.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=parent);self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def csv(self,name,text):
        p=self.root/name;p.write_text(text,encoding='utf-8');return p
    def test_streamed_statistics_preserve_zero_negative_missing_and_sampling(self):
        a=np.arange(2100,dtype=float);a[2]=np.nan;a[4]=-5
        x,y=Stats(),Stats();x.add(a)
        for part in np.array_split(a,7):y.add(part)
        self.assertEqual(x.summary(),y.summary())
        self.assertEqual(x.summary()['negative'],1)
        self.assertEqual(x.summary()['zero'],1)
        self.assertEqual(x.summary()['missing_or_nonfinite'],1)
    def test_blocked_automotive_never_opens_raw(self):
        with self.assertRaises(ValueError):inputs('automotive_spare_parts_demand',self.root)
    def test_archive_rejects_unexpected_members_before_streaming(self):
        with patch('v2.profile_retail.subprocess.run',return_value=SimpleNamespace(stdout='../escape.csv\n')):
            with self.assertRaises(ValueError):
                with archive_stream(self.root/'train.csv.7z'):pass
    def test_m5_prefix_is_compared_instead_of_concatenated(self):
        paths={}
        paths['calendar.csv']=self.csv('calendar.csv','date,d,event_name_1\n2020-01-31,d_1,\n2020-02-01,d_2,Event\n')
        base='id,item_id,store_id,cat_id,d_1'
        paths['sales_train_validation.csv']=self.csv('sales_train_validation.csv',base+'\na_validation,a,s,c,0\n')
        paths['sales_train_evaluation.csv']=self.csv('sales_train_evaluation.csv',base+',d_2\na_evaluation,a,s,c,0,3\n')
        paths['sell_prices.csv']=self.csv('sell_prices.csv','store_id,item_id,wm_yr_wk,sell_price\ns,a,1,0\ns,a,1,2\n')
        paths['sample_submission.csv']=self.csv('sample_submission.csv','id,F1\na_validation,0\n')
        result=profile_m5(paths,chunk=1)
        self.assertTrue(result['validation_is_exact_prefix_of_evaluation'])
        self.assertEqual(result['prices']['duplicates_product_store_week'],1)
        self.assertEqual(result['prices']['price']['zero'],1)
        self.assertEqual(result['sales_files']['sales_train_evaluation.csv']['monthly_units'],{'2020-01':0.0,'2020-02':3.0})
        paths['sales_train_evaluation.csv'].write_text(base+',d_2\na_evaluation,a,s,c,1,3\n')
        self.assertFalse(profile_m5(paths,chunk=1)['validation_is_exact_prefix_of_evaluation'])
    def test_favorita_does_not_turn_returns_missing_promotions_or_template_into_sales(self):
        content={
          'items.csv.7z':'item_nbr,family\n1,F\n',
          'stores.csv.7z':'store_nbr,city\n1,C\n',
          'oil.csv.7z':'date,dcoilwtico\n2020-01-01,\n',
          'holidays_events.csv.7z':'date,type\n2020-01-01,Holiday\n',
          'transactions.csv.7z':'date,store_nbr,transactions\n2020-01-01,1,2\n',
          'train.csv.7z':'id,date,store_nbr,item_nbr,unit_sales,onpromotion\n1,2020-01-01,1,1,-2,\n2,2020-01-02,1,1,0.5,True\n3,2020-01-02,1,1,0,False\n',
          'test.csv.7z':'id,date,store_nbr,item_nbr,onpromotion\n4,2020-02-01,1,2,False\n',
          'sample_submission.csv.7z':'id,unit_sales\n4,0\n'}
        paths={k:self.csv(k,v) for k,v in content.items()}
        @contextlib.contextmanager
        def stream(path):
            with path.open('rb') as f:yield f
        with patch('v2.profile_retail.archive_stream',stream):result=profile_favorita(paths,chunk=1)
        train=result['files']['train.csv.7z'];test=result['files']['test.csv.7z']
        self.assertEqual(train['unit_sales']['negative'],1)
        self.assertEqual(train['unit_sales']['fractional'],1)
        self.assertEqual(train['promotion']['missing'],1)
        self.assertEqual(train['business_duplicates_within_chunks_and_boundary'],1)
        self.assertTrue(train['business_duplicate_check_complete'])
        self.assertEqual(test['unknown_item_rows'],1)
        self.assertNotIn('unit_sales',test)
        self.assertNotIn('unit_sales',result['files']['sample_submission.csv.7z'])
