"""Pruebas de la preparación ML: contrato, split, fuga, baseline y registro.

Cubre las trece áreas obligatorias de la Tarea 6 sin entrenar modelos
supervisados y sin calcular métricas de TEST.
"""
import csv
import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import ml_pipeline as mp
from simulator_inputs import FEATURE_NAMES, HERE, InputError, content_sha256

DATA = HERE / "data" / "escenarios_v1_1"
MANIFEST = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))

_OFFICIAL_FRAME = None


def official_frame():
    global _OFFICIAL_FRAME
    if _OFFICIAL_FRAME is None:
        _OFFICIAL_FRAME = mp.load_supervised()
    return _OFFICIAL_FRAME


def make_row(month="2025-04", product=1, store=5, lag1=1, lag2=2, lag3=3,
             target=4, **extra):
    _, month_number = mp.parse_month(month)
    angle = 2 * math.pi * (month_number - 1) / 12
    row = {
        "mes_objetivo": month, "productId": product, "locationId": store,
        "ventas_mes_anterior": lag1, "ventas_hace_2_meses": lag2,
        "ventas_hace_3_meses": lag3,
        "mes_sin": round(math.sin(angle), 12),
        "mes_cos": round(math.cos(angle), 12),
        "target_ventas_mes": target,
    }
    row.update(extra)
    return row


def make_frame(rows):
    return pd.DataFrame(rows, columns=list(mp.DATASET_COLUMNS))


def write_csv(path, rows, columns=None):
    columns = list(mp.DATASET_COLUMNS) if columns is None else columns
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {key: value for key, value in row.items() if key in columns}
            )


class ContractColumnsTests(unittest.TestCase):
    """Área 1: contrato de columnas."""

    def test_official_header_matches_contract(self):
        header = (DATA / "dataset_supervisado.csv").read_text(
            encoding="utf-8"
        ).splitlines()[0]
        self.assertEqual(tuple(header.split(",")), mp.DATASET_COLUMNS)
        self.assertEqual(len(mp.DATASET_COLUMNS), 9)

    def test_loader_rejects_missing_column(self):
        columns = [c for c in mp.DATASET_COLUMNS if c != "mes_cos"]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dataset.csv"
            write_csv(path, [make_row()], columns=columns)
            with self.assertRaisesRegex(InputError, "columnas"):
                mp.load_supervised(path)

    def test_loader_rejects_extra_internal_column(self):
        row = make_row(demanda_latente=99)
        columns = list(mp.DATASET_COLUMNS) + ["demanda_latente"]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dataset.csv"
            write_csv(path, [row], columns=columns)
            with self.assertRaisesRegex(InputError, "columnas"):
                mp.load_supervised(path)

    def test_repeated_column_rejected(self):
        frame = make_frame([make_row()])
        frame = pd.concat([frame, frame[["mes_objetivo"]]], axis=1)
        with self.assertRaisesRegex(InputError, "repetida"):
            mp.validate_frame(frame)

    def test_loader_rejects_unreadable_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dataset.csv"
            path.write_text("sin,estructura\n1,2,3,4\n", encoding="utf-8")
            with self.assertRaises(InputError):
                mp.load_supervised(path)
            with self.assertRaisesRegex(InputError, "falta el archivo"):
                mp.load_supervised(Path(temp) / "no_existe.csv")


class FeatureOrderTests(unittest.TestCase):
    """Área 2: orden exacto de las cinco features."""

    @classmethod
    def setUpClass(cls):
        cls.split = mp.split_temporal(official_frame())
        cls.data = mp.split_xy(cls.split)

    def test_x_columns_match_official_feature_order(self):
        for name in ("train", "validation", "test"):
            with self.subTest(partition=name):
                self.assertEqual(
                    list(self.data[name]["X"].columns), list(FEATURE_NAMES)
                )

    def test_feature_contract_matches_simulator(self):
        self.assertEqual(mp.FEATURE_COLUMNS, FEATURE_NAMES)
        self.assertEqual(len(mp.FEATURE_COLUMNS), 5)

    def test_x_dtypes_are_numeric(self):
        X = self.data["validation"]["X"]
        self.assertTrue(
            all(pd.api.types.is_integer_dtype(X[c])
                for c in ("ventas_mes_anterior", "ventas_hace_2_meses",
                          "ventas_hace_3_meses"))
        )
        self.assertTrue(
            all(pd.api.types.is_float_dtype(X[c])
                for c in ("mes_sin", "mes_cos"))
        )


