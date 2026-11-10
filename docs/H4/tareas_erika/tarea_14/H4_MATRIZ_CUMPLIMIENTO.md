# H4 — Matriz de cumplimiento auditada, Tarea 14

> Fotografía histórica T14 conservada. La [revisión T15](../tarea_15/H4_MATRIZ_CUMPLIMIENTO_T15.md)
> cambia únicamente R17, R20 y R69 con evidencia nueva; no modifica esta puntuación retrospectivamente.

Estado al 9 de noviembre de 2026. No sustituye la aceptación conjunta ni las secciones históricas fechadas.

## Criterio

73 requisitos normalizados, 68 aplicables. Los listados repetidos se cruzan con los mismos IDs, sin sumar puntos varias veces.

```json
{
  "total": 73,
  "estados": {
    "CUMPLIDO": 47,
    "PARCIAL": 18,
    "PENDIENTE": 3,
    "NO APLICA": 5
  },
  "aplicables": 68,
  "porcentaje_estricto": 69.12,
  "porcentaje_con_medios_parciales": 82.35,
  "items_originales_trazados": 125,
  "formula": "CUMPLIDO / (total - NO APLICA); PARCIAL no suma puntos al porcentaje estricto",
  "por_responsable": {
    "Erika": {
      "CUMPLIDO": 25,
      "PARCIAL": 2,
      "NO APLICA": 4
    },
    "Ross": {
      "PARCIAL": 5,
      "CUMPLIDO": 4,
      "PENDIENTE": 2
    },
    "Compartido": {
      "CUMPLIDO": 18,
      "PARCIAL": 11,
      "PENDIENTE": 1,
      "NO APLICA": 1
    }
  }
}
```

CUMPLIDO exige evidencia técnica verificable. PARCIAL indica alcance incompleto, divergencia con la guía o validación visual pendiente. PENDIENTE carece de demostración requerida. NO APLICA excluye opciones no obligatorias, H5 y capacidad futura de intervalos. El porcentaje estricto da cero puntos a PARCIAL/PENDIENTE. El alternativo asigna 0.5 a PARCIAL y no certifica aceptación.

La secuencia integral PASS acredita el recorrido automatizado; sus diagnósticos D01/D02 y la falta de activación V1 desde la UI impiden concluir 100 %. No se equipara AppTest a revisión visual.

## Requisitos normalizados

