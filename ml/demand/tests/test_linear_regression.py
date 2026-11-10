"""Pruebas del entrenamiento de LinearRegression (H4 tarea 7).

Cubre las diez áreas obligatorias: entrenamiento solo con TRAIN, orden de
features, transformación ajustada solo con TRAIN, reproducibilidad, métricas,
exclusión de IDs y target, ausencia de fuga, TEST no utilizado, registro de
experimentos e integridad del dataset.
"""
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import ml_pipeline as mp
import train_linear_regression as tlr
from simulator_inputs import (
    FEATURE_NAMES, HERE, InputError, content_sha256, offset_month,
)

DATA = HERE / "data" / "escenarios_v1_1"
MANIFEST = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))

_FRAME = None
_SPLIT = None
_RESULT = None


def official_frame():
    global _FRAME
    if _FRAME is None:
        _FRAME = mp.load_supervised()
    return _FRAME


def official_split():
    global _SPLIT
    if _SPLIT is None:
        _SPLIT = mp.split_temporal(official_frame())
    return _SPLIT


def official_result():
    global _RESULT
    if _RESULT is None:
        _RESULT = tlr.fit_and_evaluate(official_split())
    return _RESULT


def official_train_months():
    start, end = mp.SPLIT_RANGES["train"]
    months = []
    month = start
    while mp.month_index(month) <= mp.month_index(end):
        months.append(month)
        month = offset_month(month, 1)
    return months


def read_registry(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames), list(reader)


class TrainOnlyTests(unittest.TestCase):
    """1. El entrenamiento usa exclusivamente la partición TRAIN."""

    @classmethod
    def setUpClass(cls):
        cls.split = official_split()
        cls.result = official_result()

    def test_model_uses_exactly_train_partition(self):
        self.assertEqual(self.result["n_train"], 2520)
        self.assertEqual(self.result["train_months"],
                         official_train_months())
        self.assertEqual(len(self.result["train_months"]), 15)

    def test_train_and_validation_keys_are_disjoint(self):
        train_keys = set(zip(self.split["train"]["productId"],
                             self.split["train"]["locationId"],
                             self.split["train"]["mes_objetivo"]))
        validation_keys = set(zip(self.split["validation"]["productId"],
                                  self.split["validation"]["locationId"],
                                  self.split["validation"]["mes_objetivo"]))
        self.assertEqual(train_keys & validation_keys, set())
        self.assertEqual(len(train_keys), 2520)
        self.assertEqual(len(validation_keys), 504)

    def test_training_frame_with_months_outside_train_rejected(self):
        altered = dict(self.split)
        altered["train"] = self.split["validation"]
        with self.assertRaisesRegex(InputError, "fuera de TRAIN"):
            tlr.fit_and_evaluate(altered)

    def test_fit_requires_train_and_validation_partitions(self):
        with self.assertRaisesRegex(InputError, "falta la partición"):
            tlr.fit_and_evaluate({"train": self.split["train"]})


class FeatureOrderTests(unittest.TestCase):
    """2. Orden exacto de las cinco features oficiales."""

    @classmethod
    def setUpClass(cls):
        cls.result = official_result()
        cls.split = official_split()

    def test_model_dimension_and_feature_order(self):
        self.assertEqual(int(self.result["model"].n_features_in_), 5)
        self.assertEqual(list(self.result["scaler"].mean_.index),
                         list(FEATURE_NAMES))
        self.assertEqual(list(self.result["scaler"].scale_.index),
                         list(FEATURE_NAMES))

    def test_predict_rejects_reordered_features(self):
        X, _ = mp.build_xy(self.split["validation"])
        with self.assertRaisesRegex(InputError, "orden oficial"):
            tlr.predict(self.result["scaler"], self.result["model"],
                        X[list(reversed(list(X.columns)))])

    def test_predict_rejects_missing_feature(self):
        X, _ = mp.build_xy(self.split["validation"])
        with self.assertRaisesRegex(InputError, "orden oficial"):
            tlr.predict(self.result["scaler"], self.result["model"],
                        X.drop(columns=["mes_cos"]))


