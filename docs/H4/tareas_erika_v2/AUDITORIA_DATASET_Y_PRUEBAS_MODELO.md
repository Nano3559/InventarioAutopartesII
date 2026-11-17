# Auditoría del dataset 4.0.0 y pruebas de funcionamiento

RepuestoPro · Rama `erika` · 17 de noviembre de 2026, America/La_Paz.

**Dictamen:** GO para probar técnicamente Random Forest 4.0.0 y 4.1.1 D y comparar sus pronósticos en noviembre DEMO. **NO-GO para medir precisión independiente** con la evidencia y las cohortes actualmente identificadas.

## A. Identificación y procedencia

Se auditó únicamente el build `ml/demand/data/repuestopro_v2/4.0.0/calendar-20261116-01/`. Su manifiesto identifica el origen `ACADEMIC_SYNTHETIC_NOT_REAL_SALES`, la semilla 42, el generador de calendario, el catálogo congelado y las dependencias de procedencia. El release oficial referencia el SHA256 del manifiesto del dataset y la huella coincide. Coincidieron los **22/22** archivos enumerados en `checksums.sha256`.

[Manifiesto](../../ml/demand/data/repuestopro_v2/4.0.0/calendar-20261116-01/manifest.json) · [Checksums](../../ml/demand/data/repuestopro_v2/4.0.0/calendar-20261116-01/checksums.sha256) · [Generador y particiones](../../ml/demand/v2/calendar2026.py)

## B. Estructura y volumen

El catálogo de referencia contiene **62 productos**, de los cuales **56** figuran en `included_product_ids`. Ese conjunto coincide exactamente con los productos de la tabla supervisada. Seis referencias del catálogo quedan fuera de la cobertura. Hay **tres tiendas**, ubicaciones 5, 6 y 7, y **168 pares** producto–tienda. Las tablas conservan dos variantes por familia sintética.

| Archivo del build | Filas | Función |
| --- | ---: | --- |
| `dataset_supervisado.csv` | 14.112 | 43 columnas, incluidas características, metadatos y objetivo |
| `scenario_context.csv` y `escenarios_metadatos.csv` | 14.112 cada uno | Identidad, realización y familia |
| `closed_history_monthly.csv` | 42.336 | Tres meses exactos de historia por escenario |
| `opening_stock_snapshot.csv` | 14.112 | Stock vendible al corte |
| `daily_ledger.csv` | 428.736 | Entradas, ventas y balances diarios simulados |
| `price_plan_events.csv` | 14.654 | Segmentos de precios previstos |
| `cost_plan_events.csv` y `exchange_quote_events.csv` | 14.112 cada uno | Costos y cotización |
| `open_order_plan.csv` | 1.521 | Pedidos y reservas conocidos |
| `pending_shipment_plan.csv` y `receipt_outcomes.csv` | 10.492 y 10.102 | Planes de entrega y recepciones realizadas en la simulación |
| `base_mensual.csv` | 14.112 | Ventas realizadas sintéticas y fecha de disponibilidad |
| `decision_outputs.csv` | 0 | El build de datos conserva el esquema sin resultados de modelo |

El historial inicial cubre noviembre de 2024 a enero de 2025. Los meses objetivo supervisados abarcan febrero de 2025 a octubre de 2026. El release añade 168 snapshots DEMO de noviembre sin objetivo generado.

## C. Calidad cuantitativa

Se ejecutó el validador estructural existente y se contrastaron de forma independiente conteos, claves, dominios y cruces de las tablas CSV. En el cuadro, los conteos cero corresponden a los controles descritos.

| Control | Hallazgo |
| --- | --- |
| Duplicados | 0 filas idénticas en la tabla supervisada y 0 identificadores de escenario repetidos. Las 7.056 claves realización–mes–producto–tienda tienen exactamente 2 variantes. El validador de claves primarias no reportó fallos. |
| Faltantes supervisados | Solo dos campos tienen vacíos. `proporcion_por_mayor_mes_anterior`: **6.428 (45.55 %)**, en todos los casos coincide con ventas cero en el mes anterior. `dias_hasta_primera_entrada_plan`: **4.010 (28.42 %)**, en todos los casos coincide con cero unidades de entrada previstas. 0 objetivos o rezagos vacíos. |
| Campos condicionales de costo | En las 13.568 filas `SET_LANDED_COST_BS` faltan, como corresponde a ese modo, costo USD, flete, otros y referencia de cotización. Las 544 filas `SIMULATE_IMPORT_USD` contienen esos datos. `source_percentage` está vacío en las 14.112 filas y queda fuera del vector de modelo. |
| Cantidades y dominio numérico | 0 objetivos negativos, 0 cantidades negativas en los campos de balance diario inspeccionados y 0 infinitos en las características. Los negativos de seno, coseno y variaciones de precio representan valores válidos con signo. |
| Precios | En 14.654 segmentos se encontraron 0 incumplimientos de `0 < mayorista ≤ minorista` y `0 ≤ costo ≤ mayorista`. El validador confirmó continuidad de los segmentos y ponderación mensual del precio minorista. |
| Inventario | En 428.736 filas diarias hubo 0 fallos de `apertura + recibidas − vendidas = cierre` y 0 discontinuidades entre días del mismo escenario. Hubo 0 diferencias de stock inicial entre snapshot y tabla supervisada, y 0 ventas mensuales distintas de la suma diaria. |
| Reservas | 0 pedidos con reserva superior a pendientes, 0 envíos con reserva superior a unidades pendientes y 0 escenarios con suma de reservas de pedidos superior al stock inicial. |
| Identidad y relaciones | 0 diferencias de producto o tienda al contrastar 10 tablas con el contexto. 0 diferencias de familia, realización, mes objetivo o corte entre la fila supervisada y las referencias correspondientes. |
| Objetivo y restricciones de suministro | Los 14.112 resultados están cerrados y coinciden con los objetivos supervisados. Hay **6.144 ventas mensuales cero (43.54 %)**. En **3.792 filas (26.87 %)** la demanda latente del simulador supera las ventas. Esa variable sirve para diagnóstico y queda fuera del modelo. |

