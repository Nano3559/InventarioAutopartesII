"""Temporal and input contracts for exploratory alternatives, no TEST access."""
import copy
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from v2.alternatives import AlternativeForecaster, specifications, derived_lags, tsb
from v2.experiments import load_xy


class AlternativeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.T, cls.y = load_xy("TRAIN", fold_id="F1")
        cls.V, cls.z = load_xy("VALIDATION", fold_id="F1")

    def test_fixed_small_search_and_no_test_option(self):
        options = specifications()
        self.assertEqual(len(options), 14)
        self.assertEqual(len({o["id"] for o in options}), 14)
        self.assertEqual(sum(o["family"] == "tsb" for o in options), 4)

    def test_derived_columns_use_only_three_known_lags(self):
        X = pd.DataFrame(dict(ventas_mes_anterior=[0, 0, 5], ventas_hace_2_meses=[0, 2, 2], ventas_hace_3_meses=[0, 3, 1]))
        values = derived_lags(X)
        np.testing.assert_allclose(values[:, 0], [0, 2, 3])
        np.testing.assert_allclose(values[:, 1], [3, 1, 0])
        np.testing.assert_allclose(values[:, 2], [0, -2, 3])
        np.testing.assert_allclose(values[:, 3], [0, 5/3, 8/3])

    def test_tsb_zero_and_probability_decay(self):
        self.assertEqual(tsb([0, 0, 0], .1, .1), 0)
        self.assertAlmostEqual(tsb([10, 0], .1, .3), 7)
        self.assertLess(tsb([10, 0, 0], .1, .3), tsb([10, 0], .1, .3))

    def test_validation_fit_rejected_before_any_forest(self):
        spec = next(s for s in specifications() if s["family"] == "absolute_forest")
        with patch("sklearn.ensemble.RandomForestRegressor.fit", side_effect=AssertionError("No fitting")):
            with self.assertRaises(ValueError):
                AlternativeForecaster(spec).fit(self.V, self.z)

    def test_tsb_predict_does_not_mutate_history(self):
        model = AlternativeForecaster(next(s for s in specifications() if s["family"] == "tsb")).fit(self.T, self.y)
        before = copy.deepcopy(model.history_)
        np.testing.assert_array_equal(model.predict(self.V), model.predict(self.V.iloc[::-1])[::-1])
        self.assertEqual(model.history_, before)
        with self.assertRaises(ValueError):
            model.fit(self.T, self.y)

    def test_tsb_future_rows_cannot_change_first_month_prediction(self):
        model = AlternativeForecaster(next(s for s in specifications() if s["family"] == "tsb")).fit(self.T, self.y)
        first = self.V[self.V.mes_objetivo == "2025-07"]
        mask = self.V.mes_objetivo == "2025-07"
        np.testing.assert_array_equal(model.predict(first), model.predict(self.V)[mask])

    def test_no_prediction_in_fit_months(self):
        model = AlternativeForecaster(dict(id="lag1", family="lag1")).fit(self.T, self.y)
        with self.assertRaises(ValueError):
            model.predict(self.T)

    def test_simple_rules_have_exact_expected_outputs(self):
        for family in ["lag1", "median3", "weighted_recent"]:
            model = AlternativeForecaster(dict(id=family, family=family)).fit(self.T, self.y)
            lags = self.V[["ventas_mes_anterior", "ventas_hace_2_meses", "ventas_hace_3_meses"]].to_numpy()
            expected = lags[:, 0] if family == "lag1" else np.median(lags, axis=1) if family == "median3" else lags @ np.array([.6, .3, .1])
            np.testing.assert_allclose(model.predict(self.V), expected, rtol=1e-12, atol=1e-12)


if __name__ == "__main__":
    unittest.main()