class MetadataExclusionTests(unittest.TestCase):
    """Área 5: IDs y target fuera de X; metadatos conservados aparte."""

    @classmethod
    def setUpClass(cls):
        cls.data = mp.split_xy(mp.split_temporal(official_frame()))

    def test_ids_and_target_excluded_from_x(self):
        forbidden = set(mp.ID_COLUMNS) | {mp.TARGET}
        for name in ("train", "validation", "test"):
            with self.subTest(partition=name):
                X = self.data[name]["X"]
                self.assertEqual(set(X.columns) & forbidden, set())
                self.assertEqual(list(X.columns), list(FEATURE_NAMES))

    def test_target_is_the_supervised_column(self):
        y = self.data["validation"]["y"]
        self.assertEqual(y.name, mp.TARGET)
        frame = self.data["validation"]["frame"]
        self.assertTrue((y.to_numpy() == frame[mp.TARGET].to_numpy()).all())

    def test_meta_keeps_identifiers_and_month(self):
        meta = self.data["validation"]["meta"]
        self.assertEqual(list(meta.columns), list(mp.ID_COLUMNS))
        self.assertEqual(len(meta), 504)

    def test_build_xy_rejects_missing_feature(self):
        frame = make_frame([make_row()]).drop(columns=["mes_sin"])
        with self.assertRaisesRegex(InputError, "faltan"):
            mp.build_xy(frame)


class TemporalSplitTests(unittest.TestCase):
    """Área 3: separación temporal por mes calendario."""

    def test_ranges_are_contiguous_disjoint_and_cover_window(self):
        indices = [
            (name, mp.month_index(start), mp.month_index(end))
            for name, (start, end) in mp.SPLIT_RANGES.items()
        ]
        self.assertEqual([i[0] for i in indices],
                         ["train", "validation", "test"])
        self.assertEqual(indices[0][1], mp.month_index(mp.MIN_MONTH))
        self.assertEqual(indices[2][2], mp.month_index(mp.MAX_MONTH))
        for (_, _, end), (_, start, _) in zip(indices, indices[1:]):
            self.assertEqual(end + 1, start)

    def test_official_partition_month_bounds(self):
        split = mp.split_temporal(official_frame())
        expected = {"train": (15, "2025-01", "2026-03"),
                    "validation": (3, "2026-04", "2026-06"),
                    "test": (3, "2026-07", "2026-09")}
        for name, (count, first, last) in expected.items():
            with self.subTest(partition=name):
                months = sorted(set(split[name]["mes_objetivo"]))
                self.assertEqual(len(months), count)
                self.assertEqual(months[0], first)
                self.assertEqual(months[-1], last)

    def test_no_overlap_and_chronological_order(self):
        split = mp.split_temporal(official_frame())
        train_max = mp.month_index(
            max(split["train"]["mes_objetivo"])
        )
        val_min = mp.month_index(min(split["validation"]["mes_objetivo"]))
        val_max = mp.month_index(max(split["validation"]["mes_objetivo"]))
        test_min = mp.month_index(min(split["test"]["mes_objetivo"]))
        self.assertLess(train_max, val_min)
        self.assertLess(val_max, test_min)
        for name, part in split.items():
            with self.subTest(partition=name):
                order = [mp.month_index(m) for m in part["mes_objetivo"]]
                self.assertEqual(order, sorted(order))

    def test_split_is_reproducible(self):
        first = mp.split_temporal(official_frame())
        second = mp.split_temporal(official_frame())
        for name in mp.SPLIT_RANGES:
            pd.testing.assert_frame_equal(first[name], second[name])

    def test_month_outside_window_rejected(self):
        for bad in ("2024-12", "2026-10"):
            with self.subTest(month=bad):
                with self.assertRaisesRegex(InputError, "ventana supervisada"):
                    mp.split_temporal(make_frame([make_row(month=bad)]))


