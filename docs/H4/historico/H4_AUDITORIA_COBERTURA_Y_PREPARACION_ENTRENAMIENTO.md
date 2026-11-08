# H4. Auditoría de cobertura y preparación para entrenamiento

Fecha: 3 de noviembre de 2026. Versión revisada: 1.0.0-escenarios. Alcance: archivos locales, generador, pruebas y documentación. No se conectó a Neon ni se entrenó un modelo.

La [segunda revisión integral para una tienda real](../../H3/cierre_saneamiento/SEGUNDA_REVISION_INTEGRAL_TIENDA_REAL.md) amplía esta auditoría hacia caja, cobros, stock físico, permisos, continuidad y recuperación. Sus riesgos operativos son adicionales al contrato numérico del dataset.

## Dictamen

**El dataset actual es técnicamente utilizable para un experimento académico limitado de regresión sobre ventas sintéticas. Su cobertura no permite declarar resueltos los casos normales, adversos y ambiguos de la implementación completa.**

Los CSV revisados no presentan un defecto estructural que obligue a desecharlos. Tienen las columnas, fechas, cantidades y dependencias temporales previstas. Sin embargo, los casos ambiguos siguen siendo fichas conceptuales, los eventos adversos no cubren cambios persistentes y el validador tiene controles incompletos. Por eso no se concede aprobación integral de robustez. Ningún resultado obtenido sobre estos datos certificará precisión comercial real.

Este dictamen distingue la aptitud del archivo actual de la madurez del proceso que genera y consume datos. No autoriza ejecutar el entrenamiento en esta tarea.

## Fuentes y método

Se revisaron la [definición de Fase 1](H4_FASE1_ESTRUCTURA_DATASET_Y_RIESGOS.md), el [informe de fallas](H4_FALLAS_Y_ESCENARIOS_DATASET.md), el [generador](../../../ml/demand/generate_synthetic.py), sus [pruebas](../../../ml/demand/test_generate_synthetic.py), la referencia de catálogo y todos los archivos de ml/demand/data/escenarios_v1. Se contrastó el alcance con los campos de Product, Location, Sale, SaleItem, Inventory y Return del schema actual. No se modificó código de aplicación, Prisma ni el generador.

Se leyeron los CSV guardados, no solo las estructuras que devuelve el generador en memoria. Se comprobaron hashes, claves, tipos, fechas, cantidades, cobertura, lags y metadatos. Los meses anteriores se reconstruyeron además con aritmética de calendario independiente de la función que los genera.

Se repitieron las siete pruebas existentes. Una reproducción en una carpeta temporal coincidió con los seis hashes de archivos originales. Las copias temporales no sustituyeron el dataset. Las pruebas adicionales del catálogo y del límite numérico se realizaron en memoria, sin guardar sus registros inválidos. La inspección de validation y test fue descriptiva, sin comparar errores predictivos ni elegir modelos.

## Integridad y cantidades verificadas

| Comprobación | Resultado |
|---|---|
| Referencia del catálogo | 56 productos incluidos, IDs 1 a 56. Se conservan 57 a 62 como reservados |
| Tiendas incluidas | IDs 5, 6 y 7, cada una con 1.176 filas supervisadas |
| Base mensual | 4.032 filas, 168 combinaciones producto/tienda y 24 meses completos |
| Panel supervisado | 3.528 filas, nueve columnas y 21 meses objetivo |
| Clave del panel | Sin duplicados de productId, locationId y mes_objetivo |
| Calendario y target | Enero de 2025 a septiembre de 2026, con target igual al total del propio mes |
| Lags | Coinciden con los tres meses anteriores exactos del mismo producto y tienda |
| Cantidades | Enteros no negativos. Target entre 0 y 69, con 422 ceros |
| Separación de features | Solo tres lags y mes_sin/mes_cos. Escenario, clase y rotación quedan fuera |
| Metadatos de escenarios | 4.032 claves únicas y correspondencia con la base mensual |
| Integridad de archivos | Los seis hashes de artefactos, el hash del catálogo y el del generador coinciden con el manifiesto |
| Reproducción | Seis de seis archivos reproducidos con hashes iguales. La fecha del manifiesto puede cambiar |
| Pruebas existentes | Siete aprobadas, ninguna fallida en la ejecución de esta auditoría |

El catálogo procede de la lectura de Neon documentada el 27 de octubre de 2026. No se volvió a consultar y no se certificó su vigencia actual. Estos productos son referencias del proyecto, no evidencia de operaciones comerciales durante los meses simulados.

## Cobertura de casos normales y adversos

| Conjunto | Filas | Normales | Adversas válidas |
|---|---:|---:|---:|
| Historia inicial | 504 | 372 | 132 |
| TRAIN | 2.520 | 1.815 | 705 |
| VALIDATION | 504 | 357 | 147 |
| TEST | 504 | 353 | 151 |
| Total base | 4.032 | 2.897 | 1.135 |

En el panel supervisado hay 2.525 filas normales y 1.003 adversas válidas. Las cantidades anteriores de 2.897 y 1.135 corresponden a la base de 24 meses, que también contiene la historia inicial. No deben presentarse como cantidades del entrenamiento ni del panel supervisado.

