# H4 — T21: auditoría técnica final

Fecha de ejecución: 2026-11-09, Windows, rama `erika`. **T21 APROBADA como auditoría técnica local; H4 no está cerrado al 100 %.** No se identificó una regresión crítica del flujo local probado. Existen pendientes de integración, aceptación visual, protocolo real de promoción y portabilidad que se detallan abajo. APROBADA no significa aprobación de esos pendientes ni autorización para promocionar modelos.

## Objetivo, alcance y método

Contrastar la guía oficial completa `H4_IMPLEMENTACION_MODELO_PREDICTIVO.md`, matrices e informes T10–T20 y organización del repositorio con código, artefactos y evidencias actuales. Se inspeccionaron motor, journal, runtime, contextos, registro, exportación, pipelines, adaptador de referencias y Streamlit. La matriz final conserva el mapeo original de cláusulas de las tres semanas y diferencia verificación técnica de aceptación visual.

Se capturaron hashes antes de ejecutar la regresión; se contrastaron con referencias anteriores de integridad. Se ejecutó la suite desde la raíz, se verificó descubrimiento sin duplicados y se realizó un ensayo adicional mediante AppTest sobre la aplicación normal: seis meses por cada escenario, controles de aislamiento, rechazo, rollback y reset. Las carpetas nuevas de lifecycle/decisiones de esas pruebas fueron temporales. Se compararon nuevamente archivos protegidos, código y registros históricos al terminar.

No se ejecutó el entrenador oficial, el generador histórico ni la evaluación oficial TEST. La suite sí ejecuta los entrenamientos temporales autorizados de sus fixtures, en espacios aislados. No se creó un modelo oficial nuevo. No se realizaron cambios de código productivo, refactorizaciones, operaciones de staging, commits ni push.

## Repositorio y organización

- Los **21 módulos** `test_*.py` están en `ml/demand/tests/`. El runner descubre **464 IDs únicos**, con imports válidos desde la raíz. `tests/__init__.py` aísla el destino de lifecycle en temporales; las dependencias entre helpers de tests usan el paquete de pruebas.
- Continúan presentes generador/configuración/versión histórica, catálogo, datasets, entrenadores, pipeline, selección, runtime e inferencia de referencias. Las versiones instaladas y los conteos están en `evidence/initial_audit.json`.
- El inventario inicial de Git registró **244 entradas**; su snapshot posterior contiene 245 al incluir el propio archivo de captura. El snapshot final, con archivos no seguidos expandidos, contiene **263 entradas**. El 242 de la organización es un antecedente, no el conteo de T21. El aumento corresponde a documentación/evidencia nueva, no a cambios productivos. Se preservaron los cambios anteriores. Hay tres rutas antiguas de pruebas tracked con estado D y sus archivos en `tests/` como nuevos: son movimientos todavía sin staging, no pérdida de pruebas.
- `.gitignore` contiene el aislamiento específico `/ml/demand/lifecycle/`, no una exclusión general de modelos/datasets/reportes. Los 442 originales siguen físicamente disponibles y respaldados por ZIP e inventario versionables. No deben borrarse por estar ignorados.
- `.gitattributes` preserva bytes de paquetes binarios y paquetes congelados nuevos. No convierte ni reescribe el dataset histórico. El detalle de cambios tracked preexistentes está en `evidence/git_diff_stat.txt`; los archivos nuevos no aparecen en `git diff --stat`.

## Integridad y modelos

**29/29 archivos protegidos idénticos antes y después**, incluyendo catálogo, generadores, dataset, V1, manifiestos, registro de experimentos, evaluación TEST, LinearRegression y paquete candidato/decisiones incluidos en el inventario. Las claves y huellas completas están en `integrity_before.json` e `integrity_after.json`. Los **50 archivos Python** del módulo registrados antes de T21 conservan sus bytes; esto incluye pruebas existentes.

| Identidad | SHA256 |
|---|---|
| V1 normalizado oficial (`content_sha256`) | `3e3cf6d1ef75567a69ff6f604bcb2a93f629f6d0fa503bdf734f3c6118c03883` |
| V1 binario | `fb0d8d81ba2558101a232ff616bff14fe0b95d6a13dfa24d60a8dce4b4e81d3e` |
| Manifiesto V1 binario | `41a10f4d196979cfff67410b21bf8ae527f6547aeca413e58811b4be920935f6` |
| LinearRegression binario | `55c7f1e152b485fc75150b506da541897948e4920aaabe95248aa433ff9dcbb8` |

