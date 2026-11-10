"""Selección y congelamiento de V1 con exclusivamente VALIDATION (H4 tarea 9A).

Elige el experimento de menor MAE global en VALIDATION entre el registro
oficial, verifica la identidad del artefacto ganador, recalcula sus métricas
de VALIDATION sin reentrenar, comprueba que TEST sigue reservado y escribe el
manifiesto de congelamiento. Nunca llama fit, nunca busca hiperparámetros de
nuevo y nunca calcula métricas ni predicciones sobre TEST.
"""
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import train_linear_regression as tlr
from ml_pipeline import (
    DATASET_PATH, EXPERIMENT_COLUMNS, EXPERIMENTS_PATH, FEATURE_COLUMNS,
    REPORTS_DIR, SPLIT_RANGES, TARGET, build_xy, evaluate, evaluate_by,
    load_supervised, official_manifest, rotation_labels, split_temporal,
    verify_split_counts,
)
from simulator_inputs import FEATURE_NAMES, HERE, InputError, content_sha256

V1_MANIFEST_PATH = REPORTS_DIR / "v1_selection_manifest.json"
SELECTION_SCHEMA = "h4-v1-selection-1"
REPO_ROOT = HERE.parent.parent
SELECTION_CRITERION = (
    "menor MAE global en VALIDATION; empate por menor RMSE; luego mayor R²"
)
REQUIRED_MODELS = ("BASELINE_LAG1", "LINEARREGRESSION", "RANDOMFOREST")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def read_registry(path=EXPERIMENTS_PATH):
    """Lee el registro validando el contrato exacto de columnas."""
    path = Path(path)
    if not path.is_file():
        raise InputError("REGISTRO INVÁLIDO: falta experiments.csv.")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        if header != EXPERIMENT_COLUMNS:
            raise InputError(
                "REGISTRO INVÁLIDO: experiments.csv con columnas distintas "
                "al contrato."
            )
        rows = list(reader)
    if not rows:
        raise InputError("REGISTRO INVÁLIDO: sin experimentos registrados.")
    return rows


def select_winner(rows):
    """Ganador por MAE de VALIDATION, con desempate por RMSE y luego R²."""
    scored = []
    for row in rows:
        try:
            mae = float(row["mae_val"])
            rmse = float(row["rmse_val"])
            r2 = float(row["r2_val"])
        except (KeyError, TypeError, ValueError) as exc:
            raise InputError(
                "SELECCIÓN INVÁLIDA: métricas de VALIDATION incompletas."
            ) from exc
        scored.append((mae, rmse, -r2, row))
    scored.sort(key=lambda item: (item[0], item[1], item[2]))
    return scored[0][3]


def _verify_registry_contract(rows, manifest):
    """Coherencia del registro y prohibición total de métricas de TEST."""
    by_model = {}
    for row in rows:
        for column in ("mae_test", "rmse_test", "r2_test"):
            if row.get(column, "") != "":
                raise InputError(
                    "SELECCIÓN INVÁLIDA: TEST debe permanecer reservado "
                    "sin métricas en el registro."
                )
        if row.get("features") != "|".join(FEATURE_COLUMNS):
            raise InputError("SELECCIÓN INVÁLIDA: features distintas al contrato.")
        if row.get("target") != TARGET:
            raise InputError("SELECCIÓN INVÁLIDA: target distinto al contrato.")
        ranges = {
            name: f"{start}..{end}" for name, (start, end) in SPLIT_RANGES.items()
        }
        if row.get("train_range") != ranges["train"]:
            raise InputError("SELECCIÓN INVÁLIDA: rango de TRAIN alterado.")
        if row.get("validation_range") != ranges["validation"]:
            raise InputError("SELECCIÓN INVÁLIDA: rango de VALIDATION alterado.")
        if row.get("test_range") != ranges["test"]:
            raise InputError("SELECCIÓN INVÁLIDA: rango de TEST alterado.")
        if row.get("dataset_hash") != manifest["hashes"]["dataset_supervisado.csv"]:
            raise InputError("SELECCIÓN INVÁLIDA: huella del dataset alterada.")
        if row.get("catalog_hash") != manifest["catalog_snapshot_hash"]:
            raise InputError("SELECCIÓN INVÁLIDA: huella del catálogo alterada.")
        try:
            seed = int(row.get("seed", ""))
        except ValueError as exc:
            raise InputError("SELECCIÓN INVÁLIDA: seed inválido.") from exc
        if seed != manifest["seed"]:
            raise InputError("SELECCIÓN INVÁLIDA: seed distinto al oficial.")
        by_model.setdefault(row.get("model", ""), []).append(row)
    for model in REQUIRED_MODELS:
        count = len(by_model.get(model, []))
        if count != 1:
            raise InputError(
                f"SELECCIÓN INVÁLIDA: se esperaba una única fila para "
                f"{model} y hay {count}."
            )
    return by_model


