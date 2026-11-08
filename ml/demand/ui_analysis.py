"""Métricas y monitoreo de Ross sobre emisiones cerradas. No selecciona ni entrena."""
import json
import hashlib
import math
from collections import defaultdict

from simulator_inputs import InputError, offset_month, parse_month, validate_quantity
from ui_runtime import ClosedObservation, Forecast, ORIGIN, checked_number, model_info


def model_key(row):
    return row.forecast.model


def metric_values(pairs):
    if not pairs:
        return {"n": 0, "MAE": None, "RMSE": None, "R2": None}
    errors = [p - y for y, p in pairs]
    n = len(pairs)
    mean = math.fsum(y for y, _ in pairs) / n
    denominator = math.fsum((y - mean)**2 for y, _ in pairs)
    return {
        "n": n, "MAE": math.fsum(abs(e) for e in errors) / n,
        "RMSE": math.sqrt(math.fsum(e**2 for e in errors) / n),
        "R2": None if n < 2 or denominator == 0 else 1 - math.fsum(e**2 for e in errors) / denominator,
    }


def evaluate(rows):
    if len({model_key(r) for r in rows}) > 1:
        raise InputError("Separa modelos, versiones y huellas antes de calcular métricas.")
    valid = [r for r in rows if r.forecast.prediction is not None]
    comparable = [r for r in valid if r.forecast.baseline is not None]
    return {
        **metric_values([(r.observed, r.forecast.prediction) for r in valid]),
        "closed": len(rows), "coverage": len(valid) / len(rows) if rows else None,
        "abstentions": len(rows) - len(valid),
        "baseline": metric_values([(r.observed, r.forecast.baseline) for r in comparable]),
        "model_comparable": metric_values([(r.observed, r.forecast.prediction) for r in comparable]),
    }


def group_errors(rows, dimension):
    getters = {
        "Tienda": lambda r: r.forecast.location_id,
        "Producto": lambda r: r.forecast.product_id,
        "Mes": lambda r: r.forecast.month,
        "Rotación": lambda r: r.rotation,
    }
    groups = defaultdict(list)
    for row in rows:
        groups[getters[dimension](row)].append(row)
    result = []
    for key, group in sorted(groups.items()):
        metrics = evaluate(group)
        result.append({dimension: key, "Casos": metrics["closed"], "Con predicción": metrics["n"],
                       "Cobertura": metrics["coverage"], "MAE": metrics["MAE"], "RMSE": metrics["RMSE"]})
    return result


def monitor(rows, window=3):
    if window != 3:
        raise InputError("Esta demo utiliza ventanas documentadas de tres meses.")
    if len({model_key(r) for r in rows}) > 1 or len({r.forecast.key[:2] for r in rows}) > 1:
        raise InputError("El monitoreo requiere una serie y una versión, sin mezclas.")
    recent = sorted(rows, key=lambda r: r.forecast.month)[-2*window:]
    output = {"status": "EVIDENCIA INSUFICIENTE", "reason": "Se requieren seis meses consecutivos cerrados con predicción comparable.",
              "previous_mae": None, "recent_mae": None, "baseline_previous": None, "baseline_recent": None,
              "lag1_previous": None, "lag1_recent": None}
    if any(r.forecast.reason == "ERROR DE INFERENCIA" for r in recent):
        return {**output, "status": "PROBLEMA TÉCNICO", "reason": "Revisar inferencia o compatibilidad antes de evaluar reentrenamiento."}
    if any("DATOS INCOMPLETOS" in r.forecast.reason or "HISTORIAL INSUFICIENTE" in r.forecast.reason for r in recent):
        return {**output, "status": "PROBLEMA DE DATOS", "reason": "Resolver calidad o historia antes de evaluar reentrenamiento."}
    if len(recent) != 6 or any(r.forecast.prediction is None or r.forecast.baseline is None for r in recent):
        return output
    if any(offset_month(a.forecast.month, 1) != b.forecast.month for a, b in zip(recent, recent[1:])):
        return output
    observed_by_month = {r.forecast.month: r.observed for r in rows}
    for row in recent:
        if row.forecast.features is not None:
            for lag in (1, 2, 3):
                previous = offset_month(row.forecast.month, -lag)
                if previous in observed_by_month and row.forecast.features[lag-1] != observed_by_month[previous]:
                    return {**output, "status": "PROBLEMA DE DATOS",
                            "reason": "Los lags no coinciden con observados ya cerrados. No mezcles hipótesis independientes al evaluar drift."}
    first, second = recent[:window], recent[window:]
    prior, current = evaluate(first), evaluate(second)
    increasing = current["MAE"] > prior["MAE"] and sum(
        abs(r.forecast.prediction-r.observed) > prior["MAE"] for r in second
    ) >= 2
    baseline_better = (prior["baseline"]["MAE"] < prior["MAE"]
                       and current["baseline"]["MAE"] < current["MAE"])
    for key, block in (("previous", first), ("recent", second)):
        values = [r.forecast.features[0] for r in block if r.forecast.features is not None]
        output[f"lag1_{key}"] = math.fsum(values)/len(values) if values else None
    return {**output, "status": "REVISIÓN RECOMENDADA" if increasing or baseline_better else "NORMAL",
            "reason": "Error sostenido o baseline superior en ambas ventanas. Evaluar, no entrenar automáticamente."
            if increasing or baseline_better else "No se activa el criterio demostrativo. No certifica estabilidad comercial.",
            "previous_mae": prior["MAE"], "recent_mae": current["MAE"],
            "baseline_previous": prior["baseline"]["MAE"], "baseline_recent": current["baseline"]["MAE"]}


