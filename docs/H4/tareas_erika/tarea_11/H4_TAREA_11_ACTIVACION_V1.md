# Tarea 11 — Activación controlada y validación real de V1

Fecha: 9 de noviembre de 2026. Rama: erika.

## Resultado y alcance

RandomForest V1 fue promovido realmente a ACTIVE mediante promote_v1(reason)
y utilizado por Streamlit AppTest. La activación existió únicamente en memoria
en sesiones aisladas. Al concluir se ejecutó rollback; el estado final de esas
sesiones es SIN ACTIVE. No se implementó ni declaró una activación global o
persistente. Abrir otra sesión, reconectar o restablecer comienza sin ACTIVE.

Identificador de validación/promoción principal:
ACT-V1-08a0f66961054100baa9c39e1a61c806.
Fecha de inicio: 2026-11-09 14:44:59 America/La_Paz
(18:44:59 UTC). V1 procede de la selección
SEL-V1-RANDOMFOREST-20261109T041158351931Z.
Motivo: promoción real autorizada por el usuario para validación controlada
AppTest de Tarea 11. Los eventos completos contienen fechas, motivos y huellas.

## Verificaciones previas

Se revisaron guía oficial, runtime, Streamlit, contrato de Ross, DemandSession,
manifiesto de selección, reporte TEST e informe de Tarea 10.
Los doce archivos protegidos coincidieron con la evidencia de Tarea 10;
también se verificaron los seis hashes normalizados del dataset 1.1.
La evaluación TEST figura TEST_EVALUATED_COMPLETED y corresponde a la misma
selección y huella. Solo se leyó el reporte: no se recalculó TEST.

Antes de promover se cargó el conjunto mediante el cargador verificado,
comprobando esquema, CANDIDATE interno, estimador real RandomForestRegressor,
cinco columnas, scaler ausente, corte 2026-03 y parámetros congelados:
n_estimators=200, max_depth=8, min_samples_leaf=3, max_features=sqrt,
random_state=42, n_jobs=1. Las diez pruebas unitarias previas del runtime,
incluido rollback con fixtures, pasaron antes de la promoción real.

Huellas exigidas antes de deserializar:

| Referencia | SHA256 |
|---|---|
| Binaria fijada en código | fb0d8d81ba2558101a232ff616bff14fe0b95d6a13dfa24d60a8dce4b4e81d3e |
| Normalizada congelada | 3e3cf6d1ef75567a69ff6f604bcb2a93f629f6d0fa503bdf734f3c6118c03883 |

La referencia independiente sigue siendo la constante auditada de Tarea 10;
no es una firma externa del autor histórico. El límite de confianza es el
código revisado del repositorio. Los manifiestos congelados no se editaron.

## Inferencia real de ejemplo: simulación, no venta real

Producto 1, tienda 5, octubre de 2026: primer mes posterior al panel histórico.
Las features capturadas en la llamada real a predict fueron, en este orden:

| Feature | Valor |
|---|---|
| ventas_mes_anterior | 22 |
| ventas_hace_2_meses | 18 |
| ventas_hace_3_meses | 26 |
| mes_sin | -1.0 |
| mes_cos | -0.0 |

Predicción real del estimador: **21.773409189130824 unidades**.
Baseline de sesión: 22.0. Observado generado por el simulador: 22.
No son ventas comerciales ni una nueva evaluación de precisión de V1.
get_active_model devolvió RandomForestRegressor, V1, role ACTIVE,
origin SIMULACION, trained_through 2026-03, huella binaria completa y features
ordenadas. Las emisiones conservaron la misma identidad del modelo.

## Flujo funcional

PREDECIR invocó el runtime real una vez por clic. Un rerun sin clic no produjo
otra inferencia. Repetir PREDECIR antes de revelar reemplazó la emisión pendiente
del mismo mes, sin duplicarla. GENERAR SIGUIENTE MES reveló el observado;
AVANZAR MES cerró una sola vez la emisión y avanzó a noviembre de 2026.
El cierre queda en ObservationJournal y el reloj en DemandSession.

