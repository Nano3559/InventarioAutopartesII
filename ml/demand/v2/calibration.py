"""Deriva metadata de calibración desde perfiles congelados, sin generar ventas.

No lee RAW, no usa RNG y no escribe archivos al importarse o al llamarse.
"""
from __future__ import annotations

import math
from copy import deepcopy


def _quantile(values: list[float], p: float) -> float:
    values = sorted(values)
    x = (len(values) - 1) * p
    lo, hi = math.floor(x), math.ceil(x)
    return values[lo] + (values[hi] - values[lo]) * (x - lo)


def derive_reference_parameters(monash: dict, uci: dict) -> dict:
    """Estadísticas descriptivas, no ajuste de un modelo de predicción."""
    observed = monash["observed_values"]
    valid, zero = observed["valid"], observed["zero"]
    positive = valid - zero
    if valid <= 0 or positive <= 0 or not 0 <= zero < valid:
        raise ValueError("Monash requiere observaciones y positivos válidos")
    if observed["negative"] or observed["invalid"] or observed["fractional"]:
        raise ValueError("El perfil de referencia no es un conteo válido")
    series = [s for s in monash["per_series"] if s["missing"] == 0
              and s["invalid"] == 0 and s["observed"] == 51
              and s["negative"] == 0]
    if not series:
        raise ValueError("No hay series completas de referencia")
    for s in series:
        if s["positive"] + s["zeros"] != s["observed"]:
            raise ValueError("Conteos por serie inconsistentes")
    groups = []
    for label, lo, hi in [("BAJA", 0, 1/3), ("MEDIA", 1/3, 2/3), ("ALTA", 2/3, 1)]:
        members = [s for s in series if lo < s["positive"] / s["observed"] <= hi]
        groups.append({"label": label, "count": len(members),
                       "weight": len(members)/len(series),
                       "occurrence_probability": (sum(s["positive"] for s in members) /
                           sum(s["observed"] for s in members)) if members else None,
                       "interval": {"lower_exclusive": lo, "upper_inclusive": hi}})
    if sum(g["count"] for g in groups) != len(series):
        raise ValueError("Serie sin rotación positiva, requiere política explícita")
    pos_mean = observed["mean"] * valid / positive
    if not math.isfinite(pos_mean) or pos_mean < 1:
        raise ValueError("Media positiva inválida")
    c = uci["combined"]
    q = c["positive_quantity"]
    if not 0 < q["median"] <= q["p95"] <= q["p99"] or c["rows"] <= 0:
        raise ValueError("Cuantiles UCI inconsistentes")
    return {
        "monash": {
            "all_observed": {"n": valid, "positive": positive,
                "zero_probability": zero/valid,
                "occurrence_probability": positive/valid,
                "positive_mean": pos_mean,
                "positive_mean_formula": "observed_values.mean * valid / (valid - zero)"},
            "complete_series": {"n": len(series), "excluded_incomplete": monash["series_count"]-len(series),
                "occurrence_probability": sum(s["positive"] for s in series)/sum(s["observed"] for s in series),
                "rotation_groups": groups,
                "zero_run_quantiles": {str(p): _quantile([s["longest_zero_run"] for s in series], p)
                                       for p in [0.5, 0.9, 0.95]},
                "warning": "Rotación significa frecuencia de meses positivos, no importancia comercial. No se eliminan trayectorias iguales sin prueba de duplicación."},
            "missing_probability_descriptive_only": observed["missing"]/(valid+observed["missing"]),
            "missing_policy": "No imputar cero. No usar esta tasa como averías aleatorias: los faltantes son finales de serie.",
            "transfer_limit": "Empresa y época distintas. Media de positivos global y grupos de series completas tienen poblaciones diferentes. No se afirma reproducir exactamente la distribución conjunta."},
        "uci": {
            "rows": c["rows"], "positive_quantity_quantiles": deepcopy(q),
            "p95_over_median": q["p95"]/q["median"],
            "p99_over_median": q["p99"]/q["median"],
            "negative_quantity_line_fraction": c["quantity"]["negative"]/c["rows"],
            "exact_repeat_occurrence_fraction": c["exact_duplicate_rows_after_first"]/c["rows"],
            "cross_sheet_repeat_occurrences": c["cross_sheet_duplicate_occurrences"],
            "use": "Referencias descriptivas de cola y problemas de calidad, nunca tasas de devoluciones, mayoristas o precios para RepuestoPro.",
            "excluded_transfer": ["GBP a Bs", "precios nominales", "etiqueta mayorista inferida por cantidad", "tasa causal de cancelación", "elasticidad precio", "identificadores"]}
    }