def _resolve_artifact_path(text):
    if not text or text == "SIN_ARTEFACTO":
        raise InputError(
            "SELECCIÓN INVÁLIDA: el modelo ganador no tiene artefacto."
        )
    path = Path(text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_file():
        raise InputError("SELECCIÓN INVÁLIDA: falta el artefacto ganador.")
    return path


def _predict_payload(payload, X):
    scaler = payload.get("scaler")
    features = scaler.transform(X) if scaler is not None else X
    return payload["estimator"].predict(features)


def _verify_artifact_identity(payload, row, artifact_hash):
    """El artefacto debe corresponder exactamente a la fila ganadora."""
    if payload.get("model") != row.get("model"):
        raise InputError(
            "SELECCIÓN INVÁLIDA: el artefacto no corresponde al modelo ganador."
        )
    if payload.get("role") != "CANDIDATE":
        raise InputError(
            "SELECCIÓN INVÁLIDA: el artefacto ganador debe ser CANDIDATE."
        )
    if payload.get("feature_names") != list(FEATURE_COLUMNS):
        raise InputError(
            "SELECCIÓN INVÁLIDA: el artefacto no usa las cinco features en "
            "orden oficial."
        )
    if payload.get("target") != TARGET:
        raise InputError("SELECCIÓN INVÁLIDA: target distinto en el artefacto.")
    if payload.get("dataset_hash") != row.get("dataset_hash"):
        raise InputError(
            "SELECCIÓN INVÁLIDA: huella de dataset distinta en el artefacto."
        )
    if not HEX64.match(artifact_hash):
        raise InputError("SELECCIÓN INVÁLIDA: SHA256 del artefacto inválido.")
    try:
        row_parameters = json.loads(row.get("parameters") or "{}")
    except json.JSONDecodeError as exc:
        raise InputError(
            "SELECCIÓN INVÁLIDA: parámetros ilegibles en el registro."
        ) from exc
    payload_parameters = payload.get("parameters") or {}
    for key, value in payload_parameters.items():
        if key in row_parameters and row_parameters[key] != value:
            raise InputError(
                f"SELECCIÓN INVÁLIDA: hiperparámetro {key} alterado respecto "
                "del registro."
            )
    if payload.get("parameters") is None:
        raise InputError("SELECCIÓN INVÁLIDA: artefacto sin parámetros.")


def _validation_metrics_from_artifact(payload, split):
    """Recalcula solo VALIDATION desde el artefacto ganador, sin fit."""
    validation = split["validation"]
    X, y = build_xy(validation)
    prediction = _predict_payload(payload, X)
    metrics = evaluate(y, prediction)
    groups_frame = validation[["productId", "locationId", "mes_objetivo"]].copy()
    groups_frame["rotacion_diagnostico"] = rotation_labels(
        groups_frame[["productId", "locationId", "mes_objetivo"]]
    )
    negatives = int((prediction < 0).sum())
    return {
        "global": metrics,
        "predicciones_negativas": negatives,
        "por_tienda": evaluate_by(validation, y, prediction, "locationId"),
        "por_mes": evaluate_by(validation, y, prediction, "mes_objetivo"),
        "por_rotacion": evaluate_by(
            groups_frame, y, prediction, "rotacion_diagnostico"
        ),
    }


def _comparison_from_registry(by_model):
    comparison = {}
    for model in REQUIRED_MODELS:
        row = by_model[model][0]
        comparison[model] = {
            "experiment_id": row["experiment_id"],
            "mae": float(row["mae_val"]),
            "rmse": float(row["rmse_val"]),
            "r2": float(row["r2_val"]),
        }
    return comparison


def _build_limitations(groups):
    """Limitaciones conocidas, con énfasis documentado en rotación ALTA."""
    rotations = groups["por_rotacion"]
    stores = groups["por_tienda"]
    months = groups["por_mes"]
    worst_rotation = max(rotations, key=lambda name: rotations[name]["mae"])
    worst_store = max(stores, key=lambda name: stores[name]["mae"])
    worst_month = max(months, key=lambda name: months[name]["mae"])
    negative_r2 = sorted(name for name, m in rotations.items() if m["r2"] < 0)
    limitations = [
        "Dataset sintético 1.1: los resultados proceden de simulación, no de "
        "ventas comerciales reales.",
        "Panel de 21 meses (2025-01..2026-09) con dos ciclos anuales; la "
        "estacionalidad observable es limitada.",
        "Selección basada exclusivamente en VALIDATION (2026-04..2026-06); "
        "TEST sigue reservado y sin evaluar.",
        "Cinco features de lags y calendario, sin stockout, precio, "
        "promoción ni eventos del negocio.",
        "RandomForest no extrapolá tendencias fuera del rango de lags "
        "aprendidos durante TRAIN.",
        "Los ceros aprendidos como lag cero no distinguen falta de stock de "
        "ausencia de demanda.",
        (
            f"Rotación {worst_rotation}: peor MAE de grupo "
            f"({rotations[worst_rotation]['mae']:.6f}, R² "
            f"{rotations[worst_rotation]['r2']:.6f}); es la limitación "
            "principal por grupo."
        ),
        (
            f"Tienda {worst_store}: mayor MAE por tienda "
            f"({stores[worst_store]['mae']:.6f})."
        ),
        (
            f"Mes {worst_month}: mayor MAE por mes "
            f"({months[worst_month]['mae']:.6f})."
        ),
    ]
    if negative_r2:
        limitations.append(
            "R² negativo en rotaciones "
            + ", ".join(negative_r2)
            + ": el modelo reduce MAE pero no explica varianza en esos grupos."
        )
    return limitations


def freeze_v1(manifest_path=V1_MANIFEST_PATH, registry_path=EXPERIMENTS_PATH,
              dataset_path=DATASET_PATH):
    """Congela V1 con el artefacto ganador por MAE de VALIDATION."""
    manifest = official_manifest()
    rows = read_registry(registry_path)
    by_model = _verify_registry_contract(rows, manifest)
    winner = select_winner(rows)
    artifact_path = _resolve_artifact_path(winner.get("artifact_path"))
    artifact_hash = content_sha256(artifact_path.read_bytes())
    payload = tlr.load_artifact(artifact_path)
    _verify_artifact_identity(payload, winner, artifact_hash)

    expected_hash = None
    if Path(dataset_path) == DATASET_PATH:
        expected_hash = manifest["hashes"]["dataset_supervisado.csv"]
    frame = load_supervised(dataset_path, expected_hash=expected_hash)
    split = split_temporal(frame)
    verify_split_counts(split)

    groups = _validation_metrics_from_artifact(payload, split)
    registry_keys = {"mae": "mae_val", "rmse": "rmse_val", "r2": "r2_val"}
    for key, registry_key in registry_keys.items():
        if groups["global"][key] != float(winner[registry_key]):
            raise InputError(
                "SELECCIÓN INVÁLIDA: las métricas de VALIDATION del artefacto "
                "no coinciden con el registro."
            )

    test_months = sorted(set(split["test"]["mes_objetivo"]))
    now = datetime.now(timezone.utc)
    selection_id = f"SEL-V1-{winner['model']}-{now.strftime('%Y%m%dT%H%M%S%fZ')}"
    comparison = _comparison_from_registry(by_model)
    manifest_document = {
        "schema": SELECTION_SCHEMA,
        "v1_id": "V1",
        "selection_id": selection_id,
        "frozen_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "SELECTED_FROZEN_NOT_ACTIVE",
        "active": False,
        "artifact_role": "CANDIDATE",
        "criterion": {
            "principal": "MAE global en VALIDATION",
            "secundarios": [
                "RMSE", "R²", "cobertura", "errores por tienda, mes y rotación",
                "complejidad y reproducibilidad",
            ],
            "orden_desempate": SELECTION_CRITERION,
            "busquedas_adicionales_tras_validation": False,
            "reentrenamiento": False,
            "test_utilizado": False,
        },
        "selection": {
            "model": winner["model"],
            "experiment_id": winner["experiment_id"],
            "mae_val": float(winner["mae_val"]),
            "rmse_val": float(winner["rmse_val"]),
            "r2_val": float(winner["r2_val"]),
        },
        "comparison_validation": comparison,
        "artifact": {
            "path": winner["artifact_path"],
            "sha256": artifact_hash,
            "bytes": artifact_path.stat().st_size,
            "schema": payload.get("schema"),
            "model": payload.get("model"),
            "role": payload.get("role"),
            "created_utc": payload.get("created_utc"),
            "candidate_preserved": True,
            "retrained": False,
        },
        "dataset": {
            "version": manifest["dataset_version"],
            "hashes": manifest["hashes"],
            "catalog_hash": manifest["catalog_snapshot_hash"],
            "generator_version": manifest["generator_version"],
            "seed": manifest["seed"],
        },
        "contract": {
            "features": list(FEATURE_COLUMNS),
            "feature_order_exacta": True,
            "target": TARGET,
            "preprocessing": payload.get("preprocessing"),
        },
        "periods": {
            "train": f"{SPLIT_RANGES['train'][0]}..{SPLIT_RANGES['train'][1]}",
            "validation": (
                f"{SPLIT_RANGES['validation'][0]}..{SPLIT_RANGES['validation'][1]}"
            ),
            "test_reservado": (
                f"{SPLIT_RANGES['test'][0]}..{SPLIT_RANGES['test'][1]}"
            ),
        },
        "hyperparameters": payload.get("parameters"),
        "seed": {
            "random_state": (payload.get("parameters") or {}).get("random_state"),
            "dataset_seed": manifest["seed"],
        },
        "validation_metrics": {
            **groups,
            "recomputed_from_artifact": True,
        },
        "versions": payload.get("versions"),
        "tool_versions": winner.get("tool_versions"),
        "test": {
            "filas": int(len(split["test"])),
            "meses": test_months,
            "metricas_calculadas": False,
            "predicciones_generadas": False,
        },
        "limitations": _build_limitations(groups),
        "next": (
            "Tarea 9B: evaluación única sobre TEST con decisiones congeladas; "
            "la activación como ACTIVE exige el contrato runtime pendiente."
        ),
    }
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest_document, ensure_ascii=False, indent=2) + "\n"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return manifest_document


if __name__ == "__main__":
    print(json.dumps(freeze_v1(), ensure_ascii=False, indent=2))
