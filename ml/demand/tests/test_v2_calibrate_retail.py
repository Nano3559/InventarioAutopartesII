"""Estadísticas de calibración con fixtures. Sin modelos, RNG o datos finales."""
import unittest
import tempfile
from pathlib import Path
import pandas as pd
from v2.structure import ROOT
import numpy as np
from v2.calibrate_retail import distribution,series_metrics,seasonal_amplitude,exact_positive_metrics,build_policy,m5_reference,summarize_positive_bins,DTYPE

class RetailCalibrationTests(unittest.TestCase):
    def test_equal_series_summary_is_not_row_weighted(self):
        result=distribution([0,1]);self.assertEqual(result['mean'],.5);self.assertEqual(result['p50'],.5)
        self.assertIsNone(distribution([])['mean'])
    def test_monthly_zero_is_not_stockout_and_cv_handles_zero_mean(self):
        d=series_metrics([0,0,0]);self.assertEqual(d['zero_probability'],1)
        self.assertIsNone(d['cv']);self.assertIsNone(d['normalized_absolute_change_p95'])
        self.assertEqual(series_metrics([0,0,1,0])['longest_zero_run'],2)
    def test_negative_missing_and_fractional_source_units_are_not_rounded(self):
        for a in [[-1,2],[np.nan,2]]:
            with self.assertRaises(ValueError):series_metrics(a)
        self.assertEqual(exact_positive_metrics([.5,1.5])['p50'],1)
        self.assertIsNone(exact_positive_metrics([1])['cv'])
        with self.assertRaises(ValueError):exact_positive_metrics([0,1])
    def test_seasonality_requires_two_years_for_all_twelve_months(self):
        months=[f'{y}-{m:02d}' for y in [2013,2014] for m in range(1,13)]
        self.assertEqual(seasonal_amplitude(np.ones(24),months),0)
        self.assertIsNone(seasonal_amplitude(np.ones(23),months[:-1]))
    def test_quantiles_use_all_values_exactly_and_sample_is_not_used(self):
        a=np.arange(1,101);d=exact_positive_metrics(a)
        self.assertAlmostEqual(d['p95_over_p50'],np.quantile(a,.95)/np.median(a))
        self.assertEqual(d['n'],100)
    def test_policy_uses_reference_only_and_does_not_invent_unsupported_parameters(self):
        s=distribution([.1,.2]);prices={'weekly_change_probability':s,'conditional_median_absolute_relative_change':s,'conditional_up_share_per_changing_series':s}
        ref=dict(prices=prices,store_relative_volume_factor=s,monthly_zero_probability=s,monthly_cv=s,seasonal_amplitude=s)
        f={'groups':{'REFERENCE':{'OBSERVED_INTEGER':{'positive_metrics':{'p95_over_p50':s,'p99_over_p50':s}}}}}
        p=build_policy({'REFERENCE':ref,'COMPARISON':{'invalid':'must not influence'}},f)
        self.assertEqual(p['parameters']['weekly_price_change_probability']['value'],s['mean'])
        self.assertIsNone(p['parameters']['promotion_daily_probability']['value'])
        self.assertIsNone(p['parameters']['price_elasticity']['value'])
        self.assertIsNone(p['parameters']['bolivian_exchange_rate_stock_modalities_cost_lead_time']['value'])
        self.assertFalse(p['causal_effects_estimated'])

    def test_real_curated_window_names_are_read_without_leaking_comparison(self):
        parent=ROOT/'tmp/calibration-retail-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            base=Path(directory);rows=[]
            for year in [2013,2014,2015]:
                for month in range(1,13):
                    rows.append(dict(item_id='p',store_id='s',month=f'{year}-{month:02d}',units_observed=10 if year<2015 else 100,zero_days=0,days_observed=30,days_expected=30,complete_month=True,window='REFERENCE' if year<2015 else 'DESCRIPTIVE_COMPARISON'))
            pd.DataFrame(rows).to_parquet(base/'sales_monthly_observed.parquet',index=False)
            prices=pd.DataFrame([dict(item_id='p',store_id='s',window=w,adjacent_change_eligible=True,relative_change=v,previous_observation_gap=False) for w,v in [('REFERENCE',.1),('DESCRIPTIVE_COMPARISON',.9)]])
            prices.to_parquet(base/'prices_weekly.parquet',index=False)
            result=m5_reference(base)
            self.assertEqual(result['REFERENCE']['months'],24)
            self.assertEqual(result['COMPARISON']['months'],12)
            self.assertAlmostEqual(result['REFERENCE']['prices']['conditional_median_absolute_relative_change']['p50'],.1)
            self.assertAlmostEqual(result['COMPARISON']['prices']['conditional_median_absolute_relative_change']['p50'],.9)
            self.assertEqual(result['COMPARISON']['seasonal_amplitude']['n'],0)
            pd.DataFrame(rows[:24]).to_parquet(base/'sales_monthly_observed.parquet',index=False)
            with self.assertRaises(ValueError):m5_reference(base)

    def test_favorita_exact_series_cohorts_and_unknown_promotion_remain_separate(self):
        parent=ROOT/'tmp/calibration-retail-tests';parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            base=Path(directory);bins=base/'bins';bins.mkdir()
            pd.DataFrame({'item_nbr':[10,20],'unit_cohort':['OBSERVED_INTEGER','OBSERVED_FRACTIONAL']}).to_parquet(base/'unit_cohorts.parquet',index=False)
            pd.DataFrame([dict(item_nbr=10,store_nbr=1,window='REFERENCE',rows_observed=3,promotion_true=1,promotion_false=1,promotion_unknown=1),dict(item_nbr=20,store_nbr=1,window='REFERENCE',rows_observed=1,promotion_true=0,promotion_false=0,promotion_unknown=1),dict(item_nbr=10,store_nbr=1,window='DESCRIPTIVE_COMPARISON',rows_observed=2,promotion_true=0,promotion_false=2,promotion_unknown=0)]).to_parquet(base/'monthly_recorded_summary.parquet',index=False)
            np.array([(10000010,1,1,1.),(10000010,1,1,10.),(10000010,1,1,100.),(10000020,1,2,.5),(10000010,2,1,2.),(10000010,2,1,20.)],dtype=DTYPE).tofile(bins/'00.bin')
            d=summarize_positive_bins(base,bins,{'reference':4,'comparison':2},6)
            ref=d['groups']['REFERENCE'];fractional=ref['OBSERVED_FRACTIONAL'];integer=ref['OBSERVED_INTEGER']
            self.assertEqual(integer['positive_metrics']['n']['mean'],3)
            self.assertAlmostEqual(integer['positive_metrics']['p95_over_p50']['p50'],9.1)
            self.assertEqual(fractional['series_with_single_positive'],1)
            self.assertEqual(fractional['positive_metrics']['cv']['n'],0)
            self.assertEqual(fractional['promotion']['true_frequency_given_known_observed_rows']['n'],0)
            self.assertEqual(fractional['promotion']['known_coverage_in_observed_rows']['mean'],0)
            self.assertEqual(integer['promotion']['true_frequency_given_known_observed_rows']['p50'],.5)
