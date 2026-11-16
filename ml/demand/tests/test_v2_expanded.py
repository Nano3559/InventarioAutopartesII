"""Edades fechadas y ventas grandes atendidas, sin ajustar ningún modelo."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from v2.structure import ROOT,sha256_file
from v2.generate_expanded import inputs,simulate,build,FILES,validate_schema
from v2.validate_expanded import validate_tables,inspect
from v2.validate_build import canonical_hash,split_issues


class ExpandedDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args=inputs();cls.bundle=simulate(*cls.args)
        cls.config,cls.legacy,cls.schema,cls.catalog,cls.prep=cls.args

    def validate(self,bundle):
        return validate_tables(bundle,self.schema,self.catalog,self.config,self.legacy)

    def changed(self,table,index,field,value):
        bundle={**self.bundle,table:list(self.bundle[table])}
        bundle[table][index]={**bundle[table][index],field:value}
        return bundle

    def test_full_grid_and_independent_data_gate(self):
        report=self.validate(self.bundle)
        self.assertEqual(report["status"],"PASSED_EXPANDED_DATA_GATE",report["failures"])
        self.assertEqual(report["counts"]["base"],4032)
        self.assertEqual(report["counts"]["supervised"],3528)
        self.assertEqual(report["counts"]["daily"],122640)
        self.assertFalse(report["training_authorized"])

    def test_seed_reproduces_every_data_table_without_input_mutation(self):
        before=canonical_hash(self.args)
        second=simulate(*self.args)
        for name in self.bundle:
            with self.subTest(table=name):self.assertEqual(canonical_hash(second[name]),canonical_hash(self.bundle[name]))
        self.assertEqual(canonical_hash(self.args),before)

    def test_all_four_ages_exist_in_train_and_all_17_features_vary(self):
        report=self.validate(self.bundle)
        self.assertEqual(report["train_quote_ages_days"],[0,2,7,30])
        profile=report["statistics"]["TRAIN"]["features"]
        self.assertEqual(len(profile),17)
        self.assertTrue(all(p["unique_nonnull"]>1 for p in profile.values()))

    def test_large_wholesale_means_fulfilled_units_not_requested(self):
        report=self.validate(self.bundle)
        volume=report["wholesale_volume"]["TRAIN"]
        for q in [20,40,80]:self.assertGreater(volume["fulfilled_at_least"][str(q)],0)
        self.assertGreater(volume["partially_or_unfulfilled"],0)
        self.assertGreater(volume["fully_fulfilled"],0)

    def test_quote_age_jitter_without_event_change_is_rejected(self):
        bad=self.changed("supervised",0,"antiguedad_tipo_cambio_dias",99)
        self.assertIn("FX_AGE",self.validate(bad)["failures"])

    def test_corrupted_quote_publication_is_rejected(self):
        bad=self.changed("quotes",3,"available_at","2030-01-01T00:00:00-04:00")
        self.assertIn("QUOTE_ASOF_NOT_JITTER",self.validate(bad)["failures"])

    def test_forced_large_fulfilment_without_receipt_is_rejected(self):
        index=next(i for i,o in enumerate(self.bundle["orders"]) if o["unmet_units"]>0)
        bad=self.changed("orders",index,"fulfilled_units",self.bundle["orders"][index]["requested_units"])
        self.assertTrue(self.validate(bad)["failures"])

    def test_receipt_before_dispatch_is_rejected(self):
        bad=self.changed("receipts",0,"received_at","2020-01-01T00:00:00-04:00")
        self.assertIn("RECEIVED_BEFORE_SENT",self.validate(bad)["failures"])

    def test_double_receipt_is_rejected(self):
        bad={**self.bundle,"receipts":self.bundle["receipts"]+[self.bundle["receipts"][0]]}
        self.assertIn("DUPLICATE_RECEIPT",self.validate(bad)["failures"])

    def test_plan_cannot_claim_unknown_future_orders(self):
        bad=self.changed("plans",0,"known_order_ids",'["UNKNOWN_FUTURE_ORDER"]')
        self.assertIn("PLAN_USED_UNKNOWN_FUTURE_ORDER",self.validate(bad)["failures"])

    def test_bootstrap_does_not_fabricate_preperiod_history(self):
        first=[p for p in self.bundle["plans"] if p["mes"]=="2024-10"]
        self.assertTrue(all(p["history_units"]=="[]" and p["history_months"]=="[]" and p["bootstrap"]==1 for p in first))
        bad=self.changed("plans",0,"history_units","[0,0,0]")
        self.assertIn("PLAN_HISTORY",self.validate(bad)["failures"])

    def test_daily_stock_rewrite_is_rejected(self):
        bad=self.changed("daily",0,"closing_stock",999)
        self.assertIn("DAILY_CONSERVATION",self.validate(bad)["failures"])

    def test_mode_cannot_be_inferred_or_changed_by_price(self):
        bad=self.changed("orders",0,"recorded_mode","PRICE1")
        self.assertIn("FABRICATED_MODE",self.validate(bad)["failures"])

    def test_scenario_metadata_requires_observed_event_and_registered_action(self):
        bad=self.changed("audit",0,"expected_action","REJECT")
        self.assertIn("AUDIT_ACTION",self.validate(bad)["failures"])
        bad=self.changed("audit",0,"latent_demand_units",999)
        self.assertIn("AUDIT_LATENT_IS_CONTROL_ONLY",self.validate(bad)["failures"])

    def test_requested_units_cannot_be_forged_independently_of_orders(self):
        bad=self.changed("ledger",0,"latent_units",999)
        self.assertIn("REQUESTED_UNITS_LEDGER",self.validate(bad)["failures"])

    def test_hidden_generator_fields_cannot_enter_the_raw_schema(self):
        bad=copy.deepcopy(self.schema);c=copy.deepcopy(bad["columns"][3]);c["name"]="profile";bad["columns"].append(c)
        with self.assertRaises(ValueError):validate_schema(bad)

    def test_invalid_supply_config_is_rejected(self):
        for key,value in [("lot_size",0),("lot_size",6.5),("quote_ages_days",[-1,2,7,30])]:
            args=copy.deepcopy(self.args);args[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):simulate(*args)

    def test_no_test_target_statistics_and_no_commercial_claim(self):
        report=self.validate(self.bundle)
        self.assertFalse(report["test_target_statistics_computed"])
        self.assertNotIn("TEST",report["statistics"])
        self.assertNotIn("TEST",report["wholesale_volume"])
        self.assertFalse(report["commercial_accuracy_certified"])

    def test_versioned_publication_and_serialized_independent_validation(self):
        import shutil
        with tempfile.TemporaryDirectory(dir=ROOT/"tmp",prefix="expanded-build-test-") as tmp:
            root=Path(tmp)
            paths=["catalog_reference.json","v2/contracts/expanded.v2_1.json","v2/contracts/calibration.v2.json",
                "v2/contracts/dataset_columns.v2_1.json","v2/contracts/dataset_columns.v2.json",
                "v2/contracts/dataset_schema.v2_1.schema.json","v2/contracts/preparation.v2.json",
                "v2/generate_expanded.py","v2/validate_expanded.py","v2/experiment_preparation.py",
                "v2/generate.py","v2/validate_build.py","v2/structure.py",
                "reports/v2/compatibility/compatibility-20261114-01/source_compatibility_matrix.json"]
            for name in paths:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
            destination,result=build("first",root=root)
            expected=sha256_file(destination/"manifest.json")
            report=inspect(destination,root=root,expected_manifest_sha256=expected)
            self.assertEqual(report["status"],"PASSED_EXPANDED_DATA_GATE",report["failures"])
            manifest=json.loads((destination/"manifest.json").read_text(encoding="utf-8"))
            old=json.loads((ROOT/"data/repuestopro_v2/2.0.0/academic-20261114-03/manifest.json").read_text(encoding="utf-8"))
            self.assertNotEqual(manifest["split_design"]["sets"]["TEST"]["row_content_sha256"],old["split_design"]["sets"]["TEST"]["row_content_sha256"])
            self.assertEqual(manifest["dataset_version"],"2.1.0")
            self.assertFalse(manifest["training_authorized"])
            before=(destination/"checksums.sha256").read_bytes()
            with self.assertRaises(FileExistsError):build("first",root=root)
            self.assertEqual((destination/"checksums.sha256").read_bytes(),before)
            with self.assertRaises(ValueError):inspect(destination,root=root,expected_manifest_sha256="0"*64)
            with (destination/"orders.csv").open("a",encoding="utf-8") as f:f.write("corrupted\n")
            with self.assertRaises(ValueError):inspect(destination,root=root,expected_manifest_sha256=expected)


class ExpandedRegistrationTests(unittest.TestCase):
    def test_current_2_1_plan_preserves_legacy_and_restores_variable_age(self):
        prep=json.loads((ROOT/"v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))
        plan=json.loads((ROOT/"v2/contracts/experiments.v2_1.json").read_text(encoding="utf-8"))
        self.assertEqual(prep["active_dataset_version"],"2.1.0")
        self.assertEqual(prep["dataset_build"]["build_id"],"academic-20261114-03")
        self.assertEqual([len(g["columns"]) for g in plan["feature_sets"]],[5,7,11,14,16,17])
        self.assertIn("antiguedad_tipo_cambio_dias",plan["feature_sets"][-1]["columns"])
        self.assertEqual(plan["constant_policy"]["expected_constants_for_this_build"],[])
        self.assertFalse(plan["training_authorized"])
        self.assertEqual(plan["execution_budget"]["actual_fits"],0)

    def test_active_manifest_and_preflight_hashes_are_current_and_training_is_blocked(self):
        prep=json.loads((ROOT/"v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))
        item=prep["dataset_registry"]["2.1.0"]
        manifest=ROOT.parents[1]/item["path"]/"manifest.json"
        self.assertEqual(sha256_file(manifest),item["manifest_sha256"])
        meta=prep["expanded_experiments_preparation"]
        self.assertEqual(sha256_file(ROOT.parents[1]/meta["preflight"]),meta["preflight_sha256"])
        self.assertEqual(sha256_file(ROOT.parents[1]/meta["contract"]),meta["contract_sha256"])
        self.assertFalse(meta["training_authorized"])
        log=ROOT/"reports/v2/2.1.0/expanded-20261115-01/experiments.csv"
        run=prep.get("training_run")
        if run is None:
            self.assertFalse(log.exists())
        else:
            # El preflight permanece histórico. Una ejecución posterior exige evidencia propia.
            self.assertTrue(run["user_authorized"])
            self.assertEqual(run["authorization_scope"],"ONE_RUN_TRAIN_AND_VALIDATION_ONLY")
            self.assertEqual(run["dataset_version"],"2.1.0")
            self.assertEqual(sha256_file(log),run["tracking_sha256"])
            self.assertEqual(sha256_file(ROOT.parents[1]/run["comparison_report"]),run["comparison_sha256"])
            self.assertFalse(run["test_loaded"])
            self.assertFalse(run["future_training_authorized"])
            current=json.loads((ROOT/"v2/contracts/runner.v2_1.json").read_text(encoding="utf-8"))
            self.assertFalse(current["model_training_authorized"])


if __name__=="__main__":unittest.main()
