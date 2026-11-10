"""Integridad de los archivos oficiales: huellas LF/CRLF, rechazos y lectura."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from simulator_inputs import (
    HERE, InputError, content_sha256, load_reference, normalize_eol,
    read_required, verified_bytes,
)

DATA = HERE / "data" / "escenarios_v1_1"


def official_manifest():
    return json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))


def to_crlf(data):
    return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


class HashNormalizationTests(unittest.TestCase):
    def test_lf_and_crlf_have_same_digest(self):
        self.assertEqual(content_sha256(b"a\nb\n"), content_sha256(b"a\r\nb\r\n"))
        self.assertEqual(normalize_eol(b"a\r\nb\r\n"), b"a\nb\n")
        with self.assertRaises(InputError):
            normalize_eol("texto")

    def test_official_files_match_with_lf_and_crlf(self):
        manifest = official_manifest()
        for name, expected in manifest["hashes"].items():
            with self.subTest(name=name):
                raw = (DATA / name).read_bytes()
                self.assertEqual(content_sha256(raw), expected)
                lf = normalize_eol(raw)
                self.assertEqual(content_sha256(lf), expected)
                self.assertEqual(content_sha256(to_crlf(lf)), expected)
        catalog = (HERE / "catalog_reference.json").read_bytes()
        self.assertEqual(content_sha256(catalog), manifest["catalog_snapshot_hash"])
        generator = (HERE / "generate_synthetic.py").read_bytes()
        self.assertEqual(content_sha256(generator), manifest["generator_hash"])

    def test_altered_content_is_rejected(self):
        expected = official_manifest()["hashes"]["base_mensual.csv"]
        raw = normalize_eol((DATA / "base_mensual.csv").read_bytes())
        altered = raw.replace(b"2024-10", b"2024-11", 1)
        self.assertNotEqual(content_sha256(altered), expected)
        self.assertNotEqual(content_sha256(to_crlf(altered)), expected)
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / "base_mensual.csv"
            bad.write_bytes(altered)
            with self.assertRaisesRegex(InputError, "huella"):
                verified_bytes(bad, expected, "base_mensual.csv")

    def test_missing_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "no_existe.csv"
            with self.assertRaisesRegex(InputError, "falta el archivo"):
                read_required(missing, "no_existe.csv")
            with self.assertRaisesRegex(InputError, "falta el archivo"):
                verified_bytes(missing, "0" * 64, "no_existe.csv")


class ReferenceReadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = load_reference()
        cls.manifest = official_manifest()

    def test_load_reference_reads_official_panel(self):
        self.assertEqual(len(self.reference.products), 56)
        self.assertEqual(set(self.reference.stores), {5, 6, 7})
        self.assertEqual(len(self.reference.history), 56 * 3 * 24)
        self.assertEqual(len(self.reference.months), 24)
        self.assertEqual(self.reference.months[0], "2024-10")
        self.assertEqual(self.reference.months[-1], "2026-09")

    def test_rotation_for_reads_verified_metadata(self):
        from ui_panels import rotation_for
        self.assertEqual(rotation_for(1, 5, "2025-01"), "ALTA")
        for product, store, month in [(2, 6, "2026-09"), (56, 7, "2024-11"), (30, 5, "2026-04")]:
            with self.subTest(product=product, month=month):
                self.assertIn(rotation_for(product, store, month), ("ALTA", "MEDIA", "BAJA"))

    def _copy_reference(self, temp, crlf):
        folder = Path(temp)
        sources = [HERE / "catalog_reference.json", DATA / "manifest.json",
                   DATA / "base_mensual.csv", DATA / "escenarios_metadatos.csv"]
        (folder / "data" / "escenarios_v1_1").mkdir(parents=True)
        for source in sources:
            data = source.read_bytes()
            target = folder / "catalog_reference.json" if source.name == "catalog_reference.json" \
                else folder / "data" / "escenarios_v1_1" / source.name
            target.write_bytes(to_crlf(normalize_eol(data)) if crlf else normalize_eol(data))
        return folder

    def test_reference_survives_crlf_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = self._copy_reference(temp, crlf=True)
            reference = load_reference(folder)
            self.assertEqual(len(reference.products), 56)
            self.assertEqual(len(reference.history), 56 * 3 * 24)

    def test_tampered_copy_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = self._copy_reference(temp, crlf=False)
            panel = folder / "data" / "escenarios_v1_1" / "base_mensual.csv"
            panel.write_bytes(normalize_eol(panel.read_bytes()).replace(b"2024-10", b"2024-11", 1))
            with self.assertRaisesRegex(InputError, "huella"):
                load_reference(folder)

    def test_missing_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = self._copy_reference(temp, crlf=False)
            (folder / "data" / "escenarios_v1_1" / "manifest.json").unlink()
            with self.assertRaisesRegex(InputError, "falta el archivo"):
                load_reference(folder)


if __name__ == "__main__":
    unittest.main()
