"""Vistas de Ross para inferencia, errores, monitoreo y comparación."""
import csv
import json
import uuid
from dataclasses import asdict, replace

import pandas as pd
import streamlit as st

from demand_engine import create_session
from pair_contexts import bind_pair_context
from lifecycle_registry import LifecycleRegistry
from simulator_inputs import (
    HERE, InputError, offset_month, read_required, validate_quantity, verified_bytes,
)
from ui_analysis import comparison_table, evaluate, group_errors, monitor, parse_comparison, record_table, update_uploaded_comparison
from ui_runtime import ObservationJournal, active_info, discover_runtime, issue_forecast, request_fingerprint


def journal():
    if "observation_journal" not in st.session_state:
        st.session_state.observation_journal = ObservationJournal()
    return st.session_state.observation_journal


def engine(reference=None):
    """Autoridad única de reloj, lags, observados y cierre temporal de la sesión."""
    if "demand_session" not in st.session_state:
        st.session_state.demand_session = create_session(reference)
    st.session_state.demand_session.bind_journal(journal().session_id)
    return st.session_state.demand_session


def runtime():
    bind_selected_pair()
    if "h4_runtime" not in st.session_state:
        try:
            st.session_state.h4_runtime = discover_runtime()
        except Exception:
            # No mostrar trazas, rutas privadas o mensajes arbitrarios de un proveedor.
            st.session_state.h4_runtime = None
            st.session_state.runtime_error = "No se pudo iniciar demand_runtime.py. Revisa su contrato local."
    provider = st.session_state.h4_runtime
    if callable(getattr(provider, "bind_lifecycle", None)):
        try:
            provider.bind_lifecycle(lifecycle_binding())
        except Exception:
            st.session_state.runtime_error = "Registro local o referencia no verificable. Inferencia bloqueada."
            return None
    return provider


def lifecycle_registry():
    eng = engine()
    current = st.session_state.get("lifecycle_registry")
    if current is None or current.session_id != eng.session_id:
        if current is not None:
            st.session_state.setdefault("lifecycle_archives", []).append(current)
        current = LifecycleRegistry(eng.session_id)
        st.session_state.lifecycle_registry = current
    return current


def lifecycle_binding():
    selected = engine().status()
    return lifecycle_registry().bind(selected["product_id"], selected["location_id"])


def record_reset():
    """Una evidencia de reset para todos los pares, antes de descartar estado."""
    registry = st.session_state.get("lifecycle_registry")
    if registry is None:
        archive_session_before_reset(None)
        return
    contexts = dict(st.session_state.get("pair_contexts", {}))
    selected = st.session_state.get("selected_pair_context")
    if selected:
        contexts[selected] = dict(h4_runtime=st.session_state.get("h4_runtime"),
                                  retraining_result=st.session_state.get("retraining_result"))
    affected = []
    for pair, context in sorted(contexts.items()):
        provider = context.get("h4_runtime")
        affected.append(dict(product_id=pair[0], location_id=pair[1],
                             active_before=provider.get_active_model() if provider else None,
                             active_after=None, candidate_run_id=(context.get("retraining_result") or {}).get("run_id")))
    registry.bind(*selected).emit("RESET", key="SESSION_RESET", state_before="LOCAL_CONTEXTS",
        state_after="INACTIVE", affected_contexts=affected,
        reason="RESTABLECER EDICIÓN explícito; descarta contextos, no reactiva modelos.", result="RESET", affects_active=True)
    archive_session_before_reset(registry)
    st.session_state.setdefault("lifecycle_archives", []).append(registry)
    st.session_state.pop("lifecycle_registry", None)


