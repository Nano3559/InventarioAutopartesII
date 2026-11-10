"""Pruebas de la evaluación final de V1 sobre TEST (H4 tarea 9B).

Las pruebas de comportamiento usan fixtures sintéticos aislados (dataset,
artefacto, manifiesto y registro propios en directorios temporales) y nunca
ejecutan la evaluación oficial real sobre TEST. Solo las pruebas de estado
oficial verifican, en modo lectura, que el reporte y el registro oficiales
existen con integridad conservada.
"""
import csv
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import evaluate_v1 as ev
import ml_pipeline as mp
import select_v1 as sv1
import train_linear_regression as tlr
from simulator_inputs import FEATURE_NAMES, HERE, InputError, content_sha256

FROZEN_PARAMETERS = {
    "n_estimators": 200,
    "max_depth": 8,
    "min_samples_leaf": 3,
    "max_features": "sqrt",
    "random_state": 42,
    "n_jobs": 1,
}
TEST_MONTHS = ["2026-07", "2026-08", "2026-09"]
OFFICIAL_REPORT_DIGEST = (
    content_sha256(ev.TEST_EVALUATION_PATH.read_bytes())
    if ev.TEST_EVALUATION_PATH.exists() else None
)


class DummyEstimator:
    """Sustituto determinista de RandomForest para fixtures aislados."""

    calls = 0

    def predict(self, X):
        DummyEstimator.calls += 1
        return np.asarray(X["ventas_mes_anterior"],
                          dtype="float64") * 0.8 - 2.0


def _calendar(month):
    number = int(month[5:7])
    angle = 2 * math.pi * (number - 1) / 12
    sine = round(math.sin(angle), 12)
    cosine = round(math.cos(angle), 12)
    return min(1.0, max(-1.0, sine)), min(1.0, max(-1.0, cosine))


