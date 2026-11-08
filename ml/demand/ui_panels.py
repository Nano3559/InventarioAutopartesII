"""Vistas de Ross para inferencia, errores, monitoreo y comparación."""
import csv
import hashlib
import json
from dataclasses import asdict, replace

import pandas as pd
import streamlit as st

from simulator_inputs import HERE, InputError, offset_month, validate_quantity
from ui_analysis import comparison_table, evaluate, group_errors, monitor, parse_comparison, record_table, update_uploaded_comparison
from ui_runtime import ObservationJournal, active_info, discover_runtime, issue_forecast, request_fingerprint


def journal():
    if "observation_journal" not in st.session_state:
        st.session_state.observation_journal = ObservationJournal()
    return st.session_state.observation_journal


def runtime():
    if "h4_runtime" not in st.session_state:
        try:
            st.session_state.h4_runtime = discover_runtime()
        except Exception:
            # No mostrar trazas, rutas privadas o mensajes arbitrarios de un proveedor.
            st.session_state.h4_runtime = None
            st.session_state.runtime_error = "No se pudo iniciar demand_runtime.py. Revisa su contrato local."
    return st.session_state.h4_runtime


def reconnect_runtime():
    st.session_state.pop("h4_runtime", None)
    st.session_state.pop("runtime_error", None)


def rotation_for(product_id, location_id, month):
    folder = HERE / "data" / "escenarios_v1_1"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    payload = (folder / "escenarios_metadatos.csv").read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest["hashes"]["escenarios_metadatos.csv"]:
        raise InputError("Los metadatos de rotación no coinciden con su manifiesto.")
    for row in csv.DictReader(payload.decode("utf-8").splitlines()):
        if (int(row["productId"]), int(row["locationId"]), row["mes"]) == (product_id, location_id, month):
            return row["rotacion_simulada"]
    return "SIN DATO"


def formatted(value, percent=False):
    if value is None:
        return "No disponible"
    return f"{value:.1%}" if percent else f"{value:.3f}"


def reveal_observed(key, widget_key):
    value = st.session_state[widget_key]
    if value is not None:
        journal().reveal(key, value)


