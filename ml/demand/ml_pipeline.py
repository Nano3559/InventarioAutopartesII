"""Preparación reproducible del dataset supervisado 1.1 y baseline de último mes.

Valida el contrato de nueve columnas, construye X/y sin fuga temporal, separa
TRAIN/VALIDATION/TEST por mes calendario y evalúa el baseline lag1 sobre
VALIDATION. No entrena modelos supervisados ni calcula métricas de TEST.
"""
import csv
import io
import json
import math
import platform
import re
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from simulator_inputs import (
    FEATURE_NAMES, HERE, InputError, offset_month, parse_month,
    read_required, verified_bytes,
)

DATA_DIR = HERE / "data" / "escenarios_v1_1"
DATASET_PATH = DATA_DIR / "dataset_supervisado.csv"
METADATA_PATH = DATA_DIR / "escenarios_metadatos.csv"
REPORTS_DIR = HERE / "reports"
EXPERIMENTS_PATH = REPORTS_DIR / "experiments.csv"

TARGET = "target_ventas_mes"
ID_COLUMNS = ("productId", "locationId", "mes_objetivo")
DATASET_COLUMNS = (
    "mes_objetivo", "productId", "locationId",
    "ventas_mes_anterior", "ventas_hace_2_meses", "ventas_hace_3_meses",
    "mes_sin", "mes_cos", "target_ventas_mes",
)
FEATURE_COLUMNS = tuple(FEATURE_NAMES)
QUANTITY_COLUMNS = (
    "ventas_mes_anterior", "ventas_hace_2_meses", "ventas_hace_3_meses",
    TARGET,
)
CALENDAR_COLUMNS = ("mes_sin", "mes_cos")

MIN_MONTH = "2025-01"
MAX_MONTH = "2026-09"
SPLIT_RANGES = {
    "train": ("2025-01", "2026-03"),
    "validation": ("2026-04", "2026-06"),
    "test": ("2026-07", "2026-09"),
}
EXPECTED_SPLIT_COUNTS = {"train": 2520, "validation": 504, "test": 504}
EXPECTED_TOTAL_ROWS = 3528
EXPECTED_TARGET_ZEROS = 422
LAG_COLUMNS = {"ventas_mes_anterior": 1, "ventas_hace_2_meses": 2,
               "ventas_hace_3_meses": 3}
MAX_INT64 = 2**63 - 1

EXPERIMENT_COLUMNS = (
    "experiment_id", "timestamp", "dataset_version", "dataset_hash",
    "catalog_hash", "generator_version", "seed", "features", "target",
    "train_range", "validation_range", "test_range", "model", "parameters",
    "preprocessing", "mae_val", "rmse_val", "r2_val", "mae_test",
    "rmse_test", "r2_test", "training_seconds", "tool_versions",
    "artifact_path", "notes",
)
BASELINE_MODEL = "BASELINE_LAG1"


def month_index(value):
    """Índero calendario comparable de un mes YYYY-MM."""
    year, month = parse_month(value)
    return year * 12 + month


def official_manifest():
    return json.loads(
        read_required(DATA_DIR / "manifest.json", "manifest.json")
        .decode("utf-8")
    )


@lru_cache(maxsize=1)
def _catalog_ids():
    """Conjuntos de IDs del catálogo oficial, con huella verificada."""
    manifest = official_manifest()
    catalog_bytes = verified_bytes(
        HERE / "catalog_reference.json", manifest["catalog_snapshot_hash"],
        "catalog_reference.json",
    )
    catalog = json.loads(catalog_bytes.decode("utf-8"))
    included = set(catalog["included_product_ids"])
    products = frozenset(
        row["id"] for row in catalog["products"] if row["id"] in included
    )
    stores = frozenset(
        row["id"] for row in catalog["locations"] if row["type"] == "TIENDA"
    )
    if not products or not stores:
        raise InputError("REFERENCIA NO VÁLIDA: catálogo incompleto.")
    return products, stores


@lru_cache(maxsize=1)
def _official_reference():
    from simulator_inputs import load_reference
    return load_reference()