def build_fixture(root):
    """Dataset, artefacto, manifiesto y registro sintéticos y coherentes."""
    rows = []

    def add(month, product, store, lag1, lag2, lag3, target):
        sine, cosine = _calendar(month)
        rows.append({
            "mes_objetivo": month,
            "productId": product,
            "locationId": store,
            "ventas_mes_anterior": lag1,
            "ventas_hace_2_meses": lag2,
            "ventas_hace_3_meses": lag3,
            "mes_sin": sine,
            "mes_cos": cosine,
            "target_ventas_mes": target,
        })

    add("2026-01", 1, 5, 4, 3, 2, 5)
    add("2026-04", 1, 5, 6, 5, 4, 7)
    for month in TEST_MONTHS:
        for product in range(1, 57):
            for store in (5, 6, 7):
                lag1 = (product * 3 + store + int(month[5:7])) % 12
                lag2 = (product + store * 2) % 9
                lag3 = (product * 2 + store) % 7
                add(month, product, store, lag1, lag2, lag3,
                    lag1 + product % 4)
    dataset_path = root / "dataset_supervisado.csv"
    with dataset_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(mp.DATASET_COLUMNS),
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    dataset_hash = content_sha256(dataset_path.read_bytes())

    artifact_path = root / "random_forest_candidate.joblib"
    payload = {
        "schema": "h4-random-forest-1",
        "model": "RANDOMFOREST",
        "role": "CANDIDATE",
        "feature_names": list(FEATURE_NAMES),
        "target": mp.TARGET,
        "train_range": "2025-01..2026-03",
        "trained_through": "2026-03",
        "dataset_version": "fixture",
        "dataset_hash": dataset_hash,
        "catalog_hash": "f" * 64,
        "seed": 42,
        "preprocessing": "ninguno (fixture de prueba)",
        "parameters": dict(FROZEN_PARAMETERS),
        "versions": {"python": "3.11.0", "scikit-learn": "fixture"},
        "created_utc": "2026-11-09T00:00:00Z",
        "scaler": None,
        "estimator": DummyEstimator(),
    }
    tlr.save_artifact(artifact_path, payload)
    artifact_hash = content_sha256(artifact_path.read_bytes())

    manifest_path = root / "v1_selection_manifest.json"
    selection = {
        "schema": sv1.SELECTION_SCHEMA,
        "v1_id": "V1",
        "selection_id": "SEL-V1-RANDOMFOREST-FIXTURE",
        "frozen_utc": "2026-11-09T00:00:00Z",
        "status": "SELECTED_FROZEN_NOT_ACTIVE",
        "active": False,
        "artifact_role": "CANDIDATE",
        "criterion": {"principal": "MAE global en VALIDATION"},
        "selection": {
            "model": "RANDOMFOREST",
            "experiment_id": "EXP-RANDOMFOREST-FIXTURE",
            "mae_val": 1.25,
            "rmse_val": 2.5,
            "r2_val": 0.5,
        },
        "artifact": {
            "path": str(artifact_path),
            "sha256": artifact_hash,
            "bytes": artifact_path.stat().st_size,
            "schema": "h4-random-forest-1",
            "model": "RANDOMFOREST",
            "role": "CANDIDATE",
            "created_utc": "2026-11-09T00:00:00Z",
            "candidate_preserved": True,
            "retrained": False,
        },
        "dataset": {
            "version": "fixture",
            "hashes": {"dataset_supervisado.csv": dataset_hash},
            "catalog_hash": "f" * 64,
            "generator_version": "fixture",
            "seed": 42,
        },
        "contract": {
            "features": list(FEATURE_NAMES),
            "feature_order_exacta": True,
            "target": mp.TARGET,
            "preprocessing": "ninguno (fixture de prueba)",
        },
        "hyperparameters": dict(FROZEN_PARAMETERS),
        "seed": {"random_state": 42, "dataset_seed": 42},
        "validation_metrics": {
            "global": {"n": 504, "n_con_prediccion": 504, "mae": 1.25,
                       "rmse": 2.5, "r2": 0.5, "cobertura": 1.0},
        },
        "versions": {"python": "3.11.0", "scikit-learn": "fixture"},
        "test": {"metricas_calculadas": False},
    }
    manifest_path.write_text(
        json.dumps(selection, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )

    registry_path = root / "experiments.csv"
    with registry_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=mp.EXPERIMENT_COLUMNS,
                                lineterminator="\n")
        writer.writeheader()
        for model in sv1.REQUIRED_MODELS:
            row = {column: "" for column in mp.EXPERIMENT_COLUMNS}
            suffix = "FIXTURE" if model != "BASELINE_LAG1" else "BASE"
            row.update({
                "experiment_id": f"EXP-{model}-{suffix}",
                "timestamp": "2026-11-09T00:00:00Z",
                "dataset_version": "fixture",
                "dataset_hash": dataset_hash,
                "catalog_hash": "f" * 64,
                "generator_version": "fixture",
                "seed": "42",
                "features": "|".join(FEATURE_NAMES),
                "target": mp.TARGET,
                "train_range": "2025-01..2026-03",
                "validation_range": "2026-04..2026-06",
                "test_range": "2026-07..2026-09",
                "model": model,
                "preprocessing": "fixture",
                "mae_val": "1.25",
                "rmse_val": "2.5",
                "r2_val": "0.5",
                "training_seconds": "0.1",
                "tool_versions": "python 3.11.0",
            })
            if model == "RANDOMFOREST":
                row["experiment_id"] = "EXP-RANDOMFOREST-FIXTURE"
                row["artifact_path"] = str(artifact_path)
            writer.writerow(row)

    return {
        "dataset": dataset_path,
        "artifact": artifact_path,
        "manifest": manifest_path,
        "registry": registry_path,
        "report": root / "v1_test_evaluation.json",
        "dataset_hash": dataset_hash,
        "artifact_hash": artifact_hash,
        "payload": payload,
    }


def run_fixture(fx):
    return ev.run_final_evaluation(
        manifest_path=fx["manifest"],
        dataset_path=fx["dataset"],
        registry_path=fx["registry"],
        report_path=fx["report"],
    )


def precheck_fixture(fx):
    return ev.precheck_v1(
        manifest_path=fx["manifest"],
        dataset_path=fx["dataset"],
        registry_path=fx["registry"],
        report_path=fx["report"],
    )


def read_rows(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames or ()), list(reader)


class FixtureCase(unittest.TestCase):
    """Base con un fixture sintético aislado por prueba."""

    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.fx = build_fixture(Path(self._temp.name))

    def tearDown(self):
        self._temp.cleanup()