class TrainOnlyTransformTests(unittest.TestCase):
    """3. La transformación se ajusta únicamente con TRAIN."""

    @classmethod
    def setUpClass(cls):
        cls.result = official_result()
        cls.split = official_split()
        cls.X_train, _ = mp.build_xy(cls.split["train"])
        cls.X_val, _ = mp.build_xy(cls.split["validation"])

    def test_scaler_statistics_equal_train_statistics(self):
        scaler = self.result["scaler"]
        np.testing.assert_allclose(
            scaler.mean_.to_numpy(), self.X_train.mean().to_numpy(),
            rtol=0, atol=1e-12,
        )
        std = self.X_train.astype("float64").std(axis=0, ddof=0)
        expected_scale = std.where(std != 0, 1.0)
        np.testing.assert_allclose(
            scaler.scale_.to_numpy(), expected_scale.to_numpy(),
            rtol=0, atol=1e-12,
        )

    def test_statistics_differ_from_validation_statistics(self):
        scaler = self.result["scaler"]
        distance = np.abs(
            scaler.mean_.to_numpy() - self.X_val.mean().to_numpy()
        )
        self.assertGreater(float(distance.max()), 1e-6)

    def test_transform_uses_frozen_train_statistics(self):
        scaler = self.result["scaler"]
        before = scaler.mean_.copy()
        manual = (
            self.X_val.astype("float64") - scaler.mean_
        ) / scaler.scale_
        transformed = scaler.transform(self.X_val)
        np.testing.assert_allclose(
            transformed.to_numpy(), manual.to_numpy(),
            rtol=1e-12, atol=1e-12,
        )
        scaler.transform(self.X_val)
        pd.testing.assert_series_equal(scaler.mean_, before)


class ReproducibilityTests(unittest.TestCase):
    """4. Entrenamientos repetidos producen predicciones idénticas."""

    @classmethod
    def setUpClass(cls):
        cls.split = official_split()
        cls.result = official_result()

    def test_two_trainings_are_identical(self):
        first = tlr.fit_and_evaluate(self.split)
        second = tlr.fit_and_evaluate(self.split)
        self.assertEqual(first["coef"], second["coef"])
        self.assertEqual(first["intercept"], second["intercept"])
        self.assertEqual(first["validation"], second["validation"])
        np.testing.assert_array_equal(
            first["predicciones_validation"],
            second["predicciones_validation"],
        )

    def test_same_inputs_give_same_predictions(self):
        X, _ = mp.build_xy(self.split["validation"])
        first = tlr.predict(self.result["scaler"], self.result["model"], X)
        second = tlr.predict(self.result["scaler"], self.result["model"], X)
        np.testing.assert_array_equal(first, second)


class MetricsTests(unittest.TestCase):
    """5. Métricas reales de VALIDATION, calculadas de forma independiente."""

    @classmethod
    def setUpClass(cls):
        cls.result = official_result()

    def test_validation_metrics_recomputed_manually(self):
        observed = self.result["observados_validation"]
        predicted = self.result["predicciones_validation"]
        metrics = self.result["validation"]
        errors = predicted - observed
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(np.square(errors))))
        ss_tot = float(np.sum(np.square(observed - observed.mean())))
        r2 = float(1.0 - float(np.sum(np.square(errors))) / ss_tot)
        self.assertEqual(metrics["n"], 504)
        self.assertEqual(metrics["n_con_prediccion"], 504)
        self.assertEqual(metrics["cobertura"], 1.0)
        self.assertAlmostEqual(metrics["mae"], mae, places=12)
        self.assertAlmostEqual(metrics["rmse"], rmse, places=12)
        self.assertAlmostEqual(metrics["r2"], r2, places=12)

    def test_metrics_match_evaluate_helper(self):
        recomputed = mp.evaluate(self.result["observados_validation"],
                                 self.result["predicciones_validation"])
        self.assertEqual(self.result["validation"], recomputed)

    def test_comparison_against_baseline_shares_same_cases(self):
        comparison = self.result["comparison"]
        self.assertEqual(comparison["linear_regression"]["n"], 504)
        self.assertEqual(comparison["baseline"]["n"], 504)
        self.assertEqual(comparison["linear_regression"]["n"],
                         comparison["baseline"]["n"])
        self.assertLess(comparison["linear_regression"]["mae"],
                        comparison["baseline"]["mae"])

    def test_negative_predictions_are_not_clipped(self):
        metrics = mp.evaluate([0, 0], [-2.0, 2.0])
        self.assertAlmostEqual(metrics["mae"], 2.0, places=12)
        predicted = self.result["predicciones_validation"]
        self.assertEqual(
            self.result["predicciones_negativas"],
            int((predicted < 0).sum()),
        )


class ExclusionTests(unittest.TestCase):
    """6. IDs y target quedan fuera de la matriz de entrenamiento."""

    @classmethod
    def setUpClass(cls):
        cls.result = official_result()
        cls.split = official_split()

    def test_identifiers_and_target_not_in_training_matrix(self):
        forbidden = set(mp.ID_COLUMNS) | {mp.TARGET}
        index = set(self.result["scaler"].mean_.index)
        self.assertEqual(index & forbidden, set())
        self.assertEqual(index, set(FEATURE_NAMES))
        X, y = mp.build_xy(self.split["train"])
        self.assertEqual(list(X.columns), list(FEATURE_NAMES))
        self.assertEqual(y.name, mp.TARGET)

    def test_predict_rejects_frame_with_identifiers(self):
        X, _ = mp.build_xy(self.split["validation"])
        X = X.assign(productId=1)
        with self.assertRaisesRegex(InputError, "orden oficial"):
            tlr.predict(self.result["scaler"], self.result["model"], X)

    def test_artifact_excludes_identifiers(self):
        payload = tlr.build_artifact(self.result, MANIFEST)
        self.assertEqual(payload["feature_names"], list(FEATURE_NAMES))
        self.assertEqual(set(payload["scaler_mean"]) & set(mp.ID_COLUMNS),
                         set())
        self.assertNotIn(mp.TARGET, payload["scaler_mean"])
        self.assertEqual(len(payload["coef"]), 5)
        self.assertEqual(payload["target"], mp.TARGET)


