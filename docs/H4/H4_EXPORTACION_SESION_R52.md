# H4 — Contrato de exportación R52

## Compatibilidad y alcance

El documento sigue siendo h4-session-1. No cambia nombres ni tipos existentes.
La ampliación está en extensions.h4_traceability, schema_version
h4-traceability-1. Es evidencia de SIMULACIÓN; no restaura una sesión ni
autoriza cargar, activar o promover modelos. No contiene estimadores.

| Campo público de Ross | Tipo y significado conservados |
|---|---|
| schema_version | String exacto h4-session-1 |
| origin | String exacto SIMULACION |
| session_id | String: UUID del ObservationJournal, no del motor |
| generator_seed | null legado. Se conserva este tipo; el seed real está en la extensión |
| records | Array de cierres ClosedObservation: forecast, observed, observed_at, rotation |

Los consumidores existentes pueden ignorar extensions. Forecast mantiene
product_id, location_id, month, features, prediction, baseline, model, reason,
issued_at y scenario. Las features se serializan como array en el orden oficial,
o null cuando no se emitieron entradas válidas. ModelInfo mantiene name,
version, artifact_hash y trained_through. No se sustituyen esos objetos por
objetos de runtime ni se mezcla un pendiente con records.

Nombre del archivo: h4-sesion-simulacion.json. MIME: application/json.
DESCARGAR SESIÓN JSON está disponible también sin cierres y después de reset.

## Extensión h4-traceability-1

Todos los campos siguientes viven en extensions.h4_traceability.

| Campo | Tipo / contenido |
|---|---|
| schema_version | String exacto h4-traceability-1 |
| authority / authorizes_model_changes | EVIDENCE_ONLY / false, descriptivos; cambiarlos nunca concede autoridad |
| exported_at | Fecha UTC real de captura, distinta del calendario simulado |
| snapshot_phase | CURRENT o PRE_RESET_SNAPSHOT |
| simulation_context | ID real de DemandSession, kind DEMAND_SESSION, rama observada al exportar y contexto padre si estuviera registrado |
| engine | Snapshot de solo datos de DemandSession; incluye engine_session_id y journal_id para vincular ambas identidades |
| observations | Cierres con producto/tienda/mes, observado, procedencia, fecha y comprobación entre fuentes |
| journal | Pendientes, revelados, revisiones y comienzo conocido del seguimiento |
| model_contexts | Referencias y candidatos separados por par, nunca un ACTIVE global |
| lifecycle | Eventos R49, sesión y cabeza de cadena verificados contra sus fuentes al capturar |
| prior_sessions | Snapshots previos a reset, separados del estado actual |
| prior_lifecycle_only | Eventos anteriores disponibles sin snapshot completo; diario/RNG de esa época se marcan desconocidos |
| limitations | Límites explícitos de evidencia, autoridad y cobertura histórica |
| document_sha256 | Huella canónica del documento completo, excluyendo únicamente este propio campo |

git_branch_at_export se lee de .git/HEAD solo si identifica una rama local.
Para worktrees, detached HEAD o archivo ausente se devuelve null, sin inventar
una rama. No se atribuye esa rama a la creación de la sesión. El ID de contexto
siempre es la identidad real del motor. parent_context_id=null y su estado
UNKNOWN_NOT_RECORDED no implican una bifurcación que no haya sido registrada.

### engine y pares

engine contiene generator_seed real, selected_pair, first_simulable_month,
origin, pairs, revisions, trace_started_at e history_before_tracking.

Cada entrada de pairs contiene:

- product_id, location_id y scenario reales; simulated_only distingue la rama
  sin historia inicial del producto nuevo.
- calendar: mes abierto, meses cerrados y mes visualizado. El mes visualizado
  de pares no seleccionados es null porque el motor no conserva esa vista.
- hypothetical_lags: hipótesis editable, no ventas observadas.
- reference_history_for_simulation: referencia histórica inicial identificada
  como tal, separada de los nuevos cierres y no convertida en filas incrementales.
- effective_lags_for_open_month: orden cronológico lag3, lag2, lag1 del generador;
  no confundirlo con el orden de features ML, que empieza por lag1.
- closed_observations: solo cierres conocidos por el motor, con source MANUAL,
  GENERATED o null si no se registró esa información.
- pending_observation: valor/source pendientes, sin clasificarlos como cierre.
- cached_generated_results: propuestas del generador, con clasificación
  SIMULATION_DRAW_NOT_CLOSED_SALES. Un observado manual puede ser distinto.
- rng: algoritmo, versión Python, versión del estado, vector interno, gauss_next,
  derivación del seed por par y su SHA256 hexadecimal.

