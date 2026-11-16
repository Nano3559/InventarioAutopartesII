"""Justificación reproducible de parámetros, sin muestrear ventas ni entrenar."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from v2.calibration import build_calibration_contract, derive_reference_parameters

ROOT = Path(__file__).resolve().parents[1]


class CalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        profile = ROOT / "reports/v2/profiling/profile-20261114-01"
        cls.monash = json.loads((profile / "monash_car_parts_profile.json").read_text(encoding="utf-8"))
        cls.uci = json.loads((profile / "uci_online_retail_ii_profile.json").read_text(encoding="utf-8"))
        cls.prep = json.loads((ROOT / "v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))
        cls.config = json.loads((ROOT / "v2/contracts/calibration.v2.json").read_text(encoding="utf-8"))

    def test_reference_statistics_recompute_exactly(self):
        self.assertEqual(derive_reference_parameters(self.monash, self.uci), self.config["reference_statistics"])

    def test_every_scenario_parameter_has_explicit_justification(self):
        declared = self.prep["scenario_design"]["parameter_policy"]["parameters"]
        self.assertEqual(set(declared), set(self.config["parameter_decisions"]))
        for name, value in self.config["parameter_decisions"].items():
            self.assertEqual(value["levels"], declared[name]["levels"])
            self.assertTrue(value["reason"])
            self.assertFalse(value["empirically_estimated"])

    def test_rotation_weights_conserve_population_and_probability(self):
        c = self.config["reference_statistics"]["monash"]["complete_series"]
        self.assertEqual(c["n"], 2509)
        self.assertEqual(c["excluded_incomplete"], 165)
        self.assertEqual(sum(g["count"] for g in c["rotation_groups"]), c["n"])
        self.assertAlmostEqual(sum(g["weight"] for g in c["rotation_groups"]), 1)
        self.assertAlmostEqual(sum(g["weight"]*g["occurrence_probability"] for g in c["rotation_groups"]), c["occurrence_probability"])

    def test_missing_is_not_part_of_zero_denominator(self):
        c = self.config["reference_statistics"]["monash"]["all_observed"]
        self.assertEqual(c["zero_probability"], 97398/130252)
        self.assertNotEqual(c["zero_probability"], 97398/(130252+6122))
        self.assertAlmostEqual(c["zero_probability"]+c["occurrence_probability"], 1)

    def test_positive_mean_and_geometric_match_source_mean(self):
        noise = self.config["parameter_decisions"]["noise"]["positive_size"]
        self.assertAlmostEqual(1/noise["success_probability"], noise["mean"])
        c = self.config["reference_statistics"]["monash"]["all_observed"]
        self.assertAlmostEqual(c["positive_mean"]*c["occurrence_probability"], self.monash["observed_values"]["mean"])

    def test_uci_tails_are_line_quantiles_not_wholesale_labels(self):
        c = self.config["reference_statistics"]["uci"]
        self.assertEqual(c["p95_over_median"], 10)
        self.assertEqual(c["p99_over_median"], 36)
        self.assertEqual(c["cross_sheet_repeat_occurrences"], 22523)
        self.assertIn("etiqueta mayorista inferida por cantidad", c["excluded_transfer"])

    def test_all_reference_hashes_match_frozen_profiles(self):
        for evidence in self.config["input_evidence"]:
            p = ROOT.parents[1] / evidence["profile_path"]
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), evidence["profile_sha256"])
        self.assertEqual(hashlib.sha256((ROOT/"v2/calibration.py").read_bytes()).hexdigest(), self.config["implementation_sha256"])

    def test_active_contract_points_to_exact_configuration(self):
        p = ROOT/"v2/contracts/calibration.v2.json"
        self.assertEqual(self.prep["calibration"]["sha256"], hashlib.sha256(p.read_bytes()).hexdigest())
        self.assertFalse(self.prep["calibration"]["commercial_calibration_certified"])

    def test_builder_does_not_mutate_inputs(self):
        original = copy.deepcopy((self.monash, self.uci, self.prep["scenario_design"]))
        first = build_calibration_contract(*original)
        second = build_calibration_contract(self.monash, self.uci, self.prep["scenario_design"])
        self.assertEqual(original, (self.monash, self.uci, self.prep["scenario_design"]))
        self.assertEqual(first, second)
        json.dumps(first, allow_nan=False)

    def test_empty_or_invalid_monash_cannot_be_calibrated(self):
        for value in (0, -1):
            m = copy.deepcopy(self.monash)
            m["observed_values"]["valid"] = value
            with self.assertRaises(ValueError):
                derive_reference_parameters(m, self.uci)
        m = copy.deepcopy(self.monash)
        m["per_series"][0].update(missing=0, observed=51)
        with self.assertRaises(ValueError):
            derive_reference_parameters(m, self.uci)

    def test_no_missing_uci_quantity_median_fallback(self):
        u = copy.deepcopy(self.uci)
        u["combined"]["positive_quantity"]["median"] = 0
        with self.assertRaises(ValueError):
            derive_reference_parameters(self.monash, u)

    def test_price_fx_and_lead_times_are_not_external_estimates(self):
        decisions = self.config["parameter_decisions"]
        for k in ("price_change", "fx_change", "supplier_lead_days"):
            self.assertEqual(decisions[k]["basis"], "ACADEMIC_ASSUMPTION")
        self.assertEqual(decisions["supplier_lead_days"]["application"], "CONTEXT_ONLY_NOT_FORECAST_FEATURE")
        self.assertIn(0, self.config["simulation_recipe"]["price_elasticity_sensitivity"])

    def test_no_prevalence_is_fabricated_from_forced_coverage(self):
        recipe = self.config["simulation_recipe"]
        self.assertIn("Sin prevalencia estimada", recipe["scenario_frequency_policy"])
        self.assertEqual(recipe["status"], "SPECIFICATION_ONLY_NOT_EXECUTED")
        self.assertFalse(self.config["dataset_created"])
        self.assertFalse(self.config["trained"])


if __name__ == "__main__":
    unittest.main()