El hash normalizado y el binario son distintos por definición. El runtime contrasta el binario con una referencia fijada en código antes de deserializar; no confía únicamente en recalcular el hash del mismo archivo ni en un JSON importado. El manifiesto y el rol interno CANDIDATE del artefacto V1 permanecen congelados. La activación temporal de una referencia en una sesión no modifica ese rol.

Resultados oficiales **leídos de evidencias existentes**, no recalculados:

| Modelo / partición | MAE | RMSE | R² |
|---|---:|---:|---:|
| Baseline lag1 / VALIDATION | 6.158730 | — | — |
| LinearRegression / VALIDATION | 5.473184 | 8.792626 | 0.290989 |
| RandomForest V1 / VALIDATION | 5.158657 | 8.441614 | 0.346469 |
| RandomForest V1 / TEST oficial | 4.814178503040102 | 8.182890558417325 | 0.42304686389766555 |

El reporte TEST registra 504/504 predicciones y cero negativas. Su cobertura 100 % significa que hubo salida para todas esas filas, no exactitud 100 % ni confianza estadística. No existe intervalo predictivo calibrado al 95 % ni calibración temporal independiente que permita declararlo. Harían falta datos de calibración temporal independientes y posteriores, sin usar TEST inicial, y otra validación de cobertura y anchura fuera de calibración. No se altera V1 para simular esa capacidad.

## Dataset y reproducibilidad

Dataset sintético 1.1: **56 productos × 3 tiendas × 24 meses = 4032 filas base**; 3528 supervisadas; tiendas 5/6/7. Periodo octubre 2024–septiembre 2026. TRAIN 2520 filas enero 2025–marzo 2026; VALIDATION 504 abril–junio 2026; TEST 504 julio–septiembre 2026. Semilla/configuración histórica conservadas; las pruebas del generador usan salidas temporales. Ni IDs ni demanda latente son features; el orden oficial es lag1, lag2, lag3, seno y coseno del mes. El escalador se ajusta solo con entrenamiento.

Se distinguen cinco garantías:

1. **Datos:** parámetros, seed, generador y dataset presentes; hashes preservados y pruebas temporales de reproducibilidad aprobadas. No se regeneró el dataset oficial.
2. **Entrenamiento:** scripts, semillas, parámetros, cortes y versiones registrados; fixtures prueban entrenamiento aislado. No se promete igualdad binaria entre entornos ni se reentrenó V1 para verificarla.
3. **Modelos disponibles:** ambos artefactos reales están presentes y verificados localmente. V1 está disponible para activación explícita y LinearRegression es REFERENCE.
4. **Portabilidad:** incompleta. No se ejecutó una instalación desde cero ni un clon limpio. Los assets indispensables sin staging todavía no existen por ello en un clon publicado.
5. **Resultados exactos:** los resultados oficiales se preservan con sus artefactos y reportes. No se confunde conservación con reproducción de un entrenamiento oficial nuevo.

Entorno observado: Python 3.11.0, numpy 2.4.6, pandas 3.1.0, scikit-learn 1.9.1, scipy 1.17.1, joblib 1.6.0, Streamlit 1.66.1. El lock documentado permite preparar dependencias; referencias históricas a otro patch de Python no equivalen a validar ese entorno. No se afirma reproducibilidad universal a partir de esta máquina.

### Hallazgos de portabilidad que no se corrigieron

- `model_comparison.archived_run()` contrasta la ruta absoluta `folder` del manifiesto archivado con su ubicación actual. Al trasladar el repositorio, el paquete archivado puede ser rechazado y fallar las pruebas que lo consultan. Causa: ubicación física incorporada como condición de identidad. El archivo protegido no se modificó.
- `select_v1._resolve_artifact_path()` usa `Path(text)` sobre rutas históricas con separadores Windows. En POSIX no se interpretan necesariamente igual. Es una limitación detectada por inspección, no un fallo ejecutado en Linux.
- Huellas binarias históricas de texto pueden depender de finales de línea; no se deben cambiar las referencias protegidas para forzar coincidencias.

