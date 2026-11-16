# H4. Estado técnico vigente y reproducción

## Entrega a Erika y archivos grandes

La entrega del proyecto debe incluir código backend y frontend, scripts, contratos, catálogo congelado, datasets propios versionados, modelos guardados, reportes, selección, métricas y documentación. El modelo 4.0.0 funciona con su artefacto y snapshots publicados. No necesita descargar los RAW externos para realizar inferencias.

La regla de `.gitattributes` conserva los bytes de `ml/demand/` para no invalidar hashes al cambiar entre Windows y Linux. Conservarla junto con los manifiestos. En Windows conviene extraer el proyecto en una ruta corta para evitar errores de longitud de nombres.

Las carpetas `sources/external_raw/`, `sources/external_curated/` y `tmp/` permanecen locales. Contienen originales de terceros, archivos grandes o temporales. Se conservan los manifiestos, hashes, procedencia, reglas de procesamiento y reportes que explican su uso. M5 y Favorita tienen condiciones de acceso y redistribución. Cada integrante debe obtener los originales desde su cuenta autorizada si necesita reproducir el procesamiento. No publicar los originales ni sus copias procesadas por cambiarles el formato. Los archivos locales no deben borrarse por preparar la entrega.

Para preparar el entorno desde la raíz del proyecto, usar Python 3.11 y los archivos de dependencias conservados:

```powershell
python -m venv ml/demand/.venv
.\ml\demand\.venv\Scripts\python.exe -m pip install -r ml/demand/requirements-ui.lock.txt -r ml/demand/requirements-training.txt
```

Comprobación offline del artefacto y su historial, sin entrenamiento ni base de datos:

```powershell
Set-Location ml/demand
.\.venv\Scripts\python.exe -B -m unittest tests.test_calendar2026 tests.test_scenario_runtime -q
```

Backend y frontend conservan sus `package-lock.json`. Ejecutar `npm ci` en cada carpeta. Los archivos `.env` reales no forman parte de la entrega. Cada integrante configura su entorno a partir de los ejemplos existentes, sin compartir secretos por el repositorio.

La evaluación final de 4.0.0 ya terminó. Erika puede revisar el modelo, ejecutar inferencias y continuar el trabajo en una versión nueva. No sobrescribir el artefacto, regenerar este build o volver a usar su TEST para seleccionar configuraciones. Un entrenamiento posterior requiere otra versión, otro identificador de experimento y un protocolo de evaluación definido antes de entrenar. Los resultados y límites vigentes se describen en la sección siguiente.

## Versión activa 4.0.0. Historial hasta octubre y pronóstico de noviembre de 2026

La versión predeterminada de Escenarios es 4.0.0. Este estado reemplaza los párrafos históricos siguientes sobre 2.2.0 y 3.0.0. Explorar ventas y la gráfica de predicción comparten las observaciones sintéticas DEMO de enero a octubre de 2026. Noviembre es exclusivamente un pronóstico, sin target conocido. El simulador permanece separado.

Dataset: `data/repuestopro_v2/4.0.0/calendar-20261116-01/`. Artefacto: `models/v2/calendar-model-20261116-01/model.joblib`. Release, selección y evaluación final: `reports/v2/4.0.0/calendar-model-20261116-01/`. Generador versionado: `v2/calendar2026.py`. Inferencia fijada: `v2/calendar2026_runtime.py`. Pruebas: `tests/test_calendar2026.py`.

El modelo seleccionado por VALIDATION es RandomForestRegressor con error absoluto. TEST se evaluó una sola vez. MAE 10,2010, RMSE 18,4046 y R² 0,6201. No ejecutar otra evaluación ni borrar su registro de intento. Las métricas se leen de un archivo guardado. Las versiones anteriores están conservadas.

Para iniciar, ejecutar la API con `npm run dev` desde backend y Vite con `npm run dev` desde frontend. El backend utiliza el entorno Python configurado para predicciones. Iniciar sesión como ADMIN y abrir `/panel/prediccion?modo=escenarios`. El mes es noviembre de 2026. La otra pestaña permite explorar el historial hasta octubre.

Las 168 combinaciones tienen historia. La inferencia base produce una cifra en 136 y se abstiene en 32 por stock superior al máximo aprendido de 150 unidades. No transformar esos casos en cero ni alterar el stock para forzar cobertura. La guía oficial explica el split, los supuestos de noviembre y los límites de la simulación mensual: [documentación H4](../../docs/H4/H4_IMPLEMENTACION_MODELO_PREDICTIVO.md).

La versión predeterminada del administrador es **2.2.0**, con el dataset sintético congelado calibrated-20261115-01. El modelo aceptado utiliza tres lags y dos variables del calendario. Su selección y evaluación final están conservadas por hash. TEST ya fue evaluado una sola vez. No ejecutar otra evaluación, reentrenar o borrar su reserva para una demostración.

**La integración de replay está comprobada, pero no completa la interacción solicitada por el docente.** La pantalla permite producto, tienda y abril, mayo o junio de 2026. No permite cambiar precios, cotización, cantidades históricas o planes de recepción para comparar escenarios. El bosque seleccionado tampoco utiliza esas variables. El dataset contiene variables económicas y de stock, pero eso no demuestra que el modelo haya aprendido sus efectos. El alcance ampliado requiere un contrato de escenarios y nueva validación autorizada, conservando 2.2.0 como referencia. Consultar el [Plan V2 oficial](../../docs/H4/PLAN_DE_TRABAJO_V2.md).

## Contrato del alcance interactivo

[scenarios.v1.json](v2/contracts/scenarios.v1.json) es el contrato documental demand-scenarios-1.0.0. Define controles de precios, cotización, costos, cantidades, fechas y reposición, con reglas de disponibilidad, comparación y falta de soporte. Sus endpoints son propuestas todavía no implementadas. Once pruebas verifican estructura y ejemplos conceptuales, no sustituyen validación semántica o pruebas de API.

El [anexo 47 del Plan V2](../../docs/H4/PLAN_DE_TRABAJO_V2.md) asigna frontend y todo el dataset a Ross, backend y servicio del modelo a Erika. Incluye reposición explicativa en H4, sin compras o movimientos operativos. No generar un dataset nuevo o entrenar por ejecutar estas pruebas. La referencia 2.2.0 permanece intacta.

## Diccionario ampliado H4-R01

[dataset_dictionary.scenarios.v1.json](v2/contracts/dataset_dictionary.scenarios.v1.json) define las 48 entradas del contrato y las tablas propuestas, con tipos, unidades, fuentes, disponibilidad y faltantes. Está vinculado por hash al contrato de escenarios y al diccionario anterior, que no se modifica. El [anexo 48 del Plan V2](../../docs/H4/PLAN_DE_TRABAJO_V2.md) registra su cierre de diseño.

Las 16 variables ampliadas son candidatas. No se generó un dataset ni se aprobaron mecanismos económicos o features finales. No convertir el costo ya puesto dos veces, usar valores de cotización por defecto como historia o incluir resultados posteriores en X. R02 revisará fuentes y R03 justificará mecanismos antes de una nueva construcción autorizada.

