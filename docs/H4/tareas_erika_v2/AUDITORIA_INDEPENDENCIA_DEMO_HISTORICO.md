# Auditoría de independencia del DEMO histórico 4.0.0

**Dictamen: GO CON LIMITACIONES para una evaluación exploratoria retrospectiva, previa autorización.** El DEMO histórico contiene etiquetas de una realización sintética separada y se puede preparar un emparejamiento de 4.0.0 contra 4.1.1 D. Comparte perfiles, calendario y mecanismo generador con el desarrollo y el TEST oficial. Parte de sus observados ya se publicó para la demostración. Estos factores impiden presentar el resultado futuro como validación externa independiente.

**Alcance de esta auditoría:** solo lectura estructural de 4.0.0, manifests, código y registros de experimentos. Se usaron etiquetas para verificar disponibilidad y coincidencias de contenido. No se cargaron modelos, no se ejecutó inferencia, no se volvió a evaluar TEST y no se calcularon errores.

## 1. Procedencia

El build es `calendar-20261116-01`. El generador llama al motor sintético de escenarios con prefijo `calendar-4.0.0`. Usa semilla raíz **42** y deriva cada estado de un SHA256 de la semilla y sus claves. Para cada producto y tienda, el perfil se deriva con la clave `profile` y **sin** el nombre de la realización. Nivel, probabilidad base de ocurrencia, elasticidad supuesta y precio inicial son compartidos. Los niveles proceden de `[4, 12, 35, 90]`, las elasticidades supuestas de `[0, −0.4, −0.8, −1.2]` y los precios iniciales de `[80, 120, 250, 600]`. La calibración de patrones usa parámetros agregados de la receta. No implica estimación comercial de elasticidad.

| Componente | Separación o dependencia |
| --- | --- |
| Estado mensual, demanda y redondeo | Las claves incluyen producto, tienda, realización y mes. Cada realización reinicia su historial y trayectoria de precio desde el perfil común. |
| Mundos y calendario | Cada realización recorre noviembre de 2024 a octubre de 2026 para construir su propia historia y publica las filas del split correspondiente. |
| Productos y tiendas | Las cuatro realizaciones usan los mismos 56 productos, tres tiendas y 168 pares. |
| Familias y escenarios | ID separado por realización. Dentro de cada familia, BASE y una intervención comparten demanda, shocks de redondeo e historia anterior; se simulan sus ventas bajo condiciones distintas. |
| Etiquetas | `base_mensual.csv` guarda ventas realizadas sintéticas de cada escenario. Las 7.056 de DEMO están cerradas y disponibles al inicio del mes siguiente. El resultado de noviembre de 2026 no existe. |
| Publicación | El `recorded_at` de las 7.056 filas es posterior al corte simulado. Se trata de un replay retrospectivo con fechas de disponibilidad simuladas, sin evidencia de emisiones prospectivas. |

[Generador de calendario](../../ml/demand/v2/calendar2026.py) · [Motor y claves](../../ml/demand/v2/generate_scenarios_v1.py) · [Receta del build](../../ml/demand/data/repuestopro_v2/4.0.0/calendar-20261116-01/recipe.json)

## 2. Cruces e independencia

DEMO abarca febrero de 2025 a octubre de 2026: **21 meses, 3.528 familias y 7.056 filas**. Incluye una BASE por familia. Comparé la existencia de cada fila DEMO frente al conjunto de claves distintas de la otra partición. Cada cifra de coincidencias cuenta filas DEMO como máximo una vez por columna. Se normalizaron tipos numéricos y valores ausentes antes de comparar las 19 características.

| Referencia | Periodo publicado | Claves comunes producto–tienda–mes | IDs de escenario / familia comunes | Mismas 19 entradas | Mismas entradas y etiqueta | Misma clave y 19 entradas y etiqueta |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| TRAIN | Feb 2025–abr 2026 | 2.520 | 0 / 0 | 18 | 9 | 0 |
| VALIDATION | May–jul 2026 | 504 | 0 / 0 | 4 | 4 | 0 |
| TEST | Ago–oct 2026 | 504 | 0 / 0 | 2 | 2 | 0 |

| Referencia | Misma clave y 3 rezagos | Misma clave y etiqueta | Misma clave, rezagos y etiqueta |
| --- | ---: | ---: | ---: |
| TRAIN | 356 | 1.496 | 199 |
| VALIDATION | 64 | 327 | 39 |
| TEST | 76 | 285 | 38 |

