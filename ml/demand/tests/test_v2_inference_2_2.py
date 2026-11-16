"""Final 2.2 runtime checks. TEST loader and training are forbidden here."""
import csv
import unittest
from unittest.mock import patch
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from v2.inference_v2_2 import FrozenDemandInference, InferenceError, validate_request
from v2.preprocessing_train_v2_2 import AuthorizedPreprocessor22
from v2 import final_evaluation_v2_2 as final
from v2.structure import ROOT


class Inference22Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(final,'load_test_once',side_effect=AssertionError('Never reload TEST')),patch.object(AuthorizedPreprocessor22,'fit',side_effect=AssertionError('No fit')):
            cls.runtime=FrozenDemandInference()

    def test_all_504_validation_predictions_match_training_report(self):
        path=ROOT/'reports/v2/2.2.0/calibrated-20261115-01/runs/train-2.2-20261115-01/validation_predictions.csv'
        with path.open(encoding='utf-8') as f:
            rows=[r for r in csv.DictReader(f) if r['candidate_id']==final.ACCEPTED]
        keys=[(int(r['productId']),int(r['locationId']),r['mes_objetivo']) for r in rows]
        with patch.object(final,'load_test_once',side_effect=AssertionError('No TEST')),patch.object(RandomForestRegressor,'fit',side_effect=AssertionError('No fit')),patch.object(StandardScaler,'fit',side_effect=AssertionError('No fit')):
            actual=self.runtime.model.predict(self.runtime._features.loc[keys])
        np.testing.assert_allclose(actual,[float(r['raw_prediction']) for r in rows],rtol=0,atol=1e-12)
        self.assertEqual(len(actual),504)

    def test_identity_metrics_and_policy_are_frozen(self):
        r=self.runtime.predict(self.runtime.request_for(28,5,'2026-04'))
        self.assertEqual(r['prediction'],40.96)
        self.assertEqual(r['datasetVersion'],'2.2.0')
        self.assertEqual(r['policyVersion'],'NONNEGATIVE_CONTINUOUS_1')
        self.assertEqual(r['evaluationContext']['mae'],9.204618055555557)
        self.assertEqual(r['artifactSha256'],'def5a93dcabf27916d1120af0160d2910dc7737f4036ec2507f60eb7d5670f35')

    def test_snapshot_and_unknown_entities_reject_before_prediction(self):
        req=self.runtime.request_for(28,5,'2026-04')
        with patch.object(self.runtime.model,'predict',side_effect=AssertionError('No predict')):
            for changes,code in [({'historySnapshotId':'different'},'SNAPSHOT_MISMATCH'),({'productId':99999},'UNKNOWN_ENTITY'),({'locationId':1},'UNKNOWN_ENTITY'),({'targetMonth':'2026-07'},'UNAVAILABLE_REQUIRED_FEATURE')]:
                with self.subTest(changes=changes),self.assertRaises(InferenceError) as err:self.runtime.predict({**req,**changes})
                self.assertEqual(err.exception.code,code)

    def test_nonfinite_and_wrong_shape_fail_closed(self):
        req=self.runtime.request_for(28,5,'2026-04')
        for raw in [np.array([np.nan]),np.array([np.inf]),np.array([1.,2.])]:
            with patch.object(self.runtime.model,'predict',return_value=raw),self.assertRaises(InferenceError):self.runtime.predict(req)

    def test_policy_clips_without_rounding(self):
        req=self.runtime.request_for(28,5,'2026-04')
        with patch.object(self.runtime.model,'predict',return_value=np.array([-1.])):
            r=self.runtime.predict(req);self.assertEqual(r['prediction'],0);self.assertIn('NEGATIVE_PREDICTION_CLIPPED',r['warnings'])
        with patch.object(self.runtime.model,'predict',return_value=np.array([1.23456789])):self.assertEqual(self.runtime.predict(req)['prediction'],1.23456789)

    def test_stale_contract_and_extra_features_rejected(self):
        req=self.runtime.request_for(28,5,'2026-04')
        for changes in [{'contractVersion':'v2-inference-2.1-1'},{'features':{}},{'productId':True}]:
            with self.subTest(changes=changes),self.assertRaises(InferenceError):validate_request({**req,**changes})

    def test_final_test_cannot_repeat(self):
        with patch.object(final,'load_test_once',side_effect=AssertionError('No second TEST')):
            with self.assertRaises(FileExistsError):final.evaluate()


if __name__=='__main__':unittest.main()
