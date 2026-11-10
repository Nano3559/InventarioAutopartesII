"""Genera matriz normalizada y trazabilidad a listas originales sin contarlas dos veces."""
from collections import Counter
import csv
import json
from pathlib import Path
import re

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "ml/demand/run_tests.py").is_file())
OUT = Path(__file__).resolve().parent
rows = []
ML = "ml/demand/"
DOC = "docs/H4/"
SUITE = DOC+"tareas_erika/tarea_14/evidence/full_tests.txt"
FLOW = DOC+"tareas_erika/tarea_14/evidence/integral.json"


def add(week, requirement, owner, status, files, evidence, notes="", technical=None, visual="NO APLICA"):
    rows.append(dict(id=f"R{len(rows)+1:02}", semana=week, requisito_original=requirement,
                     responsable=owner, estado=status, cumplimiento_tecnico=technical or status,
                     demostracion_visual=visual, archivos="; ".join(ML+f for f in files.split("; ")) if files and files != "—" else "—",
                     evidencia=evidence, observaciones=notes))


add("1", "Problema, unidad producto + tienda + mes, origen sintético y horizonte mensual (§1–4)", "Compartido", "CUMPLIDO", "simulator_inputs.py", DOC+"H4_IMPLEMENTACION_MODELO_PREDICTIVO.md", "Definición técnica; no certifica demanda comercial.")
add("1", "Dataset validado con estadísticas, distribución y ejemplos sintéticos (§14)", "Erika", "CUMPLIDO", "data/escenarios_v1_1/validacion.json; data/escenarios_v1_1/manifest.json", "ml/demand/test_generate_synthetic.py; "+SUITE)
add("1", "Verificar dataset y hashes, conservar 1.1 inmutable (§14 d1–2)", "Erika", "CUMPLIDO", "simulator_inputs.py", DOC+"tareas_erika/tarea_14/evidence/integrity_after.json")
add("1", "Catálogo de referencia, IDs válidos, tiendas y reservados (§3–4)", "Compartido", "CUMPLIDO", "catalog_reference.json; simulator_inputs.py", "ml/demand/test_simulator_ui.py; "+SUITE)
add("1", "Motor separado del generador histórico y conservación de versiones (§13–14)", "Erika", "CUMPLIDO", "demand_engine.py; generate_synthetic.py; versions/generate_v1_0_0.py", DOC+"tareas_erika/tarea_14/evidence/integrity_after.json")
add("1", "Contrato de nueve columnas y cinco features; excluir IDs y target de X (§4)", "Erika", "CUMPLIDO", "ml_pipeline.py; simulator_inputs.py", "ml/demand/test_ml_pipeline.py; "+SUITE)
add("1", "Lags del mismo par, meses exactos y calendario seno/coseno (§4, §13)", "Erika", "CUMPLIDO", "demand_engine.py; simulator_inputs.py", FLOW, "En ajuste incremental los lags se reconstruyen desde cierres.")
add("1", "Validaciones numéricas, tipos, faltantes, IDs y casos ambiguos (§10, §13)", "Compartido", "CUMPLIDO", "simulator_inputs.py; ml_pipeline.py", "ml/demand/test_simulator_validation.py; "+SUITE)
add("1–2", "TRAIN/VALIDATION/TEST por meses completos sin solapamiento (§6)", "Erika", "CUMPLIDO", "ml_pipeline.py", "ml/demand/test_ml_pipeline.py; ml/demand/reports/v1_selection_manifest.json; "+SUITE)
add("2", "Preprocesamiento ajustado solo con TRAIN, conjunto modelo/scaler reproducible (§7)", "Erika", "CUMPLIDO", "train_linear_regression.py; train_random_forest.py", "ml/demand/test_linear_regression.py; "+SUITE, "RF sin scaler; LR conserva su transformación.")
add("1", "Interfaz Streamlit con selectores de producto, tienda y mes (§13, §14 d1–4)", "Ross", "PARCIAL", "streamlit_app.py", FLOW, "AppTest verifica controles; revisión visual no realizada.", "CUMPLIDO", "PENDIENTE")
add("1", "Edición manual y confirmación de entradas; invalidación de emisión pendiente (§13)", "Ross", "PARCIAL", "streamlit_app.py; ui_runtime.py", "ml/demand/test_ross_ui.py; "+FLOW, "Técnicamente verificado; presentación visual pendiente.", "CUMPLIDO", "PENDIENTE")
add("1", "Ocho escenarios, precargas y escenario como metadato, no feature (§13)", "Compartido", "CUMPLIDO", "demand_engine.py; streamlit_app.py", FLOW, "Seis meses por cada escenario con V1 real o abstención.")
add("1", "Resultado mensual manual/automático reproducible e idempotente (§13)", "Erika", "CUMPLIDO", "demand_engine.py; ui_panels.py", "ml/demand/test_demand_engine.py; "+FLOW, "Reproducibilidad de la misma secuencia de acciones por sesión; ver R20 para intercalado de pares.")
add("1", "STOCKOUT: separar latente, disponibilidad y observado; no recortar manual inválido (§13)", "Compartido", "CUMPLIDO", "demand_engine.py; ui_panels.py", "ml/demand/test_engine_integration.py; "+FLOW)
add("1", "Cierre único, avance calendario y actualización de lags (§13)", "Erika", "CUMPLIDO", "demand_engine.py; ui_runtime.py; ui_panels.py", FLOW, "Cierre explícito alternado con cierre al avanzar; no duplica meses.")
add("1", "Sin resultado o con mes incompleto no se cierra (§13)", "Compartido", "PARCIAL", "ui_panels.py; demand_engine.py", FLOW, "D02: avance cierra observado manual con casilla de mes completo false. Sin resultado sí bloquea.")
add("1", "Observado revelado bloquea edición y segunda predicción del mismo mes (§13)", "Ross", "CUMPLIDO", "ui_runtime.py; streamlit_app.py", "ml/demand/test_ross_ui.py; "+SUITE)
add("1", "Sesiones y datos por producto/tienda aislados; no trasladar ventas (§13)", "Compartido", "CUMPLIDO", "demand_engine.py; ui_runtime.py", FLOW, "Diccionarios de cierres por par y sesiones separados; no equivale a aislamiento del azar de R20.")
add("1", "Azar independiente por sesión y por par producto–tienda (§13)", "Erika", "PARCIAL", "demand_engine.py", FLOW, "D01: hay un único Random por sesión; otro par consume la secuencia del primero.")
add("1–3", "Candidato y referencia ACTIVE independientes por sesión y por par (§13)", "Compartido", "PARCIAL", "ui_panels.py; demand_runtime.py; retraining.py", FLOW, "ACTIVE y último resultado son de sesión, no referencias distintas por par; decisiones identifican correctamente el par.")
add("2", "Baseline último mes evaluado en VALIDATION (§8, §14 d6)", "Erika", "CUMPLIDO", "ml_pipeline.py; reports/experiments.csv", "ml/demand/test_ml_pipeline.py; ml/demand/reports/v1_selection_manifest.json")
add("2", "Baseline interactivo claramente etiquetado (§14 d6)", "Ross", "PARCIAL", "ui_runtime.py; ui_panels.py", "ml/demand/test_ross_ui.py; "+FLOW, "Referencia baseline registrada con inferencia; no hay ruta independiente de baseline sin ACTIVE.")
add("2", "LinearRegression entrenada, pipeline, registro y predicciones originales (§8, §14 d7–8)", "Erika", "CUMPLIDO", "train_linear_regression.py; models/linear_regression_candidate.joblib; reports/experiments.csv", "ml/demand/test_linear_regression.py; "+SUITE)
add("2", "RandomForest: búsqueda limitada, control temporal interno y reproducibilidad (§8, §14 d9–10)", "Erika", "CUMPLIDO", "train_random_forest.py; models/random_forest_candidate.joblib", "ml/demand/test_random_forest.py; ml/demand/reports/v1_selection_manifest.json; "+SUITE)
add("2", "Comparación VALIDATION, MAE/RMSE/R², cobertura, errores por grupos (§8–9)", "Compartido", "CUMPLIDO", "select_v1.py; reports/v1_selection_manifest.json", "ml/demand/test_select_v1.py; "+SUITE, "Métricas previas leídas, no recalculadas oficialmente.")
add("2–3", "Selección V1 justificada y congelada antes de TEST (§8, §14 d10–11)", "Compartido", "CUMPLIDO", "select_v1.py; reports/v1_selection_manifest.json", "ml/demand/test_select_v1.py; ml/demand/reports/v1_test_evaluation.json")
add("3", "Evaluación TEST final única con decisiones congeladas (§9, §14 d11)", "Compartido", "CUMPLIDO", "evaluate_v1.py; reports/v1_test_evaluation.json", DOC+"tareas_erika/tarea_14/evidence/integrity_after.json", "Se verifica reporte existente; no se ejecuta TEST oficial otra vez.")
add("2–3", "Registro de experimentos con parámetros, métricas, tiempos y versiones (§15)", "Erika", "CUMPLIDO", "reports/experiments.csv", DOC+"tareas_erika/tarea_14/evidence/integrity_after.json", "Registro oficial preservado; ensayos nuevos usan manifiestos separados.")
add("2", "Integración y revisión de baseline, LinearRegression y RandomForest reales en interfaz (§13 cierre Ross)", "Compartido", "PARCIAL", "ui_runtime.py; demand_runtime.py; train_linear_regression.py", "ml/demand/test_linear_regression.py; "+FLOW, "V1 RF sí en AppTest; no demostración equivalente de LR real dentro de Streamlit.", "PARCIAL", "PENDIENTE")
add("3", "Artefacto modelo/preprocesamiento, versiones, corte y huellas verificados (§15)", "Erika", "CUMPLIDO", "demand_runtime.py; reports/v1_selection_manifest.json", "ml/demand/test_demand_runtime.py; "+SUITE)
add("3", "Contrato Ross create_runtime/get_active_model/predict; sin Neon ni uploads ejecutables (§15)", "Erika", "CUMPLIDO", "demand_runtime.py; ui_runtime.py", "ml/demand/test_demand_runtime.py; "+SUITE)
add("2–3", "PREDECIR con ACTIVE real, features editadas y sin fit implícito (§13)", "Compartido", "CUMPLIDO", "demand_runtime.py; ui_panels.py", FLOW, "Activación explícita mediante arnés; falta vía interactiva normal, R69.")
add("2–3", "Gráficos/tablas de historia, predicción, comparación y errores (§13–14)", "Ross", "PARCIAL", "streamlit_app.py; ui_panels.py", FLOW, "Elementos renderizados en AppTest; aspecto visual no verificado.", "CUMPLIDO", "PENDIENTE")
add("2–3", "MAE/RMSE/R², cobertura, baseline y errores por tienda/producto/mes/rotación (§9, §13)", "Ross", "CUMPLIDO", "ui_analysis.py; ui_panels.py", "ml/demand/test_ross_ui.py; ml/demand/test_model_comparison.py; "+SUITE, "Sin métrica ficticia para abstenciones o target constante.")
add("3", "Monitoreo: dos ventanas de tres meses; revisión recomendada demostrativa (§13)", "Ross", "CUMPLIDO", "ui_analysis.py; ui_panels.py", "ml/demand/test_ross_ui.py; "+SUITE, "No prueba estadística de drift ni disparador automático de fit.")
add("3", "Priorizar PROBLEMA TÉCNICO/DATOS antes de recomendar reentrenamiento (§13)", "Ross", "CUMPLIDO", "ui_analysis.py", "ml/demand/test_ross_ui.py; "+SUITE)
add("3", "Nuevos observados cerrados verificados; no usar predicciones o latentes como target (§11)", "Erika", "CUMPLIDO", "retraining.py; demand_engine.py", "ml/demand/test_retraining.py; "+FLOW, "Observados concordantes motor/diario; las hipótesis quedan en trace.")
add("3", "Fijar corte antes del ajuste y reservar meses nuevos sin reutilizar TEST V1 (§11)", "Erika", "CUMPLIDO", "retraining.py; model_comparison.py", "ml/demand/test_retraining.py; "+FLOW, "Protocolo aprobado: 3 historia + 6 ajuste + 3 reserva; no se leen CSV históricos para ajustar.")
add("3", "ENSAYAR REENTRENAMIENTO explícito; progreso, exclusión concurrente, datos insuficientes (§11)", "Erika", "CUMPLIDO", "retraining.py; ui_panels.py", "ml/demand/test_retraining.py; "+FLOW)
add("3", "Crear CANDIDATE versionado independiente, sin sobrescribir ni activar (§11, §15)", "Erika", "CUMPLIDO", "retraining.py", FLOW+"; docs/H4/tareas_erika/tarea_12/evidence/example.json")
add("3", "Comparación justa en filas comunes, cinco features y ventanas posteriores a ambos ajustes (§11)", "Compartido", "CUMPLIDO", "model_comparison.py", "ml/demand/test_model_comparison.py; "+FLOW)
add("3", "Métricas de comparación, cobertura y evidencia insuficiente explícitas (§11)", "Compartido", "CUMPLIDO", "model_comparison.py", DOC+"tareas_erika/tarea_13/evidence/validation-60a54a1435134d62b247c71b8369d50c.json", "Tres observaciones: R² solo descriptivo; no declarar superioridad.")
add("3", "Rechazo con motivo, identidad y resultados originales conservados (§11, §15)", "Compartido", "CUMPLIDO", "model_comparison.py", FLOW)
add("3", "ACTIVAR CANDIDATO elegible desde simulador con comparación y criterios previos (§11)", "Compartido", "PARCIAL", "demand_runtime.py; ui_panels.py", DOC+"tareas_erika/tarea_13/evidence/fixture_validation.json", "Ruta positiva solo en fixtures por autorización expresa; promoción real bloqueada. No es una falla a eludir.")
add("3", "Impedir promoción automática y autorización desde JSON importados (§11)", "Erika", "CUMPLIDO", "demand_runtime.py; model_comparison.py", "ml/demand/test_model_comparison.py; "+SUITE)
add("3", "Demostrar promoción/rechazo y retorno con fixtures aislados (§14 d13–14)", "Compartido", "CUMPLIDO", "test_model_comparison.py", DOC+"tareas_erika/tarea_13/evidence/fixture_validation.json; "+SUITE, "Política de pruebas no importada por la app.")
add("3", "Rollback compatible con motivo, hashes y predicciones previas inmutables (§11)", "Erika", "CUMPLIDO", "demand_runtime.py", "ml/demand/test_model_comparison.py; "+FLOW)
add("3", "Registro local de versiones/estados y decisiones completo (§11, §15)", "Erika", "PARCIAL", "demand_runtime.py; retraining.py; model_comparison.py", DOC+"H4_TAREA_13_COMPARACION_DECISION.md", "Candidatos y decisiones persistidos; no registro unificado ARCHIVED/REJECTED/ACTIVE por par. ACTIVE solo en memoria.")
add("3", "Reset restaura escenario, seed, reloj y referencia V1 local (§13)", "Compartido", "PARCIAL", "streamlit_app.py; demand_runtime.py", FLOW, "Restaura datos/seed, pero deja SIN ACTIVE, según autorizaciones T10–13; difiere del texto original.")
add("3", "Carga incompatible/fallo de inferencia: abstención segura sin salida ficticia (§13)", "Erika", "CUMPLIDO", "demand_runtime.py; ui_panels.py", "ml/demand/test_demand_runtime.py; ml/demand/test_ross_ui.py; "+SUITE)
add("3", "Exportar sesión con seed/estado aleatorio, rama, procedencia y revisiones (§15)", "Compartido", "PARCIAL", "ui_panels.py; retraining.py; demand_engine.py", "ml/demand/test_ross_ui.py; "+FLOW, "DESCARGAR SESIÓN mantiene generator_seed=null; no serializa rama/estado RNG ni origen manual/generado por cierre. Incremental sí preserva parte.")
add("3", "Seis meses coherentes, stockout, nuevo, mes incompleto y cambio persistente (§13 cierre Ross)", "Compartido", "PARCIAL", "validate_h4_integral.py; ui_panels.py", FLOW, "60 meses validados; D02 sobre completitud impide declarar cumplimiento pleno.")
add("3", "Ciclo integrado edición→inferencia→observado→candidato→comparación→rechazo→retorno (§13)", "Compartido", "CUMPLIDO", "validate_h4_integral.py", FLOW, "12 meses + candidato temporal; alcance automatizado con activación V1 programática, no demo visual.")
add("1–3", "Pruebas del simulador, regresión y conservación de hashes (§17)", "Compartido", "CUMPLIDO", "test_engine_integration.py; test_retraining.py; test_model_comparison.py", SUITE, "375 anteriores siguen pasando; no implica ausencia de defectos nuevos en diagnósticos.")
add("3", "Revisión visual real en computadora y capturas (§13 cierre Ross)", "Ross", "PENDIENTE", "streamlit_app.py; ui_panels.py", DOC+"tareas_erika/tarea_14/evidence/visual_review.json", "Computer Use se detuvo por no poder verificar la URL; cero capturas.", "PARCIAL", "PENDIENTE")
add("3", "Revisión visual en pantalla estrecha (§13 cierre Ross)", "Ross", "PENDIENTE", "streamlit_app.py", DOC+"tareas_erika/tarea_14/evidence/visual_review.json", "No realizada; AppTest no comprueba el aspecto responsive.", "PARCIAL", "PENDIENTE")
add("1–3", "Prompts con procedencia, sin inventar texto o fechas (§15)", "Compartido", "PARCIAL", "—", DOC+"PROMPTS_MODELO_PREDICTIVO_H4.md", "Log existente llega al 4 de noviembre; este cierre aporta resumen separado de T10–14, no recupera prompts originales T1–9.")
add("3", "Documentación técnica y guía reproducible de ejecución/demostración (§14 d15)", "Erika", "CUMPLIDO", "validate_h4_integral.py", DOC+"H4_INFORME_FINAL.md; docs/H4/H4_GUIA_EJECUCION_WINDOWS.md")
add("1–3", "Riesgos, fallas, límites sintéticos/comerciales y stack comprobado (§14)", "Compartido", "CUMPLIDO", "requirements-training.txt; requirements-ui.lock.txt", DOC+"H4_INFORME_FINAL.md")
add("3", "Cierre y revisión conjunta de checklist y tracking (§14 d15)", "Compartido", "PARCIAL", "—", DOC+"H4_MATRIZ_CUMPLIMIENTO.md", "Matriz auditada nueva; casillas de guía oficial fechada no se actualizan como si hubiera aceptación conjunta.")
add("3", "Participación de Erika y Ross en exposición/defensa (§14–17)", "Compartido", "PENDIENTE", "—", DOC+"H4_GUIA_EJECUCION_WINDOWS.md", "No hay evidencia de ensayo conjunto, asistencia o defensa realizada.")
add("3", "Preparar presentación y demo conjunta defendible (§14 d15)", "Compartido", "PARCIAL", "—", DOC+"H4_GUIA_EJECUCION_WINDOWS.md", "Guion documentado; no consta validación por ambos ni demo visual completa.")
add("2", "MLPRegressor, opcional (§8)", "Erika", "NO APLICA", "—", DOC+"H4_IMPLEMENTACION_MODELO_PREDICTIVO.md", "No autorizada como experimento obligatorio; no penaliza el porcentaje.")
add("2", "Baseline estacional adicional, opcional (§8)", "Erika", "NO APLICA", "—", DOC+"H4_IMPLEMENTACION_MODELO_PREDICTIVO.md", "El baseline obligatorio lag1 sí está evaluado.")
add("H5", "API/administración productiva, Neon, jobs, reposición y alertas (§14)", "Compartido", "NO APLICA", "—", DOC+"H4_IMPLEMENTACION_MODELO_PREDICTIVO.md", "Fuera de H4; no se implementa ni toca producción.")
add("Futuro", "Intervalos de predicción con cobertura objetivo 95 % (solicitud T14)", "Erika", "NO APLICA", "demand_runtime.py", DOC+"H4_INFORME_FINAL.md", "Capacidad futura no implementada: no existe calibración temporal independiente ni validación de cobertura. TEST no se calibra.")
add("1–3", "Dependencias de entrenamiento/UI aisladas y versiones reales (§12, §15)", "Erika", "CUMPLIDO", "requirements-training.txt; requirements-ui.lock.txt", DOC+"tareas_erika/tarea_12/evidence/example.json; docs/H4/H4_INFORME_FINAL.md")
add("2–3", "Demo interactiva normal: disponer de ACTIVE compatible al usar PREDECIR (§13)", "Compartido", "PARCIAL", "demand_runtime.py; streamlit_app.py; ui_panels.py", FLOW, "D03: create_runtime empieza vacío y no hay botón que active V1; CLI/AppTest actúan solo sobre su propio proceso/sesión.")
add("1–3", "Seguridad: sin conexiones/escrituras productivas ni cambios de histórico (§3, §12–14)", "Compartido", "CUMPLIDO", "demand_runtime.py; retraining.py; model_comparison.py", DOC+"tareas_erika/tarea_14/evidence/integrity_after.json")
add("3", "Recorrido reproducible y separado de una evaluación TEST oficial (§14–15)", "Erika", "CUMPLIDO", "validate_h4_integral.py; validate_candidate_comparison.py", DOC+"H4_GUIA_EJECUCION_WINDOWS.md; "+FLOW)
add("2", "TimeSeriesSplit de tres cortes internos como comprobación adicional propuesta (§6)", "Erika", "NO APLICA", "train_random_forest.py", DOC+"H4_IMPLEMENTACION_MODELO_PREDICTIVO.md", "Se ejecutó el split interno fijo registrado de V1; la propuesta adicional no fue requisito autorizado. No se reentrena para añadirla.")
add("2–3", "Métricas y desgloses por escenarios con número de casos/cobertura (§9)", "Ross", "PARCIAL", "ui_analysis.py; ui_panels.py", "ml/demand/test_ross_ui.py; "+FLOW, "El registro conserva Escenario y se prueban los ocho; las vistas de errores agrupan tienda/producto/rotación/mes, no escenario.")

