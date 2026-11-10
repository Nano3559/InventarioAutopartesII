"""Pruebas del entrenamiento de RandomForest (H4 tarea 8).

Cubre las doce áreas obligatorias: entrenamiento solo con TRAIN,
reproducibilidad con random_state=42, validación temporal interna sin fuga,
hiperparámetros acotados, cinco features exactas, exclusión de IDs y target,
TEST reservado, métricas correctas, comparación justa, artefacto persistido,
integridad del dataset y registro de experimentos.
"""
import csv
import inspect
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

import ml_pipeline as mp
import train_linear_regression as tlr
import train_random_forest as trf
from simulator_inputs import FEATURE_NAMES, HERE, InputError, content_sha256

DATA = HERE / "data" / "escenarios_v1_1"
MANIFEST = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))

_FRAME = None
_SPLIT = None
_CANDIDATE = None
_SHARED_RUN = None


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


def official_candidate():
    global _CANDIDATE
    if _CANDIDATE is None:
        _CANDIDATE = trf.train_candidate(official_split()["train"])
    return _CANDIDATE


def read_registry(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames), list(reader)


def official_hashes():
    hashes = {
        name: content_sha256((DATA / name).read_bytes())
        for name in MANIFEST["hashes"]
    }
    hashes["catalog_reference.json"] = content_sha256(
        (HERE / "catalog_reference.json").read_bytes()
    )
    hashes["generate_synthetic.py"] = content_sha256(
        (HERE / "generate_synthetic.py").read_bytes()
    )
    return hashes


def shared_run():
    """Una única ejecución real sobre copia del registro, con hashes."""
    global _SHARED_RUN
    if _SHARED_RUN is None:
        lr_before = content_sha256(trf.LR_ARTIFACT_PATH.read_bytes())
        hashes_before = official_hashes()
        registry_rows_before = read_registry(mp.EXPERIMENTS_PATH)[1]
        with tempfile.TemporaryDirectory() as temp:
            registry = Path(temp) / "experiments.csv"
            shutil.copyfile(mp.EXPERIMENTS_PATH, registry)
            artifact = Path(temp) / "rf.joblib"
            result = trf.run_experiment(registry_path=registry,
                                        artifact_path=artifact)
            rows = read_registry(registry)[1]
        _SHARED_RUN = {
            "result": result,
            "rows": rows,
            "registry_rows_before": registry_rows_before,
            "hashes_before": hashes_before,
            "hashes_after": official_hashes(),
            "lr_before": lr_before,
            "lr_after": content_sha256(trf.LR_ARTIFACT_PATH.read_bytes()),
        }
    return _SHARED_RUN


class TrainOnlyTests(unittest.TestCase):
    """1. El entrenamiento usa exclusivamente la partición TRAIN."""

    @classmethod
    def setUpClass(cls):
        cls.split = official_split()
        cls.candidate = official_candidate()

    def test_candidate_uses_exactly_train_partition(self):
        self.assertEqual(self.candidate["n_train"], 2520)
        self.assertEqual(len(self.candidate["train_months"]), 15)
        self.assertEqual(self.candidate["train_months"][0], "2025-01")
        self.assertEqual(self.candidate["train_months"][-1], "2026-03")

    def test_train_and_validation_keys_are_disjoint(self):
        train_keys = set(zip(self.split["train"]["productId"],
                             self.split["train"]["locationId"],
                             self.split["train"]["mes_objetivo"]))
        validation_keys = set(zip(self.split["validation"]["productId"],
                                  self.split["validation"]["locationId"],
                                  self.split["validation"]["mes_objetivo"]))
        self.assertEqual(train_keys & validation_keys, set())
        self.assertEqual(len(train_keys), 2520)

    def test_training_on_test_partition_rejected(self):
        with self.assertRaisesRegex(InputError, "fuera de TRAIN"):
            trf.train_candidate(self.split["test"])

    def test_train_candidate_only_receives_train(self):
        parameters = inspect.signature(trf.train_candidate).parameters
        self.assertEqual(list(parameters), ["train_frame"])


