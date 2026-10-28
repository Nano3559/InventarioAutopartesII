RepuestoPro — Plan de trabajo H4: modelo predictivo de demanda
Equipo: Erika (Machine Learning e inferencia Python) y Ross (integración Express y vistas React)
Duración planificada: 3 semanas, del 28/10/2026 al 17/11/2026 (15 días hábiles)
Estado: planificación; todas las casillas empiezan sin completar.
Documento base: H4_MODELO_PREDICTIVO_PROPUESTA_DETALLADA.md (19 secciones) y AUDITORIA_MODELO_PREDICTIVO_H4.md (27/10/2026).
Alcance de «100 %»: este plan cubre todos los puntos de la propuesta documental H4, incluidos los apartados conceptuales, técnicos y de evidencia. No significa que la implementación ya esté al 100 % ni garantiza una calificación. El documento propone alrededor del 70 % funcional para H4 y deja la integración comercial definitiva para H5. Las tareas opcionales o futuras se identifican por separado; no se presentan como requisitos obligatorios de H4.

1. Objetivo y criterios de aceptación
Objetivo: desarrollar y demostrar un experimento reproducible de regresión supervisada que estime unidades brutas vendidas el mes siguiente por producto y tienda, utilizando inicialmente datos sintéticos identificados y separados de Neon; conectar la inferencia a una vista demostrativa de RepuestoPro sin alterar inventario ni compras.
- [ ] Se explica el problema producto + tienda + mes, horizonte de un mes, target de ventas brutas y diferencia entre ventas observadas y demanda real insatisfecha.
- [ ] Se demuestra el flujo datos → variables → entrenamiento → validación → test → inferencia → interfaz.
- [ ] Cada entregable tiene evidencia verificable: archivo, comando reproducible, captura, prueba, commit o PR.
- [ ] Se distingue claramente datos sintéticos, ventas registradas de origen no certificado y datos comerciales reales certificados.
- [ ] Se mantiene el sistema comercial sin modificaciones automáticas de inventario, compras o reposiciones.
2. Distribución de trabajo y acuerdos
Área	Responsable	Apoyo / revisión	Resultado esperado
Auditoría y definición de problema	Erika	Ross	Decisiones y restricciones documentadas
Generador y dataset sintético	Erika	Ross	Dataset reproducible y manifiesto
Variables, splits y controles de leakage	Erika	Ross	Pipeline validado
Baseline, LinearRegression y RandomForest	Erika	Ross	Experimentos comparables
Evaluación, métricas y selección	Erika	Ross	Informe de resultados
Artefacto e inferencia Python	Erika	Ross	Contrato y predicción funcional
Diseño y endpoints Express	Ross	Erika	API de predicciones
Pantallas, filtros y gráficos React	Ross	Erika	Demo visual
Integración, seguridad y pruebas	Ross	Erika	Flujo de extremo a extremo
Documentación, prompts y exposición	Ambos	Ambos	Evidencias y presentación


