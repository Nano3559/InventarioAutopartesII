# RepuestoPro H4 — Informe final de auditoría y preparación del cierre de Erika

> Fotografía histórica de T14. La [corrección acotada T15](tareas_erika/tarea_15/H4_TAREA_15_CORRECCIONES_FUNCIONALES.md)
> subsana D01/D02/D03; consultar la [matriz T15](tareas_erika/tarea_15/H4_MATRIZ_CUMPLIMIENTO_T15.md).
> Los resultados y porcentajes originales siguientes se conservan como evidencia de aquella auditoría.

Tarea 14. Fecha: 9 de noviembre de 2026, America/La_Paz. Rama: erika.
**Conclusión: H4 no puede declararse al 100 %.** La implementación técnica
principal funciona en AppTest y conserva sus artefactos, pero hay dos defectos
reproducidos, diferencias de alcance frente a la guía y revisión visual pendiente.
Este informe no autoriza ni ejecuta correcciones adicionales.

## 1. Alcance y método

Se leyó la guía oficial completa y se revisaron informes T10–13, código,
manifiestos, registros, pruebas y evidencias. La guía contiene un estado fechado
al 4 de noviembre; sus expresiones de funcionalidades pendientes no se toman
como prueba del estado actual. Se contrastaron con los archivos existentes.
Se conservaron sus secciones históricas y checkboxes sin marcar aceptación
conjunta unilateralmente.

Se ejecutaron las 375 pruebas, un nuevo arnés integral con el modelo real,
diagnósticos de discrepancias y hashes antes/después. No se añadieron tests a
unittest discovery: faltaba evidencia del recorrido largo unificado, que ahora
aporta validate_h4_integral.py. No se corrigieron defectos ni se debilitaron tests.

La automatización del navegador se detuvo por una comprobación de seguridad
de Computer Use: no pudo determinar la URL actual de Windows con confianza
suficiente. No se intentó un método alternativo de control del navegador.
No se obtuvieron capturas. Esto no impidió las comprobaciones CLI/AppTest.

## 2. Objetivo y arquitectura implementada

Se estima la venta bruta observada del siguiente mes por producto y tienda.
Es regresión temporal supervisada de un paso, no estimación de demanda perdida
ni recomendación comercial de reposición.

| Componente | Implementación | Función |
|---|---|---|
| Referencia y entradas | simulator_inputs.py, ml_pipeline.py | Hashes, catálogo, tipos, features y split |
| Simulación | demand_engine.py / DemandSession | Escenarios, reloj, observados y lags por par |
| Emisiones | ui_runtime.py / ObservationJournal | Predicción antes del observado, bloqueo y cierre |
| Inferencia | demand_runtime.py | Carga verificada, ACTIVE por sesión, abstenciones y rollback |
| Interfaz/análisis | streamlit_app.py, ui_panels.py, ui_analysis.py | Controles, gráficos, métricas y monitoreo |
| Ensayo incremental | retraining.py | Cierres nuevos verificados, snapshot y candidato separado |
| Comparación/decisión | model_comparison.py | Reserva común, métricas, insuficiencia y rechazo |

El runtime mantiene los contratos de Ross create_runtime(), get_active_model()
y predict(features). No hay ACTIVE global persistido. La aplicación inicia
sin ACTIVE y reset/reconexión descartan su referencia local. Las predicciones
cerradas conservan versión y huella. La política real de promoción de nuevos
candidatos está bloqueada incondicionalmente; la ruta positiva solo está en
fixtures de pruebas, nunca en JSON importados o configuración normal.

## 3. Dataset y separación temporal

Dataset sintético 1.1.0-escenarios: 56 productos, tiendas 5/6/7, 24 meses de
octubre de 2024 a septiembre de 2026, seed 42. Conserva 4.032 filas mensuales y
3.528 filas supervisadas. Hay 504 filas iniciales de historia fuera de los
targets de entrenamiento/validación/test.

| Partición original | Periodo objetivo | Filas |
|---|---|---:|
| TRAIN | Enero 2025–marzo 2026 | 2.520 |
| VALIDATION | Abril–junio 2026 | 504 |
| TEST final V1 | Julio–septiembre 2026 | 504 |

Las cinco features son ventas_mes_anterior, ventas_hace_2_meses,
ventas_hace_3_meses, mes_sin, mes_cos, en ese orden. Los IDs son metadatos; el
target es target_ventas_mes. No se incluyen latentes, stock actual, precios o
escenarios internos. El calendario es conocido antes del mes objetivo.
Los lags se forman con meses anteriores exactos del mismo par.

