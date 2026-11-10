# H4 — Tarea 17: contextos independientes por producto y tienda

## Resultado y alcance

R21 pasa de PARCIAL a CUMPLIDO con evidencia automatizada. Suite completa:
**404 pruebas aprobadas, 61.861 segundos: 394 anteriores y 10 nuevas**.
Los 29 archivos protegidos coinciden antes/después y con la referencia
independiente T15. No se acredita revisión visual ni se implementan R49/R52.

La matriz T17 conserva los 73 IDs y 68 aplicables: 51 cumplidos, 14 parciales,
3 pendientes y 5 no aplica. Porcentaje estricto: 51/68 = 75 %. Solo cambia R21.
Las matrices T14/T15 y los informes anteriores permanecen como fotografías
históricas. La promoción real de nuevos candidatos continúa bloqueada.

## Auditoría y causa

DemandSession ya separaba reloj, historia, cierres y azar mediante sus PairState.
ObservationJournal identifica emisiones/observados por producto, tienda y mes.
DemandRuntime es una instancia mutable con ACTIVE, pila de rollback y eventos.
RetrainingSession conserva el registro de confianza de sus candidatos.

La interfaz mantenía un solo h4_runtime, retraining_result y estado de decisión
para toda la sesión. Cambiar los selectores no cambiaba esas referencias.
No era necesario modificar el motor, los estimadores ni el contrato de Ross.

## Diseño implementado

pair_contexts.py contiene el enlace de contextos en memoria de st.session_state:

- pair_context_owner identifica la DemandSession propietaria.
- selected_pair_context identifica el par seleccionado (product_id, location_id).
- pair_contexts conserva las claves de los pares al abandonarlos.
- Las claves históricas de Ross son la vista de trabajo del par actual.

Después de DemandSession.select(), antes de renderizar los paneles, se guarda
la vista del par anterior, se retiran sus claves y se recupera la del nuevo.
No se copian ni reconstruyen proveedores: al regresar se conserva la misma
instancia, su ACTIVE verificado y su pila de rollback. Un par nuevo no recibe
runtime ni candidato del anterior y crea su proveedor inicialmente inactivo.
La vista del par actual es la autoridad durante el rerun; su snapshot se guarda
al cambiar de par. El mapa no es un registro persistente ni una exportación.

Se incluyen runtime/errores/motivos de activación, servicio y resultado de
reentrenamiento, servicio y resultados de comparación, rechazo, motivos y
mensajes de rollback, y reportes/hash de carga. Cada uploader tiene clave por
par para evitar que el archivo visible del par anterior se procese en otro.

Las sesiones de Streamlit no comparten este mapa. Si cambia la identidad del
motor, se descartan referencias del propietario anterior. Se conserva el uso
de proveedores locales inyectados inicialmente por los arneses existentes.
La aplicación no importa mapas, runtimes ni autorizaciones desde JSON.

La comparación comprueba que el candidato nuevo pertenece al par seleccionado.
El ejemplo archivado T12 se ofrece como referencia histórica exclusivamente
para su par original 1/5; no se asigna como candidato nuevo de la sesión.
En otros pares sin candidato no se habilita esa comparación.

## Reset, reconexión y contratos

Reset elimina todos los contextos, motivos y cargas, y conserva el comportamiento
aprobado de restauración inicial del simulador: V1 disponible, SIN ACTIVE.
Reconectar reemplaza únicamente el proveedor del par actual. No reactiva V1,
no elimina el candidato local ni afecta las referencias de otros pares.
Rollback opera sobre la pila del proveedor del par actual.

create_runtime(), get_active_model() y predict(features) no cambian. Tampoco
cambian las respuestas de Ross, las cinco features, el contrato del diario,
los artefactos ni la política de promoción. Para Ross, las claves existentes
siguen disponibles pero ahora describen exclusivamente el par seleccionado.
Cualquier panel nuevo debe enlazar el par antes de leerlas; no debe mantener
un alias de runtime externo que sobreviva a cambios de selección o reset.

El historial se conserva al cambiar de par, activar, reconectar o revertir.
Reset sigue siendo la acción explícita de reiniciar la simulación; elimina
su diario en memoria conforme al comportamiento previo, sin borrar artefactos
ni paquetes de candidatos que existan en disco.

## Pruebas y evidencia

test_pair_contexts.py añade diez pruebas:

1. Restauración de identidad, candidato y decisiones al cambiar de par.
2. Rechazo de herencia al cambiar el propietario de la sesión.
3. Una referencia retirada por reconexión no reaparece desde un snapshot viejo.
4. Limpieza de contextos sin tocar directamente el diario.
5. Activación V1 real en 1/5, pares 2/5 y 1/6 inicialmente inactivos, retorno
   a 1/5 con el mismo proveedor y emisión, sin fit ni emisión por seleccionar.
6. Rollback independiente en 2/5, conservando ACTIVE, eventos y cierres de 1/5.
7. Reset de todos los pares y nueva acción explícita de activación requerida.
8. Reconexión local al par, con recuperación intacta del otro proveedor.
9. Sesiones separadas y rechazo de promoción incluso ante JSON APROBADO/PROMOVER.
10. ENSAYAR REENTRENAMIENTO desde AppTest: seis filas nuevas, candidato temporal,
    comparación, INSUFFICIENT_EVIDENCE y rechazo; otro par no hereda candidato,
    servicio, reporte o rechazo; al regresar se recuperan. Reset los descarta.

El candidato y las decisiones de esta última prueba se crean en directorios
temporales y se eliminan al terminar. No se promueven. Las pruebas anteriores
conservan cobertura de los ocho escenarios y de las protecciones ya existentes.

Durante el diagnóstico, el sandbox bloqueaba socketpair al iniciar el bucle de
eventos de AppTest. La suite se ejecutó con permiso para sockets locales.
La pasada preliminar detectó una suposición incorrecta en una prueba nueva:
antes de revelar el observado, PREDECIR permite reemplazar una emisión pendiente.
Se corrigió esa prueba para medir la conservación al cambiar de par; no se
alteraron pruebas anteriores ni se cambió esa política de emisiones.
El log preliminar se conserva identificado como tal; el resultado final es
full_tests.txt, 404/404 OK. Los avisos de contexto de Streamlit no son fallos.

- [Suite completa final](evidence/full_tests.txt).
- [Resumen verificable](evidence/validation.json).
- [Integridad previa](evidence/integrity_before.json).
- [Integridad posterior](evidence/integrity_after.json).
- [Matriz T17](H4_MATRIZ_CUMPLIMIENTO_T17.md) y su CSV.
- [Git status acumulado](evidence/git_status.txt).
- [Git diff stat acumulado](evidence/git_diff_stat.txt).

No hubo revisión de navegador ni capturas en esta tarea. AppTest acredita
comportamiento técnico, no la aceptación visual de R11/R12/R34/R56/R57.

## Integridad y restricciones

Se compararon 29 SHA256 con T15: datasets, catálogo, generadores, modelos LR/V1,
experiments.csv, manifiestos, reporte TEST, candidato archivado y decisiones.
También se verificó la referencia del dataset mediante su lector validado y
las dos huellas de V1 contra constantes independientes del archivo cargado:

- Binaria: fb0d8d81ba2558101a232ff616bff14fe0b95d6a13dfa24d60a8dce4b4e81d3e.
- Normalizada: 3e3cf6d1ef75567a69ff6f604bcb2a93f629f6d0fa503bdf734f3c6118c03883.

No se reentrenó V1 ni se reevaluó TEST oficial. No se modificaron dataset 1.1,
generadores históricos, artefactos/reportes congelados o contratos públicos.
No se promovió el candidato real ni se accedió a sistemas productivos.
No se ejecutaron commits, push ni operaciones de preparación de Git.

## Archivos e impacto sobre requisitos siguientes

Modificados en T17: streamlit_app.py y ui_panels.py.
Nuevos: pair_contexts.py, test_pair_contexts.py, este informe, matriz T17
Markdown/CSV y evidence/. Otros cambios Git son previos a esta tarea.
No fue necesario modificar demand_engine.py, demand_runtime.py o retraining.py.

R49 sigue PARCIAL: se ha definido el contexto al que pertenecen los eventos,
pero no se implementa un registro unificado/persistente de versiones/estados.
R50 sigue PARCIAL: el reset por contextos está probado y respeta SIN ACTIVE;
la conciliación documental completa queda fuera de esta actualización de R21.
R52 sigue PARCIAL: no se amplía h4-session-1 ni se exporta el mapa de contextos,
seed, estado aleatorio o procedencia adicional. Las claves del uploader solo
aislan la revisión de reportes, sin otorgar autoridad de activación.
R45 sigue PARCIAL y bloqueado para promoción real. LR no se incorpora aún.

Se detiene la implementación antes de R49 y R52.
