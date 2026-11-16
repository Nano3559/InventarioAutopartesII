"""Pruebas de arquitectura V2. No importan motores, generadores o entrenadores."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from v2.structure import ROOT, ensure_structure, new_build_directory, sha256_file, validate_contract, write_new_json
from v2.register_sources import register

RUN = ROOT / "tmp/structure-20261111-01"


class V2StructureTests(unittest.TestCase):
    def fixture(self):
        RUN.mkdir(parents=True, exist_ok=True)
        tmp = tempfile.TemporaryDirectory(dir=RUN, prefix="test-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        ensure_structure(root)
        return root

    def test_protected_v1_files_have_exact_original_bytes(self):
        baseline = json.loads((ROOT / "v2/contracts/protected_files.sha256.json").read_text())
        project = ROOT.parents[1]
        self.assertGreater(len(baseline), 30)
        for relative, expected in baseline.items():
            with self.subTest(path=relative):
                self.assertEqual(sha256_file(project / relative), expected)

    def test_sources_and_tmp_are_outside_data(self):
        root = self.fixture()
        for name in ("sources/external_raw", "sources/external_curated", "sources/manifests", "tmp"):
            self.assertFalse((root / name).is_relative_to(root / "data"))
        self.assertFalse((root / "data/external_raw").exists())
        self.assertFalse((root / "data/external_curated").exists())

    def test_all_real_manifests_match_every_raw_file_byte_hash(self):
        registered = set()
        manifests = list((ROOT / "sources/manifests").glob("*/*.json"))
        self.assertGreaterEqual(len(manifests), 5)
        for path in manifests:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            validate_contract(manifest, "source_manifest")
            folder = ROOT / manifest["raw_root"]
            for item in manifest["files"]:
                original = folder / item["relative_path"]
                registered.add(original)
                self.assertEqual(original.stat().st_size, item["file_size_bytes"])
                self.assertEqual(sha256_file(original), item["sha256"])
        self.assertEqual(registered, {p for p in (ROOT / "sources/external_raw").rglob("*") if p.is_file()})

    def test_registration_preserves_raw_and_unknown_metadata(self):
        root = self.fixture()
        folder = root / "sources/external_raw/unknown_source"
        folder.mkdir()
        raw = folder / "original.bin"
        raw.write_bytes(b"original\r\nbytes\x00")
        before = sha256_file(raw)
        registration = register("run1", root)
        manifest_path = root / registration[0]["manifest"]
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        validate_contract(document, "source_manifest")
        for field in ("source_url", "provider", "obtained_at", "license", "commercial_use_allowed", "currency", "units"):
            self.assertIsNone(document[field])
        self.assertEqual(document["completeness"], "UNKNOWN")
        self.assertEqual(document["processing_status"], "PENDING_SOURCE_REVIEW")
        self.assertEqual(sha256_file(raw), before)
        self.assertFalse(any((root / "sources/external_curated").iterdir()))
        manifest_before = sha256_file(manifest_path)
        register("run2", root)
        self.assertEqual(sha256_file(manifest_path), manifest_before)
        self.assertEqual(sha256_file(raw), before)

    def test_writes_cannot_target_raw_or_v1_reports_or_models(self):
        root = self.fixture()
        for path in ("sources/external_raw/new.json", "reports/experiments.csv", "reports/v1_test_evaluation.json", "models/random_forest_candidate.joblib", "data/escenarios_v1/base_mensual.csv"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                write_new_json(root / path, {}, root=root)
            self.assertFalse((root / path).exists())

    def test_manifest_and_temporary_writes_never_overwrite(self):
        root = self.fixture()
        path = root / "tmp/run1/result.json"
        write_new_json(path, {"one": 1}, root=root)
        with self.assertRaises(FileExistsError):
            write_new_json(path, {"two": 2}, root=root)
        self.assertEqual(json.loads(path.read_text()), {"one": 1})

    def test_build_id_prevents_overwrite_and_allows_multiple_builds(self):
        root = self.fixture()
        first = new_build_directory("2.0.0", "build-1", root)
        with self.assertRaises(FileExistsError):
            new_build_directory("2.0.0", "build-1", root)
        second = new_build_directory("2.0.0", "build-2", root)
        self.assertNotEqual(first, second)
        self.assertEqual(list(first.iterdir()), [])
        self.assertEqual(list(second.iterdir()), [])
        with self.assertRaises(ValueError):
            new_build_directory("2.0.0", "../escape", root)

    def test_bad_hash_and_approval_are_rejected(self):
        path = next((ROOT / "sources/manifests").glob("*/*.json"))
        document = json.loads(path.read_text(encoding="utf-8"))
        bad = copy.deepcopy(document)
        bad["files"][0]["sha256"] = "a" * 64
        with self.assertRaises(ValueError):
            validate_contract(bad, "source_manifest")
        bad = copy.deepcopy(document)
        bad["processing_status"] = "APPROVED_FOR_PROFILING"
        with self.assertRaises(ValueError):
            validate_contract(bad, "source_manifest")

    def test_dataset_reference_is_draft_not_v2_approval(self):
        ref = json.loads((ROOT / "v2/contracts/dataset_columns.reference.json").read_text())
        validate_contract(ref, "dataset_schema")
        self.assertEqual(len(ref["columns"]), 9)
        self.assertTrue(all(c["approval_status"] == "V1_REFERENCE" for c in ref["columns"]))
        ref["status"] = "APPROVED"
        with self.assertRaises(Exception):
            validate_contract(ref, "dataset_schema")

    def test_curated_contract_requires_script_parameters_and_original_hashes(self):
        with self.assertRaises(Exception):
            validate_contract({"schema_version": "curated-manifest-1"}, "curated_manifest")