def render_prediction(reference, product_id, location_id, month, features, input_error, scenario="NORMAL"):
    st.subheader("Predicción interactiva")
    st.button("RECONECTAR RUNTIME", on_click=reconnect_runtime,
              help="Crea una instancia local al incorporar el proveedor de Erika. No entrena.")
    store, provider = journal(), runtime()
    key = product_id, location_id, month
    info = None
    try:
        info = active_info(provider)
    except Exception:
        st.error("El modelo ACTIVE no cumple el contrato. La inferencia permanece bloqueada.")
    if st.session_state.get("runtime_error"):
        st.error(st.session_state.runtime_error)
    if info is None:
        st.warning("MODELO NO DISPONIBLE · Conecta el runtime y el artefacto de Erika para habilitar PREDECIR.")
    else:
        st.caption(f"ACTIVE: {info.label} · Entrenado hasta {info.trained_through} · Origen SIMULACIÓN")
    closed = key in store.closed
    locked = store.is_locked(key)
    can_predict = info is not None and features is not None and not locked and info.trained_through < month
    if info and info.trained_through >= month:
        st.warning("Corte incompatible: este mes no es posterior al entrenamiento de ACTIVE.")
    if st.button("PREDECIR", disabled=not can_predict, type="primary"):
        try:
            forecast = issue_forecast(reference, product_id, location_id, month, features, provider, scenario=scenario)
            store.issue(forecast)
        except Exception:
            fallback = issue_forecast(reference, product_id, location_id, month, features, None, scenario=scenario)
            store.issue(replace(fallback, model=info, reason="ERROR DE INFERENCIA"))
            st.error("La inferencia falló. Se registra una abstención, sin predicción ficticia ni pérdida de cierres anteriores.")
    if st.button("REGISTRAR ABSTENCIÓN", disabled=locked or can_predict):
        # También permite medir cobertura sin fabricar una predicción.
        try:
            store.issue(issue_forecast(reference, product_id, location_id, month, None,
                                       provider if info is not None else None,
                                       input_error or ("CORTE INCOMPATIBLE" if info else "MODELO NO DISPONIBLE"), scenario))
        except InputError as exc:
            st.error(str(exc))
    forecast = store.pending.get(key)
    if closed:
        st.success("Mes cerrado. La emisión y su observado no se sobrescriben.")
        st.dataframe(pd.DataFrame(record_table([store.closed[key]])), hide_index=True, width="stretch")
    elif forecast:
        st.caption(f"Versión congelada de esta emisión: {forecast.model.label if forecast.model else 'SIN MODELO'}")
        if forecast.prediction is not None:
            st.metric("Predicción del mes objetivo · unidades", formatted(forecast.prediction))
            if forecast.prediction < 0:
                st.warning("Salida negativa del modelo: se conserva sin recortar para analizar su error.")
            values = [
                {"Mes": offset_month(month, -lag), "Unidades": forecast.features[lag-1], "Serie": "Historia emitida"}
                for lag in (3, 2, 1)
            ] + [{"Mes": month, "Unidades": forecast.prediction, "Serie": "Predicción"}]
            st.vega_lite_chart(pd.DataFrame(values), {
                "mark": {"type": "line", "point": True},
                "encoding": {"x": {"field": "Mes", "type": "ordinal"},
                             "y": {"field": "Unidades", "type": "quantitative"},
                             "color": {"field": "Serie", "type": "nominal"},
                             "tooltip": [{"field": "Mes"}, {"field": "Unidades"}, {"field": "Serie"}]},
            }, width="stretch")
        else:
            st.info(f"Abstención registrada: {forecast.reason}")
        st.caption(f"Emisión {forecast.issued_at} · Entrada congelada {request_fingerprint(forecast)[:12]} · SIMULACIÓN")
        st.subheader("Resultado posterior a la emisión")
        widget_key = f"observed_{product_id}_{location_id}_{month}"
        if key in store.revealed:
            observed = store.revealed[key]
            st.number_input("Venta observada del mes", value=observed, min_value=0,
                            max_value=2**53-1, step=1, key=f"{widget_key}_revealed", disabled=True)
            st.caption("Observado revelado: entradas y predicción bloqueadas. Cierra el mes o restablece la sesión para otra hipótesis.")
        else:
            observed = st.number_input("Venta observada del mes", value=None, min_value=0,
                                       max_value=2**53-1, step=1, key=widget_key,
                                       on_change=reveal_observed, args=(key, widget_key))
        complete = st.checkbox("El mes objetivo está cerrado y completo", key=f"closed_{product_id}_{location_id}_{month}")
        if st.button("REGISTRAR OBSERVADO", disabled=not complete):
            try:
                validate_quantity(observed)
                rotation = rotation_for(product_id, location_id, month)
                store.close(key, observed, rotation)
                st.rerun()
            except InputError as exc:
                st.error(str(exc))
    st.caption("Editar o predecir no entrena. El observado nunca se envía a predict(features).")
    a, b = st.columns(2)
    with a:
        st.button("GENERAR SIGUIENTE MES", disabled=True, width="stretch")
    with b:
        st.button("AVANZAR MES", disabled=True, width="stretch")
    st.caption("Generación y reloj: pendientes del motor de Erika. Registrar observado cierra evidencia de esta vista, no ejecuta ese motor.")


def render_monitoring():
    st.subheader("Historial, errores y monitoreo local")
    rows = list(journal().closed.values())
    if not rows:
        st.info("Aún no hay meses cerrados. Las métricas no se inventan ni se calculan sobre meses abiertos.")
        return
    models = list(dict.fromkeys(r.forecast.model for r in rows))
    chosen = st.selectbox("Modelo y versión a analizar", models,
                          format_func=lambda m: m.label if m else "Sin modelo · abstenciones")
    selected = [r for r in rows if r.forecast.model == chosen]
    stats = evaluate(selected)
    for col, label, value in zip(st.columns(4), ("MAE", "RMSE", "R²", "Cobertura"),
                                 (stats["MAE"], stats["RMSE"], stats["R2"], stats["coverage"])):
        col.metric(label, formatted(value, label == "Cobertura"))
    st.caption(f"{stats['closed']} cierres · {stats['n']} predicciones · {stats['abstentions']} abstenciones. "
               "R² no es porcentaje de precisión. No disponible con menos de dos casos o target constante.")
    st.caption(f"Baseline sobre {stats['baseline']['n']} casos comunes: MAE {formatted(stats['baseline']['MAE'])}. "
               f"Modelo sobre esos mismos casos: MAE {formatted(stats['model_comparable']['MAE'])}.")
    frame = pd.DataFrame(record_table(selected))
    st.dataframe(frame, hide_index=True, width="stretch")
    for dimension in ("Tienda", "Producto", "Rotación", "Mes"):
        with st.expander(f"Errores por {dimension.lower()}"):
            st.dataframe(pd.DataFrame(group_errors(selected, dimension)), hide_index=True, width="stretch")
    pairs = list(dict.fromkeys((r.forecast.product_id, r.forecast.location_id) for r in selected))
    pair = st.selectbox("Serie para evolución y drift", pairs, format_func=lambda p: f"Producto {p[0]} · Tienda {p[1]}")
    series = [r for r in selected if r.forecast.key[:2] == pair]
    chart = pd.DataFrame(record_table(series)).sort_values("Mes")
    st.line_chart(chart, x="Mes", y=["Observado", "Predicción", "Baseline"], x_label="Mes", y_label="Unidades")
    st.line_chart(chart, x="Mes", y="Error absoluto", x_label="Mes", y_label="Error en unidades")
    result = monitor(series)
    st.write(f"**Estado del modelo: {result['status']}**")
    st.caption(result["reason"])
    st.caption("Criterio demostrativo: dos ventanas consecutivas de tres meses por serie y versión. "
               "No prueba estadística de drift ni política comercial. Nunca inicia entrenamiento.")
    st.dataframe(pd.DataFrame([{
        "MAE anterior": result["previous_mae"], "MAE reciente": result["recent_mae"],
        "Baseline anterior": result["baseline_previous"], "Baseline reciente": result["baseline_recent"],
        "Media lag1 anterior": result["lag1_previous"], "Media lag1 reciente": result["lag1_recent"],
    }]), hide_index=True, width="stretch")
    st.download_button("DESCARGAR SESIÓN JSON", json.dumps({
        "schema_version": "h4-session-1", "origin": "SIMULACION",
        "session_id": journal().session_id, "generator_seed": None,
        "records": [asdict(r) for r in rows],
    }, ensure_ascii=False, allow_nan=False, indent=2), file_name="h4-sesion-simulacion.json", mime="application/json")