El ensayo incremental aprobado utiliza solo doce cierres nuevos posteriores a
septiembre de 2026: octubre–diciembre como historia, enero–junio de 2027 para
seis targets de ajuste y julio–septiembre reservados para comparación. No usa
TRAIN/VALIDATION/TEST originales como filas ni valores del TEST original como
lags de ese ajuste. Para la comparación mensual de un paso sí se permite que
un observado de julio ya cerrado sea un lag de agosto; no es un pronóstico de
tres pasos emitido todo desde junio.

## 4. Modelos entrenados y selección

Se conservan baseline lag1, LinearRegression con preprocesamiento guardado y
RandomForestRegressor. RandomForest realizó una búsqueda interna limitada de
16 configuraciones dentro de TRAIN, con corte temporal interno documentado.
No se ejecutó un entrenamiento oficial durante esta auditoría.

Métricas VALIDATION leídas del manifiesto congelado:

| Modelo | MAE | RMSE | R² |
|---|---:|---:|---:|
| Baseline lag1 | 6.158730158730159 | 10.972729544228894 | −0.10419248473065923 |
| LinearRegression | 5.473184442331192 | 8.792626425594534 | 0.2909894778615837 |
| RandomForest V1 | 5.158657249544053 | 8.441614483508094 | 0.3464685883046653 |

Selección SEL-V1-RANDOMFOREST-20261109T041158351931Z. Configuración V1:
n_estimators=200, max_depth=8, min_samples_leaf=3, max_features=sqrt,
random_state=42, n_jobs=1; sin scaler. La selección se congeló con validation
antes de la evaluación TEST. No se reajustó con TRAIN+VALIDATION.

TEST final ya registrado una vez: **MAE 4.814178503040102,
RMSE 8.182890558417325, R² 0.42304686389766555**, sobre 504 filas y cobertura
100 %. Se leyó el reporte existente: no se recalculó, calibró ni utilizó para
modificar parámetros o escoger otro candidato.

## 5. Runtime e identidad

V1 SHA256 binario:
fb0d8d81ba2558101a232ff616bff14fe0b95d6a13dfa24d60a8dce4b4e81d3e.
Huella normalizada conservada en documentos congelados:
3e3cf6d1ef75567a69ff6f604bcb2a93f629f6d0fa503bdf734f3c6118c03883.

Se exigen ambas antes de deserializar los mismos bytes leídos. La referencia
binaria está fijada en código tras auditoría; no es una firma externa del autor.
Se verifican esquema, estimador, features, parámetros, scaler, corte y entorno
compatible. Inferencia y generación nunca aprenden del observado futuro.
No finitos o errores técnicos producen rechazo/abstención; negativos finitos
se conservan sin recortar para medir el error original.

## 6. Resultado del recorrido integral de Tarea 14

El arnés nuevo ejecutó el Streamlit real mediante AppTest, no un doble de V1:

1. Inicio inactivo, cambio de producto/tienda y selección NORMAL.
2. Edición inicial lag3=8, lag2=10, lag1=12 y validación del orden/calendario.
3. Promoción V1 explícita dentro de esa sesión de validación.
4. Doce emisiones entre octubre de 2026 y septiembre de 2027, con generación,
   cierre explícito alternado con cierre al avanzar, lags y reloj coherentes.
5. ENSAYAR REENTRENAMIENTO por botón: una única llamada a fit, sobre seis filas
   nuevas de una serie; jamás sobre el estimador V1.
6. Creación de candidato temporal independiente, comparación de las tres filas
   reservadas, INSUFFICIENT_EVIDENCE y REJECTED_FOR_PROMOTION.
7. Rollback a SIN ACTIVE, cierres previos iguales, reset y otra sesión aislada.

Además se recorrieron seis meses en cada uno de los ocho escenarios:
NORMAL, CRECIMIENTO, CAÍDA, PICO MAYORISTA, STOCKOUT, PRODUCTO NUEVO,
CAMBIO PERSISTENTE y RECUPERACIÓN. Total: **60 meses de recorridos registrados**.
Cada PREDECIR habilitado debió producir una predicción numérica con la huella
de V1; PRODUCTO NUEVO emitió abstenciones seguras. No se añadió una promesa de
cobertura por el mero transcurso de meses o edición de casillas.

Primera predicción del arnés para producto 1/tienda 5/octubre 2026:
**10.025387319264723 unidades**, con features [12,10,8,−1,−0] y observado
generado 12. Son valores simulados, no ventas comerciales.