class SplitCountTests(unittest.TestCase):
    """Área 4: conteos esperados del split oficial."""

    @classmethod
    def setUpClass(cls):
        cls.frame = official_frame()
        cls.split = mp.split_temporal(cls.frame)

    def test_official_row_counts(self):
        counts = mp.verify_split_counts(self.split)
        self.assertEqual(counts, mp.EXPECTED_SPLIT_COUNTS)
        self.assertEqual(len(self.frame), mp.EXPECTED_TOTAL_ROWS)
        self.assertEqual(sum(counts.values()), mp.EXPECTED_TOTAL_ROWS)

    def test_every_pair_has_twenty_one_months(self):
        sizes = self.frame.groupby(["productId", "locationId"]).size()
        self.assertEqual(len(sizes), 168)
        self.assertEqual(set(sizes), {21})

    def test_verify_split_counts_rejects_wrong_expectation(self):
        with self.assertRaisesRegex(InputError, "2521"):
            mp.verify_split_counts(
                self.split, expected={**mp.EXPECTED_SPLIT_COUNTS,
                                      "train": 2521}
            )

    def test_split_agrees_with_official_conjunto_labels(self):
        meta = pd.read_csv(DATA / "escenarios_metadatos.csv")
        mapping = {"TRAIN": "train", "VALIDATION": "validation",
                   "TEST": "test"}
        for label, part in mapping.items():
            with self.subTest(label=label):
                expected = {
                    (int(r.productId), int(r.locationId), str(r.mes))
                    for r in meta[meta["conjunto"] == label].itertuples()
                }
                actual = set(zip(
                    self.split[part]["productId"],
                    self.split[part]["locationId"],
                    self.split[part]["mes_objetivo"],
                ))
                self.assertEqual(expected, actual)
        history_months = set(meta.loc[meta["conjunto"] == "HISTORIA", "mes"])
        self.assertEqual(history_months & set(self.frame["mes_objetivo"]), set())


class ZeroPreservationTests(unittest.TestCase):
    """Área 6: los ceros válidos se conservan sin convertirse en ausencia."""

    @classmethod
    def setUpClass(cls):
        cls.frame = official_frame()
        cls.split = mp.split_temporal(cls.frame)

    def test_row_count_and_dtypes_preserved(self):
        self.assertEqual(len(self.frame), mp.EXPECTED_TOTAL_ROWS)
        for column in mp.QUANTITY_COLUMNS:
            with self.subTest(column=column):
                self.assertEqual(self.frame[column].dtype, np.int64)
                self.assertFalse(self.frame[column].isna().any())

    def test_target_zeros_preserved(self):
        zeros = int((self.frame[mp.TARGET] == 0).sum())
        self.assertEqual(zeros, mp.EXPECTED_TARGET_ZEROS)

    def test_lag_zeros_preserved(self):
        expected = {"ventas_mes_anterior": 422, "ventas_hace_2_meses": 416,
                    "ventas_hace_3_meses": 411}
        for column, count in expected.items():
            with self.subTest(column=column):
                self.assertEqual(int((self.frame[column] == 0).sum()), count)

    def test_zero_target_rows_reach_validation(self):
        zeros = int((self.split["validation"][mp.TARGET] == 0).sum())
        self.assertGreater(zeros, 0)


class InvalidInputRejectionTests(unittest.TestCase):
    """Área 7: rechazo de cantidades, meses, IDs y valores inválidos."""

    def test_negative_quantity_rejected(self):
        with self.assertRaisesRegex(InputError, "negativos"):
            mp.validate_frame(make_frame([make_row(lag1=-1)]))
        with self.assertRaisesRegex(InputError, "negativos"):
            mp.validate_frame(make_frame([make_row(target=-3)]))

    def test_decimal_quantity_rejected(self):
        with self.assertRaisesRegex(InputError, "negativos"):
            mp.validate_frame(make_frame([make_row(lag1=1.5)]))

    def test_boolean_rejected(self):
        with self.assertRaisesRegex(InputError, "negativos"):
            mp.validate_frame(make_frame([make_row(lag1=True)]))

    def test_nan_and_infinite_rejected(self):
        with self.assertRaisesRegex(InputError, "negativos"):
            mp.validate_frame(make_frame([make_row(lag1=np.nan)]))
        with self.assertRaisesRegex(InputError, "fin"):
            mp.validate_frame(make_frame([make_row(mes_cos=np.inf)]))

    def test_non_numeric_calendar_rejected(self):
        with self.assertRaisesRegex(InputError, "fin"):
            mp.validate_frame(make_frame([make_row(mes_sin="abc")]))

    def test_malformed_month_rejected(self):
        for bad in ("2025/01", "2025-13", "", "abril"):
            with self.subTest(month=bad):
                row = make_row()
                row["mes_objetivo"] = bad
                with self.assertRaises(InputError):
                    mp.validate_frame(make_frame([row]))

    def test_non_string_month_rejected(self):
        row = make_row()
        row["mes_objetivo"] = 202504
        with self.assertRaisesRegex(InputError, "YYYY-MM"):
            mp.validate_frame(make_frame([row]))

    def test_ids_outside_catalog_rejected(self):
        with self.assertRaisesRegex(InputError, "productId"):
            mp.validate_frame(make_frame([make_row(product=999)]))
        with self.assertRaisesRegex(InputError, "locationId"):
            mp.validate_frame(make_frame([make_row(store=1)]))

    def test_csv_with_invalid_value_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dataset.csv"
            write_csv(path, [make_row(lag1="-5")])
            with self.assertRaisesRegex(InputError, "negativos"):
                mp.load_supervised(path)

    def test_csv_with_malformed_month_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dataset.csv"
            row = make_row()
            row["mes_objetivo"] = "2025/01"
            write_csv(path, [row])
            with self.assertRaises(InputError):
                mp.load_supervised(path)


