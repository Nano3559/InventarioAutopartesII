"""Interfaz de Ross: edición, integración, métricas y monitoreo local H4."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Compatible con ejecución desde la raíz y con AppTest, sin instalar un paquete.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from simulator_inputs import (  # noqa: E402
    InputError, MAX_UI_QUANTITY, SCENARIOS, build_inputs, load_reference,
    month_label, offset_month,
)
from ui_panels import journal, render_comparison, render_monitoring, render_prediction  # noqa: E402


def save_draft(context, suffix):
    product_id, location_id, month = context.split("_")
    journal().discard_pending((int(product_id), int(location_id), month))
    st.session_state.drafts[context][suffix] = st.session_state[f"editor_{context}_{suffix}"]
    st.session_state.validated.pop(context, None)


def reset_editor():
    for key in list(st.session_state):
        if key.startswith(("editor_", "observed_", "closed_")):
            del st.session_state[key]
    st.session_state.drafts = {}
    st.session_state.validated = {}
    st.session_state.pop("observation_journal", None)
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
    with right:
        month = st.selectbox("Mes objetivo", months, key="month", format_func=month_label)
    st.caption(
        f"productId: {product_id} · locationId: {location_id} · mes_objetivo: {month}. "
        "Los IDs identifican la serie, no son cantidades ni features del modelo."
    )

    context = f"{product_id}_{location_id}_{month}"
    closed = journal().is_locked((product_id, location_id, month))
    recent = reference.recent(product_id, location_id, month)
    if context not in st.session_state.drafts:
        st.session_state.drafts[context] = {
            "lag3": recent[0][1], "lag2": recent[1][1], "lag1": recent[2][1],
            "scenario": "NORMAL", "complete": True,
        }
    draft = st.session_state.drafts[context]

    st.subheader("Editar entradas simuladas")
    scenario = st.selectbox(
        "Escenario para revisión", SCENARIOS,
        index=SCENARIOS.index(draft["scenario"]), key=f"editor_{context}_scenario",
        on_change=save_draft, args=(context, "scenario"), disabled=closed,
    )
    st.caption(
        "En esta entrega el escenario es una etiqueta de revisión. "
        "Las precargas y resultados dinámicos se conectarán al motor de Erika. "
        "Elegirlo no cambia automáticamente tus cantidades ni se envía como feature."
    )
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
            st.caption(f"Referencia 1.1: {original if original is not None else 'sin dato'} unidades")
    complete = st.checkbox(
        "Los tres meses anteriores están completos", value=draft["complete"],
        key=f"editor_{context}_complete", on_change=save_draft, args=(context, "complete"), disabled=closed,
    )
    error = None
    try:
        features = build_inputs(reference, product_id, location_id, month, values, complete, scenario)
    except InputError as exc:
        error, features = str(exc), None
        st.warning(f"PREDICCIÓN NO DISPONIBLE · {error}")

    if st.button("VALIDAR ENTRADAS", type="primary", disabled=closed):
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
        "Referencia sintética 1.1": [v for _, v in recent],
        "Edición local": values,
    })
    st.line_chart(chart, x="Mes", y=["Referencia sintética 1.1", "Edición local"],
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


if __name__ == "__main__":
    main()
