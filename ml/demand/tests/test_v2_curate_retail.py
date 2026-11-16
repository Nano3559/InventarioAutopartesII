"""Fixtures temporales para transformación, sin RAW productivo o modelos."""
import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from v2.curate_retail import m5, favorita, normalize_promotion, check_sorted_keys
from v2.validate_curated_retail import validate_favorita, validate_m5
from v2.structure import ROOT

class CurateRetailTests(unittest.TestCase):
    def setUp(self):
        parent=ROOT/'tmp/curate-retail-20261115-01';parent.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=parent);self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.out=self.root/'out';self.out.mkdir()
    def file(self,name,text):
        p=self.root/name;p.write_text(text,encoding='utf-8');return p
    def config(self):
        return {'selected_sales_file':'train.csv.7z','complete_calendar_months':{'start':'2013-01','end':'2017-07'},'reference_estimation_window':{'start':'2013-01','end':'2015-12'},'descriptive_comparison_window':{'start':'2016-01','end':'2017-07'}}
    def test_promotion_unknown_is_not_false_and_invalid_blocks(self):
        self.assertEqual(normalize_promotion(pd.Series([True,False,None,'TRUE'])).tolist(),['TRUE','FALSE','UNKNOWN','TRUE'])
        with self.assertRaises(ValueError):normalize_promotion(pd.Series(['discount']))
    def test_duplicate_or_unordered_keys_block_before_acceptance(self):
        frame=pd.DataFrame({'id':[1,2],'date':['2013-01-01']*2,'store_nbr':[1,1],'item_nbr':[1,1]})
        with self.assertRaises(ValueError):check_sorted_keys(frame)
        with self.assertRaises(ValueError):check_sorted_keys(frame.iloc[:1],999999999999999999)
    def test_m5_preserves_partial_months_and_rejects_gap_price_change(self):
        dates=pd.date_range('2011-01-29',periods=21)
        cal=pd.DataFrame({'date':dates.strftime('%Y-%m-%d'),'d':['d_'+str(i+1) for i in range(21)],'wm_yr_wk':[i//7+1 for i in range(21)]})
        cp=self.root/'calendar.csv';cal.to_csv(cp,index=False)
        prices=self.file('prices.csv','item_id,store_id,wm_yr_wk,sell_price\na,s,1,10\na,s,3,15\n')
        sales=pd.DataFrame({'item_id':['a'],'store_id':['s'],'cat_id':['c'],**{'d_'+str(i+1):[i] for i in range(21)}});sp=self.root/'sales.csv';sales.to_csv(sp,index=False)
        cfg=self.config();cfg['selected_sales_file']='sales.csv';cfg['reference_estimation_window']={'start':'2011-01','end':'2014-12'}
        result=m5({'calendar.csv':cp,'sell_prices.csv':prices,'sales.csv':sp},self.out,cfg)
        monthly=pd.read_parquet(self.out/'sales_monthly_observed.parquet');weekly=pd.read_parquet(self.out/'prices_weekly.parquet')
        self.assertEqual(result['source_units'],sum(range(21)))
        self.assertFalse(monthly.complete_month.any())
        self.assertEqual(monthly.days_observed.sum(),21)
        self.assertFalse(weekly.adjacent_change_eligible.any())
        self.assertTrue(weekly.relative_change.isna().all())
        self.assertEqual(weekly.available_at_assumed_date.iloc[0],'2011-02-05')
        profile={'sales_files':{'sales_train_evaluation.csv':{'units':{'sum':210.,'total':21,'zero':1}}},'prices':{'rows':2}}
        self.assertTrue(validate_m5(self.out,profile)['source_totals_match'])
        weekly.loc[1,'relative_change']=.5
        weekly.to_parquet(self.out/'prices_weekly.parquet',index=False)
        with self.assertRaises(ValueError):validate_m5(self.out,profile)
    def favorite_fixture(self):
        content={'items.csv.7z':'item_nbr,family\n1,A\n2,B\n3,C\n','stores.csv.7z':'store_nbr,city\n1,C\n',
          'holidays_events.csv.7z':'date,type\n2013-01-01,Holiday\n2013-01-01,Event\n','transactions.csv.7z':'date,store_nbr,transactions\n2013-01-01,1,5\n',
          'train.csv.7z':'id,date,store_nbr,item_nbr,unit_sales,onpromotion\n1,2013-01-01,1,1,2,True\n2,2013-01-01,1,2,0.5,\n3,2013-01-02,1,1,-1,False\n4,2016-01-01,1,1,0.5,False\n5,2016-01-01,1,3,2,True\n'}
        return {k:self.file(k,v) for k,v in content.items()}
    def test_favorita_preserves_sign_fraction_missing_days_and_reference_cohort(self):
        paths=self.favorite_fixture()
        @contextlib.contextmanager
        def stream(path):
            with path.open('rb') as f:yield f
        with patch('v2.curate_retail.archive_stream',stream):audit=favorita(paths,self.out,self.config())
        positive=pd.read_parquet(self.out/'positive_observations.parquet');negative=pd.read_parquet(self.out/'negative_adjustments.parquet')
        monthly=pd.read_parquet(self.out/'monthly_recorded_summary.parquet');cohorts=pd.read_parquet(self.out/'unit_cohorts.parquet').set_index('item_nbr')
        self.assertEqual(audit['input_rows'],5);self.assertEqual(audit['positive_rows'],4);self.assertEqual(audit['negative_rows'],1)
        self.assertEqual(positive.unit_sales.sum()+negative.unit_sales.sum(),4.)
        self.assertEqual(negative.unit_sales.iloc[0],-1.)
        self.assertEqual(positive.onpromotion.eq('UNKNOWN').sum(),1)
        self.assertFalse(monthly.product_store_panel_complete_certified.any())
        self.assertEqual(cohorts.loc[1,'unit_cohort'],'OBSERVED_INTEGER')
        self.assertEqual(cohorts.loc[2,'unit_cohort'],'OBSERVED_FRACTIONAL')
        self.assertEqual(cohorts.loc[3,'unit_cohort'],'UNKNOWN')
        self.assertEqual(len(pd.read_parquet(self.out/'holidays_events.parquet')),2)
        profile={'files':{'train.csv.7z':{'rows':5,'unit_sales':{'sum':4.,'negative':1,'zero':0,'fractional':2},'promotion':{'missing':1,'true':2,'false':2}}}}
        self.assertTrue(validate_favorita(self.out,profile,self.config())['source_totals_match'])
        monthly['product_store_panel_complete_certified']=True
        monthly.to_parquet(self.out/'monthly_recorded_summary.parquet',index=False)
        with self.assertRaises(ValueError):validate_favorita(self.out,profile,self.config())
