# H4 — Ejecución y demostración desde Windows PowerShell

Guía actualizada en Tarea 15, 9 de noviembre de 2026. Experimento local SIMULACIÓN.
Consultar primero [informe final](H4_INFORME_FINAL.md) y
[matriz de cumplimiento](tareas_erika/tarea_14/H4_MATRIZ_CUMPLIMIENTO.md): el cierre no es 100 %.
La [revisión T15](tareas_erika/tarea_15/H4_MATRIZ_CUMPLIMIENTO_T15.md) y el
[informe de correcciones](tareas_erika/tarea_15/H4_TAREA_15_CORRECCIONES_FUNCIONALES.md) documentan los tres defectos corregidos.

## 1. Entrar al repositorio y comprobar entorno

```powershell
Set-Location -LiteralPath 'C:\Universidad\Sistemas\9vosemestre\programacion\InventarioAutopartesII'
git branch --show-current
git status --short
$h4Python = Join-Path (Get-Location).Path 'ml\demand\.venv\Scripts\python.exe'
& $h4Python --version
```

La rama auditada es erika. No cambiar de rama ni descartar cambios locales.
El entorno verificado usa Python 3.11.0, numpy 2.4.6, pandas 3.1.0,
scikit-learn 1.9.1 y joblib 1.6.0; las versiones del paquete importan al cargar
artefactos. requirements-ui.lock.txt y requirements-training.txt documentan
las dependencias. No sustituir un entorno funcional solo para seguir esta guía.

Solo si falta el entorno, prepararlo expresamente antes de la demo:

```powershell
py -3.11 -m venv ml/demand/.venv
& $h4Python -m pip install -r ml/demand/requirements-ui.lock.txt -r ml/demand/requirements-training.txt
```

No se ejecutaron instalaciones durante la Tarea 14. Si falta una versión,
detenerse y revisar compatibilidad; no reentrenar V1 para resolver la carga.

## 2. Abrir la interfaz local

