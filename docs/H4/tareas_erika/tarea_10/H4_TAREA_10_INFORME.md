# H4 — Tarea 10: runtime de inferencia local

Fecha: 9 de noviembre de 2026. Rama: erika.

## Resultado

Implementado demand_runtime.py respetando create_runtime(), get_active_model()
y predict(features). V1 permanece SELECTED_FROZEN_NOT_ACTIVE. No se ejecutó
promote_v1 sobre V1 real, entrenamiento oficial, evaluación TEST oficial,
escritura de experimentos oficiales, commit ni push.

## Cambios propios de Tarea 10

Nuevos: ml/demand/demand_runtime.py, ml/demand/test_demand_runtime.py,
ml/demand/test_runtime_integration.py, este informe y evidence/.

Modificados: ml/demand/streamlit_app.py (dos líneas para descartar h4_runtime
y runtime_error al restablecer) y ml/demand/README.md (estado y uso local).
Los cambios previos de simulator_inputs.py, ui_panels.py y del resto de
streamlit_app.py se conservaron. Ninguna prueba existente fue editada.

## Contrato y validación

Cada instancia comienza sin ACTIVE. Solo la promoción explícita con motivo
puede seleccionar el candidato; no existe activación automática ni botón de
promoción. La carga valida identidad antes de joblib.load y utiliza los mismos
bytes verificados, evitando una segunda lectura del fichero. Valida esquema,
rol CANDIDATE, modelo, features, target, scaler ausente, versión de sklearn,
tipo y dimensión del estimador, nombres de columnas, parámetros declarados y
corte temporal. Una carga fallida conserva el ACTIVE anterior.

La huella normalizada congelada es
3e3cf6d1ef75567a69ff6f604bcb2a93f629f6d0fa503bdf734f3c6118c03883.
La referencia binaria fijada en código tras auditoría es
fb0d8d81ba2558101a232ff616bff14fe0b95d6a13dfa24d60a8dce4b4e81d3e.
Ambas se exigen. La segunda es una referencia independiente del archivo en
tiempo de carga, protegida por revisión de código: no se obtiene del archivo
para aceptarlo a sí mismo. No es una firma externa de procedencia histórica;
el límite de confianza es el código local del repositorio. No se admiten
artefactos subidos. Los documentos congelados no se modificaron.

El hash binario entregado a Ross identifica el paquete serializado completo.
Las cinco features se exigen en orden exacto; se rechazan columnas extra,
booleanos, valores no finitos, lags negativos o fraccionarios y calendario
incompatible con los doce pares seno/coseno. La salida contiene exactamente
prediction y reason. Los negativos finitos se conservan sin recorte.
La falta de historia, entradas incompletas y valores fuera del contrato dan
abstenciones; fallos del estimador producen un motivo genérico sin traza.

El contrato de Ross sigue controlando IDs, historia disponible, mes completo
y mes posterior al entrenamiento: predict(features) no recibe esos metadatos.
No se inventaron umbrales estadísticos de cobertura comercial.

## Promoción, reversión y sesiones

promote_v1(reason) valida antes de sustituir la referencia y conserva la
anterior; rollback(reason) permite restaurarla, incluido el estado sin ACTIVE.
Ambas acciones dejan eventos con motivo, fecha y metadatos copiados. No
reescriben el candidato ni su rol interno. No hay ACTIVE global persistido:
la selección es local en memoria por instancia de Streamlit. Reconectar o
restablecer crea un proveedor inactivo. Otra sesión no recibe sus promociones.

ObservationJournal conserva metadatos de emisiones ya registradas; cambiar
ACTIVE no modifica predicciones anteriores. DemandSession sigue siendo la
autoridad del reloj y los ocho escenarios. El runtime no entrena ni avanza
meses, ni aprende de observados. El contrato público de Ross no cambió.

## Pruebas y evidencia

Comando ejecutado desde la raíz:

```powershell
.\ml\demand\.venv\Scripts\python.exe -B -m unittest discover -s ml/demand -p 'test_*.py' -q
```

Resultado: **345 pruebas, OK, 46.415 segundos**: 333 anteriores y 12 nuevas.
Las nuevas cubren fixtures temporales de promoción/reversión, aislamiento,
rechazo previo a deserialización, contrato de entradas, errores y negativos,
conservación de cierres, inferencia en Streamlit, reset y reconexión.
Los entrenamientos de prueba existentes fueron autorizados y no modificaron
V1 ni generaron experimentos oficiales. TEST oficial no se reevaluó.

Los primeros intentos quedaron bloqueados por socketpair de asyncio en el
sandbox. Se interrumpieron; la suite completa se ejecutó fuera del sandbox
con autorización. El log incluye advertencias de Streamlit en AppTest;
no hubo fallos ni errores de pruebas. git diff --check pasó.

Se compararon SHA256 binarios antes/después de los doce archivos de datos,
modelos y reportes existentes: **cero alteraciones**. Los seis hashes
normalizados oficiales del dataset y el catálogo también coincidieron en la
auditoría. El manifiesto conserva active=false y el reporte TEST conserva
MAE 4.814178503040102, RMSE 8.182890558417325 y R² 0.42304686389766555.

Evidencia: [log completo](evidence/full_tests.txt),
[huellas iniciales](evidence/integrity_before.json),
[verificación final](evidence/integrity_after.json),
[git status](evidence/git_status.txt),
[git diff --stat](evidence/git_diff_stat.txt).
El diff stat de Git no incluye archivos nuevos sin seguimiento; el inventario
anterior distingue los cambios propios de esta tarea de los previos.

## Pendiente de autorización

La promoción real de V1 y la prueba manual con esa referencia ACTIVE quedan
pendientes de autorización posterior. El mecanismo se validó con fixtures
aislados; no se cambió el estado oficial ni se ejecutó inferencia TEST real.
