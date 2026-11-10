"""Entrenamiento reproducible de LinearRegression con TRAIN (H4, semana 2).

Ajusta scaler y regresión exclusivamente con TRAIN, evalúa sobre VALIDATION
contra el baseline en los mismos casos y agrega una ejecución real a
experiments.csv. No usa TEST, no entrena RandomForest y no selecciona V1.
"""
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.linear_model import LinearRegression

import ml_pipeline as mp
from simulator_inputs import HERE, InputError

MODEL_NAME = "LINEARREGRESSION"
ARTIFACT_SCHEMA = "h4-linear-regression-1"
MODELS_DIR = HERE / "models"
DEFAULT_ARTIFACT_PATH = MODELS_DIR / "linear_regression_candidate.joblib"


def tool_versions():
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit-learn": sklearn.__version__,
        "scipy": scipy.__version__,
        "joblib": joblib.__version__,
    }


def tool_versions_text():
    versions = tool_versions()
    return "; ".join(
        f"{'scikit-learn' if key == 'scikit-learn' else key} {value}"
        for key, value in versions.items()
    )


def train_model(train_frame):
    """Ajusta scaler y LinearRegression exclusivamente con el frame recibido."""
    mp.assert_no_leakage(train_frame)
    X, y = mp.build_xy(train_frame)
    scaler = mp.TrainStandardizer().fit(X)
    model = LinearRegression().fit(scaler.transform(X), y)
    return scaler, model


def predict(scaler, model, X):
    """Inferencia con las cinco features en orden oficial, sin recortes."""
    if list(X.columns) != list(mp.FEATURE_COLUMNS):
        raise InputError(
            "MODELO INVÁLIDO: se esperaban las cinco features en orden "
            "oficial."
        )
    return np.asarray(model.predict(scaler.transform(X)), dtype="float64")


def model_parameters(model):
    return {
        key: model.get_params()[key]
        for key in sorted(model.get_params())
    }


def fit_and_evaluate(split):
    """Entrena con TRAIN y evalúa solo en VALIDATION; ignora TEST."""
    for name in ("train", "validation"):
        if name not in split:
            raise InputError(
                f"DATASET INVÁLIDO: falta la partición {name}."
            )
    train = split["train"]
    validation = split["validation"]
    allowed = set(range(
        mp.month_index(mp.SPLIT_RANGES["train"][0]),
        mp.month_index(mp.SPLIT_RANGES["train"][1]) + 1,
    ))
    used = {mp.month_index(month) for month in set(train["mes_objetivo"])}
    if not used <= allowed:
        raise InputError(
            "ENTRENAMIENTO INVÁLIDO: el marco contiene meses fuera de TRAIN."
        )
    mp.assert_no_leakage(validation)

    fit_started = time.perf_counter()
    scaler, model = train_model(train)
    fit_seconds = time.perf_counter() - fit_started

    X_val, y_val = mp.build_xy(validation)
    validation_prediction = predict(scaler, model, X_val)
    validation_metrics = mp.evaluate(y_val, validation_prediction)
    baseline_metrics = mp.evaluate(y_val, mp.baseline_predict(X_val))
    meta = mp.build_meta(validation)
    groups = {
        "por_tienda": mp.evaluate_by(
            meta, y_val, validation_prediction, "locationId"
        ),
        "por_rotacion": mp.evaluate_by(
            meta.assign(rotacion_diagnostico=mp.rotation_labels(meta)),
            y_val, validation_prediction, "rotacion_diagnostico",
        ),
        "por_mes": mp.evaluate_by(
            meta, y_val, validation_prediction, "mes_objetivo"
        ),
    }
    comparison = {
        "baseline": baseline_metrics,
        "linear_regression": validation_metrics,
        "diferencia_lr_menos_baseline": {
            key: validation_metrics[key] - baseline_metrics[key]
            for key in ("mae", "rmse", "r2")
        },
    }
    return {
        "scaler": scaler,
        "model": model,
        "fit_seconds": fit_seconds,
        "n_train": int(len(train)),
        "train_months": sorted(set(train["mes_objetivo"])),
        "validation": validation_metrics,
        "baseline_validation": baseline_metrics,
        "comparison": comparison,
        "grupos_validation": groups,
        "predicciones_validation": validation_prediction,
        "observados_validation": np.asarray(y_val, dtype="float64"),
        "predicciones_negativas": int((validation_prediction < 0).sum()),
        "coef": [float(value) for value in model.coef_],
        "intercept": float(model.intercept_),
        "parameters": model_parameters(model),
    }


