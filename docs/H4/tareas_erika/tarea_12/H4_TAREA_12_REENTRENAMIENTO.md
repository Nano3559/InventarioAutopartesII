# H4 — Tarea 12: reentrenamiento incremental y nuevo CANDIDATE

Fecha: 9 de noviembre de 2026. Rama: erika.

## Resultado

Se implementó el ensayo explícito en Streamlit y se creó un RandomForest
CANDIDATE independiente. El ejemplo utilizó realmente **6 filas nuevas de una
serie** (producto 1, tienda 5). Se conservaron 3 filas reservadas sin evaluación.
No hay métricas comparativas disponibles ni evidencia de superioridad a V1.
El reentrenamiento no promueve, modifica ni sustituye ACTIVE.

## Arquitectura

DemandSession exporta una copia de los cierres del par seleccionado, con seed,
escenario, identidades de sesión/diario y procedencia MANUAL o GENERATED. No
exporta demanda latente. El motor queda vinculado a un único diario.

prepare_incremental contrasta el motor con ObservationJournal.closed por
producto, tienda, mes y observado. Rechaza claves discordantes, cierres faltantes,
observados contradictorios, procedencia desconocida o cierres anteriores a su
emisión. Los registros pending o revealed no cuentan como cerrados. La etiqueta
se obtiene del observado concordante, nunca de forecast.prediction.

Los lags se reconstruyen exclusivamente desde los tres cierres anteriores del
mismo par. Una diferencia frente a las features hipotéticas emitidas se registra
en trace; no invalida el observado. No se utiliza como dato de ajuste una
precarga de escenario, demanda latente o predicción. Los valores manuales son
observados declarados por el usuario en la simulación, no ventas comerciales
certificadas; el programa no puede certificar su procedencia fuera del simulador.

RetrainingSession pertenece a una sesión, usa bloqueo contra concurrencia y
reutiliza el resultado ante una solicitud idéntica. Los datos de otro par o
sesión no se mezclan. Se crea una instancia nueva de RandomForestRegressor;
no se carga ni se reutiliza el estimador de V1 para ajustar pesos.

Los resultados se guardan bajo candidates/<session_id>/<run_id>/:

- incremental.json: cierres, trazabilidad, features reconstruidas y cortes.
- train.csv: seis filas que se entregan al ajuste.
- reserved.csv: tres filas separadas que no pasan a fit.
- candidate.joblib: modelo nuevo, contrato, parámetros, versiones y huella de datos.
- manifest.json: identidad, procedencia, conteos y SHA256 binarios de los archivos.

La ruta de ejecución es nueva y no sobrescribe candidatos previos. Se rechazan
destinos dentro de data/, models/ y reports/, así como raíces que los contengan.
El rol interno del nuevo artefacto es CANDIDATE. El esquema incremental es
distinto del candidato congelado V1; el runtime actual no lo activa ni lo carga
automáticamente. Su validación para comparación/promoción corresponde a Tarea 13.

## Elegibilidad y separación temporal aprobadas

Se exige una secuencia completa de 12 cierres nuevos por par:

| Uso | Meses | Filas objetivo |
|---|---|---:|
| Historia inicial | Octubre–diciembre 2026 | 0 |
| Ajuste | Enero–junio 2027 | 6 |
| Reserva futura para comparación | Julio–septiembre 2027 | 3 |

El corte de entrenamiento es junio de 2027. Los meses posteriores al bloque
aprobado se ignoran para este ensayo fijo. No se incorporan TRAIN, VALIDATION
ni TEST originales como filas, ni valores de TEST original como lags del ajuste.
El servicio de reentrenamiento no lee los CSV históricos. Con menos meses o
problemas de calidad devuelve ENSAYO NO DISPONIBLE o un error de datos, sin fit.
Los seis ejemplos de una serie son un mínimo demostrativo de la simulación,
no evidencia de suficiencia estadística o calidad comercial.

Parámetros fijos del candidato: n_estimators=200, max_depth=8,
min_samples_leaf=3, max_features=sqrt, random_state=42, n_jobs=1.
No se hizo búsqueda de hiperparámetros ni se consultó la reserva para elegirlos.
El conjunto X conserva las cinco features oficiales y excluye IDs y target.

## Streamlit, sesiones y fallos

ENSAYAR REENTRENAMIENTO es un botón separado de PREDECIR, GENERAR y AVANZAR.
Muestra progreso y resultado, identifica el par y advierte que entrenar no
activa. Los reruns no entrenan; repetir la solicitud sin datos distintos
reutiliza el candidato ya obtenido en esa sesión. La operación no accede al
runtime ACTIVE. Los contratos create_runtime(), get_active_model(),
predict(features) y las estructuras de Ross no cambiaron.

