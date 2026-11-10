# H4 — Tarea 19: exportación completa y trazabilidad (R52)

## Resultado y estado del requisito

Parte técnica de Erika terminada y verificada: **442 pruebas aprobadas en
78.806 segundos: 420 anteriores y 22 nuevas**. Integridad de los 29 archivos
protegidos preservada, contrastada con T18 y el snapshot previo.

**R52 conserva PARCIAL**: cumplimiento técnico CUMPLIDO, demostración visual
PENDIENTE. La descarga está integrada y validada con AppTest, pero falta la
revisión visual real/aceptación de Ross. No se incrementa artificialmente el
porcentaje: siguen 52/68 cumplidos, 76,47 % estricto. R30 no se inicia.

## Auditoría y compatibilidad

Se contrastaron la guía oficial, matriz T18 e informe T18 con DemandSession,
PairContexts, LifecycleRegistry, runtime, reentrenamiento, comparación,
ObservationJournal y la interfaz.

Antes, DESCARGAR SESIÓN JSON emitía h4-session-1 con session_id del diario,
origin SIMULACION, generator_seed=null y records de cierres con sus forecasts.
No incluía seed real, RNG, pendientes, revisiones sustituidas, contextos de
modelos ni eventos R49. La descarga no aparecía hasta tener cierres.

Ahora se conserva exactamente ese contrato público y se añade
extensions.h4_traceability, schema_version=h4-traceability-1. generator_seed
legado sigue null para no cambiar su tipo; el valor real está en
extensions.h4_traceability.engine.generator_seed. No se renombran session_id,
records ni los campos/tipos de Forecast o ClosedObservation.

El [contrato de exportación](../../H4_EXPORTACION_SESION_R52.md) documenta los campos,
sus tipos, quién puede consumirlos, canonicalización, desconocidos y límites.
No se modifica create_runtime(), get_active_model() ni predict(features).

## Arquitectura implementada

- session_export.py construye un documento de solo datos, valida las fuentes
  vivas y calcula document_sha256. No invoca fit, predict ni joblib.load.
- DemandSession.export_state() captura todos los pares sin seleccionarlos,
  avanzar el reloj, generar valores o consumir RNG. Incluye seed, calendario,
  escenario, hipótesis, referencia inicial, cierres/procedencia, pendientes,
  draws internos separados y estado RNG completo con gauss_next.
- session_trace.py registra fechas/UUID reales para revisiones nuevas del motor
  y del diario. El diario conserva cada forecast emitido, incluso si después
  se sustituye o descarta antes de revelar un resultado.
- PairContexts entrega la vista actual de los alias de Ross sobre los snapshots
  guardados. No se exportan instancias de runtime ni verificadores ejecutables.
- DemandRuntime.export_references() verifica las referencias locales y entrega
  solo metadatos de ACTIVE y la pila anterior. Los métodos de exportación de
  reentrenamiento/comparación devuelven fuentes propias, nunca JSON importados.
- La interfaz usa el mismo botón/nombre de archivo y lo ofrece también sin
  cierres. Captura snapshots de evidencia antes del descarte de reset.

Los snapshots actuales incluyen todos los pares visitados, claramente
identificados, sin convertir sus referencias en un ACTIVE global.

## Campos y verificaciones

| Información | Fuente y comprobación |
|---|---|
| Identidades | UUID del motor, UUID del diario y propietario de PairContexts deben concordar |
| Producto/tienda/mes | Catálogo, claves y forecasts del mismo par; calendario simulado separado de fechas UTC reales |
| Contexto/rama | ID real de DemandSession y rama observada al exportar; valores no registrados permanecen null/UNKNOWN |
| Seed/RNG | Seed real y getstate por par, versión Python, estado MT19937 y caché gaussiana; ninguna llamada aleatoria durante exportación |
| Cierres | Motor y diario coinciden en observado, clave y existencia; no hay pendientes simultáneamente cerrados |
| Procedencia | MANUAL/GENERATED registrados por el motor; se cotejan contra revisiones cuando existen |
| Emisiones/revisiones | Datos originales conservados desde el comienzo del seguimiento, fechas y secuencias reales |
| Referencias | Identidad/huellas de ACTIVE y referencias previas verificadas antes de exportarlas |
| Candidatos | Registro propio de entrenamiento, manifiesto y hashes de cada archivo; solo lectura, sin deserialización |
| Decisiones | Fuentes propias de comparación/rechazo y cadena R49 verificada |
| Reset | Snapshot PRE_RESET_SNAPSHOT separado del motor nuevo SIN ACTIVE |

