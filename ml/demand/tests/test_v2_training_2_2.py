"""Comparación con dobles sin aprendizaje y fixtures, nunca TEST."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from v2.train_v2_2 import context,compare,factory
from v2.experiments import score_predictions
from v2.experiments_v2_2 import load_xy,candidates,execute_experiments
from v2.preprocessing_train_v2_2 import AuthorizedPreprocessor22
from v2.preprocessing_v2_2 import DemandPreprocessor22
from tests.test_v2_preparation_2_2 import fixture_frame

class Training22Tests(unittest.TestCase):
    def test_separate_authorization_does_not_unlock_preparation_runner(self):
        auth,plan,*_=context();self.assertTrue(auth['model_training_authorized']);self.assertFalse(auth['test_allowed'])
        self.assertFalse(plan['training_authorized'])
        with self.assertRaises(PermissionError):execute_experiments('no')
    def test_factory_is_unfitted_and_uses_authorized_adapter(self):
        _,plan,*_=context();candidate=candidates(plan)[0];pipeline=factory(candidate)
        self.assertIsInstance(pipeline.named_steps['preprocessing'],AuthorizedPreprocessor22)
        self.assertFalse(hasattr(pipeline.named_steps['model'],'coef_'))
    def test_unauthorized_scope_is_rejected_before_loading(self):
        auth,*_=context();auth['test_allowed']=True
        with patch('pathlib.Path.read_text',return_value=json.dumps(auth)):
            with self.assertRaises(PermissionError):context()
    def test_adapter_keeps_train_boundary_and_state_version(self):
        X=fixture_frame([f'2025-{m:02d}' for m in range(1,13)])
        pre=AuthorizedPreprocessor22(feature_set_id='expanded_baseline_v1_features').fit(X)
        self.assertEqual(pre.to_state()['state']['adapter_version'],'preprocessing-2.2-training-1')
        self.assertEqual(pre.to_state()['state']['fit_frame_origin'],'CONTROLLED_FIXTURE_ONLY')
        with self.assertRaises(ValueError):AuthorizedPreprocessor22().fit(fixture_frame(['2026-04','2026-05','2026-06']))
        with self.assertRaises(ValueError):DemandPreprocessor22.from_state(pre.to_state())
    def test_comparison_only_requests_train_validation_and_respects_budget(self):
        _,plan,*_=context();plan=copy.deepcopy(plan);plan['feature_sets']=plan['feature_sets'][:1]
        plan['models']['random_forest']['grid']={'criterion':['squared_error','absolute_error'],'max_depth':[4],'min_samples_leaf':[2]}
        plan['execution_budget']['maximum_planned_fits']=11
        X,y=load_xy('TRAIN');V,z=load_xy('VALIDATION');X=X.iloc[:2];y=y.iloc[:2];V=V.iloc[:2];z=z.iloc[:2];calls=[]
        def loader(part,fold_id=None):
            self.assertIn(part,['TRAIN','VALIDATION']);calls.append((part,fold_id));return (X,y) if part=='TRAIN' else (V,z)
        def evaluator(candidate,pipeline,X,y,V,z):
            pred=z.to_numpy(dtype=float)
            return dict(candidate=candidate,pipeline=None,predictions=pred,score=score_predictions(z,pred),train_score=score_predictions(y,y.to_numpy()),fit_seconds=0.,predict_seconds=0.)
        result=compare(plan,loader,lambda c:object(),workers=2,evaluator=evaluator)
        self.assertEqual(result['fit_attempts'],11);self.assertFalse(result['test_loaded'])
        self.assertEqual(len(result['cv_records']),9)
        self.assertEqual(len(result['outer']),3)
        self.assertTrue(all(r['fit_partition']=='TRAIN' for r in result['cv_records']))
        self.assertNotIn('TEST',{p for p,_ in calls})
