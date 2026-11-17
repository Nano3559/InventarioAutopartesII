# M41-04 — Baselines mensuales offline

El módulo es Python estándar. Recibe la historia de un par producto–tienda, valida qué revisiones estaban disponibles al corte y calcula un baseline determinista. El adaptador proyecta emisiones existentes al esquema de [M41-01](H4_M41_01_EVALUACION_OFFLINE.md). La autorización, procedencia e independencia de la cohorte corresponden a la [ficha M41-03](H4_M41_03_FICHA_COHORTES.md). Las fórmulas se aplican a **ventas observadas en unidades**, con horizonte mensual.

## Contrato de entrada y salida

`forecast(request, method, **parameters)` exige `productId`, `locationId` (IDs enteros positivos de 32 bits), `targetMonth` (`AAAA-MM`), `familyId` de la fila objetivo, `cutoffAt` y `history`. El corte equivale al primer instante del mes objetivo en UTC−04:00. Una representación zonificada equivalente es válida.

Cada elemento de `history` exige `productId`, `locationId`, `month`, `observationId`, `observed`, `closureStatus` (`CLOSED` o `OPEN`), `complete` (booleano), `availableAt` y `provenance` (`sourceId` y `sha256` binario de referencia en hexadecimal minúsculo). `observed` es un entero entre 0 y 1.000.000.000 o `null`. `availableAt` es ISO 8601 con zona o `null`. `stockAvailable` es opcional y admite booleano o `null`. Sirve como contexto de procedencia y segmentación. Los baselines pronostican ventas observadas y no corrigen el efecto de un quiebre sobre esas ventas.

- Un mes utilizable es anterior al objetivo, cerrado, completo y con observado conocido. La revisión debe estar disponible como máximo al corte y el observado cerrado no puede preceder al fin de su mes.
- Los duplicados de mes o de `observationId`, otros productos o tiendas, campos desconocidos, meses futuros o del objetivo y cantidades inválidas se rechazan con `ValueError`. Debe enviarse una sola revisión por mes, seleccionada con el protocolo al corte.
- La falta de historia válida devuelve un resultado con `status=ABSTAINED`, `forecast=null` y `abstentionReason`. Los motivos son `NO_HISTORY`, `MONTH_MISSING`, `MONTH_NOT_COMPLETE`, `OBSERVED_MISSING`, `AVAILABILITY_UNKNOWN`, `AVAILABLE_AFTER_CUTOFF`, `SEASONAL_ANCHOR_MISSING` e `INSUFFICIENT_POSITIVE_MONTHS`.
- En una respuesta `COVERED`, el motivo es nulo y el pronóstico es finito y no negativo. Se incluyen método, versión `1.0.0`, parámetros, producto, tienda, mes, familia, corte y `observationsUsed` con identidades, valores y procedencia. El orden de la historia de entrada es libre. La función devuelve copias de las observaciones consultadas.

## Métodos y cálculos

No hay parámetros implícitos. Los parámetros de suavizado deben pertenecer a `(0, 1]`. Selección de parámetros y ventanas corresponden a una etapa de desarrollo autorizada y separada.

| Método | Parámetros e historia | Fórmula y abstención |
|---|---|---|
| `lag1` | Ninguno. Mes exacto `t−1`. | Devuelve su observado, incluido cero. Se abstiene si ese mes está ausente o no es utilizable. |
| `moving_average` | `k` entero positivo. Últimos `k` meses exactos desde `t−1`. | Suma de observados dividida entre `k`. Incluye ceros válidos. Una ventana incompleta produce abstención. |
| `sba` | `alpha` para tamaño e intervalo. Tramo consecutivo y utilizable que termina en `t−1`, con dos meses positivos como mínimo. | En la primera venta positiva inicializa el tamaño `z`. En la segunda fija el intervalo `p` en la distancia en meses y actualiza `z`. Cada positivo posterior actualiza `z ← z + α(y − z)` y `p ← p + α(g − p)`, con `g` desde la última ocurrencia. Los ceros cuentan para medir los intervalos y no actualizan el estado entre ocurrencias. Devuelve `(1 − α/2) z/p`. |
| `tsb` | `alpha` para tamaño, `beta` para ocurrencia. Mismo tramo consecutivo, con un positivo como mínimo. | En el primer positivo inicializa `z = y` y `p = 1`. En cada mes posterior actualiza `p ← p + β(I[y>0] − p)` y solo en meses positivos actualiza `z ← z + α(y − z)`. Devuelve `p × z`. Los ceros posteriores reducen la probabilidad. |
| `seasonal_naive` | Ninguno. Observación exacta `t−12`. | Devuelve su observado, incluido cero. Se abstiene si falta el ancla o no estaba disponible. Recibir 12 filas no sustituye la comprobación del mes exacto. |