## Modelo, API y límites

El puente [admin_prediction_v2.py](admin_prediction_v2.py) utiliza por defecto [inference_v2_2.py](v2/inference_v2_2.py). Los contratos vigentes son [selección](v2/contracts/selection.v2_2.json), [inferencia](v2/contracts/inference.v2_2.json) y [API administrativa](v2/contracts/admin_api.v2_2.json). Los endpoints son GET /api/predictions/catalog y POST /api/predictions/demand. Solo ADMIN tiene acceso. TIENDA e INVENTARIO reciben 403. Las consultas verifican snapshots y la versión activa, sin entrenar o consultar de nuevo TEST.

MAE TEST 2.2.0 = 9,2046 frente a 12,8690 del baseline. RMSE = 16,9085 y R² = 0,6466. No son métricas de ventas reales o una garantía comercial. La predicción se limita a cero si fuera negativa, rechaza valores no finitos y conserva decimales. El simulador Streamlit sigue separado. No hay compras o reposición automáticas.

## Arranque y recuperación explícita

Para la aplicación habitual, ejecutar desde backend: `npm run dev:backend`. En otra terminal, desde frontend: `npm run dev`. Abrir /panel/prediccion con ADMIN. Este arranque utiliza la base operativa configurada para autenticar y otros módulos. No equivale a una prueba aislada sin Neon. No ejecutar migraciones como parte del arranque de la demo.

La recuperación se selecciona exclusivamente en la terminal del servidor, mediante `DEMAND_RELEASE`. Solo se admiten 2.2.0 y 2.1.0. La variable no es una credencial. No cambia el artefacto, sus parámetros o los datasets. No se acepta desde la petición HTTP.

```powershell
# Desde backend, activar la versión predeterminada
$env:DEMAND_RELEASE = '2.2.0'
npm run dev:backend
```

Para recuperar, detener ese proceso con Ctrl+C, establecer `DEMAND_RELEASE` a `2.1.0` en la misma terminal y volver a iniciar. Actualizar las referencias de la pantalla. Aparecerá un aviso de recuperación explícita y la identidad 2.1.0. Sus métricas y snapshots pertenecen a esa versión. Para volver a 2.2.0, detener el proceso, restablecer la variable e iniciar nuevamente. También puede quitarse la variable con `Remove-Item Env:DEMAND_RELEASE` antes del arranque para utilizar el valor predeterminado.

Una falla no activa otra versión automáticamente. Un valor desconocido se rechaza. El servicio y el frontend verifican hash, selección, política y versión. Una respuesta o snapshot de otra versión no se mezcla con la consulta abierta. La prueba local recorrió 2.2.0 → 2.1.0 → 2.2.0 con inferencia real sobre VALIDATION y sin repetir TEST.

## Dashboard y desfase operativo

La inspección autorizada de Neon del 15 de noviembre de 2026 fue READ ONLY. Confirmó que Sale.status no existe allí, aunque el código lo requiere. También faltan campos de movimientos, devoluciones, pagos y facturas. No es un fallo del modelo de demanda. No quitar el filtro de ventas confirmadas ni devolver cifras inventadas para ocultarlo.

Después de esa inspección, el usuario limitó el trabajo a preparar y probar localmente. No se aplicaron cambios o nuevas consultas a Neon. En un fixture PostgreSQL local se reprodujo el 503 con ocho migraciones, se aplicaron las dos migraciones aditivas existentes y se obtuvo respuesta 200 para ADMIN, INVENTARIO y dos tiendas. Se conservaron las columnas y filas originales del fixture. El historial productivo contiene otros desfases y no permite ejecutar migrate deploy a ciegas. La reparación productiva continúa pendiente de rama de prueba, recuperación y reconciliación autorizada.

Se corrigieron además el alcance de conteos por tienda, los productos sin inventario en la vista global y el total de solicitudes pendientes, que antes dependía de una lista limitada a diez. TIENDA sin ubicación se rechaza antes de consultar. Estas correcciones no crean las columnas faltantes en producción.

## Evidencia histórica

Los apartados siguientes se conservan como historial de versiones y etapas anteriores. Sus estados pendientes, métricas y comandos describen ese momento. No sustituyen el estado vigente de esta introducción. Los reportes y artefactos históricos permanecen intactos.

# Historial técnico anterior

## Pantalla administrativa V2-11 completada para replay

PredictionsPage incluye producto, tienda, mes aprobado, horizonte fijo, gráfico con baseline, tabla y trazabilidad. demandView.ts valida catálogo, identidad, hash, política, historia y métricas antes de renderizar. Las consultas anteriores se cancelan del lado cliente y sus respuestas tardías se ignoran. No se permiten features o targets editados desde el navegador. Streamlit permanece separado.

Las métricas provienen del TEST ya guardado. No se recalcula al consultar. La pantalla explica origen sintético, ventas observadas frente a demanda total, límites de pedidos grandes y ausencia de reposición automática. Pasaron 12 pruebas, dos controles con respuesta real del bridge, tipos y build. La revisión visual utilizó fixtures explícitos a 1280 y 390 píxeles. El anexo 29 conserva evidencia y límites de esa revisión.

El anexo 30 explica la ampliación del dataset. El build 2.1.0 no es una concatenación de las cinco fuentes externas. Las pendientes requieren permisos, perfilado y compatibilidad antes de preparar otra versión. No se genera esa ampliación o se reutiliza el TEST cerrado en esta tarea.


## API administrativa conectada a V2

GET /api/predictions/catalog y POST /api/predictions/demand utilizan [admin_prediction_v2.py](admin_prediction_v2.py) y el artefacto aceptado. El contrato público está en [admin_api.v2_1.json](v2/contracts/admin_api.v2_1.json). Solo ADMIN puede consultar. La solicitud admite producto y tienda, con mes y snapshot opcionales. El servidor resuelve la referencia aprobada. Por defecto reproduce junio de 2026, con historia de marzo a mayo, no el mes actual.

El proveedor solo permite ACADEMIC_REPLAY de abril a junio. No consulta Neon o TEST, no entrena y no acepta features del cliente. Los errores distinguen entrada inválida, snapshot incompatible, ausencia de historia e indisponibilidad. Node verifica versión, hash, política y respuesta. No hay fallback a V1. Las métricas TEST se leen de la evidencia guardada sin recalcularlas. El simulador permanece separado.

El anexo 28 del plan conserva integración y pruebas. Pasaron 40 pruebas Python, diez HTTP y dos de pantalla, con tipos y build correctos. Los endpoints ahora sirven V2 y los archivos V1 permanecen intactos. No se habilitó LIVE_FORECAST o reposición automática. Los apartados siguientes conservan el estado anterior de implementación.


## Contrato local V2-09B verificado antes de conectar la API

[v2/inference.py](v2/inference.py) utiliza la selección y el artefacto aceptados, con política NONNEGATIVE_V1 y preprocesamiento congelado. [inference.v2_1.json](v2/contracts/inference.v2_1.json) fija esquemas, unidades, disponibilidad y versiones. Las 504 predicciones de VALIDATION coinciden exactamente con las guardadas. No se entrena o repite TEST.