El estado RNG contiene la caché gauss_next: omitirla impediría reproducir la
siguiente muestra normal. El vector MT19937 usa enteros representables
exactamente en JSON. El seed derivado de 256 bits se identifica en hexadecimal,
evitando redondearlo como número JavaScript. La reproducción requiere la
misma implementación/versión y el mismo contexto y secuencia de acciones.
No hay API productiva de importación o restauración del RNG desde archivos.

La demanda latente no se exporta. La disponibilidad y las propuestas internas
no se incorporan a observations ni a records como etiquetas reales.

### Observaciones y revisiones

observations añade source, provenance_status y consistency al valor cerrado.
ENGINE_AND_JOURNAL exige coherencia de ambas autoridades. Los cierres históricos
anteriores al simulador que solo existan en el diario se identifican como
LEGACY_JOURNAL_ONLY, con procedencia desconocida; no se atribuyen al motor.

Las revisiones tienen UUID, secuencia, fecha UTC, tipo, par, mes y detalles.
El motor registra hipótesis/escenario, draws, ingreso manual/generado, cierre,
avance y reset directo. El diario registra cada emisión, descarte, revelado,
cierre y revisión/confirmación de entradas desde la interfaz. Así se conservan
las emisiones sustituidas antes de revelar el observado. Rerenderizar o
exportar no crea otra emisión ni consume RNG.

El seguimiento comienza en trace_started_at. Las revisiones anteriores que no
se conservaron no se reconstruyen con fechas o valores supuestos. Su cobertura
queda UNKNOWN. Los snapshots de datos actuales no se presentan como revisiones
pasadas recuperadas.

### Modelos, candidatos y decisiones

model_contexts contiene por par references, current_candidate_id, candidates
y decisions. references exporta active, previous_references y runtime_events
como metadatos. Las referencias locales se contrastan con sus verificadores
de identidad/artefacto; un proveedor externo sin ese método se identifica como
UNKNOWN_EXTERNAL_PROVIDER, sin certificar su archivo.

Los candidatos proceden exclusivamente del registro de confianza de
RetrainingSession. Se cotejan manifiesto y todos sus archivos mediante SHA256
sin deserializar joblib. decisions conserva la evidencia de ComparisonSession
y su fuente verificada. Los eventos R49 relacionan activación, comparación,
insuficiencia, rechazo, bloqueo y rollback. Los reportes JSON importados no
registran candidatos y nunca se convierten en referencias activas.

Los campos públicos de Ross pueden seguir consumiéndose sin esta extensión.
RNG, revisiones, metadatos de referencias y candidatos son el contrato interno
versionado de Erika, disponible para que Ross añada filtros y vistas. Ninguno
de esos campos es una instrucción ejecutable.

## Consistencia, reset e integridad

El exportador comprueba identidades de sesión/par, claves de emisiones/cierres,
fechas, observados, revelados, procedencia y revisiones originales cuando
existen. Rechaza contradicciones; no completa meses ni convierte faltantes en
cero. Se compara la vista actual de PairContexts, no un snapshot obsoleto.

Reset captura la evidencia previa al descarte y conserva su fase explícita
PRE_RESET_SNAPSHOT. El documento de la sesión nueva contiene records vacío y
ACTIVE local inactivo; las referencias antiguas dentro de prior_sessions no
describen el estado actual. Los snapshots no se anidan recursivamente: cada
archivo previo contiene solo su sesión y el documento actual los agrupa.

Si el snapshot previo no puede verificarse, reset conserva las fuentes de
motor/cierres como UNVERIFIED, sin certificarlas como observaciones coherentes.
Si solo existe un registro R49 anterior, se exportan sus eventos disponibles
y se marca UNKNOWN_NOT_CAPTURED para su historia ausente. Una fuente antigua
no disponible no se fabrica ni se usa como autorización.

document_sha256 se calcula mediante JSON UTF-8, sort_keys=true,
ensure_ascii=false, allow_nan=false y separadores coma/dos puntos sin espacios,
excluyendo el campo document_sha256. verify_session_export comprueba ese
contenido lógico. La huella binaria del archivo formateado puede ser distinta.

Recalcular SHA256 tras editar JSON no autentica sus afirmaciones. La cadena
R49 se contrasta con el ancla local en memoria al capturar; este export no es
una firma externa. No existe conversión del JSON en proveedores, candidatos
confiables, permisos ni decisiones ejecutables.

## Pendiente de Ross

La descarga está conectada y probada con AppTest. Quedan revisión visual real
y aceptación de consumo de la extensión: archivo antes/después de cierre y
reset, separación de pares, legibilidad de procedencia y referencias, y
distinción entre snapshot previo y estado actual. No deben reemplazarse esas
evidencias por capturas simuladas o por el resultado de unittest.
