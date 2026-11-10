"""Pruebas de la selección y congelamiento de V1 (H4 tarea 9A).

Cubre selección por MAE de VALIDATION, coherencia del registro, identidad
del artefacto, integridad SHA256, contrato de features, hiperparámetros
congelados, ausencia de reentrenamiento, TEST no utilizado, preservación
del candidato original y dataset intacto.
"""
import csv
import json
import tempfile
import unittest
from pathlib import Path

import ml_pipeline as mp
import select_v1 as sv1
import train_linear_regression as tlr
import train_random_forest as trf
from simulator_inputs import FEATURE_NAMES, HERE, InputError, content_sha256

_FREEZE = None


def official_hashes():
    manifest = mp.official_manifest()
    hashes = {
        name: content_sha256((mp.DATA_DIR / name).read_bytes())
        for name in manifest["hashes"]
    }
    hashes["catalog_reference.json"] = content_sha256(
        (HERE / "catalog_reference.json").read_bytes()
    )
    hashes["generate_synthetic.py"] = content_sha256(
        (HERE / "generate_synthetic.py").read_bytes()
    )
    return hashes


def official_freeze():
    """Estado oficial de la congelación en modo lectura.

    Tras la evaluación final de 9B el registro ya contiene las métricas de
    TEST de V1, por lo que freeze_v1 sobre el registro real se detiene con
    derecho (una re-congelación quedaría prohibida). La lectura del
    manifiesto oficial conserva todas las verificaciones sin rehacer la
    selección; los ejercicios de freeze usan copias saneadas y salidas
    temporales.
    """
    global _FREEZE
    if _FREEZE is None:
        rows = sv1.read_registry()
        winner = sv1.select_winner(rows)
        artifact_path = sv1._resolve_artifact_path(winner["artifact_path"])
        before = {
            "artifact": content_sha256(artifact_path.read_bytes()),
            "registry": content_sha256(mp.EXPERIMENTS_PATH.read_bytes()),
            "hashes": official_hashes(),
        }
        text = sv1.V1_MANIFEST_PATH.read_text(encoding="utf-8")
        document = json.loads(text)
        after = {
            "artifact": content_sha256(artifact_path.read_bytes()),
            "registry": content_sha256(mp.EXPERIMENTS_PATH.read_bytes()),
            "hashes": official_hashes(),
        }
        _FREEZE = {
            "document": document,
            "text": text,
            "before": before,
            "after": after,
            "artifact_path": artifact_path,
            "rows": rows,
            "winner": winner,
        }
    return _FREEZE


def sanitized_registry_copy(destination):
    """Copia del registro con TEST vacío (estado previo a la evaluación)."""
    rows = sv1.read_registry()
    for row in rows:
        for field in ("mae_test", "rmse_test", "r2_test"):
            row[field] = ""
    path = Path(destination) / "experiments.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=mp.EXPERIMENT_COLUMNS,
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


class SelectionByMaeTests(unittest.TestCase):
    """Selección formal por MAE global de VALIDATION."""

    @classmethod
    def setUpClass(cls):
        cls.freeze = official_freeze()
        cls.document = cls.freeze["document"]

    def test_winner_is_lowest_validation_mae(self):
        rows = self.freeze["rows"]
        winner = self.freeze["winner"]
        expected = min(float(row["mae_val"]) for row in rows)
        self.assertEqual(float(winner["mae_val"]), expected)
        self.assertEqual(winner["model"], "RANDOMFOREST")
        self.assertEqual(self.document["selection"]["model"], winner["model"])
        self.assertEqual(self.document["selection"]["experiment_id"],
                         winner["experiment_id"])
        self.assertEqual(self.document["selection"]["mae_val"], expected)

    def test_selection_criterion_is_documented(self):
        criterion = self.document["criterion"]
        self.assertEqual(criterion["principal"], "MAE global en VALIDATION")
        self.assertIn("RMSE", criterion["secundarios"])
        self.assertIn("R²", criterion["secundarios"])
        self.assertIn("menor MAE", criterion["orden_desempate"])
        self.assertFalse(criterion["busquedas_adicionales_tras_validation"])
        self.assertFalse(criterion["reentrenamiento"])
        self.assertFalse(criterion["test_utilizado"])

    def test_select_winner_orders_by_mae_then_rmse_then_r2(self):
        def row(model, mae, rmse, r2):
            return {"model": model, "mae_val": str(mae), "rmse_val": str(rmse),
                    "r2_val": str(r2)}

        ordered = [
            row("A", 5.0, 9.0, 0.1),
            row("B", 4.0, 8.0, 0.2),
            row("C", 4.0, 7.0, 0.0),
            row("D", 4.0, 7.0, 0.5),
        ]
        self.assertEqual(sv1.select_winner(ordered)["model"], "D")
        self.assertEqual(sv1.select_winner(list(reversed(ordered)))["model"],
                         "D")
        without_d = ordered[:3]
        self.assertEqual(sv1.select_winner(without_d)["model"], "C")
        self.assertEqual(sv1.select_winner(list(reversed(without_d)))["model"],
                         "C")
        tie = [row("A", 4.0, 7.0, 0.0), row("B", 4.0, 7.0, 0.9)]
        self.assertEqual(sv1.select_winner(tie)["model"], "B")

    def test_manifest_compares_all_three_models(self):
        comparison = self.document["comparison_validation"]
        self.assertEqual(set(comparison), set(sv1.REQUIRED_MODELS))
        by_model = {row["model"]: row for row in self.freeze["rows"]}
        for model, entry in comparison.items():
            with self.subTest(model=model):
                self.assertEqual(entry["experiment_id"],
                                 by_model[model]["experiment_id"])
                self.assertEqual(entry["mae"],
                                 float(by_model[model]["mae_val"]))
                self.assertEqual(entry["rmse"],
                                 float(by_model[model]["rmse_val"]))
                self.assertEqual(entry["r2"],
                                 float(by_model[model]["r2_val"]))