class DuplicateRejectionTests(unittest.TestCase):
    """Área 8: claves duplicadas de producto, tienda y mes."""

    def test_duplicate_key_rejected_in_memory(self):
        frame = make_frame([make_row(), make_row()])
        with self.assertRaisesRegex(InputError, "duplicada"):
            mp.validate_frame(frame)

    def test_duplicate_key_rejected_in_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dataset.csv"
            write_csv(path, [make_row(), make_row(target=9)])
            with self.assertRaisesRegex(InputError, "duplicada"):
                mp.load_supervised(path)

    def test_same_month_different_pairs_allowed(self):
        frame = make_frame([make_row(product=1), make_row(product=2)])
        validated = mp.validate_frame(frame)
        self.assertEqual(len(validated), 2)


class LeakageTests(unittest.TestCase):
    """Área 9: ausencia de fuga temporal y consistencia con la historia."""

    @classmethod
    def setUpClass(cls):
        cls.frame = official_frame()

    def test_official_dataset_has_no_leakage(self):
        counts = mp.assert_no_leakage(self.frame)
        self.assertEqual(counts, {"lag_vs_historia": 0,
                                  "target_vs_historia": 0,
                                  "calendario": 0})

    def test_injected_future_lag_detected(self):
        frame = self.frame.copy()
        index = frame.index[0]
        frame.loc[index, "ventas_mes_anterior"] = (
            int(frame.loc[index, "ventas_mes_anterior"]) + 1
        )
        counts = mp.check_no_leakage(frame)
        self.assertGreater(counts["lag_vs_historia"], 0)
        with self.assertRaisesRegex(InputError, "inconsistencia"):
            mp.assert_no_leakage(frame)

    def test_target_mismatch_detected(self):
        frame = self.frame.copy()
        index = frame.index[0]
        frame.loc[index, mp.TARGET] = int(frame.loc[index, mp.TARGET]) + 1
        counts = mp.check_no_leakage(frame)
        self.assertGreater(counts["target_vs_historia"], 0)

    def test_calendar_mismatch_detected(self):
        frame = self.frame.copy()
        index = frame.index[frame["mes_objetivo"] == "2025-01"][0]
        frame.loc[index, "mes_sin"] = 0.5
        counts = mp.check_no_leakage(frame)
        self.assertGreater(counts["calendario"], 0)

    def test_features_reference_only_earlier_months(self):
        panel_min = mp.month_index("2024-10")
        split = mp.split_temporal(self.frame)
        for name, part in split.items():
            with self.subTest(partition=name):
                earliest = mp.month_index(min(part["mes_objetivo"]))
                # El lag3 del primer mes del split vive dentro del panel
                # oficial (2024-10..2026-09); los lags son meses anteriores.
                self.assertGreaterEqual(earliest - 3, panel_min)
                self.assertLess(earliest - 3, earliest)