| ID | Semana | Requisito original | Responsable | Estado | Técnico | Visual | Implementación | Prueba/evidencia | Observaciones |
|---|---|---|---|---|---|---|---|---|---|
| R01 | 1 | Problema, unidad producto + tienda + mes, origen sintético y horizonte mensual (§1–4) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/simulator_inputs.py | docs/H4/H4_IMPLEMENTACION_MODELO_PREDICTIVO.md | Definición técnica; no certifica demanda comercial. |
| R02 | 1 | Dataset validado con estadísticas, distribución y ejemplos sintéticos (§14) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/data/escenarios_v1_1/validacion.json; ml/demand/data/escenarios_v1_1/manifest.json | ml/demand/test_generate_synthetic.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R03 | 1 | Verificar dataset y hashes, conservar 1.1 inmutable (§14 d1–2) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/simulator_inputs.py | docs/H4/tareas_erika/tarea_14/evidence/integrity_after.json |  |
| R04 | 1 | Catálogo de referencia, IDs válidos, tiendas y reservados (§3–4) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/catalog_reference.json; ml/demand/simulator_inputs.py | ml/demand/test_simulator_ui.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R05 | 1 | Motor separado del generador histórico y conservación de versiones (§13–14) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_engine.py; ml/demand/generate_synthetic.py; ml/demand/versions/generate_v1_0_0.py | docs/H4/tareas_erika/tarea_14/evidence/integrity_after.json |  |
| R06 | 1 | Contrato de nueve columnas y cinco features; excluir IDs y target de X (§4) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/ml_pipeline.py; ml/demand/simulator_inputs.py | ml/demand/test_ml_pipeline.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R07 | 1 | Lags del mismo par, meses exactos y calendario seno/coseno (§4, §13) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_engine.py; ml/demand/simulator_inputs.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | En ajuste incremental los lags se reconstruyen desde cierres. |
| R08 | 1 | Validaciones numéricas, tipos, faltantes, IDs y casos ambiguos (§10, §13) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/simulator_inputs.py; ml/demand/ml_pipeline.py | ml/demand/test_simulator_validation.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R09 | 1–2 | TRAIN/VALIDATION/TEST por meses completos sin solapamiento (§6) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/ml_pipeline.py | ml/demand/test_ml_pipeline.py; ml/demand/reports/v1_selection_manifest.json; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R10 | 2 | Preprocesamiento ajustado solo con TRAIN, conjunto modelo/scaler reproducible (§7) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/train_linear_regression.py; ml/demand/train_random_forest.py | ml/demand/test_linear_regression.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt | RF sin scaler; LR conserva su transformación. |
| R11 | 1 | Interfaz Streamlit con selectores de producto, tienda y mes (§13, §14 d1–4) | Ross | PARCIAL | CUMPLIDO | PENDIENTE | ml/demand/streamlit_app.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | AppTest verifica controles; revisión visual no realizada. |
| R12 | 1 | Edición manual y confirmación de entradas; invalidación de emisión pendiente (§13) | Ross | PARCIAL | CUMPLIDO | PENDIENTE | ml/demand/streamlit_app.py; ml/demand/ui_runtime.py | ml/demand/test_ross_ui.py; docs/H4/tareas_erika/tarea_14/evidence/integral.json | Técnicamente verificado; presentación visual pendiente. |
| R13 | 1 | Ocho escenarios, precargas y escenario como metadato, no feature (§13) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_engine.py; ml/demand/streamlit_app.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | Seis meses por cada escenario con V1 real o abstención. |
| R14 | 1 | Resultado mensual manual/automático reproducible e idempotente (§13) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_engine.py; ml/demand/ui_panels.py | ml/demand/test_demand_engine.py; docs/H4/tareas_erika/tarea_14/evidence/integral.json | Reproducibilidad de la misma secuencia de acciones por sesión; ver R20 para intercalado de pares. |
| R15 | 1 | STOCKOUT: separar latente, disponibilidad y observado; no recortar manual inválido (§13) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_engine.py; ml/demand/ui_panels.py | ml/demand/test_engine_integration.py; docs/H4/tareas_erika/tarea_14/evidence/integral.json |  |
| R16 | 1 | Cierre único, avance calendario y actualización de lags (§13) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_engine.py; ml/demand/ui_runtime.py; ml/demand/ui_panels.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | Cierre explícito alternado con cierre al avanzar; no duplica meses. |
| R17 | 1 | Sin resultado o con mes incompleto no se cierra (§13) | Compartido | PARCIAL | PARCIAL | NO APLICA | ml/demand/ui_panels.py; ml/demand/demand_engine.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | D02: avance cierra observado manual con casilla de mes completo false. Sin resultado sí bloquea. |
| R18 | 1 | Observado revelado bloquea edición y segunda predicción del mismo mes (§13) | Ross | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/ui_runtime.py; ml/demand/streamlit_app.py | ml/demand/test_ross_ui.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R19 | 1 | Sesiones y datos por producto/tienda aislados; no trasladar ventas (§13) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_engine.py; ml/demand/ui_runtime.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | Diccionarios de cierres por par y sesiones separados; no equivale a aislamiento del azar de R20. |
| R20 | 1 | Azar independiente por sesión y por par producto–tienda (§13) | Erika | PARCIAL | PARCIAL | NO APLICA | ml/demand/demand_engine.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | D01: hay un único Random por sesión; otro par consume la secuencia del primero. |
| R21 | 1–3 | Candidato y referencia ACTIVE independientes por sesión y por par (§13) | Compartido | PARCIAL | PARCIAL | NO APLICA | ml/demand/ui_panels.py; ml/demand/demand_runtime.py; ml/demand/retraining.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | ACTIVE y último resultado son de sesión, no referencias distintas por par; decisiones identifican correctamente el par. |
| R22 | 2 | Baseline último mes evaluado en VALIDATION (§8, §14 d6) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/ml_pipeline.py; ml/demand/reports/experiments.csv | ml/demand/test_ml_pipeline.py; ml/demand/reports/v1_selection_manifest.json |  |
| R23 | 2 | Baseline interactivo claramente etiquetado (§14 d6) | Ross | PARCIAL | PARCIAL | NO APLICA | ml/demand/ui_runtime.py; ml/demand/ui_panels.py | ml/demand/test_ross_ui.py; docs/H4/tareas_erika/tarea_14/evidence/integral.json | Referencia baseline registrada con inferencia; no hay ruta independiente de baseline sin ACTIVE. |
| R24 | 2 | LinearRegression entrenada, pipeline, registro y predicciones originales (§8, §14 d7–8) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/train_linear_regression.py; ml/demand/models/linear_regression_candidate.joblib; ml/demand/reports/experiments.csv | ml/demand/test_linear_regression.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R25 | 2 | RandomForest: búsqueda limitada, control temporal interno y reproducibilidad (§8, §14 d9–10) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/train_random_forest.py; ml/demand/models/random_forest_candidate.joblib | ml/demand/test_random_forest.py; ml/demand/reports/v1_selection_manifest.json; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R26 | 2 | Comparación VALIDATION, MAE/RMSE/R², cobertura, errores por grupos (§8–9) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/select_v1.py; ml/demand/reports/v1_selection_manifest.json | ml/demand/test_select_v1.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt | Métricas previas leídas, no recalculadas oficialmente. |
| R27 | 2–3 | Selección V1 justificada y congelada antes de TEST (§8, §14 d10–11) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/select_v1.py; ml/demand/reports/v1_selection_manifest.json | ml/demand/test_select_v1.py; ml/demand/reports/v1_test_evaluation.json |  |
| R28 | 3 | Evaluación TEST final única con decisiones congeladas (§9, §14 d11) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/evaluate_v1.py; ml/demand/reports/v1_test_evaluation.json | docs/H4/tareas_erika/tarea_14/evidence/integrity_after.json | Se verifica reporte existente; no se ejecuta TEST oficial otra vez. |
| R29 | 2–3 | Registro de experimentos con parámetros, métricas, tiempos y versiones (§15) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/reports/experiments.csv | docs/H4/tareas_erika/tarea_14/evidence/integrity_after.json | Registro oficial preservado; ensayos nuevos usan manifiestos separados. |
| R30 | 2 | Integración y revisión de baseline, LinearRegression y RandomForest reales en interfaz (§13 cierre Ross) | Compartido | PARCIAL | PARCIAL | PENDIENTE | ml/demand/ui_runtime.py; ml/demand/demand_runtime.py; ml/demand/train_linear_regression.py | ml/demand/test_linear_regression.py; docs/H4/tareas_erika/tarea_14/evidence/integral.json | V1 RF sí en AppTest; no demostración equivalente de LR real dentro de Streamlit. |
| R31 | 3 | Artefacto modelo/preprocesamiento, versiones, corte y huellas verificados (§15) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_runtime.py; ml/demand/reports/v1_selection_manifest.json | ml/demand/test_demand_runtime.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R32 | 3 | Contrato Ross create_runtime/get_active_model/predict; sin Neon ni uploads ejecutables (§15) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_runtime.py; ml/demand/ui_runtime.py | ml/demand/test_demand_runtime.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R33 | 2–3 | PREDECIR con ACTIVE real, features editadas y sin fit implícito (§13) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_runtime.py; ml/demand/ui_panels.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | Activación explícita mediante arnés; falta vía interactiva normal, R69. |
| R34 | 2–3 | Gráficos/tablas de historia, predicción, comparación y errores (§13–14) | Ross | PARCIAL | CUMPLIDO | PENDIENTE | ml/demand/streamlit_app.py; ml/demand/ui_panels.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | Elementos renderizados en AppTest; aspecto visual no verificado. |
| R35 | 2–3 | MAE/RMSE/R², cobertura, baseline y errores por tienda/producto/mes/rotación (§9, §13) | Ross | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/ui_analysis.py; ml/demand/ui_panels.py | ml/demand/test_ross_ui.py; ml/demand/test_model_comparison.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt | Sin métrica ficticia para abstenciones o target constante. |
| R36 | 3 | Monitoreo: dos ventanas de tres meses; revisión recomendada demostrativa (§13) | Ross | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/ui_analysis.py; ml/demand/ui_panels.py | ml/demand/test_ross_ui.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt | No prueba estadística de drift ni disparador automático de fit. |
| R37 | 3 | Priorizar PROBLEMA TÉCNICO/DATOS antes de recomendar reentrenamiento (§13) | Ross | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/ui_analysis.py | ml/demand/test_ross_ui.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R38 | 3 | Nuevos observados cerrados verificados; no usar predicciones o latentes como target (§11) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/retraining.py; ml/demand/demand_engine.py | ml/demand/test_retraining.py; docs/H4/tareas_erika/tarea_14/evidence/integral.json | Observados concordantes motor/diario; las hipótesis quedan en trace. |
| R39 | 3 | Fijar corte antes del ajuste y reservar meses nuevos sin reutilizar TEST V1 (§11) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/retraining.py; ml/demand/model_comparison.py | ml/demand/test_retraining.py; docs/H4/tareas_erika/tarea_14/evidence/integral.json | Protocolo aprobado: 3 historia + 6 ajuste + 3 reserva; no se leen CSV históricos para ajustar. |
| R40 | 3 | ENSAYAR REENTRENAMIENTO explícito; progreso, exclusión concurrente, datos insuficientes (§11) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/retraining.py; ml/demand/ui_panels.py | ml/demand/test_retraining.py; docs/H4/tareas_erika/tarea_14/evidence/integral.json |  |
| R41 | 3 | Crear CANDIDATE versionado independiente, sin sobrescribir ni activar (§11, §15) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/retraining.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json; docs/H4/tareas_erika/tarea_12/evidence/example.json |  |
| R42 | 3 | Comparación justa en filas comunes, cinco features y ventanas posteriores a ambos ajustes (§11) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/model_comparison.py | ml/demand/test_model_comparison.py; docs/H4/tareas_erika/tarea_14/evidence/integral.json |  |
| R43 | 3 | Métricas de comparación, cobertura y evidencia insuficiente explícitas (§11) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/model_comparison.py | docs/H4/tareas_erika/tarea_13/evidence/validation-60a54a1435134d62b247c71b8369d50c.json | Tres observaciones: R² solo descriptivo; no declarar superioridad. |
| R44 | 3 | Rechazo con motivo, identidad y resultados originales conservados (§11, §15) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/model_comparison.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json |  |
| R45 | 3 | ACTIVAR CANDIDATO elegible desde simulador con comparación y criterios previos (§11) | Compartido | PARCIAL | PARCIAL | NO APLICA | ml/demand/demand_runtime.py; ml/demand/ui_panels.py | docs/H4/tareas_erika/tarea_13/evidence/fixture_validation.json | Ruta positiva solo en fixtures por autorización expresa; promoción real bloqueada. No es una falla a eludir. |
| R46 | 3 | Impedir promoción automática y autorización desde JSON importados (§11) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_runtime.py; ml/demand/model_comparison.py | ml/demand/test_model_comparison.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R47 | 3 | Demostrar promoción/rechazo y retorno con fixtures aislados (§14 d13–14) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/test_model_comparison.py | docs/H4/tareas_erika/tarea_13/evidence/fixture_validation.json; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt | Política de pruebas no importada por la app. |
| R48 | 3 | Rollback compatible con motivo, hashes y predicciones previas inmutables (§11) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_runtime.py | ml/demand/test_model_comparison.py; docs/H4/tareas_erika/tarea_14/evidence/integral.json |  |
| R49 | 3 | Registro local de versiones/estados y decisiones completo (§11, §15) | Erika | PARCIAL | PARCIAL | NO APLICA | ml/demand/demand_runtime.py; ml/demand/retraining.py; ml/demand/model_comparison.py | docs/H4/tareas_erika/tarea_13/H4_TAREA_13_COMPARACION_DECISION.md | Candidatos y decisiones persistidos; no registro unificado ARCHIVED/REJECTED/ACTIVE por par. ACTIVE solo en memoria. |
| R50 | 3 | Reset restaura escenario, seed, reloj y referencia V1 local (§13) | Compartido | PARCIAL | PARCIAL | NO APLICA | ml/demand/streamlit_app.py; ml/demand/demand_runtime.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | Restaura datos/seed, pero deja SIN ACTIVE, según autorizaciones T10–13; difiere del texto original. |
| R51 | 3 | Carga incompatible/fallo de inferencia: abstención segura sin salida ficticia (§13) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_runtime.py; ml/demand/ui_panels.py | ml/demand/test_demand_runtime.py; ml/demand/test_ross_ui.py; docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt |  |
| R52 | 3 | Exportar sesión con seed/estado aleatorio, rama, procedencia y revisiones (§15) | Compartido | PARCIAL | PARCIAL | NO APLICA | ml/demand/ui_panels.py; ml/demand/retraining.py; ml/demand/demand_engine.py | ml/demand/test_ross_ui.py; docs/H4/tareas_erika/tarea_14/evidence/integral.json | DESCARGAR SESIÓN mantiene generator_seed=null; no serializa rama/estado RNG ni origen manual/generado por cierre. Incremental sí preserva parte. |
| R53 | 3 | Seis meses coherentes, stockout, nuevo, mes incompleto y cambio persistente (§13 cierre Ross) | Compartido | PARCIAL | PARCIAL | NO APLICA | ml/demand/validate_h4_integral.py; ml/demand/ui_panels.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | 60 meses validados; D02 sobre completitud impide declarar cumplimiento pleno. |
| R54 | 3 | Ciclo integrado edición→inferencia→observado→candidato→comparación→rechazo→retorno (§13) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/validate_h4_integral.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | 12 meses + candidato temporal; alcance automatizado con activación V1 programática, no demo visual. |
| R55 | 1–3 | Pruebas del simulador, regresión y conservación de hashes (§17) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/test_engine_integration.py; ml/demand/test_retraining.py; ml/demand/test_model_comparison.py | docs/H4/tareas_erika/tarea_14/evidence/full_tests.txt | 375 anteriores siguen pasando; no implica ausencia de defectos nuevos en diagnósticos. |
| R56 | 3 | Revisión visual real en computadora y capturas (§13 cierre Ross) | Ross | PENDIENTE | PARCIAL | PENDIENTE | ml/demand/streamlit_app.py; ml/demand/ui_panels.py | docs/H4/tareas_erika/tarea_14/evidence/visual_review.json | Computer Use se detuvo por no poder verificar la URL; cero capturas. |
| R57 | 3 | Revisión visual en pantalla estrecha (§13 cierre Ross) | Ross | PENDIENTE | PARCIAL | PENDIENTE | ml/demand/streamlit_app.py | docs/H4/tareas_erika/tarea_14/evidence/visual_review.json | No realizada; AppTest no comprueba el aspecto responsive. |
| R58 | 1–3 | Prompts con procedencia, sin inventar texto o fechas (§15) | Compartido | PARCIAL | PARCIAL | NO APLICA | — | docs/H4/PROMPTS_MODELO_PREDICTIVO_H4.md | Log existente llega al 4 de noviembre; este cierre aporta resumen separado de T10–14, no recupera prompts originales T1–9. |
| R59 | 3 | Documentación técnica y guía reproducible de ejecución/demostración (§14 d15) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/validate_h4_integral.py | docs/H4/H4_INFORME_FINAL.md; docs/H4/H4_GUIA_EJECUCION_WINDOWS.md |  |
| R60 | 1–3 | Riesgos, fallas, límites sintéticos/comerciales y stack comprobado (§14) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/requirements-training.txt; ml/demand/requirements-ui.lock.txt | docs/H4/H4_INFORME_FINAL.md |  |
| R61 | 3 | Cierre y revisión conjunta de checklist y tracking (§14 d15) | Compartido | PARCIAL | PARCIAL | NO APLICA | — | docs/H4/tareas_erika/tarea_14/H4_MATRIZ_CUMPLIMIENTO.md | Matriz auditada nueva; casillas de guía oficial fechada no se actualizan como si hubiera aceptación conjunta. |
| R62 | 3 | Participación de Erika y Ross en exposición/defensa (§14–17) | Compartido | PENDIENTE | PENDIENTE | NO APLICA | — | docs/H4/H4_GUIA_EJECUCION_WINDOWS.md | No hay evidencia de ensayo conjunto, asistencia o defensa realizada. |
| R63 | 3 | Preparar presentación y demo conjunta defendible (§14 d15) | Compartido | PARCIAL | PARCIAL | NO APLICA | — | docs/H4/H4_GUIA_EJECUCION_WINDOWS.md | Guion documentado; no consta validación por ambos ni demo visual completa. |
| R64 | 2 | MLPRegressor, opcional (§8) | Erika | NO APLICA | NO APLICA | NO APLICA | — | docs/H4/H4_IMPLEMENTACION_MODELO_PREDICTIVO.md | No autorizada como experimento obligatorio; no penaliza el porcentaje. |
| R65 | 2 | Baseline estacional adicional, opcional (§8) | Erika | NO APLICA | NO APLICA | NO APLICA | — | docs/H4/H4_IMPLEMENTACION_MODELO_PREDICTIVO.md | El baseline obligatorio lag1 sí está evaluado. |
| R66 | H5 | API/administración productiva, Neon, jobs, reposición y alertas (§14) | Compartido | NO APLICA | NO APLICA | NO APLICA | — | docs/H4/H4_IMPLEMENTACION_MODELO_PREDICTIVO.md | Fuera de H4; no se implementa ni toca producción. |
| R67 | Futuro | Intervalos de predicción con cobertura objetivo 95 % (solicitud T14) | Erika | NO APLICA | NO APLICA | NO APLICA | ml/demand/demand_runtime.py | docs/H4/H4_INFORME_FINAL.md | Capacidad futura no implementada: no existe calibración temporal independiente ni validación de cobertura. TEST no se calibra. |
| R68 | 1–3 | Dependencias de entrenamiento/UI aisladas y versiones reales (§12, §15) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/requirements-training.txt; ml/demand/requirements-ui.lock.txt | docs/H4/tareas_erika/tarea_12/evidence/example.json; docs/H4/H4_INFORME_FINAL.md |  |
| R69 | 2–3 | Demo interactiva normal: disponer de ACTIVE compatible al usar PREDECIR (§13) | Compartido | PARCIAL | PARCIAL | NO APLICA | ml/demand/demand_runtime.py; ml/demand/streamlit_app.py; ml/demand/ui_panels.py | docs/H4/tareas_erika/tarea_14/evidence/integral.json | D03: create_runtime empieza vacío y no hay botón que active V1; CLI/AppTest actúan solo sobre su propio proceso/sesión. |
| R70 | 1–3 | Seguridad: sin conexiones/escrituras productivas ni cambios de histórico (§3, §12–14) | Compartido | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/demand_runtime.py; ml/demand/retraining.py; ml/demand/model_comparison.py | docs/H4/tareas_erika/tarea_14/evidence/integrity_after.json |  |
| R71 | 3 | Recorrido reproducible y separado de una evaluación TEST oficial (§14–15) | Erika | CUMPLIDO | CUMPLIDO | NO APLICA | ml/demand/validate_h4_integral.py; ml/demand/validate_candidate_comparison.py | docs/H4/H4_GUIA_EJECUCION_WINDOWS.md; docs/H4/tareas_erika/tarea_14/evidence/integral.json |  |
| R72 | 2 | TimeSeriesSplit de tres cortes internos como comprobación adicional propuesta (§6) | Erika | NO APLICA | NO APLICA | NO APLICA | ml/demand/train_random_forest.py | docs/H4/H4_IMPLEMENTACION_MODELO_PREDICTIVO.md | Se ejecutó el split interno fijo registrado de V1; la propuesta adicional no fue requisito autorizado. No se reentrena para añadirla. |
| R73 | 2–3 | Métricas y desgloses por escenarios con número de casos/cobertura (§9) | Ross | PARCIAL | PARCIAL | NO APLICA | ml/demand/ui_analysis.py; ml/demand/ui_panels.py | ml/demand/test_ross_ui.py; docs/H4/tareas_erika/tarea_14/evidence/integral.json | El registro conserva Escenario y se prueban los ocho; las vistas de errores agrupan tienda/producto/rotación/mes, no escenario. |

