"""Interfaz de Ross: edición, integración, métricas y monitoreo local H4."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Compatible con ejecución desde la raíz y con AppTest, sin instalar un paquete.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from demand_engine import SCENARIO_PRELOADS  # noqa: E402
from pair_contexts import bind_pair_context, clear_pair_contexts  # noqa: E402
from simulator_inputs import (  # noqa: E402
    InputError, MAX_UI_QUANTITY, SCENARIOS, build_inputs, load_reference,
    month_label, offset_month,
)
from ui_panels import (  # noqa: E402
    engine, journal, render_comparison, render_monitoring, render_prediction,
    render_retraining,
    render_candidate_decision,
    record_reset, render_lifecycle, render_session_export,
)


def save_draft(context, suffix):
    product_id, location_id, month = context.split("_")
    key = (int(product_id), int(location_id), month)
    journal().discard_pending(key)
    before = st.session_state.drafts[context].get(suffix)
    requested = st.session_state[f"editor_{context}_{suffix}"]
    st.session_state.drafts[context][suffix] = st.session_state[f"editor_{context}_{suffix}"]
    st.session_state.validated.pop(context, None)
    sync_engine(context, suffix, key)
    after = st.session_state.drafts[context].get(suffix)
    journal().record_edit(key, suffix, before, after, accepted=after == requested)


def sync_engine(context, suffix, key):
    """Lleva escenario y lags del editor al motor (autoridad del reloj)."""
    eng = engine()
    state = eng.status()
    month = key[2]
    if suffix == "scenario":
        chosen = st.session_state[f"editor_{context}_scenario"]
        try:
            eng.apply_scenario(chosen)
        except InputError as exc:
            # Rechaza el cambio sin consumir azar y conserva el motor como fuente.
            st.session_state["scenario_error"] = str(exc)
            st.session_state[f"editor_{context}_scenario"] = state["scenario"]
            st.session_state.drafts[context]["scenario"] = state["scenario"]
            return
        # El motor aplica la hipótesis al mes abierto aunque se elija viendo otro mes.
        open_month = state["open_month"]
        open_context = f"{key[0]}_{key[1]}_{open_month}"
        draft = st.session_state.drafts.get(open_context)
        if draft is None:
            # El mes abierto todavía no se abrió en el editor: se crea con su historia.
            series = dict(eng.history_series())
            draft = {
                "lag3": series.get(offset_month(open_month, -3)),
                "lag2": series.get(offset_month(open_month, -2)),
                "lag1": series.get(offset_month(open_month, -1)),
                "scenario": chosen, "complete": True,
            }
            st.session_state.drafts[open_context] = draft
        draft["scenario"] = chosen
        st.session_state[f"editor_{open_context}_scenario"] = chosen
        # La validación previa del mes abierto queda obsoleta con la nueva hipótesis.
        st.session_state.validated.pop(open_context, None)
        for lag_suffix, value in zip(("lag3", "lag2", "lag1"), SCENARIO_PRELOADS[chosen]):
            if value is None:
                # PRODUCTO NUEVO no inventa historia: los widgets conservan su valor.
                continue
            draft[lag_suffix] = value
            st.session_state[f"editor_{open_context}_{lag_suffix}"] = value
    elif suffix in ("lag3", "lag2", "lag1"):
        if month == state["open_month"] == state["viewing_month"] and not eng.is_closed(month):
            draft = st.session_state.drafts[context]
            try:
                eng.edit_lags(draft["lag3"], draft["lag2"], draft["lag1"])
            except InputError as exc:
                st.session_state["engine_error"] = str(exc)


def reset_editor():
    record_reset()
    st.session_state.pop("last_session_export", None)
    clear_pair_contexts(st.session_state)
    for key in list(st.session_state):
        if key.startswith(("editor_", "observed_", "closed_", "comparison_upload_")):
            del st.session_state[key]
    st.session_state.drafts = {}
    st.session_state.validated = {}
    st.session_state.pop("observation_journal", None)
    st.session_state.pop("demand_session", None)
    st.session_state.pop("h4_runtime", None)
    st.session_state.pop("runtime_error", None)
    st.session_state.pop("v1_activation_reason", None)
    st.session_state.pop("v1_activation_error", None)
    st.session_state.pop("retraining_session", None)
    st.session_state.pop("retraining_result", None)
    st.session_state.pop("retraining_error", None)
    for key in ("candidate_comparison_session", "candidate_comparison_result", "candidate_rejection",
                "candidate_decision_error", "candidate_decision_reason", "candidate_rollback_notice",
                "comparison_report", "comparison_source"):
        st.session_state.pop(key, None)
    st.session_state.pop("month_sync", None)
    st.session_state.pop("engine_error", None)
    st.session_state.pop("scenario_error", None)
    st.session_state.product = st.session_state.initial_product
    st.session_state.store = st.session_state.initial_store
    st.session_state.month = st.session_state.initial_month


def main():
    st.set_page_config(page_title="H4 · Simulador local", page_icon="📊", layout="wide")
    st.title("Simulador de ventas · H4")
    st.caption("SIMULACIÓN · Archivos locales · Sin conexión a ventas reales o Neon")
    st.info(
        "Área de Ross · Edición, integración de predicción, métricas y monitoreo local. "
        "El motor y los modelos de Erika se conectan mediante un contrato separado."
    )
    try:
        reference = load_reference()
    except (InputError, OSError, ValueError, KeyError):
        st.error("No se pudo verificar la referencia local. Revisa catálogo, panel 1.1 y manifiesto.")
        st.stop()

    months = tuple(offset_month(m, 1) for m in reference.months[2:])
    for key, value in {
        "drafts": {}, "validated": {},
        "initial_product": next(iter(reference.products)),
        "initial_store": next(iter(reference.stores)), "initial_month": months[-1],
        "product": next(iter(reference.products)), "store": next(iter(reference.stores)),
        "month": months[-1],
    }.items():
        if key not in st.session_state:
            st.session_state[key] = value
    # El avance del reloj actualiza el mes objetivo antes de crear el selectbox.
    if "month_sync" in st.session_state:
        st.session_state["month"] = st.session_state.pop("month_sync")

    st.button("RESTABLECER EDICIÓN", on_click=reset_editor, help="Restaura esta sesión a la referencia original.")
    left, middle, right = st.columns(3)
    with left:
        product_id = st.selectbox(
            "Producto", tuple(reference.products), key="product",
            format_func=lambda p: f"{reference.products[p]['itemCode']} · {reference.products[p]['name']}",
        )
    with middle:
        location_id = st.selectbox(
            "Tienda", tuple(reference.stores), key="store",
            format_func=lambda p: reference.stores[p]["name"],
        )
    eng = engine(reference)
    eng.select(product_id, location_id)
    bind_pair_context(st.session_state, eng.session_id, product_id, location_id)
    # Meses con al menos tres de historia en el panel; el motor los extiende al avanzar.
    first_full = offset_month(reference.months[0], 3)
    selectable = tuple(m for m in eng.selectable_months() if m >= first_full)
    if st.session_state["month"] not in selectable:
        st.session_state["month"] = selectable[-1]
    with right:
        month = st.selectbox("Mes objetivo", selectable, key="month", format_func=month_label)
    eng.select_month(month)
    session_status = eng.status()
    st.caption(
        f"productId: {product_id} · locationId: {location_id} · mes_objetivo: {month}. "
        "Los IDs identifican la serie, no son cantidades ni features del modelo."
    )
    st.caption(
        f"Reloj de simulación · abierto {session_status['open_month']} · escenario {session_status['scenario']} · "
        f"historia {session_status['history_status']} · cerrados "
        f"{', '.join(session_status['closed_months']) or 'ninguno'} · observado pendiente "
        f"{session_status['pending_observed'] if session_status['pending_observed'] is not None else 'no'}"
    )

    context = f"{product_id}_{location_id}_{month}"
    closed = journal().is_locked((product_id, location_id, month))
    recent = eng.recent_history()
    if context not in st.session_state.drafts:
        st.session_state.drafts[context] = {
            "lag3": recent[0][1], "lag2": recent[1][1], "lag1": recent[2][1],
            "scenario": session_status["scenario"], "complete": True,
        }
    draft = st.session_state.drafts[context]

    st.subheader("Editar entradas simuladas")
    scenario = st.selectbox(
        "Escenario para revisión", SCENARIOS,
        index=SCENARIOS.index(draft["scenario"]), key=f"editor_{context}_scenario",
        on_change=save_draft, args=(context, "scenario"), disabled=closed,
    )
    st.caption(
        "El escenario precarga supuestos en el motor de la sesión y queda bloqueado tras "
        "cerrar o generar. No es una feature del modelo ni restablece ediciones en un rerun."
    )
    scenario_error = st.session_state.pop("scenario_error", None)
    if scenario_error:
        st.error(scenario_error)
    values = []
    for column, suffix, (history_month, original), label in zip(
        st.columns(3), ("lag3", "lag2", "lag1"), recent,
        ("Ventas hace 3 meses", "Ventas hace 2 meses", "Ventas mes anterior"),
    ):
        with column:
            values.append(st.number_input(
                f"{label} · {month_label(history_month)}", min_value=0,
                max_value=MAX_UI_QUANTITY, value=draft[suffix], step=1,
                key=f"editor_{context}_{suffix}", on_change=save_draft, args=(context, suffix),
                disabled=closed,
                help="Unidades enteras. El máximo es técnico: enteros exactos en JavaScript.",
            ))
            st.caption(f"Historia de sesión: {original if original is not None else 'sin dato'} unidades")
    complete = st.checkbox(
        "Los tres meses anteriores están completos", value=draft["complete"],
        key=f"editor_{context}_complete", on_change=save_draft, args=(context, "complete"), disabled=closed,
    )
    error = None
    try:
        features = build_inputs(reference, product_id, location_id, month, values, complete,
                                scenario, history=recent)
    except InputError as exc:
        error, features = str(exc), None
        st.warning(f"PREDICCIÓN NO DISPONIBLE · {error}")

    if st.button("VALIDAR ENTRADAS", type="primary", disabled=closed):
        journal().record_confirmation((product_id, location_id, month), features, error)
        if error:
            st.session_state.validated.pop(context, None)
        else:
            st.session_state.validated[context] = features
    if context in st.session_state.validated:
        st.success("Entradas validadas. No se ejecutó predicción ni entrenamiento.")
    elif features:
        st.caption("Edición pendiente de confirmar con VALIDAR ENTRADAS.")

    st.subheader("Historia reciente y edición")
    chart = pd.DataFrame({
        "Mes": pd.to_datetime([m + "-01" for m, _ in recent]),
        "Historia de sesión": [v for _, v in recent],
        "Edición local": values,
    })
    st.line_chart(chart, x="Mes", y=["Historia de sesión", "Edición local"],
                  x_label="Mes", y_label="Unidades")
    st.dataframe(chart.assign(Mes=[m for m, _ in recent]), hide_index=True, width="stretch")
    st.caption("La edición cambia solo esta sesión. No modifica el CSV ni representa ventas reales.")
    if features:
        st.subheader("Contrato de entrada · cinco features")
        st.dataframe(pd.DataFrame([features]), hide_index=True, width="stretch")
        st.caption("mes_sin y mes_cos se derivan del mes objetivo. No se editan manualmente.")

    prediction, monitoring, comparison = st.tabs(["Predicción y observado", "Errores y monitoreo", "Comparación de modelos"])
    with prediction:
        render_prediction(reference, product_id, location_id, month, features, error, scenario)
    with monitoring:
        render_monitoring()
    with comparison:
        render_comparison(reference)
    render_retraining()
    render_candidate_decision()
    render_lifecycle()
    render_session_export()


if __name__ == "__main__":
    main()