class BaselineLag1Tests(unittest.TestCase):
    """Área 10: el baseline predice exactamente el lag1, sin recortes."""

    @classmethod
    def setUpClass(cls):
        cls.data = mp.split_xy(mp.split_temporal(official_frame()))

    def test_baseline_equals_lag1_on_controlled_frame(self):
        frame = make_frame([
            make_row(month="2025-05", lag1=7, target=9),
            make_row(month="2025-06", lag1=0, target=3),
        ])
        X, _ = mp.build_xy(frame)
        prediction = mp.baseline_predict(X)
        self.assertEqual(list(prediction), [7.0, 0.0])

    def test_baseline_equals_lag1_on_validation(self):
        validation = self.data["validation"]
        prediction = mp.baseline_predict(validation["X"])
        expected = validation["X"]["ventas_mes_anterior"].to_numpy(
            dtype="float64"
        )
        self.assertTrue((prediction.to_numpy() == expected).all())

    def test_baseline_does_not_use_target(self):
        validation = self.data["validation"]
        prediction = mp.baseline_predict(validation["X"])
        differs = prediction.to_numpy() != validation["y"].to_numpy()
        self.assertTrue(differs.any())

    def test_baseline_rejects_missing_feature(self):
        with self.assertRaisesRegex(InputError, "ventas_mes_anterior"):
            mp.baseline_predict(pd.DataFrame({"otra": [1.0]}))


class MetricCorrectnessTests(unittest.TestCase):
    """Área 11: MAE, RMSE, R², n y cobertura con ejemplos controlados."""

    def test_controlled_example_exact_values(self):
        metrics = mp.evaluate([10, 20, 30], [10, 25, 25])
        self.assertEqual(metrics["n"], 3)
        self.assertEqual(metrics["n_con_prediccion"], 3)
        self.assertAlmostEqual(metrics["mae"], 10 / 3, places=12)
        self.assertAlmostEqual(metrics["rmse"], math.sqrt(50 / 3), places=12)
        self.assertAlmostEqual(metrics["r2"], 0.75, places=12)
        self.assertEqual(metrics["cobertura"], 1.0)

    def test_predictions_are_not_rounded_before_measuring(self):
        metrics = mp.evaluate([0], [0.4])
        self.assertAlmostEqual(metrics["mae"], 0.4, places=12)
        self.assertAlmostEqual(metrics["rmse"], 0.4, places=12)

    def test_empty_window_is_no_disponible(self):
        metrics = mp.evaluate([], [])
        self.assertEqual(metrics["n"], 0)
        self.assertIsNone(metrics["mae"])
        self.assertIsNone(metrics["rmse"])
        self.assertIsNone(metrics["r2"])
        self.assertEqual(metrics["cobertura"], 0.0)

    def test_coverage_counts_abstentions_in_denominator(self):
        metrics = mp.evaluate([1, 2, 3], [1.0, np.nan, 3.0])
        self.assertEqual(metrics["n"], 3)
        self.assertEqual(metrics["n_con_prediccion"], 2)
        self.assertAlmostEqual(metrics["cobertura"], 2 / 3, places=12)
        self.assertEqual(metrics["mae"], 0.0)

    def test_r2_none_when_target_is_constant(self):
        metrics = mp.evaluate([5, 5, 5], [4, 6, 5])
        self.assertIsNone(metrics["r2"])
        self.assertAlmostEqual(metrics["mae"], 2 / 3, places=12)

    def test_size_mismatch_rejected(self):
        with self.assertRaisesRegex(InputError, "tamaños"):
            mp.evaluate([1, 2], [1])

    def test_evaluate_by_groups_aligns_rows(self):
        data = mp.split_xy(mp.split_temporal(official_frame()))["validation"]
        prediction = mp.baseline_predict(data["X"])
        groups = mp.evaluate_by(data["meta"], data["y"], prediction,
                                "locationId")
        self.assertEqual(set(groups), {"5", "6", "7"})
        self.assertEqual(sum(g["n"] for g in groups.values()), 504)


