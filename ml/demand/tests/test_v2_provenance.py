"""Contrato de revisión de fuentes. No perfila ni carga datos o modelos."""
import copy
import json
from pathlib import Path
import unittest

from v2.structure import ROOT, inventory_digest, validate_contract


class ProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = json.loads((ROOT / "reports/v2/source_provenance_matrix.json").read_text(encoding="utf-8"))
        cls.manifests = [json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "sources/manifests").glob("*/*.json")]

    def test_original_manifests_remain_compatible(self):
        schema = json.loads((ROOT / "v2/contracts/source_manifest.schema.json").read_text(encoding="utf-8"))
        for doc in self.manifests:
            legacy = {key: doc[key] for key in schema["required"]}
            legacy["processing_status"] = "PENDING_SOURCE_REVIEW"
            validate_contract(legacy, "source_manifest")

    def test_reviewed_manifests_distinguish_user_confirmation_from_unknown_acquisition(self):
        self.assertEqual(len(self.manifests), 5)
        for doc in self.manifests:
            validate_contract(doc,"source_manifest")
            self.assertTrue(doc["evidence_urls"])
            self.assertIsNone(doc["obtained_at"])
            if doc["source_id"] in ("m5_walmart", "corporacion_favorita"):
                self.assertEqual(doc["acquisition_verification_status"], "PARTIALLY_VERIFIED")
                competition = "m5-forecasting-accuracy" if doc["source_id"] == "m5_walmart" else "favorita-grocery-sales-forecasting"
                self.assertEqual(doc["obtained_from_url"], f"https://www.kaggle.com/competitions/{competition}/data")
                self.assertTrue(any(e["scope"].startswith("USER_ATTESTATION_AND_") for e in doc["evidence"]))
            else:
                self.assertIsNone(doc["obtained_from_url"])
                self.assertEqual(doc["acquisition_verification_status"], "UNKNOWN")

    def test_current_academic_eligibility_preserves_historical_scope(self):
        approved = {d["source_id"] for d in self.manifests if d["processing_status"] == "APPROVED_FOR_PROFILING"}
        self.assertEqual(approved, {"monash_car_parts", "uci_online_retail_ii", "m5_walmart", "corporacion_favorita"})
        self.assertEqual(set(self.matrix["approved_academic_profiling"]), {"monash_car_parts", "uci_online_retail_ii"})
        for doc in self.manifests:
            if doc["source_id"] in approved:
                bad = copy.deepcopy(doc)
                bad["license_status"] = "UNKNOWN"
                with self.assertRaises(ValueError):
                    validate_contract(bad, "source_manifest")
                bad["license_status"] = "VERIFIED"
                bad["evidence_urls"] = []
                with self.assertRaises(ValueError):
                    validate_contract(bad, "source_manifest")

    def test_m5_permission_is_academic_only_and_does_not_claim_execution(self):
        doc = next(d for d in self.manifests if d["source_id"] == "m5_walmart")
        evidence = next(e for e in doc["evidence"] if e["scope"] == "USER_ATTESTATION_AND_SUPPLIED_OFFICIAL_RULES")
        review = json.loads((ROOT / evidence["path"]).read_text(encoding="utf-8"))["m5"]
        self.assertEqual(review["authorized_user_scope"], ["ROSS"])
        self.assertTrue(review["rules_accepted"])
        self.assertTrue(review["downloaded_from_own_account"])
        self.assertFalse(review["execution_authorized_in_this_task"])
        self.assertIsNone(review["actual_download_date"])
        self.assertFalse(doc["commercial_use_allowed"])
        self.assertEqual(doc["commercial_use_status"], "RESTRICTED")
        self.assertEqual(doc["redistribution_status"], "RESTRICTED")

    def test_snapshot_identity_and_raw_metadata_are_unchanged(self):
        for doc in self.manifests:
            old = next(row for row in self.matrix["sources"] if row["source_id"] == doc["source_id"])
            for key in ("sha256", "inventory_sha256", "snapshot_id"):
                self.assertEqual(doc[key], old[key])
            self.assertEqual(doc["snapshot_id"], "sha256-" + inventory_digest(doc["files"])[:24])
            if doc["file_count"] == 1:
                self.assertEqual(doc["sha256"], doc["files"][0]["sha256"])
                self.assertNotEqual(doc["sha256"], doc["inventory_sha256"])

    def test_favorita_confirmation_does_not_enable_commercial_use_or_automotive(self):
        doc = next(d for d in self.manifests if d["source_id"] == "corporacion_favorita")
        evidence = next(e for e in doc["evidence"] if e["scope"] == "USER_ATTESTATION_AND_OFFICIAL_RULES")
        review = json.loads((ROOT / evidence["path"]).read_text(encoding="utf-8"))
        access = review["favorita"]
        self.assertEqual(access["competition_year"], 2017)
        self.assertEqual(access["authorized_user_scope"], ["ROSS"])
        self.assertTrue(access["rules_accepted"])
        self.assertTrue(access["downloaded_from_own_account"])
        self.assertFalse(access["execution_authorized_in_this_task"])
        self.assertIsNone(access["actual_download_date"])
        self.assertFalse(doc["commercial_use_allowed"])
        self.assertEqual(doc["redistribution_status"], "RESTRICTED")
        auto = next(d for d in self.manifests if d["source_id"] == "automotive_spare_parts_demand")
        self.assertEqual(auto["profiling_decision"], "BLOCKED_LICENSE")
        self.assertEqual(review["automotive"]["decision"], "BLOCKED_LICENSE")

    def test_unknown_permissions_do_not_become_commercial_permission(self):
        for doc in self.manifests:
            if doc["commercial_use_status"] == "UNKNOWN":
                self.assertIsNone(doc["commercial_use_allowed"])
        auto = next(d for d in self.manifests if d["source_id"] == "automotive_spare_parts_demand")
        self.assertIsNone(auto["license"])
        pasta = next(d for d in auto["subdatasets"] if d["name"] == "pasta")
        self.assertEqual(pasta["license"], "CC BY-NC 3.0")