class InternalValidationTests(unittest.TestCase):
    """2. Validación temporal interna dentro de TRAIN, sin fuga."""

    @classmethod
    def setUpClass(cls):
        cls.split = official_split()
        cls.candidate = official_candidate()
        cls.adjust, cls.evaluation = trf.internal_temporal_split(
            cls.split["train"]
        )

    def test_internal_split_is_temporal_disjoint_and_sized(self):
        self.assertEqual(len(self.adjust), 2016)
        self.assertEqual(len(self.evaluation), 504)
        self.assertEqual(sorted(set(self.adjust["mes_objetivo"])),
                         [f"2025-{month:02d}" for month in range(1, 13)])
        self.assertEqual(sorted(set(self.evaluation["mes_objetivo"])),
                         ["2026-01", "2026-02", "2026-03"])
        latest_adjust = mp.month_index(max(self.adjust["mes_objetivo"]))
        earliest_eval = mp.month_index(min(self.evaluation["mes_objetivo"]))
        self.assertLess(latest_adjust, earliest_eval)

    def test_internal_parts_are_train_subsets_and_leak_free(self):
        train_keys = set(zip(self.split["train"]["productId"],
                             self.split["train"]["locationId"],
                             self.split["train"]["mes_objetivo"]))
        for part in (self.adjust, self.evaluation):
            keys = set(zip(part["productId"], part["locationId"],
                           part["mes_objetivo"]))
            with self.subTest(rows=len(part)):
                self.assertTrue(keys <= train_keys)
                counts = mp.assert_no_leakage(part)
                self.assertEqual(sum(counts.values()), 0)

    def test_internal_split_rejects_non_train_frames(self):
        with self.assertRaisesRegex(InputError, "fuera de TRAIN"):
            trf.internal_temporal_split(self.split["validation"])

    def test_grid_metrics_come_from_internal_eval(self):
        self.assertEqual(len(self.candidate["grid_results"]), 16)
        for entry in self.candidate["grid_results"]:
            metrics = entry["internal_validation"]
            with self.subTest(parameters=entry["parameters"]):
                self.assertEqual(metrics["n"], 504)
                self.assertEqual(metrics["cobertura"], 1.0)
                self.assertIsNotNone(metrics["mae"])
        self.assertEqual(self.candidate["internal_eval_months"],
                         ["2026-01", "2026-02", "2026-03"])
        self.assertEqual(self.candidate["internal_adjust_rows"], 2016)


class GridTests(unittest.TestCase):
    """3. Hiperparámetros acotados y selección explícita."""

    @classmethod
    def setUpClass(cls):
        cls.candidate = official_candidate()

    def test_grid_size_and_hyperparameter_domain(self):
        self.assertEqual(len(trf.GRID), 16)
        self.assertEqual(
            set(trf.ALLOWED_HYPERPARAMETERS),
            {"n_estimators", "max_depth", "min_samples_leaf", "max_features"},
        )
        for parameters in trf.GRID:
            with self.subTest(parameters=parameters):
                self.assertEqual(set(parameters),
                                 set(trf.ALLOWED_HYPERPARAMETERS))
                self.assertIn(parameters["n_estimators"], (100, 200))
                self.assertIn(parameters["max_depth"], (None, 8))
                self.assertIn(parameters["min_samples_leaf"], (1, 3))
                self.assertIn(parameters["max_features"], ("sqrt", 1.0))

    def test_selected_configuration_belongs_to_grid(self):
        self.assertIn(self.candidate["best_parameters"],
                      [dict(entry) for entry in trf.GRID])

    def test_grid_results_follow_grid_order(self):
        evaluated = [entry["parameters"]
                     for entry in self.candidate["grid_results"]]
        self.assertEqual(evaluated, [dict(entry) for entry in trf.GRID])

    def test_fit_model_rejects_unknown_hyperparameter(self):
        with self.assertRaisesRegex(InputError, "HIPERPARÁMETRO"):
            trf.fit_model({"n_estimators": 10, "bootstrap": True}, None, None)