Solución futura propuesta, pendiente de revisión: resolver paquetes desde una raíz confiable relativa a `ml/demand`, mantener el `folder` original como metadato histórico y comprobar los hashes independientes del manifiesto original y de su paquete. Si se necesita un mapa de traslado, debe ser externo al manifiesto congelado, vinculado a su huella, sin aceptar rutas arbitrarias/importaciones como autoridad. Añadir fixtures de traslado y separadores antes de declarar portabilidad. Esta auditoría no implementa esa modificación ni debilita los controles actuales.

## Escenarios y flujo mensual

Evidencia nueva: `evidence/validate_flows.py`, `flows.json` y `flows_log.txt`. Se ejecutó la aplicación con AppTest, no capturas de navegador. **48 cierres** de octubre 2026 a marzo 2027, seis por escenario, más un cierre manual separado. Los números son ventas simuladas, no ventas comerciales ni una evaluación de exactitud.

| Escenario | Precarga declarada (lag3, lag2, lag1) | Resultado técnico |
|---|---|---|
| NORMAL | 10, 10, 10 | 6 cierres, inferencia RF, generación, reset y reproducción aprobados |
| CRECIMIENTO | 8, 12, 17 | 6 cierres y efecto creciente, lags observados coherentes |
| CAÍDA | 17, 12, 8 | 6 cierres y observados no negativos |
| PICO MAYORISTA | 10, 10, 10 | 6 cierres y efecto definido por generador conservado |
| STOCKOUT | 10, 10, 10 | 6 cierres; observado limitado por disponibilidad; latente separado |
| PRODUCTO NUEVO | desconocidos | 6 cierres con abstención; no se inventa historia |
| CAMBIO PERSISTENTE | 10, 10, 10 | 6 cierres y efecto persistente según implementación |
| RECUPERACIÓN | 4, 6, 8 | 6 cierres y efecto de recuperación conservado |

Las precargas son configuración de escenario; los inputs efectivos y las emisiones se conservan por mes en `flows.json`. Tras cada cierre se contrastaron motor y journal, se desplazaron lags con el observado y se avanzó exactamente un mes. Generar otra vez devolvió el mismo observado pendiente. Las emisiones cerradas no cambiaron después de avanzar, comparar, rechazar o cambiar contexto. No se observaron predicciones RF públicas negativas en este ensayo.

La selección de escenario determina sus reglas mientras permanece seleccionada; no se implementó ni se inventó un final automático. PRODUCTO NUEVO fuerza abstención incluso al acumular meses mientras continúa ese escenario. La demanda latente de stockout es metadato interno, no etiqueta de entrenamiento ni venta exportada. Para cambiar escenario tras cierres se exige reset conforme a las reglas actuales.

El caso manual rechazó cierre incompleto sin cambiar reloj, historia ni RNG; al confirmar completitud permitió el cierre de 10 unidades. Cero es un observado válido y tiene pruebas existentes. No se completaron cierres con ventas ficticias.

## Ciclo de vida, aislamiento y seguridad

- Contratos Ross preservados: `create_runtime()`, `get_active_model()` y `predict(features)`, con estructura de respuesta existente. No se editó ningún contrato público.
- V1 se activa mediante acción explícita normal de Streamlit con motivo y verificación de identidad. ACTIVE y CANDIDATE son locales a sesión y par. La prueba nueva activó 1/5, comprobó que 2/5 no lo heredara, hizo rollback independiente y recuperó 1/5 sin alterar sus cierres. Otra sesión permaneció vacía e inactiva.
- El RNG es mutable e independiente por par. Su seed derivada depende de seed base/producto/tienda; repetir seed y operaciones reproduce resultados. Dos sesiones con seed idéntica pueden reproducir la misma serie: aislamiento no significa generar realizaciones distintas obligatoriamente.
- Reset crea contexto/UUID nuevos, restaura seed 42, reloj octubre 2026 y escenario NORMAL, conserva evidencia anterior y deja **V1 disponible, SIN ACTIVE**. Este criterio está aprobado expresamente en T17; no se activa por historial ni por exportación.
- La inferencia adicional se ejecutó con `RandomForestRegressor.fit`, `LinearRegression.fit` y ajuste del escalador bloqueados mediante guardas: **0 llamadas**. La suite cubre asimismo inferencia real del adaptador LR y orden de las cinco features.
- Reentrenamiento: solo doce meses nuevos cerrados y verificados posteriores a septiembre 2026; octubre–diciembre 2026 para reconstruir lags, enero–junio 2027 para entrenar y julio–septiembre 2027 reservados. Fixtures comprueban coherencia journal/motor, exclusión de predicciones/latente/ediciones como etiquetas, deduplicación, insuficiencia, reproducibilidad, aislamiento y ausencia de promoción automática. No se mezclan TRAIN/VALIDATION/TEST iniciales, ni sus valores TEST como lags.
- Candidato archivado `CAND-f3690f19436644959f2218cdc079110c`: 6 filas de entrenamiento, una serie, 3 observaciones reservadas. La comparación técnica existente/nuevamente ejercitada sobre esa reserva devuelve V1 MAE **0.927907** y candidato MAE **4.454167** (redondeados), con **INSUFFICIENT_EVIDENCE**. No constituyen superioridad estadística. Son datos distintos de TEST oficial y de los 48 cierres nuevos de esta auditoría.
- Se probó rechazo y bloqueo de intento con texto `APROBADO`. El protocolo real de promoción positiva sigue bloqueado en runtime e interfaz. La demostración de promoción positiva usa exclusivamente fixtures aislados de la suite; no habilita una opción de producción ni JSON de autorización.
- Rollback verifica identidad y recupera referencia previa sin reentrenar ni modificar predicciones cerradas. No hay ACTIVE global ni recuperación automática desde un registro editado/importado.