El proveedor permite únicamente ACADEMIC_REPLAY de snapshots aprobados de abril a junio de 2026. La solicitud incluye versión, producto, tienda, mes y snapshot. No acepta features, target o rutas arbitrarias. El artefacto valida 17 columnas, pero el bosque consume las 14 seleccionadas. Las restantes son soporte de validación. Los errores no activan V1 como reemplazo.

La entrada de consola desde la raíz es `.\ml\demand\.venv\Scripts\python.exe -B ml/demand/v2/inference.py`, con un JSON por stdin. El ejemplo comprobado está en el anexo 27 del plan. No es un endpoint nuevo. La API administrativa sigue en V1, verificada sin BD. La conexión V2 corresponde a V2-10. No se activó un modelo global, LIVE_FORECAST o reposición automática.


## Selección fijada y TEST final consumido

El equipo aceptó absolute_forest-d4 para H4. [selection.v2_1.json](v2/contracts/selection.v2_1.json) fija el artefacto original, su hash, preprocesamiento, 14 features, política NONNEGATIVE_V1 y autorización única antes de abrir TEST. La evaluación final obtuvo MAE 7,6327, RMSE 15,4253 y R² 0,6429 en 504 filas. El baseline obtuvo MAE 11,7639. La suma prevista queda 15,46 % por debajo de la observada, con 18 errores superiores a 40 unidades. No existe validación comercial.

El [resultado completo](reports/v2/2.1.0/expanded-20261115-01/final_test/result.json) conserva el evento único. v2/final_evaluation.py reserva final_test para todo el build antes del acceso y bloquea repeticiones, incluso después de un fallo. No borrar la reserva o intentar otra evaluación. La rutina comparadora original continúa rechazando TEST. Se registró una carga, una llamada de predicción y cero ajustes. Las pruebas de cierre usan evidencia guardada o fixtures y no repiten la predicción de TEST.

El anexo 26 del plan registra artefacto, política y alcance. V2-08 académico queda cerrado. No se creó un ACTIVE ni se integró el candidato al panel. Sigue pendiente V2-09B con Erika. Los apartados siguientes conservan la historia de selección. Los estados de manifests anteriores son históricos y no se reescriben para reflejar la evaluación posterior.


## Recomendación previa a la aceptación, conservada sin cambios de modelos

El anexo 25 del plan recomienda absolute_forest-d4 para H4 por el criterio principal MAE, tras revisar los siete productos pendientes y los errores grandes. El [reporte pareado](reports/v2/2.1.0/expanded-20261115-01/runs/alternatives-20261115-01/candidate-review-20261115-01/paired_review.json) conserva los casos por tienda y mes. recommendation.json identifica el artefacto propuesto. Se mantiene sin promoción y TEST sigue reservado.

El bosque absoluto mejora MAE frente a la ruta, pero tiene más errores extremos y subestima la suma observada un 17,27 %. La ruta se conserva como alternativa, sin declarar aceptación comercial. Esta revisión utiliza predicciones guardadas, sin reentrenar. VALIDATION reutilizado es evidencia exploratoria. No se recomiendan compras automáticas. Los apartados siguientes conservan las comparaciones previas.


## Comparación vigente de alternativas 2.1.0

El run [alternatives-20261115-01](reports/v2/2.1.0/expanded-20261115-01/runs/alternatives-20261115-01/comparison.json) compara 14 configuraciones con folds de TRAIN y nueve referencias finales en VALIDATION. El bosque con error absoluto obtiene MAE 7,6174 y mejora baja rotación, pero RMSE 15,1752 es mayor que el 14,6629 del bosque anterior. La ruta de mediana en baja rotación obtiene MAE 8,2329 y RMSE 14,6514. Ninguna se activó.

El componente experimental está en v2/alternatives.py, separado del adaptador y runner originales. El contrato alternatives.v2_1.json fija este run y sus hashes. No se añaden columnas a los CSV. TSB utiliza solo meses cerrados. La ruta de baja rotación se define con TRAIN. Los artefactos están separados en models/v2/alternatives-20261115-01 y el log en el subdirectorio del run. Repetir el identificador se rechaza antes de ajustar modelos. El anexo 24 del plan explica límites, alternativas y pendientes. TEST sigue reservado. La reutilización de VALIDATION hace que esta comparación sea exploratoria.


## Primer entrenamiento académico 2.1.0, referencia conservada

El run [training-20261115-01](reports/v2/2.1.0/expanded-20261115-01/runs/training-20261115-01/comparison.json) completó 102 ajustes y comparó 13 opciones en VALIDATION, incluido el baseline. RandomForest con 14 features obtuvo MAE 8,538, frente a 11,046 del baseline y 8,790 del mejor modelo lineal. El estado es REVIEW_REQUIRED por deterioro de algunos productos y grupos de baja rotación. No se promovió ni se evaluó TEST. Los resultados corresponden exclusivamente al dataset sintético.

El candidato está en models/v2/training-20261115-01, junto con el estado de preprocesamiento y su manifest. El log propio está en reports/v2/2.1.0/expanded-20261115-01/experiments.csv. No se modificaron V1, datasets o RAW. El permiso de entrenamiento fue temporal y runner.v2_1.json vuelve a mantener false. El anexo 22 del plan registra esta entrega. Los apartados de preparación siguientes conservan su alcance anterior.


La revisión posterior está en el anexo 23 del plan y en el subdirectorio diagnosis-20261115-01 del run. Explica la sobreestimación de ceros, cambios de volumen y diferencias entre modalidad sin ventas y cobertura parcial. Conserva errores por las 504 filas y los 17 productos que empeoran. No hubo nuevos ajustes, cambio de política, promoción o acceso a TEST. La decisión del equipo continúa pendiente.

## Preparación previa de la rutina 2.1.0, sin entrenamiento

[v2/experiments.py](v2/experiments.py) conecta el adaptador con X e y alineados por producto, tienda y mes. Rechaza claves duplicadas, resultados faltantes o cantidades inválidas. Mantiene tres folds mensuales dentro de TRAIN, VALIDATION para selección y TEST reservado. Construye pipelines nuevos por fold. Los controles de comparación, fallos, empates, errores por grupo y registro se prueban con dobles que no aprenden relaciones.

Desde la raíz, la preparación segura se ejecuta con:

```powershell
.\ml\demand\.venv\Scripts\python.exe -B ml/demand/v2/run_experiments.py --run-id IDENTIFICADOR_NUEVO
```

Publica únicamente run_plan.json bajo reports/v2/experiment_runner. Lee ocho particiones para comprobar alineación, sin ajustar preprocesadores, entrenar, predecir o registrar métricas de modelos. No crea experiments.csv ni artefactos. Rechaza identificadores existentes. El contrato runner.v2_1.json mantiene model_training_authorized en false. La acción execute está bloqueada antes de cargar targets o construir modelos. No existe una opción de CLI para saltar ese bloqueo.

El anexo 21 del plan registra esta integración. La futura ejecución autorizada utilizará su propio log V2, conservará métricas originales y corregidas de predicciones negativas, además de requerir revisión si mejora globalmente pero empeora grupos. Falta ejecutar y validar modelos reales, revisar el artefacto con Erika y evaluar TEST al final. No existe modelo 2.1 entrenado.