def archive_session_before_reset(registry):
    # Snapshot de evidencia anterior al descarte; jamás se utiliza para restaurar.
    from session_export import build_session_export
    try:
        archived = build_session_export(engine(), journal(), st.session_state, registry,
                                        phase="PRE_RESET_SNAPSHOT")
    except Exception:
        # No certificar un cierre inconsistente ni impedir el reset por no poder exportarlo.
        archived = dict(status="UNVERIFIED", engine_session_id=engine().session_id,
                        reason="No se pudo verificar el snapshot previo al reset.",
                        history_status="UNVERIFIED_SOURCES",
                        unverified_engine=engine().export_state(),
                        unverified_closed_records=[asdict(r) for r in journal().closed.values()])
    st.session_state.setdefault("session_export_archives", []).append(archived)


def render_session_export():
    from session_export import build_session_export
    try:
        document = build_session_export(engine(), journal(), st.session_state,
            st.session_state.get("lifecycle_registry"),
            st.session_state.get("session_export_archives", []))
        st.session_state.last_session_export = document
        st.download_button("DESCARGAR SESIÓN JSON",
            json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2),
            file_name="h4-sesion-simulacion.json", mime="application/json")
        st.caption("h4-session-1 compatible · Trazabilidad h4-traceability-1 · Solo evidencia, sin activación desde JSON.")
    except Exception:
        st.session_state.pop("last_session_export", None)
        st.error("No se puede exportar una sesión verificable: revisa cierres, referencias y procedencia.")


def render_lifecycle():
    with st.expander("Registro local de versiones y decisiones · solo evidencia"):
        registries = [*st.session_state.get("lifecycle_archives", [])]
        if st.session_state.get("lifecycle_registry"):
            registries.append(st.session_state.lifecycle_registry)
        try:
            records = [r for registry in registries for r in registry.records()]
            st.caption("Orden por sesión y secuencia. El reset conserva la evidencia; ningún registro activa modelos.")
            st.dataframe(pd.DataFrame([dict(Sesión=r["session_id"], Secuencia=r["sequence"],
                Fecha=r["timestamp"], Producto=r["product_id"], Tienda=r["location_id"],
                Evento=r["type"], Versión=(r["model"] or {}).get("version"),
                Resultado=r["result"], Huella=r["event_sha256"]) for r in records]), hide_index=True)
        except Exception:
            st.error("Registro local alterado o incompleto. No se utiliza para activar modelos.")


def bind_selected_pair():
    eng = engine()
    selected = eng.status()
    bind_pair_context(st.session_state, eng.session_id,
                      selected["product_id"], selected["location_id"])


def compare_reference_models(features, *, complete=True):
    """Adaptador R30 para una acción explícita de Ross; no dibuja ni activa modelos."""
    from reference_runtime import ReferenceComparisonSession
    bind_selected_pair()
    eng = engine()
    selected = eng.status()
    if "reference_comparison_session" not in st.session_state:
        st.session_state.reference_comparison_session = ReferenceComparisonSession(
            eng.session_id, selected["product_id"], selected["location_id"])
    service = st.session_state.reference_comparison_session
    service.bind_lifecycle(lifecycle_binding())
    result = service.predict(eng, features, runtime(), complete=complete)
    st.session_state.reference_comparison_result = result
    return result


def reconnect_runtime():
    provider = st.session_state.get("h4_runtime")
    before = provider.get_active_model() if provider else None
    lifecycle_binding().emit("RUNTIME_DISCONNECTED", key=uuid.uuid4().hex,
        model=before, previous_reference=before, active_before=before, active_after=None,
        state_before="ACTIVE" if before else "INACTIVE", state_after="INACTIVE",
        reason="RECONECTAR RUNTIME explícito del par actual.", result="DISCONNECTED", affects_active=True)
    st.session_state.pop("h4_runtime", None)
    st.session_state.pop("runtime_error", None)