def build_calibration_contract(monash: dict, uci: dict, scenario_design: dict) -> dict:
    refs = derive_reference_parameters(monash, uci)
    params = deepcopy(scenario_design["parameter_policy"]["parameters"])
    decisions = {}
    for name, p in params.items():
        decisions[name] = {"levels": p["levels"], "unit": p["unit"],
            "basis": "ACADEMIC_ASSUMPTION", "empirically_estimated": False,
            "reason": "Cobertura explícita de pruebas, no prevalencia ni relación comercial medida.",
            "application": "FORCED_COVERAGE_AND_SENSITIVITY_ONLY"}
    decisions["noise"].update(basis="REFERENCE_INFORMED_WITH_ASSUMED_MECHANISM",
        reason="Monash fundamenta intermitencia y media positiva. El perfil no identifica dispersión condicional ni dependencia temporal.",
        application="Hurdle: indicador Bernoulli por mes y tamaño entero positivo condicionado.",
        occurrence_groups=refs["monash"]["complete_series"]["rotation_groups"],
        positive_size={"primary": "GEOMETRIC_ON_1_INFINITY", "mean": refs["monash"]["all_observed"]["positive_mean"],
            "success_probability": 1/refs["monash"]["all_observed"]["positive_mean"],
            "alternative": "ZERO_TRUNCATED_POISSON_MATCHING_SAME_POSITIVE_MEAN",
            "alternative_equation": "lambda / (1-exp(-lambda)) = positive_mean",
            "warning": "Mecanismos hipotéticos. No se estimó varianza ni se ajustó una distribución completa."})
    decisions["bulk_size"].update(basis="UCI_TAIL_REFERENCE_WITH_ASSUMED_MULTIPLIERS",
        reason="Las razones p95/mediana y p99/mediana UCI apoyan probar colas. Los multiplicadores 2,4,8 son pruebas moderadas, no cuantiles automotrices.",
        uci_ratios={"p95_over_median": refs["uci"]["p95_over_median"], "p99_over_median": refs["uci"]["p99_over_median"]})
    decisions["trend_annual"]["reason"] = "Probar caída, estabilidad y crecimiento moderado. No extrapolar 1998-2002 a Bolivia ni ajustar usando TEST."
    decisions["seasonality"]["reason"] = "Amplitud hasta 20% y fase por serie supuestas. Sin trasladar fiestas británicas ni estimar estacionalidad con cobertura cambiante."
    decisions["store_level"]["reason"] = "Variación simétrica de 25%, sin evidencia de tiendas comparable en estas fuentes. No asignar por orden de ID."
    decisions["price_change"]["reason"] = "Cambios relativos de sensibilidad. El ejemplo 120 a 150 equivale a 25%. UCI no identifica elasticidad causal de repuestos."
    decisions["fx_change"]["reason"] = "Escenarios de dirección e intensidad. Ninguna fuente registra Bs/USD. No son cotizaciones ni pronósticos monetarios."
    for name in ["fx_age", "pass_through", "pass_through_delay"]:
        decisions[name]["reason"] = "Contrastar información reciente/antigua y transmisión nula/parcial/completa con retraso. Sin evidencia comercial de esos coeficientes."
    for name in ["stockout", "stock_coverage", "receipt_fraction", "supplier_lead_days"]:
        decisions[name]["reason"] = "Prueba operativa con límites de calendario y conservación de unidades. Monash y UCI no observan stock ni plazos del proveedor."
    decisions["supplier_lead_days"]["application"] = "CONTEXT_ONLY_NOT_FORECAST_FEATURE"
    for name in ["entity_age", "modality_coverage", "boundary_clock"]:
        decisions[name]["basis"] = "CONTRACT_BOUNDARY_RULE"
        decisions[name]["reason"] = "Límites de los tres lags, proporciones con conteos enteros y reloj de conocimiento. No requiere estimación comercial."
    decisions["regime_change"]["reason"] = "Cambios de nivel de estrés, simétricos alrededor de uno. Ninguna fuente demuestra estos tamaños para RepuestoPro."
    return {
        "contract_version": "v2-calibration-1", "stage": "V2-05A",
        "status": "ACADEMIC_PARAMETERS_JUSTIFIED_NOT_GENERATED",
        "scope": "Referencia estadística y supuestos fijados antes de generar datos. No calibración comercial.",
        "seed": 42, "reference_statistics": refs, "parameter_decisions": decisions,
        "simulation_recipe": {
            "status": "SPECIFICATION_ONLY_NOT_EXECUTED",
            "rotation": "Asignar grupo a la pareja producto-tienda con pesos de series completas, seed 42 y claves estables. Usar probabilidad del grupo. No copiar ni mapear series externas.",
            "rotation_weights": {g["label"]: g["weight"] for g in refs["monash"]["complete_series"]["rotation_groups"]},
            "primary_positive_mean_multiplier": 1,
            "scale_sensitivity_multipliers": [1, 3, 10],
            "scale_note": "La escala primaria es referencia externa, no volumen propio. 3 y 10 son estrés separados, no tasas estimadas ni pesos.",
            "time_effects": "Multiplicar media positiva por (1+annual_trend)^(elapsed_months/12), factor tienda y 1+a*sin(2*pi*mes/12+fase). Amplitud a entre 0 y 0.2. Media positiva nunca menor a 1. No alterar entradas con futuros.",
            "price_elasticity_sensitivity": [0, -0.5, -1],
            "price_response": "Media positiva *= (precio_vigente/precio_base)^elasticidad, aplicada por modalidad. Parámetros supuestos y escenarios separados, incluyendo efecto nulo. No volver a aplicar variacion_precio como otro efecto.",
            "fx_response": "Una trayectoria Bs/USD común a todas las parejas por ejecución. FX afecta costo importado y después precio mediante pass_through y retraso. No sumar otro efecto FX directo sobre ventas por defecto.",
            "fx_base_bs_per_usd": 10,
            "fx_base_warning": "Ancla ficticia para aritmética. No cotización actual, oficial ni paralela. Ninguna consulta externa la respalda.",
            "price_base_retail_bs": 120, "price_base_wholesale_bs": 108, "cost_base_bs": 80,
            "price_base_warning": "Anclas ficticias 120/108/80, no Product actual ni historia propia. Descuento mayorista 10% y margen son supuestos. No exportarlos como features extra.",
            "cost_imported_fraction": 1,
            "cost_formula": "cost_t = cost_base * (fx_t/fx_base). Hipótesis 100% costo importado para escenario, no estructura contable real.",
            "pricing_policy": "precio_t = precio_base * (1 + pass_through * (cost_t_lag/cost_base - 1)); aplicar cambio de precio de escenario explícito una sola vez. Si viola costo <= mayor <= menor, rechazar escenario inválido o registrar decisión de repricing explícita antes del evento. No reparar silenciosamente.",
            "wholesale_unit_share_sensitivity": [0, 0.25, 0.75, 1],
            "wholesale_share_note": "Niveles ficticios de sensibilidad. Etiqueta viene de modalidad simulada explícita. Distribuir enteros conservando total, sin inferir modalidad por precio o tamaño. Multiplicador bulk afecta solo evento forzado, no cada mes.",
            "stock_accounting": "Pedidos latentes de simulación no son target. Atender unidades enteras cronológicamente hasta stock vendible, con entradas solo al recibir y devoluciones solo tras inspección. Registrar días observados y días sin stock de forma independiente.",
            "target": "Unidades brutas válidas atendidas por mes. No restar devoluciones futuras ni etiquetar como demanda perdida.",
            "base_distribution": "Referencia de frecuencia positiva y tamaño Monash. No sumar conjuntamente todos los niveles de estrés ni imponer todos los adversos al dataset de entrenamiento.",
            "scenario_frequency_policy": "Sin prevalencia estimada: 57 casos y 8 combinaciones se verifican en suite separada de cobertura forzada. No usar su proporción como pesos poblacionales ni como distribución comercial.",
            "scenario_training_policy": "Solo casos validados y elegibles. Una mezcla de estrés para experimentos será una variante separada identificada, no una contaminación silenciosa del conjunto base.",
            "random_streams": "Streams independientes para asignación, calendario, conteos, precios/FX, stock, modo y escenarios. Derivar seeds con SHA-256 de seed, versión y nombre, nunca hash() de Python.",
            "availability": "Conservar event_at y available_at. Solo información disponible al corte alimenta features. Cambios intra-mes no anunciados afectan resultado, no entradas.",
            "missing": "Ceros solo observados. Valores opcionales desconocidos permanecen null. Falta de lags no se disfraza con cero.",
        },
        "future_checks": {
            "exact": ["unidades enteras y no negativas", "conservación de stock y modalidad", "mayor <= menor y costo <= ambos", "sin información posterior al corte", "57 casos y 8 combinaciones trazables"],
            "reference_only": ["fracción cero por grupo", "media de tamaño positivo", "rachas de ceros", "colas de pedidos", "dispersión por pareja"],
            "numeric_validation": "Antes de aplicar efectos, para N Bernoulli independientes por grupo usar margen diagnóstico 3*sqrt(p*(1-p)/N). Con heterogeneidad, dependencia o efectos, no reutilizarlo como test formal. No exigir 74.78% exacto ni máxima 52.",
            "no_metric_tuning": "No ajustar generador, escenarios o seed para ganar a baseline o mirando TEST.",
            "heldout": "Congelar nueva ejecución independiente y manifiesto de TEST antes de seleccionar modelos. Periodos de V1 no constituyen TEST nuevo. V2-08 no está ejecutado."
        },
        "limitations": ["No elasticidad causal, demanda perdida, cotización real ni plazo comercial certificados.",
            "UCI tiene repetidos y cancelaciones sin limpiar. Sus cuantiles son descriptivos de líneas positivas con esas limitaciones, no distribución de pedidos depurada.",
            "El mecanismo de conteos, independencia temporal y efectos económicos son hipótesis. Un modelo puede aprender la fórmula sintética.",
            "La configuración especifica diseño implementable, no acredita funcionamiento del generador aún inexistente."],
        "dataset_created": False, "raw_modified": False, "trained": False,
    }
