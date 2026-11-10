"""Deriva la revisión T15 sin alterar la fotografía y evidencia T14."""
from collections import Counter
from copy import deepcopy
import csv
import json
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "ml/demand/run_tests.py").is_file())
OUT = Path(__file__).resolve().parent
baseline = json.loads((ROOT/"docs/H4/tareas_erika/tarea_14/evidence/matrix.json").read_text(encoding="utf-8"))
rows = deepcopy(baseline["requirements"])
changes = {
    "R17": "D02 corregido: motor preflight complete=False rechaza sin mutar; UI exige confirmación para manual, generado mensual completo permite cierre. Pruebas MonthClosureTests y NormalStreamlitFixTests.",
    "R20": "D01 corregido: un Random por PairState, derivado de seed de sesión + IDs con SHA256 estable. Intercalado, reset, seeds y ocho escenarios verificados.",
    "R69": "D03 corregido: motivo obligatorio y ACTIVAR V1 CONGELADA en la sesión normal. AppTest sin runtime inyectado activa V1 real, predice sin fit y revierte. La revisión visual sigue pendiente en R56/R57.",
}
for row in rows:
    if row["id"] in changes:
        assert row["estado"] == "PARCIAL"
        row["estado"] = row["cumplimiento_tecnico"] = "CUMPLIDO"
        row["observaciones"] = changes[row["id"]]
        row["evidencia"] = "ml/demand/test_h4_functional_fixes.py; docs/H4/tareas_erika/tarea_15/evidence/functional_validation.json; docs/H4/tareas_erika/tarea_15/evidence/full_tests.txt"
    elif row["id"] == "R53":
        row["observaciones"] += " Actualización T15: D02 subsanado; se conserva PARCIAL hasta repetir la revisión integral de este requisito, fuera de esta etapa."
    elif row["id"] == "R33":
        row["observaciones"] += " Actualización T15: R69 ya tiene acción normal explícita; ver matriz T15."
counts = Counter(r["estado"] for r in rows)
denominator = len(rows)-counts["NO APLICA"]
summary = dict(total=len(rows),estados=dict(counts),aplicables=denominator,
               porcentaje_estricto=round(100*counts["CUMPLIDO"]/denominator,2),
               porcentaje_con_medios_parciales=round(100*(counts["CUMPLIDO"]+0.5*counts["PARCIAL"])/denominator,2),
               changed_ids=list(changes),baseline_porcentaje=baseline["summary"]["porcentaje_estricto"],
               criterio="Mismos 73 IDs y 68 aplicables de T14. Solo R17/R20/R69 pasan PARCIAL→CUMPLIDO; sin modificar pesos.")
assert len(rows)==73 and denominator==68
assert [r["id"] for old,r in zip(baseline["requirements"],rows) if old["estado"] != r["estado"]] == list(changes)
(OUT/"matrix.json").write_text(json.dumps(dict(summary=summary,requirements=rows,crosswalk=baseline["crosswalk"]),indent=2,ensure_ascii=False),encoding="utf-8")
with (ROOT/"docs/H4/tareas_erika/tarea_15/H4_MATRIZ_CUMPLIMIENTO_T15.csv").open("w",newline="",encoding="utf-8-sig") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader();writer.writerows(rows)
text = ["# H4 — Matriz de cumplimiento tras Tarea 15", "", "Revisión acotada de D01, D02 y D03. La fotografía T14 se conserva en ../tarea_14/H4_MATRIZ_CUMPLIMIENTO.md y ../tarea_14/evidence/matrix.json.", "", "## Criterio y cambios", "", "Mismos requisitos, denominador y pesos. No se acredita revisión visual ni se corrigen otros pendientes. El cambio de porcentaje procede exclusivamente de tres requisitos con nueva evidencia funcional.", "", "```json", json.dumps(summary,indent=2,ensure_ascii=False), "```", "", "| ID | Antes | Después | Evidencia y alcance |", "|---|---|---|---|"]
text += [f"| {rid} | PARCIAL | CUMPLIDO | {note} |" for rid,note in changes.items()]
text += ["", "## Matriz completa con estados conservados", "", "| ID | Semana | Requisito | Responsable | Estado | Técnico | Visual | Archivo | Prueba/evidencia | Observación |", "|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    text.append("| "+" | ".join(str(r[k]).replace("|","/") for k in ("id","semana","requisito_original","responsable","estado","cumplimiento_tecnico","demostracion_visual","archivos","evidencia","observaciones"))+" |")
text += ["", "La relación literal de los 125 ítems originales no cambia: consultar el anexo de la matriz T14. R53 se mantiene parcial; R21/R49/R50/R52 y revisión visual/documental continúan abiertos. Este cálculo no certifica H4 al 100 % ni equivale a una nota académica.", ""]
(ROOT/"docs/H4/tareas_erika/tarea_15/H4_MATRIZ_CUMPLIMIENTO_T15.md").write_text("\n".join(text),encoding="utf-8")
print(json.dumps(summary))