## Adaptador 2.1.0 implementado

[v2/preprocessing.py](v2/preprocessing.py) ofrece DemandPreprocessor y load_feature_partition. Recibe las 17 features y mes_objetivo como contexto. Selecciona grupos aprobados, imputa medianas y crea indicadores fijos. La categoría utiliza vocabulario TRAIN con UNKNOWN. La ruta lineal escala solo variables numéricas y la ruta de bosque no escala. Los IDs quedan en el índice, fuera de la matriz.

El fit acepta únicamente prefijos TRAIN aprobados y completos. Con el índice del loader exige cohortes producto-tienda completas por mes. Cada instancia se ajusta una vez. Transform y la restauración JSON mantienen parámetros y columnas. El contrato está en v2/contracts/preprocessing.v2_1.json. Los tests ajustan preprocesadores solo con fixtures, leen el build sin ajustarlo y bloquean el fit de regresores. El anexo 20 conserva la entrega del adaptador. La integración posterior está en el anexo 21. El entrenamiento posterior se registra en el apartado de resultado vigente.


## Estado vigente: dataset ampliado 2.1.0

El [build expanded-20261115-01](data/repuestopro_v2/2.1.0/expanded-20261115-01/manifest.json) está publicado y validado. Contiene cotizaciones con edades calculadas desde eventos, ventas mayoristas grandes efectivamente atendidas y trazabilidad diaria de stock. Las 17 features varían en TRAIN. El [plan de experimentos 2.1](v2/contracts/experiments.v2_1.json) conserva cero ajustes y ninguna autorización de entrenamiento. Los registros siguientes describen versiones anteriores y conservan su fecha.

Para otra generación autorizada: `python ml/demand/v2/generate_expanded.py --build-id IDENTIFICADOR_NUEVO`. Para revisión: `python ml/demand/v2/validate_expanded.py --build-id ID --run-id ID_NUEVO --expected-manifest-sha256 HASH_REGISTRADO`. No se sobrescriben builds. La versión 2.0.0 mantiene sus scripts y contratos. La evidencia ampliada está en reports/v2/2.1.0/expanded-20261115-01/validation-20261115-01. En ese estado de preparación todavía no había modelo 2.1 ni experimentos ejecutados. La ejecución posterior está descrita al inicio. No se escribió en Neon ni se alteraron originales externos.


## Preparación registrada antes de ampliar a 2.1.0

La [preparación V2-08](v2/contracts/experiments.v2.json) define seis grupos de 5 a 16 features, excluyendo explícitamente la edad constante sin cambiar el CSV. Se fijaron tres folds mensuales y una comparación futura de baseline, modelo lineal y bosque. El [preflight](reports/v2/experiments_preparation/experiments-preparation-20261114-02/preflight.json) registra cero ajustes. Los casos de cotización variable y abastecimiento de mayoristas grandes son prototipos de la futura variante, no otro dataset. Reproducir con `python ml/demand/v2/experiment_preparation.py --run-id IDENTIFICADOR_NUEVO`. No entrena ni crea logs de experimentos ficticios. El anexo 18 del plan explica decisiones y pendientes.