## D. Validación temporal

| Realización | Meses objetivo | Meses | Filas | Familias |
| --- | --- | ---: | ---: | ---: |
| TRAIN | Feb 2025–abr 2026 | 15 | 5.040 | 2.520 |
| VALIDATION | May–jul 2026 | 3 | 1.008 | 504 |
| TEST | Ago–oct 2026 | 3 | 1.008 | 504 |
| DEMO | Feb 2025–oct 2026 | 21 | 7.056 | 3.528 |

Cada realización contiene 336 filas por mes objetivo y conserva su calendario y sus familias. Los **42.336 registros de historia** corresponden a los meses t−3, t−2 y t−1, con cantidades idénticas a los rezagos publicados. Hubo **0 meses incompletos, 0 disponibilidades anteriores al cierre, 0 disponibilidades posteriores al corte y 0 referencias de snapshot de historia discordantes**. El objetivo queda disponible al comienzo del mes siguiente. TEST se inspeccionó estructuralmente y no se ejecutó inferencia ni se calcularon métricas predictivas sobre él.

La continuidad del libro es diaria dentro del escenario. Los estados de inventario de distintos meses son supuestos sintéticos independientes y no evidencian una cadena comercial continua de balances.

[Split](../../ml/demand/data/repuestopro_v2/4.0.0/calendar-20261116-01/split_manifest.json) · [Validador estructural](../../ml/demand/v2/validate_scenarios_v1.py)

## E. Compatibilidad con Random Forest 4.0.0

El artefacto `calendar-model-20261116-01` se cargó después de verificar release y datos. El vector contiene **18 campos numéricos y una categoría**, en el orden fijado por el manifiesto. El preprocesamiento aplica imputación mediana numérica con indicador de faltante y codificación one-hot de categoría. El comparador reprodujo exactamente el valor y motivo devueltos por la inferencia oficial en los 168 snapshots DEMO.

SHA256 del artefacto: `8d73bbfb769e432461f2a202e37842b47820a76627e46be3e4ba412e64562e1e`.

## F. Compatibilidad con Random Forest 4.1.1 D

El candidato D se cargó tras verificar su huella y el registro experimental. Recibe las mismas 19 entradas del snapshot y añade **media, desviación estándar poblacional y fracción de ceros** de sus tres rezagos mediante la función del entrenamiento. El comparador valida esos rezagos contra el historial publicado. La puerta común de rango se toma del release 4.0.0 y se aplica a ambos modelos para comparar la misma entrada. Ese resultado no acredita una política operativa propia para D.

SHA256 del candidato: `affafcffd98b4f67cd73416f803b4e062a487850a0465115174007692f52703c`.

[Release](../../ml/demand/reports/v2/4.0.0/calendar-model-20261116-01/release.json) · [Registro de D](../../ml/demand/experiments/model_4_1_1/evaluation/temporal-01.json) · [Comparador](../../ml/demand/experiments/model_4_1_1/comparator/README.md)

## G. Pruebas de funcionamiento

Se ejecutaron **7 pruebas focalizadas**, todas aprobadas. Cubren carga y huellas, orden y transformación de variables, entradas incompatibles, abstenciones, correspondencia con el runtime y AppTest de Streamlit. Una pasada adicional recorrió **168 snapshots**, ejecutó dos comparaciones por snapshot, exigió igualdad exacta y contrastó 4.0.0 con su runtime.

Desde PowerShell en la raíz del repositorio:

```powershell
Push-Location ml/demand
try {
  & ./.venv/Scripts/python.exe -B -c "import json; from v2.calendar2026 import BUILD; from v2.validate_scenarios_v1 import validate; r=validate(BUILD); print(json.dumps(r)); raise SystemExit(not r['valid'])"
} finally { Pop-Location }
$comparador = 'ml/demand/experiments/model_4_1_1/comparator'
& ml/demand/.venv/Scripts/python.exe -B -m unittest discover -v -s "$comparador/tests"
& ml/demand/.venv/Scripts/python.exe -B "$comparador/compare_models.py" --snapshot calendar-2026-53-6-november
& ml/demand/.venv/Scripts/python.exe -B "$comparador/compare_models.py" --snapshot calendar-2026-6-5-november
```

