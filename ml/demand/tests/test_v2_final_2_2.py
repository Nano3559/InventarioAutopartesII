"""One-shot safety with temporary fixtures, never opens real TEST."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pandas as pd
from v2 import final_evaluation_v2_2 as final
from v2.structure import ROOT


class Final22Guards(unittest.TestCase):
    def test_existing_reservation_rejected_before_selection_or_data(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            root=Path(folder);(root/final.FINAL).mkdir(parents=True)
            with patch.object(final,'read_selection',side_effect=AssertionError('No load')):
                with self.assertRaises(FileExistsError):final.evaluate(root)

    def test_failure_consumes_event_and_blocks_second_load(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            root=Path(folder)
            X=pd.DataFrame({'mes_objetivo':['2025-01']},index=pd.MultiIndex.from_tuples([(1,5,'2025-01')],names=['productId','locationId','mes_objetivo']))
            y=pd.Series([0],index=X.index,name='target_ventas_mes')
            with patch.object(final,'read_selection',return_value=({'artifact_sha256':'fixture'},'fixture')),patch.object(final,'load_model',return_value=object()),patch.object(final,'load_xy',return_value=(X,y)),patch.object(final,'load_test_once',side_effect=RuntimeError('fixture failure')) as loader:
                with self.assertRaises(RuntimeError):final.evaluate(root)
                with self.assertRaises(FileExistsError):final.evaluate(root)
                self.assertEqual(loader.call_count,1)
            self.assertTrue((root/final.FINAL/'failure.json').exists())

    def test_unapproved_policy_rejected_before_loading(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            root=Path(folder);p=root/final.SELECTION;p.parent.mkdir(parents=True)
            p.write_text(json.dumps(dict(evaluation_version=final.VERSION,accepted_candidate=final.ACCEPTED,user_accepted=True,test_authorization='ONE_FINAL_EVALUATION_NO_RETRAINING',prediction_policy={**final.POLICY,'rounding':'CEIL'})),encoding='utf-8')
            with self.assertRaises(ValueError):final.read_selection(root)


if __name__=='__main__':unittest.main()