El build academic-20261114-03 aprobó integridad y política offline. Los [reportes de revisión](reports/v2/2.0.0/academic-20261114-03/validation-20261114-02/closure.json) conservan 57 fixtures de escenarios y ocho combinaciones. Esto no significa que el generador haya ejecutado los 57 escenarios, que el backend esté certificado o que se haya medido precisión comercial. La antigüedad de cotización es constante en TRAIN y el volumen observado llega a nueve unidades mensuales. El [anexo 17](../../docs/H4/PLAN_DE_TRABAJO_V2.md#17-validación-de-datos-y-política-offline-v2-07) explica el alcance.

Para revisar sin modificar datos: `python ml/demand/v2/validate.py --build-id academic-20261114-03 --run-id IDENTIFICADOR_NUEVO`. Publica solo reportes V2, sin ajustar scalers, generar otro dataset o entrenar. El build conserva su estado original de construcción, mientras la revisión posterior se acredita mediante hashes externos. El entrenamiento continúa sin autorización.


## Construcción registrada en V2-06

Existe el primer build [2.0.0/academic-20261114-03](data/repuestopro_v2/2.0.0/academic-20261114-03/manifest.json), académico y sintético. Tiene 4.032 filas mensuales y 3.528 supervisadas. Su estado es BUILT_PENDING_V2_07_NOT_FOR_TRAINING. No hay modelo V2 entrenado. El [anexo 16 del plan](../../docs/H4/PLAN_DE_TRABAJO_V2.md#16-primer-build-académico-v2-06) registra alcance, límites, pruebas y siguiente fase.

Para reproducir sin sobrescribir: ejecutar desde la raíz `python ml/demand/v2/generate.py --build-id IDENTIFICADOR_NUEVO`, usando el entorno Python del módulo. El proceso usa tmp, publica exclusivamente en data/repuestopro_v2/2.0.0 y nunca escribe en V1, RAW o Neon. Los CSV son reproducibles con seed 42. El manifest y los checksums conservan configuración, fuente de catálogo, generador, split y procedencia. No ejecutar entrenadores V1 contra estos archivos.

Los apartados siguientes conservan registros anteriores de la estructura y de V1. Sus afirmaciones sobre etapas todavía no ejecutadas deben leerse según la fecha de cada registro.


## Estructura base V2. Registro del 11 de noviembre de 2026

Esta ampliación prepara rutas, contratos y trazabilidad. No publica un dataset V2 ni un modelo V2. El reparto vigente es Erika en backend y Ross en frontend y dataset. El [Plan de trabajo V2](../../docs/H4/PLAN_DE_TRABAJO_V2.md) define las tareas posteriores.

| Ruta | Uso y convención |
|---|---|
| `sources/external_raw/` | Originales inmutables. No renombrar, convertir, limpiar ni mezclar. Cada hash corresponde a los bytes originales |
| `sources/manifests/<source_id>/<snapshot_id>.json` | Un manifest por fuente y snapshot, con inventario completo y hashes por archivo |
| `sources/external_curated/<source_id>/<snapshot_id>/<processing_version>/` | Futuras transformaciones reproducibles. Hoy no hay archivos procesados |
| `data/repuestopro_v2/<dataset_version>/<build_id>/` | Futuro dataset publicado. No se creó ningún build |
| `reports/v2/<dataset_version>/<build_id>/` | Estadísticas, calidad, distribuciones y experimentos de ese build. No copiar el registro V1 |
| `models/v2/<run_id>/` | Modelos futuros. No contiene modelos V1 copiados |
| `v2/` | Código separado y contratos. No duplica generadores o entrenadores V1 |
| `tmp/<run_id>/` | Descarga autorizada futura, extracción auxiliar, conversiones, profiling temporal y construcción. No utilizar RAW, data, reports o models como temporales |

El flujo aprobado es **fuente original → RAW → manifest, hash, procedencia y licencia → revisión de fuente → procesamiento → curated → perfil estadístico → calibración o transformación → dataset V2 → validación → reportes → experimentos → modelo**. No se pasa directamente de RAW a entrenamiento. Los datos propios auditados podrán incorporarse como otra procedencia identificada cuando sean utilizables. Una fuente externa no se convierte en ventas reales de RepuestoPro cambiando sus IDs.

Hay cinco fuentes registradas y 136 archivos originales. En el registro inicial todas quedaron en PENDING_SOURCE_REVIEW. La revisión V2-04B está en la [matriz de procedencia](reports/v2/source_provenance_matrix.json). Monash y UCI pasan a APPROVED_FOR_PROFILING exclusivamente académico, con atribución. Las otras tres continúan pendientes. No se ejecutó profiling. Los manifiestos no certifican completitud ni adquisición real. Los campos no demostrados se guardan como null. UNKNOWN se utiliza para completitud no certificada. registered_at no es la fecha de descarga. obtained_at permanece desconocida. La licencia del paquete R no se atribuye automáticamente a sus datasets. Las inspecciones locales se limitaron a documentación, cabeceras y metadata de contenedores. Los 7z no se extrajeron ni listaron.

En una fuente de un archivo, sha256 representa sus bytes. En una carpeta de varios archivos, sha256 tiene hash_scope FILE_INVENTORY_SHA256: identifica el inventario ordenado de ruta relativa, tamaño y hash por archivo, codificado como JSON canónico UTF-8. files[].sha256 sigue siendo siempre el hash de bytes originales. inventory_sha256 identifica ese inventario también en fuentes de un archivo. Los snapshot_id son identificadores de contenido, no fechas de obtención. source_id puede normalizar acentos para su uso como identificador, pero raw_root conserva exactamente el nombre original.

El contrato [source_manifest.schema.json](v2/contracts/source_manifest.schema.json) define RAW_REGISTERED, PENDING_SOURCE_REVIEW, APPROVED_FOR_PROFILING, CURATED y REJECTED. El registrador crea fuentes pendientes, nunca las aprueba por existencia. La validación de metadata admite aprobación para profiling solo con licencia y uso académico verificados, evidencia y decisión expresa. CURATED no se admite en esta fase. La ampliación de campos de procedencia es opcional y compatible con los manifests iniciales. Se preservaron sus copias anteriores en tmp/provenance-20261111-01/manifests_before. Mantener la identidad del snapshot y sus hashes al actualizar la revisión, sin cambiar RAW.

Los contratos [dataset_schema.schema.json](v2/contracts/dataset_schema.schema.json) y [curated_manifest.schema.json](v2/contracts/curated_manifest.schema.json) describen columnas y transformaciones futuras. Cada columna requiere name, type, unit, role, source, nullable, availability_time, description y estado de aprobación. Los roles son IDENTIFIER, FEATURE, TARGET, METADATA y CONTROL. [dataset_columns.reference.json](v2/contracts/dataset_columns.reference.json) es una referencia DRAFT de las nueve columnas V1.1, no el schema final V2. [candidate_groups.json](v2/contracts/candidate_groups.json) mantiene precios, moneda, modalidad, disponibilidad, categoría y tiempos como candidatos sin fuente aprobada.

Toda transformación futura debe identificar manifest original, archivos y hashes originales, processing_version, script y hash del script, parámetros, fecha de ejecución y archivos de salida con sus hashes. Todavía no se ejecuta ninguna. Un build futuro debe contener base_mensual.csv, dataset_supervisado.csv, escenarios_metadatos.csv, manifest.json, schema.json, split_manifest.json, validation.json y checksums.sha256. No hay CSV vacíos ni resultados inventados. Los reportes futuros serán estadisticas.json, calidad.json, distribuciones.csv y experiments.csv, exclusivamente bajo reports/v2.

La estructura se prepara con v2.structure. Su escritor de registro solo admite archivos nuevos en manifests o tmp. La reserva de build exige versión y build_id, rechaza sobrescrituras y no publica archivos. No se llamó para crear builds reales. Los tests utilizan únicamente carpetas temporales dentro de tmp. El registro usa jsonschema ya disponible en el entorno H4, sin instalar dependencias ni resolver referencias por Internet.

**Reutilización analizada, sin refactor V1:**

| Clasificación | Componentes y condición |
|---|---|
| REUTILIZABLE SIN CAMBIOS | Lógica de métricas de ml_pipeline.evaluate, baseline por lag1 y utilidades de calendario, después de validar el contrato de entrada. No implican usar el resto del pipeline V1 |
| REUTILIZABLE CON ADAPTADOR | Carga de catálogo, cálculo de hash normalizado para referencias textuales, métricas por grupos y lógica de separación temporal. V2 debe conservar procedencia, claves, versiones y cortes propios. Los hashes RAW usan bytes exactos, no normalización LF/CRLF |
| NO REUTILIZABLE PARA V2 tal como está | validate_frame exige nueve columnas, fechas y catálogo V1.1. TrainStandardizer exige cinco features. Cargadores, periodos, conteos, entrenadores, selección, TEST y runtimes fijan contratos, rutas o hashes V1. No apuntarlos a V2 ni modificar su evidencia |

El análisis no ejecutó estos componentes. Las rutas y utilidades existentes pueden servir como referencia, pero no se importaron generadores, entrenadores ni validadores históricos. La evidencia de esta preparación está en `tmp/structure-20261111-01/`, no en reportes oficiales o históricos. Puede contener inventarios extensos, hashes y logs de tests, no estadísticas de ventas. Conservarla para revisar el cierre antes de una limpieza futura autorizada de temporales.

## Integración revisada el 10 de noviembre de 2026

El reporte vigente está en la sección 20 de la [guía oficial](../../docs/H4/H4_IMPLEMENTACION_MODELO_PREDICTIVO.md). La aplicación normal incorpora COMPARAR TRES REFERENCIAS, con baseline y LR independientes de ACTIVE, además del desglose de errores por escenario. La suite integrada aprobó 473 pruebas. Se verificaron modelos reales, seis cierres, monitoreo, comparación, rollback y descarga en navegador de escritorio y pantalla estrecha. No se repitió el TEST oficial ni se reentrenó V1.

El entorno local de esta revisión usa Python 3.11.9 y las versiones ya declaradas en los requisitos. La observación Python 3.11.0 de la organización anterior describe el equipo auditado entonces. No hace falta regenerar artefactos para adaptar rutas. La localización del único candidato archivado se resuelve dentro del checkout después de comprobar su manifiesto fijado por hash. Los archivos originales no cambian. La aceptación del equipo y la promoción real de candidatos siguen pendientes.

La [guía oficial](../../docs/H4/H4_IMPLEMENTACION_MODELO_PREDICTIVO.md) define el diseño. Este apartado contiene los comandos actuales; el texto anterior se conserva abajo como histórico. La organización no completa funcionalidades de T20 ni cambia la matriz H4.

## Estructura actual

```text
ml/demand/
  tests/                   21 módulos test_*.py y fixtures
  run_tests.py             runner desde cualquier directorio
  data/escenarios_v1_1/     dataset oficial y manifiestos
  data/escenarios_v1/       versión histórica
  versions/                generador anterior
  models/                  LR y RF V1 congelados, indispensables
  reports/                 experimentos, selección y TEST único
  candidates/              candidato incremental archivado y manifiesto
  decisions/               comparación y rechazo originales
  lifecycle/               eventos locales, ignorados pero preservados
  generate_synthetic.py    generador separado del motor dinámico
  ml_pipeline.py           features, baseline, split y preprocesamiento
  train_*.py               entrenadores conservados
  demand_engine.py         escenarios, reloj y seed por par
  demand_runtime.py        V1 e inferencia local
  reference_runtime.py     trabajo de referencia LR de T20
  retraining.py            ensayo incremental independiente
  model_comparison.py      comparación y bloqueo de promoción real
  lifecycle_registry.py    evidencia del ciclo
  session_export.py        exportación versionada
  streamlit_app.py          interfaz local
  ui_*.py                  contratos, diario, análisis y paneles
```

La [lista completa de los 21 traslados](../../docs/H4/tareas_erika/organizacion/evidence/test_moves.json) relaciona cada ruta anterior con la nueva. Se conservan nombres de clases, métodos, aserciones y fixtures. Los informes y JSON fechados mantienen sus rutas históricas: `ml/demand/test_NOMBRE.py` corresponde ahora a `ml/demand/tests/test_NOMBRE.py`.

## Entorno y ejecución desde PowerShell

Desde la raíz, solo si falta el entorno:

```powershell
py -3.11 -m venv ml/demand/.venv
$h4Python = Join-Path (Get-Location).Path 'ml/demand/.venv/Scripts/python.exe'
& $h4Python -m pip install -r ml/demand/requirements-ui.lock.txt
& $h4Python -m pip install -r ml/demand/requirements-training.txt
```

No recrear un entorno funcional innecesariamente. El entorno auditado usa Python 3.11.0, NumPy 2.4.6, pandas 3.1.0, scikit-learn 1.9.1, SciPy 1.17.1 y joblib 1.6.0. Conservar versiones y configuraciones: seed 42 no garantiza por sí sola bytes idénticos entre plataformas, fechas y serializaciones.

Suite completa y descubrimiento:

```powershell
& $h4Python -B ml/demand/run_tests.py
& $h4Python -B ml/demand/run_tests.py --list
& $h4Python -B -m unittest discover -s ml/demand/tests -t ml/demand -p 'test_*.py'
```

`-t ml/demand` carga una sola identidad `tests.test_*` y permite imports relativos entre fixtures. No ejecutar los archivos de test como scripts. Para un subconjunto: `& $h4Python -B ml/demand/run_tests.py -p 'test_*ui*.py' -v`.

`tests/__init__.py` deriva las rutas de su archivo y redirige únicamente el destino de eventos de AppTest a un `TemporaryDirectory`, limpiado al terminar el proceso. Los fixtures conservan sus modelos/datasets/candidatos temporales. No se modifica la lógica productiva. La colección inicial real fue de 464 casos únicos; los IDs solo añaden el prefijo `tests.`. Los logs antes/después están en [../../docs/H4/tareas_erika/organizacion/evidence](../../docs/H4/tareas_erika/organizacion/evidence).

La suite ajusta modelos de fixtures temporales autorizados, sin reentrenar V1 ni repetir TEST oficial. AppTest requiere sockets locales y permiso del entorno si el sandbox los bloquea. Sus resultados no acreditan revisión visual.

Validación de esta organización: **464/464 antes (172.661 s) y 464/464 después (202.571 s)**, sin casos omitidos, duplicados ni fallidos. Los 29 archivos protegidos y los 442 registros originales permanecen íntegros. Los módulos productivos, incluido el trabajo en curso de T20, conservan exactamente sus bytes previos; únicamente los tests y un helper de fixtures cambiaron imports.

Streamlit:

```powershell
& $h4Python -B -m streamlit run ml/demand/streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Abrir http://127.0.0.1:8501. V1 requiere activación explícita con motivo, por sesión/par. Reset no reactiva modelos automáticamente. La promoción real de candidatos permanece bloqueada y los JSON son evidencia sin autoridad.

## Archivos indispensables para un clon limpio

Deben acompañar la entrega manual a Git, sin ignorarlos:

- Módulos Python, tests, generadores, entrenadores, selección, inferencia, reentrenamiento, interfaz y locks/dependencias.
- `catalog_reference.json`, dataset 1.1 completo y manifiestos, versión anterior y generador histórico.
- `models/linear_regression_candidate.joblib` y `models/random_forest_candidate.joblib`, aproximadamente 4,3 MB entre ambos. No regenerar un modelo para eludir una huella.
- Los tres archivos de `reports`: `experiments.csv`, `v1_selection_manifest.json` y `v1_test_evaluation.json`.
- Los cinco archivos del candidato `CAND-f3690f19436644959f2218cdc079110c` y sus dos decisiones originales, usados por pruebas/comparaciones.
- Documentación/evidencias referenciadas por las pruebas en `docs/H4`, incluidos snapshots de integridad y originales del catálogo.

Parte de estos archivos sigue sin seguimiento. Esta tarea no hace `git add`, commit ni push: un clon de lo ya publicado no los recibirá hasta que Ross incorpore manualmente la entrega. La disponibilidad local no equivale a respaldo remoto. No se añade Git LFS.

La nueva `.gitattributes` del módulo preserva los bytes de paquetes y metadatos con referencias binarias en `models`, `reports`, `candidates` y `decisions`. No modifica los datos ni sustituye `content_sha256()` normalizado. V1 conserva la huella oficial `3e3cf6d1ef75567a69ff6f604bcb2a93f629f6d0fa503bdf734f3c6118c03883`; las huellas binarias existentes son adicionales. Algunos snapshots binarios de textos históricos reflejan los CRLF del entorno Windows auditado.

**Portabilidad corregida el 10 de noviembre:** el manifiesto conserva la ruta absoluta histórica, pero archived_run() ya no la usa como autoridad de ubicación. Solo el paquete de identidad y hash fijados en código se localiza dentro del checkout y verifica sus archivos antes de cargar el modelo. Una copia a otra carpeta está cubierta por regresiones. Runtime V1 y entrenadores conservan sus rutas relativas. Esto no constituye una prueba de clon limpio en todos los sistemas operativos.

## Preparación de datos y entrenamiento futuro

Los datos oficiales ya están preparados; no regenerarlos durante la ejecución normal. TRAIN: enero 2025–marzo 2026 (2520 filas), VALIDATION: abril–junio 2026 (504), TEST: julio–septiembre 2026 (504). Se conservan tres lags, dos features de calendario y las configuraciones originales; IDs/escenario no son features. LR ajusta su preprocesador solo en TRAIN.

Una futura reproducción autorizada del generador debe usar una carpeta nueva:

```powershell
& $h4Python -B ml/demand/generate_synthetic.py --output RUTA_NUEVA
```

**No ejecutar los entrenadores con sus destinos por defecto:** apuntan a artefactos/reportes oficiales. Plantilla para un futuro experimento separado, no ejecutada durante esta organización:

```powershell
@'
import sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path('ml/demand').resolve()))
import ml_pipeline as mp
import train_linear_regression as lr
import train_random_forest as rf
out = Path('ml/demand/reproducciones') / uuid.uuid4().hex
out.mkdir(parents=True, exist_ok=False)
registry = out / 'experiments.csv'
mp.run_baseline(registry_path=registry)
lr.run_experiment(registry_path=registry, artifact_path=out / 'linear_regression.joblib')
rf.run_experiment(registry_path=registry, artifact_path=out / 'random_forest.joblib')
print(out)
'@ | & $h4Python -B -
```

Esta plantilla registra resultados/versiones en otra carpeta y no sustituye V1 ni autoriza una activación. Se conserva la lógica de selección para futuros experimentos separados. No llamar a `evaluate_v1.run_final_evaluation()` sobre el TEST oficial ya evaluado; un experimento nuevo exige su propio protocolo.

El ensayo incremental utiliza `RetrainingSession(engine.session_id, output_root=RUTA_NUEVA).train(engine, journal)` con observados nuevos concordantes y cerrados: octubre–diciembre 2026 como historia, enero–junio 2027 para seis targets y julio–septiembre 2027 reservados. No usa predicciones, latentes o TEST inicial como etiquetas/lags de ajuste. `example_retraining.py` conserva una demostración explícita. No se ejecutó ahora. El resultado es CANDIDATE independiente, nunca promoción automática.

## Git y respaldo de evidencia local

Las reglas existentes ya cubren entornos, bytecode y cachés Python. La única nueva exclusión de datos H4 es `/ml/demand/lifecycle/`: eventos locales por sesión, no necesarios para arrancar un clon. **Los 442 originales permanecen físicamente intactos.** No se presupone que todos sean de tests o que su evidencia única sea regenerable.

Antes de excluirlos se creó [lifecycle_preservado.zip](../../docs/H4/tareas_erika/organizacion/evidence/lifecycle_preservado.zip) con los 442 JSON, más [inventario SHA256](../../docs/H4/tareas_erika/organizacion/evidence/lifecycle_inventory.json). Ambos están fuera de las reglas de exclusión y deben acompañar la entrega manual. Se preserva evidencia sin mostrar cada evento por separado en Git. No se ignoran modelos, candidatos, reportes, decisiones ni documentación.

Para una copia adicional:

```powershell
Expand-Archive -LiteralPath docs/H4/tareas_erika/organizacion/evidence/lifecycle_preservado.zip -DestinationPath RUTA_NUEVA_DE_RESPALDO
```

Usar un destino nuevo y comprobar el inventario, sin sobrescribir registros vivos. Extraer evidencia no activa modelos. La exportación de sesiones está descrita en [R52](../../docs/H4/H4_EXPORTACION_SESION_R52.md).

## Documentación anterior conservada (histórica)

Lo siguiente describe entregas anteriores; para comandos actuales usar los apartados de arriba.

### Artefactos locales de demanda H4

La única guía oficial de diseño, columnas, fases, evaluación y límites es [H4_IMPLEMENTACION_MODELO_PREDICTIVO.md](../../docs/H4/H4_IMPLEMENTACION_MODELO_PREDICTIVO.md).

La versión guardada vigente está en [data/escenarios_v1_1](data/escenarios_v1_1). Se conservan [data/escenarios_v1](data/escenarios_v1) y el generador anterior en [versions/generate_v1_0_0.py](versions/generate_v1_0_0.py). El catálogo de referencia está en [catalog_reference.json](catalog_reference.json).

El generador y sus pruebas requieren Python 3.10 o posterior, sin dependencias externas. Su manifiesto conserva la versión usada en la generación guardada. Para una reproducción futura autorizada, desde la raíz se utiliza `python ml/demand/generate_synthetic.py --output RUTA_NUEVA`, sin sobrescribir versiones anteriores. Las pruebas se ejecutan con `python -m unittest discover -s ml/demand -p "test_*.py" -v` y algunas generan copias temporales.

Las tareas 1–9B añadieron pipeline, candidatos entrenados, selección congelada V1 y su evaluación TEST única. No hay conexión a bases de datos. No se mezclan metadatos, inválidos o grises con el CSV supervisado.

La interfaz de Ross está en streamlit_app.py, con ui_runtime.py para conectar inferencia y registrar emisiones, ui_analysis.py para métricas y monitoreo y ui_panels.py para las vistas. Incluye edición, observados posteriores, errores por grupos, drift demostrativo y comparación visual. DemandSession conserva los ocho escenarios y reloj mensual. No se muestran resultados de ejemplo como si fueran modelos reales.

Desde la raíz, con Python 3.11:

```powershell
python -m venv ml/demand/.venv
.\ml\demand\.venv\Scripts\python.exe -m pip install -r ml/demand/requirements-ui.lock.txt
.\ml\demand\.venv\Scripts\python.exe -m streamlit run ml/demand/streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Crear el entorno e instalar solo es necesario la primera vez. Para probar exclusivamente esta interfaz sin regenerar datasets:

```powershell
.\ml\demand\.venv\Scripts\python.exe -m unittest discover -s ml/demand -p 'test_*ui*.py' -v
```

El motor DemandSession implementa generación y avance mensual. demand_runtime.py implementa create_runtime(), get_active_model() y predict(features), sin entrenamiento ni conexión a Neon. Cada sesión comienza sin ACTIVE: V1 permanece SELECTED_FROZEN_NOT_ACTIVE. PREDECIR solo se habilita con una referencia local compatible. Registrar observados o descargar una sesión no modifica el dataset.

Tarea 10: la promoción futura se ejecuta explícitamente mediante promote_v1(reason), después de autorización. No hay botón de activación ni promoción automática. rollback(reason) restaura la referencia anterior, incluso el estado inicial sin modelo. Estos cambios son locales en memoria; no existe un ACTIVE global persistido. RECONECTAR RUNTIME y RESTABLECER EDICIÓN descartan la referencia local, sin cambiar emisiones ya conservadas en otros objetos o sesiones. Las pruebas de promoción usan artefactos temporales.

La carga exige la huella binaria fijada en código tras auditoría y la huella normalizada del manifiesto histórico. Se verifican antes de joblib.load y se deserializan los mismos bytes leídos. El hash binario identifica todo el paquete serializado, incluido modelo y configuración; no se aceptan uploads. La referencia fijada protege frente a sustitución del archivo o edición aislada del manifiesto, bajo la confianza en el código del repositorio. No constituye firma externa del autor original. Los contratos de Ross no cambian. Instalar también requirements-training.txt en el entorno local para disponer de las dependencias de inferencia; los locks de UI se conservan.