def _require_int(value, column):
    if isinstance(value, (bool, np.bool_)):
        raise InputError(
            f"DATASET INVÁLIDO: {column} debe contener enteros no negativos."
        )
    if isinstance(value, (int, np.integer)):
        number = int(value)
    elif isinstance(value, str):
        text = value.strip()
        if not re.fullmatch(r"[0-9]+", text):
            raise InputError(
                f"DATASET INVÁLIDO: {column} debe contener enteros no negativos."
            )
        number = int(text)
    elif isinstance(value, (float, np.floating)):
        finite = float(value)
        if not math.isfinite(finite) or not finite.is_integer():
            raise InputError(
                f"DATASET INVÁLIDO: {column} debe contener enteros no negativos."
            )
        number = int(finite)
    else:
        raise InputError(
            f"DATASET INVÁLIDO: {column} debe contener enteros no negativos."
        )
    if number < 0:
        raise InputError(
            f"DATASET INVÁLIDO: {column} debe contener enteros no negativos."
        )
    if number > MAX_INT64:
        raise InputError(
            f"DATASET INVÁLIDO: {column} fuera del rango entero no negativo."
        )
    return number


def _require_calendar(value, column):
    if isinstance(value, (bool, np.bool_)):
        raise InputError(
            f"DATASET INVÁLIDO: {column} debe ser un número finito en [-1, 1]."
        )
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InputError(
            f"DATASET INVÁLIDO: {column} debe ser un número finito en [-1, 1]."
        ) from exc
    if not math.isfinite(number) or not -1.0 - 1e-9 <= number <= 1.0 + 1e-9:
        raise InputError(
            f"DATASET INVÁLIDO: {column} debe ser un número finito en [-1, 1]."
        )
    return number


def validate_frame(frame):
    """Valida el contrato de nueve columnas y devuelve la tabla tipada.

    Rechaza columnas faltantes o extra, meses fuera de la ventana supervisada,
    cantidades no enteras, negativas o no finitas, calendario fuera de rango,
    IDs fuera del catálogo y claves duplicadas. Los ceros válidos se conservan.
    """
    if not isinstance(frame, pd.DataFrame):
        raise InputError("DATASET INVÁLIDO: se esperaba una tabla.")
    columns = list(frame.columns)
    if len(columns) != len(set(columns)):
        raise InputError("DATASET INVÁLIDO: columna repetida en el contrato.")
    if set(columns) != set(DATASET_COLUMNS):
        raise InputError(
            "DATASET INVÁLIDO: se requieren exactamente las columnas "
            f"{', '.join(DATASET_COLUMNS)}."
        )
    out = frame.loc[:, list(DATASET_COLUMNS)].copy()

    for value in out["mes_objetivo"].tolist():
        if not isinstance(value, str):
            raise InputError(
                "DATASET INVÁLIDO: mes_objetivo debe ser texto YYYY-MM."
            )
        parse_month(value)
        index = month_index(value)
        if not month_index(MIN_MONTH) <= index <= month_index(MAX_MONTH):
            raise InputError(
                f"DATASET INVÁLIDO: mes_objetivo {value} fuera de la ventana "
                f"supervisada {MIN_MONTH}..{MAX_MONTH}."
            )
    out["mes_objetivo"] = out["mes_objetivo"].astype(str)

    for column in ("productId", "locationId"):
        out[column] = [
            _require_int(value, column) for value in out[column].tolist()
        ]
    for column in QUANTITY_COLUMNS:
        out[column] = [
            _require_int(value, column) for value in out[column].tolist()
        ]
    for column in CALENDAR_COLUMNS:
        out[column] = [
            _require_calendar(value, column) for value in out[column].tolist()
        ]

    if out.duplicated(subset=["productId", "locationId", "mes_objetivo"]).any():
        raise InputError(
            "DATASET INVÁLIDO: fila duplicada de producto, tienda y mes."
        )

    products, stores = _catalog_ids()
    bad_product = sorted(set(out["productId"]) - products)
    if bad_product:
        raise InputError(
            f"DATASET INVÁLIDO: productId {bad_product[0]} fuera del catálogo."
        )
    bad_store = sorted(set(out["locationId"]) - stores)
    if bad_store:
        raise InputError(
            f"DATASET INVÁLIDO: locationId {bad_store[0]} fuera del catálogo."
        )

    for column in ("productId", "locationId", *QUANTITY_COLUMNS):
        out[column] = out[column].astype("int64")
    return out.reset_index(drop=True)