class LeakageTests(unittest.TestCase):
    """7. Ausencia de fuga temporal en el entrenamiento."""

    @classmethod
    def setUpClass(cls):
        cls.split = official_split()
        cls.result = official_result()

    def test_corrupt_train_lag_rejected_before_fit(self):
        train = self.split["train"].copy()
        index = train.index[0]
        train.loc[index, "ventas_mes_anterior"] = (
            int(train.loc[index, "ventas_mes_anterior"]) + 1
        )
        altered = dict(self.split)
        altered["train"] = train
        with self.assertRaisesRegex(InputError, "inconsistencia"):
            tlr.fit_and_evaluate(altered)

    def test_corrupt_validation_target_rejected(self):
        validation = self.split["validation"].copy()
        index = validation.index[0]
        validation.loc[index, mp.TARGET] = (
            int(validation.loc[index, mp.TARGET]) + 1
        )
        altered = dict(self.split)
        altered["validation"] = validation
        with self.assertRaisesRegex(InputError, "inconsistencia"):
            tlr.fit_and_evaluate(altered)

    def test_validation_content_does_not_change_coefficients(self):
        altered = dict(self.split)
        altered["validation"] = self.split["train"]
        other = tlr.fit_and_evaluate(altered)
        self.assertEqual(self.result["coef"], other["coef"])
        self.assertEqual(self.result["intercept"], other["intercept"])


