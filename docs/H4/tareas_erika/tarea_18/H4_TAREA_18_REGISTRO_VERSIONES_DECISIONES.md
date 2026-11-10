# H4 — Tarea 18: registro completo de versiones y decisiones (R49)

## Resultado

R49 pasa de PARCIAL a CUMPLIDO mediante evidencia verificable. Resultado final:
**420 pruebas aprobadas en 75.380 segundos: 404 anteriores y 16 nuevas**.
Los 29 archivos protegidos permanecen iguales a la referencia T17 y al snapshot
previo. Se verificaron las huellas binaria/normalizada de V1 y la del manifiesto.

ACTIVE sigue siendo una referencia en memoria, independiente por sesión y par.
Los archivos del registro no cargan, restauran, activan ni promueven modelos.
La promoción real de candidatos continúa bloqueada. No se inicia R52 ni R30.
La matriz T18 cambia únicamente R49: 52/68 cumplidos = 76,47 % estricto.

## Auditoría de lo existente

Se contrastaron la guía oficial, la matriz/informe T17 y el informe T13 con
pair_contexts, DemandRuntime, RetrainingSession, ComparisonSession, Streamlit
y ObservationJournal. Los contratos públicos de Ross permanecen intactos.

| Componente anterior | Evidencia existente | Falta de R49 resuelta |
|---|---|---|
| DemandRuntime | Lista de activaciones/bloqueos/rollback en memoria, sin identidad del par | Vincular estos eventos al registro del contexto; conservarlos en disco |
| RetrainingSession | Manifiestos/artefactos exclusivos y registro de confianza en memoria | Enlazar creación de candidato con versión, datos y fuente verificable |
| ComparisonSession | Comparación y rechazo separados, persistidos e identificados | Enlazarlos sin copiar métricas y conservar insuficiencia explícita |
| ObservationJournal | Emisiones, observados y cierres por producto/tienda/mes | Se conserva como autoridad del historial; no se duplica en este registro |
| pair_contexts | Referencias independientes por par, descartadas al reset | Mantener un registro de la DemandSession fuera de las claves intercambiadas |

No se incorporaron como eventos nuevos las activaciones o decisiones históricas
T10–17. No se atribuyeron fechas de entrenamiento a eventos observados hoy.
Los timestamps de fuentes existentes se etiquetan source_timestamp y se
distinguen de timestamp, que es la fecha UTC real de incorporación al registro.
Un proveedor ya activo al conectarse se registra como observado en ese momento,
sin inventar una activación anterior.

## Arquitectura y verificación

lifecycle_registry.py implementa un registro de evidencia por DemandSession.
El destino normal es ml/demand/lifecycle/<session_id>/; cada evento ocupa un
archivo nuevo exclusivo, con secuencia, UUID y JSON canónico. No se reescriben
eventos anteriores. La escritura se sincroniza antes de confirmarse en memoria.

Cada evento contiene schema, id, sequence, timestamp UTC, session_id, product_id,
location_id, type, modelo/versión/huella cuando corresponden, estados anterior
y posterior, referencia anterior, observaciones de ACTIVE, datos, motivo y
resultado. previous_sha256 y event_sha256 enlazan la cadena. El inventario y
la cabeza esperada se conservan independientemente en el objeto de la sesión.

records() detecta archivos añadidos/eliminados, cambios de contenido o secuencia
y cadenas recalculadas que no coincidan con el ancla de memoria. Devuelve copias.
verify_sources() contrasta las fuentes enlazadas. Las fuentes nuevas se cotejan
contra su registro de confianza en memoria antes de incorporarlas, no solo
contra un hash calculado del archivo que se intenta registrar.

Para V1 se conservan las referencias independientes auditadas:

- Binaria: fb0d8d81ba2558101a232ff616bff14fe0b95d6a13dfa24d60a8dce4b4e81d3e.
- Normalizada: 3e3cf6d1ef75567a69ff6f604bcb2a93f629f6d0fa503bdf734f3c6118c03883.
- Manifiesto: 41a10f4d196979cfff67410b21bf8ae527f6547aeca413e58811b4be920935f6.

El evento enlaza el manifiesto del candidato o el archivo de decisión mediante
identificador, ruta y SHA256. La comparación conserva periodo, número de casos
y huella exacta de la reserva. Las métricas y filas originales permanecen en
su archivo fuente; no se duplican como resultados experimentales nuevos.

Los estados CANDIDATE/REJECTED/ARCHIVED del registro describen el ciclo local.
Nunca modifican el rol interno del artefacto. En transiciones de referencias
se conserva la anterior con su estado ARCHIVED para interpretar el retorno.
affects_active distingue cambios/observaciones de referencia de decisiones
sobre candidatos. En un rechazo, previous_reference identifica la referencia
de la comparación; no se inventa un snapshot del ACTIVE actual, que reject()
no recibe. active_snapshot_available=false hace explícita esa diferencia.

## Eventos integrados

| Evento | Fuente y comportamiento |
|---|---|
| V1_AVAILABLE | Una vez por par/registro, después de comprobar artefacto y manifiesto, sin joblib ni activación |
| RUNTIME_CONNECTED | Observa una nueva instancia local; los reruns de la misma no crean otro evento |
| ACTIVATE_V1 | Activación explícita, referencia anterior/posterior e identidad verificadas |
| PROMOTE | Alias histórico promote_v1, únicamente para V1 congelada; no autoriza candidatos |
| CANDIDATE_CREATED | Ensayo nuevo de RetrainingSession vinculado antes del entrenamiento; referencia al manifiesto |
| MODELS_COMPARED | Comparación válida con identidades, periodo, filas y huella de reserva |
| INSUFFICIENT_EVIDENCE | Decisión separada enlazada al mismo reporte, sin duplicar sus métricas |
| CANDIDATE_REJECTED | Rechazo explícito, estado REJECTED, motivo y fuente conservados |
| PROMOTION_BLOCKED | Intento rechazado; no convierte identidad de JSON no verificado en identidad confiable de candidato |
| PROMOTE_FIXTURE / REJECT_FIXTURE | Hook del runtime usado exclusivamente por la subclase de pruebas, scope ISOLATED_FIXTURE |
| ROLLBACK | Referencias anterior/posterior y modelo retirado conservados; sin fit |
| RUNTIME_DISCONNECTED | Reconexión explícita del par, que queda sin su antigua referencia activa |
| RESET | Una operación de sesión con affected_contexts para todos los pares descartados |

Una clave por tipo/fuente/par hace idempotentes candidato, comparación,
insuficiencia y rechazo. Mismo rechazo/comparación y motivo devuelve la decisión
anterior. Una clave repetida con contenido contradictorio se rechaza. Repetir
el renderizado, visitar otro par o leer la tabla no produce decisiones nuevas.
Una segunda acción real de activación, reconexión o rollback es otro evento.

## Integración y reset

bind_lifecycle() es una extensión opcional de las clases locales; no cambia
create_runtime(), get_active_model(), predict(features) ni sus respuestas.
UI conecta cada proveedor/servicio al binding de su par. Se rechaza reutilizar
un servicio de otra sesión/par. pair_contexts.py no necesitó modificaciones.

El registro de la sesión está fuera de PAIR_KEYS. Al reset, se registra la
operación con los snapshots de los pares antes de eliminar sus referencias.
El objeto anterior pasa a lifecycle_archives, conservando su ancla verificable,
y sus archivos permanecen en disco. El nuevo motor tiene otro session_id y
otro registro. Comienza SIN ACTIVE, con V1 disponible para una acción nueva.
La tabla local de Streamlit permite revisar la evidencia actual y la anterior.