def load_supervised(path=DATASET_PATH, expected_hash=None):
    """Lee el CSV supervisado como texto y aplica el contrato completo."""
    if expected_hash is not None:
        verified_bytes(path, expected_hash, Path(path).name)
    try:
        raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    except FileNotFoundError as exc:
        raise InputError(
            f"REFERENCIA NO VÁLIDA: falta el archivo {Path(path).name}."
        ) from exc
    except OSError as exc:
        raise InputError(
            f"REFERENCIA NO VÁLIDA: no se puede leer {Path(path).name}."
        ) from exc
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise InputError(
            f"DATASET INVÁLIDO: CSV ilegible en {Path(path).name}."
        ) from exc
    return validate_frame(raw)


def split_temporal(frame):
    """Separa TRAIN/VALIDATION/TEST por mes calendario, sin solapamientos."""
    table = validate_frame(frame)
    index = pd.Series(
        [month_index(m) for m in table["mes_objetivo"]],
        index=table.index, dtype="int64",
    )
    parts = {}
    assigned = pd.Series(False, index=table.index)
    for name, (start, end) in SPLIT_RANGES.items():
        mask = (
            (index >= month_index(start)) & (index <= month_index(end))
        )
        parts[name] = table[mask].sort_values(
            ["mes_objetivo", "productId", "locationId"]
        ).reset_index(drop=True)
        assigned |= mask
    if not bool(assigned.all()):
        outside = sorted(set(table.loc[~assigned, "mes_objetivo"]))
        raise InputError(
            "DATASET INVÁLIDO: meses fuera de los rangos "
            f"TRAIN/VALIDATION/TEST: {', '.join(outside)}."
        )
    if any(len(part) == 0 for part in parts.values()):
        raise InputError("DATASET INVÁLIDO: falta una partición del split.")
    return parts


def verify_split_counts(split, expected=None):
    """Comprueba los conteos oficiales de cada partición."""
    expected = EXPECTED_SPLIT_COUNTS if expected is None else expected
    counts = {name: int(len(part)) for name, part in split.items()}
    for name, wanted in expected.items():
        if counts.get(name) != wanted:
            raise InputError(
                f"DATASET INVÁLIDO: se esperaban {wanted} filas en {name} "
                f"y hay {counts.get(name)}."
            )
    return counts


def build_xy(frame):
    """Construye X con las cinco features en orden y y con el target.

    productId, locationId y mes_objetivo quedan fuera de X; el target tampoco
    forma parte de las entradas.
    """
    missing = [c for c in FEATURE_COLUMNS if c not in frame.columns]
    if missing or TARGET not in frame.columns:
        raise InputError(
            f"DATASET INVÁLIDO: faltan columnas para construir X/y: "
            f"{', '.join(missing or [TARGET])}."
        )
    X = frame.loc[:, list(FEATURE_COLUMNS)].copy()
    forbidden = set(ID_COLUMNS) | {TARGET}
    repeated = forbidden & set(X.columns)
    if repeated:
        raise InputError(
            "DATASET INVÁLIDO: identificadores o target no pueden entrar en X."
        )
    y = frame[TARGET].copy()
    return X, y


def build_meta(frame):
    """Metadatos de selección y análisis, nunca usados como features."""
    missing = [c for c in ID_COLUMNS if c not in frame.columns]
    if missing:
        raise InputError(
            f"DATASET INVÁLIDO: faltan metadatos: {', '.join(missing)}."
        )
    return frame.loc[:, list(ID_COLUMNS)].copy()