class TestNotUsedTests(unittest.TestCase):
    """8. TEST queda reservado: no entra al entrenamiento ni a la evaluación."""

    @classmethod
    def setUpClass(cls):
        cls.split = official_split()
        cls.result = official_result()

    def test_altered_test_partition_changes_nothing(self):
        altered = dict(self.split)
        garbage = self.split["test"].copy()
        garbage[mp.TARGET] = garbage[mp.TARGET] + 1000
        altered["test"] = garbage
        other = tlr.fit_and_evaluate(altered)
        self.assertEqual(self.result["coef"], other["coef"])
        self.assertEqual(self.result["validation"], other["validation"])
        self.assertEqual(self.result["n_train"], other["n_train"])

    def test_fit_and_evaluate_works_without_test_partition(self):
        without_test = {"train": self.split["train"],
                        "validation": self.split["validation"]}
        other = tlr.fit_and_evaluate(without_test)
        self.assertEqual(self.result["coef"], other["coef"])

    def test_run_experiment_reports_test_reserved(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = Path(temp) / "experiments.csv"
            artifact = Path(temp) / "model.joblib"
            result = tlr.run_experiment(registry_path=registry,
                                        artifact_path=artifact)
            self.assertFalse(result["test"]["metricas_calculadas"])
            self.assertNotIn("mae", result["test"])
            self.assertEqual(result["test"]["filas"], 504)
            _, rows = read_registry(registry)
            for column in ("mae_test", "rmse_test", "r2_test"):
                self.assertEqual(rows[0][column], "")


class RegistryTests(unittest.TestCase):
    """9. Ejecución real agregada a experiments.csv sin sobrescribir."""

    def test_run_records_linear_regression_row(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = Path(temp) / "experiments.csv"
            artifact = Path(temp) / "model.joblib"
            result = tlr.run_experiment(registry_path=registry,
                                        artifact_path=artifact)
            header, rows = read_registry(registry)
        self.assertEqual(tuple(header), mp.EXPERIMENT_COLUMNS)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["model"], tlr.MODEL_NAME)
        self.assertEqual(row["experiment_id"], result["experiment_id"])
        self.assertEqual(row["features"], "|".join(FEATURE_NAMES))
        self.assertEqual(row["target"], mp.TARGET)
        self.assertEqual(row["train_range"], "2025-01..2026-03")
        self.assertEqual(row["validation_range"], "2026-04..2026-06")
        self.assertEqual(row["test_range"], "2026-07..2026-09")
        self.assertEqual(len(row["dataset_hash"]), 64)
        self.assertGreater(float(row["training_seconds"]), 0.0)
        self.assertEqual(float(row["mae_val"]),
                         result["validation"]["mae"])
        self.assertEqual(float(row["rmse_val"]),
                         result["validation"]["rmse"])
        self.assertEqual(float(row["r2_val"]), result["validation"]["r2"])
        for column in ("mae_test", "rmse_test", "r2_test"):
            self.assertEqual(row[column], "")
        parameters = json.loads(row["parameters"])
        self.assertEqual(len(parameters["coef"]), 5)
        self.assertIsInstance(parameters["intercept"], float)
        self.assertTrue(parameters["fit_intercept"])
        self.assertIn("scikit-learn", row["tool_versions"])
        self.assertTrue(row["artifact_path"].endswith(".joblib"))

    def test_run_preserves_existing_registry_rows(self):
        self.assertTrue(mp.EXPERIMENTS_PATH.exists())
        with tempfile.TemporaryDirectory() as temp:
            registry = Path(temp) / "experiments.csv"
            artifact = Path(temp) / "model.joblib"
            shutil.copyfile(mp.EXPERIMENTS_PATH, registry)
            _, before = read_registry(mp.EXPERIMENTS_PATH)
            tlr.run_experiment(registry_path=registry,
                               artifact_path=artifact)
            _, after = read_registry(registry)
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(after[0], before[0])
        self.assertEqual(after[1]["model"], tlr.MODEL_NAME)

    def test_real_registry_contains_both_experiments(self):
        self.assertTrue(mp.EXPERIMENTS_PATH.exists(),
                        "falta experiments.csv con la ejecución real")
        header, rows = read_registry(mp.EXPERIMENTS_PATH)
        self.assertEqual(tuple(header), mp.EXPERIMENT_COLUMNS)
        models = {row["model"] for row in rows}
        self.assertIn(mp.BASELINE_MODEL, models)
        self.assertIn(tlr.MODEL_NAME, models)
        report = json.loads(
            (mp.REPORTS_DIR / "v1_test_evaluation.json").read_text(
                encoding="utf-8")
        )
        v1_id = report["registry"]["experiment_id"]
        for row in rows:
            for column in ("mae_test", "rmse_test", "r2_test"):
                if row["experiment_id"] == v1_id:
                    self.assertNotEqual(row[column], "")
                else:
                    self.assertEqual(row[column], "")


class ArtifactTests(unittest.TestCase):
    """Artefacto reproducible para inferencia posterior."""

    @classmethod
    def setUpClass(cls):
        cls.result = official_result()
        cls.split = official_split()

    def test_artifact_roundtrip_preserves_predictions(self):
        X, _ = mp.build_xy(self.split["validation"])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "model.joblib"
            payload = tlr.build_artifact(self.result, MANIFEST)
            tlr.save_artifact(path, payload)
            loaded = tlr.load_artifact(path)
        from_artifact = tlr.predict_from_artifact(loaded, X)
        in_memory = tlr.predict(self.result["scaler"], self.result["model"], X)
        np.testing.assert_array_equal(from_artifact, in_memory)

    def test_artifact_rejects_unknown_schema(self):
        X, _ = mp.build_xy(self.split["validation"])
        payload = tlr.build_artifact(self.result, MANIFEST)
        payload["schema"] = "otro-esquema"
        with self.assertRaisesRegex(InputError, "esquema"):
            tlr.predict_from_artifact(payload, X)

    def test_artifact_rejects_wrong_feature_contract(self):
        X, _ = mp.build_xy(self.split["validation"])
        payload = tlr.build_artifact(self.result, MANIFEST)
        payload["feature_names"] = list(reversed(FEATURE_NAMES))
        with self.assertRaisesRegex(InputError, "orden oficial"):
            tlr.predict_from_artifact(payload, X)


class IntegrityTests(unittest.TestCase):
    """10. El dataset oficial queda intacto tras entrenar."""

    def test_official_files_unchanged_after_training(self):
        before = {
            name: content_sha256((DATA / name).read_bytes())
            for name in MANIFEST["hashes"]
        }
        before["catalog_reference.json"] = content_sha256(
            (HERE / "catalog_reference.json").read_bytes()
        )
        before["generate_synthetic.py"] = content_sha256(
            (HERE / "generate_synthetic.py").read_bytes()
        )
        with tempfile.TemporaryDirectory() as temp:
            tlr.run_experiment(
                registry_path=Path(temp) / "experiments.csv",
                artifact_path=Path(temp) / "model.joblib",
            )
        after = {
            name: content_sha256((DATA / name).read_bytes())
            for name in MANIFEST["hashes"]
        }
        after["catalog_reference.json"] = content_sha256(
            (HERE / "catalog_reference.json").read_bytes()
        )
        after["generate_synthetic.py"] = content_sha256(
            (HERE / "generate_synthetic.py").read_bytes()
        )
        self.assertEqual(before, after)
        for name, expected in MANIFEST["hashes"].items():
            self.assertEqual(after[name], expected, name)


if __name__ == "__main__":
    unittest.main()