class RegistryCoherenceTests(unittest.TestCase):
    """Coherencia del registro de experimentos."""

    @classmethod
    def setUpClass(cls):
        cls.freeze = official_freeze()
        cls.document = cls.freeze["document"]

    def test_registry_rows_share_official_contract(self):
        rows = self.freeze["rows"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({row["experiment_id"] for row in rows}), 3)
        manifest = mp.official_manifest()
        for row in rows:
            with self.subTest(model=row["model"]):
                self.assertEqual(row["features"],
                                 "|".join(FEATURE_NAMES))
                self.assertEqual(row["target"], mp.TARGET)
                self.assertEqual(row["train_range"], "2025-01..2026-03")
                self.assertEqual(row["validation_range"], "2026-04..2026-06")
                self.assertEqual(row["test_range"], "2026-07..2026-09")
                self.assertEqual(row["dataset_hash"],
                                 manifest["hashes"]["dataset_supervisado.csv"])
                self.assertEqual(int(row["seed"]), manifest["seed"])

    def test_registry_test_fields_only_on_v1_row(self):
        """Solo la fila de V1 conserva métricas de TEST tras la evaluación."""
        for row in self.freeze["rows"]:
            is_v1 = row["model"] == "RANDOMFOREST"
            for column in ("mae_test", "rmse_test", "r2_test"):
                if is_v1:
                    self.assertNotEqual(row[column], "")
                else:
                    self.assertEqual(row[column], "")

    def test_freeze_refuses_registry_with_test_metrics(self):
        rows = self.freeze["rows"]
        with tempfile.TemporaryDirectory() as temp:
            registry = Path(temp) / "experiments.csv"
            with registry.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=mp.EXPERIMENT_COLUMNS,
                                        lineterminator="\n")
                writer.writeheader()
                for row in rows:
                    copy = dict(row)
                    if copy["model"] == "RANDOMFOREST":
                        copy["mae_test"] = "1.0"
                    writer.writerow(copy)
            with self.assertRaisesRegex(InputError, "TEST debe permanecer"):
                sv1.freeze_v1(manifest_path=Path(temp) / "v1.json",
                              registry_path=registry)

    def test_freeze_does_not_write_the_registry(self):
        before = content_sha256(mp.EXPERIMENTS_PATH.read_bytes())
        with tempfile.TemporaryDirectory() as temp:
            result = sv1.freeze_v1(
                manifest_path=Path(temp) / "v1.json",
                registry_path=sanitized_registry_copy(temp),
            )
        self.assertEqual(result["status"], "SELECTED_FROZEN_NOT_ACTIVE")
        self.assertEqual(content_sha256(mp.EXPERIMENTS_PATH.read_bytes()),
                         before)
        self.assertEqual(self.freeze["before"]["registry"], before)