## Cobertura literal de listas originales

Se conservan los textos originales y el responsable de cada columna del cronograma. La relación muchos-a-muchos explica la normalización.

| Fuente | Requisito literal | IDs de la matriz |
|---|---|---|
| §17 funcional 1 | Dataset generado, versión y hash | R02, R03 |
| §17 funcional 2 | Estadísticas descriptivas | R02 |
| §17 funcional 3 | Distribución del target | R02 |
| §17 funcional 4 | Ejemplos de filas identificadas como sintéticas | R01, R02 |
| §17 funcional 5 | Fechas, filas y comprobación del split | R09 |
| §17 funcional 6 | Resultado del baseline | R22 |
| §17 funcional 7 | LinearRegression entrenada | R24 |
| §17 funcional 8 | RandomForest entrenado | R25 |
| §17 funcional 9 | Configuraciones probadas | R25 |
| §17 funcional 10 | Métricas de validation | R26 |
| §17 funcional 11 | Modelo elegido y justificación | R27 |
| §17 funcional 12 | Evaluación final en test | R28 |
| §17 funcional 13 | Comparación gráfica entre modelos | R34, R42 |
| §17 funcional 14 | Errores encontrados y tratamiento | R60 |
| §17 funcional 15 | Primera predicción funcional | R33 |
| §17 funcional 16 | Primera visualización con historia y pronóstico | R34 |
| §17 funcional 17 | Modelo y preprocesamiento guardados | R31 |
| §17 funcional 18 | experiments.csv | R29 |
| §17 funcional 19 | Prompts utilizados, con procedencia | R58 |
| §17 funcional 20 | Configuraciones, seed y versiones | R31, R68 |
| §17 funcional 21 | Limitaciones técnicas y comerciales | R60 |
| §17 funcional 22 | Evidencia del conjunto funcional aproximado del 70 % | R54, R55, R56, R69 |
| §17 funcional 23 | Stack comprobado y dependencias propuestas claramente separados | R68 |
| §17 funcional 24 | Reentrenamiento local con CANDIDATE, comparación, promoción o rechazo y rollback demostrados | R38, R39, R40, R41, R42, R43, R44, R45, R47, R48 |
| §17 funcional 25 | Plan de monitoreo, versionado y rollback con límites H4/H5 | R36, R49 |
| §17 funcional 26 | Participación de Erika y Ross en demo y defensa | R62 |
| §17 funcional 27 | Simulador editable con ocho escenarios, selectores, lags y calendario derivado | R11, R12, R13 |
| §17 funcional 28 | Predicción interactiva después de editar, sin reentrenamiento implícito | R33 |
| §17 funcional 29 | Generación automática y observado manual, cierre y avance mensual correctos | R14, R16, R17 |
| §17 funcional 30 | Historial, gráfico actualizado, error reciente, cobertura y baseline comparable | R34, R35 |
| §17 funcional 31 | Revisión recomendada demostrativa, casos ambiguos, sesiones aisladas y reset reproducible | R36, R37, R19, R20, R50 |
| §17 funcional 32 | Evidencia de pruebas del simulador y conservación de los hashes de 1.1 | R03, R55 |
| §17 diseño 1 | Problemática de ventas mensuales | R01 |
| §17 diseño 2 | Objetivo predictivo a un mes | R01 |
| §17 diseño 3 | Unidad producto + tienda + mes | R01 |
| §17 diseño 4 | Dataset elegido y origen sintético | R02 |
| §17 diseño 5 | Estructura exacta de nueve columnas | R06 |
| §17 diseño 6 | Cinco features iniciales y disponibilidad | R07 |
| §17 diseño 7 | Target bruto y exclusiones | R06 |
| §17 diseño 8 | Aprendizaje supervisado | R01 |
| §17 diseño 9 | Split temporal con meses y filas | R09 |
| §17 diseño 10 | Normalización ajustada solo con training | R10 |
| §17 diseño 11 | Algoritmos a comparar | R22, R24, R25, R64 |
| §17 diseño 12 | Random Forest como candidato principal | R25 |
| §17 diseño 13 | MAE, RMSE y R², sin métricas inventadas | R26, R35 |
| §17 diseño 14 | Seis fases con evidencia esperada | R61 |
| §17 diseño 15 | Riesgos y límites de cobertura | R02, R03, R60 |
| §17 diseño 16 | Justificación de decisiones de la tabla anterior | R60 |
| §17 diseño 17 | Diseño del simulador, tecnología, controles y separación EDITAR/PREDECIR/REENTRENAR | R11, R12, R13, R16, R69 |
| §17 diseño 18 | Plan de avance, sesiones, monitoreo, promoción y rollback locales con pruebas previstas | R36, R39, R40, R45, R48 |
| §14 checklist 1 | Dataset validado con estadísticas, distribución y ejemplos identificados como sintéticos. | R02 |
| §14 checklist 2 | Pipeline de lectura, features y preprocesamiento reproducible. | R06, R07, R10 |
| §14 checklist 3 | Baseline evaluado. | R22 |
| §14 checklist 4 | LinearRegression entrenada y registrada. | R24 |
| §14 checklist 5 | RandomForestRegressor entrenado y registrado. | R25 |
| §14 checklist 6 | experiments.csv con ejecuciones, parámetros y resultados. | R29 |
| §14 checklist 7 | Validation temporal y análisis por grupos. | R26 |
| §14 checklist 8 | Modelo seleccionado con justificación. | R27 |
| §14 checklist 9 | Test final reservado y evaluado después de congelar decisiones. | R28 |
| §14 checklist 10 | Artefacto y transformaciones guardados. | R31 |
| §14 checklist 11 | Simulador interactivo con selectores y edición manual de los tres lags. | R11, R12 |
| §14 checklist 12 | Ocho escenarios, modo manual y generación automática local reproducible. | R13, R14 |
| §14 checklist 13 | Predicción interactiva con ACTIVE, sin fit al editar o predecir. | R33, R69 |
| §14 checklist 14 | Avance temporal con shift correcto y resultado posterior separado de features. | R16, R17 |
| §14 checklist 15 | Visualización actualizable de histórico, pronóstico, comparación y errores. | R34 |
| §14 checklist 16 | Monitoreo local, baseline comparable y revisión recomendada identificada como demostrativa. | R36 |
| §14 checklist 17 | CANDIDATE entrenado en un ensayo separado, comparación y rechazo o promoción locales. | R40, R41, R42, R44, R45 |
| §14 checklist 18 | Rollback local compatible y trazable, conservando V1 y su evaluación. | R48 |
| §14 checklist 19 | Sesiones aisladas, abstenciones, reset reproducible y dataset 1.1 inmutable. | R19, R20, R21, R50, R03 |
| §14 checklist 20 | Riesgos y fallas encontrados documentados. | R60 |
| §14 checklist 21 | Stack existente y propuesto documentado. | R68 |
| §14 checklist 22 | Plan y ensayo local de reentrenamiento documentados. | R38, R39, R40 |
| §14 checklist 23 | Prompts con procedencia. | R58 |
| §14 checklist 24 | Versiones, hashes y configuraciones conservados. | R31, R49 |
| §14 checklist 25 | Demo reproducible. | R54, R56, R71 |
| §14 checklist 26 | Exposición y defensa preparadas por ambos. | R62, R63 |
| §14 semana 1, día 1–2, Erika | Revisar generador 1.1 y hashes. Definir motor separado, contrato ML y generación dinámica | R03, R04, R05, R06, R07, R14 |
| §14 semana 1, día 1–2, Ross | Definir experiencia, controles editables, escenarios, validaciones y recorrido de usuario | R11, R12, R13, R34 |
| §14 semana 1, día 1–2, Compartido | Ambos cierran entradas, alcance de Streamlit y contrato de estado sin alterar el generador histórico | R01, R06, R11 |
| §14 semana 1, día 3–4, Erika | Implementar motor, escenarios, lectura, reloj, shift de lags y generador aleatorio de sesión | R05, R07, R13, R14, R16, R19, R20 |
| §14 semana 1, día 3–4, Ross | Implementar interfaz local, selectores, formularios, edición y gráficos iniciales | R11, R12, R34 |
| §14 semana 1, día 3–4, Compartido | Editor y motor independientes, calendario correcto y sesiones aisladas | R07, R19, R20 |
| §14 semana 1, día 5, Erika | Integrar motor y comprobar reproducibilidad | R14, R16, R19 |
| §14 semana 1, día 5, Ross | Integrar interfaz y ejecutar validaciones y casos ambiguos | R08, R11, R12, R13 |
| §14 semana 1, día 5, Compartido | Ambos prueban edición, avance, escenarios y reset. Simulador funcional de datos, sin fingir un modelo ya entrenado. Dataset, validadores, tests y documentación | R02, R08, R13, R16, R55 |
| §14 semana 2, día 6, Erika | Implementar baseline último mes y evaluar baseline estacional solo si hay cobertura | R22, R65 |
| §14 semana 2, día 6, Ross | Conectar flujo PREDECIR, origen, versión y visualización de métricas | R23, R33, R35 |
| §14 semana 2, día 6, Compartido | Baseline interactivo etiquetado. Referencia estacional opcional con soporte informado | R23 |
| §14 semana 2, día 7–8, Erika | Entrenar LinearRegression, preparar pipeline y registrar experimentos | R10, R24, R29 |
| §14 semana 2, día 7–8, Ross | Integrar inferencia con el simulador, mostrar features, resultado, versión y errores | R30, R33, R34, R35 |
| §14 semana 2, día 7–8, Compartido | Predicción tras editar, sin reentrenamiento implícito ni consulta de test | R33 |
| §14 semana 2, día 9–10, Erika | Entrenar RandomForest con configuraciones limitadas y validation | R25, R26, R27 |
| §14 semana 2, día 9–10, Ross | Preparar comparación visual y errores por tienda, rotación y mes | R26, R34, R35 |
| §14 semana 2, día 9–10, Compartido | Ambos eligen y congelan configuración V1 con validation. Simulador responde, métricas, gráficos y tracking | R27, R29 |
| §14 semana 3, día 11, Erika | Congelar parámetros, transformaciones y artefacto V1 | R27, R28, R31 |
| §14 semana 3, día 11, Ross | Verificar protocolo y separación de test | R09, R28 |
| §14 semana 3, día 11, Compartido | Ambos evalúan test final una vez y guardan V1 y resultados, incluso si no mejora al baseline | R28 |
| §14 semana 3, día 12, Erika | Integrar inferencia estable y registro local de versiones | R31, R32, R49 |
| §14 semana 3, día 12, Ross | Integrar historial, observados, predicciones, cobertura y MAE/RMSE recientes | R34, R35, R36 |
| §14 semana 3, día 12, Compartido | Simulación editable conectada a ACTIVE y monitoreo por versión | R33, R36 |
| §14 semana 3, día 13, Erika | Implementar ensayo local y creación de CANDIDATE sin sobrescribir ACTIVE | R38, R39, R40, R41 |
| §14 semana 3, día 13, Ross | Implementar revisión recomendada y comparación visual ACTIVE/CANDIDATE | R36, R42, R43 |
| §14 semana 3, día 13, Compartido | Ambos prueban promoción y rechazo sobre ventana nueva comparable, sin reutilizar el test de V1 | R44, R45, R46, R47 |
| §14 semana 3, día 14, Erika | Comprobar rollback compatible, carga y aislamiento de artefactos | R19, R48, R51 |
| §14 semana 3, día 14, Ross | Probar drift demostrativo, stockout, producto nuevo, mes incompleto, errores y sesiones | R08, R13, R15, R19, R36, R53 |
| §14 semana 3, día 14, Compartido | Ambos verifican retorno, abstenciones, reset y trazabilidad, sin reajustar por test | R48, R50, R52 |
| §14 semana 3, día 15, Erika | Presentar motor, modelos, configuración e inferencia | R59, R63 |
| §14 semana 3, día 15, Ross | Presentar interfaz, escenarios, métricas, gráficos y trazabilidad | R56, R57, R63 |
| §14 semana 3, día 15, Compartido | Ambos cierran demo interactiva, documentación, prompts, experiments.csv y defensa | R29, R58, R59, R61, R62, R63, R71 |
| §17 pruebas: Edición y contrato | Cambiar cada lag, aplicar el formulario y recalcular exactamente cinco features. Seno y coseno corresponden al mes. La inferencia utiliza lo ingresado, no una precarga anterior | R06, R07, R12 |
| §17 pruebas: Predicción tras editar | La salida se recalcula con ACTIVE compatible, sin fit. Se registra el nuevo corte de entradas. No se exige que siempre cambie el número, porque un árbol puede dar la misma salida | R33 |
| §17 pruebas: Selectores y escenario | Historia del par correcto, ocho precargas editables y metadatos excluidos de X. Cambiar escenario no borra silenciosamente una edición confirmada | R04, R13 |
| §17 pruebas: Validación numérica | Negativos, booleanos, decimales de unidades, NaN, Infinity, overflow, IDs y meses inválidos se rechazan también en el motor | R08 |
| §17 pruebas: Tiempo y doble clic | Avance de diciembre a enero, calendario correcto y shift 8/10/12 + 17 → 10/12/17. Reintentar cerrar no duplica historia ni genera otra muestra | R16, R18 |
| §17 pruebas: Resultado posterior | Cambiar el observado no afecta la predicción ya emitida del mismo mes. Solo entra como lag tras cierre. Editar después de revelarlo crea otra rama, sin sustituir el pronóstico evaluado | R18, R38 |
| §17 pruebas: Modos manual y automático | Mismo contrato de cantidades y cierre. La generación conserva el resultado entre reruns y no consume azar por dibujar la pantalla | R14, R17 |
| §17 pruebas: Ambiguos | Producto nuevo, tienda sin cobertura o menos de tres meses bloquean con HISTORIAL INSUFICIENTE. Mes faltante o incompleto bloquea con DATOS INCOMPLETOS, sin convertirlo en cero | R08, R13 |
| §17 pruebas: Stockout | Se diferencian demanda interna, disponibilidad y venta observada. La latente no llega al modelo y no se permite una venta superior a la disponibilidad declarada sin corregir el supuesto | R15 |
| §17 pruebas: Error y cobertura | MAE/RMSE conocidos con ejemplos controlados, baseline sobre los mismos meses y denominadores con abstenciones. Sin métricas ficticias cuando faltan casos | R35, R43 |
| §17 pruebas: Revisión recomendada | Un solo error no dispara revisión. Las dos ventanas cerradas y reglas demostrativas producen el estado esperado. Datos inválidos no motivan entrenamiento | R36, R37 |
| §17 pruebas: Candidato | Cortes futuros comparables, sin reutilizar test V1. Entrenar o fallar no sobrescribe ACTIVE. Se puede rechazar aunque sea una versión más nueva | R39, R40, R41 |
| §17 pruebas: Promoción local | Solo candidato aprobado y compatible. Cambio completo de referencia, conservando artefactos, métricas y decisiones de V1 | R45, R46, R47 |
| §17 pruebas: Rollback | Restauración compatible de modelo y preprocesador con motivo. Rechazo seguro si falta una versión válida, sin cambiar resultados históricos | R48 |
| §17 pruebas: Sesiones y reset | Dos sesiones no comparten historia, azar, candidatos o ACTIVE mutable. Reset restaura seed y escenario base, de forma reproducible y solo en la sesión actual | R19, R20, R21, R50 |
| §17 pruebas: Inmutabilidad y visual | Hashes de 1.1 iguales antes y después. Sin llamadas a base. Interfaz muestra origen SIMULACIÓN, versión, unidades, estados pendientes, errores, gráfico y acciones separadas | R03, R55, R56, R57 |