PRODUCTO NUEVO bloqueó PREDECIR y registró prediction=null, con el motivo
HISTORIAL INSUFICIENTE y la explicación existente de Ross. No se asignó error
cero ni se fabricó una predicción. Los ocho escenarios completaron emisión o
abstención, generación y avance: NORMAL, CRECIMIENTO, CAÍDA, PICO MAYORISTA,
STOCKOUT, PRODUCTO NUEVO, CAMBIO PERSISTENTE y RECUPERACIÓN.

RandomForestRegressor.fit estuvo interceptado para fallar si se invocaba
durante toda la validación real: **cero llamadas**. El contrato de Ross no
cambió y no se enviaron IDs, escenario u observado como features.

Rollback restauró SIN ACTIVE y preservó el cierre y su predicción original.
RESTABLECER EDICIÓN creó otra instancia inactiva y limpió el diario local;
no alteró la emisión ya capturada como evidencia. Cada escenario usó una sesión
independiente, con promoción explícita y rollback en finally.

## Pruebas, integridad y archivos

El ejecutable optativo ml/demand/validate_v1_activation.py reproduce esta
validación y escribe evidencia. No se ejecuta con unittest discovery: requiere
una nueva autorización para repetir promociones reales. No modifica código
productivo, dependencias ni contratos existentes.

Un primer intento falló por una aserción propia que esperaba el motivo corto
de abstención; Ross devuelve el motivo con explicación. Se conservó la
evidencia, se revirtió la sesión y se corrigió únicamente la aserción. El
segundo recorrido completó los ocho escenarios. No hubo modificación funcional
del runtime o la interfaz para hacer pasar la validación.

La regresión usa los módulos test_demand_runtime, test_runtime_integration,
test_ross_ui, test_simulator_ui, test_engine_integration y
test_simulator_validation. Solo se entrenan pequeños fixtures temporales;
no se reentrena V1 ni se ejecutan selección/evaluación oficial.
Resultado: **108 pruebas aprobadas en 107.078 segundos**. Se ejecutaron con
unittest.defaultTestLoader.loadTestsFromNames sobre los seis módulos anteriores
y TextTestRunner, fuera del sandbox para permitir los sockets locales internos
de AppTest. El log queda en regression.txt. No se repitió la suite completa de
entrenamiento/evaluación: la Tarea 10 conserva su resultado de 345 pruebas.

Los doce archivos protegidos permanecen idénticos al finalizar. No se cambiaron
dataset, artefactos, manifiestos, reporte TEST ni experiments.csv. No hubo
commits, push, conexión Neon ni cambios backend/frontend productivos o Prisma.
git diff --check no mostró errores.

Archivos nuevos de esta tarea: validate_v1_activation.py, este informe y
evidence/. Ningún archivo existente se modificó en Tarea 11.
El estado Git acumulado incluye las tareas anteriores sin commit; su diff stat
versionado continúa en 4 archivos, 216 inserciones y 36 eliminaciones. No
incluye los archivos nuevos sin seguimiento.

## Evidencia y pendientes

- [Activación, ejemplo, escenarios, rollback e integridad](evidence/activation.json)
- [Log de validación final](evidence/validation.txt)
- [Log de regresión](evidence/regression.txt)
- [Primer intento conservado](evidence/attempt1.json)
- [Git status](evidence/git_status.txt)
- [Git diff stat](evidence/git_diff_stat.txt)
- [Integridad después de la regresión](evidence/integrity_final.json)

La inferencia real quedó comprobada en AppTest; no se dejó un navegador humano
con sesión activa. Persistencia global, una interfaz de promoción y despliegue
productivo quedan fuera de esta validación. No se inició reentrenamiento ni
Tarea 12. El manifiesto histórico mantiene SELECTED_FROZEN_NOT_ACTIVE y
active=false porque describe la selección congelada, no una sesión temporal.