class ArtifactIdentityTests(unittest.TestCase):
    """Identidad del artefacto seleccionado e integridad SHA256."""

    @classmethod
    def setUpClass(cls):
        cls.freeze = official_freeze()
        cls.document = cls.freeze["document"]

    def test_manifest_hash_matches_artifact_file(self):
        expected = content_sha256(self.freeze["artifact_path"].read_bytes())
        self.assertEqual(self.document["artifact"]["sha256"], expected)
        self.assertEqual(self.freeze["before"]["artifact"], expected)
        self.assertEqual(self.freeze["after"]["artifact"], expected)

    def test_artifact_payload_matches_selection(self):
        payload = tlr.load_artifact(self.freeze["artifact_path"])
        artifact = self.document["artifact"]
        self.assertEqual(payload["model"], self.document["selection"]["model"])
        self.assertEqual(payload["role"], "CANDIDATE")
        self.assertEqual(payload["schema"], artifact["schema"])
        self.assertEqual(payload["feature_names"],
                         self.document["contract"]["features"])
        self.assertEqual(payload["dataset_hash"],
                         self.document["dataset"]["hashes"][
                             "dataset_supervisado.csv"])
        self.assertEqual(self.freeze["artifact_path"].stat().st_size,
                         artifact["bytes"])
        winner_path = self.freeze["winner"]["artifact_path"]
        self.assertEqual(artifact["path"], winner_path)

    def test_all_recorded_hashes_are_sha256(self):
        self.assertRegex(self.document["artifact"]["sha256"],
                         r"^[0-9a-f]{64}$")
        self.assertRegex(
            self.document["dataset"]["hashes"]["dataset_supervisado.csv"],
            r"^[0-9a-f]{64}$",
        )
        self.assertRegex(self.document["dataset"]["catalog_hash"],
                         r"^[0-9a-f]{64}$")
        for name, digest in self.document["dataset"]["hashes"].items():
            with self.subTest(name=name):
                self.assertRegex(digest, r"^[0-9a-f]{64}$")


class FeatureContractTests(unittest.TestCase):
    """Cinco features y orden oficial en manifiesto, arteacto y registro."""

    @classmethod
    def setUpClass(cls):
        cls.freeze = official_freeze()
        cls.document = cls.freeze["document"]

    def test_five_features_and_exact_order_everywhere(self):
        expected = list(FEATURE_NAMES)
        self.assertEqual(self.document["contract"]["features"], expected)
        self.assertTrue(self.document["contract"]["feature_order_exacta"])
        payload = tlr.load_artifact(self.freeze["artifact_path"])
        self.assertEqual(payload["feature_names"], expected)
        row = self.freeze["winner"]
        self.assertEqual(row["features"].split("|"), expected)
        self.assertEqual(self.document["contract"]["target"], mp.TARGET)


class FrozenHyperparameterTests(unittest.TestCase):
    """Hiperparámetros y semilla congelados sin reentrenamiento."""

    @classmethod
    def setUpClass(cls):
        cls.freeze = official_freeze()
        cls.document = cls.freeze["document"]
        cls.payload = tlr.load_artifact(cls.freeze["artifact_path"])

    def test_hyperparameters_match_artifact_and_registry(self):
        frozen = self.document["hyperparameters"]
        self.assertEqual(frozen, self.payload["parameters"])
        row_parameters = json.loads(self.freeze["winner"]["parameters"])
        for key, value in frozen.items():
            with self.subTest(key=key):
                self.assertEqual(row_parameters[key], value)

    def test_hyperparameters_stay_inside_declared_grid(self):
        grid_entry = {
            key: value
            for key, value in self.document["hyperparameters"].items()
            if key in trf.ALLOWED_HYPERPARAMETERS
        }
        self.assertIn(grid_entry, [dict(entry) for entry in trf.GRID])

    def test_seed_is_fixed(self):
        self.assertEqual(self.document["seed"]["random_state"], 42)
        self.assertEqual(self.document["seed"]["dataset_seed"], 42)
        self.assertEqual(self.document["hyperparameters"]["random_state"], 42)
        self.assertEqual(self.document["hyperparameters"]["n_jobs"], 1)

    def test_validation_metrics_recomputed_match_registry_exactly(self):
        metrics = self.document["validation_metrics"]["global"]
        winner = self.freeze["winner"]
        self.assertEqual(metrics["mae"], float(winner["mae_val"]))
        self.assertEqual(metrics["rmse"], float(winner["rmse_val"]))
        self.assertEqual(metrics["r2"], float(winner["r2_val"]))
        self.assertEqual(metrics["n"], 504)
        self.assertEqual(metrics["cobertura"], 1.0)
        self.assertTrue(
            self.document["validation_metrics"]["recomputed_from_artifact"]
        )
        self.assertEqual(
            self.document["validation_metrics"]["predicciones_negativas"], 0
        )