RESTABLECER EDICIÓN descarta servicio y resultado locales sin borrar los
artefactos guardados. No existe registro ACTIVE global nuevo ni recuperación
automática de candidatos desde disco. Los cierres en memoria previos a esta
implementación que carezcan de procedencia se rechazan; no se infiere su origen.
Un fallo de escritura puede dejar una carpeta incompleta sin manifiesto de
ejecución terminada; no debe utilizarse como candidato válido.

## Ejemplo ejecutado y reproducción

Comando explícito desde la raíz:

```powershell
.\ml\demand\.venv\Scripts\python.exe -B ml/demand/example_retraining.py
```

El ejemplo registra manualmente 12 observados SIMULADOS, 10 a 21, con seed 42,
producto 1 y tienda 5. La historia inicial es 10, 11, 12; los targets de ajuste
son 13 a 18; los targets reservados son 19, 20, 21. Para enero de 2027 se
reconstruyen lags 12, 11, 10. No se presentan esos valores como ventas reales.

Ejecución creada: CAND-f3690f19436644959f2218cdc079110c.
Sesión: 9958a7bc0be3447e88c6b4a331b05ace.
Fecha: 2026-11-09 14:56:18 America/La_Paz (18:56:18 UTC).
Datos incrementales SHA256:
bbd5a485b3645a62111fa0f8fa5bab68221656e2d6a570458455794a25cd5639.
train.csv SHA256:
e0ead8c21ec90d003e435a67b2601ee2095f9242dfd955f0f4b7f3d6c6921d45.

Repetir el ejemplo crea otra sesión y versión; no sobrescribe ésta. Los tiempos
y UUID cambian, por lo que no se promete igualdad binaria del paquete completo.
Se verificó igualdad de train.csv y predicciones del estimador con los mismos
datos/seed, incluso cambiando exclusivamente la reserva. Ninguna métrica de
precisión se calculó sobre entrenamiento, reserva ni TEST inicial.

## Archivos propios de la tarea

Nuevos: ml/demand/retraining.py, ml/demand/test_retraining.py,
ml/demand/example_retraining.py, el directorio del candidato de ejemplo,
este informe y evidence/.

Modificados: ml/demand/demand_engine.py (vínculo y exportación de cierres,
procedencia); ml/demand/ui_panels.py (ensayo explícito y vínculo de diario);
ml/demand/streamlit_app.py (presentación y limpieza del ensayo en reset).
Se conservaron cambios previos y no se editó ninguna prueba anterior.

## Validación y evidencia

Las pruebas nuevas cubren reconstrucción desde observados, discrepancias
hipotéticas permitidas, insuficiencia, pendientes, contradicciones, claves y
fechas, procedencia, exportación sin latentes, separación temporal, columnas,
deduplicación, concurrencia, reproducibilidad, reserva sin influencia en fit,
aislamiento, candidato versionado, preservación de ACTIVE y reset en AppTest.
Resultado final: **360 pruebas aprobadas en 49.755 segundos**, incluidas las
345 anteriores y 15 nuevas. Comando: python -B -m unittest discover -s ml/demand
-p 'test_*.py' -q, usando ml/demand/.venv/Scripts/python.exe.
El log completo queda en full_tests.txt. git diff --check pasó.

La suite usa entrenamientos temporales aislados autorizados. No reentrena V1
ni repite la evaluación oficial TEST. Streamlit se probó fuera del sandbox por
los sockets internos de AppTest. Los avisos ScriptRunContext pertenecen a las
pruebas de Streamlit y no son métricas ni errores de entrenamiento.

Se verificó integridad contra las huellas de Tarea 10 de los doce archivos
protegidos, además del catálogo y generador contra el manifiesto oficial.
No se modificaron dataset 1.1, artefactos congelados, manifiesto V1, reporte TEST
ni experiments.csv. No hubo commits, push, cambios productivos ni acceso Neon.

- [Resultado del candidato ejecutado](evidence/example.json)
- [Suite completa](evidence/full_tests.txt)
- [Integridad final](evidence/integrity.json)
- [Git status acumulado](evidence/git_status.txt)
- [Git diff stat acumulado](evidence/git_diff_stat.txt)

## Pendientes: Tarea 13, sin iniciar

Verificar identidad y compatibilidad del nuevo candidato, congelar criterios
de decisión y comparar contra ACTIVE sobre las mismas filas reservadas de
julio–septiembre de 2027. Conservar abstenciones, cobertura y errores por grupo.
Solo después considerar promoción o rechazo explícitos con motivo y rollback.
No hay afirmación de que este candidato supere a V1. La reserva se conserva
sin evaluación y la promoción sigue requiriendo autorización posterior.