Un RESET se guarda una sola vez, incluyendo todos los affected_contexts. La
consulta records(pair) lo incluye para cualquier par afectado sin duplicarlo.
No borra candidatos o decisiones persistidos ni convierte evidencia antigua
en un modelo activo nuevo. La reconexión afecta exclusivamente al par actual.

Si falla la evidencia de una activación o rollback, no se confirma el cambio
de referencia. Si falla el registro después de entrenar, el candidato aislado
puede existir, pero un reintento recupera ese resultado y registra su evidencia
sin otro fit. Una cadena corrupta bloquea nuevas escrituras; no se repara ni
se continúa silenciosamente. No hay recuperación automática desde disco.

## Ejemplo real reproducible, exclusivamente simulado

Comando desde la raíz, PowerShell:

```powershell
& .\ml\demand\.venv\Scripts\python.exe -B ml/demand/example_lifecycle.py `
  --output docs/H4/tareas_erika/tarea_18/evidence/example
```

Cada ejecución crea una carpeta/UUID nuevos. No sobrescribe ejemplos anteriores.
Los datos son observados manuales demostrativos 10…21 para octubre 2026 a
septiembre 2027, una serie 1/5. Los tres primeros meses forman historia nueva;
enero–junio 2027 aporta seis filas de ajuste y julio–septiembre tres reservas.
Los valores iniciales de TEST no se utilizan como lags del entrenamiento.
Las emisiones de calentamiento son abstenciones controladas por falta de
historia nueva; las posteriores usan inferencia real de V1.

Ejecución final conservada:

- Sesión: f69c4a8eb1784203b3283f667e5e93dc.
- Candidato: CAND-6b179cf114a246a0be13cd040ff24549.
- 6 filas de entrenamiento, 1 serie y 3 observaciones de comparación.
- 10 eventos: disponibilidad, conexión, activación, candidato, comparación,
  insuficiencia, rechazo, bloqueo de promoción, rollback y reset.
- Cabeza: 5dd3ec6b276eaacee5255903171056cbe4828137c9f7874c9ac0c46ed8da5385.
- Estado final: SIN ACTIVE. Predicciones cerradas preservadas hasta el reset.
- Decisión: INSUFFICIENT_EVIDENCE y REJECTED_FOR_PROMOTION. No se promovió.

En esta reserva simulada: MAE V1 0.9279069888581345 y candidato
4.454166666666662; RMSE 1.1202195739427763 y 4.528384630429605,
cobertura 3/3 en ambos. No son métricas TEST oficiales ni evidencia suficiente
de superioridad estadística. El candidato original T12 permanece intacto.

Se conserva además una ejecución intermedia del ejemplo, identificada por
example_log.json; la final es example_log_final.json. Ambas están aisladas
bajo evidence/example, sin añadir experimentos al registro oficial.

La demostración positiva separada, fixture_example.py dentro de esta carpeta
de evidencias, importa exclusivamente la política de unittest de T13. Su sesión
0250ba565dad4c2faada858bd4d8d7ee registra PROMOTE_FIXTURE y ROLLBACK, termina
SIN ACTIVE y elimina el artefacto temporal del fixture. Conserva la traza, no
declara el fixture disponible para carga posterior. La app no importa ese script.

## Pruebas y validación

Las 16 pruebas nuevas cubren secuencia/fechas UTC, campos, idempotencia,
contradicciones, alteración incluso recalculando hashes, inventario, fuentes,
copias, JSON sin autoridad, rutas protegidas, sesiones/pares, disponibilidad,
activación/rollback sin fit, fallos de escritura, promoción de fixture, ciclo
completo con candidato/rechazo, ausencia de historia fabricada al vincular
tarde, recuperación de entrenamiento sin repetir fit, fuente sustituida y
reset/reruns reales de AppTest con conservación de evidencia.

Resultado final: **420/420 OK en 75.380 s**. La pasada anterior de 418 pruebas
también aprobó; se añadieron dos casos y se repitió la suite tras reforzar la
verificación de fuentes y distinguir decisiones de cambios de ACTIVE.
No se eliminaron ni debilitaron pruebas anteriores.

El ejecutor run_tests.py aísla los registros de todas las sesiones AppTest en
un TemporaryDirectory, incluyendo los de las 404 pruebas anteriores. Las
pruebas conservan sus entrenamientos de fixtures/candidatos temporales.
Se necesitó permiso de sockets locales de AppTest; no acceso a servicios
productivos. No se realizó revisión visual ni se generaron capturas.

## Integridad y límites

29 SHA256 protegidos coinciden antes/después y con T17: datasets, catálogo,
generadores, LR/V1, experiments.csv, manifiestos, TEST y candidato/decisiones
oficiales. Se validó además la referencia de datos sin regenerarla. Los eventos
del ejemplo final se comprobaron por cadena, cabeza registrada y fuentes.

La cadena detecta alteraciones contra el ancla de memoria conservada durante
la sesión/reset. No es una firma externa ni garantiza autenticidad frente a
alguien que controle código, memoria y todos los archivos. Tras cerrar el
proceso quedan archivos y resúmenes, pero no se restaura una autoridad desde
ellos. La secuencia determina el orden; los timestamps son lecturas reales
del reloj del equipo, no una certificación de tiempo externa.

Un proveedor independiente creado fuera de Streamlit no tiene IDs de negocio
en el contrato de Ross: conserva sus eventos anteriores y solo participa en
el registro unificado cuando código local lo vincula explícitamente. No se
inventan IDs ni se reconstruye un historial anterior a esa vinculación.

No se reentrenó V1, reevaluó TEST, modificó dataset 1.1, alteró hiperparámetros
de V1 o sobrescribió archivos congelados. No hubo cambios productivos, commits
ni push. El registro normal ml/demand/lifecycle no fue poblado por la suite;
sus evidencias son temporales, salvo los ejemplos explícitos bajo docs.

## Archivos y siguientes requisitos

Modificados: demand_runtime.py, retraining.py, model_comparison.py,
streamlit_app.py y ui_panels.py. Nuevos: lifecycle_registry.py,
test_lifecycle_registry.py, example_lifecycle.py, informe/matriz T18 y
evidence/. DemandSession, ObservationJournal y pair_contexts no cambian.

R52 sigue PARCIAL: h4-session-1 no se amplía, no exporta este registro ni seed,
estado RNG, rama o procedencia adicional. Habrá que acordar un esquema de
exportación que enlace evidencias conservando el principio de cero autoridad
de los JSON importados. No se implementa esa tarea aquí.

R30 sigue PARCIAL: LR aún no se integra como REFERENCE; requiere carga y
preprocesador verificados y revisión de Ross. V1 conserva su selección.
R45 sigue PARCIAL y la promoción real continúa bloqueada. R50 mantiene su
estado anterior; el reset respeta el acuerdo SIN ACTIVE, sin cerrar por ello
la conciliación documental global del requisito.

## Evidencias

- [Pruebas completas finales](evidence/full_tests.txt).
- [Resumen de validación](evidence/validation.json).
- [Ejemplo final](evidence/example_log_final.json).
- [Resumen completo del ciclo](evidence/example/example-c84179d4d0614c7dbaf89155f796ed8a/summary.json).
- [Eventos del ciclo](evidence/example/example-c84179d4d0614c7dbaf89155f796ed8a/events/f69c4a8eb1784203b3283f667e5e93dc).
- [Demostración de fixtures](evidence/fixture_log.json).
- [Integridad previa](evidence/integrity_before.json) y [posterior](evidence/integrity_after.json).
- [Matriz T18](H4_MATRIZ_CUMPLIMIENTO_T18.md) y su CSV.
- [Git status](evidence/git_status.txt) y [diff stat](evidence/git_diff_stat.txt), acumulados.

Se detiene el trabajo sin iniciar R52 ni integrar LR.
