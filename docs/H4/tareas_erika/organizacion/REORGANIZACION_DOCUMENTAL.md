# H4 — Reorganización documental de tareas de Erika

Fecha: 2026-11-09. Alcance: organización documental y ajustes de rutas de sus consumidores. **191 archivos trasladados; ninguno perdido ni sobrescrito por el traslado.** No se modificó lógica productiva, modelos, datasets, eventos ni decisiones históricas. La matriz conserva sus estados; este trabajo no aumenta el porcentaje de cumplimiento H4.

## Auditoría previa y criterio

Se inspeccionaron los 224 archivos originales de `docs/H4`, sus subdirectorios, scripts, referencias y tipos de evidencia. Se analizaron todos los JSON de las carpetas de tareas y organización. Se localizaron referencias en Markdown, README, CSV, scripts de auditoría y pruebas. Antes de mover se capturaron SHA256 de documentos, código Python del módulo y 29 archivos protegidos; se contrastaron estos últimos con la referencia anterior T21.

Se mantuvieron en raíz guía oficial, `H4_INFORME_FINAL.md`, matriz final MD/CSV, checklist de Ross, guía Windows, contrato R52, prompts y README. `historico/` no se movió ni editó. La matriz sin sufijo de tarea es la fotografía original T14; se trasladó a `tarea_14/`, conservando en raíz únicamente la matriz final consolidada.

No existían informe T20, informe T16 ni carpeta de evidencias T16; no se generaron documentos para aparentar completitud. La evidencia T20 existente sí se conserva.

## Árbol final resumido

```text
docs/H4/
  H4_IMPLEMENTACION_MODELO_PREDICTIVO.md
  H4_INFORME_FINAL.md
  H4_MATRIZ_CUMPLIMIENTO_FINAL.md
  H4_MATRIZ_CUMPLIMIENTO_FINAL.csv
  H4_CHECKLIST_VALIDACION_ROSS.md
  H4_GUIA_EJECUCION_WINDOWS.md
  H4_EXPORTACION_SESION_R52.md
  PROMPTS_MODELO_PREDICTIVO_H4.md
  README.md
  historico/                          # intacto
  tareas_erika/
    README.md
    document_paths.py                 # consulta compatible de rutas antiguas
    tarea_10/                         # informe + evidence/
    tarea_11/                         # informe + evidence/
    tarea_12/                         # informe + evidence/
    tarea_13/                         # informe + evidence/
    tarea_14/                         # matriz T14 MD/CSV + evidence/
    tarea_15/                         # informe, matriz T15 MD/CSV + evidence/
    tarea_17/                         # informe, matriz T17 MD/CSV + evidence/
    tarea_18/                         # informe, matriz T18 MD/CSV + evidence/
    tarea_19/                         # informe, matriz T19 MD/CSV + evidence/
    tarea_20/evidence/                # solo archivos realmente existentes
    tarea_21/                         # informe + evidence/
    organizacion/
      REORGANIZACION_DOCUMENTAL.md
      evidence/                      # organización previa, intacta
      evidence_documental/           # auditoría de este traslado
```

El árbol completo, archivo por archivo, está en `evidence_documental/tree_final.txt`. El índice `../README.md` enlaza los nueve informes existentes. Los 191 traslados se distribuyen así:

| Grupo | Archivos trasladados |
|---|---:|
| T10 | 6 |
| T11 | 9 |
| T12 | 6 |
| T13 | 8 |
| T14 | 16 |
| T15 | 17 |
| T17 | 11 |
| T18 | 57 |
| T19 | 27 |
| T20 | 3 |
| T21 | 18 |
| Organización previa | 13 |
| **Total** | **191** |

## Evidencia e integridad

`evidence_documental/before.json` captura el inventario previo; `moves.json` registra cada ruta antigua/nueva y SHA256. `moves_verified.json` acredita igualdad de bytes **inmediatamente después de cada traslado y antes de editar referencias**. Las actualizaciones posteriores permitidas están diferenciadas en `reference_edits_final.json` y `verified.json`; no se afirma que un Markdown con enlaces actualizados conserve su hash original.

Todos los originales siguen presentes en su ruta actual. Los cambios documentales se limitan a referencias y la explicación de compatibilidad; los scripts documentales incorporan además resolución de raíz y salidas seguras. JSON históricos, CSV intermedios, logs anteriores, ZIP, joblib de ejemplos, observados, decisiones y eventos mantienen sus bytes. `historico/` conserva todos sus originales.

Los **29 archivos protegidos del módulo** mantienen sus hashes. V1 conserva SHA256 normalizado `3e3cf6d1ef75567a69ff6f604bcb2a93f629f6d0fa503bdf734f3c6118c03883` y binario `fb0d8d81ba2558101a232ff616bff14fe0b95d6a13dfa24d60a8dce4b4e81d3e`. El inventario de 442 eventos de lifecycle y su ZIP se verificaron byte a byte; el respaldo sigue disponible en `evidence/lifecycle_preservado.zip` con su inventario original.

## Referencias actualizadas