El candidato temporal de esta auditoría se ajustó con targets
[13,13,11,11,11,11]. En la reserva nueva [11,11,13], V1 obtuvo MAE
1.2946298679336252 y el candidato temporal 0.8916666666666669. **No se
declaró superioridad ni se promovió:** tres casos siguen siendo insuficientes.
Este paquete temporal es distinto del candidato archivado de Tarea 12.
Se eliminó al cerrar el directorio temporal; el snapshot, hashes, métricas y
decisiones están preservados en integral.json. No se afirma que su ruta
temporal continúe disponible.

## 7. Candidato archivado y decisiones preservadas

CAND-f3690f19436644959f2218cdc079110c conserva seis filas de ajuste, una serie
y tres filas de reserva. Su comparación formal de T13 permanece intacta:

| Modelo | N | Cobertura | MAE | RMSE |
|---|---:|---:|---:|---:|
| V1 | 3 | 100 % | 0.9279069888581345 | 1.1202195739427763 |
| Candidato archivado | 3 | 100 % | 4.454166666666662 | 4.528384630429605 |

Decisión INSUFFICIENT_EVIDENCE y rechazo para promoción. No se infiere
superioridad estadística de tres observaciones. El artefacto sigue internamente
CANDIDATE; las decisiones de rechazo son registros separados. Los fixtures
positivos y su rollback siguen cubiertos por la suite completa y la evidencia
de T13; no se habilita esa política en Streamlit.

## 8. Defectos reproducidos y alcance: sin correcciones

### D01 — Azar compartido entre pares de una sesión

La guía §13 pide azar independiente por sesión y por producto/tienda. El motor
tiene un único self._rng por sesión. La misma serie 1/5 produce
[22,22,22,23,23,21] sola y [22,23,21,21,21,23] al intercalar generación de
2/5. Cambiar de par consume la secuencia del otro. No mezcla directamente
observados entre diccionarios ni afecta las sesiones distintas; sí incumple
la independencia por par y dificulta reproducir una trayectoria al intercalar.
Evidencia: diagnostics.per_pair_rng. Corrección pendiente de autorización.

### D02 — Cierre manual sin confirmación de mes completo

Tras una abstención, ingresar observado manual 10 y dejar desmarcada la casilla
de mes cerrado/completo. AVANZAR MES cierra octubre y avanza de todas formas.
REGISTRAR OBSERVADO sí exige la casilla. Causa: can_advance depende del
observado pendiente/cierre, y close_month no recibe un estado de completitud.
Esto contradice la exigencia de no cerrar un mes incompleto y permite eludir
la confirmación por una segunda ruta. No demuestra que el dato externo sea
incompleto, sino que falta su comprobación uniforme. Evidencia:
diagnostics.manual_close. No se modificó la lógica de cierre.

### D03 — Inferencia real inaccesible desde el arranque normal del navegador

create_runtime devuelve SIN ACTIVE; reconectar también. No hay botón que
promueva V1 en la misma sesión del navegador. PREDECIR queda deshabilitado al
abrir normalmente, aunque el modelo y el código existen. Los arneses inyectan
la instancia explícita en AppTest y comprueban la inferencia real, pero no
constituyen una ruta humana completa. Activar en otra consola no comparte
st.session_state. Se requiere una decisión/autorización de integración para
una demo interactiva completa; no se añadió una activación automática.

### Diferencias de alcance y documentación

- ACTIVE y el último resultado del candidato son de sesión, no referencias
  independientes por cada par como menciona la guía. Los cierres y datos sí
  identifican sus pares. No se atribuye aislamiento de versiones por par.
- Reset devuelve SIN ACTIVE, por autorizaciones posteriores T10–13; la guía
  original habla de restaurar V1. Es una adaptación aprobada, pendiente de
  reconciliación documental, no permiso para activarla automáticamente.
- DESCARGAR SESIÓN JSON conserva generator_seed=null y no serializa estado RNG,
  rama o procedencia manual/generada por cierre. El snapshot incremental sí
  contiene seed y procedencia, pero no reemplaza una exportación completa.
- La promoción positiva real está deliberadamente bloqueada por autorización.
  No debe corregirse como si fuera una falla del botón.
- Registro de versiones y estados parcial: hay paquetes/decisiones nuevos y
  eventos en memoria, pero no un registro completo ACTIVE/ARCHIVED por par.
- El escenario está en las emisiones, pero el panel de errores no ofrece el
  desglose por escenario solicitado en §9; agrupa tienda/producto/rotación/mes.
- El log de prompts principal llega al 4 de noviembre y la guía oficial conserva
  checkboxes antiguos. Se aporta trazabilidad de este cierre sin inventar
  prompts T1–9 o una revisión conjunta ya realizada.