AppTest utiliza loopback interno. El entorno de prueba fue Python 3.11.0, scikit-learn 1.9.1, NumPy 2.4.6, pandas 3.1.0 y joblib 1.6.0.

## H. Resultados y hallazgos

| Verificación | Resultado |
| --- | --- |
| Validador estructural | **PASS**, cero errores, 14.112 filas, 7.056 familias |
| Cobertura conjunta en noviembre DEMO | **136/168 (80.95 %)** con dos pronósticos. **32/168** abstenciones de ambos por stock fuera del rango oficial. |
| Tensador de Correa, Tienda 2 | 4.0.0 **87.17**, D **80.02** unidades. Ambos elegibles, diferencia −7.15 unidades. |
| Snapshot `calendar-2026-6-5-november` | Ambos devuelven nulo y `OUTSIDE_TRAINING_RANGE`. |
| Errores y escritura | No se detectaron fallos en los controles examinados. Los faltantes de entrada corresponden a casos documentados. El inventario protegido de 554 archivos mantuvo la misma huella agregada `4d5098398a45d8c3879ba08aad7dbc08c3c7696740a5cbbb6fa5e7268991fc27`. D conservó su huella. |

## I. Disponibilidad para evaluación independiente

| Fuente localizada | Evidencia y estado |
| --- | --- |
| TRAIN y VALIDATION 4.0.0 | Usados para ajuste, selección o experimentos 4.1.0 y 4.1.1. Excluidos como reserva independiente. |
| TEST 4.0.0 | Etiquetado y consumido por la evaluación oficial de intento único. Excluido de nuevas evaluaciones para esta tarea. |
| Noviembre DEMO 4.0.0 | Entradas publicadas para 168 pares, con **0 objetivos de noviembre**. Sirve para pruebas de funcionamiento y comparación de pronósticos. |
| DEMO histórico 4.0.0 | Contiene **7.056 etiquetas sintéticas** entre febrero de 2025 y octubre de 2026, incluidas **3.528 variantes BASE**. El manifiesto acredita separación del ajuste y selección oficiales. Parte de esa realización respalda la demostración histórica. Queda sin acreditar y autorizar una reserva nueva que identifique filas sin uso previo para evaluación, dependencias entre familias y reconstrucción equivalente al corte para ambos modelos. |
| Builds históricos 2.x y 3.0.0 | Releases con otros calendarios y contratos. La revisión previa M41-02/03 dejó 3.0.0 condicionado a autorización, linaje y equivalencia del esquema. |
| Fixtures, resultados experimentales y reportes | Pruebas sintéticas de comportamiento, resultados de particiones de desarrollo o evidencias guardadas. No se localizó una cohorte posterior etiquetada con autorización y procedencia completas. |

**Conclusión:** no se identificó una cohorte local **nueva, etiquetada, autorizada y verificablemente independiente** para medir el error predictivo de ambos modelos. La coincidencia de esquema y la separación de una realización por sí solas no satisfacen los controles de M41-03. No se ejecutó evaluación independiente.

[Ficha de elegibilidad M41-03](H4_M41_03_FICHA_COHORTES.md) · [Evaluación 4.1.0](../../ml/demand/experiments/model_4_1_0/reports/COMPARACION_EXPERIMENTAL.md) · [Folds TRAIN de 4.1.1](../../ml/demand/experiments/model_4_1_1/reports/COMPARACION_TEMPORAL.md)

## J. Limitaciones

La auditoría valida integridad estructural y comportamiento en el release sintético. Las ventas están condicionadas por disponibilidad. Variantes de una misma familia comparten datos y los conteos de filas no representan igual cantidad de observaciones independientes. Las 32 abstenciones describen el dominio de los snapshots publicados. Los dos pronósticos del ejemplo carecen de un resultado de noviembre para conocer su error.

## K. Recomendaciones

1. Registrar una cohorte candidata con la ficha M41-03, identificadores de producto–tienda, meses cerrados y observados verificables, fechas de disponibilidad, procedencia y hashes.
2. Auditar usos previos, solapamiento por familia, disponibilidad al corte y equivalencia del adaptador al esquema 4.0.0 antes de designar una reserva.
3. Si se acredita esa reserva, preparar comparación pareada con la misma población y fecha de corte, MAE primario, RMSE, error firmado y cobertura, con abstenciones separadas. Pedir autorización antes de ejecutar la evaluación.

## L. Dictamen

| Posibilidad | Dictamen |
| --- | --- |
| Probar funcionamiento de 4.0.0 y D | **GO**, carga y comportamiento reproducidos. |
| Comparar sus pronósticos localmente | **GO**, únicamente con entradas DEMO autorizadas y elegibles. |
| Evaluar precisión predictiva independiente o declarar una mejora | **NO-GO**, falta una reserva elegible y observada. |

La auditoría escribió únicamente este informe. No se modificaron datos, snapshots, artefactos, runtime, frontend, backend, resultados TEST ni registros comerciales. No hubo entrenamiento, migraciones ni acceso a Neon.
