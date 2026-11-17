import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

COMPARATOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(COMPARATOR))
from compare_models import comparison
from feature_adapter import adapt, outside_range, select_snapshot
from model_loader import checked_bytes, load_models
from features.lag_features import DERIVED
from v2 import calendar2026_runtime as runtime


class ComparatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release, cls.snapshots, cls.models, _ = load_models()
        cls.entry = cls.snapshots["calendar-2026-53-6-november"]

    def test_verified_models_and_missing_candidate(self):
        self.assertEqual(list(self.models), ["4.0.0", "4.1.1 C", "4.1.1 D"])
        self.assertEqual(self.models["4.0.0"]["sha256"], self.release["artifactSha256"])
        self.assertIsNone(self.models["4.1.1 C"]["pipeline"])
        self.assertIsNone(self.models["4.1.1 C"]["sha256"])
        self.assertEqual(len(self.models["4.1.1 D"]["sha256"]), 64)
        self.assertEqual(self.models["4.1.1 D"]["features"][-3:], DERIVED)

    def test_modified_manifest_never_reaches_deserialization(self):
        with patch("model_loader.RELEASE_SHA256", "0" * 64), patch("model_loader.joblib.load") as deserialize:
            with self.assertRaisesRegex(ValueError, "INTEGRITY_MISMATCH"):
                load_models()
            deserialize.assert_not_called()
        with self.assertRaisesRegex(ValueError, "INTEGRITY_MISMATCH"):
            checked_bytes(COMPARATOR / "model_loader.py", "0" * 64)

    def test_all_catalog_snapshots_and_common_input(self):
        self.assertEqual(len(self.snapshots), 168)
        for snapshot in self.snapshots.values():
            original, expanded, reason = adapt(snapshot)
            self.assertIsNone(reason)
            self.assertEqual(list(original.columns), self.release["features"])
            self.assertTrue(original.equals(expanded[original.columns]))
        original, expanded, _ = adapt(self.entry)
        np.testing.assert_allclose(expanded[DERIVED].iloc[0], [254 / 3, np.std([50, 74, 130]), 0])

    def test_determinism_and_equivalence_with_official_runtime(self):
        result = comparison(self.entry, self.release, self.models)
        self.assertEqual(result, comparison(self.entry, self.release, self.models))
        official, _ = runtime.engine().estimate(self.entry["features"])
        self.assertEqual(official["salesUnits"], result["models"][0]["forecastUnits"])
        self.assertAlmostEqual(result["models"][2]["absoluteDifferenceUnits"], 7.15)
        self.assertEqual(result["models"][1]["reason"], "ARTIFACT_NOT_PERSISTED")
        self.assertIsNone(result["observedUnits"])

    def test_shared_gate_and_missing_history(self):
        ineligible = next(s for s in self.snapshots.values() if outside_range(s, self.release["bounds"]))
        guarded = comparison(ineligible, self.release, self.models)
        self.assertEqual([m["status"] for m in guarded["models"]], ["ABSTAINED", "UNAVAILABLE", "ABSTAINED"])
        self.assertTrue(all(m["forecastUnits"] is None for m in guarded["models"]))
        self.assertEqual(guarded["models"][2]["reason"], "OUTSIDE_TRAINING_RANGE")
        broken = {**self.entry, "history": []}
        self.assertEqual(comparison(broken, self.release, self.models)["models"][0]["reason"], "UNAVAILABLE_REQUIRED_FEATURE")

    def test_invalid_input_and_snapshot_selection(self):
        self.assertIs(select_snapshot(self.snapshots, "2026-11", 53, 6), self.entry)
        self.assertIs(select_snapshot(self.snapshots, None, snapshot_id=self.entry["baseSnapshotId"]), self.entry)
        for month in ("2026-10", "2026-12"):
            with self.assertRaisesRegex(ValueError, "SNAPSHOT_MISMATCH_OR_UNAVAILABLE"):
                select_snapshot(self.snapshots, month, 53, 6)
        broken = copy.deepcopy(self.entry)
        broken["history"][0]["unidades_por_menor"] += 1
        with self.assertRaisesRegex(ValueError, "INCONSISTENT_SNAPSHOT_HISTORY"):
            adapt(broken)
        broken["features"]["mes_cos"] = float("inf")
        with self.assertRaisesRegex(ValueError, "INVALID_SNAPSHOT_VALUE"):
            adapt(broken)

    def test_streamlit_cards_render(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(str(COMPARATOR / "streamlit_app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual([card.label for card in app.metric], ["4.0.0", "4.1.1 C", "4.1.1 D"])
        self.assertEqual(app.title[0].value, "Comparador experimental de modelos predictivos")
        self.assertEqual(app.warning[0].value, "Una diferencia entre pronósticos no demuestra mayor precisión")
        self.assertEqual(app.metric[0].value, "87.17 u.")
        self.assertEqual(app.metric[1].value, "Sin pronóstico")
        self.assertEqual(app.metric[2].value, "80.02 u.")
        self.assertEqual(app.selectbox[2].value, "2026-11")
        app.selectbox[0].select(6).run()
        app.selectbox[1].select(5).run()
        self.assertFalse(app.exception)
        self.assertTrue(all(card.value == "Sin pronóstico" for card in app.metric))
        self.assertIn("stock_vendible_al_corte_unidades", app.warning[1].value)