def render_retraining():
    """Acción explícita independiente: no cambia el proveedor de inferencia."""
    from retraining import RetrainingSession
    bind_selected_pair()
    st.subheader("Ensayo incremental · SIMULACIÓN")
    st.caption("Requiere 12 cierres nuevos del par seleccionado: octubre–diciembre 2026 "
               "como historia, enero–junio 2027 para ajuste y julio–septiembre 2027 reservados. "
               "Mínimo demostrativo, sin garantía de calidad. Entrenar no activa el candidato.")
    eng = engine()
    if st.button("ENSAYAR REENTRENAMIENTO"):
        try:
            if "retraining_session" not in st.session_state:
                st.session_state.retraining_session = RetrainingSession(eng.session_id)
            st.session_state.retraining_session.bind_lifecycle(lifecycle_binding())
            with st.spinner("Validando cierres y entrenando un candidato independiente…"):
                result = st.session_state.retraining_session.train(eng, journal())
            st.session_state.retraining_result = result
            st.session_state.pop("retraining_error", None)
        except InputError as exc:
            st.session_state.retraining_error = str(exc)
        except Exception:
            st.session_state.retraining_error = "El ensayo falló. ACTIVE y los cierres anteriores se conservan."
    if st.session_state.get("retraining_error"):
        st.warning(st.session_state.retraining_error)
    result = st.session_state.get("retraining_result")
    if result:
        st.success(f"CANDIDATE {result['run_id']} · producto {result['product_id']} · "
                   f"tienda {result['location_id']} · {result['n_train']} filas de ajuste · "
                   f"{result['n_reserved']} reservadas. Sin promoción automática.")
        st.caption("Métricas comparativas no disponibles hasta la comparación posterior válida.")


def render_candidate_decision():
    """Acciones locales separadas de la vista JSON de Ross, siempre de solo lectura."""
    from model_comparison import ComparisonSession, BLOCK_REASON, ARCHIVE_RUN
    st.subheader("Comparación y decisión local · SIMULACIÓN")
    st.warning(BLOCK_REASON)
    provider = runtime()
    eng = engine()
    run = st.session_state.get("retraining_result")
    pair = eng.status()
    # El ejemplo archivado pertenece exclusivamente a producto 1 / tienda 5.
    # No se incorpora al registro de candidatos nuevos de ninguna sesión.
    archive_available = (pair["product_id"], pair["location_id"]) == (1, 5)
    st.caption(f"Candidato a comparar: {run['run_id'] if run else 'sin candidato del par'}. "
               + (f"Referencia histórica disponible: {ARCHIVE_RUN}, verificada con huella independiente."
                  if not run and archive_available else ""))
    available = False
    try:
        available = active_info(provider) is not None
    except Exception:
        pass
    if not available:
        st.caption("COMPARAR requiere un ACTIVE explícito en esta sesión. Esta acción no activa V1.")
    if st.button("COMPARAR CANDIDATE", disabled=not available or not (run or archive_available)):
        try:
            if "candidate_comparison_session" not in st.session_state:
                st.session_state.candidate_comparison_session = ComparisonSession(eng.session_id)
            service = st.session_state.candidate_comparison_session
            service.bind_lifecycle(lifecycle_binding())
            if run:
                if (run["product_id"], run["location_id"]) != (pair["product_id"], pair["location_id"]):
                    raise InputError("El candidato no pertenece al par seleccionado.")
                result = service.compare(provider, st.session_state.retraining_session, run["run_id"])
            else:
                result = service.compare_archived(provider)
            st.session_state.candidate_comparison_result = result
            # Reutiliza el contrato existente de Ross sin convertirlo en autorización.
            st.session_state.comparison_report = parse_comparison(json.dumps(result["ross_report"]).encode(), eng._reference)
            st.session_state.comparison_source = "COMPARACIÓN LOCAL VERIFICADA"
            st.session_state.pop("candidate_decision_error", None)
        except Exception:
            st.session_state.candidate_decision_error = "No se pudo verificar la comparación. ACTIVE permanece intacto."
    result = st.session_state.get("candidate_comparison_result")
    if result:
        st.write(f"Decisión: **{result['eligibility']}** · {result['n_train']} filas de ajuste · "
                 f"{result['n_comparison']} observaciones de comparación.")
        st.caption("R² de tres observaciones es descriptivo; no acredita superioridad estadística.")
        st.dataframe(pd.DataFrame([dict(Modelo=m["version"], **result["metrics"][m["artifact_hash"]])
                                   for m in (result["active"], result["candidate"])]), hide_index=True)
    reason = st.text_input("Motivo de decisión o rollback", key="candidate_decision_reason")
    if st.button("RECHAZAR CANDIDATE", disabled=result is None or not reason.strip()):
        try:
            decision = st.session_state.candidate_comparison_session.reject(result["id"], reason)
            st.session_state.candidate_rejection = decision
        except Exception:
            st.session_state.candidate_decision_error = "No se pudo registrar el rechazo de esta sesión."
    st.button("PROMOVER CANDIDATE", disabled=True, help=BLOCK_REASON)
    if st.button("ROLLBACK LOCAL", disabled=provider is None or not reason.strip()):
        try:
            provider.rollback(reason)
            st.session_state.candidate_rollback_notice = "Rollback aplicado solo a esta sesión. Los registros previos se conservan."
            st.rerun()
        except Exception:
            st.session_state.candidate_decision_error = "Rollback no disponible o referencia anterior no verificable."
    if st.session_state.get("candidate_rejection"):
        st.info("REJECTED_FOR_PROMOTION · " + st.session_state.candidate_rejection["reason"])
    if st.session_state.get("candidate_rollback_notice"):
        st.success(st.session_state.candidate_rollback_notice)
    if st.session_state.get("candidate_decision_error"):
        st.error(st.session_state.candidate_decision_error)