class TestReservedTests(unittest.TestCase):
    """Área 12: TEST existe, está reservado y no se evalúa."""

    @classmethod
    def setUpClass(cls):
        cls.split = mp.split_temporal(official_frame())

    def test_test_partition_exists_and_is_reserved(self):
        test = self.split["test"]
        self.assertEqual(len(test), mp.EXPECTED_SPLIT_COUNTS["test"])
        self.assertEqual(min(test["mes_objetivo"]), "2026-07")
        self.assertEqual(max(test["mes_objetivo"]), "2026-09")

    def test_run_baseline_does_not_evaluate_test(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = Path(temp) / "experiments.csv"
            result = mp.run_baseline(registry_path=registry)
            self.assertFalse(result["test"]["metricas_calculadas"])
            self.assertNotIn("mae", result["test"])
            self.assertNotIn("rmse", result["test"])
            self.assertNotIn("r2", result["test"])
            self.assertEqual(result["test"]["filas"], 504)
            self.assertEqual(result["test"]["meses"],
                             ["2026-07", "2026-08", "2026-09"])
            with registry.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            for column in ("mae_test", "rmse_test", "r2_test"):
                self.assertEqual(rows[0][column], "")

    def test_real_registry_test_fields_only_on_v1_row(self):
        """Tras la evaluación final solo la fila V1 lleva métricas de TEST."""
        self.assertTrue(mp.EXPERIMENTS_PATH.exists(),
                        "falta experiments.csv con la ejecución real")
        with mp.EXPERIMENTS_PATH.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(tuple(reader.fieldnames), mp.EXPERIMENT_COLUMNS)
            rows = list(reader)
        self.assertGreaterEqual(len(rows), 1)
        report = json.loads(
            (mp.REPORTS_DIR / "v1_test_evaluation.json").read_text(
                encoding="utf-8")
        )
        v1_id = report["registry"]["experiment_id"]
        keys = {"mae_test": "mae", "rmse_test": "rmse", "r2_test": "r2"}
        for row in rows:
            for column in ("mae_test", "rmse_test", "r2_test"):
                if row["experiment_id"] == v1_id:
                    self.assertNotEqual(row[column], "")
                    self.assertEqual(float(row[column]),
                                     report["metrics"][keys[column]])
                else:
                    self.assertEqual(row[column], "")


class RegistryMechanicsTests(unittest.TestCase):
    """Registro de experimentos: solo agregado, con contrato de columnas."""

    def test_append_creates_header_and_appends_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "reports" / "experiments.csv"
            mp.append_experiment({"experiment_id": "EXP-1"}, path=path)
            mp.append_experiment({"experiment_id": "EXP-2", "seed": 42},
                                 path=path)
            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(tuple(reader.fieldnames),
                                 mp.EXPERIMENT_COLUMNS)
                rows = list(reader)
            self.assertEqual([r["experiment_id"] for r in rows],
                             ["EXP-1", "EXP-2"])
            self.assertEqual(rows[1]["seed"], "42")
            self.assertEqual(rows[0]["mae_test"], "")

    def test_append_rejects_unknown_column(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "experiments.csv"
            with self.assertRaisesRegex(InputError, "desconocida"):
                mp.append_experiment({"experiment_id": "EXP-1",
                                      "mae_test_falso": "1"}, path=path)

    def test_append_rejects_foreign_header(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "experiments.csv"
            path.write_text("otro,esquema\n1,2\n", encoding="utf-8")
            with self.assertRaisesRegex(InputError, "columnas distintas"):
                mp.append_experiment({"experiment_id": "EXP-1"}, path=path)

    def test_run_baseline_row_matches_computed_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = Path(temp) / "experiments.csv"
            result = mp.run_baseline(registry_path=registry)
            with registry.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            row = rows[0]
            metrics = result["baseline"]["validation"]
            self.assertEqual(row["experiment_id"], result["experiment_id"])
            self.assertEqual(row["model"], mp.BASELINE_MODEL)
            self.assertEqual(float(row["mae_val"]), metrics["mae"])
            self.assertEqual(float(row["rmse_val"]), metrics["rmse"])
            self.assertEqual(float(row["r2_val"]), metrics["r2"])
            self.assertEqual(row["features"], "|".join(mp.FEATURE_COLUMNS))
            self.assertEqual(row["target"], mp.TARGET)
            self.assertEqual(row["seed"], "42")
            self.assertEqual(row["dataset_version"], "1.1.0-escenarios")
            self.assertEqual(len(row["dataset_hash"]), 64)
            self.assertEqual(row["train_range"], "2025-01..2026-03")
            self.assertEqual(row["validation_range"], "2026-04..2026-06")
            self.assertEqual(row["test_range"], "2026-07..2026-09")


class DatasetIntegrityTests(unittest.TestCase):
    """Área 13: el dataset oficial queda intacto tras usar el pipeline."""

    def test_dataset_files_match_manifest_hashes(self):
        for name, expected in MANIFEST["hashes"].items():
            with self.subTest(name=name):
                raw = (DATA / name).read_bytes()
                self.assertEqual(content_sha256(raw), expected)
        catalog = (HERE / "catalog_reference.json").read_bytes()
        self.assertEqual(content_sha256(catalog),
                         MANIFEST["catalog_snapshot_hash"])
        generator = (HERE / "generate_synthetic.py").read_bytes()
        self.assertEqual(content_sha256(generator),
                         MANIFEST["generator_hash"])

    def test_tampered_dataset_copy_is_rejected_by_hash(self):
        official = MANIFEST["hashes"]["dataset_supervisado.csv"]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dataset_supervisado.csv"
            path.write_bytes((DATA / "dataset_supervisado.csv").read_bytes()
                             + b"\n")
            with self.assertRaisesRegex(InputError, "huella"):
                mp.load_supervised(path, expected_hash=official)

    def test_official_dataset_path_unchanged_after_pipeline(self):
        before = content_sha256((DATA / "dataset_supervisado.csv").read_bytes())
        mp.load_supervised()
        mp.split_temporal(official_frame())
        after = content_sha256((DATA / "dataset_supervisado.csv").read_bytes())
        self.assertEqual(before, after)
        self.assertEqual(after, MANIFEST["hashes"]["dataset_supervisado.csv"])


class StandardizerTests(unittest.TestCase):
    """Transformaciones ajustadas únicamente con la tabla de entrenamiento."""

    def test_fit_uses_only_the_given_table(self):
        columns = list(mp.FEATURE_COLUMNS)
        X_train = pd.DataFrame([[0.0, 2.0, 4.0, 0.0, 1.0],
                                [2.0, 4.0, 6.0, 1.0, 0.0]],
                               columns=columns)
        X_val = pd.DataFrame([[10.0, 20.0, 30.0, 0.5, 0.5]],
                             columns=columns)
        scaler = mp.TrainStandardizer().fit(X_train)
        transformed = scaler.transform(X_val)
        # La media de TRAIN para la primera feature es 1.0, no 10.0.
        self.assertAlmostEqual(scaler.mean_.iloc[0], 1.0, places=12)
        self.assertAlmostEqual(transformed.iloc[0, 0], (10.0 - 1.0) / 1.0,
                               places=12)

    def test_transform_before_fit_rejected(self):
        columns = list(mp.FEATURE_COLUMNS)
        scaler = mp.TrainStandardizer()
        with self.assertRaisesRegex(InputError, "NO AJUSTADO"):
            scaler.transform(pd.DataFrame([[0.0] * 5], columns=columns))

    def test_fit_rejects_wrong_columns(self):
        with self.assertRaisesRegex(InputError, "cinco features"):
            mp.TrainStandardizer().fit(pd.DataFrame({"otra": [1.0]}))


class RunBaselineEndToEndTests(unittest.TestCase):
    """Ejecución real del baseline con desgloses por grupos de VALIDATION."""

    def test_run_baseline_returns_validation_metrics_and_groups(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = Path(temp) / "experiments.csv"
            result = mp.run_baseline(registry_path=registry)
        metrics = result["baseline"]["validation"]
        self.assertEqual(metrics["n"], 504)
        self.assertEqual(metrics["n_con_prediccion"], 504)
        self.assertEqual(metrics["cobertura"], 1.0)
        self.assertIsNotNone(metrics["mae"])
        self.assertIsNotNone(metrics["rmse"])
        self.assertIsNotNone(metrics["r2"])
        self.assertEqual(set(result["desglose_validation"]["por_tienda"]),
                         {"5", "6", "7"})
        self.assertEqual(
            set(result["desglose_validation"]["por_rotacion"]),
            {"ALTA", "MEDIA", "BAJA"},
        )
        self.assertEqual(
            set(result["desglose_validation"]["por_mes"]),
            {"2026-04", "2026-05", "2026-06"},
        )
        self.assertEqual(result["filas"]["total"], 3528)
        self.assertEqual(result["dataset_version"], "1.1.0-escenarios")


if __name__ == "__main__":
    unittest.main()