- Markdown activo y enlaces de informes trasladados; README raíz H4 y README del módulo. Los enlaces locales se verificaron sin roturas fuera del histórico inmutable.
- Rutas de evidencia de la matriz final CSV, sin cambiar nombres/tipos ni valores de estado, responsables o métricas.
- Cuatro tests: `test_h4_functional_fixes`, `test_model_comparison`, `test_reference_runtime`, `test_retraining`.
- Tres scripts de auditoría del módulo: `validate_v1_activation.py`, `validate_h4_integral.py`, `validate_candidate_comparison.py`.
- Diez scripts documentales trasladados: resolución de raíz, referencias entre tareas y, donde correspondía, discovery/imports de `tests/`. No se modificaron aserciones del producto: el verificador invierte las sustituciones de rutas en memoria y recupera exactamente los hashes originales de los siete scripts externos.
- Comentario de `.gitignore` que documenta la nueva ubicación del respaldo; **cero reglas añadidas o modificadas**.

Para snapshots protegidos no se corrigieron rutas en su contenido: `historical_references.json` identifica los archivos que conservan referencias antiguas; `moves.json` y `document_paths.relocated_path()` resuelven la consulta local. No hay duplicación de paquetes, enlaces simbólicos ni reconstrucción de eventos históricos. El mapa no sirve para autorizar carga/activación de modelos.

T21: `validate_flows.py` acepta `--output-dir` y rechaza sobrescribir sus resultados anteriores. `build_closure.py --check-paths` valida entradas sin escribir; `--output-dir` exige destino nuevo y separa resultados regenerados del cierre histórico. Sus referencias al código antiguo admiten exclusivamente los cambios de ruta registrados, sin reescribir `source_before.json`. Se comprobó la reconstrucción aislada en `evidence_documental/closure_rebuild/`.

## Clasificación Git y conservación

| Evidencia | Decisión |
|---|---|
| Scripts de auditoría/reproducción | Conservar, revisar y versionar junto con su documentación |
| Manifiestos, inventarios, hashes, matrices históricas | Conservar sin regenerar; versionar |
| Eventos, ejemplos, decisiones y exportaciones únicos | Conservar todos; versionar como evidencia |
| Modelos de ejemplo dentro de evidencia | Conservar bytes; no tratarlos como ACTIVE ni cargarlos desde importación |
| ZIP histórico e inventario | Conservar y versionar ambos; no descomprimir sobre originales |
| Logs regenerables de ejecuciones previas | Conservar: documentan resultados/intentos de una fecha, no equivalen a futuros reruns |
| Nuevos logs interrumpidos y autorizados | Conservar ambos, diferenciados; solo la ejecución completa acredita el resultado |
| Temporales nuevos | Se usaron directorios temporales del sistema; no se detectó necesidad de nueva exclusión |

No se ignoran `tareas_erika/` ni `evidence/`. Se comprobó con Git que los archivos trasladados no quedan excluidos. No se hicieron staging, commits ni push. Los modelos/datasets/reportes siguen pendientes de incorporación selectiva por Ross si aún están untracked.

## Validación ejecutada

1. Verificación SHA256 de los **191 traslados**, sin sobrescritura; conservación del inventario completo original.
2. Compatibilidad: las **191 rutas antiguas** resuelven a archivos actuales; todos los scripts documentales son sintácticamente válidos y los enlaces Markdown comprobados existen.
3. `build_closure.py --check-paths`: aprobado. Reconstrucción documental aislada: aprobada, mismos 54 CUMPLIDOS/11 PARCIALES/3 NO VERIFICADOS/5 NO APLICA; no se reemplazó la matriz final.
4. Suite completa desde raíz: **464 aprobadas, 0 fallidas, 0 errores, 0 omitidas**, **107.749 segundos**, en `evidence_documental/full_tests_authorized.txt`. El intento restringido se interrumpió al no progresar en AppTest; no se presenta como ejecución aprobada. La ejecución completa posterior usó aprobación para sockets locales.
5. Script T21 trasladado con salida nueva: ocho escenarios, **48 cierres y un caso manual**, reset y reproducibilidad aprobados, **cero fit durante inferencia**; resultados en `evidence_documental/flows_authorized/`. No son ventas reales ni nueva evaluación TEST. La suite mantiene sus entrenamientos de fixtures aislados autorizados; no se entrenó ningún modelo oficial.
6. Integridad posterior: **29/29 protegidos**, **442/442 eventos históricos** y **442 entradas ZIP** intactos. `git diff --check` sin incidencias. Snapshots de estado y diff en `evidence_documental/`.

## Límites y pendientes

- Esta reorganización no resuelve la portabilidad del candidato oficial archivado con `folder` absoluto ni las rutas Windows congeladas: son hallazgos previos T21. No se editó ningún manifiesto para sortearlos. Los ejemplos de evidencia también conservan rutas históricas y no deben presentarse como paquetes reubicables automáticamente.
- Los verificadores T14/T15 contienen conteos históricos 375/394; no se ejecutaron para sobrescribir snapshots ni se cambiaron esos conteos para aparentar vigencia. La validación actual se realizó con el runner de 464 y el verificador nuevo de organización.
- El script de traslado es de ejecución única y evita sobrescribir su inventario inicial. Para comprobaciones posteriores usar `verify.py`; no repetir los movimientos.
- La revisión visual y los pendientes funcionales registrados en T21 continúan pendientes. No se amplió el alcance ni se promovieron candidatos.

La organización queda validada localmente sin pérdida documental. Ross debe revisar e incorporar selectivamente los movimientos, ajustes de rutas y evidencia nueva, conservando los archivos oficiales y respaldos.