Las hipótesis manuales no se convierten en observados. La referencia histórica
inicial se etiqueta por separado y no se incorpora al entrenamiento incremental.
Las propuestas cacheadas del generador no se presentan como cierres; la demanda
latente se omite. Las revisiones anteriores que no se registraron no se inventan.

Si hay contradicción se rechaza la exportación verificable. Durante reset se
conservan fuentes no verificables en una sección UNVERIFIED, sin certificar sus
observados. Los eventos R49 antiguos sin snapshot siguen disponibles como
prior_lifecycle_only, con historia/RNG ausentes identificados como desconocidos.

## Seguridad

La exportación es evidencia y datos, nunca una autoridad. Ningún archivo se
convierte en proveedor o candidato registrado. El validador de evidencia solo
comprueba integridad lógica; incluso recomputar la huella de un JSON editado
no permite activar o promover modelos. Las pruebas intentan esa ruta y el
runtime la rechaza. Se conserva el bloqueo de promoción real de candidatos.

La cadena y las huellas no se presentan como firma externa. Los snapshots
previos a reset describen el estado anterior al descarte, no referencias
restauradas. El JSON no contiene estimadores, pickle ni callbacks.

## Ejemplo real y reproducible de exportación

Desde la raíz en PowerShell:

```powershell
& .\ml\demand\.venv\Scripts\python.exe -B ml/demand/example_session_export.py `
  --output docs/H4/tareas_erika/tarea_19/evidence/example