La referencia source_document del catálogo conserva la ruta histórica. Su original exacto y el mapa de ubicación actual están en [los traslados documentales](../../docs/H4/historico/traslados_documentales.json). Los hashes y archivos del dataset no se modificaron.

## Entrega inicial de Ross: registro histórico

El administrador conserva el artefacto congelado 2.2.0 para reproducción histórica. La pestaña **Escenarios** contiene el trabajo de frontend de Ross, sujeto a la futura API de Erika. El contrato no debe confundirse con un endpoint implementado. Sin capacidades y snapshots compatibles, el envío se deshabilita. El simulador Streamlit permanece separado.

El dataset nuevo es `data/repuestopro_v2/3.0.0/scenarios-20261115-02/`. Contiene 7.056 filas supervisadas y 3.528 familias de comparación. `dataset_supervisado.csv`, `base_mensual.csv` y `escenarios_metadatos.csv` mantienen papeles distintos. El manifiesto registra las demás tablas, el schema, el split y los hashes. `decision_outputs.csv` tiene solo cabecera porque no existe un modelo ampliado aceptado. El build `scenarios-20261115-01` permanece conservado, no aprobado por metadata de auditoría reemplazada. Nunca concatenar ambos builds.

`v2/generate_scenarios_v1.py` implementa la versión 1.0.1. `v2/validate_scenarios_v1.py` comprueba estructura y eventos sin entrenar. `v2/contracts/scenario_sources.v1.json` contiene procedencia y supuestos. `v2/contracts/generator.scenarios.v1.json` fija los mecanismos. `v2/contracts/scenario_capabilities.schema.json` propone la respuesta que debe implementar Erika. El detalle se encuentra en el anexo 49 del Plan V2 y el traspaso `reports/v2/contracts/ross-scenarios-20261115-01/handoff.json`.