## Trazabilidad y exportación

Se contrastaron **442 eventos en 154 sesiones**, identificadores únicos, secuencias consecutivas por sesión, fecha UTC, encadenamiento `previous_sha256`, hash canónico y correspondencia de sesión/par. La evidencia inicial registra la verificación; las huellas finales y el inventario confirman que no cambió ningún byte histórico.

El ZIP `../organizacion/evidence/lifecycle_preservado.zip` tiene 442 entradas, CRC válido y correspondencia byte por byte con inventario y archivos actuales. SHA256: `2d4de62b2eaa99831ecab98ee4908a1b511f4f1022331bbb59cdef02eeade9a0`.

R49 registra disponibilidad, activación, candidato, comparación/decisión, rechazo, bloqueo, fixtures, rollback y reset sin duplicación por reruns. Las pruebas de integridad no convierten una cadena hash local en una firma externa contra reescritura total; el registro es evidencia, nunca autoridad de activación. Los nuevos eventos de fixtures se almacenaron en temporales; sus rutas originales dentro del resumen de ensayo no deben presentarse como archivos persistentes existentes.

R52 conserva envelope `h4-session-1` y extensión `h4-traceability-1`: seed real, estado RNG por par, reloj, escenarios, cierres y procedencia, revisiones, emisiones/identidad de modelo, contextos y decisiones, snapshots previos al reset. El campo legacy desconocido no se rellena con un seed supuesto; los valores nuevos explícitos están en la extensión. Datos hipotéticos, pendientes y latentes no se convierten en observados cerrados. Los hashes de exportación detectan coherencia interna, no autorizan cargar modelos. La suite cubre manipulación/rehash de JSON y evidencia previa corrupta, además de desconocidos históricos.

## Streamlit y matriz

Selectores, inputs, acciones mensuales, activación V1, historial, estados, comparación del candidato archivado, rechazo, rollback, reset y exportación fueron verificados técnicamente. **No se realizó revisión visual interactiva ni capturas en T21.** AppTest no certifica layout, legibilidad ni responsive.

Hallazgo de integración R30: existe `ui_panels.compare_reference_models()` y servicio real `reference_runtime`, pero la aplicación normal no llama al adaptador para presentar las tres salidas. La prueba del adaptador no demuestra esa conexión. Ross debe conectarlo, preservar etiquetas/abstenciones y validar la presentación. R23 requiere también mostrar baseline independiente de ACTIVE. R52 está técnicamente listo; falta aceptar visualmente su descarga/consumo. Los desgloses de errores agrupan tienda/producto/rotación/mes, pero no escenario (R73).

La matriz final clasifica **73 requisitos: 54 CUMPLIDOS, 11 PARCIALES, 3 NO VERIFICADOS, 0 NO CUMPLIDOS y 5 NO APLICA**. Aplicables 68; cumplimiento estricto **79,41 %**. No se otorga medio punto a parciales. R50 y R53 cambian por evidencia nueva explícita; R21/R49 permanecen cumplidos; R30/R52 permanecen parciales. Los pendientes se enumeran individualmente en el CSV y Markdown final, con responsables, cláusulas originales y pruebas actuales.

