# M41-01 — Evaluación detallada de predicciones emitidas

La herramienta `ml/demand/v2/offline_evaluation.py` recibe observaciones y predicciones ya emitidas. Produce evidencia por fila, métricas y desgloses como JSON. Las predicciones, el origen y la autorización se establecen antes de usar esta herramienta. El evaluador oficial de 4.0.0 conserva su flujo y reporte histórico.

## Entrada

El esquema de entrada y salida se identifica como `demand-offline-evaluation-1`. La validación es estricta y rechaza campos desconocidos.

| Campo de cohorte | Regla |
|---|---|
| `schema`, `kind`, `cohortId`, `datasetVersion`, `modelId`, `modelSha256`, `sources`, `rows` | Obligatorios. Los hashes son cadenas SHA256 en hexadecimal minúsculo. `sources` asocia identificadores de fuentes con sus hashes. |
| `kind=FIXTURE` | Dataset independiente con prefijo `fixture-`. `authorizationRef` ausente o nulo. |
| `kind=AUTHORIZED_FUTURE` | `authorizationRef` obligatorio. El dataset debe tener una identidad independiente de 4.0.0 y de los fixtures. El responsable verifica la autorización antes de usar la herramienta. |
| `baselineId` | Obligatorio cuando alguna fila incluye pronóstico baseline. Se evalúa un baseline por cohorte. |

| Campo de fila | Regla |
|---|---|
| `productId`, `locationId`, `targetMonth`, `familyId`, `cutoffAt` | Obligatorios. Los IDs de producto y tienda son enteros positivos. El mes es `AAAA-MM`, desde noviembre de 2026. El corte equivale al inicio del mes objetivo en UTC−04:00 para el calendario del proyecto. Una combinación producto, tienda, mes y familia se admite una sola vez por cohorte. |
| `observed`, `forecast`, `status`, `provenance` | Obligatorios, sujetos a las reglas por estado. El observado es un entero cuando existe. Los pronósticos son números finitos. Las cantidades válidas están entre 0 y 1.000.000.000. |
| `observedAt`, `issuedAt`, `baselineIssuedAt` | Fechas ISO 8601 con zona. El observado solo es utilizable desde el cierre del mes. Las emisiones del modelo y baseline deben existir a más tardar en el corte. La emisión de una abstención también se registra. |
| `abstentionReason`, `ineligibilityReason` | Obligatorio únicamente en el estado correspondiente. En los otros estados se omite o usa `null`. |
| `baseline` | Opcional. Si existe se exige su fecha de emisión, referencia de procedencia e identidad en la cohorte. Si falta, se excluye solo de la comparación pareada. |
| `groups`, `classifiedAt` | Opcionales. `groups` admite `volume`, `intermittency`, `availability` e `incident`. Cuando se declara volumen o intermitencia, `classifiedAt` debe estar al corte o antes. Sus reglas se fijan con información disponible entonces o con una definición previa de desarrollo. Disponibilidad e incidente pueden describir un desenlace posterior y solo sirven para segmentar el reporte. |
| `provenance` | Referencia a una entrada de `sources` para cada componente aplicable: `observed`, `forecast` (incluida abstención), `baseline` y `grouping`. La herramienta puede comprobar la estructura y la referencia. El productor o auditor contrasta esos hashes con los bytes de las fuentes autorizadas y sus registros temporales. |

- **COVERED** requiere observado cerrado y forecast numérico. Un forecast cero es válido.
- **ABSTAINED** requiere observado cerrado, fecha de emisión, motivo y forecast nulo. Aporta al denominador de cobertura.
- **INELIGIBLE** requiere motivo y tiene forecast nulo. Puede carecer de observado. Se incluye en el inventario y queda fuera de las métricas y cobertura.

La evidencia de evaluación puede contener el resultado posterior. La entrada de esta herramienta solo describe salidas ya emitidas y metadatos de evaluación. No acepta variables predictivas libres. Una fecha o referencia declarada no acredita por sí sola que los datos originales fueran conocidos al corte.

## Salida y fórmulas

El JSON incluye `metadata`, `inputSha256` de la representación ordenada y validada, `summary`, `groups` y `rows`. Cada fila lleva identidad de cohorte, dataset, modelo, observación, pronóstico, estado, procedencia y los campos derivados `signedError` y `absoluteError`. El orden por mes, producto, tienda y familia es determinista. Cambiar solo el orden de entrada no cambia el resultado ni su huella.

| Indicador | Fórmula y denominador |
|---|---|
| Error firmado y absoluto | `e = forecast − observed` y `abs(e)`, solo para cubiertas. |
| MAE, RMSE, sesgo | `sum(abs(e))/n`, `sqrt(sum(e²)/n)`, `sum(e)/n`. `n` cuenta solo cubiertas. Sesgo positivo indica sobreestimación. |
| WAPE | `sum(abs(e))/sum(observed)` en cubiertas. Es una razón. El observado cero aporta error al numerador, si lo hay. Si la suma es cero, WAPE queda `null`. |
| P90 y P95 | Cuantiles del error absoluto ordenado, por interpolación lineal en la posición de base cero `(n−1)×p`. |
| Cobertura y conteos | `covered/(covered+abstained)`. Inclusión completa de `total`, `eligible`, `covered`, `abstained` e `ineligible`. |
| Comparación pareada | Solo usa filas cubiertas con baseline numérico. Las dos métricas se calculan sobre las mismas filas y observados. `deltaMae = MAE modelo − MAE baseline`. Un valor negativo favorece al modelo. |

Sin filas puntuables, MAE, RMSE, sesgo y percentiles son `null`. Sin filas elegibles, cobertura es `null`. Con filas elegibles totalmente abstendidas, cobertura es 0. Los desgloses por producto, tienda, mes, volumen, intermitencia, disponibilidad e incidente incluyen un grupo `null` para etiquetas ausentes, sin perder esas filas. Los resultados se ponderan por fila. Si hay varias familias por par y mes, el protocolo de la cohorte debe definir previamente qué familias incluir.

## Fixture y ejecución reproducible

Desde `ml/demand`:

```powershell
& ./.venv/Scripts/python.exe -B -m v2.offline_evaluation tests/fixtures/m41_evaluation.json
& ./.venv/Scripts/python.exe -B -m unittest -v tests.test_offline_evaluation_m41
```

El fixture trae seis filas desordenadas. Cuatro errores cubiertos son 0, +2, −2 y +90. Se espera MAE 23,5, RMSE `sqrt(8108/4)`, sesgo 22,5, WAPE `94/28`, p90 63,6 y p95 76,8. Una abstención y una fila inelegible dejan cobertura 4/5. La pareja modelo/baseline común tiene n=2, MAE 1 frente a 2,5 y delta −1,5. `fixture-evidence` se verifica en las pruebas sobre el JSON compacto ordenado por claves de las filas del fixture en su orden original, omitiendo `provenance`.

Para una futura cohorte, custodiar la aprobación, separar los datos del release oficial, verificar fuentes y disponibilidad al corte, congelar elegibilidad y agrupaciones, y exportar el JSON de entrada para evaluar. La salida de la CLI va a stdout. Con entrada inválida, la CLI termina con código 2 y un diagnóstico. Usar las métricas junto con cobertura y denominadores. Los grupos pequeños y los percentiles extremos requieren cautela. La herramienta no ajusta modelos, no emite inferencia, no calcula intervalos ni vuelve a evaluar TEST. Una comparación favorable en un fixture verifica cálculos y flujo.