class NoRetrainingTests(unittest.TestCase):
    """Ausencia de reentrenamiento y de activación prematura."""

    @classmethod
    def setUpClass(cls):
        cls.freeze = official_freeze()
        cls.document = cls.freeze["document"]

    def test_selection_source_never_fits(self):
        source = Path(sv1.__file__).read_text(encoding="utf-8")
        for token in (".fit(", "train_candidate", "fit_model",
                      "save_artifact", "joblib.dump", "train_random_forest"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_artifact_bytes_unchanged_by_freeze(self):
        before = content_sha256(self.freeze["artifact_path"].read_bytes())
        with tempfile.TemporaryDirectory() as temp:
            sv1.freeze_v1(manifest_path=Path(temp) / "v1.json",
                          registry_path=sanitized_registry_copy(temp))
        after = content_sha256(self.freeze["artifact_path"].read_bytes())
        self.assertEqual(before, after)
        self.assertEqual(before, self.document["artifact"]["sha256"])

    def test_v1_is_not_active_yet(self):
        self.assertFalse(self.document["active"])
        self.assertEqual(self.document["status"],
                         "SELECTED_FROZEN_NOT_ACTIVE")
        self.assertEqual(self.document["artifact_role"], "CANDIDATE")
        self.assertEqual(self.document["artifact"]["role"], "CANDIDATE")
        self.assertFalse(self.document["artifact"]["retrained"])
        self.assertTrue(self.document["artifact"]["candidate_preserved"])


class TestReservedTests(unittest.TestCase):
    """TEST completamente reservado durante la selección."""

    @classmethod
    def setUpClass(cls):
        cls.freeze = official_freeze()
        cls.document = cls.freeze["document"]

    def test_manifest_records_test_as_reserved(self):
        test = self.document["test"]
        self.assertEqual(
            set(test),
            {"filas", "meses", "metricas_calculadas",
             "predicciones_generadas"},
        )
        self.assertEqual(test["filas"], 504)
        self.assertEqual(test["meses"],
                         ["2026-07", "2026-08", "2026-09"])
        self.assertFalse(test["metricas_calculadas"])
        self.assertFalse(test["predicciones_generadas"])

    def test_manifest_contains_no_test_metrics_anywhere(self):
        for token in ('"mae_test"', '"rmse_test"', '"r2_test"'):
            with self.subTest(token=token):
                self.assertNotIn(token, self.freeze["text"])

    def test_freeze_ignores_changes_exclusive_to_test_rows(self):
        frame = mp.load_supervised()
        mask = frame["mes_objetivo"] >= "2026-07"
        self.assertTrue(bool(mask.any()))
        frame.loc[mask, mp.TARGET] = 999999
        with tempfile.TemporaryDirectory() as temp:
            dataset = Path(temp) / "dataset_supervisado.csv"
            frame.to_csv(dataset, index=False)
            document = sv1.freeze_v1(manifest_path=Path(temp) / "v1.json",
                                     dataset_path=dataset,
                                     registry_path=sanitized_registry_copy(
                                         temp))
        self.assertEqual(
            document["selection"]["mae_val"],
            self.document["selection"]["mae_val"],
        )
        self.assertEqual(document["validation_metrics"]["global"],
                         self.document["validation_metrics"]["global"])

    def test_freeze_detects_changes_in_validation_rows(self):
        frame = mp.load_supervised()
        mask = frame["mes_objetivo"].between("2026-04", "2026-06")
        self.assertTrue(bool(mask.any()))
        frame.loc[mask, mp.TARGET] = frame.loc[mask, mp.TARGET] + 7
        with tempfile.TemporaryDirectory() as temp:
            dataset = Path(temp) / "dataset_supervisado.csv"
            frame.to_csv(dataset, index=False)
            with self.assertRaisesRegex(InputError,
                                        "no coinciden con el registro"):
                sv1.freeze_v1(manifest_path=Path(temp) / "v1.json",
                              dataset_path=dataset,
                              registry_path=sanitized_registry_copy(temp))


class DatasetIntegrityTests(unittest.TestCase):
    """Dataset, catálogo y manifiesto oficial intactos tras congelar."""

    @classmethod
    def setUpClass(cls):
        cls.freeze = official_freeze()

    def test_official_hashes_unchanged_by_freeze(self):
        before = self.freeze["before"]["hashes"]
        after = self.freeze["after"]["hashes"]
        self.assertEqual(before, after)
        manifest = mp.official_manifest()
        for name, digest in manifest["hashes"].items():
            self.assertEqual(after[name], digest, name)
        self.assertEqual(after["catalog_reference.json"],
                         manifest["catalog_snapshot_hash"])

    def test_official_manifest_file_exists_and_is_valid(self):
        path = sv1.V1_MANIFEST_PATH
        self.assertTrue(path.exists(),
                        "falta reports/v1_selection_manifest.json")
        document = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(document["schema"], sv1.SELECTION_SCHEMA)
        self.assertEqual(document["v1_id"], "V1")
        self.assertEqual(document["selection"]["model"], "RANDOMFOREST")
        self.assertEqual(document["selection"]["experiment_id"],
                         self.freeze["winner"]["experiment_id"])
        self.assertEqual(document["artifact"]["sha256"],
                         self.freeze["before"]["artifact"])
        self.assertFalse(document["active"])


if __name__ == "__main__":
    unittest.main()