def split_xy(split):
    """Empareja X, y y metadatos por partición con índices alineados."""
    out = {}
    for name, part in split.items():
        frame = part.reset_index(drop=True)
        X, y = build_xy(frame)
        out[name] = {"X": X, "y": y, "meta": build_meta(frame), "frame": frame}
    return out


class TrainStandardizer:
    """Escalado z ajustado exclusivamente con la tabla que se le pase a fit.

    El pipeline de entrenamiento lo ajusta solo con TRAIN; el baseline no lo
    utiliza. transform exige un fit previo.
    """

    def fit(self, X):
        if not isinstance(X, pd.DataFrame) or list(X.columns) != list(
            FEATURE_COLUMNS
        ):
            raise InputError(
                "PREPROCESAMIENTO INVÁLIDO: se esperaban las cinco features."
            )
        self.mean_ = X.astype("float64").mean(axis=0)
        scale = X.astype("float64").std(axis=0, ddof=0)
        self.scale_ = scale.where(scale != 0, 1.0)
        return self

    def transform(self, X):
        if not hasattr(self, "mean_"):
            raise InputError(
                "PREPROCESAMIENTO NO AJUSTADO: fit usa exclusivamente TRAIN."
            )
        if not isinstance(X, pd.DataFrame) or list(X.columns) != list(
            FEATURE_COLUMNS
        ):
            raise InputError(
                "PREPROCESAMIENTO INVÁLIDO: se esperaban las cinco features."
            )
        return (X.astype("float64") - self.mean_) / self.scale_


def baseline_predict(X):
    """Predicción baseline: el último mes observado (lag1), sin recortes."""
    if "ventas_mes_anterior" not in X.columns:
        raise InputError(
            "BASELINE INVÁLIDO: falta la feature ventas_mes_anterior."
        )
    return X["ventas_mes_anterior"].astype("float64").reset_index(drop=True)


def evaluate(y_true, y_pred):
    """MAE, RMSE, R², n y cobertura sin redondear predicciones.

    Sin casos con predicción finita las métricas quedan en None (NO
    DISPONIBLE). La cobertura usa todos los casos del denominador.
    """
    true = np.asarray(y_true, dtype="float64").ravel()
    pred = np.asarray(y_pred, dtype="float64").ravel()
    if true.shape != pred.shape:
        raise InputError("MÉTRICAS INVÁLIDAS: tamaños distintos.")
    total = int(true.size)
    usable = np.isfinite(pred) & np.isfinite(true)
    with_prediction = int(usable.sum())
    coverage = (with_prediction / total) if total else 0.0
    if total == 0 or with_prediction == 0:
        return {
            "n": total, "n_con_prediccion": with_prediction, "mae": None,
            "rmse": None, "r2": None, "cobertura": coverage,
        }
    errors = pred[usable] - true[usable]
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    observed = true[usable]
    ss_tot = float(np.sum(np.square(observed - observed.mean())))
    r2 = None
    if with_prediction >= 2 and ss_tot > 0:
        r2 = float(1.0 - float(np.sum(np.square(errors))) / ss_tot)
    return {
        "n": total, "n_con_prediccion": with_prediction, "mae": mae,
        "rmse": rmse, "r2": r2, "cobertura": coverage,
    }


def evaluate_by(frame, y_true, y_pred, column):
    """Métricas por grupo alineadas fila a fila con frame."""
    if column not in frame.columns:
        raise InputError(f"MÉTRICAS INVÁLIDAS: falta la columna {column}.")
    true = np.asarray(y_true, dtype="float64").ravel()
    pred = np.asarray(y_pred, dtype="float64").ravel()
    if len(frame) != true.size or len(frame) != pred.size:
        raise InputError(
            "MÉTRICAS INVÁLIDAS: el grupo no está alineado con las salidas."
        )
    groups = {}
    for value, positions in frame.groupby(column, sort=True).indices.items():
        groups[str(value)] = evaluate(true[positions], pred[positions])
    return groups


