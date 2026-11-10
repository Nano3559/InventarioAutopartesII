"""Entrenamiento reproducible de RandomForestRegressor con TRAIN (H4 tarea 8).

Búsqueda pequeña y explícita de hiperparámetros (16 configuraciones) con
validación temporal interna dentro de TRAIN: ajuste 2025-01..2025-12 y
evaluación 2026-01..2026-03. Reentreno final sobre TRAIN completo con
random_state=42 y evaluación única en VALIDATION. No usa TEST ni selecciona
V1. Sin estandarización: los árboles no la requieren y el contrato de
inferencia usa las cinco features crudas en orden oficial.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

import ml_pipeline as mp
import train_linear_regression as tlr
from simulator_inputs import HERE, InputError

MODEL_NAME = "RANDOMFOREST"
ARTIFACT_SCHEMA = "h4-random-forest-1"
MODELS_DIR = HERE / "models"
DEFAULT_ARTIFACT_PATH = MODELS_DIR / "random_forest_candidate.joblib"
LR_ARTIFACT_PATH = MODELS_DIR / "linear_regression_candidate.joblib"
RANDOM_STATE = 42
PREPROCESSING_TEXT = (
    "ninguno (RandomForest sin estandarización; cinco features crudas en "
    "orden oficial)"
)
INTERNAL_ADJUST_RANGE = ("2025-01", "2025-12")
INTERNAL_EVAL_RANGE = ("2026-01", "2026-03")
ALLOWED_HYPERPARAMETERS = frozenset(
    ("n_estimators", "max_depth", "min_samples_leaf", "max_features")
)
GRID = tuple(
    {"n_estimators": n_estimators, "max_depth": max_depth,
     "min_samples_leaf": min_samples_leaf, "max_features": max_features}
    for n_estimators in (100, 200)
    for max_depth in (None, 8)
    for min_samples_leaf in (1, 3)
    for max_features in ("sqrt", 1.0)
)
SELECTION_CRITERION = (
    "menor MAE en la validación interna; empate por menor RMSE; luego el "
    "orden del grid"
)


def internal_temporal_split(train_frame):
    """Divide TRAIN en ajuste interno y validación interna, sin solape."""
    if not isinstance(train_frame, pd.DataFrame) or (
        "mes_objetivo" not in train_frame.columns
    ):
        raise InputError("DATASET INVÁLIDO: se esperaba el marco de TRAIN.")
    allowed = set(range(
        mp.month_index(mp.SPLIT_RANGES["train"][0]),
        mp.month_index(mp.SPLIT_RANGES["train"][1]) + 1,
    ))
    used = {mp.month_index(month)
            for month in set(train_frame["mes_objetivo"])}
    if not used <= allowed:
        raise InputError(
            "ENTRENAMIENTO INVÁLIDO: el marco contiene meses fuera de TRAIN."
        )
    index = pd.Series(
        [mp.month_index(month) for month in train_frame["mes_objetivo"]],
        index=train_frame.index, dtype="int64",
    )
    adjust_mask = index <= mp.month_index(INTERNAL_ADJUST_RANGE[1])
    eval_mask = index >= mp.month_index(INTERNAL_EVAL_RANGE[0])
    if bool((adjust_mask & eval_mask).any()):
        raise InputError(
            "VALIDACIÓN INTERNA INVÁLIDA: solape entre ajuste y evaluación."
        )
    order = ["mes_objetivo", "productId", "locationId"]
    adjust = train_frame[adjust_mask].sort_values(order).reset_index(drop=True)
    evaluation = train_frame[eval_mask].sort_values(order).reset_index(
        drop=True
    )
    if len(adjust) == 0 or len(evaluation) == 0:
        raise InputError(
            "VALIDACIÓN INTERNA INCOMPLETA: faltan meses de ajuste o "
            "evaluación."
        )
    return adjust, evaluation


def fit_model(parameters, X, y):
    """Ajusta el bosque con random_state=42; sin estandarización."""
    unknown = set(parameters) - ALLOWED_HYPERPARAMETERS
    if unknown:
        raise InputError(
            f"HIPERPARÁMETRO NO PERMITIDO: {sorted(unknown)[0]}."
        )
    model = RandomForestRegressor(
        **parameters, random_state=RANDOM_STATE, n_jobs=1
    )
    model.fit(X, y)
    return model


def predict(model, X):
    """Inferencia con las cinco features crudas en orden oficial, sin recortes."""
    if list(X.columns) != list(mp.FEATURE_COLUMNS):
        raise InputError(
            "MODELO INVÁLIDO: se esperaban las cinco features en orden "
            "oficial."
        )
    return np.asarray(model.predict(X), dtype="float64")


def train_candidate(train_frame):
    """Búsqueda interna y reentreno final. Recibe exclusivamente TRAIN."""
    adjust, evaluation = internal_temporal_split(train_frame)
    X_adjust, y_adjust = mp.build_xy(adjust)
    X_eval, y_eval = mp.build_xy(evaluation)
    grid_results = []
    search_started = time.perf_counter()
    for parameters in GRID:
        model = fit_model(parameters, X_adjust, y_adjust)
        metrics = mp.evaluate(y_eval, predict(model, X_eval))
        if metrics["mae"] is None:
            raise InputError(
                "VALIDACIÓN INTERNA SIN MÉTRICAS: la evaluación no produjo "
                "casos comparables."
            )
        grid_results.append({
            "parameters": dict(parameters),
            "internal_validation": metrics,
        })
    search_seconds = time.perf_counter() - search_started
    best = min(
        grid_results,
        key=lambda entry: (
            entry["internal_validation"]["mae"],
            entry["internal_validation"]["rmse"],
        ),
    )
    X_train, y_train = mp.build_xy(train_frame)
    fit_started = time.perf_counter()
    final_model = fit_model(best["parameters"], X_train, y_train)
    fit_seconds = time.perf_counter() - fit_started
    return {
        "model": final_model,
        "best_parameters": dict(best["parameters"]),
        "grid_results": grid_results,
        "best_internal_metrics": best["internal_validation"],
        "internal_adjust_rows": int(len(adjust)),
        "internal_eval_rows": int(len(evaluation)),
        "internal_adjust_months": sorted(set(adjust["mes_objetivo"])),
        "internal_eval_months": sorted(set(evaluation["mes_objetivo"])),
        "search_seconds": search_seconds,
        "fit_seconds": fit_seconds,
        "n_train": int(len(train_frame)),
        "train_months": sorted(set(train_frame["mes_objetivo"])),
    }


def evaluate_validation(model, validation_frame):
    """Métricas, desgloses y predicciones sobre un marco de evaluación."""
    X_val, y_val = mp.build_xy(validation_frame)
    prediction = predict(model, X_val)
    meta = mp.build_meta(validation_frame)
    return {
        "metrics": mp.evaluate(y_val, prediction),
        "predicciones": prediction,
        "observados": np.asarray(y_val, dtype="float64"),
        "grupos": {
            "por_tienda": mp.evaluate_by(
                meta, y_val, prediction, "locationId"
            ),
            "por_rotacion": mp.evaluate_by(
                meta.assign(rotacion_diagnostico=mp.rotation_labels(meta)),
                y_val, prediction, "rotacion_diagnostico",
            ),
            "por_mes": mp.evaluate_by(
                meta, y_val, prediction, "mes_objetivo"
            ),
        },
        "negativas": int((prediction < 0).sum()),
    }


def compare_models(validation_frame, rf_prediction):
    """Comparación justa de baseline, LinearRegression y RF en VALIDATION."""
    X_val, y_val = mp.build_xy(validation_frame)
    lr_payload = tlr.load_artifact(LR_ARTIFACT_PATH)
    baseline_metrics = mp.evaluate(y_val, mp.baseline_predict(X_val))
    lr_metrics = mp.evaluate(
        y_val, tlr.predict(lr_payload["scaler"], lr_payload["estimator"], X_val)
    )
    rf_metrics = mp.evaluate(y_val, rf_prediction)
    return {
        "baseline": baseline_metrics,
        "linear_regression": lr_metrics,
        "random_forest": rf_metrics,
        "diferencia_rf_menos": {
            "baseline": {
                key: rf_metrics[key] - baseline_metrics[key]
                for key in ("mae", "rmse", "r2")
            },
            "linear_regression": {
                key: rf_metrics[key] - lr_metrics[key]
                for key in ("mae", "rmse", "r2")
            },
        },
    }


def build_artifact(candidate, manifest):
    """Conjunto reproducible del CANDIDATE: modelo, búsqueda y metadatos."""
    model = candidate["model"]
    importances = {
        name: float(value)
        for name, value in zip(mp.FEATURE_COLUMNS, model.feature_importances_)
    }
    return {
        "schema": ARTIFACT_SCHEMA,
        "model": MODEL_NAME,
        "role": "CANDIDATE",
        "feature_names": list(mp.FEATURE_COLUMNS),
        "target": mp.TARGET,
        "train_range": (
            f"{mp.SPLIT_RANGES['train'][0]}..{mp.SPLIT_RANGES['train'][1]}"
        ),
        "trained_through": mp.SPLIT_RANGES["train"][1],
        "dataset_version": manifest["dataset_version"],
        "dataset_hash": manifest["hashes"]["dataset_supervisado.csv"],
        "catalog_hash": manifest["catalog_snapshot_hash"],
        "seed": manifest["seed"],
        "preprocessing": PREPROCESSING_TEXT,
        "parameters": {
            **candidate["best_parameters"],
            "random_state": RANDOM_STATE,
            "n_jobs": 1,
        },
        "hyperparameter_search": {
            "grid": [dict(entry) for entry in GRID],
            "criterion": SELECTION_CRITERION,
            "internal_split": (
                "TRAIN ajuste "
                f"{INTERNAL_ADJUST_RANGE[0]}..{INTERNAL_ADJUST_RANGE[1]}; "
                f"evaluación {INTERNAL_EVAL_RANGE[0]}.."
                f"{INTERNAL_EVAL_RANGE[1]}"
            ),
            "results": candidate["grid_results"],
            "best_internal_metrics": candidate["best_internal_metrics"],
        },
        "feature_importances": importances,
        "versions": tlr.tool_versions(),
        "created_utc": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "scaler": None,
        "estimator": model,
    }


def predict_from_artifact(artifact, X):
    """Inferencia desde el artefacto guardado, con contrato de features."""
    if not isinstance(artifact, dict) or artifact.get("schema") != (
        ARTIFACT_SCHEMA
    ):
        raise InputError("ARTEFACTO INVÁLIDO: esquema no reconocido.")
    if artifact.get("feature_names") != list(X.columns):
        raise InputError(
            "ARTEFACTO INVÁLIDO: se esperaban las cinco features en orden "
            "oficial."
        )
    return predict(artifact["estimator"], X)


def _artifact_path_text(path):
    try:
        return str(Path(path).resolve().relative_to(HERE.parent.parent))
    except ValueError:
        return str(path)


def run_experiment(dataset_path=mp.DATASET_PATH,
                   registry_path=mp.EXPERIMENTS_PATH,
                   artifact_path=DEFAULT_ARTIFACT_PATH, expected_hash=None):
    """Entrena el CANDIDATE con TRAIN, evalúa VALIDATION y registra."""
    started = time.perf_counter()
    manifest = mp.official_manifest()
    if expected_hash is None and Path(dataset_path) == mp.DATASET_PATH:
        expected_hash = manifest["hashes"]["dataset_supervisado.csv"]
    frame = mp.load_supervised(dataset_path, expected_hash=expected_hash)
    split = mp.split_temporal(frame)
    counts = mp.verify_split_counts(split)
    mp.assert_no_leakage(frame)

    candidate = train_candidate(split["train"])
    evaluation = evaluate_validation(
        candidate["model"], split["validation"]
    )
    comparison = compare_models(
        split["validation"], evaluation["predicciones"]
    )
    test_info = {
        "filas": int(len(split["test"])),
        "meses": sorted(set(split["test"]["mes_objetivo"])),
        "metricas_calculadas": False,
    }
    payload = build_artifact(candidate, manifest)
    tlr.save_artifact(artifact_path, payload)

    now = datetime.now(timezone.utc)
    experiment_id = f"EXP-{MODEL_NAME}-{now.strftime('%Y%m%dT%H%M%S%fZ')}"
    parameters = {
        "random_state": RANDOM_STATE,
        "n_jobs": 1,
        **candidate["best_parameters"],
        "search": (
            f"grid {len(GRID)} configs; selección por {SELECTION_CRITERION}"
        ),
        "internal_mae": candidate["best_internal_metrics"]["mae"],
        "internal_rmse": candidate["best_internal_metrics"]["rmse"],
    }
    row = {
        "experiment_id": experiment_id,
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_version": manifest["dataset_version"],
        "dataset_hash": manifest["hashes"]["dataset_supervisado.csv"],
        "catalog_hash": manifest["catalog_snapshot_hash"],
        "generator_version": manifest["generator_version"],
        "seed": manifest["seed"],
        "features": "|".join(mp.FEATURE_COLUMNS),
        "target": mp.TARGET,
        "train_range": (
            f"{mp.SPLIT_RANGES['train'][0]}..{mp.SPLIT_RANGES['train'][1]}"
        ),
        "validation_range": (
            f"{mp.SPLIT_RANGES['validation'][0]}.."
            f"{mp.SPLIT_RANGES['validation'][1]}"
        ),
        "test_range": (
            f"{mp.SPLIT_RANGES['test'][0]}..{mp.SPLIT_RANGES['test'][1]}"
        ),
        "model": MODEL_NAME,
        "parameters": json.dumps(parameters, ensure_ascii=False),
        "preprocessing": PREPROCESSING_TEXT,
        "mae_val": evaluation["metrics"]["mae"],
        "rmse_val": evaluation["metrics"]["rmse"],
        "r2_val": evaluation["metrics"]["r2"],
        "mae_test": None,
        "rmse_test": None,
        "r2_test": None,
        "training_seconds": candidate["fit_seconds"],
        "tool_versions": tlr.tool_versions_text(),
        "artifact_path": _artifact_path_text(artifact_path),
        "notes": (
            f"CANDIDATE sin seleccionar V1; búsqueda interna de {len(GRID)} "
            "configs (menor MAE en "
            f"{INTERNAL_EVAL_RANGE[0]}..{INTERNAL_EVAL_RANGE[1]} de TRAIN); "
            "comparación vs baseline y LinearRegression en los mismos 504 "
            "casos; predicciones negativas sin recortar: "
            f"{evaluation['negativas']}; TEST reservado sin métricas."
        ),
    }
    mp.append_experiment(row, path=registry_path)
    return {
        "experiment_id": experiment_id,
        "dataset_version": manifest["dataset_version"],
        "filas": counts,
        "n_train": candidate["n_train"],
        "train_months": candidate["train_months"],
        "internal": {
            "grid_size": len(GRID),
            "criterion": SELECTION_CRITERION,
            "adjust_range": list(INTERNAL_ADJUST_RANGE),
            "eval_range": list(INTERNAL_EVAL_RANGE),
            "adjust_rows": candidate["internal_adjust_rows"],
            "eval_rows": candidate["internal_eval_rows"],
            "adjust_months": candidate["internal_adjust_months"],
            "eval_months": candidate["internal_eval_months"],
            "best_parameters": candidate["best_parameters"],
            "best_internal_metrics": candidate["best_internal_metrics"],
            "search_seconds": candidate["search_seconds"],
        },
        "fit_seconds": candidate["fit_seconds"],
        "feature_importances": {
            name: float(value)
            for name, value in zip(
                mp.FEATURE_COLUMNS,
                candidate["model"].feature_importances_,
            )
        },
        "validation": evaluation["metrics"],
        "baseline_validation": comparison["baseline"],
        "linear_regression_validation": comparison["linear_regression"],
        "comparison": comparison,
        "grupos_validation": evaluation["grupos"],
        "predicciones_negativas": evaluation["negativas"],
        "test": test_info,
        "artifact_path": _artifact_path_text(artifact_path),
        "registro": str(Path(registry_path)),
        "versions": tlr.tool_versions(),
        "total_seconds": time.perf_counter() - started,
    }


if __name__ == "__main__":
    print(json.dumps(run_experiment(), ensure_ascii=False, indent=2))
