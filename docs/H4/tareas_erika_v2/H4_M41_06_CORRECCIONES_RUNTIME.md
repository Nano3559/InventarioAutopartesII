# M41-06 · Correcciones del runtime de escenarios

Alcance del cambio en rama `erika`: preparación y respuesta de escenarios del release congelado `calendar-model-20261116-01` (dataset 4.0.0).

| Hallazgo | Causa | Corrección |
| --- | --- | --- |
| M41-05-01 · P1 | `prepare()` aplicaba la fecha solicitada y calculaba la vigencia para cada `SET_PRICES`, incluso con ambos importes iguales a BASE. | El esquema, los importes y la fecha se validan antes de comparar los importes como `Decimal`. Si ambos coinciden, se preserva el estado efectivo de BASE. Si cambia uno o ambos, el cálculo ponderado conserva la fecha solicitada. |
| M41-05-02 · P2 | `preview()` comparaba el suministro con un pronóstico intermedio antes de resolver la abstención por canal desconocido. | La comparación usa las unidades del pronóstico publicado. Se conserva `UNKNOWN_CHANNEL_MIX`, la reposición `INCOMPLETE` cuando corresponde y las advertencias independientes del pronóstico. |
| M41-05-03 · P2 | La generación de impactos escalares incluía pares de valores iguales como cambios. | Los impactos escalares se emiten cuando difieren sus valores efectivos. La comparación se hace antes de serializar decimales. La huella `scenarioInputSha256` se calcula sobre la solicitud original, incluida cualquier edición redundante. |

## Evidencia funcional

En DEMO `calendar-2026-53-6-november` (Tensador de Correa, tienda 2), con precios de 108.3000 y 92.0550 Bs, vigencia desde el 1 de noviembre y seguridad de cinco unidades:

| Variable | KEEP | SET_PRICES idéntico antes | SET_PRICES idéntico después |
| --- | ---: | ---: | ---: |
| Días de vigencia de nuevo precio | 0 | 30 | 0 |
| Pronóstico de ventas | 87.17 | 86.685 | 87.17 |
| Unidades requeridas | 93 | 92 | 93 |
| Unidades sugeridas de reposición | 0 | 0 | 0 |

Los 168 snapshots DEMO publicados dieron el mismo estado efectivo, impactos y advertencias de preparación al comparar `KEEP` con `SET_PRICES` idéntico desde el inicio del mes. Esta comprobación compara entradas efectivas y es independiente de la evaluación predictiva oficial.

## Regresión

Desde `ml/demand` en PowerShell:

```powershell
& ./.venv/Scripts/python.exe -B -m unittest tests.test_scenario_runtime_m41_06 tests.test_calendar2026 tests.test_scenario_plan_impacts tests.test_scenario_replenishment tests.test_scenario_verified_reads tests.test_scenario_contract tests.test_scenario_runtime tests.test_scenario_capabilities_schema
```

Resultado: 84 pruebas aprobadas, incluidas seis nuevas. Las seis nuevas reprodujeron cuatro fallos de aserción antes del cambio. Las pruebas cubren vigencia, cambios reales de una diezmilésima de boliviano, fecha y precisión inválidas, stock, abstención, advertencias, determinismo y rechazo de estimaciones no finitas.

La regresión HTTP existente (`node -r ts-node/register --test src/modules/predictions/scenarios.http.test.ts` desde `backend`) aprobó 36 pruebas contando subpruebas, con cero fallos. Incluye compatibilidad con el consumidor frontend, idempotencia y validación del contrato. Se ejecutó en localhost con sesión y caché simuladas.

Se conserva `demand-scenarios-1.0.0` y el contrato admite `impacts: []`. La huella permite correlacionar una respuesta con la solicitud original cuando se dispone de esa solicitud. Una respuesta previa recuperada mediante idempotencia puede conservar la salida histórica. El cambio se aplica al generar nuevas respuestas.

La verificación antes y después cubrió 554 archivos bajo `ml/demand/data`, `models`, `reports` y `v2/contracts`. La huella agregada, calculada con ruta y SHA256 binario de cada archivo, fue `4d5098398a45d8c3879ba08aad7dbc08c3c7696740a5cbbb6fa5e7268991fc27`. El SHA256 binario del modelo fue `8d73bbfb769e432461f2a202e37842b47820a76627e46be3e4ba412e64562e1e`. La verificación utilizó DEMO y fixtures de regresión, sin entrenamiento ni nueva evaluación de TEST.
