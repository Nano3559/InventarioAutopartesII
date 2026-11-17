"""Local Streamlit UI for the frozen DEMO comparator."""

import streamlit as st

from compare_models import comparison
from model_loader import load_models

st.set_page_config(page_title="Comparador experimental | RepuestoPro", layout="wide")
st.title("Comparador experimental de modelos predictivos")
st.caption("RepuestoPro · Horizonte mensual · Snapshots DEMO sintéticos")
st.warning("Una diferencia entre pronósticos no demuestra mayor precisión")

roles = {"4.0.0": "Modelo oficial", "4.1.1 C": "Variante experimental", "4.1.1 D": "Candidato experimental"}
states = {"OK": "Elegible", "ABSTAINED": "Abstención", "UNAVAILABLE": "Indisponible"}
reasons = {
    "ARTIFACT_NOT_PERSISTED": "Artefacto entrenado sin guardar",
    "OUTSIDE_TRAINING_RANGE": "Entrada fuera del rango de referencia",
    "UNAVAILABLE_REQUIRED_FEATURE": "Historial insuficiente",
    "NONFINITE_PREDICTION": "Estimación no finita",
}

try:
    release, snapshots, models, versions = st.cache_resource(load_models)()
except (OSError, ValueError) as error:
    st.error(f"No se pudo verificar la carga: {error}")
    st.stop()

entries = list(snapshots.values())
products = {s["productId"]: s["productName"] for s in entries}
with st.container(border=True):
    a, b, c = st.columns([2, 1, 1])
    product_ids = sorted(products)
    product = a.selectbox("Producto", product_ids, index=product_ids.index(53) if 53 in products else 0,
                          format_func=products.get)
    entries = [s for s in entries if s["productId"] == product]
    stores = {s["locationId"]: s["locationName"] for s in entries}
    store_ids = sorted(stores)
    store = b.selectbox("Tienda", store_ids, index=store_ids.index(6) if 6 in stores else 0,
                        format_func=stores.get)
    entries = [s for s in entries if s["locationId"] == store]
    month = c.selectbox("Mes", sorted({s["targetMonth"] for s in entries}))
    entries = {s["baseSnapshotId"]: s for s in entries if s["targetMonth"] == month}
    snapshot = st.selectbox("Snapshot", sorted(entries), disabled=len(entries) == 1)

try:
    result = comparison(entries[snapshot], release, models)
except (ValueError, TypeError, KeyError) as error:
    st.error(f"Entrada incompatible: {error}")
    st.stop()

st.caption(f"{products[product]} · {stores[store]} · Corte {result['cutoffAt']}")
numeric = []
for card, row in zip(st.columns(3), result["models"]):
    forecast = row["forecastUnits"]
    with card.container(border=True):
        st.caption(roles[row["model"]])
        st.metric(row["model"], "Sin pronóstico" if forecast is None else f"{forecast:.2f} u.")
        st.write(states[row["status"]])
        if forecast is not None:
            numeric.append({"Modelo": row["model"], "Unidades": forecast,
                            "Color": "#2563EB" if row["model"] == "4.0.0" else "#0F766E"})
        elif row["reason"] == "ARTIFACT_NOT_PERSISTED":
            st.caption("C tiene métricas por fold. Su artefacto entrenado no se guardó.")
        else:
            st.caption(reasons[row["reason"]])
if result["outsideFeatures"]:
    st.warning("Fuera del rango de referencia · " + ", ".join(result["outsideFeatures"]))
if numeric:
    st.bar_chart(numeric, x="Modelo", y="Unidades", color="Color", height=240)

st.subheader("Diferencias respecto a 4.0.0")
st.dataframe([{
    "Modelo": row["model"], "Estado": states[row["status"]], "Motivo": reasons.get(row["reason"]),
    "Pronóstico": row["forecastUnits"], "Diferencia absoluta": row["absoluteDifferenceUnits"],
    "Diferencia % con signo": row["differencePercent"],
} for row in result["models"]], hide_index=True, column_config={
    "Pronóstico": st.column_config.NumberColumn(format="%.2f"),
    "Diferencia absoluta": st.column_config.NumberColumn(format="%.2f"),
    "Diferencia % con signo": st.column_config.NumberColumn(format="%.2f"),
})
st.caption("La diferencia porcentual usa 4.0.0 como denominador. Noviembre DEMO carece de ventas observadas autorizadas.")
with st.expander("Snapshot, procedencia y versiones"):
    st.write(f"Snapshot: {snapshot} · Origen: DEMO sintético · Producto {product} · Tienda {store}")
    st.dataframe([{"Modelo": row["model"], "ID": row["modelId"], "SHA256": row["sha256"]}
                  for row in result["models"]], hide_index=True)
    st.json(versions)
