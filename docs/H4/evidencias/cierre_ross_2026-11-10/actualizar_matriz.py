"""Actualiza la matriz vigente con evidencia técnica, sin firmar aceptación humana."""
import csv
import json
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent
DOCS = OUT.parents[1]
source = DOCS / "H4_MATRIZ_CUMPLIMIENTO_FINAL.csv"
raw = source.read_bytes()
with source.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    columns = reader.fieldnames
    rows = list(reader)
evidence = "docs/H4/evidencias/cierre_ross_2026-11-10/"
changes = {
    "R11": ("CUMPLIDO", "CUMPLIDO", "CUMPLIDO",
            "Controles reales revisados en 1366x900 y 390x844. Revisión automatizada con navegador, no firma de estudiantes.",
            "Ninguna de código. Aceptación del equipo se controla en R61."),
    "R23": ("CUMPLIDO", "CUMPLIDO", "CUMPLIDO",
            "Baseline y LR reales visibles sin ACTIVE mediante COMPARAR TRES REFERENCIAS. RF exige V1 activa.",
            "Ninguna para la integración técnica verificada."),
    "R30": ("CUMPLIDO", "CUMPLIDO", "CUMPLIDO",
            "Aplicación normal conectada a las tres referencias. Artefactos reales, sin fit o TEST oficial nuevo. Captura de sus tres salidas.",
            "Ninguna de conexión. Aceptación académica conjunta pendiente en R61/R62."),
    "R34": ("CUMPLIDO", "CUMPLIDO", "CUMPLIDO",
            "Tablas, barras, historia y métricas revisadas con seis cierres reales de simulación. Pantalla estrecha con tablas desplazables.",
            "Repetición por el equipo dentro de su aceptación manual."),
    "R56": ("CUMPLIDO", "CUMPLIDO", "CUMPLIDO",
            "Navegador real 1366x900. Activación, referencias, seis cierres, monitoreo, comparación, rechazo, descarga y rollback. No acredita participación en defensa.",
            "Participación humana se controla en R61/R62/R63."),
    "R57": ("CUMPLIDO", "CUMPLIDO", "CUMPLIDO",
            "Navegador real 390x844. Controles y métricas apilados, textos legibles y tablas con desplazamiento horizontal. Viewport restaurado.",
            "Aceptación del equipo separada de esta revisión automatizada."),
    "R73": ("CUMPLIDO", "CUMPLIDO", "NO APLICA",
            "Desglose Escenario en sesiones y reportes con casos, predicciones, cobertura, MAE y RMSE. Ausencia de metadato conserva NO REGISTRADO.",
            "Ninguna para la función verificada por regresiones."),
    "R52": ("PARCIAL", "CUMPLIDO", "CUMPLIDO",
            "Descarga real conservada en sesion_visual.json. Seis cierres y verify_session_export=True. Falta aceptación personal del consumo por Ross.",
            "Ross y Erika deben confirmar aceptación del consumo y presentación, sin atribuirla a la revisión automatizada."),
}
for row in rows:
    if row["id"] in changes:
        status, technical, visual, observation, pending = changes[row["id"]]
        row.update(estado=status, cumplimiento_tecnico=technical, demostracion_visual=visual,
                   observaciones=observation, accion_pendiente=pending)
        row["evidencia"] += "; ml/demand/tests/test_ross_closure.py; " + evidence + "revision_visual.json; " + evidence + "pruebas_finales.txt"
    if row["id"] == "R30":
        row["archivos"] += "; ml/demand/streamlit_app.py"
with source.open("w", encoding="utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, columns)
    writer.writeheader()
    writer.writerows(rows)
counts = Counter(r["estado"] for r in rows)
applicable = len(rows) - counts["NO APLICA"]
percent = f"{100*counts['CUMPLIDO']/applicable:.2f}".replace(".", ",")
summary = dict(total=len(rows), statuses=dict(counts), applicable=applicable,
               strict_percent=100*counts["CUMPLIDO"]/applicable,
               note="Cumplimiento técnico y documental. No equivale a nota, precisión o aceptación humana.")
(OUT / "resumen_matriz.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
text = f"""# H4 — Matriz vigente tras integración de Ross

Fecha: 2026-11-10, America/La_Paz. Conserva los 73 identificadores y cláusulas de T14/T21. La revisión actual está en la sección 20 de H4_IMPLEMENTACION_MODELO_PREDICTIVO.md. Las matrices históricas no se modifican.

73 requisitos: **{counts['CUMPLIDO']} CUMPLIDOS, {counts['PARCIAL']} PARCIALES, {counts['NO VERIFICADO']} NO VERIFICADOS, {counts['NO CUMPLIDO']} NO CUMPLIDOS, {counts['NO APLICA']} NO APLICA**. Aplicables: {applicable}. Cumplimiento estricto: **{counts['CUMPLIDO']}/{applicable} = {percent} %**. No mide precisión predictiva, porcentaje exacto del H4 ni nota académica.

R11/R23/R30/R34/R56/R57/R73 incorporan evidencia nueva. La revisión visual usa navegador real automatizado en escritorio y pantalla estrecha. R52 ya tiene descarga y verificación real, pero continúa PARCIAL por aceptación humana pendiente. R12 conserva su aceptación manual pendiente. No se inventan participación, firmas o prompts originales. Promoción real de candidatos permanece bloqueada.

Fuentes: evidencias/cierre_ross_2026-11-10/pruebas_finales.txt, revision_visual.json, sesion_visual.json y test_ross_closure.py. La suite final aprobó 473 casos. Los 29 archivos protegidos conservan sus bytes. El CSV compañero conserva todos los campos originales, fuentes y responsables.

| ID | Semana / responsable | Requisito | Estado | Técnico / visual | Implementación | Prueba o evidencia | Observación | Acción pendiente |
|---|---|---|---|---|---|---|---|---|
"""
def escape(value):
    return value.replace("|", "\\|").replace("\n", " ")
for row in rows:
    fields = [row["id"], row["semana"]+" / "+row["responsable"], row["requisito_original"], row["estado"],
              row["cumplimiento_tecnico"]+" / "+row["demostracion_visual"], row["archivos"], row["evidencia"],
              row["observaciones"], row["accion_pendiente"]]
    text += "| " + " | ".join(escape(v) for v in fields) + " |\n"
(DOCS / "H4_MATRIZ_CUMPLIMIENTO_FINAL.md").write_text(text, encoding="utf-8")
print(json.dumps(summary, ensure_ascii=True))