def render_comparison(reference):
    st.subheader("Comparación visual de modelos y candidato")
    st.caption("Solo lectura. Esta vista no entrena, selecciona, promueve o revierte modelos. "
               "Una menor media no prueba por sí sola que deba activarse un candidato.")
    uploaded = st.file_uploader("Reporte de Erika · JSON h4-comparison-1", type=["json"], max_upload_size=2)
    upload_error = update_uploaded_comparison(st.session_state, uploaded.getvalue() if uploaded is not None else None, reference)
    if upload_error:
        st.error(upload_error)
    provider = runtime()
    can_read = provider is not None and callable(getattr(provider, "get_comparison_report", None))
    if st.button("LEER COMPARACIÓN DEL RUNTIME", disabled=not can_read):
        try:
            payload = provider.get_comparison_report()
            report = parse_comparison(json.dumps(payload, allow_nan=False).encode(), reference)
            st.session_state.comparison_report = report
            st.session_state.comparison_source = "RUNTIME LOCAL"
        except Exception:
            st.session_state.pop("comparison_report", None)
            st.error("No se pudo validar la comparación del runtime. No se sustituye por datos de ejemplo.")
    report = st.session_state.get("comparison_report")
    if report is None:
        st.info("Sin reporte de comparación. Se habilitarán tablas y gráficos cuando Erika entregue resultados.")
        return
    table = pd.DataFrame(comparison_table(report))
    st.caption(f"Origen: SIMULACIÓN · Fuente: {st.session_state.get('comparison_source', 'REPORTE LOCAL')} · Uso: {report['purpose']}")
    st.dataframe(table, hide_index=True, width="stretch")
    chart = table.assign(Identidad=table["Modelo"] + " · " + table["Versión"] + " · " + table["Huella"].str[:8])
    if table["MAE común"].notna().any():
        st.bar_chart(chart, x="Identidad", y="MAE común", y_label="Error en unidades")
    else:
        st.warning("No hay filas comunes con predicción de todos los modelos. No se declara una mejora.")
    st.caption("Métricas recalculadas sobre las mismas filas elegibles, con coberturas por separado. "
               "El archivo importado no certifica por sí solo la procedencia o el protocolo experimental.")
    active = table[table["Papel"] == "ACTIVE"]
    candidate = table[table["Papel"] == "CANDIDATE"]
    if len(active) == len(candidate) == 1 and pd.notna(active.iloc[0]["MAE común"]):
        difference = candidate.iloc[0]["MAE común"] - active.iloc[0]["MAE común"]
        label = "menor" if difference < 0 else "mayor" if difference > 0 else "igual"
        st.write(f"MAE de CANDIDATE {label} al de ACTIVE en las filas comunes. Esto no activa el candidato.")
    st.write(f"**Decisión registrada por el proveedor: {report['decision']}**")
    st.write(report["reason"] or "Sin justificación adjunta. No hay promoción automática.")
    chosen = st.selectbox("Modelo para desglosar el reporte", report["models"], format_func=lambda m: m.label)
    rows = report["groups"][chosen.artifact_hash]
    for dimension in ("Tienda", "Rotación", "Mes", "Producto"):
        with st.expander(f"Reporte: errores por {dimension.lower()}"):
            st.dataframe(pd.DataFrame(group_errors(rows, dimension)), hide_index=True, width="stretch")
    st.caption("SIN DATO en rotación indica que el reporte no adjunta ese metadato. No se infiere a partir del ID.")