@lru_cache(maxsize=1)
def _rotation_map():
    """Mapa de rotación de diagnóstico por producto, tienda y mes."""
    manifest = official_manifest()
    data = verified_bytes(
        METADATA_PATH, manifest["hashes"]["escenarios_metadatos.csv"],
        "escenarios_metadatos.csv",
    )
    meta = pd.read_csv(io.BytesIO(data))
    required = {"mes", "productId", "locationId", "rotacion_simulada"}
    if not required <= set(meta.columns):
        raise InputError(
            "DATASET INVÁLIDO: escenarios_metadatos.csv incompleto."
        )
    for month in sorted(set(meta["mes"])):
        parse_month(month)
    return {
        (int(row.productId), int(row.locationId), str(row.mes)): str(
            row.rotacion_simulada
        )
        for row in meta.itertuples(index=False)
    }


def rotation_labels(meta):
    """Etiquetas de rotación como metadato de diagnóstico, nunca feature."""
    mapping = _rotation_map()
    return pd.Series(
        [
            mapping.get(
                (int(product), int(store), str(month)), "SIN DATO"
            )
            for product, store, month in zip(
                meta["productId"], meta["locationId"], meta["mes_objetivo"]
            )
        ],
        index=meta.index, name="rotacion_diagnostico",
    )


def check_no_leakage(frame, reference=None):
    """Compara lags y target con la historia oficial y el calendario con el mes.

    Devuelve conteos de inconsistencia; cero indica ausencia de fuga temporal.
    """
    if reference is None:
        reference = _official_reference()
    history = reference.history
    counts = {"lag_vs_historia": 0, "target_vs_historia": 0,
              "calendario": 0}
    for row in frame.itertuples(index=False):
        product = int(row.productId)
        store = int(row.locationId)
        month = str(row.mes_objetivo)
        year, month_number = parse_month(month)
        angle = 2 * math.pi * (month_number - 1) / 12
        if (
            abs(float(row.mes_sin) - round(math.sin(angle), 12)) > 1e-12
            or abs(float(row.mes_cos) - round(math.cos(angle), 12)) > 1e-12
        ):
            counts["calendario"] += 1
        for column, lag in LAG_COLUMNS.items():
            expected = history.get(
                (product, store, offset_month(month, -lag))
            )
            if expected is None or int(getattr(row, column)) != expected:
                counts["lag_vs_historia"] += 1
        expected_target = history.get((product, store, month))
        if expected_target is None or int(row.target_ventas_mes) != (
            expected_target
        ):
            counts["target_vs_historia"] += 1
    return counts


def assert_no_leakage(frame, reference=None):
    """Eleva InputError si el dataset presenta cualquier inconsistencia."""
    counts = check_no_leakage(frame, reference)
    if any(counts.values()):
        raise InputError(
            "DATASET INVÁLIDO: inconsistencia temporal o de calendario "
            f"{counts}."
        )
    return counts