## 9. Pruebas automáticas y revisión visual

**375 pruebas aprobadas en 51.134 segundos.** Todas las 375 anteriores
continúan pasando; no se eliminaron, cambiaron ni añadieron tests a discovery.
Los diagnósticos nuevos muestran por qué ese resultado no prueba cumplimiento
total de la guía. Los futuros arreglos necesitan regresiones específicas.

En el arnés adicional fit solo estuvo permitido al pulsar el ensayo incremental.
Los contadores registran un ajuste de candidato con seis filas y cero intentos
de fit durante inferencia. La aplicación produjo valores reales en todas las
emisiones habilitadas con fit prohibido fuera del ensayo.

Se inició Streamlit en 127.0.0.1:8502 y se comprobó /_stcore/health: HTTP 200,
respuesta ok. Esto prueba arranque del servidor, no corrección visual de páginas.
Se detuvo el servidor de auditoría al finalizar.

**Revisión visual: PENDIENTE. Cero capturas.** La herramienta detuvo Computer
Use por URL no verificable. No se revisaron visualmente escritorio ni pantalla
estrecha, selectores, gráficos, tablas, estados, comparación o rollback.
No se sustituyeron capturas reales por imágenes generadas o salidas de AppTest.

## 10. Revisión de cobertura objetivo 95 %

**No existe evidencia suficiente para declarar intervalos de predicción con
cobertura del 95 %.** El runtime entrega predicción puntual y reason, sin un
calibrador o intervalo. No hay una partición temporal independiente reservada
para calibración y otra posterior para comprobar cobertura. VALIDATION se usó
para selección; TEST ya fue usado una sola vez y está excluido de calibración.
Las tres filas incrementales se usaron para comparación, no acreditan cobertura
de intervalos. Los p95 del dataset son percentiles de cantidades, no intervalos
de error predictivo.

No se calculó una banda MAE×constante ni se convirtió R² en confianza. Esta
capacidad queda como mejora futura: aprobar un protocolo temporal, recolectar
datos nuevos, separar ajuste/calibración/evaluación y medir cobertura y amplitud
por periodo/grupo con soporte suficiente. No se fija un umbral estadístico
arbitrario ni se altera V1. Se registra como NO APLICA al alcance obligatorio
actual, no como capacidad implementada.

## 11. Matriz de cumplimiento y porcentajes

La [matriz exhaustiva](tareas_erika/tarea_14/H4_MATRIZ_CUMPLIMIENTO.md) normaliza **73 requisitos** y
vincula **125 ítems literales** de la guía: 33 celdas de tareas/responsables del
cronograma, 26 criterios de cierre, 18 evidencias de diseño, 32 evidencias
funcionales y 16 grupos de prueba. Repeticiones se remiten a los mismos IDs;
no se inflan puntos contando dos veces una misma obligación.

| Estado | Cantidad |
|---|---:|
| CUMPLIDO | 47 |
| PARCIAL | 18 |
| PENDIENTE | 3 |
| NO APLICA | 5 |
| Total | 73 |

Los cinco NO APLICA son MLP opcional, baseline estacional opcional, H5,
intervalos futuros y la comprobación adicional propuesta TimeSeriesSplit de
tres cortes. El split interno realmente utilizado por V1 está registrado.

**Porcentaje estricto: 47 / (73−5) × 100 = 69.12 %.** PARCIAL y PENDIENTE no
suman puntos. Como referencia separada, asignar medio punto a PARCIAL daría
82.35 %. Este último no equivale a aceptación. Ambos dependen de esta
normalización explícita y no son una nota académica, una medición de esfuerzo
ni la certificación del «70 % funcional» descrito por el docente.

Responsabilidad exclusiva de Erika: 25 cumplidos, dos parciales y cuatro
NO APLICA; 25/27 aplicables = 92.59 %. Los dos parciales son independencia del
azar por par y registro completo de versiones. Además hay obligaciones
compartidas abiertas: este porcentaje exclusivo no autoriza cerrar unilateralmente
su participación ni transfiere todos los pendientes a Ross.

La matriz conserva estado técnico y demostración visual separados. Cada fila
incluye responsable, fuente original, implementación, pruebas y observaciones.
Los dos pendientes visuales y la defensa conjunta sin evidencia son los tres
PENDIENTE; los alcances parcialmente implementados se detallan por ID.

## 12. Integridad y seguridad