# Las referencias repetidas de la guía se vinculan, no suman puntos adicionales.
def ids(*nums):
    return [f"R{n:02}" for n in nums]

FUNCTIONAL = [ids(2,3),ids(2),ids(2),ids(1,2),ids(9),ids(22),ids(24),ids(25),ids(25),ids(26),ids(27),ids(28),ids(34,42),ids(60),ids(33),ids(34),ids(31),ids(29),ids(58),ids(31,68),ids(60),ids(54,55,56,69),ids(68),ids(38,39,40,41,42,43,44,45,47,48),ids(36,49),ids(62),ids(11,12,13),ids(33),ids(14,16,17),ids(34,35),ids(36,37,19,20,50),ids(3,55)]
CHECKLIST = [ids(2),ids(6,7,10),ids(22),ids(24),ids(25),ids(29),ids(26),ids(27),ids(28),ids(31),ids(11,12),ids(13,14),ids(33,69),ids(16,17),ids(34),ids(36),ids(40,41,42,44,45),ids(48),ids(19,20,21,50,3),ids(60),ids(68),ids(38,39,40),ids(58),ids(31,49),ids(54,56,71),ids(62,63)]
DESIGN = [ids(1),ids(1),ids(1),ids(2),ids(6),ids(7),ids(6),ids(1),ids(9),ids(10),ids(22,24,25,64),ids(25),ids(26,35),ids(61),ids(2,3,60),ids(60),ids(11,12,13,16,69),ids(36,39,40,45,48)]
GROUPS = [ids(6,7,12),ids(33),ids(4,13),ids(8),ids(16,18),ids(18,38),ids(14,17),ids(8,13),ids(15),ids(35,43),ids(36,37),ids(39,40,41),ids(45,46,47),ids(48),ids(19,20,21,50),ids(3,55,56,57)]
SCHEDULE = [
    (ids(3,4,5,6,7,14),ids(11,12,13,34),ids(1,6,11)),
    (ids(5,7,13,14,16,19,20),ids(11,12,34),ids(7,19,20)),
    (ids(14,16,19),ids(8,11,12,13),ids(2,8,13,16,55)),
    (ids(22,65),ids(23,33,35),ids(23)),
    (ids(10,24,29),ids(30,33,34,35),ids(33)),
    (ids(25,26,27),ids(26,34,35),ids(27,29)),
    (ids(27,28,31),ids(9,28),ids(28)),
    (ids(31,32,49),ids(34,35,36),ids(33,36)),
    (ids(38,39,40,41),ids(36,42,43),ids(44,45,46,47)),
    (ids(19,48,51),ids(8,13,15,19,36,53),ids(48,50,52)),
    (ids(59,63),ids(56,57,63),ids(29,58,59,61,62,63,71)),
]