def _format_value(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return repr(value)
    return str(value)


def append_experiment(row, path=EXPERIMENTS_PATH):
    """Agrega una ejecución al registro. Solo agrega; nunca sobrescribe."""
    unknown = set(row) - set(EXPERIMENT_COLUMNS)
    if unknown:
        raise InputError(
            f"REGISTRO INVÁLIDO: columna desconocida {sorted(unknown)[0]}."
        )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    if exists:
        with path.open("r", encoding="utf-8", newline="") as handle:
            header = handle.readline().rstrip("\r\n")
        if header != ",".join(EXPERIMENT_COLUMNS):
            raise InputError(
                "REGISTRO INVÁLIDO: experiments.csv con columnas distintas "
                "al contrato."
            )
    with path.open("a" if exists else "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        if not exists:
            writer.writerow(EXPERIMENT_COLUMNS)
        writer.writerow(
            [_format_value(row.get(column, "")) for column in EXPERIMENT_COLUMNS]
        )
    return path


def run_baseline(dataset_path=DATASET_PATH, registry_path=EXPERIMENTS_PATH,
                 expected_hash=None):
    """Evalúa el baseline lag1 sobre VALIDATION y registra la ejecución.

    Verifica la huella oficial, valida el contrato, confirma la ausencia de
    fuga temporal, comprueba el split y sus conteos, calcula métricas y
    desgloses solo en VALIDATION, y deja TEST reservado sin métricas.
    """
    started = time.perf_counter()
    manifest = official_manifest()
    if expected_hash is None and Path(dataset_path) == DATASET_PATH:
        expected_hash = manifest["hashes"]["dataset_supervisado.csv"]
    frame = load_supervised(dataset_path, expected_hash=expected_hash)
    split = split_temporal(frame)
    counts = verify_split_counts(split)
    assert_no_leakage(frame)

    validation = split_xy(split)["validation"]
    prediction = baseline_predict(validation["X"])
    metrics = evaluate(validation["y"], prediction)
    groups_frame = validation["meta"].assign(
        rotacion_diagnostico=rotation_labels(validation["meta"])
    )
    groups = {
        "por_tienda": evaluate_by(
            validation["meta"], validation["y"], prediction, "locationId"
        ),
        "por_rotacion": evaluate_by(
            groups_frame, validation["y"], prediction,
            "rotacion_diagnostico",
        ),
        "por_mes": evaluate_by(
            validation["meta"], validation["y"], prediction, "mes_objetivo"
        ),
    }
    elapsed = time.perf_counter() - started

    now = datetime.now(timezone.utc)
    experiment_id = f"EXP-{BASELINE_MODEL}-{now.strftime('%Y%m%dT%H%M%S%fZ')}"
    ranges = {
        name: f"{start}..{end}" for name, (start, end) in SPLIT_RANGES.items()
    }
    row = {
        "experiment_id": experiment_id,
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_version": manifest["dataset_version"],
        "dataset_hash": manifest["hashes"]["dataset_supervisado.csv"],
        "catalog_hash": manifest["catalog_snapshot_hash"],
        "generator_version": manifest["generator_version"],
        "seed": manifest["seed"],
        "features": "|".join(FEATURE_COLUMNS),
        "target": TARGET,
        "train_range": ranges["train"],
        "validation_range": ranges["validation"],
        "test_range": ranges["test"],
        "model": BASELINE_MODEL,
        "parameters": "prediccion=ventas_mes_anterior",
        "preprocessing": "ninguno (baseline sin transformaciones)",
        "mae_val": metrics["mae"],
        "rmse_val": metrics["rmse"],
        "r2_val": metrics["r2"],
        "mae_test": None,
        "rmse_test": None,
        "r2_test": None,
        "training_seconds": elapsed,
        "tool_versions": (
            f"python {platform.python_version()}; pandas {pd.__version__}; "
            f"numpy {np.__version__}"
        ),
        "artifact_path": "SIN_ARTEFACTO",
        "notes": (
            "Baseline lag1 sobre VALIDATION; cobertura "
            f"{metrics['cobertura']:.6f}; desgloses por tienda, rotación y "
            "mes en la ejecución; TEST reservado sin métricas."
        ),
    }
    append_experiment(row, path=registry_path)
    test_months = sorted(set(split["test"]["mes_objetivo"]))
    return {
        "experiment_id": experiment_id,
        "dataset_version": manifest["dataset_version"],
        "filas": {"total": int(len(frame)), **counts},
        "meses": {
            name: {
                "inicio": SPLIT_RANGES[name][0],
                "fin": SPLIT_RANGES[name][1],
            }
            for name in SPLIT_RANGES
        },
        "baseline": {"modelo": BASELINE_MODEL, "validation": metrics},
        "desglose_validation": groups,
        "test": {
            "filas": int(len(split["test"])),
            "meses": test_months,
            "metricas_calculadas": False,
        },
        "registro": str(Path(registry_path)),
        "training_seconds": elapsed,
    }


if __name__ == "__main__":
    print(json.dumps(run_baseline(), ensure_ascii=False, indent=2))
