"""Preparación 2.2 con TRAIN/VALIDATION y fixtures. Ningún regresor se ajusta."""
import copy
import csv
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from v2.structure import ROOT
from v2.data_v2_2 import read_context,read_prefix,load_feature_partition,load_records,verify_targets_and_lags,window_for
from v2.preprocessing import RAW,CONTEXT,validate_frame
from v2.preprocessing_v2_2 import DemandPreprocessor22
from v2.experiments_v2_2 import load_xy,align_targets,candidates,make_pipeline,context,execute_experiments
from v2.validate_build import canonical_hash,cutoff,month_offset


def fixture_frame(months):
    rows=[]
    for i,month in enumerate(months):
        m=int(month[-2:]);days=(cutoff(month)-cutoff(month_offset(month,-1))).days
        row=dict(zip(RAW,[2+i,3+i,4+i,math.sin(2*math.pi*m/12),math.cos(2*math.pi*m/12),.1+.01*i,.8+.01*i,120.+i,108.+i,.01*i,.005*i,10.+i*.1,.01*i,[0,2,7,30][i%4],i%3,(days-(i%2))/days,1+i%2]))
        row[CONTEXT]=month;rows.append(row)
    x=pd.DataFrame(rows,columns=[*RAW,CONTEXT]);x.attrs['fixture_only']=True;return x