def build_artifact(result, manifest):
    """Conjunto reproducible: transformación, coeficientes y metadatos."""
    scaler = result["scaler"]
    model = result["model"]
    return {
        "schema": ARTIFACT_SCHEMA,
        "model": MODEL_NAME,
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
        "scaler_mean": {
            key: float(value) for key, value in scaler.mean_.items()
        },
        "scaler_scale": {
            key: float(value) for key, value in scaler.scale_.items()
        },
        "coef": result["coef"],
        "intercept": result["intercept"],
        "parameters": result["parameters"],
        "versions": tool_versions(),
        "created_utc": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "scaler": scaler,
        "estimator": model,
    }


def save_artifact(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, path)
    return path


def load_artifact(path):
    return joblib.load(Path(path))


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
    return predict(artifact["scaler"], artifact["estimator"], X)


def _relative_to_repo(path):
    try:
        return str(Path(path).resolve().relative_to(HERE.parent.parent))
    except ValueError:
        return str(path)


def run_experiment(dataset_path=mp.DATASET_PATH,
                   registry_path=mp.EXPERIMENTS_PATH,
                   artifact_path=DEFAULT_ARTIFACT_PATH, expected_hash=None):
    """Entrena con TRAIN, evalúa VALIDATION y registra la ejecución real."""
    started = time.perf_counter()
    manifest = mp.official_manifest()
    if expected_hash is None and Path(dataset_path) == mp.DATASET_PATH:
        expected_hash = manifest["hashes"]["dataset_supervisado.csv"]
    frame = mp.load_supervised(dataset_path, expected_hash=expected_hash)
    split = mp.split_temporal(frame)
    counts = mp.verify_split_counts(split)
    mp.assert_no_leakage(frame)

    result = fit_and_evaluate(split)
    test_info = {
        "filas": int(len(split["test"])),
        "meses": sorted(set(split["test"]["mes_objetivo"])),
        "metricas_calculadas": False,
    }
    payload = build_artifact(result, manifest)
    save_artifact(artifact_path, payload)

    now = datetime.now(timezone.utc)
    experiment_id = f"EXP-{MODEL_NAME}-{now.strftime('%Y%m%dT%H%M%S%fZ')}"
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
        "parameters": json.dumps(
            {**result["parameters"], "coef": result["coef"],
             "intercept": result["intercept"]},
            ensure_ascii=False,
        ),
        "preprocessing": (
            "TrainStandardizer (z): media y desviación ajustadas solo con "
            "TRAIN, ddof=0"
        ),
        "mae_val": result["validation"]["mae"],
        "rmse_val": result["validation"]["rmse"],
        "r2_val": result["validation"]["r2"],
        "mae_test": None,
        "rmse_test": None,
        "r2_test": None,
        "training_seconds": result["fit_seconds"],
        "tool_versions": tool_versions_text(),
        "artifact_path": _relative_to_repo(artifact_path),
        "notes": (
            f"LR solo con TRAIN ({counts['train']} filas); comparación en "
            "VALIDATION sobre los mismos 504 casos; predicciones negativas "
            f"sin recortar: {result['predicciones_negativas']}; TEST "
            "reservado sin métricas; candidato sin seleccionar V1."
        ),
    }
    mp.append_experiment(row, path=registry_path)
    return {
        "experiment_id": experiment_id,
        "dataset_version": manifest["dataset_version"],
        "filas": counts,
        "n_train": result["n_train"],
        "train_months": result["train_months"],
        "fit_seconds": result["fit_seconds"],
        "coef": result["coef"],
        "intercept": result["intercept"],
        "parameters": result["parameters"],
        "validation": result["validation"],
        "baseline_validation": result["baseline_validation"],
        "comparison": result["comparison"],
        "grupos_validation": result["grupos_validation"],
        "predicciones_negativas": result["predicciones_negativas"],
        "test": test_info,
        "artifact_path": _relative_to_repo(artifact_path),
        "registro": str(Path(registry_path)),
        "versions": tool_versions(),
        "total_seconds": time.perf_counter() - started,
    }


if __name__ == "__main__":
    print(json.dumps(run_experiment(), ensure_ascii=False, indent=2))