Acuerdos de coordinación
- [ ] Día 1: confirmar que terminó el saneamiento previo y autorizar el inicio de H4; no modificar producción por esta tarea.
- [ ] Día 2: acordar contrato de API, formato de error, versión y distinción entre respuesta simulada y predicción del modelo.
- [ ] Día 5: revisión conjunta de dataset, variables y separación temporal.
- [ ] Día 10: congelar candidato elegido por validación y entregar a Ross un paquete de inferencia documentado.
- [ ] Día 13: prueba integrada y revisión de casos extremos.
- [ ] Día 15: ensayo de demo y cierre de evidencias.
- [ ] Usar ramas personales, commits pequeños y PR con revisión cruzada; evitar editar el mismo archivo simultáneamente.
3. Cronograma de 15 días — checklist ejecutable
Semana 1 — Datos y estructura (28 octubre – 3 noviembre)
Día 1 — Miércoles 28/10
- [ ] Erika: revisar auditoría y confirmar target, horizonte, unidad de análisis y exclusiones.
- [ ] Ross: identificar navegación, permisos y ubicación apropiada de la vista predictiva en RepuestoPro.
- [ ] Ambos: confirmar saneamiento y definir alcance H4 frente a H5.
Día 2 — Jueves 29/10
- [ ] Erika: diseñar generador DATOS_SINTETICOS_DEMANDA_H4 con semilla 42, parámetros documentados y meses 2024-10 a 2026-09.
- [ ] Ross: acordar API con Erika y crear estructura del módulo sin acoplarse todavía al modelo.
- [ ] Ambos: aprobar contrato de entrada/salida y política de errores y datos sintéticos.
Día 3 — Viernes 30/10
- [ ] Erika: generar dataset desde snapshot autorizado de productos y ubicaciones TIENDA, sin escribir en Neon.
- [ ] Erika: comprobar alta/media/baja rotación, ceros simulados, tendencia, estacionalidad, diferencias por tienda y ruido.
- [ ] Ross: crear vista inicial y componentes de filtros usando mocks etiquetados.
Día 4 — Lunes 02/11
- [ ] Erika: construir ventas_mes_anterior, ventas_hace_2_meses, ventas_hace_3_meses, promedio_3_meses, mes_sin, mes_cos y target_ventas_mes.
- [ ] Erika: documentar codificación de productId/locationId como claves/categorías, no cantidades.
- [ ] Ross: implementar selección de producto/tienda, mes objetivo y gráfico histórico provisional.
Día 5 — Martes 03/11
- [ ] Erika: crear partición cronológica por meses completos, verificar cantidades y leakage.
- [ ] Erika: preparar análisis exploratorio (distribuciones, meses cero, rotación, diferencias por tienda).
- [ ] Ross: probar contrato mock y estados de carga, error y ausencia de datos.
- [ ] Ambos: revisar reproducibilidad, cobertura y decisiones.
Hito semana 1:
- [ ] Dataset reproducible, manifiesto y controles de calidad.
- [ ] Features y splits comprobados.
- [ ] Primera interfaz conectada a mock explícito.
Semana 2 — Modelos y API (4 – 10 noviembre)
Día 6 — Miércoles 04/11
- [ ] Erika: implementar baseline ingenuo predicción = ventas_mes_anterior.
- [ ] Ross: implementar endpoint de demostración y validación de parámetros con respuesta mock marcada.
Día 7 — Jueves 05/11
- [ ] Erika: entrenar LinearRegression; documentar variables, coeficientes, negativos y resultados de validación.
- [ ] Ross: conectar React al endpoint de prueba; mostrar origen de datos y mes objetivo.
Día 8 — Viernes 06/11
- [ ] Erika: entrenar RandomForestRegressor y probar una búsqueda pequeña y documentada de hiperparámetros.
- [ ] Ross: incorporar tarjetas de unidades previstas y métricas, sin inventar valores reales.
Día 9 — Lunes 09/11
- [ ] Erika: aplicar validación temporal interna sobre meses únicos de training y comparar MAE, RMSE, R², estabilidad y casos con cero.
- [ ] Erika: revisar normalización y codificación sin ajustar transformadores con validation/test.
- [ ] Ross: terminar gráfico que diferencie historia sintética y pronóstico.
Día 10 — Martes 10/11
- [ ] Erika: seleccionar modelo con validation, congelar configuración y registrar la decisión; conservar test intacto hasta evaluación final.
- [ ] Erika: guardar modelo, preprocesamiento y metadatos; publicar contrato de inferencia Python.
- [ ] Ross: preparar adaptador Express ↔ Python y pruebas del contrato.
Hito semana 2:
- [ ] Baseline, regresión lineal y Random Forest reproducibles y comparados.
- [ ] Selección documentada sin usar test para ajustar.
- [ ] Modelo guardado y demo UI con API mock.
Semana 3 — Inferencia, integración y defensa (11 – 17 noviembre)
Día 11 — Miércoles 11/11
- [ ] Erika: finalizar inferencia para productId, locationId y mes objetivo con historial disponible al corte.
- [ ] Ross: sustituir mock por inferencia real del experimento y gestionar errores/timeouts.
Día 12 — Jueves 12/11
- [ ] Erika: ejecutar una sola evaluación final sobre test tras congelar decisiones; registrar MAE, RMSE, R² y conteos.
- [ ] Ross: mostrar predicción, modelo, origen sintético, historial y MAE de referencia en React.
Día 13 — Viernes 13/11
- [ ] Erika: probar ceros, baja rotación, IDs inválidos, negativos, datos insuficientes y reproducibilidad.
- [ ] Ross: calcular y mostrar sugerencia demostrativa de reposición sin escrituras de inventario.
- [ ] Ambos: ejecutar prueba de extremo a extremo y corregir fallos.
Día 14 — Lunes 16/11
- [ ] Erika: completar documentación de datos, modelos, parámetros, métricas, riesgos y limitaciones.
- [ ] Ross: completar pruebas de integración, UX, documentación de endpoints y capturas.
- [ ] Ambos: consolidar experiments.csv, registro de prompts y evidencias en el repositorio.
Día 15 — Martes 17/11
- [ ] Erika: ensayar explicación de aprendizaje supervisado, dataset, leakage, splits, modelos y métricas.
- [ ] Ross: ensayar flujo desde filtros hasta gráfico y recomendación.
- [ ] Ambos: revisar checklist, abrir/revisar PR y preparar demostración y conclusiones.
Hito semana 3:
- [ ] Predicción real del modelo experimental visible desde RepuestoPro.
- [ ] Test final, pruebas de integración y evidencias cerradas.
- [ ] Demo H4 reproducible y documentada.
4. Checklist de cobertura exhaustiva del documento H4 (19 secciones)
§1 Contexto y propósito
- [ ] Explicar alcance académico de H4 y significado de «aprox. 70 % funcional»; no equipararlo a porcentaje de archivos.
- [ ] Registrar que la propuesta original no equivale a implementación existente.
§2 Ejemplo del docente sobre seguimiento
- [ ] Preparar explicación de analogía: seguimiento de evolución física → seguimiento de ventas mensuales; distinguir seguimiento comercial y registro de experimentos.
§3 Problema predictivo
- [ ] Formalizar regresión supervisada de un paso: producto + tienda + mes → unidades brutas siguientes.
- [ ] Separar devoluciones de ventas brutas; no llamar a ventas observadas «demanda total».
- [ ] Documentar dos modos comerciales de la segunda auditoría: POR MENOR Product.price1, POR MAYOR Product.wholesalePrice; Product.price2 legacy. No reescribir SaleItem.unitPrice ni deducir modo histórico comparando con precios actuales.
§4 Datos actuales
- [ ] Citar la fotografía de auditoría del 27/10: 247 ventas, 520 detalles, 45 productos vendidos, 12 devoluciones; 226 ventas en tiendas y 21 en almacenes, marzo–octubre 2026.
- [ ] Advertir que procedencia no certificada y octubre incompleto impiden entrenar un predictor comercial fiable.
§5 Datos reales y sintéticos
- [ ] Generar DATOS_SINTETICOS_DEMANDA_H4, meses 2024-10 a 2026-09 (24), seed 42, orden estable por IDs.
- [ ] Usar snapshot autorizado de catálogo y ubicaciones TIENDA; documentar que son actuales proyectados sobre meses simulados.
- [ ] Simular rotación alta/media/baja, ceros, tendencia, estacionalidad, diferencias entre tiendas y ruido controlado.
- [ ] Conservar parámetros, snapshot, versiones de herramientas, hash y manifiesto.
- [ ] Verificar conteos reales del snapshot; 62 × 3 × 24 = 4.464 y 62 × 3 × 21 = 3.906 son ejemplos condicionales, no conteos garantizados.
- [ ] Comprobar que no se inserta ni mezcla dataset sintético en Sale, SaleItem o Neon.
§6 Tipo de aprendizaje
- [ ] Justificar aprendizaje supervisado frente a no supervisado y refuerzo; identificar X e y.
§7 Variables y fuga de información
- [ ] Crear columnas productId, locationId, mes_objetivo, 3 lags, promedio 3 meses, mes_sin, mes_cos, target_ventas_mes.
- [ ] Tratar IDs como categorías o claves; no como magnitudes.
- [ ] Excluir información posterior al cierre anterior, cantidades del mes objetivo, datos personales y snapshots actuales de stock, precios, costo o minStock como historia.
- [ ] Tratar devoluciones por separado, sin duplicarlas mediante joins.
- [ ] Diferenciar cero simulado conocido de ausencia de registros reales no verificada.
- [ ] Probar explícitamente ausencia de leakage temporal.
§8 Entrenamiento, validación y test
- [ ] Usar octubre–diciembre 2024 solo para construir primeros lags.
- [ ] Training: enero 2025–marzo 2026 (15 meses); validation: abril–junio 2026 (3); test: julio–septiembre 2026 (3).
- [ ] Mantener meses completos en cada conjunto; no hacer split aleatorio de filas.
- [ ] Aplicar evaluación mensual de un paso y documentar disponibilidad de lags en cada corte.
- [ ] Realizar comprobación adicional con TimeSeriesSplit sobre meses únicos del training; verificar folds y posible gap.
- [ ] No utilizar test para seleccionar features, parámetros o modelo.
§9 Normalización
- [ ] Documentar StandardScaler con fit solo en training y transformaciones en validation/test; reajustar por fold cuando aplique.
- [ ] Explicar por qué LinearRegression puede escalarse opcionalmente, Random Forest no lo requiere y MLP sí suele beneficiarse.
- [ ] Codificar categorías correctamente y revisar redundancia entre lags y promedio de tres meses.
§10 Baseline y LinearRegression
- [ ] Implementar baseline ingenuo de mes anterior.
- [ ] Entrenar LinearRegression, comparar mismas fechas/métricas y examinar salidas negativas.
- [ ] Conservar métricas de predicción original y documentar efecto de max(0, predicción) para presentación operativa.
§11 RandomForestRegressor
- [ ] Entrenar RandomForest y explorar n_estimators, max_depth, min_samples_leaf, max_features con validación temporal.
- [ ] Analizar sobreajuste, ceros, estabilidad y dificultad para extrapolar; no declarar ganador anticipadamente.
§12 Red neuronal para regresión
- [ ] Cobertura conceptual obligatoria del documento: explicar MLP de regresión, ReLU, salida lineal, arquitectura ilustrativa 64/32, escalado, riesgos de sobreajuste y parámetros de entrenamiento.
- [ ] Opcional si hay tiempo: entrenar MLPRegressor como tercer candidato sin usar partición aleatoria como sustituto de la validación temporal; registrar arquitectura, activación, solver, learning rate, batch size, seed, iteraciones y parada.
- [ ] Si no se implementa MLP, justificar que la propuesta la deja como comparación conceptual de menor prioridad.
§13 Comparación y selección
- [ ] Comparar baseline, LinearRegression y RandomForest (y MLP solo si se ejecuta) por MAE, RMSE, R², estabilidad, ceros y complejidad.
- [ ] Elegir usando validation; conservar modelo simple si el complejo no mejora de manera útil.
- [ ] Aclarar que buen resultado sintético no demuestra precisión comercial real.
§14 Métricas
- [ ] Calcular MAE como criterio principal, además de RMSE y R², con unidades y número de observaciones.
- [ ] Mostrar resultados globales y por tienda o rotación.
- [ ] Explicar por qué no usar accuracy ni MAPE como métrica principal con ceros; no llamar R² «porcentaje de precisión».
§15 Experimentos, prompts y configuraciones
- [ ] Crear ml/demand/reports/experiments.csv con columnas: experiment_id, timestamp, model, features, train_range, validation_range, test_range, parameters, seed, mae_val, rmse_val, r2_val, mae_test, rmse_test, r2_test, training_seconds, notes.
- [ ] Mantener métricas test vacías durante selección y completarlas solo en evaluación final congelada.
- [ ] Registrar versiones de Python, pandas, NumPy, scikit-learn; hash/versión de dataset, scaler, encoder, features, parámetros, tiempos y artefactos.
- [ ] Crear docs/PROMPTS_MODELO_PREDICTIVO_H4.md; registrar prompts reales de auditoría, generación, entrenamiento, correcciones, integración, pruebas y documentación.
- [ ] Marcar NO RECUPERADO cuando falte el prompt original; no inventarlo retroactivamente.
§16 Avance funcional H4
- [ ] Problema y auditoría explicados; dataset y análisis disponibles.
- [ ] Features, target, split temporal, baseline, LinearRegression y RandomForest funcionando.
- [ ] Comparación, escalado documentado, experimentos y modelo guardado.
- [ ] Predicción desde script o endpoint y primera visualización.
- [ ] Evidencia reproducible y prompts registrados.
§17 Demo H4 e integración H5
- [ ] Demo permite seleccionar producto y tienda; muestra meses recientes, mes objetivo, modelo, unidades previstas, MAE y origen sintético.
- [ ] Gráfico distingue historia simulada y pronóstico.
- [ ] Calcular max(0, ceil(demanda_prevista + stock_seguridad - stock_actual)) con Inventory.stock por producto/tienda; documentar política de seguridad.
- [ ] No equiparar Inventory.minStock automáticamente a stock de seguridad.
- [ ] No ejecutar compras, traslados, ajustes de stock ni reposición automática.
- [ ] Documentar que integración definitiva, ranking, permisos completos, monitoreo de error real, reentrenamiento y versionado extendido son posibles trabajos H5, no funciones prometidas como terminadas en H4.
§18 Riesgos y explicación para clase
- [ ] Explicar origen incierto, historia insuficiente, demanda no observada por falta de stock, leakage y aprendizaje de reglas sintéticas.
- [ ] Preparar defensa de supervised regression, split temporal, normalización solo en training, elección de modelo y limitaciones.
- [ ] Aclarar que el sistema todavía no demuestra precisión con ventas reales.
§19 Fuentes y trazabilidad
- [ ] Conservar referencias técnicas de scikit-learn (TimeSeriesSplit, StandardScaler, LinearRegression, RandomForestRegressor, MLPRegressor, métricas) y Goodfellow et al. (2016).
- [ ] Identificar como bases documentales la propuesta, auditoría y Ejercicio 1.pdf citado en la propuesta; no afirmar haber revisado ese PDF en este plan.
- [ ] Conservar decisiones que provienen de la segunda auditoría de precios y confirmar su vigencia con el código antes de implementar dependencias.
5. Contrato de integración preliminar (por aprobar)
Solicitud conceptual: productId, locationId, mesObjetivo (mes siguiente a la historia disponible).
Respuesta conceptual: productId, locationId, mesObjetivo, unidadesPrevistas, modelo, origenDatos: "SINTETICO", maeReferencia, versionModelo, versionDataset.
- [ ] Erika y Ross acuerdan ruta, método HTTP, tipos, códigos de error y contrato definitivo.
- [ ] Ross trabaja con mock marcado SIMULADO_API hasta conectar la inferencia real; nunca lo presenta como predicción entrenada.
- [ ] Erika entrega inferencia con el mismo contrato y pruebas unitarias.
- [ ] Validar producto y ubicación TIENDA; manejar historial insuficiente, modelos ausentes, errores de Python y respuestas no finitas.
- [ ] Documentar si el ejemplo pronostica el mes posterior al último mes sintético (octubre 2026) y no confundirlo con una predicción comercial real.
6. Evidencias y definición de «terminado»
Una tarea se marca [x] solo cuando exista evidencia, no porque se haya comenzado.
- [ ] README con instalación, versiones, ejecución de generación, entrenamiento, evaluación e inferencia.
- [ ] Snapshot/manifiesto del dataset, seed, parámetros, hash y reglas de exclusión de Git para archivos grandes/sensibles.
- [ ] Tests automáticos del generador, features, splits, leakage, predicción y contrato de API.
- [ ] Tabla comparativa de métricas con conteos, períodos y justificación de selección.
- [ ] Artefacto de modelo/preprocesamiento versionado o reproducible con instrucciones; comprobar que .gitignore no bloquee accidentalmente los archivos que deban entregarse.
- [ ] experiments.csv y registro fiel de prompts.
- [ ] Capturas o grabación de demo: filtros → historial → pronóstico → MAE → reposición ilustrativa.
- [ ] Documentación de límites, decisiones y separación H4/H5.
- [ ] Revisión cruzada de PR y confirmación de que no se escribió en Neon ni se automatizaron compras.
7. Riesgos y contingencias
Riesgo	Medida	Responsable
Saneamiento no concluido	No iniciar cambios dependientes de datos productivos; mantener trabajo documental hasta autorización	Ambos
Catálogo/tiendas inaccesibles	Solicitar lectura autorizada; no inventar IDs reales ni afirmar que el dataset ya existe	Erika
Sobreajuste a reglas sintéticas	Baseline, validación temporal, métricas por grupo y limitaciones explícitas	Erika
Fuga de información	Revisiones de features, pipelines y cortes temporales	Erika
Integración Python–Express falla	Contrato acordado día 2, mock y pruebas tempranas	Ross
Retrasos de cronograma	Priorizar baseline + dos modelos + script inferencia + vista mínima; MLP queda conceptual	Ambos
Riesgo de credenciales/archivos grandes	No exportar datos personales ni secretos; verificar .gitignore y archivos del PR	Ambos