class FeatureContractTests(unittest.TestCase):
    """4. Cinco features exactas y exclusión de IDs y target."""

    @classmethod
    def setUpClass(cls):
        cls.split = official_split()
        cls.candidate = official_candidate()

    def test_model_uses_exact_five_features(self):
        model = self.candidate["model"]
        self.assertEqual(int(model.n_features_in_), 5)
        self.assertEqual(list(model.feature_names_in_), list(FEATURE_NAMES))
        X, y = mp.build_xy(self.split["train"])
        self.assertEqual(list(X.columns), list(FEATURE_NAMES))
        self.assertEqual(y.name, mp.TARGET)

    def test_predict_rejects_reordered_features(self):
        X, _ = mp.build_xy(self.split["validation"])
        with self.assertRaisesRegex(InputError, "orden oficial"):
            trf.predict(self.candidate["model"],
                        X[list(reversed(list(X.columns)))])

    def test_predict_rejects_missing_feature(self):
        X, _ = mp.build_xy(self.split["validation"])
        with self.assertRaisesRegex(InputError, "orden oficial"):
            trf.predict(self.candidate["model"], X.drop(columns=["mes_cos"]))

    def test_predict_rejects_extra_identifier(self):
        X, _ = mp.build_xy(self.split["validation"])
        with self.assertRaisesRegex(InputError, "orden oficial"):
            trf.predict(self.candidate["model"], X.assign(productId=1))

    def test_artifact_excludes_identifiers(self):
        payload = trf.build_artifact(self.candidate, MANIFEST)
        forbidden = set(mp.ID_COLUMNS) | {mp.TARGET}
        self.assertEqual(payload["feature_names"], list(FEATURE_NAMES))
        self.assertEqual(set(payload["feature_importances"])
                         & forbidden, set())
        self.assertEqual(set(payload["feature_importances"]),
                         set(FEATURE_NAMES))
        self.assertEqual(payload["target"], mp.TARGET)


class ReproducibilityTests(unittest.TestCase):
    """5. Reproducibilidad con random_state=42."""

    @classmethod
    def setUpClass(cls):
        cls.split = official_split()
        cls.candidate = official_candidate()

    def test_random_state_is_fixed(self):
        self.assertEqual(trf.RANDOM_STATE, 42)
        self.assertEqual(int(self.candidate["model"].random_state), 42)

    def test_refits_are_deterministic(self):
        X_train, y_train = mp.build_xy(self.split["train"])
        X_val, _ = mp.build_xy(self.split["validation"])
        first = trf.fit_model(self.candidate["best_parameters"],
                              X_train, y_train)
        second = trf.fit_model(self.candidate["best_parameters"],
                               X_train, y_train)
        np.testing.assert_array_equal(
            trf.predict(first, X_val), trf.predict(second, X_val)
        )
        np.testing.assert_array_equal(
            trf.predict(first, X_val),
            trf.predict(self.candidate["model"], X_val),
        )
        np.testing.assert_array_equal(first.feature_importances_,
                                      second.feature_importances_)


class MetricsTests(unittest.TestCase):
    """6. Métricas reales de VALIDATION calculadas de forma independiente."""

    @classmethod
    def setUpClass(cls):
        cls.split = official_split()
        cls.evaluation = trf.evaluate_validation(
            official_candidate()["model"], official_split()["validation"]
        )

    def test_validation_metrics_recomputed_manually(self):
        observed = self.evaluation["observados"]
        predicted = self.evaluation["predicciones"]
        metrics = self.evaluation["metrics"]
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
        recomputed = mp.evaluate(self.evaluation["observados"],
                                 self.evaluation["predicciones"])
        self.assertEqual(self.evaluation["metrics"], recomputed)

    def test_negative_count_is_consistent_without_clipping(self):
        predicted = self.evaluation["predicciones"]
        self.assertEqual(self.evaluation["negativas"],
                         int((predicted < 0).sum()))
        metrics = mp.evaluate([0, 0], [-2.0, 2.0])
        self.assertAlmostEqual(metrics["mae"], 2.0, places=12)