## Pruebas y comandos

Desde la raíz, entorno local existente:

```powershell
& .\ml\demand\.venv\Scripts\python.exe -B ml/demand/run_tests.py -v
& .\ml\demand\.venv\Scripts\python.exe -B ml/demand/run_tests.py --list
& .\ml\demand\.venv\Scripts\python.exe -B docs/H4/tareas_erika/tarea_21/evidence/validate_flows.py
git diff --check
git status --short
git diff --stat
```

Regresión: **464 aprobadas, 0 fallidas, 0 errores, 0 omitidas**, 438.656 segundos. Descubrimiento: 464 IDs únicos / 21 módulos; sin errores de importación. No se añadieron, eliminaron ni debilitaron tests de producto. El script adicional de auditoría está separado del conteo de la suite. AppTest requirió acceso a sockets locales del entorno; se ejecutó con aprobación automática. Sus avisos de contexto bare mode y widget no equivalen a fallos; el log completo se conserva. `git diff --check` terminó sin incidencias.

## Entrega selectiva a Git por Ross

**No se ejecutó staging.** Los snapshots `git_status_before.txt`, `git_status_after.txt` y `git_diff_stat.txt` son el estado real, no una lista de cambios hechos íntegramente en T21. Esta tarea solo añadió documentación/evidencia en `docs/H4`; no cambió código del módulo ni archivos protegidos.

`git diff --stat` al terminar: **9 archivos tracked, 687 inserciones y 791 eliminaciones**, todos cambios previos a esta auditoría; no incluye los nuevos documentos sin staging. `git diff --check` no informó problemas.

Antes de que un clon pueda reproducir la entrega, revisar e incorporar selectivamente:

1. Código Python H4, `run_tests.py`, `tests/` completo y su bootstrap; registrar los movimientos desde las tres rutas tracked antiguas sin perder los tests. Incluir módulos nuevos de runtime/contextos/lifecycle/reentrenamiento/comparación/referencias/exportación.
2. Configuración de dependencias, README, `.gitignore`, `.gitattributes` del módulo y configuración de simulación.
3. Catálogo, generadores versionados y directorios de datos/manifiestos requeridos, sin regenerarlos ni cambiar hashes.
4. `ml/demand/models/`, reportes y manifiestos de selección/evaluación/experimentos y LinearRegression; los joblib verificados son necesarios para inferencia sin entrenamiento.
5. Paquete archivado en `ml/demand/candidates/9958a7bc0be3447e88c6b4a331b05ace/CAND-f3690f19436644959f2218cdc079110c/` completo y `decisions/` oficiales necesarios; revisar la limitación de ruta antes de prometer ejecución en otra ubicación.
6. Documentación oficial, contratos, matrices, evidencia de integridad y respaldo ZIP/inventario de lifecycle; no subir `.venv`, cachés ni secretos. Las sesiones futuras locales ignoradas no sustituyen la evidencia preservada.

Un archivo presente pero untracked no está garantizado en un clon. No se certifica un clon limpio hasta versionar los elementos y ejecutar instalación/pruebas en otra ubicación. La política de portabilidad propuesta debe probarse sin alterar paquetes históricos.

## Correcciones, pendientes y conclusión

No se corrigió código productivo en T21. Solo se corrigió una suposición de codificación de lectura del nuevo generador de documentación de auditoría, antes de generar sus entregables; no afectó pruebas ni fuentes del producto.

Pendientes reales: conexión/presentación de referencias R23/R30; aceptación visual R11/R12/R34/R52/R56/R57; protocolo real previo R45 sin desbloquearlo; desglose por escenarios R73; procedencia incompleta de prompts R58; revisión/defensa conjunta R61/R62/R63. Además, probar portabilidad y clon limpio mediante solución revisada al path archivado y separadores. El checklist de Ross detalla evidencias exigidas y no contiene casillas marcadas como si estuvieran aprobadas.

Se recomienda cerrar **la auditoría T21**, mantener la entrega H4 parcialmente cumplida y abordar esos pendientes en tareas autorizadas. No se autoriza promoción real, reentrenamiento V1 ni nueva evaluación TEST. La validación integral final debe seguir después de la conexión de interfaz y la aceptación documentada de ambos responsables.