def rotation_for(product_id, location_id, month):
    folder = HERE / "data" / "escenarios_v1_1"
    manifest = json.loads(read_required(folder / "manifest.json", "manifest.json").decode("utf-8"))
    payload = verified_bytes(folder / "escenarios_metadatos.csv",
                             manifest["hashes"]["escenarios_metadatos.csv"], "escenarios_metadatos.csv")
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
    if value is None:
        return
    # El motor valida primero (p. ej. disponibilidad en STOCKOUT) para no
    # dejar una emisión revelada sin observado registrado en el reloj.
    eng = engine()
    state = eng.status()
    if key[2] == state["open_month"] and not eng.is_closed(key[2]):
        try:
            eng.set_manual_observed(value)
        except InputError as exc:
            st.session_state["engine_error"] = str(exc)
            st.session_state[widget_key] = eng.pending_observed()
            return
    journal().reveal(key, value)


def close_current_month(eng, store, key, *, complete):
    """Valida ambas autoridades y la referencia antes de escribir un cierre."""
    eng.validate_close_month(complete=complete)
    state = eng.status()
    if key != (state["product_id"], state["location_id"], state["open_month"]):
        raise InputError("El cierre no corresponde al par y mes abierto.")
    observed = eng.pending_observed()
    if key not in store.pending or key in store.closed:
        raise InputError("Primero emite una predicción o registra una abstención para este mes.")
    if key in store.revealed and store.revealed[key] != observed:
        raise InputError("El observado del diario no coincide con el motor. No se cierra el mes.")
    rotation = rotation_for(key[0], key[1], key[2])
    eng.close_month(complete=complete)
    store.close(key, observed, rotation)