class ComparisonTests(unittest.TestCase):
    """7. Comparación justa de los tres modelos sobre los mismos 504 casos."""

    @classmethod
    def setUpClass(cls):
        cls.shared = shared_run()
        cls.comparison = cls.shared["result"]["comparison"]

    def test_three_models_share_same_504_cases(self):
        for name in ("baseline", "linear_regression", "random_forest"):
            with self.subTest(model=name):
                self.assertEqual(self.comparison[name]["n"], 504)
                self.assertEqual(self.comparison[name]["cobertura"], 1.0)

    def test_baseline_and_lr_match_registered_experiments(self):
        _, rows = read_registry(mp.EXPERIMENTS_PATH)
        registered = {row["model"]: row for row in rows}
        for key, model in (("mae_val", "BASELINE_LAG1"),
                           ("rmse_val", "BASELINE_LAG1"),
                           ("r2_val", "BASELINE_LAG1")):
            metric = key.replace("_val", "")
            self.assertEqual(
                self.comparison["baseline"][metric],
                float(registered[model][key]),
            )
        for key in ("mae_val", "rmse_val", "r2_val"):
            metric = key.replace("_val", "")
            self.assertEqual(
                self.comparison["linear_regression"][metric],
                float(registered["LINEARREGRESSION"][key]),
            )

    def test_rf_metrics_match_its_registered_row(self):
        row = self.shared["rows"][-1]
        self.assertEqual(row["model"], trf.MODEL_NAME)
        for key in ("mae_val", "rmse_val", "r2_val"):
            metric = key.replace("_val", "")
            self.assertEqual(
                self.comparison["random_forest"][metric],
                float(row[key]),
            )


class TestReservedTests(unittest.TestCase):
    """8. TEST completamente reservado."""

    @classmethod
    def setUpClass(cls):
        cls.shared = shared_run()

    def test_run_reports_test_reserved(self):
        test = self.shared["result"]["test"]
        self.assertFalse(test["metricas_calculadas"])
        self.assertNotIn("mae", test)
        self.assertEqual(test["filas"], 504)
        self.assertEqual(test["meses"], ["2026-07", "2026-08", "2026-09"])

    def test_registry_test_fields_only_on_v1_row(self):
        report = json.loads(
            (mp.REPORTS_DIR / "v1_test_evaluation.json").read_text(
                encoding="utf-8")
        )
        v1_id = report["registry"]["experiment_id"]
        keys = {"mae_test": "mae", "rmse_test": "rmse", "r2_test": "r2"}
        for source in (self.shared["rows"],
                       read_registry(mp.EXPERIMENTS_PATH)[1]):
            for row in source:
                for column in ("mae_test", "rmse_test", "r2_test"):
                    if row["experiment_id"] == v1_id:
                        self.assertNotEqual(row[column], "")
                        self.assertEqual(float(row[column]),
                                         report["metrics"][keys[column]])
                    else:
                        self.assertEqual(row[column], "")


class ArtifactTests(unittest.TestCase):
    """9. Artefacto persistido, recuperable y sin pisar el de LR."""

    @classmethod
    def setUpClass(cls):
        cls.split = official_split()
        cls.candidate = official_candidate()
        cls.shared = shared_run()

    def test_artifact_roundtrip_preserves_predictions(self):
        X, _ = mp.build_xy(self.split["validation"])
        payload = trf.build_artifact(self.candidate, MANIFEST)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rf.joblib"
            tlr.save_artifact(path, payload)
            loaded = tlr.load_artifact(path)
        from_artifact = trf.predict_from_artifact(loaded, X)
        in_memory = trf.predict(self.candidate["model"], X)
        np.testing.assert_array_equal(from_artifact, in_memory)

    def test_artifact_identifies_candidate_without_scaler(self):
        payload = trf.build_artifact(self.candidate, MANIFEST)
        self.assertEqual(payload["schema"], trf.ARTIFACT_SCHEMA)
        self.assertEqual(payload["model"], trf.MODEL_NAME)
        self.assertEqual(payload["role"], "CANDIDATE")
        self.assertIsNone(payload["scaler"])
        self.assertIn("sin estandarización", payload["preprocessing"])
        self.assertEqual(len(payload["hyperparameter_search"]["grid"]), 16)
        self.assertIn("random_state", payload["parameters"])
        self.assertEqual(payload["trained_through"], "2026-03")

    def test_linear_regression_artifact_not_overwritten(self):
        self.assertEqual(self.shared["lr_before"], self.shared["lr_after"])
        self.assertEqual(
            self.shared["lr_after"],
            content_sha256(trf.LR_ARTIFACT_PATH.read_bytes()),
        )

    def test_artifact_rejects_wrong_schema_and_features(self):
        X, _ = mp.build_xy(self.split["validation"])
        payload = trf.build_artifact(self.candidate, MANIFEST)
        payload["schema"] = "otro-esquema"
        with self.assertRaisesRegex(InputError, "esquema"):
            trf.predict_from_artifact(payload, X)
        payload = trf.build_artifact(self.candidate, MANIFEST)
        payload["feature_names"] = list(reversed(FEATURE_NAMES))
        with self.assertRaisesRegex(InputError, "orden oficial"):
            trf.predict_from_artifact(payload, X)