```

El comando crea una carpeta nueva por ejecución, usa V1 congelada mediante
acciones explícitas locales y **no entrena ningún modelo**. Genera tres
documentos: current.json, rollback.json y after_reset.json.

Ejecución conservada:

- Carpeta: example-e77c656488a945e18f746f5d017b50a5.
- Motor: 156a9e39894041f9a28c602bf57ad52e.
- Diario público: 96801118b50f4168908ab13ef2e16306.
- Motor posterior al reset: 4e5303c6a8d44fcd900e17f749adb2f9.
- Seed real 42, dos pares: 1/5 con observado manual y 2/6 con generado STOCKOUT.
- Dos cierres exclusivamente simulados, hipótesis separadas y V1 real solo en 1/5.
- Rollback conserva los cierres; después de reset, records actual está vacío,
  las fuentes anteriores quedan archivadas y el runtime nuevo no tiene ACTIVE.

Se verificaron las huellas lógicas y binarias de los tres archivos en
validation.json. Los datos son demostrativos, no ventas reales ni una nueva
evaluación TEST. El ejemplo no crea un candidato; la exportación de candidatos
y decisiones se prueba con un candidato temporal aislado de seis filas.

## Pruebas

Resultado final: **442/442 OK, 78.806 s**. Los 22 casos nuevos cubren:

- Envelope público y records sin cambios de tipos; seed real en la extensión.
- RNG con caché gaussiana y reproducción del siguiente mes desde el snapshot.
- Exportación sin consumir azar, modificar selección o alterar el futuro simulado.
- Pares y sesiones independientes; fuentes MANUAL/GENERATED, cero conocido y pendientes.
- Exclusión de latente y separación de hipótesis frente a cierres reales de la simulación.
- Emisiones sustituidas/descartadas y revisiones/confirmaciones de la UI.
- Rechazo de cierres, procedencia o forecasts alterados frente a sus revisiones.
- Historial anterior no registrado explícitamente desconocido, incluidos eventos R49 sin snapshot.
- Referencias anteriores, manifiestos de candidato y decisiones verificables.
- Exportación sin fit ni joblib.load; rechazo de fuentes alteradas.
- Hash del documento, copias y ausencia de activación desde JSON incluso editado/rehasheado.
- Descarga disponible sin cierres, después de reset, y cuarentena de fuentes inconsistentes.

La primera ejecución de los casos nuevos detectó una selección incorrecta en
el helper de prueba: intentaba registrar abstención cuando PREDECIR estaba
habilitado con ACTIVE. Se corrigió el helper para ejercer la acción permitida.
No se modificaron ni debilitaron pruebas anteriores. La pasada intermedia de
440 pruebas también aprobó; se añadieron dos casos y se repitió la suite final.

run_tests.py aísla todos los registros de las sesiones AppTest en una carpeta
temporal. Los entrenamientos de pruebas siguen aislados y no escriben
experimentos oficiales. Se requirieron los sockets locales de AppTest fuera
del sandbox. No se hizo revisión visual ni se produjeron capturas.

## Archivos e integridad

Modificados en T19:

- demand_engine.py: snapshot/revisiones, sin cambios en fórmulas o consumo de RNG.
- ui_runtime.py: historial de emisiones y revisiones sin cambiar dataclasses públicas.
- pair_contexts.py: vista no mutante para exportación.
- demand_runtime.py: metadatos verificables de referencias.
- retraining.py y model_comparison.py: copias/fuentes de confianza para exportar.
- streamlit_app.py y ui_panels.py: seguimiento del editor, descarga y archivo previo al reset.

Nuevos: session_trace.py, session_export.py, test_session_export.py,
example_session_export.py, este informe, contrato de exportación, matriz T19
Markdown/CSV y evidence/.

Los 29 archivos protegidos coinciden antes/después y con T18. Se verificaron
independientemente los SHA256 binario y normalizado de V1 y el manifiesto;
dataset, catálogo, generadores históricos, artefactos, manifests, TEST y
experimentos oficiales permanecen intactos. No hubo commits, push o cambios
productivos. git diff --check aprobó.

## Pendientes de Ross y aceptación de R52

La parte técnica está lista para consumir. Ross debe revisar en navegador real
la descarga desde una sesión sin cierres, con pendientes, varios pares y tras
reset; abrir los archivos y comprobar correspondencia con lo mostrado.
Debe aceptar el consumo de la extensión versionada, mostrar la procedencia
sin confundir draws/hipótesis con observados y distinguir snapshot previo de
ACTIVE actual. Las claves RNG y referencias internas no conceden permisos.

Hasta esa aceptación visual, R52 permanece PARCIAL y el porcentaje global no
cambia. R30 continúa PARCIAL; no se integra LinearRegression en esta tarea.

## Evidencias

- [Contrato versionado](../../H4_EXPORTACION_SESION_R52.md).
- [Pruebas completas finales](evidence/full_tests.txt).
- [Resumen verificable](evidence/validation.json).
- [Ejemplo reproducible](evidence/example_log.json).
- [Export actual](evidence/example/example-e77c656488a945e18f746f5d017b50a5/current.json).
- [Export tras rollback](evidence/example/example-e77c656488a945e18f746f5d017b50a5/rollback.json).
- [Export tras reset](evidence/example/example-e77c656488a945e18f746f5d017b50a5/after_reset.json).
- [Integridad previa](evidence/integrity_before.json) y [posterior](evidence/integrity_after.json).
- [Matriz T19](H4_MATRIZ_CUMPLIMIENTO_T19.md) y su CSV.
- [Git status](evidence/git_status.txt) y [diff stat](evidence/git_diff_stat.txt), acumulados.

Se detiene la tarea sin iniciar R30.