def record_table(rows):
    return [{
        "Mes": r.forecast.month, "Producto": r.forecast.product_id, "Tienda": r.forecast.location_id,
        "Observado": r.observed, "Predicción": r.forecast.prediction, "Baseline": r.forecast.baseline,
        "Error absoluto": None if r.forecast.prediction is None else abs(r.forecast.prediction-r.observed),
        "Modelo": r.forecast.model.name if r.forecast.model else "SIN MODELO",
        "Versión": r.forecast.model.version if r.forecast.model else "NO DISPONIBLE",
        "Huella": r.forecast.model.artifact_hash if r.forecast.model else "",
        "Rotación": r.rotation, "Escenario": r.forecast.scenario, "Motivo": r.forecast.reason,
        "Estado": "CERRADO CON ABSTENCIÓN" if r.forecast.prediction is None else "CERRADO CON PREDICCIÓN",
        "Emitido": r.forecast.issued_at, "Cerrado": r.observed_at, "Origen": ORIGIN,
    } for r in sorted(rows, key=lambda r: r.forecast.key)]


def parse_comparison(payload, reference):
    """Reporte JSON de solo lectura. No carga artefactos ni acepta métricas prefijadas."""
    if len(payload) > 2 * 1024 * 1024:
        raise InputError("El reporte supera el límite técnico de 2 MiB.")
    def reject_constant(value):
        raise InputError("El reporte contiene NaN o Infinity.")
    def unique_object(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise InputError("El JSON repite una clave.")
            result[k] = v
        return result
    try:
        data = json.loads(payload, parse_constant=reject_constant, object_pairs_hook=unique_object)
        if data["schema_version"] != "h4-comparison-1" or data["origin"] != ORIGIN:
            raise InputError("Versión u origen del reporte incompatibles.")
        if data["purpose"] not in ("VALIDATION", "COMPARACION_LOCAL", "TEST_FINAL"):
            raise InputError("Finalidad del reporte inválida.")
        if data["purpose"] == "TEST_FINAL" and data.get("frozen_selection") is not True:
            raise InputError("Test final requiere selección congelada, sin ajustes desde esta vista.")
        models = [model_info(m) for m in data["models"]]
        if len(models) < 2 or len({m.artifact_hash for m in models}) != len(models):
            raise InputError("Se necesitan dos o más modelos distintos con huellas únicas.")
        roles = {m.artifact_hash: raw.get("role", "REFERENCE") for m, raw in zip(models, data["models"])}
        if any(r not in ("ACTIVE", "CANDIDATE", "BASELINE", "REFERENCE") for r in roles.values()):
            raise InputError("Papel de modelo inválido.")
        if list(roles.values()).count("ACTIVE") > 1 or list(roles.values()).count("CANDIDATE") > 1:
            raise InputError("La comparación local admite una referencia ACTIVE y un CANDIDATE.")
        if data.get("decision", "PENDIENTE") not in ("PENDIENTE", "APROBADO", "RECHAZADO"):
            raise InputError("Decisión inválida.")
        if not isinstance(data.get("reason", ""), str) or len(data.get("reason", "")) > 2000:
            raise InputError("Motivo del reporte inválido.")
        if not isinstance(data["rows"], list) or not data["rows"]:
            raise InputError("El reporte no contiene observaciones comparables.")
        groups = {m.artifact_hash: [] for m in models}
        seen = set()
        for row in data["rows"]:
            p, loc, month = row["productId"], row["locationId"], row["mes_objetivo"]
            reference.check_ids(p, loc)
            parse_month(month)
            key = p, loc, month
            if key in seen:
                raise InputError("El reporte repite producto, tienda y mes.")
            seen.add(key)
            observed = validate_quantity(row["observed"])
            rotation = row.get("rotation", "SIN DATO")
            if rotation not in ("ALTA", "MEDIA", "BAJA", "SIN DATO"):
                raise InputError("Rotación de diagnóstico inválida.")
            if set(row["predictions"]) != set(groups):
                raise InputError("Cada fila debe declarar la predicción o abstención de cada modelo.")
            for model in models:
                if model.trained_through >= month:
                    raise InputError("La comparación incluye meses usados para entrenar uno de los modelos.")
                value = row["predictions"][model.artifact_hash]
                prediction = None if value is None else checked_number(value)
                forecast = Forecast(p, loc, month, None, prediction, None, model,
                                    "ABSTENCIÓN" if value is None else "", "REPORTE IMPORTADO")
                groups[model.artifact_hash].append(ClosedObservation(forecast, observed, "REPORTE IMPORTADO", rotation))
        return {"groups": groups, "models": models, "roles": roles, "purpose": data["purpose"],
                "decision": data.get("decision", "PENDIENTE"), "reason": data.get("reason", "")}
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, RecursionError) as exc:
        if isinstance(exc, InputError):
            raise
        raise InputError("Reporte JSON inválido. Revisa el contrato de comparación.") from exc


