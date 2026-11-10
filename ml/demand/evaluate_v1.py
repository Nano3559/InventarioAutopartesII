"""Evaluación final única de V1 sobre TEST (H4 tarea 9B).

Antes de predecir verifica el congelamiento: manifiesto de selección, V1
RandomForest con estado SELECTED_FROZEN_NOT_ACTIVE, SHA256 del arteacto,
integridad del dataset 1.1, cinco features en orden exacto, hiperparámetros
congelados, TEST sin métricas y ausencia de evaluación previa. Si falta
cualquier condición se detiene sin tocar TEST.

La evaluación carga el arteacto congelado, predice exclusivamente sobre
TEST (2026-07..2026-09), calcula métricas globales y por grupos sin
recortar salidas, actualiza solo los campos de TEST de la fila de
RandomForest en experiments.csv y escribe el reporte final. Si el reporte
ya existe devuelve el resultado registrado sin recalcular predicciones ni
modificar ningún archivo.
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import train_linear_regression as tlr
from ml_pipeline import (
    DATASET_PATH, EXPERIMENT_COLUMNS, EXPERIMENTS_PATH, FEATURE_COLUMNS,
    REPORTS_DIR, SPLIT_RANGES, TARGET, build_xy, evaluate, evaluate_by,
    load_supervised, official_manifest, rotation_labels, split_temporal,
)
from select_v1 import (
    SELECTION_SCHEMA, V1_MANIFEST_PATH, read_registry,
)
from simulator_inputs import InputError, content_sha256, offset_month

TEST_EVALUATION_PATH = REPORTS_DIR / "v1_test_evaluation.json"
EVALUATION_SCHEMA = "h4-v1-test-evaluation-1"
REQUIRED_V1_MODEL = "RANDOMFOREST"
TEST_FIELDS = ("mae_test", "rmse_test", "r2_test")
REPORT_PATH_TEXT = "ml/demand/reports/v1_test_evaluation.json"
MANIFEST_PATH_TEXT = "ml/demand/reports/v1_selection_manifest.json"


def months_between(start, end):
    months = [start]
    while months[-1] != end:
        months.append(offset_month(months[-1], 1))
    return months


def load_selection_manifest(path=V1_MANIFEST_PATH):
    path = Path(path)
    if not path.is_file():
        raise InputError(
            "MANIFIESTO DE CONGELAMIENTO INVÁLIDO: falta "
            "v1_selection_manifest.json."
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(
            "MANIFIESTO DE CONGELAMIENTO INVÁLIDO: JSON ilegible."
        ) from exc
    if document.get("schema") != SELECTION_SCHEMA:
        raise InputError(
            "MANIFIESTO DE CONGELAMIENTO INVÁLIDO: esquema no reconocido."
        )
    return document


def _resolve_artifact_path(text):
    from select_v1 import _resolve_artifact_path as resolve
    return resolve(text)


def precheck_v1(manifest_path=V1_MANIFEST_PATH, dataset_path=DATASET_PATH,
                registry_path=EXPERIMENTS_PATH,
                report_path=TEST_EVALUATION_PATH):
    """Nueve verificaciones obligatorias antes de predecir sobre TEST."""
    selection = load_selection_manifest(manifest_path)

    if selection.get("selection", {}).get("model") != REQUIRED_V1_MODEL:
        raise InputError(
            f"SELECCIÓN INVÁLIDA: V1 debe ser {REQUIRED_V1_MODEL}."
        )
    status = selection.get("status")
    if status != "SELECTED_FROZEN_NOT_ACTIVE":
        raise InputError(
            "SELECCIÓN INVÁLIDA: el estado congelado debe ser "
            f"SELECTED_FROZEN_NOT_ACTIVE y es {status!r}."
        )

    artifact_info = selection.get("artifact", {})
    artifact_path = _resolve_artifact_path(artifact_info.get("path"))
    artifact_hash = content_sha256(artifact_path.read_bytes())
    if artifact_hash != artifact_info.get("sha256"):
        raise InputError(
            "ARTEFACTO INVÁLIDO: la huella SHA256 no coincide con el "
            "manifiesto congelado."
        )

    payload = tlr.load_artifact(artifact_path)
    if payload.get("role") != "CANDIDATE":
        raise InputError("ARTEFACTO INVÁLIDO: el artefacto debe ser CANDIDATE.")
    if payload.get("model") != REQUIRED_V1_MODEL:
        raise InputError("ARTEFACTO INVÁLIDO: el artefacto no es V1 RandomForest.")

    hashes = selection.get("dataset", {}).get("hashes", {})
    expected_dataset_hash = hashes.get("dataset_supervisado.csv")
    dataset_hash = content_sha256(Path(dataset_path).read_bytes())
    if dataset_hash != expected_dataset_hash:
        raise InputError(
            "DATASET INVÁLIDO: la huella no coincide con el congelamiento."
        )
    if Path(dataset_path) == DATASET_PATH:
        official_hash = official_manifest()["hashes"]["dataset_supervisado.csv"]
        if dataset_hash != official_hash or official_hash != expected_dataset_hash:
            raise InputError(
                "DATASET INVÁLIDO: las huellas oficiales de 1.1 no coinciden."
            )

    contract_features = selection.get("contract", {}).get("features")
    expected_features = list(FEATURE_COLUMNS)
    if payload.get("feature_names") != expected_features:
        raise InputError(
            "CONTRATO INVÁLIDO: el arteacto no usa las cinco features en "
            "orden oficial."
        )
    if contract_features != expected_features:
        raise InputError(
            "CONTRATO INVÁLIDO: el manifiesto no registra las cinco features "
            "en orden oficial."
        )
    if payload.get("target") != TARGET or selection.get("contract", {}).get(
        "target"
    ) != TARGET:
        raise InputError("CONTRATO INVÁLIDO: target distinto al oficial.")

    frozen_parameters = selection.get("hyperparameters")
    if payload.get("parameters") != frozen_parameters:
        raise InputError(
            "PARÁMETROS INVÁLIDOS: los hiperparámetros del artefacto no "
            "coinciden con los congelados."
        )

    rows = read_registry(registry_path)
    rf_rows = [row for row in rows if row["model"] == REQUIRED_V1_MODEL]
    if len(rf_rows) != 1:
        raise InputError(
            f"REGISTRO INVÁLIDO: se esperaba una única fila de "
            f"{REQUIRED_V1_MODEL} y hay {len(rf_rows)}."
        )
    rf_row = rf_rows[0]
    if rf_row["experiment_id"] != selection.get("selection", {}).get(
        "experiment_id"
    ):
        raise InputError(
            "REGISTRO INVÁLIDO: la fila de V1 no corresponde a la selección "
            "congelada."
        )
    if rf_row.get("artifact_path") != artifact_info.get("path"):
        raise InputError(
            "REGISTRO INVÁLIDO: la ruta del artefacto difiere de la "
            "selección congelada."
        )

    if Path(report_path).exists():
        raise InputError(
            "EVALUACIÓN YA REGISTRADA: existe un reporte final de TEST."
        )

    for row in rows:
        for field in TEST_FIELDS:
            if row.get(field, "") != "":
                raise InputError(
                    "REGISTRO INVÁLIDO: TEST ya contiene métricas; la "
                    "evaluación final ya fue registrada."
                )

    return {
        "selection": selection,
        "payload": payload,
        "artifact_path": artifact_path,
        "artifact_hash": artifact_hash,
        "dataset_hash": dataset_hash,
        "rows": rows,
        "rf_row": rf_row,
    }


def _predict(payload, X):
    scaler = payload.get("scaler")
    features = scaler.transform(X) if scaler is not None else X
    return payload["estimator"].predict(features)


def evaluate_test_partition(payload, test_frame):
    """Métricas exclusivamente sobre TEST, sin recortar predicciones."""
    X, y = build_xy(test_frame)
    prediction = _predict(payload, X)
    metrics = evaluate(y, prediction)
    groups_frame = test_frame[["productId", "locationId", "mes_objetivo"]].copy()
    groups_frame["rotacion_diagnostico"] = rotation_labels(groups_frame)
    return {
        **metrics,
        "predicciones_negativas": int((prediction < 0).sum()),
        "observados": y,
        "predicciones": prediction,
        "groups": {
            "por_tienda": evaluate_by(
                test_frame, y, prediction, "locationId"
            ),
            "por_mes": evaluate_by(
                test_frame, y, prediction, "mes_objetivo"
            ),
            "por_rotacion": evaluate_by(
                groups_frame, y, prediction, "rotacion_diagnostico"
            ),
        },
    }


def update_test_fields(registry_path, experiment_id, metrics):
    """Actualiza únicamente mae_test/rmse_test/r2_test de una fila."""
    path = Path(registry_path)
    rows = read_registry(path)
    matches = [row for row in rows if row["experiment_id"] == experiment_id]
    if len(matches) != 1:
        raise InputError(
            "REGISTRO INVÁLIDO: no se encontró la fila del experimento."
        )
    target = matches[0]
    for field in TEST_FIELDS:
        if target.get(field, "") != "":
            raise InputError(
                "REGISTRO INVÁLIDO: los campos de TEST ya fueron registrados."
            )
        if any(row.get(field, "") for row in rows):
            raise InputError(
                "REGISTRO INVÁLIDO: TEST ya contiene métricas en otra fila."
            )
    target["mae_test"] = repr(float(metrics["mae"]))
    target["rmse_test"] = repr(float(metrics["rmse"]))
    target["r2_test"] = repr(float(metrics["r2"]))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPERIMENT_COLUMNS,
                                lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "")
                             for column in EXPERIMENT_COLUMNS})
    return target


def _load_report(path):
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(
            "ESTADO INCONSISTENTE: el reporte de evaluación es ilegible."
        ) from exc
    if document.get("schema") != EVALUATION_SCHEMA:
        raise InputError(
            "ESTADO INCONSISTENTE: esquema de reporte no reconocido."
        )
    return document


def _verify_already_evaluated(selection, report, registry_path, artifact_path):
    if report.get("selection_id") != selection.get("selection_id"):
        raise InputError(
            "ESTADO INCONSISTENTE: el reporte no corresponde a la selección "
            "congelada."
        )
    if report.get("artifact", {}).get("sha256") != content_sha256(
        artifact_path.read_bytes()
    ):
        raise InputError(
            "ESTADO INCONSISTENTE: el artefacto difiere del reporte "
            "registrado."
        )
    rows = read_registry(registry_path)
    experiment_id = report.get("registry", {}).get("experiment_id")
    matches = [row for row in rows if row["experiment_id"] == experiment_id]
    if len(matches) != 1:
        raise InputError(
            "ESTADO INCONSISTENTE: falta la fila registrada en experiments.csv."
        )
    row = matches[0]
    metrics = report.get("metrics", {})
    for field, key in zip(TEST_FIELDS, ("mae", "rmse", "r2")):
        if row.get(field, "") == "" or float(row[field]) != metrics.get(key):
            raise InputError(
                "ESTADO INCONSISTENTE: los campos de TEST de experiments.csv "
                "no coinciden con el reporte."
            )
    return rows


def run_final_evaluation(manifest_path=V1_MANIFEST_PATH,
                         dataset_path=DATASET_PATH,
                         registry_path=EXPERIMENTS_PATH,
                         report_path=TEST_EVALUATION_PATH):
    """Evaluación oficial única de V1 sobre TEST, con protección de repetición."""
    report_path = Path(report_path)
    selection = load_selection_manifest(manifest_path)
    if report_path.exists():
        report = _load_report(report_path)
        artifact_path = _resolve_artifact_path(
            selection.get("artifact", {}).get("path")
        )
        _verify_already_evaluated(selection, report, registry_path,
                                  artifact_path)
        return {"execution": "already_evaluated", "report": report}

    checked = precheck_v1(manifest_path=manifest_path,
                          dataset_path=dataset_path,
                          registry_path=registry_path,
                          report_path=report_path)
    selection = checked["selection"]
    payload = checked["payload"]
    artifact_path = checked["artifact_path"]

    expected_hash = None
    if Path(dataset_path) == DATASET_PATH:
        expected_hash = checked["dataset_hash"]
    frame = load_supervised(dataset_path, expected_hash=expected_hash)
    split = split_temporal(frame)
    test = split["test"]
    expected_months = months_between(SPLIT_RANGES["test"][0],
                                     SPLIT_RANGES["test"][1])
    test_months = sorted(set(test["mes_objetivo"]))
    if test_months != expected_months:
        raise InputError(
            f"TEST INVÁLIDO: meses {test_months} distintos de {expected_months}."
        )
    if len(test) != 504:
        raise InputError(
            f"TEST INVÁLIDO: se esperaban 504 registros y hay {len(test)}."
        )

    result = evaluate_test_partition(payload, test)
    metrics = {
        "n": result["n"],
        "n_con_prediccion": result["n_con_prediccion"],
        "mae": result["mae"],
        "rmse": result["rmse"],
        "r2": result["r2"],
        "cobertura": result["cobertura"],
        "predicciones_negativas": result["predicciones_negativas"],
    }

    updated_row = update_test_fields(registry_path,
                                     checked["rf_row"]["experiment_id"],
                                     metrics)

    now = datetime.now(timezone.utc)
    validation_global = selection.get("validation_metrics", {}).get(
        "global", {}
    )
    report = {
        "schema": EVALUATION_SCHEMA,
        "v1_id": "V1",
        "selection_id": selection.get("selection_id"),
        "manifest_path": MANIFEST_PATH_TEXT,
        "evaluated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "TEST_EVALUATED_COMPLETED",
        "artifact": {
            "path": selection.get("artifact", {}).get("path"),
            "sha256": checked["artifact_hash"],
        },
        "dataset": {
            "version": selection.get("dataset", {}).get("version"),
            "hash": checked["dataset_hash"],
        },
        "test": {
            "period": f"{SPLIT_RANGES['test'][0]}..{SPLIT_RANGES['test'][1]}",
            "rows": int(len(test)),
            "months": test_months,
        },
        "metrics": metrics,
        "groups": result["groups"],
        "validation_metrics": validation_global,
        "comparison_descriptive": {
            "mae_test_menos_val": metrics["mae"] - validation_global["mae"],
            "rmse_test_menos_val": (
                metrics["rmse"] - validation_global["rmse"]
            ),
            "r2_test_menos_val": metrics["r2"] - validation_global["r2"],
        },
        "versions": payload.get("versions"),
        "tool_versions": updated_row.get("tool_versions"),
        "registry": {
            "path": "ml/demand/reports/experiments.csv",
            "experiment_id": updated_row["experiment_id"],
            "updated_fields": list(TEST_FIELDS),
        },
        "retrained": False,
        "model_changed": False,
        "hyperparameters_changed": False,
        "next": (
            "Pendiente: demand_runtime.py (contrato ACTIVE) y activación "
            "posterior de V1; ninguna decisión se toma con este resultado."
        ),
    }
    with report_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return {"execution": "evaluated_now", "report": report}


if __name__ == "__main__":
    print(json.dumps(run_final_evaluation(), ensure_ascii=False, indent=2))
