"""Ross: reproducibility, sources and independent structural validation. No fit."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from v2.generate_scenarios_v1 import ROOT, CSV_NAMES, dependencies, simulate, write_tables, fulfil, build
from v2.validate_scenarios_v1 import validate


class ScenarioGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipe = dependencies()
        cls.tables, cls.dictionary = simulate(cls.recipe, products_limit=1, recorded_at="2026-11-15T00:00:00-04:00")

    def fixture(self):
        parent = ROOT / "tmp/scenario-tests"
        parent.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(temp.cleanup)
        path = Path(temp.name)
        write_tables(path, self.tables, self.dictionary)
        (path / "schema.json").write_text(json.dumps(self.dictionary), encoding="utf-8")
        (path / "split_manifest.json").write_text(json.dumps({"splits": self.recipe["splits"]}), encoding="utf-8")
        return path

    def mutate(self, path, table, key, value):
        file = path / (CSV_NAMES.get(table, table) + ".csv")
        with file.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            names, rows = reader.fieldnames, list(reader)
        rows[0][key] = value
        with file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=names)
            writer.writeheader()
            writer.writerows(rows)

    def test_source_registry_covers_dictionary_and_preserves_decision_history(self):
        reg = json.loads((ROOT / "v2/contracts/scenario_sources.v1.json").read_text(encoding="utf-8"))
        self.assertEqual({x["source_id"] for x in reg["sources"]}, set(self.dictionary["sources"]))
        for item in reg["external_sources"]:
            self.assertEqual(item["allowed_here"], item["source_id"] != "automotive_spare_parts_demand")
            if item["allowed_here"]:
                self.assertEqual(item["academic_use_status"], "VERIFIED")
        bound = reg["historical_matrix_preserved"]
        self.assertEqual(hashlib.sha256((ROOT / bound["path"]).read_bytes()).hexdigest(), bound["sha256"])

    def test_reproducible_without_reusing_old_build(self):
        again, _ = simulate(self.recipe, products_limit=1, recorded_at="2026-11-15T00:00:00-04:00")
        self.assertEqual(self.tables, again)
        self.assertEqual(self.recipe["dataset_version"], "3.0.0")

    def test_independent_validator_accepts_fixture(self):
        result = validate(self.fixture())
        self.assertTrue(result["valid"], result["errors"][:10])
        self.assertEqual(result["partition_counts"], {"TRAIN": 90, "VALIDATION": 18, "TEST": 18})
        self.assertFalse(result["test_scored"])

    def test_rejects_misaligned_targets(self):
        path = self.fixture()
        self.mutate(path, "supervised_monthly", "target_ventas_mes", "9999")
        self.assertFalse(validate(path)["valid"])

    def test_rejects_future_knowledge(self):
        path = self.fixture()
        self.mutate(path, "exchange_quote_events", "available_at", "2099-01-01T00:00:00-04:00")
        self.assertFalse(validate(path)["valid"])

    def test_rejects_stock_discontinuity(self):
        path = self.fixture()
        self.mutate(path, "daily_ledger", "closing_units", "9999")
        self.assertFalse(validate(path)["valid"])

    def test_rejects_nonconsecutive_history(self):
        path = self.fixture()
        self.mutate(path, "closed_history_monthly", "mes", "2000-01")
        self.assertFalse(validate(path)["valid"])

    def test_zero_stock_delayed_receipt_is_not_a_negative_target(self):
        outcome = fulfil([5] * 3, [2] * 3, 0, 4, 10)
        self.assertEqual(outcome["target"], 0)
        self.assertEqual(outcome["latent"], 21)
        self.assertEqual(outcome["zero_days"], 3)

    def test_price_inelasticity_and_sensitivity_are_explicit(self):
        original = fulfil([10] * 3, [10] * 3, 1000, 4, 0)
        insensitive = fulfil([10] * 3, [10] * 3, 1000, 4, 0, retail_ratio=1.25, wholesale_ratio=1.25, elasticity=0)
        sensitive = fulfil([10] * 3, [10] * 3, 1000, 4, 0, retail_ratio=1.25, wholesale_ratio=1.25, elasticity=-1.2)
        self.assertEqual(original["target"], insensitive["target"])
        self.assertLess(sensitive["target"], original["target"])

    def test_future_reservations_are_not_sold(self):
        out = fulfil([100], [0], 10, 2, 0, future_reserved=4)
        self.assertEqual(out["target"], 6)
        self.assertEqual(out["closing"], 4)

    def test_families_do_not_cross_splits_and_features_exclude_outcomes(self):
        features = {f["name"] for f in self.dictionary["tables"]["supervised_monthly"]["fields"] if f["role"] == "FEATURE"}
        self.assertFalse({"target_ventas_mes", "scenario_id", "scenario_family_id", "realization_id", "assumed_elasticity", "latent_demand_units"} & features)
        self.assertEqual(len(features), 33)
        families = {}
        for row in self.tables["scenario_metadata"]:
            families.setdefault(row["scenario_family_id"], set()).add(row["partition"])
        self.assertTrue(all(len(s) == 1 for s in families.values()))

    def test_refuses_path_traversal_and_existing_build(self):
        with self.assertRaises(ValueError):
            build("../outside")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            fake = Path(tmp)
            (fake / "v2/contracts").mkdir(parents=True)
            recipe = copy.deepcopy(self.recipe)
            recipe["dictionary"] = {"path": "fake", "sha256": "bad"}
            (fake / "v2/contracts/generator.scenarios.v1.json").write_text(json.dumps(recipe))
            with self.assertRaises(ValueError):
                dependencies(fake)

    def test_delivered_build_has_real_audit_metadata_and_current_schema(self):
        path = ROOT / "data/repuestopro_v2/3.0.0/scenarios-20261115-02"
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        schema = json.loads((path / "schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["no_dataset_generated"])
        self.assertEqual(schema["dataset_version"], "3.0.0")
        self.assertEqual(manifest["generator_version"], "scenario-generator-1.0.1")
        with (path / "scenario_context.csv").open(encoding="utf-8", newline="") as f:
            first = next(csv.DictReader(f))
        self.assertEqual(first["recorded_at"], manifest["recorded_at"])
        self.assertNotEqual(first["recorded_at"], first["assumed_as_of"])
        self.assertEqual(hashlib.sha256((ROOT / manifest["generator"]["path"]).read_bytes()).hexdigest(), manifest["generator"]["sha256"])

    def test_published_build_validates_and_cannot_be_overwritten(self):
        path = ROOT / "data/repuestopro_v2/3.0.0/scenarios-20261115-02"
        before = (path / "manifest.json").read_bytes()
        with self.assertRaises(FileExistsError):
            build("scenarios-20261115-02")
        self.assertEqual(before, (path / "manifest.json").read_bytes())
        self.assertTrue(validate(path)["valid"])

    def test_first_candidate_kept_with_exact_source_archive(self):
        old = ROOT / "data/repuestopro_v2/3.0.0/scenarios-20261115-01"
        manifest = json.loads((old / "manifest.json").read_text(encoding="utf-8"))
        for field, archived in [("generator", "versions/generate_scenarios_v1_0_0.py"), ("recipe", "versions/generator.scenarios.v1_0_0.json")]:
            self.assertEqual(hashlib.sha256((ROOT / archived).read_bytes()).hexdigest(), manifest[field]["sha256"])


if __name__ == "__main__":
    unittest.main()