```powershell
& $h4Python -B -m streamlit run ml/demand/streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Abrir [Streamlit local](http://127.0.0.1:8501). Mantener esta consola abierta;
Ctrl+C detiene el servidor. Si el puerto está ocupado, elegir otro explícitamente
y abrir su URL correspondiente. La auditoría comprobó HTTP 200/ok en el puerto
8502 y detuvo ese servidor al finalizar.

## 3. Qué puede demostrarse en la interfaz normal actual

1. Elegir producto y tienda válidos; comprobar los IDs y el mes objetivo.
2. Elegir NORMAL, CRECIMIENTO, CAÍDA, PICO MAYORISTA, STOCKOUT,
   PRODUCTO NUEVO, CAMBIO PERSISTENTE o RECUPERACIÓN antes de generar/cerrar.
3. Editar los lags de hace tres meses, hace dos meses y mes anterior.
   Pulsar VALIDAR ENTRADAS; verificar las cinco features y calendario.
4. Al iniciar SIN ACTIVE, PREDECIR está deshabilitado. Escribir un motivo y
   pulsar ACTIVAR V1 CONGELADA. Se verifican ambas huellas y se registra
   ACTIVATE_V1 en el runtime local. PREDECIR utiliza entonces RandomForest V1.
   La alternativa sin modelo es registrar una abstención explícita.
5. GENERAR SIGUIENTE MES genera el observado del mes abierto. No es un salto
   de calendario. Alternativamente, ingresar una venta observada manual.
6. Para un observado manual, confirmar el mes completo y pulsar REGISTRAR
   OBSERVADO para cerrar; después pulsar AVANZAR MES. También se puede cerrar
   al avanzar si está confirmado. Sin confirmación ambas rutas están bloqueadas.
   Un resultado generado es el observado mensual completo del simulador y puede
   avanzar directamente. Estos son los nombres reales de los controles.
7. Repetir doce meses nuevos para el mismo par. ENSAYAR REENTRENAMIENTO crea
   un candidato independiente: seis filas de ajuste y tres reservadas, con
   octubre–diciembre de 2026 utilizados solo como historia inicial.
8. El resultado debe decir CANDIDATE, sin promoción automática. La comparación
   requiere un ACTIVE ya establecido en la misma sesión.

La activación selecciona únicamente V1, no un candidato nuevo ni un archivo
subido. Es local por sesión, no global. Registrar un motivo y pulsar ROLLBACK
LOCAL revierte a la referencia anterior, incluido SIN ACTIVE. Reset o
RECONECTAR RUNTIME vuelven a iniciar sin ACTIVE; para usar V1 se requiere otra
acción explícita. Los eventos de activación/rollback viven en runtime.events
mientras existe esa instancia; no se afirma un registro global persistente.

Cada par tiene su propio generador, derivado determinísticamente de la seed y
sus IDs. Intercalar otra serie no consume su secuencia. Conservar seed, IDs y
secuencia de acciones permite reproducir la sesión. Las nuevas secuencias
pueden diferir de T14 por el arreglo de D01; el dataset histórico no cambió.

## 4. Verificar las correcciones con V1 real

```powershell
& $h4Python -B docs/H4/tareas_erika/tarea_15/evidence/record_validation.py
```

Este arnés abre la interfaz normal mediante AppTest, escribe el motivo y pulsa
ACTIVAR V1 CONGELADA sin inyectar un runtime activo. Emite una predicción real,
genera/cierra/avanza un mes y aplica rollback; comprueba además la secuencia de
seis meses sola/intercalada y el bloqueo de un cierre manual incompleto.
No entrena modelos. Los resultados quedan en tareas_erika/tarea_15/evidence/functional_validation.json.

AppTest no abre una sesión humana ni proporciona capturas. El estado final es
SIN ACTIVE. El comando reemplaza solo su evidencia T15; guardar una copia para
conservar ejecuciones anteriores. El recorrido integral T14 de 60 meses se
conserva como evidencia histórica en tareas_erika/tarea_14/evidence/integral.json. Su arnés
incluye diagnósticos diseñados para reproducir fallas anteriores y no se
presenta como la validación actual de T15. La nueva revisión integral/visual
de todo H4 sigue pendiente de una etapa posterior.

## 5. Comparación archivada y bloqueo de promoción

```powershell
& $h4Python -B ml/demand/validate_candidate_comparison.py
```

Compara V1 temporal con el candidato archivado auditado de Tarea 12 sobre sus
tres filas reservadas. No entrena. Genera nuevos archivos de decisión con IDs
únicos y revierte V1 al finalizar. No cambia las decisiones anteriores.

En Streamlit, cuando exista un ACTIVE en esa misma sesión, COMPARAR CANDIDATE
usa la ejecución propia o el archivado auditado, RECHAZAR requiere motivo y
ROLLBACK LOCAL restaura una referencia anterior verificable. PROMOVER CANDIDATE
permanece deshabilitado; también se bloquea en el runtime. Un JSON con
APROBADO no otorga permiso. La política positiva existe exclusivamente en
test_model_comparison.py, para fixtures aislados.

## 6. Ejecutar las pruebas

La ubicación actual es `ml/demand/tests/`. Su bootstrap aísla los eventos de AppTest en una carpeta temporal. Alternativa desde la raíz: `& $h4Python -B ml/demand/run_tests.py`. Consultar el [README actual](../../ml/demand/README.md) para estructura, dependencias, respaldo y entrenamiento futuro aislado. Los comandos/resultados de informes fechados se conservan como históricos.

```powershell
& $h4Python -B -m unittest discover -s ml/demand/tests -t ml/demand -p 'test_*.py' -q
git diff --check
git status --short
git diff --stat
```

Resultado verificado en T15: 394 pruebas, OK (375 anteriores + 19 nuevas). Las pruebas entrenan modelos
temporales autorizados; no reentrenan V1 ni ejecutan TEST oficial otra vez.
AppTest necesita sockets locales; en un entorno que los bloquee se requiere
autorizar su ejecución fuera de ese sandbox.

## 7. Guion breve de defensa

- Erika: problema y limitación sintética; dataset/split; baseline, LR y RF;
  selección de V1; métricas VALIDATION y TEST ya registradas; runtime y
  reentrenamiento independiente con observados verificados.
- Ross: controles, gráficos, observados posteriores, métricas/cobertura,
  monitoreo y vista de comparación; señalar la revisión visual todavía pendiente.
- Ambos: presentar rechazo INSUFFICIENT_EVIDENCE, bloqueo real de promoción,
  fixtures positivos y rollback; distinguir evidencia automatizada de demo humana.
- Mostrar matriz, diagnósticos D01/D02/D03, integridad y límites del 95 %.
  No presentar esta auditoría como aceptación conjunta o defensa ya realizada.

No ejecutar scripts de selección, entrenamiento oficial o evaluación TEST para
abrir una demo. No realizar commits, push, cambios de esquema o escrituras Neon.