| Escenario adverso | TRAIN | VALIDATION | TEST | Evaluación de cobertura |
|---|---:|---:|---:|---|
| Pedido mayorista extraordinario válido | 107 | 28 | 23 | Presente en los tres conjuntos. Se conserva el pico sin borrarlo |
| Caída de ventas confirmada | 134 | 25 | 33 | Presente, pero actúa sobre meses aislados, no sobre un régimen permanente |
| Pico temporal confirmado | 123 | 35 | 31 | Presente, sin una campaña comercial documentada como causa |
| Mes cero confirmado | 281 | 47 | 52 | Presente y válido bajo el supuesto de captura completa |
| Serie completamente cero | 30 | 6 | 6 | Dos combinaciones persistentes. Útiles para comprobar límites de métricas |
| Serie constante positiva | 30 | 6 | 6 | Dos combinaciones persistentes. No equivale a cubrir todo tipo de baja variación |

La cobertura normal es adecuada para el experimento inicial: combina niveles de rotación, diferencias entre tiendas, ruido, ciclo anual y tendencia moderada. Todos son supuestos de simulación. La presencia de estos componentes no demuestra que un algoritmo pueda anticiparlos correctamente ni que reproduzcan el negocio real.

La cobertura adversa es parcial. Faltan cambios persistentes de nivel, recuperación posterior a una crisis, varios meses consecutivos de caída, estacionalidad que cambia entre años y episodios de disponibilidad con fechas explícitas. Los eventos aleatorios actuales comparten la misma lógica durante todo el periodo. No se evaluó un cambio de régimen entre entrenamiento y meses posteriores.

| Rotación simulada | Filas supervisadas | Ceros | Media de unidades |
|---|---:|---:|---:|
| Baja | 1.197 | 393 | 2,6901 |
| Media | 1.197 | 8 | 9,1278 |
| Alta | 1.134 | 21 | 18,9841 |

La baja rotación tiene una presencia importante de ceros y no se eliminó para mejorar indicadores. Hay que conservar la evaluación por grupo en una fase posterior. Rotación es un metadato latente del generador, no una feature autorizada.

## Cobertura de casos ambiguos

Los diez casos de casos_grises.json están separados físicamente del CSV supervisado y tienen apto_entrenamiento false. Esto evita mezclarlos por una lectura directa de ese archivo. Sin embargo, **no constituye una prueba ejecutable de detección o exclusión de observaciones ambiguas**.

Todas las fichas utilizan productId 1, locationId 5 y mes_objetivo 2026-07. Esa clave también existe en el panel con lags 15, 21 y 20, y target 26. Los diez case_id distinguen fichas de escenario, pero no diez observaciones ambiguas independientes. No se encontró una unión que las haya introducido al entrenamiento. Tampoco puede afirmarse que esas diez claves se hayan retirado del panel, porque son la misma clave y permanece allí.

Si las fichas representan diez situaciones alternativas, deben declararse como universos de prueba independientes y aportar los datos que producen cada situación. Actualmente no contienen evidencia estructurada de falta de stock, captura parcial, meses de historia, inicio de operaciones o fecha real de conocimiento. El test comprueba el número de fichas y su bandera de exclusión, pero no verifica una respuesta del sistema frente a esos hechos.

| Caso gris actual | Qué falta para una prueba verificable |
|---|---|
| SIN_STOCK | Ventas observadas, intervalo de indisponibilidad y definición de qué se desconoce |
| CAPTURA_INCOMPLETA | Cobertura del mes, registros parciales y fecha de cierre pendiente |
| PRODUCTO_SIN_HISTORIA | Secuencia con menos de tres meses, sin rellenar los faltantes |
| TIENDA_SIN_HISTORIA | Fecha de apertura o historia insuficiente de la ubicación |
| DESCATALOGACION_DUDOSA | Evidencia de vigencia desconocida y regla de revisión |
| ORIGEN_DEMO_NO_CERTIFICADO | Procedencia desconocida expresada como dato de entrada, no solo como descripción |
| CARGA_RETROACTIVA | Fecha de venta, fecha de registro y fecha de corte que permitan demostrar el orden |
| DEVOLUCION_TARDIA | Venta original y devolución posterior separadas, con cantidades y fechas |
| PROMOCION_NO_DOCUMENTADA | Observaciones del pico y evidencia comercial ausente |
| SUSTITUCION_NO_CONFIRMADA | Dos productos y relación no confirmada, sin trasladar ventas automáticamente |

target_demanda_real null no equivale a target_ventas_mes desconocido. Un mes sin stock puede tener ventas observadas conocidas aunque no se conozca la demanda perdida. Una devolución tardía tampoco vuelve desconocido el total bruto vendido. Cada caso debe indicar si falta el target de ventas, si falta una feature o si solo existe una limitación para interpretar demanda. No todos requieren la misma respuesta ni la exclusión automática.

