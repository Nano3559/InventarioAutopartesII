# H4 — Estructura, pruebas y reproducibilidad

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

**Límite previo de portabilidad:** el manifiesto del candidato archivado contiene una ruta absoluta y `archived_run()` exige esa ubicación. En otro directorio/OS puede rechazar el candidato aunque sus bytes sean correctos. No se cambió ese manifiesto ni se debilitó su verificación. Su traslado portátil requiere revisión autorizada independiente. Runtime V1 y entrenadores conservan sus rutas relativas al módulo.

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