class ManifestVerificationTests(FixtureCase):
    """Verificación del manifiesto de congelamiento."""

    def test_precheck_passes_on_valid_fixture(self):
        checked = precheck_fixture(self.fx)
        self.assertEqual(checked["selection"]["selection"]["model"],
                         "RANDOMFOREST")
        self.assertEqual(checked["selection"]["status"],
                         "SELECTED_FROZEN_NOT_ACTIVE")

    def test_missing_manifest_rejected(self):
        self.fx["manifest"].unlink()
        with self.assertRaisesRegex(InputError, "MANIFIESTO"):
            precheck_fixture(self.fx)

    def test_wrong_status_rejected(self):
        document = json.loads(self.fx["manifest"].read_text(encoding="utf-8"))
        document["status"] = "ACTIVE"
        self.fx["manifest"].write_text(
            json.dumps(document, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaisesRegex(InputError,
                                    "SELECTED_FROZEN_NOT_ACTIVE"):
            precheck_fixture(self.fx)

    def test_non_random_forest_v1_rejected(self):
        document = json.loads(self.fx["manifest"].read_text(encoding="utf-8"))
        document["selection"]["model"] = "LINEARREGRESSION"
        self.fx["manifest"].write_text(
            json.dumps(document, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaisesRegex(InputError, "debe ser RANDOMFOREST"):
            precheck_fixture(self.fx)

    def test_wrong_schema_rejected(self):
        document = json.loads(self.fx["manifest"].read_text(encoding="utf-8"))
        document["schema"] = "esquema-desconocido"
        self.fx["manifest"].write_text(
            json.dumps(document, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaisesRegex(InputError, "esquema"):
            precheck_fixture(self.fx)


class ArtifactIntegrityTests(FixtureCase):
    """Integridad SHA256 y parámetros del artefacto congelado."""

    def test_tampered_artifact_rejected(self):
        with self.fx["artifact"].open("ab") as handle:
            handle.write(b"\x00")
        with self.assertRaisesRegex(InputError, "SHA256"):
            precheck_fixture(self.fx)

    def test_missing_artifact_rejected(self):
        self.fx["artifact"].unlink()
        with self.assertRaises(InputError):
            precheck_fixture(self.fx)

    def test_changed_frozen_parameters_rejected(self):
        document = json.loads(self.fx["manifest"].read_text(encoding="utf-8"))
        document["hyperparameters"]["n_estimators"] = 100
        self.fx["manifest"].write_text(
            json.dumps(document, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaisesRegex(InputError, "PARÁMETROS"):
            precheck_fixture(self.fx)

    def test_artifact_bytes_unchanged_by_evaluation(self):
        before = content_sha256(self.fx["artifact"].read_bytes())
        run_fixture(self.fx)
        after = content_sha256(self.fx["artifact"].read_bytes())
        self.assertEqual(before, after)
        self.assertEqual(before, self.fx["artifact_hash"])


class DatasetIntegrityTests(FixtureCase):
    """Integridad del dataset durante la evaluación."""

    def test_modified_dataset_rejected_before_predicting(self):
        with self.fx["dataset"].open("a", encoding="utf-8",
                                     newline="\n") as handle:
            handle.write("2026-08,1,5,1,1,1,0.5,0.866,3\n")
        with self.assertRaisesRegex(InputError, "DATASET INVÁLIDO"):
            precheck_fixture(self.fx)

    def test_dataset_bytes_unchanged_by_evaluation(self):
        before = content_sha256(self.fx["dataset"].read_bytes())
        run_fixture(self.fx)
        after = content_sha256(self.fx["dataset"].read_bytes())
        self.assertEqual(before, after)
        self.assertEqual(after, self.fx["dataset_hash"])


class FeatureContractTests(FixtureCase):
    """Cinco features exactas y orden oficial."""

    def test_reordered_manifest_features_rejected(self):
        document = json.loads(self.fx["manifest"].read_text(encoding="utf-8"))
        document["contract"]["features"] = list(
            reversed(document["contract"]["features"])
        )
        self.fx["manifest"].write_text(
            json.dumps(document, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaisesRegex(InputError, "CONTRATO INVÁLIDO"):
            precheck_fixture(self.fx)

    def test_missing_manifest_feature_rejected(self):
        document = json.loads(self.fx["manifest"].read_text(encoding="utf-8"))
        document["contract"]["features"] = [
            name for name in document["contract"]["features"]
            if name != "mes_cos"
        ]
        self.fx["manifest"].write_text(
            json.dumps(document, ensure_ascii=False), encoding="utf-8"
        )
        with self.assertRaisesRegex(InputError, "CONTRATO INVÁLIDO"):
            precheck_fixture(self.fx)

    def test_payload_features_match_official_order(self):
        checked = precheck_fixture(self.fx)
        self.assertEqual(checked["payload"]["feature_names"],
                         list(FEATURE_NAMES))
        self.assertEqual(checked["selection"]["contract"]["features"],
                         list(FEATURE_NAMES))


class NoTrainingTests(FixtureCase):
    """La evaluación no entrena ni modifica parámetros."""

    def test_source_never_fits(self):
        source = Path(ev.__file__).read_text(encoding="utf-8")
        for token in (".fit(", "train_candidate", "fit_model",
                      "save_artifact", "joblib.dump"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_frozen_parameters_unchanged_after_evaluation(self):
        run_fixture(self.fx)
        payload = tlr.load_artifact(self.fx["artifact"])
        self.assertEqual(payload["parameters"], FROZEN_PARAMETERS)
        document = json.loads(self.fx["manifest"].read_text(encoding="utf-8"))
        self.assertEqual(document["hyperparameters"], FROZEN_PARAMETERS)

    def test_report_marks_no_retraining(self):
        result = run_fixture(self.fx)
        report = result["report"]
        self.assertFalse(report["retrained"])
        self.assertFalse(report["model_changed"])
        self.assertFalse(report["hyperparameters_changed"])
        self.assertEqual(result["execution"], "evaluated_now")


class MetricsComputationTests(FixtureCase):
    """Cálculo correcto de métricas sobre TEST sintético."""

    def test_metrics_match_manual_computation(self):
        result = run_fixture(self.fx)
        report = result["report"]
        frame = mp.load_supervised(self.fx["dataset"])
        split = mp.split_temporal(frame)
        X, y = mp.build_xy(split["test"])
        payload = tlr.load_artifact(self.fx["artifact"])
        prediction = payload["estimator"].predict(X)
        expected = mp.evaluate(y, prediction)
        for key in ("n", "n_con_prediccion", "mae", "rmse", "r2",
                    "cobertura"):
            with self.subTest(key=key):
                self.assertEqual(report["metrics"][key], expected[key])
        self.assertEqual(report["metrics"]["predicciones_negativas"],
                         int((prediction < 0).sum()))

    def test_negative_predictions_are_kept_without_clipping(self):
        result = run_fixture(self.fx)
        negatives = result["report"]["metrics"]["predicciones_negativas"]
        self.assertGreater(negatives, 0)
        frame = mp.load_supervised(self.fx["dataset"])
        split = mp.split_temporal(frame)
        X, _ = mp.build_xy(split["test"])
        payload = tlr.load_artifact(self.fx["artifact"])
        prediction = payload["estimator"].predict(X)
        self.assertLess(float(prediction.min()), 0.0)

    def test_global_metrics_shape(self):
        metrics = run_fixture(self.fx)["report"]["metrics"]
        self.assertEqual(metrics["n"], 504)
        self.assertEqual(metrics["n_con_prediccion"], 504)
        self.assertEqual(metrics["cobertura"], 1.0)
        self.assertIsInstance(metrics["predicciones_negativas"], int)
        self.assertGreaterEqual(metrics["mae"], 0.0)
        self.assertGreaterEqual(metrics["rmse"], 0.0)
        self.assertIsInstance(metrics["r2"], float)

    def test_groups_by_store_month_and_rotation(self):
        groups = run_fixture(self.fx)["report"]["groups"]
        self.assertEqual(set(groups["por_tienda"]), {"5", "6", "7"})
        self.assertEqual(set(groups["por_mes"]), set(TEST_MONTHS))
        for grouping in groups.values():
            self.assertEqual(sum(entry["n"] for entry in grouping.values()),
                             504)
        self.assertEqual(groups["por_tienda"]["5"]["n"], 168)


class RegistrySingleEvaluationTests(FixtureCase):
    """Registro único y reporte de evaluación final."""

    def test_only_rf_row_receives_test_fields(self):
        run_fixture(self.fx)
        _, rows = read_rows(self.fx["registry"])
        by_model = {row["model"]: row for row in rows}
        for field in ev.TEST_FIELDS:
            self.assertNotEqual(by_model["RANDOMFOREST"][field], "")
            self.assertEqual(by_model["BASELINE_LAG1"][field], "")
            self.assertEqual(by_model["LINEARREGRESSION"][field], "")

    def test_registry_metrics_equal_report(self):
        result = run_fixture(self.fx)
        _, rows = read_rows(self.fx["registry"])
        rf = next(row for row in rows if row["model"] == "RANDOMFOREST")
        metrics = result["report"]["metrics"]
        self.assertEqual(float(rf["mae_test"]), metrics["mae"])
        self.assertEqual(float(rf["rmse_test"]), metrics["rmse"])
        self.assertEqual(float(rf["r2_test"]), metrics["r2"])
        self.assertEqual(rf["experiment_id"],
                         result["report"]["registry"]["experiment_id"])

    def test_report_is_completed_and_traceable(self):
        result = run_fixture(self.fx)
        report = json.loads(self.fx["report"].read_text(encoding="utf-8"))
        self.assertEqual(result["report"], report)
        self.assertEqual(report["schema"], ev.EVALUATION_SCHEMA)
        self.assertEqual(report["status"], "TEST_EVALUATED_COMPLETED")
        self.assertEqual(report["v1_id"], "V1")
        self.assertEqual(report["selection_id"],
                         "SEL-V1-RANDOMFOREST-FIXTURE")
        self.assertEqual(report["artifact"]["sha256"],
                         self.fx["artifact_hash"])
        self.assertEqual(report["dataset"]["hash"], self.fx["dataset_hash"])
        self.assertEqual(report["test"]["period"], "2026-07..2026-09")
        self.assertEqual(report["test"]["rows"], 504)
        self.assertEqual(report["test"]["months"], TEST_MONTHS)
        self.assertEqual(report["registry"]["updated_fields"],
                         list(ev.TEST_FIELDS))
        self.assertIn("python", report["versions"])

    def test_header_and_row_count_preserved(self):
        header_before, rows_before = read_rows(self.fx["registry"])
        run_fixture(self.fx)
        header_after, rows_after = read_rows(self.fx["registry"])
        self.assertEqual(header_before, header_after)
        self.assertEqual(len(rows_before), len(rows_after))


class PreservationTests(FixtureCase):
    """Preservación de todos los campos y filas previos del registro."""

    def test_only_the_three_test_fields_change(self):
        header, before = read_rows(self.fx["registry"])
        run_fixture(self.fx)
        _, after = read_rows(self.fx["registry"])
        self.assertEqual(len(before), len(after))
        for old, new in zip(before, after):
            for column in header:
                if column in ev.TEST_FIELDS and old["model"] == (
                    "RANDOMFOREST"
                ):
                    self.assertEqual(old[column], "")
                    self.assertNotEqual(new[column], "")
                else:
                    self.assertEqual(old[column], new[column],
                                     (old["model"], column))

    def test_non_test_rows_are_byte_identical(self):
        _, before = read_rows(self.fx["registry"])
        run_fixture(self.fx)
        _, after = read_rows(self.fx["registry"])
        for old, new in zip(before, after):
            if old["model"] == "RANDOMFOREST":
                continue
            self.assertEqual(old, new)


class IdempotencyTests(FixtureCase):
    """Segunda ejecución devuelve el resultado registrado sin recalcular."""

    def test_second_run_returns_registered_result(self):
        first = run_fixture(self.fx)
        self.assertEqual(first["execution"], "evaluated_now")
        calls_after_first = DummyEstimator.calls
        report_bytes = self.fx["report"].read_bytes()
        registry_bytes = self.fx["registry"].read_bytes()

        second = run_fixture(self.fx)
        self.assertEqual(second["execution"], "already_evaluated")
        self.assertEqual(second["report"], first["report"])
        self.assertEqual(self.fx["report"].read_bytes(), report_bytes)
        self.assertEqual(self.fx["registry"].read_bytes(), registry_bytes)
        self.assertEqual(DummyEstimator.calls, calls_after_first)

    def test_multiple_reruns_stay_stable(self):
        run_fixture(self.fx)
        report_bytes = self.fx["report"].read_bytes()
        for _ in range(3):
            result = run_fixture(self.fx)
            self.assertEqual(result["execution"], "already_evaluated")
        self.assertEqual(self.fx["report"].read_bytes(), report_bytes)


class SecondEvaluationRejectionTests(FixtureCase):
    """Rechazo explícito de una segunda evaluación oficial."""

    def test_precheck_rejects_when_report_exists(self):
        run_fixture(self.fx)
        with self.assertRaisesRegex(InputError,
                                    "EVALUACIÓN YA REGISTRADA"):
            precheck_fixture(self.fx)

    def test_precheck_rejects_when_registry_already_filled(self):
        run_fixture(self.fx)
        self.fx["report"].unlink()
        with self.assertRaisesRegex(InputError, "TEST ya contiene métricas"):
            precheck_fixture(self.fx)

    def test_update_test_fields_refuses_second_write(self):
        result = run_fixture(self.fx)
        with self.assertRaisesRegex(InputError, "ya fueron registrados"):
            ev.update_test_fields(self.fx["registry"],
                                  result["report"]["registry"][
                                      "experiment_id"],
                                  result["report"]["metrics"])

    def test_evaluation_refuses_overwriting_existing_report(self):
        run_fixture(self.fx)
        report_bytes = self.fx["report"].read_bytes()
        result = run_fixture(self.fx)
        self.assertEqual(result["execution"], "already_evaluated")
        self.assertEqual(self.fx["report"].read_bytes(), report_bytes)


class OfficialStateTests(unittest.TestCase):
    """Estado oficial en modo lectura; nunca re-ejecuta la evaluación."""

    def test_official_report_exists_and_completed(self):
        path = ev.TEST_EVALUATION_PATH
        self.assertTrue(path.exists(),
                        "falta reports/v1_test_evaluation.json")
        report = json.loads(path.read_text(encoding="utf-8"))
        selection = json.loads(
            sv1.V1_MANIFEST_PATH.read_text(encoding="utf-8")
        )
        self.assertEqual(report["schema"], ev.EVALUATION_SCHEMA)
        self.assertEqual(report["status"], "TEST_EVALUATED_COMPLETED")
        self.assertEqual(report["selection_id"],
                         selection["selection_id"])
        self.assertEqual(report["artifact"]["sha256"],
                         selection["artifact"]["sha256"])
        self.assertEqual(report["test"]["rows"], 504)
        self.assertEqual(report["test"]["months"], TEST_MONTHS)
        self.assertEqual(report["registry"]["updated_fields"],
                         list(ev.TEST_FIELDS))

    def test_official_registry_filled_only_on_rf_row(self):
        _, rows = read_rows(mp.EXPERIMENTS_PATH)
        report = json.loads(ev.TEST_EVALUATION_PATH.read_text(
            encoding="utf-8"))
        by_model = {row["model"]: row for row in rows}
        rf = by_model["RANDOMFOREST"]
        for field in ev.TEST_FIELDS:
            self.assertNotEqual(rf[field], "")
            self.assertEqual(by_model["BASELINE_LAG1"][field], "")
            self.assertEqual(by_model["LINEARREGRESSION"][field], "")
        self.assertEqual(float(rf["mae_test"]), report["metrics"]["mae"])
        self.assertEqual(rf["mae_val"], "5.158657249544053")

    def test_official_metrics_are_valid(self):
        report = json.loads(ev.TEST_EVALUATION_PATH.read_text(
            encoding="utf-8"))
        metrics = report["metrics"]
        self.assertEqual(metrics["n"], 504)
        self.assertEqual(metrics["n_con_prediccion"], 504)
        self.assertEqual(metrics["cobertura"], 1.0)
        self.assertGreater(metrics["mae"], 0.0)
        self.assertGreater(metrics["rmse"], 0.0)
        self.assertIsInstance(metrics["r2"], float)
        self.assertIsInstance(metrics["predicciones_negativas"], int)
        for grouping in report["groups"].values():
            self.assertEqual(sum(entry["n"] for entry in grouping.values()),
                             504)

    def test_official_precheck_rejects_second_evaluation(self):
        with self.assertRaisesRegex(InputError, "EVALUACIÓN YA REGISTRADA"):
            ev.precheck_v1()

    def test_official_artifact_and_dataset_intact(self):
        selection = json.loads(
            sv1.V1_MANIFEST_PATH.read_text(encoding="utf-8")
        )
        artifact = HERE / "models" / "random_forest_candidate.joblib"
        self.assertEqual(content_sha256(artifact.read_bytes()),
                         selection["artifact"]["sha256"])
        payload = tlr.load_artifact(artifact)
        self.assertEqual(payload["parameters"], FROZEN_PARAMETERS)
        self.assertEqual(payload["created_utc"], "2026-11-09T04:00:26Z")
        manifest = mp.official_manifest()
        for name, digest in manifest["hashes"].items():
            self.assertEqual(
                content_sha256((mp.DATA_DIR / name).read_bytes()), digest,
                name,
            )

    def test_official_report_unchanged_during_suite(self):
        self.assertIsNotNone(OFFICIAL_REPORT_DIGEST,
                             "el reporte oficial debe existir")
        self.assertEqual(
            content_sha256(ev.TEST_EVALUATION_PATH.read_bytes()),
            OFFICIAL_REPORT_DIGEST,
        )
        _, rows = read_rows(mp.EXPERIMENTS_PATH)
        self.assertEqual(len(rows), 3)


if __name__ == "__main__":
    unittest.main()