SBA y TSB terminan la búsqueda hacia atrás en el primer hueco o mes inválido. Si el tramo posterior al hueco conserva la historia mínima, se puede inicializar desde ese tramo. El historial consultado se devuelve completo para auditar la continuidad y disponibilidad. Una serie totalmente en cero permite predecir cero con lag1, media móvil o un ancla estacional válida. Para SBA y TSB no alcanza para inicializar un tamaño positivo y devuelve abstención.

### Ejemplos manuales

- **Lag1 y media móvil.** Con `[2, 4, 6]`, lag1 devuelve **6**. Con `k=2`, la media móvil devuelve **5**.
- **SBA.** Para `[8, 0, 12]` y `α=0,5`, la segunda ocurrencia inicializa `p=2` y actualiza `z=10`. Resultado **3,75**. Para `[0, 8, 0, 12, 0, 0, 4, 0]` se actualiza después a `p=2,5` y `z=7`. Resultado **2,10**.
- **TSB.** Para esa misma serie larga con `α=β=0,5`, desde el primer positivo la secuencia de probabilidades es `1, 0,5, 0,75, 0,375, 0,1875, 0,59375, 0,296875`. El tamaño final es `7` y el resultado **2,078125**. Con `[8, 0, 0, 0, 0, 0]` el resultado es `8 × 0,5⁵ = 0,25`.
- **Estacional.** Si el mes `t−12` tiene observado **17** válido, el resultado es **17**. Si se elimina ese mes, el resultado queda nulo.

Referencias de formulación: [Syntetos y Boylan](https://research.lancaster-university.uk/en/publications/the-accuracy-of-intermittent-demand-estimates/) y [Teunter, Syntetos y Babai](https://research.rug.nl/en/publications/intermittent-demand-linking-forecasting-to-inventory-obsolescence/). La inicialización y los mínimos anteriores son decisiones explícitas de esta implementación.

## Integración offline

1. Crear la solicitud con la clave de la fila objetivo y la fuente verificada. Calcular `forecast` con el método y los parámetros fijados.
2. Conservar el resultado original y la **hora real** de emisión en un registro de evidencia. Registrar su fuente y SHA256 en `cohort["sources"]`. La validación de formato por sí sola no acredita el hash ni la fecha.
3. Llamar `attach_to_cohort(cohort, emissions)`, donde cada elemento de `emissions` contiene `result`, `issuedAt` y `sourceId`. El adaptador asocia producto, tienda, mes y familia. Verifica un corte equivalente y, para resultados cubiertos, exige que las observaciones consultadas estén disponibles antes o al emitir. La emisión debe ser a más tardar al corte. M41-01 exige ese tiempo, por lo que un replay posterior requiere su flujo aprobado. No se antedata.
4. El adaptador devuelve una copia de la cohorte, con un `baselineId` que identifica método, versión y parámetros, y añade `baseline`, `baselineIssuedAt` y `provenance.baseline` a cada fila cubierta por el baseline. Un cero se conserva. Una abstención queda sin baseline numérico. Sus razones permanecen en la evidencia original. El adaptador rechaza emparejamientos duplicados o inexistentes, varias configuraciones y la sobrescritura de un baseline existente.
5. En una etapa autorizada, M41-01 calcula la comparación solo en filas cubiertas por ambos. Conservar las emisiones originales para auditar cobertura del baseline y motivos de ausencia. Cada método se adjunta a una copia separada de la misma cohorte. Esta tarea comprueba el flujo con fixtures independientes.

No se han medido mejoras de calidad predictiva. Seleccionar la ventana histórica de SBA/TSB, distinguir ceros por stock de ceros de demanda y evaluar estacionalidad requieren un protocolo y datos suficientes. La política de continuidad, los límites y la procedencia verificable deben revisarse antes de aplicar el módulo a una cohorte real.

## Pruebas focalizadas

Desde `ml/demand`:

```powershell
& ./.venv/Scripts/python.exe -B -m unittest -v tests.test_offline_baselines_m41 tests.test_offline_evaluation_m41
```

Los fixtures bajo `tests/fixtures/` son independientes. Los meses, cierres, disponibilidad y huella de procedencia que usa la suite de baselines se construyen de forma determinista a partir de `m41_baseline_histories.json`. Las pruebas cubren entradas inválidas, fechas, rachas de ceros, anclas, ejemplos manuales, reproducibilidad, inmutabilidad y compatibilidad de salida.