No se recomienda introducir cantidades negativas o etiquetas inventadas para completar estos casos. La suite ambigua debe permanecer separada del panel numérico, con una política explícita de revisión, abstención o conservación de ventas brutas. La futura evaluación deberá contar también los casos sin predicción para no ocultar falta de cobertura.

## Hallazgos del validador y de las pruebas

| Severidad | Hallazgo y evidencia | Alcance del problema | Acción recomendada |
|---|---|---|---|
| ALTA | La lista included_product_ids se toma como autoridad sin contrastarla con products del catálogo. Una referencia alterada que sustituye el ID 1 por 999999 permite construir y validar datos para ese ID inexistente en products | No hay IDs inexistentes en el archivo actual. El hueco afecta futuras entradas de catálogo | Comprobar pertenencia, unicidad, tipos y exclusiones de los IDs antes de generar |
| ALTA | Los grises son descripciones y las siete pruebas no ejecutan su comportamiento esperado | No valida el manejo de ambigüedad ni la falta de historia | Crear entradas estructuradas independientes y pruebas de políticas, sin mezclar grises con entrenamiento |
| MEDIA | El contrato declara int64, pero validate acepta un valor 2 elevado a 70 si coincide entre base y lag | El archivo actual tiene cantidades pequeñas. No hay desbordamiento observado | Validar el límite entero y los errores de conversión antes de aceptar archivos |
| MEDIA | cantidad_tiendas queda fijada en tres y las fichas grises fijan locationId 5, aunque el comando admite otro --catalog | El catálogo actual sí tiene tres tiendas. Cambiar el catálogo podría producir metadatos o fichas inconsistentes | Derivar cantidades e identidades del catálogo validado |
| MEDIA | El límite de 150 unidades se comprueba en el test para seed 42, pero no es una restricción aplicada por validate | No falla esta generación, cuyo máximo es 69 | Distinguir rango observado, límite del contrato y umbral de plausibilidad. Acordar la política antes de usar otros parámetros |
| MEDIA | Los casos inválidos parten de una sola fila y alteran un campo cada vez | Cubren quince fallas simples, no combinaciones, errores de lectura o todos los valores no finitos | Ampliar pruebas de ingestión CSV, columnas ausentes, booleanos, infinitos y referencias corruptas |
| MEDIA | La prueba temporal existente cambia manualmente target y base, sin volver a ejecutar la construcción de features | No prueba por sí sola todos los caminos de fuga de información | Conservar la comprobación independiente de calendario y añadir pruebas del futuro pipeline de features |
| BAJA | Solo se conserva una seed y una versión de supuestos para la comparación inicial | Adecuado para reproducir un experimento, insuficiente para afirmar estabilidad general | Evaluar sensibilidad en experimentos separados sin elegir la seed que mejore test |

Los quince ejemplos inválidos guardados fueron rechazados con el motivo esperado. Ese resultado sigue siendo válido, aunque no cubra los huecos adicionales. Los probes del catálogo alterado y del entero fuera de rango demostraron aceptación no deseada en memoria. No se incorporaron al CSV ni se corrigió el generador durante esta auditoría.

## Qué falta y cuándo debe resolverse

| Momento | Condición |
|---|---|
| Antes de reutilizar el generador con otra referencia | Validar el catálogo completo, el límite numérico y los metadatos derivados |
| Antes del experimento numérico básico | Congelar los hashes actuales, documentar las cinco features permitidas y los cortes temporales. Ajustar cualquier scaler o encoder solo con TRAIN cuando se implemente |
| Antes de afirmar cobertura de ambiguos | Convertir las fichas en entradas verificables, definir políticas por tipo de incertidumbre y probar sus respuestas |
| Antes de afirmar robustez adversa | Añadir una suite separada de cambios persistentes, disponibilidad, capturas parciales e inicio sin historia. No alterar test repetidamente para favorecer un modelo |
| Antes de seleccionar un modelo | Acordar criterios de mejora frente al baseline y mostrar errores por tienda, rotación y escenario. Mantener test fuera de la selección |
| Antes de uso comercial | Reunir datos reales certificados y disponibilidad histórica suficiente. Validar reglas comerciales e integración |

Los cambios persistentes y los casos ambiguos no tienen que convertirse en filas del mismo archivo limpio. Pueden formar suites separadas con sus propios contratos y resultados esperados. Su función es probar límites de la implementación. Una ampliación futura debe conservar la versión actual y registrar diferencias, sin reconstruirla silenciosamente.

## Estado final de esta revisión

**Datos numéricos actuales: listos con limitaciones para un entrenamiento académico básico, cuando se autorice. Cobertura integral de normales, adversos y ambiguos: todavía no lista. Uso comercial: no validado.**

La auditoría aporta integridad y cobertura descriptiva, no métricas predictivas. No se calcularon MAE, RMSE o R², no se ajustó un scaler ni se ejecutó baseline, LinearRegression, Random Forest o MLP. No se modificaron el catálogo, los CSV, el manifiesto o el generador. Las siete pruebas locales aprobaron y la reproducción temporal coincidió con los originales. Neon permaneció sin conexión. No hubo commit, push o deploy.