Las ventas nuevas son sintéticas, no datos futuros reales. Su periodo es octubre de 2026 a septiembre de 2028. TEST nuevo está reservado sin evaluación de modelos. Los pares de una familia no son observaciones independientes. El siguiente adaptador debe excluir IDs de escenario, resultados futuros y metadata. No se puede cargar el dataset nuevo con el adaptador de 2.2.0 o afirmar que aquel modelo considera los campos ampliados.

Para validar el build sin escribir dentro de él, desde `ml/demand/`:

```powershell
.\.venv\Scripts\python.exe -B -m unittest tests.test_scenario_generation tests.test_scenario_dictionary tests.test_scenario_contract tests.test_v2_structure -q
```

La regeneración solo admite un `build_id` nuevo. Para reproducir también la metadata, `--recorded-at` debe recibir la fecha del manifiesto original. No ejecutar el generador para consultar una predicción. No volver a evaluar TEST de 2.2.0. El entorno visual `src/test/fixtures/ScenarioVisual.tsx` solo se abre de forma deliberada en desarrollo, no forma parte de la entrada de la aplicación ni representa una API real.

La revisión `reports/v2/contracts/ross-scenarios-20261115-01/train_feature_review.json` identifica cuatro candidatas constantes que deben excluirse antes del fit. Es un diagnóstico de TRAIN. No utiliza TEST para elegir variables. El dataset se entrega para revisión del nuevo adaptador, no como un modelo activado.

## Estado del dashboard tras reconciliar Neon

El 15 de noviembre de 2026 se completó la reconciliación de esquema con Prisma 5.22.0. Las diez migraciones están aplicadas. Se conservan como excepciones documentadas Product.quality vacío y la clave foránea previa de RequestHistory. No ejecutar el diff como script de limpieza. El dashboard vuelve a consultar ventas confirmadas, sin ignorar anulaciones. El fallback de disponibilidad parcial sigue protegiendo futuras incompatibilidades.

El ensayo aislado aprobó 58 comprobaciones y la revisión productiva posterior aprobó 46 lecturas. Se conserva el respaldo `pre-h4-production-backup-20261115`. La evidencia está en [el reporte de reconciliación](reports/v2/closure/neon-reconcile-20261115-01/review.json). Esto no activa escenarios ampliados, no modifica el artefacto 2.2.0 y no permite repetir TEST. La latencia observada del dashboard requiere optimización aparte.

## Escenarios 3.0.0: integración vigente

La pestaña **Escenarios** del administrador ya consume la API real y el artefacto ampliado. Este estado reemplaza la entrega anterior limitada a fixtures, que queda registrada como historia. **Consulta histórica** conserva 2.2.0. Streamlit sigue separado. No cambiar DEMAND_RELEASE a 3.0.0: esa variable corresponde al replay 2.1/2.2. Los escenarios usan una referencia separada, fijada en código.

El dataset publicado `data/repuestopro_v2/3.0.0/scenarios-20261115-02/` no se modificó. `v2/scenario_data.py` prepara sus entradas, `v2/train_scenarios.py` contiene el experimento offline y `v2/scenario_runtime.py` implementa validación e inferencia. `admin_scenarios.py` recibe peticiones JSON por stdin. La API nunca ejecuta entrenamiento, un generador o evaluación de TEST. Los hashes se comprueban antes de deserializar el modelo.

La selección está en `reports/v2/3.0.0/scenarios-model-20261115-01/`. Incluye release, selección, configuración, experiments.csv, snapshots de entrada y evaluación final guardada. El artefacto está en `models/v2/scenarios-model-20261115-01/model.joblib`. El contrato de ejecución es `v2/contracts/scenario_runtime.v1.json`. No sobrescribir esa carpeta o volver a ejecutar `evaluate_scenarios_once`. Su bloqueo impide repetir el TEST ya consumido. El manifiesto del dataset conserva el estado de su publicación inicial, no el estado posterior del entrenamiento.

La API expone GET `/api/predictions/scenarios/capabilities`, GET `/api/predictions/scenarios/snapshots/:id` y POST `/api/predictions/scenarios/preview`, solo ADMIN. Su cache idempotente guarda respuestas sintéticas en `tmp/scenario-preview-cache-v1`, separadas por actor y clave. No guarda tokens o datos personales. El cliente no puede enviar targets, rutas o features arbitrarias. Las ediciones nunca cambian Product, Sale, inventario o Neon.

MAE de VALIDATION: 10,43 unidades, baseline 17,11. MAE del TEST nuevo: 10,16, baseline 15,57. La selección priorizó MAE aunque el bosque cuadrático tenía mejor RMSE. Los resultados son sintéticos. El modelo no demuestra elasticidad económica real. Los valores fuera del rango de TRAIN se abstienen. Cotización y costo sirven para una compra hipotética y validación de precios, no para fingir una respuesta causal de ventas. Reposición conserva límites mensuales, sin órdenes automáticas o garantía diaria.

Desde el proyecto, iniciar backend y frontend con sus comandos habituales. Ingresar como ADMIN y abrir Predicción de ventas → Escenarios. Debe verse V3.0.0. No regenerar datos ni entrenar para iniciar la demo. El ejemplo documentado en H4 usa Farola Delantera Derecha, Tienda 1 y abril de 2028. Para el dashboard puede consultarse septiembre de 2026. El inventario sigue siendo actual.

La [evidencia de cierre](reports/v2/closure/scenario-integration-20261115-01/review.json) registra 526 pruebas, compilaciones, integridad y revisión visual integrada. El harness de desarrollo `src/test/fixtures/scenario-integration.html` usa una sesión de prueba local, no forma parte de la aplicación compilada o de su seguridad productiva. Sus servidores auxiliares se detuvieron. La sesión personal del usuario no se presenta como comprobada por ese harness.