def comparison_table(report):
    groups = report["groups"]
    common = set.intersection(*[
        {r.forecast.key for r in rows if r.forecast.prediction is not None}
        for rows in groups.values()
    ])
    result = []
    for model in report["models"]:
        rows = groups[model.artifact_hash]
        stats = evaluate(rows)
        shared = evaluate([r for r in rows if r.forecast.key in common])
        result.append({"Modelo": model.name, "Versión": model.version, "Huella": model.artifact_hash,
                       "Papel": report["roles"][model.artifact_hash],
                       "Meses hasta entrenamiento": model.trained_through,
                       "Filas": stats["closed"], "Cobertura": stats["coverage"], "Casos comunes": len(common),
                       "MAE común": shared["MAE"], "RMSE común": shared["RMSE"], "R2 común": shared["R2"]})
    return result


def update_uploaded_comparison(state, payload, reference):
    """Un archivo se carga una sola vez por cambio, sin desplazar al runtime en reruns."""
    if payload is None:
        previous = state.pop("comparison_upload_hash", None)
        state.pop("comparison_upload_error", None)
        if previous is not None and state.get("comparison_source") == "ARCHIVO IMPORTADO":
            state.pop("comparison_report", None)
            state.pop("comparison_source", None)
        return None
    digest = hashlib.sha256(payload).hexdigest()
    if digest != state.get("comparison_upload_hash"):
        state["comparison_upload_hash"] = digest
        state.pop("comparison_upload_error", None)
        state.pop("comparison_report", None)
        state["comparison_source"] = "ARCHIVO IMPORTADO"
        try:
            state["comparison_report"] = parse_comparison(payload, reference)
        except InputError as exc:
            state["comparison_upload_error"] = str(exc)
    return state.get("comparison_upload_error")
