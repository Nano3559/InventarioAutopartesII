"""Consistencia del catálogo de escenarios. No ejecuta el futuro simulador."""
import copy
import json
import math
from pathlib import Path
import unittest

from v2.structure import ROOT, validate_contract


class V2ScenarioDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prep = json.loads((ROOT / "v2/contracts/preparation.v2.json").read_text(encoding="utf-8"))
        cls.design = cls.prep["scenario_design"]
        cls.cases = {c["scenario_id"]: c for c in cls.design["scenarios"]}
        cls.dictionary = json.loads((ROOT / "v2/contracts/dataset_columns.v2.json").read_text(encoding="utf-8"))

    def test_case_ids_are_unique_and_classes_are_explicit(self):
        cases = self.design["scenarios"]
        self.assertEqual(len(self.cases), len(cases))
        counts = {k:sum(c["case_class"] == k for c in cases) for k in ("NORMAL","ADVERSO","AMBIGUO")}
        self.assertEqual(counts, {"NORMAL":12,"ADVERSO":25,"AMBIGUO":20})
        for c in cases:
            self.assertEqual(c["case_class"], {"N":"NORMAL","A":"ADVERSO","G":"AMBIGUO"}[c["scenario_id"][0]])

    def test_every_case_defines_assumptions_response_and_future_evidence(self):
        for c in self.cases.values():
            for name in ("name","assumptions","expected_response","training_eligibility","timing","future_evidence"):
                self.assertTrue(c[name], (c["scenario_id"], name))

    def test_feature_groups_and_parameter_references_are_resolved(self):
        groups = {c["group"] for c in self.prep["candidate_groups"]} | {"baseline","calendario","auditoria"}
        parameters = self.design["parameter_policy"]["parameters"]
        for c in self.cases.values():
            self.assertTrue(set(c["feature_groups"]).issubset(groups), c["scenario_id"])
            self.assertTrue(set(c["parameter_ids"]).issubset(parameters), c["scenario_id"])

    def test_operational_and_data_risk_families_are_covered(self):
        covered = {f for c in self.cases.values() for f in c["families"]}
        required = {"retail","wholesale","modality","prices","exchange","stock","supplier","reception","transit","calendar","history","target","returns","finance","inspection","voids","duplicates","source","provenance","leakage","split","cold_start","category","regime","interaction","units","economics","outlier","missingness","discontinued","promotion","closed_store","prediction_output"}
        self.assertTrue(required.issubset(covered), required-covered)

    def test_invalid_cases_never_become_training_examples(self):
        for id_ in ("A04","A05","A13","A14","A15","A16","A17","A18","A20"):
            c = self.cases[id_]
            self.assertEqual(c["expected_action"], "REJECT")
            self.assertEqual(c["training_eligibility"], "INVALID_FIXTURE_ONLY")

    def test_cold_start_missing_history_and_open_target_require_review(self):
        for id_ in ("G01","G02","G03","G04"):
            c = self.cases[id_]
            self.assertEqual(c["expected_action"], "REVIEW")
            self.assertEqual(c["training_eligibility"], "EXCLUDED_UNTIL_REVIEW")

    def test_optional_missingness_does_not_invent_zero_history(self):
        for id_ in ("G05","G06","G07","G08","G09","G10","G11","G14"):
            self.assertEqual(self.cases[id_]["expected_action"], "KEEP_WITH_NULL")
        self.assertFalse(self.dictionary["design"]["row_policy"]["missing_month_is_zero"])

    def test_legitimate_adverse_observations_are_not_rejected_for_large_error(self):
        for id_ in ("A01","A02","A03","A06","A07","A08","A10","A11","A12","A19","G15"):
            self.assertEqual(self.cases[id_]["expected_action"], "KEEP")
        self.assertTrue(self.design["selection_policy"]["no_row_dropping_for_metric_gain"])

    def test_future_events_and_unknown_knowledge_are_not_pre_cutoff_information(self):
        self.assertEqual(self.cases["A01"]["timing"], "DURING_TARGET_UNKNOWN_AT_CUTOFF")
        self.assertEqual(self.cases["G09"]["timing"], "POST_CUTOFF_INFORMATION")
        self.assertEqual(self.cases["G13"]["timing"], "UNKNOWN_AVAILABILITY")
        self.assertEqual(self.design["clock_policy"]["timezone"], "America/La_Paz")

    def test_required_combinations_resolve_ids_and_preserve_rejection_priority(self):
        combinations = self.design["mandatory_combinations"]
        self.assertEqual(len({c["id"] for c in combinations}), len(combinations))
        self.assertEqual(len(combinations), 8)
        for c in combinations:
            self.assertTrue(set(c["members"]).issubset(self.cases))
            if any(self.cases[id_]["expected_action"] == "REJECT" for id_ in c["members"]):
                self.assertEqual(c["expected_action"], "REJECT")
        self.assertTrue(next(c for c in combinations if c["id"] == "C06")["context_only"])

    def test_replenishment_context_does_not_add_forecast_features(self):
        for id_ in ("A09","A21","A25","G16","G17","G19","G20"):
            self.assertEqual(self.cases[id_]["training_eligibility"], "CONTEXT_ONLY")
        features = {c["name"] for c in self.dictionary["columns"] if c["role"] == "FEATURE"}
        self.assertEqual(len(features), 17)
        self.assertFalse({"supplier_lead_days","plazo_proveedor","scenario_id","scenario_instance_id","event_at","available_at","parameters_json","latent_demand_units"} & features)

    def test_instance_clock_and_parameters_are_audit_only(self):
        validate_contract(self.dictionary, "dataset_schema")
        table = self.dictionary["design"]["supporting_tables"]["escenarios_metadatos.csv"]
        cols = {c["name"]:c for c in table["columns"]}
        self.assertEqual(table["primary_key"], ["scenario_instance_id"])
        for name in ("scenario_instance_id","event_at","available_at","parameters_json"):
            self.assertEqual(cols[name]["availability_class"], "AUDIT_ONLY")
            self.assertNotEqual(cols[name]["role"], "FEATURE")
        self.assertTrue(cols["event_at"]["nullable"])
        self.assertTrue(cols["available_at"]["nullable"])

    def test_audit_instance_parameters_cannot_be_admitted_as_features(self):
        table = self.dictionary["design"]["supporting_tables"]["escenarios_metadatos.csv"]
        for name in ("scenario_instance_id","event_at","available_at","parameters_json"):
            doc = copy.deepcopy(self.dictionary)
            c = copy.deepcopy(next(c for c in table["columns"] if c["name"] == name))
            c.update(role="FEATURE", availability_class="PRE_CUTOFF", source_kind="SIMULATED")
            doc["columns"].append(c)
            doc["design"]["feature_sets"]["v2_full"].append(name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_contract(doc, "dataset_schema")

    def test_parameter_levels_are_declared_assumptions_not_fitted_estimates(self):
        policy = self.design["parameter_policy"]
        self.assertEqual(policy["status"], "DESIGN_LEVELS_NOT_EMPIRICALLY_CALIBRATED")
        for name in ("probabilities","rotation_shares","elasticity_coefficients"):
            self.assertIsNone(policy[name])
        for p in policy["parameters"].values():
            self.assertTrue(p["unit"] and p["meaning"] and p["levels"])
            self.assertTrue(all(math.isfinite(v) for v in p["levels"] if isinstance(v, (int,float))))
        self.assertFalse(self.design["generator_implemented"])
        self.assertFalse(self.design["dataset_generated"])
        self.assertFalse(self.design["training_performed"])

    def test_actions_match_the_audit_table_contract(self):
        table = self.dictionary["design"]["supporting_tables"]["escenarios_metadatos.csv"]
        action_col = next(c for c in table["columns"] if c["name"] == "expected_action")
        allowed = set(action_col["allowed_values"])
        self.assertTrue(all(c["expected_action"] in allowed for c in self.cases.values()))
        self.assertTrue(all(c["expected_action"] in allowed for c in self.design["mandatory_combinations"]))


if __name__ == "__main__":
    unittest.main()
