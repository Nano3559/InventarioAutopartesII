import unittest
from unittest.mock import patch

import admin_prediction as admin


class AdminPredictionTests(unittest.TestCase):
    def test_catalog_and_prediction_use_frozen_model_without_training(self):
        catalog = admin.query(dict(action="catalog"))
        self.assertEqual(len(catalog["products"]), 56)
        self.assertEqual({r["id"] for r in catalog["locations"]}, {5, 6, 7})
        result = admin.query(dict(productId=1, locationId=5))
        self.assertEqual(result["targetMonth"], "2026-10")
        self.assertEqual(result["features"]["ventas_mes_anterior"], 22)
        self.assertEqual(result["features"]["ventas_hace_2_meses"], 18)
        self.assertEqual(result["features"]["ventas_hace_3_meses"], 26)
        self.assertAlmostEqual(result["prediction"], 22.06922935207354, places=8)
        self.assertEqual(result["metrics"]["n"], 504)

    def test_unknown_selection_and_booleans_are_not_product_ids(self):
        for value in [True, 0, -1, "1", 9999]:
            with self.subTest(value=value), self.assertRaises(admin.InvalidSelection):
                admin.query(dict(productId=value, locationId=5))

    def test_missing_duplicate_and_negative_history_are_rejected(self):
        histories = [[], [dict(month="2026-01", units=1)] * 3,
                     [dict(month=m, units=1) for m in ["2026-01", "2026-02", "2026-04"]],
                     [dict(month=m, units=-1) for m in ["2026-01", "2026-02", "2026-03"]]]
        for history in histories:
            with self.subTest(history=history), self.assertRaises(ValueError):
                admin.validate_history(history)

    def test_dataset_integrity_failure_abstains(self):
        with patch.object(admin, "BASE_SHA256", "invalid"), self.assertRaises(ValueError):
            admin.query(dict(productId=1, locationId=5))

    def test_zero_sales_are_valid_history(self):
        admin.validate_history([dict(month=m, units=0) for m in ["2026-01", "2026-02", "2026-03"]])

    def test_catalog_and_test_report_cannot_be_silently_replaced(self):
        for name in ["CATALOG_SHA256", "TEST_REPORT_SHA256"]:
            with self.subTest(name=name), patch.object(admin, name, "invalid"), self.assertRaises(ValueError):
                admin.query(dict(productId=1, locationId=5))