class IntegrityTests(unittest.TestCase):
    """10. El dataset oficial queda intacto tras entrenar."""

    @classmethod
    def setUpClass(cls):
        cls.shared = shared_run()

    def test_official_files_unchanged_after_training(self):
        self.assertEqual(self.shared["hashes_before"],
                         self.shared["hashes_after"])
        for name, expected in MANIFEST["hashes"].items():
            self.assertEqual(self.shared["hashes_after"][name], expected,
                             name)


class RegistryTests(unittest.TestCase):
    """12. Registro de experimentos sin sobrescribir las filas previas."""

    @classmethod
    def setUpClass(cls):
        cls.shared = shared_run()

    def test_run_records_random_forest_row(self):
        row = self.shared["rows"][-1]
        result = self.shared["result"]
        self.assertEqual(row["model"], trf.MODEL_NAME)
        self.assertEqual(row["experiment_id"], result["experiment_id"])
        self.assertEqual(row["features"], "|".join(FEATURE_NAMES))
        self.assertEqual(row["target"], mp.TARGET)
        self.assertEqual(row["train_range"], "2025-01..2026-03")
        self.assertEqual(row["validation_range"], "2026-04..2026-06")
        self.assertEqual(row["test_range"], "2026-07..2026-09")
        self.assertEqual(len(row["dataset_hash"]), 64)
        self.assertGreater(float(row["training_seconds"]), 0.0)
        self.assertEqual(float(row["mae_val"]), result["validation"]["mae"])
        self.assertEqual(float(row["rmse_val"]), result["validation"]["rmse"])
        self.assertEqual(float(row["r2_val"]), result["validation"]["r2"])
        for column in ("mae_test", "rmse_test", "r2_test"):
            self.assertEqual(row[column], "")
        parameters = json.loads(row["parameters"])
        self.assertEqual(parameters["random_state"], 42)
        self.assertEqual(parameters["n_jobs"], 1)
        self.assertIn("internal_mae", parameters)
        self.assertEqual(
            {key for key in parameters
             if key in trf.ALLOWED_HYPERPARAMETERS},
            set(trf.ALLOWED_HYPERPARAMETERS),
        )
        self.assertIn("scikit-learn", row["tool_versions"])
        self.assertTrue(row["artifact_path"].endswith(".joblib"))
        self.assertIn("CANDIDATE sin seleccionar V1", row["notes"])

    def test_run_preserves_previous_rows(self):
        before = self.shared["registry_rows_before"]
        after = self.shared["rows"]
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(after[:len(before)], before)
        self.assertEqual(after[-1]["model"], trf.MODEL_NAME)

    def test_real_registry_contains_three_experiments(self):
        self.assertTrue(mp.EXPERIMENTS_PATH.exists(),
                        "falta experiments.csv con la ejecución real")
        header, rows = read_registry(mp.EXPERIMENTS_PATH)
        self.assertEqual(tuple(header), mp.EXPERIMENT_COLUMNS)
        models = [row["model"] for row in rows]
        self.assertIn(mp.BASELINE_MODEL, models)
        self.assertIn("LINEARREGRESSION", models)
        self.assertIn(trf.MODEL_NAME, models)
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


if __name__ == "__main__":
    unittest.main()