def render_prediction(reference, product_id, location_id, month, features, input_error, scenario="NORMAL"):
    st.subheader("Predicción interactiva")
    st.button("RECONECTAR RUNTIME", on_click=reconnect_runtime,
              help="Crea una instancia local al incorporar el proveedor de Erika. No entrena.")
    store, provider = journal(), runtime()
    eng = engine()
    key = product_id, location_id, month
    info = None
    try:
        info = active_info(provider)
    except Exception:
        st.error("El modelo ACTIVE no cumple el contrato. La inferencia permanece bloqueada.")
    reason = st.text_input("Motivo de activación de V1", key="v1_activation_reason",
                           help="Activa únicamente la V1 seleccionada en esta sesión. No entrena ni promueve candidatos nuevos.")
    supports_v1 = callable(getattr(provider, "activate_v1", None))
    v1_active = info is not None and info.version == "V1"
    if st.button("ACTIVAR V1 CONGELADA", disabled=not supports_v1 or v1_active or not reason.strip()):
        try:
            provider.activate_v1(reason)
            st.session_state.pop("v1_activation_error", None)
            st.rerun()
        except Exception:
            st.session_state.v1_activation_error = "No se pudo verificar y activar V1. La referencia anterior se conserva."
    if st.session_state.get("v1_activation_error"):
        st.error(st.session_state.v1_activation_error)
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
    complete = False
    forecast = store.pending.get(key)
    if closed:
        st.success("Mes cerrado. La emisión y su observado no se sobrescriben.")
        st.dataframe(pd.DataFrame(record_table([store.closed[key]])), hide_index=True, width="stretch")
        st.number_input("Venta observada del mes cerrado", value=store.closed[key].observed,
                        min_value=0, max_value=2**53-1, step=1,
                        key=f"closed_observed_{product_id}_{location_id}_{month}", disabled=True)
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
                live = eng.status()
                if month == live["open_month"] and not eng.is_closed(month):
                    if eng.pending_observed() != observed:
                        eng.set_manual_observed(observed)
                    close_current_month(eng, store, key, complete=complete)
                else:
                    store.close(key, observed, rotation_for(product_id, location_id, month))
                st.rerun()
            except InputError as exc:
                st.error(str(exc))
    st.caption("Editar o predecir no entrena. El observado nunca se envía a predict(features).")
    detail = eng.generation_detail()
    if detail is not None and month == eng.status()["open_month"]:
        st.caption(
            f"STOCKOUT · demanda latente {detail['latent']} · disponibilidad {detail['availability']} · "
            f"venta observada {detail['observed']}. La latente no es una feature ni una venta conocida."
        )
    live = eng.status()
    can_generate = (
        month == live["open_month"] and not eng.is_closed(month)
        and live["pending_observed"] is None and key in store.pending
    )
    can_advance = (
        month == live["open_month"]
        and (eng.is_closed(month) or (live["pending_observed"] is not None
             and (eng.observation_source() == "GENERATED" or complete)))
    )
    if (live["pending_observed"] is not None and eng.observation_source() == "MANUAL"
            and not complete and not eng.is_closed(month)):
        st.info("MES INCOMPLETO: confirma que el mes objetivo está cerrado y completo para registrar el observado o avanzar. El reloj y el historial se conservan.")
    a, b = st.columns(2)
    with a:
        if st.button("GENERAR SIGUIENTE MES", disabled=not can_generate, width="stretch"):
            try:
                # Idempotente en el motor: un rerun no consume azar ni cambia el valor.
                observed = eng.generate_observed()
                store.reveal(key, observed)
                st.rerun()
            except InputError as exc:
                st.session_state["engine_error"] = str(exc)
    with b:
        if st.button("AVANZAR MES", disabled=not can_advance, width="stretch"):
            try:
                if not eng.is_closed(month):
                    close_current_month(eng, store, key,
                                        complete=eng.observation_source() == "GENERATED" or complete)
                eng.advance_month()
                st.session_state["month_sync"] = eng.status()["open_month"]
                st.rerun()
            except InputError as exc:
                st.session_state["engine_error"] = str(exc)
    engine_error = st.session_state.pop("engine_error", None)
    if engine_error:
        st.error(engine_error)
    st.caption(
        "Generación y reloj operan sobre el motor de la sesión (seed 42). "
        "Registrar observado cierra la evidencia de esta vista y sincroniza el cierre del mes abierto."
    )


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


def render_comparison(reference):
    st.subheader("Comparación visual de modelos y candidato")
    st.caption("Solo lectura. Esta vista no entrena, selecciona, promueve o revierte modelos. "
               "Una menor media no prueba por sí sola que deba activarse un candidato.")
    bind_selected_pair()
    pair = engine().status()
    uploaded = st.file_uploader("Reporte de Erika · JSON h4-comparison-1", type=["json"], max_upload_size=2,
                               key=f"comparison_upload_{pair['product_id']}_{pair['location_id']}")
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