8. Alternativa de 2 semanas (solo si es necesario)
- Días 1–3: dataset, features, splits y contrato (Erika); estructura UI y mocks (Ross).
- Días 4–6: baseline, LinearRegression y RandomForest (Erika); endpoint y vista inicial (Ross).
- Días 7–8: validación, congelar modelo, inferencia y conexión Express–React.
- Días 9–10: test final, pruebas, prompts, documentación y demo.
Recortes permitidos: interfaz avanzada, MLP implementada, rankings y mejoras H5. No recortar: separación temporal, ausencia de leakage, trazabilidad de datos sintéticos, baseline, métricas, inferencia y evidencia.
9. Estado general
- [ ] Semana 1 cerrada y revisada.
- [ ] Semana 2 cerrada y revisada.
- [ ] Semana 3 cerrada y revisada.
- [ ] Cobertura de las 19 secciones de la propuesta comprobada.
- [ ] Prototipo H4 ejecutado de extremo a extremo.
- [ ] Evidencias y presentación final revisadas por ambos.
Nota final: este checklist busca cubrir el 100 % de lo descrito en la propuesta H4, distinguiendo claramente explicación conceptual, implementación funcional, tareas opcionales y alcance futuro H5. No sustituye la verificación real de resultados ni convierte los datos sintéticos en ventas reales.