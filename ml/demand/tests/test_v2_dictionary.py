"""Contrato y compatibilidad de diseño. No crea datos ni ejecuta modelos."""
import copy
import json
from pathlib import Path
import unittest

from v2.structure import ROOT, validate_contract


class DatasetDictionaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dictionary = json.loads((ROOT / "v2/contracts/dataset_columns.v2.json").read_text(encoding="utf-8"))
        cls.matrix = json.loads((ROOT / "reports/v2/compatibility/compatibility-20261114-01/source_compatibility_matrix.json").read_text(encoding="utf-8"))

    def changed(self):
        return copy.deepcopy(self.dictionary)

    def column(self, doc, name):
        return next(c for c in doc["columns"] if c["name"] == name)

    def test_full_dictionary_and_legacy_reference_are_both_valid(self):
        validate_contract(self.dictionary, "dataset_schema")
        reference = json.loads((ROOT / "v2/contracts/dataset_columns.reference.json").read_text(encoding="utf-8"))
        validate_contract(reference, "dataset_schema")
        self.assertEqual(reference["status"], "DRAFT")
        self.assertEqual(self.dictionary["status"], "APPROVED")

    def test_target_cannot_become_input(self):
        doc = self.changed()
        self.column(doc, "target_ventas_mes")["role"] = "FEATURE"
        doc["design"]["feature_sets"]["v2_full"].append("target_ventas_mes")
        with self.assertRaises(ValueError):
            validate_contract(doc, "dataset_schema")

    def test_future_feature_is_rejected(self):
        doc = self.changed()
        self.column(doc, "precio_menor_cierre_anterior_bs")["availability_class"] = "POST_TARGET_CLOSE"
        with self.assertRaises(ValueError):
            validate_contract(doc, "dataset_schema")

    def test_target_is_not_known_at_cutoff(self):
        doc = self.changed()
        self.column(doc, "target_ventas_mes")["availability_class"] = "PRE_CUTOFF"
        with self.assertRaises(ValueError):
            validate_contract(doc, "dataset_schema")

    def test_ids_and_audit_columns_cannot_enter_features(self):
        for name in ("productId", "locationId", "mes_objetivo", "feature_cutoff_at", "quality_status", "history_snapshot_id"):
            doc = self.changed()
            self.column(doc, name).update(role="FEATURE", availability_class="PRE_CUTOFF")
            doc["design"]["feature_sets"]["v2_full"].append(name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_contract(doc, "dataset_schema")

    def test_category_is_not_an_ordinal_quantity(self):
        doc = self.changed()
        self.column(doc, "categoryId")["encoding"] = "NONE"
        with self.assertRaises(ValueError):
            validate_contract(doc, "dataset_schema")

    def test_external_transaction_rows_cannot_become_local_features(self):
        doc = self.changed()
        self.column(doc, "precio_menor_cierre_anterior_bs")["source_kind"] = "UCI_TRANSACTION_ROWS"
        with self.assertRaises(ValueError):
            validate_contract(doc, "dataset_schema")

    def test_gbp_prices_and_inverted_exchange_units_are_rejected(self):
        for name, unit in (("precio_menor_cierre_anterior_bs", "GBP/unidad"), ("tipo_cambio_bs_usd_conocido", "USD/Bs")):
            doc = self.changed()
            self.column(doc, name)["unit"] = unit
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_contract(doc, "dataset_schema")

    def test_feature_set_cannot_hide_controls_or_unknown_columns(self):
        for name in ("quality_status", "target_ventas_mes", "not_a_column"):
            doc = self.changed()
            doc["design"]["feature_sets"]["baseline_v1_features"].append(name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_contract(doc, "dataset_schema")

    def test_missing_months_and_invalid_cases_cannot_be_relabelled_trainable(self):
        for policy in ("missing_month_is_zero", "review_and_invalid_rows_in_training"):
            doc = self.changed()
            doc["design"]["row_policy"][policy] = True
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                validate_contract(doc, "dataset_schema")

    def test_external_id_mapping_and_random_row_split_are_rejected(self):
        doc = self.changed()
        doc["design"]["reference_use"]["external_row_mapping_allowed"] = True
        with self.assertRaises(ValueError):
            validate_contract(doc, "dataset_schema")
        doc = self.changed()
        doc["design"]["split_design"]["random_row_split_allowed"] = True
        with self.assertRaises(ValueError):
            validate_contract(doc, "dataset_schema")

    def test_supporting_tables_cannot_duplicate_columns(self):
        doc = self.changed()
        table = doc["design"]["supporting_tables"]["base_mensual.csv"]
        table["columns"].append(copy.deepcopy(table["columns"][0]))
        with self.assertRaises(ValueError):
            validate_contract(doc, "dataset_schema")

    def test_sources_are_references_with_matching_local_identity(self):
        self.assertEqual({s["source_id"] for s in self.matrix["sources"]}, {"monash_car_parts", "uci_online_retail_ii"})
        for source in self.matrix["sources"]:
            manifest = json.loads((ROOT.parents[1] / source["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(source["raw_sha256"], manifest["sha256"])
            self.assertEqual(source["snapshot_id"], manifest["snapshot_id"])
            self.assertFalse(source["direct_training_rows_allowed"])
            self.assertFalse(source["external_id_mapping_allowed"])
            self.assertFalse(source["calibrated_now"])

    def test_dictionary_does_not_claim_that_a_build_or_test_hash_exists(self):
        design = self.dictionary["design"]
        self.assertFalse(design["publication"]["build_created"])
        self.assertIsNone(design["split_design"]["test_hash"])
        self.assertEqual(design["split_design"]["target_month_counts"], {"train":15,"validation":3,"test":3})
        self.assertEqual(design["publication"]["destination"], "data/repuestopro_v2/<dataset_version>/<build_id>/")

    def test_all_feature_sets_and_candidate_groups_use_defined_columns(self):
        doc = self.dictionary
        columns = {c["name"]:c for c in doc["columns"]}
        features = {name for name,c in columns.items() if c["role"] == "FEATURE"}
        self.assertEqual(len(features), 17)
        self.assertNotIn("promedio_3_meses", features)
        groups = json.loads((ROOT / "v2/contracts/candidate_groups.json").read_text(encoding="utf-8"))
        for group in groups.values():
            self.assertTrue(set(group["columns"]).issubset(features))
            self.assertFalse(group["approved_for_training"])
        self.assertEqual(groups["reposicion"]["columns"], [])
        self.assertEqual(groups["tiempos_proveedor"]["columns"], [])


if __name__ == "__main__":
    unittest.main()