Se capturaron SHA256 binarios antes/después de **29 archivos existentes**:
dataset 1.1 y versión anterior, catálogo, ambos generadores, modelos LR/V1,
manifiestos, evaluación TEST, experiments.csv, los cinco archivos del candidato
archivado y las decisiones originales. Ninguno cambió. Además se contrastaron
los 12 archivos congelados con la evidencia histórica T10, el manifiesto del
candidato con su referencia fija T13 y los hashes normalizados del dataset,
catálogo y generador con el manifiesto oficial.

No se leyó ningún secreto ni se accedió a Neon. No se modificaron backend,
frontend productivo, mobile, Prisma, datos o artefactos oficiales. No se promovió
el candidato real, no se reentrenó V1 ni se reevaluó TEST. No hubo commits/push.
git diff --check pasó. Las ejecuciones temporales de pruebas no añadieron
experimentos oficiales ni persistieron candidatos nuevos de esta auditoría.

## 13. Inventario de esta tarea y evidencia

Se crearon únicamente:

- ml/demand/validate_h4_integral.py: arnés y diagnósticos de auditoría.
- Este informe, H4_MATRIZ_CUMPLIMIENTO.md/.csv y H4_GUIA_EJECUCION_WINDOWS.md.
- tareas_erika/tarea_14/evidence/: snapshot de integridad, resultados, logs, matriz JSON,
  generador reproducible de matriz y registro del bloqueo visual.

No se modificó ningún archivo existente en T14. El estado acumulado del repo
continúa con cambios previos: cuatro archivos versionados, 317 inserciones y
36 eliminaciones, además de los nuevos sin seguimiento. El diff stat no incluye
los módulos sin seguimiento de tareas anteriores ni los archivos nuevos T14.

- [Recorrido integral y diagnósticos](tareas_erika/tarea_14/evidence/integral.json)
- [Log integral](tareas_erika/tarea_14/evidence/integral_log.txt)
- [375 pruebas](tareas_erika/tarea_14/evidence/full_tests.txt)
- [Integridad final](tareas_erika/tarea_14/evidence/integrity_after.json)
- [Arranque HTTP](tareas_erika/tarea_14/evidence/server_health.json)
- [Limitación visual](tareas_erika/tarea_14/evidence/visual_review.json)
- [Git status](tareas_erika/tarea_14/evidence/git_status.txt)
- [Git diff stat](tareas_erika/tarea_14/evidence/git_diff_stat.txt)
- [Guía Windows y guion](H4_GUIA_EJECUCION_WINDOWS.md)

## 14. Pendientes que impiden el 100 % y autorización requerida

1. Autorizar correcciones de D01 y D02, acordar su comportamiento y añadir
   regresiones específicas antes de corregir. Esta auditoría no las implementa.
2. Definir y autorizar una vía explícita para disponer de V1 en una sesión humana
   de Streamlit (D03), manteniendo el bloqueo de nuevos candidatos y el alcance
   por sesión. No introducir una activación automática de forma implícita.
3. Reconciliar con la guía los alcances por par, reset y registro/exportación;
   completar lo que el equipo mantenga como requisito, con aprobación previa.
4. Realizar revisión visual real en escritorio y pantalla estrecha, con capturas
   y recorrido que incluya estados ACTIVE/CANDIDATE, comparación y rollback.
5. Completar/revisar conjuntamente tracking, log de prompts, checklist, guion
   y participación de ambos en ensayo/defensa. No inventar lo no recuperado.
6. Si se quisiera promoción real futura, aprobar antes un protocolo y obtener
   evidencia nueva suficiente. El bloqueo actual es deliberado; no se debe
   sortear para declarar un 100 %. Los intervalos 95 % siguen como mejora futura.

La responsabilidad técnica principal de Erika está avanzada y documentada;
su cierre definitivo y el de H4 quedan pendientes de estos acuerdos/evidencias.
Se detiene el trabajo para solicitar autorización antes de cualquier corrección.

## Anexo de procedencia documental del cierre

Resumen de las solicitudes disponibles en este chat, sin presentarlo como
transcripción literal: T10 implementó runtime y fixtures manteniendo V1 inactiva;
T11 autorizó promoción temporal de V1 y su validación/rollback; T12 aprobó uso
exclusivo de doce meses nuevos en reparto 3+6+3 y discrepancias hipotéticas como
trazabilidad; T13 aprobó comparación y rechazo reales con promoción positiva
solo de fixtures; T14 solicita esta auditoría integral, matriz, revisión visual,
integridad y documentación, sin correcciones importantes no autorizadas.
Los prompts originales de T1–9 no están recuperados en este cierre. No se
inventan fechas o resultados de esas solicitudes ni se sobrescribe el log previo.