class Preparation22Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.X,cls.y=load_xy('TRAIN');cls.V,cls.z=load_xy('VALIDATION')
        cls.spec,cls.plan,cls.fields,*_=read_context()
    def test_actual_outer_partitions_targets_and_prefix_limits(self):
        self.assertEqual((len(self.X),len(self.V)),(2520,504))
        self.assertTrue(self.X.index.equals(self.y.index));self.assertTrue(self.V.index.equals(self.z.index))
        self.assertEqual(self.X.attrs['prefix_rows_parsed'],2520)
        self.assertEqual(self.V.attrs['prefix_rows_parsed'],3024)
        self.assertEqual(self.V.attrs['target_alignment_evidence']['latest_month_parsed'],'2026-06')
        self.assertFalse(self.X.attrs['test_rows_loaded']);self.assertEqual(set(self.X.columns),set(RAW)|{CONTEXT})
    def test_test_rejected_before_metadata_or_data_open(self):
        with patch('v2.data_v2_2.read_context',side_effect=AssertionError('No abrir contexto')):
            for loader in [load_records,load_feature_partition,load_xy]:
                with self.assertRaises(PermissionError):loader('TEST')
    def test_prefix_reader_does_not_request_one_extra_row(self):
        parent=ROOT/'tmp/prepare-2.2-20261115-01';parent.mkdir(parents=True,exist_ok=True)
        class Guard:
            fieldnames=['productId','locationId','mes_objetivo']
            consumed=0
            def __iter__(self):return self
            def __next__(self):
                self.consumed+=1
                if self.consumed>1:raise AssertionError('TEST row requested')
                return dict(productId='1',locationId='5',mes_objetivo='2025-01')
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            path=Path(directory)/'fixture.csv';path.write_text('header')
            fields=[dict(name=n,type='integer' if n!='mes_objetivo' else 'month',nullable=False) for n in Guard.fieldnames]
            guard=Guard()
            with patch('v2.data_v2_2.csv.DictReader',return_value=guard):
                rows=read_prefix(path,fields,'2025-01','2025-01',dict(selected_product_ids=[1],selected_store_ids=[5]),CONTEXT)
            self.assertEqual(len(rows),1);self.assertEqual(guard.consumed,1)
    def test_folds_stay_inside_train_with_whole_month_cohorts(self):
        expected={'F1':1008,'F2':1512,'F3':2016}
        for fold in self.plan['temporal_validation']['folds']:
            X,_=load_xy('TRAIN',fold_id=fold['id']);V,_=load_xy('VALIDATION',fold_id=fold['id'])
            self.assertEqual(len(X),expected[fold['id']]);self.assertEqual(len(V),504)
            self.assertLess(X[CONTEXT].max(),V[CONTEXT].min());self.assertLessEqual(V[CONTEXT].max(),'2026-03')
        with self.assertRaises(ValueError):window_for('TRAIN','UNKNOWN',self.plan)
    def test_target_shuffle_realigns_but_missing_duplicate_negative_are_rejected(self):
        shuffled=self.y.sample(frac=1,random_state=42)
        self.assertTrue(align_targets(self.X,shuffled).equals(self.y))
        for y in [self.y.iloc[:-1],pd.concat([self.y,self.y.iloc[:1]])]:
            with self.assertRaises(ValueError):align_targets(self.X,y)
        bad=self.y.copy();bad.iloc[0]=-1
        with self.assertRaises(ValueError):align_targets(self.X,bad)
    def test_target_and_lag_are_checked_against_actual_base_prefix(self):
        _,rows=load_records('TRAIN');bad=list(rows);bad[0]={**bad[0],'target_ventas_mes':bad[0]['target_ventas_mes']+1}
        with self.assertRaises(ValueError):verify_targets_and_lags(bad)
        bad[0]={**rows[0],'ventas_mes_anterior':rows[0]['ventas_mes_anterior']+1}
        with self.assertRaises(ValueError):verify_targets_and_lags(bad)
    def test_no_target_ids_or_controls_allowed_in_feature_columns(self):
        for field in ['target_ventas_mes','productId','locationId','history_snapshot_id']:
            x=self.X.copy();x[field]=1
            with self.assertRaises(ValueError):validate_frame(x,self.fields)
    def test_real_preprocessor_fit_is_blocked_now(self):
        with patch('sklearn.preprocessing.StandardScaler.fit',side_effect=AssertionError('No fit real')):
            with self.assertRaises(PermissionError):DemandPreprocessor22().fit(self.X,self.y)
    def test_fixture_scaler_uses_train_only_and_transform_does_not_learn(self):
        X=fixture_frame([f'2025-{m:02d}' for m in range(1,13)])
        V=fixture_frame(['2026-04','2026-05','2026-06']);V.loc[0,'categoryId']=999;V.loc[0,'ventas_mes_anterior']=100000
        pre=DemandPreprocessor22()
        with patch('v2.preprocessing.read_context',side_effect=AssertionError('No contexto 2.1')):pre.fit(X)
        state=pre.to_state();before=canonical_hash(state);transformed=pre.transform(V)
        self.assertEqual(canonical_hash(pre.to_state()),before)
        self.assertEqual(state['state']['adapter_version'],'preprocessing-2.2-1')
        self.assertEqual(state['state']['fit_frame_origin'],'CONTROLLED_FIXTURE_ONLY')
        self.assertAlmostEqual(state['state']['means'][0],X.ventas_mes_anterior.mean())
        self.assertEqual(transformed[0,-1],1.)
        self.assertEqual(state['state']['y_used'],False)
        with self.assertRaises(ValueError):pre.fit(X)
    def test_forest_fixture_has_no_scaling_and_state_restores(self):
        X=fixture_frame([f'2025-{m:02d}' for m in range(1,13)])
        pre=DemandPreprocessor22(model_kind='random_forest').fit(X)
        state=pre.to_state();self.assertIsNone(state['state']['means']);self.assertIsNone(state['state']['scales'])
        restored=DemandPreprocessor22.from_state(state)
        np.testing.assert_array_equal(pre.transform(X),restored.transform(X))
        bad=copy.deepcopy(state);bad['state']['adapter_version']='preprocessing-2.1-1';bad['sha256']=canonical_hash(bad['state'])
        with self.assertRaises(ValueError):DemandPreprocessor22.from_state(bad)
    def test_validation_fit_and_constant_or_all_null_fixture_fail(self):
        with self.assertRaises(ValueError):DemandPreprocessor22().fit(fixture_frame(['2026-04','2026-05','2026-06']))
        X=fixture_frame([f'2025-{m:02d}' for m in range(1,13)])
        X['ventas_mes_anterior']=1
        with self.assertRaises(ValueError):DemandPreprocessor22().fit(X)
        X=fixture_frame([f'2025-{m:02d}' for m in range(1,13)]);X['proporcion_por_mayor_mes_anterior']=None
        with self.assertRaises(ValueError):DemandPreprocessor22().fit(X)
    def test_prepared_candidates_include_both_forest_criteria_without_fit(self):
        rows=candidates(self.plan);self.assertEqual(len(rows),54)
        self.assertEqual({r['parameters']['criterion'] for r in rows if r['model']=='random_forest'},{'squared_error','absolute_error'})
        self.assertEqual(len(rows)*3+12,174)
        with patch('sklearn.linear_model.LinearRegression.fit',side_effect=AssertionError('No fit')),patch('sklearn.ensemble.RandomForestRegressor.fit',side_effect=AssertionError('No fit')):
            pipeline=make_pipeline(next(r for r in rows if r['model']=='linear_regression'))
            self.assertFalse(hasattr(pipeline.named_steps['preprocessing'],'_fitted_'))
    def test_execution_refuses_before_any_context_or_factory(self):
        with patch('v2.experiments_v2_2.context',side_effect=AssertionError('No contexto')):
            with self.assertRaises(PermissionError):execute_experiments('blocked')