def main():
    guide = (ROOT/DOC/"H4_IMPLEMENTACION_MODELO_PREDICTIVO.md").read_text(encoding="utf-8")
    functional_section = guide.split("**Lo que debemos mostrar al finalizar H4**",1)[1].split("Las pruebas siguientes",1)[0]
    design_section = guide.split("**Lo que debemos presentar antes de implementar**",1)[1].split("**Lo que debemos mostrar al finalizar H4**",1)[0]
    numbered = lambda text: [(int(m.group(1)),m.group(2).strip()) for m in re.finditer(r"^\| (\d+) \| (.+?) \|$",text,re.M)]
    checklist = re.findall(r"^- \[ \] (.+)$",guide,re.M)
    groups_section = guide.split("| Grupo de prueba |",1)[1].split("## 18.",1)[0]
    groups = [line.split("|")[1:3] for line in groups_section.splitlines() if line.startswith("| ") and not line.startswith("|---")]
    schedule_section = guide.split("| Semana | Día |",1)[1].split("La semana 1 entrega",1)[0]
    schedule = [line.split("|")[1:-1] for line in schedule_section.splitlines() if re.match(r"\| [123] \|",line)]
    assert len(numbered(functional_section))==32 and len(checklist)==26 and len(schedule)==11 and len(groups)==16
    crosswalk = []
    for group, originals, mapping in [("§17 funcional",numbered(functional_section),FUNCTIONAL),("§17 diseño",numbered(design_section),DESIGN),("§14 checklist",list(enumerate(checklist,1)),CHECKLIST)]:
        assert len(originals)==len(mapping)
        for (number,text), refs in zip(originals,mapping):
            crosswalk.append(dict(origen=f"{group} {number}", requisito_literal=text, filas=refs))
    for i, (values, mapping) in enumerate(zip(schedule,SCHEDULE),1):
        week,day,erika,ross,shared = [x.strip() for x in values]
        for owner,text,refs in zip(("Erika","Ross","Compartido"),(erika,ross,shared),mapping):
            crosswalk.append(dict(origen=f"§14 semana {week}, día {day}, {owner}", requisito_literal=text, filas=refs))
    for (label,text), refs in zip(groups,GROUPS):
        crosswalk.append(dict(origen="§17 pruebas: "+label.strip(), requisito_literal=text.strip(), filas=refs))
    by_id={r["id"]:r for r in rows}
    for entry in crosswalk:
        for rid in entry["filas"]:
            assert rid in by_id
    for row in rows:
        row["fuentes_originales"]="; ".join(c["origen"] for c in crosswalk if row["id"] in c["filas"])
    counts=Counter(r["estado"] for r in rows)
    applicable=len(rows)-counts["NO APLICA"]
    summary=dict(total=len(rows), estados=dict(counts), aplicables=applicable,
                 porcentaje_estricto=round(100*counts["CUMPLIDO"]/applicable,2),
                 porcentaje_con_medios_parciales=round(100*(counts["CUMPLIDO"]+0.5*counts["PARCIAL"])/applicable,2),
                 items_originales_trazados=len(crosswalk), formula="CUMPLIDO / (total - NO APLICA); PARCIAL no suma puntos al porcentaje estricto")
    summary["por_responsable"]={owner:dict(Counter(r["estado"] for r in rows if r["responsable"]==owner)) for owner in ("Erika","Ross","Compartido")}
    (OUT/"matrix.json").write_text(json.dumps(dict(summary=summary,requirements=rows,crosswalk=crosswalk),indent=2,ensure_ascii=False),encoding="utf-8")
    with (ROOT/DOC/"tareas_erika/tarea_14/H4_MATRIZ_CUMPLIMIENTO.csv").open("w",newline="",encoding="utf-8-sig") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    text=["# H4 — Matriz de cumplimiento auditada, Tarea 14", "", "Estado al 9 de noviembre de 2026. No sustituye la aceptación conjunta ni las secciones históricas fechadas.", "", "## Criterio", "", f"{len(rows)} requisitos normalizados, {applicable} aplicables. Los listados repetidos se cruzan con los mismos IDs, sin sumar puntos varias veces.", "", "```json",json.dumps(summary,indent=2,ensure_ascii=False),"```", "", "CUMPLIDO exige evidencia técnica verificable. PARCIAL indica alcance incompleto, divergencia con la guía o validación visual pendiente. PENDIENTE carece de demostración requerida. NO APLICA excluye opciones no obligatorias, H5 y capacidad futura de intervalos. El porcentaje estricto da cero puntos a PARCIAL/PENDIENTE. El alternativo asigna 0.5 a PARCIAL y no certifica aceptación.", "", "La secuencia integral PASS acredita el recorrido automatizado; sus diagnósticos D01/D02 y la falta de activación V1 desde la UI impiden concluir 100 %. No se equipara AppTest a revisión visual.", "", "## Requisitos normalizados", "", "| ID | Semana | Requisito original | Responsable | Estado | Técnico | Visual | Implementación | Prueba/evidencia | Observaciones |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        text.append("| "+" | ".join(str(r[k]).replace("|","/") for k in ("id","semana","requisito_original","responsable","estado","cumplimiento_tecnico","demostracion_visual","archivos","evidencia","observaciones"))+" |")
    text += ["", "## Cobertura literal de listas originales", "", "Se conservan los textos originales y el responsable de cada columna del cronograma. La relación muchos-a-muchos explica la normalización.", "", "| Fuente | Requisito literal | IDs de la matriz |", "|---|---|---|"]
    text += ["| "+c["origen"]+" | "+c["requisito_literal"].replace("|","/")+" | "+", ".join(c["filas"])+" |" for c in crosswalk]
    (ROOT/DOC/"tareas_erika/tarea_14/H4_MATRIZ_CUMPLIMIENTO.md").write_text("\n".join(text)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))


if __name__=="__main__":
    main()