Las coincidencias parciales incluyen ventas cero y estados discretos generados bajo parámetros comunes. La ausencia de identidades compartidas y el código respaldan realizaciones distintas. Los conteos por sí solos no demuestran independencia estadística ni una copia de etiquetas. Dentro de DEMO, las **3.528 parejas** tienen los mismos tres rezagos, **2.752** comparten etiqueta y **1.560** comparten las 19 entradas y la etiqueta. Tratar ambas variantes como observaciones independientes sobrerrepresentaría su historia común.

| Dimensión | Evaluación de la evidencia |
| --- | --- |
| Independencia de registros | IDs disjuntos y resultados simulados por realización. Hay colisiones de contenido completo entre pares distintos, además de coincidencias parciales bajo la misma clave. |
| Independencia temporal | DEMO completo se solapa con todos los meses oficiales. Agosto–octubre DEMO es posterior al TRAIN y a la VALIDATION de 4.0.0 y posterior al TRAIN de D. Abarca exactamente el periodo del TEST oficial. Los modelos estaban ya fijados para esta auditoría, pero los meses se reconstruyeron retrospectivamente. |
| Independencia respecto a selección | El código de 4.0.0 ajusta con TRAIN y selecciona con VALIDATION. 4.1.0 usa ambos bloques; 4.1.1 selecciona en folds internos de TRAIN y reajusta con TRAIN. En el código y registros revisados no se encontró uso de DEMO como puntuación para seleccionar esos modelos. La revisión no puede certificar consultas manuales fuera del repositorio. |
| Exposición previa | Los 1.680 observados BASE de enero a octubre de 2026 se publicaron en el historial mostrado por los snapshots de noviembre. Octubre se reproduce usando los datos ya publicados de ese mundo. El ejemplo DEMO y las pruebas de funcionamiento previas no acreditan una reserva ciega. |
| Validez externa | Los mismos perfiles, calendario, catálogo, fórmulas y supuestos limitan la generalización a productos, tiendas y fuentes nuevas. La semilla raíz común con claves distintas no cambia esa limitación. |

[Validación de particiones previa](AUDITORIA_DATASET_Y_PRUEBAS_MODELO.md) · [4.1.0](../../ml/demand/experiments/model_4_1_0/training/run_experiment.py) · [4.1.1](../../ml/demand/experiments/model_4_1_1/training/run_temporal.py) · [Criterios M41-03](H4_M41_03_FICHA_COHORTES.md)

## 3. Disponibilidad temporal y recomposición de entradas

Se contrastaron las fechas del evento `available_at` con el primer instante del mes objetivo, UTC−04:00. Los planes pueden tener vigencia posterior al corte si ya se conocían en ese momento bajo el calendario sintético.

| Entrada o fuente | Filas DEMO | Disponibilidad posterior al corte | Verificación adicional |
| --- | ---: | ---: | --- |
| Historial mensual | 21.168 | 0 | Los meses t−3, t−2 y t−1 y sus cantidades coinciden con las 7.056 filas. La proporción mayorista coincide con t−1 y queda ausente cuando su total es cero. |
| Precios previstos | 7.327 | 0 | Los precios BASE coinciden en ambas modalidades. La duración del cambio coincide. Al rederivar fracciones ponderadas desde eventos redondeados, 45 minoristas y 148 mayoristas difieren más de 1e−10, con máximos de 4.86e−7 y 5.72e−7. BASE coincide exactamente. El generador usa los precios de intervención antes de redondear el evento publicado. |
| Stock inicial | 7.056 | 0 | Coincide con stock vendible al corte. Los días sin stock anteriores coinciden en 6.720 filas cuyo mes BASE previo está publicado. En las primeras 336 proceden del calentamiento del mismo mundo, según el generador. |
| Pedidos y reservas | 757 | 0 | Compromisos por modalidad dentro del mes y reservas de vencimiento posterior recompuestos sin diferencias. |
| Entregas previstas | 5.248 | 0 | Cantidad prevista elegible y días a la primera entrada recompuestos sin diferencias. |
| Logística | 7.056 | 0 | Plazos y política describen el plan. Esos plazos directos quedan fuera del vector de ambos bosques. |
| Calendario y categoría | 7.056 | Calculables al corte | Seno, coseno y categoría de catálogo coinciden en todas las filas. |
| Recepciones realizadas | 5.051 | **3.361** | Son resultados del simulador y quedan fuera del vector. Las características de entradas se reconstruyeron únicamente desde planes. |
| Objetivo mensual y stockouts del mes objetivo | 7.056 | **7.056** | El objetivo se conoce al cierre y se usa solo como etiqueta de una eventual evaluación. El predictor de stockout usa t−1. |

La revisión de las fuentes, el orden y el código de construcción no encontró variables posteriores al corte entre las 19 entradas. La trazabilidad temporal se sostiene dentro de la simulación. Los sellos sintéticos no certificarían esa misma disponibilidad para transacciones reales.

