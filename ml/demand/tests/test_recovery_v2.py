"""Explicit recovery uses VALIDATION snapshots, never TEST evaluation or fitting."""
import os
import unittest
from unittest.mock import patch
import admin_prediction_v2 as admin
from v2 import final_evaluation, final_evaluation_v2_2


class RecoveryTests(unittest.TestCase):
    def test_release_roundtrip_and_snapshot_separation(self):
        with patch.object(final_evaluation,'load_test_once',side_effect=AssertionError('No TEST')),patch.object(final_evaluation_v2_2,'load_test_once',side_effect=AssertionError('No TEST')):
            with patch.dict(os.environ,{'DEMAND_RELEASE':'2.2.0'}):
                current=admin.query({'productId':20,'locationId':5})
                self.assertEqual(current['version'],'V2.2.0');self.assertEqual(current['prediction'],0)
            with patch.dict(os.environ,{'DEMAND_RELEASE':'2.1.0'}):
                previous=admin.query({'productId':20,'locationId':5})
                self.assertEqual(previous['version'],'V2.1.0');self.assertEqual(previous['prediction'],40.8725)
                with self.assertRaises(admin.InferenceError):admin.query({'productId':20,'locationId':5,'targetMonth':'2026-06','historySnapshotId':current['historySnapshotId']})
            with patch.dict(os.environ,{'DEMAND_RELEASE':'2.2.0'}):
                restored=admin.query({'productId':20,'locationId':5})
                self.assertEqual(restored['prediction'],current['prediction']);self.assertEqual(restored['artifactSha256'],current['artifactSha256'])

    def test_unapproved_release_rejected(self):
        with patch.dict(os.environ,{'DEMAND_RELEASE':'../../other-model'}):
            with self.assertRaises(admin.InferenceError):admin.query({'action':'catalog'})


if __name__=='__main__':unittest.main()