## 4. Compatibilidad y cobertura estructural

El release 4.0.0 fija **18 características numéricas y una categoría**. Las siete categorías de DEMO están presentes en TRAIN. Los únicos faltantes del vector son proporción mayorista (3.246) y días a primera entrada (2.005), admitidos por el preprocesamiento documentado. Los tres rezagos están completos. El registro de D añade media, desviación estándar poblacional y fracción de ceros derivadas de esos mismos rezagos. Su artefacto y el de 4.0.0 pueden recibir los vectores en su orden documentado, mediante el adaptador offline y sin modificar archivos.

| Población DEMO | Filas | Dentro de cotas 4.0.0 | Fuera de cotas |
| --- | ---: | ---: | ---: |
| BASE e intervenciones, 21 meses | 7.056 | 7.035 | 21 |
| Solo BASE, 21 meses | 3.528 | 3.520 | 8 |
| Solo BASE, agosto–octubre 2026 | 504 | 504 | 0 |

Los 21 casos fuera de cotas corresponden a rezagos y a cinco variaciones mayoristas ponderadas. El conteo es una comprobación de elegibilidad de entrada y no una cobertura de pronósticos medida. El runtime HTTP y el comparador publicado admiten los snapshots de noviembre. Los meses históricos requieren un recorrido offline autorizado, con validación de las características y las etiquetas por separado. Para D se propone la misma puerta de rango de 4.0.0, sin atribuirle una política operativa propia.

## 5. Protocolo propuesto · Sin ejecutar

1. **Fijar población por regla reproducible.** Seleccionar exactamente las 504 filas de `dataset_supervisado.csv` con `realization_id == "DEMO"`, `scenario_id` terminado en `-BASE` y `mes_objetivo` en `2026-08`, `2026-09` o `2026-10`. Verificar un escenario por par y mes. Fijar la lista ordenada y huella antes de ejecutar. BASE excluye la variante de intervención de cada familia y, en esta ventana, evita las diferencias de redondeo de precios.
2. **Conservar modelos congelados.** Usar exclusivamente 4.0.0 `calendar-model-20261116-01` y D `temporal-01`. Verificar SHA256 y orden de características. Comparar desde la misma fila al corte con el adaptador de tres resúmenes para D y **Lag1** del mes cerrado t−1. Separar las etiquetas hasta terminar y congelar las emisiones.
3. **Evaluar sobre filas comunes.** MAE como métrica primaria, RMSE, R² cuando exista variación suficiente y error firmado como complementos. Registrar denominador total, cobertura, abstenciones por método y sus causas. Calcular los errores pareados del bosque oficial, D y Lag1 sobre la intersección de emisiones. Dejar las abstenciones sin valor y reportarlas aparte. Mostrar resultados por mes, tienda y patrón de demanda con sus denominadores.
4. **Control de sensibilidad predeclarado.** Repetir el resumen excluyendo `family-DEMO-52-7-2026-08-BASE` del cálculo secundario. Sus 19 entradas y etiqueta cero coinciden con una familia TEST de otro producto y tienda, `family-TEST-27-5-2026-08`, en BASE y COST_ONLY. El análisis principal conserva las 504 filas. Este control evita decidir exclusiones tras conocer errores.
5. **Interpretación y autorización.** Informar diferencia pareada de MAE, comportamiento por mes y cobertura; una reducción en esta ventana sería evidencia exploratoria del mismo generador. Reportar la repetición de los mismos 168 pares durante tres meses y la exposición histórica de las etiquetas. Quedan fuera la promoción y la generalización comercial. Solicitar aprobación antes de ejecutar. Para evidencia externa, registrar una cohorte con fuente y periodo nuevos según M41-03.

## 6. Dictamen e integridad

| Decisión | Resultado |
| --- | --- |
| Comparación exploratoria de 4.0.0 contra D | **GO CON LIMITACIONES**, sujeto a la autorización del protocolo anterior |
| Validación externa, prospectiva o de reserva ciega independiente | **NO-GO** |
| Evaluación en esta tarea | **NO EJECUTADA** |

Se compararon huellas antes y después. El inventario de 554 archivos protegidos mantuvo el SHA256 agregado `4d5098398a45d8c3879ba08aad7dbc08c3c7696740a5cbbb6fa5e7268991fc27`. El modelo 4.0.0 conserva `8d73bbfb769e432461f2a202e37842b47820a76627e46be3e4ba412e64562e1e` y D `affafcffd98b4f67cd73416f803b4e062a487850a0465115174007692f52703c`. Solo se escribió este informe.
