> ARCHIVO HISTÓRICO. Esta propuesta dejó de estar vigente el 3 de noviembre de 2026. La guía oficial es [H4_IMPLEMENTACION_MODELO_PREDICTIVO.md](../../H4_IMPLEMENTACION_MODELO_PREDICTIVO.md). Se conserva el contenido anterior como antecedente. Se adaptan los enlaces locales y la puntuación, sin cambiar las decisiones históricas.

# H4. Plan por fases, dataset, predicción y algoritmo

Fecha de revisión: 27 de octubre de 2026. Estado: propuesta para exposición. La implementación de H4 continúa pendiente de autorización.

Proponemos estimar las unidades que un producto podría vender el próximo mes en una tienda. Utilizaremos inicialmente datos sintéticos. Compararemos una referencia ingenua, LinearRegression y RandomForestRegressor. Random Forest será el candidato principal, sin declararlo ganador antes de evaluar resultados.

## 1. Estado actual del proyecto

Esta síntesis respalda la [propuesta detallada de H4](H4_MODELO_PREDICTIVO_PROPUESTA_DETALLADA.md), sin reemplazarla. Se contrastó con el código actual, la [auditoría](../AUDITORIA_MODELO_PREDICTIVO_H4.md), el [plan de saneamiento](../../../H3/cierre_saneamiento/PLAN_SANEAMIENTO_REPUESTOPRO_PRE_H4.md), el [plan de trabajo de Erika](H4_PLAN_DE_TRABAJO.md) y Ejercicio 1.pdf. Este PDF describe el sistema comercial. Los algoritmos y el avance aproximado del 70 % proceden de la propuesta del equipo y las indicaciones transmitidas sobre H4.

La revisión comenzó con el árbol de trabajo limpio, en a9ff618, después del PR 50. Frente a b1003a1, el único archivo incorporado es H4_PLAN_DE_TRABAJO.md, agregado por Erika en b20b96a. Aporta responsables y un cronograma preliminar, sin modificar código, Prisma ni migraciones. No cambia el problema predictivo. Esta revisión precisa dos aspectos de ese checklist: el promedio de tres meses queda fuera de las entradas iniciales y las reposiciones predictivas se reservan para H5. El cronograma no autoriza comenzar la implementación.

El código conserva SaleItem.quantity como cantidad vendida, Sale.saleDate como fecha y Sale.locationId como ubicación de la venta. Las tiendas son registros de Location con type TIENDA. Los reportes utilizan la zona America/La_Paz. Return registra las devoluciones por separado. Inventory.stock representa stock actual, no una serie histórica. POR MENOR utiliza Product.price1, POR MAYOR utiliza Product.wholesalePrice y Product.price2 permanece como legacy. No se deducirá el modo histórico comparando precios actuales con SaleItem.unitPrice. Sale.type identifica el flujo NORMAL o MAYOR, no necesariamente el modo comercial de cada línea.

La auditoría previa registró 247 ventas entre marzo y octubre de 2026, con octubre incompleto y procedencia comercial o demo sin certificar. Son cifras de una revisión fechada, no una consulta nueva a Neon. Por eso no se considera suficiente historial real certificado para este primer experimento.

## 2. Plan por fases

La definición documental de la primera fase está en [H4. Fase 1: estructura del dataset y riesgos](../H4_FASE1_ESTRUCTURA_DATASET_Y_RIESGOS.md).

Actualización del 3 de noviembre de 2026: la solicitud posterior del equipo permite generar datos de prueba locales. La primera generación y su separación entre casos positivos, negativos y grises están documentadas en [fallas y escenarios del dataset](../H4_FALLAS_Y_ESCENARIOS_DATASET.md). No se ha entrenado ningún modelo. Los estados anteriores describen la propuesta antes de esta autorización.

| Fase | Trabajo previsto | Resultado esperado |
|---|---|---|
| 1. Comprensión y preparación | Revisar ventas, productos, tiendas, fechas, cantidades y calidad. Definir entradas, resultado objetivo y reglas de exclusión | Estructura final del dataset definida |
| 2. Construcción del dataset | Simular 24 meses con productos reales del catálogo, tiendas reales, seed 42, tendencia, estacionalidad, ruido, distintas rotaciones y ceros | Dataset reproducible, identificado como sintético |
| 3. Preparación para entrenamiento | Construir tres lags, calendario y target. Separar meses en orden temporal. Ajustar las transformaciones solo con entrenamiento | Datos preparados sin información futura |
| 4. Entrenamiento y comparación | Evaluar baseline ingenuo, LinearRegression y RandomForestRegressor con MAE, RMSE y R² | Comparación documentada sobre las mismas fechas |
| 5. Selección y demostración H4 | Elegir con validación, evaluar test al final, guardar modelo, configuraciones, métricas, versiones, experimentos y prompts. Crear una predicción con primera visualización | Experimento reproducible, aproximadamente 70 % funcional de H4 |
| 6. Integración posterior H5 | Completar backend, frontend definitivo, gráficos finales, ranking, reposiciones, seguimiento real, reentrenamiento y monitoreo | Integración comercial posterior |

La demostración H4 mostrará producto, tienda, histórico, mes siguiente, unidades previstas, modelo, MAE de referencia y origen del dataset. Puede ejecutarse mediante un script con una visualización inicial. El porcentaje funcional expresa una meta de entrega, no un resultado ya alcanzado. La reposición reactiva existente seguirá siendo distinta de una recomendación predictiva futura.

## 3. Tipo de dataset y variables

El nombre propuesto es **DATOS_SINTETICOS_DEMANDA_H4**. Será **tabular** porque cada fila tendrá columnas, **temporal** porque seguirá meses ordenados, **sintético inicial** porque las ventas se simularán y **supervisado** porque cada ejemplo incluirá un resultado conocido. Sintético describe el origen, tabular describe la estructura, temporal describe el orden y supervisado describe el aprendizaje.

La unidad de análisis será **PRODUCTO + TIENDA + MES**. El periodo simulado será octubre de 2024 a septiembre de 2026, 24 meses completos. Se utilizarán identificadores verificados del catálogo y de las tiendas existentes. Los productos de prueba o dudosos necesitarán revisión antes de fijar ese catálogo. No se inventarán tiendas ni se afirmará que los productos actuales ya se vendían en 2024.

La futura generación tendrá seed fija 42, tendencia moderada, estacionalidad anual, ruido controlado, diferencias entre tiendas, productos de alta, media o baja rotación y meses con cero ventas. Se conservarán una copia del catálogo utilizado, parámetros, versiones y una huella del archivo para poder repetirla. No se insertarán simulaciones en Sale, SaleItem ni Neon. Las métricas demostrarán el proceso bajo esos supuestos, sin certificar precisión comercial real.

El mes objetivo será m. Al cierre de m-1 se intentará predecir m. Los siguientes nombres son columnas propuestas del dataset, no campos nuevos de Prisma.

| Variable | Función | Significado |
|---|---|---|
| productId | Identificador y posible categoría de entrada | Producto del catálogo |
| locationId | Identificador y posible categoría de entrada | Location de tipo TIENDA |
| mes_objetivo | Identificador temporal | Mes m que se quiere pronosticar |
| ventas_mes_anterior | Entrada | Unidades de m-1 |
| ventas_hace_2_meses | Entrada | Unidades de m-2 |
| ventas_hace_3_meses | Entrada | Unidades de m-3 |
| mes_sin, mes_cos | Entradas | Representación cíclica del mes, que mantiene próximos diciembre y enero |
| target_ventas_mes | Target, resultado conocido al entrenar | Total de unidades vendidas brutas en m |

Los lags son cantidades observadas en meses anteriores del mismo producto y tienda. promedio_3_meses queda fuera de la versión inicial porque es la media exacta de los tres lags. No añade información nueva y crea dependencia lineal en LinearRegression. Podría probarse después como una variante mediante validación.

Los identificadores se conservarán como claves. Si se incorporan al modelo, se codificarán como categorías, sin asumir que un ID mayor significa mayor demanda. El catálogo de categorías del codificador se ajustará solo con training. No se usarán datos personales, información futura, stock actual como stock histórico ni precios actuales como precios históricos. En datos reales futuros, ausencia de registros no significará automáticamente cero ventas.

## 4. Predicción y tipo de aprendizaje

Realizaremos **regresión supervisada temporal**, también descrita como **pronóstico de demanda a un mes**. La pregunta será: ¿cuántas unidades de un producto podrían venderse el próximo mes en una determinada tienda? Buscamos una cantidad numérica, por ejemplo 17 unidades. No buscamos clasificar la demanda como alta, media o baja.

El aprendizaje será supervisado porque el modelo recibirá ejemplos con ventas anteriores y una cantidad posterior ya conocida. Aprenderá una relación entre esas entradas y el resultado para intentar predecir un mes todavía desconocido. No es aprendizaje no supervisado, que busca grupos sin una respuesta objetivo. Tampoco es aprendizaje por refuerzo, que aprende decisiones mediante recompensas al interactuar con un entorno.

El horizonte inicial será un mes, con un paso hacia adelante. No se promete pronosticar varios meses desde una sola fecha. El target medirá unidades vendidas brutas, con devoluciones separadas. Aunque hablemos de demanda, las ventas observadas no miden las unidades que se dejaron de vender por falta de stock.

## 5. Algoritmos propuestos

| Alternativa | Papel y ventajas | Límites |
|---|---|---|
| Baseline ingenuo | Predicción = ventas del mes anterior. Referencia mínima para comparar | No aprende cambios de calendario ni relaciones entre variables |
| LinearRegression | Modelo simple de Machine Learning, rápido, interpretable y fácil de explicar | Supone una relación lineal y puede producir valores negativos |
| RandomForestRegressor | Candidato principal. Combina árboles y puede representar relaciones no lineales entre historia, producto, tienda y calendario | Puede sobreajustarse, memorizar grupos pequeños y extrapolar mal tendencias nuevas |

Random Forest se propone por la estructura tabular, su capacidad para representar relaciones no lineales y una implementación manejable para H4. Estas propiedades se apoyan en la [documentación de scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html). No se elige solo por ser más complejo. El baseline es una referencia, no el modelo final previsto. Si los modelos no lo mejoran de forma útil, se cuestionará su utilidad y se conservará la opción simple cuando corresponda.

También se consideró una red neuronal MLP para regresión. Como experimento opcional podría recibir entradas procesadas, pasar por 64 neuronas con ReLU, otras 32 con ReLU y terminar en una neurona de salida lineal. ReLU permite representar relaciones no lineales. 64 y 32 no son obligatorios, las capas no tienen que ser pares y no existe una arquitectura universal. Requeriría normalización, más ajustes de configuración y control del sobreajuste, que ocurre cuando memoriza los ejemplos sin generalizar bien. Por eso no será el modelo principal. Podrá agregarse al experimento si el docente solicita compararla.

**Random Forest es candidato, no ganador.** La selección utilizará validation, con MAE como criterio principal, además de RMSE, R², estabilidad y complejidad. Test se mantendrá separado hasta cerrar la configuración final.

## 6. Preparación y evaluación

StandardScaler puede utilizarse con LinearRegression, aunque no es obligatorio para mínimos cuadrados ordinarios, llamados OLS. Random Forest no necesita normalización numérica. Para MLP se recomienda normalizar entradas numéricas como los lags. mes_sin y mes_cos ya tienen un rango acotado. Los identificadores categóricos requieren codificación, no escalado como cantidades.

El scaler se ajustará **solo con training**. Después transformará training, validation y test usando esos mismos valores. Nunca calculará media o desviación con todo el dataset. La misma regla se repetirá en cada validación temporal interna. [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html) conserva las estadísticas aprendidas para transformar datos posteriores.

Octubre a diciembre de 2024 servirán para construir los primeros tres lags. Los 21 meses objetivo restantes se dividirán así:

| Conjunto | Meses objetivo, inclusive | Cantidad | Proporción |
|---|---|---:|---:|
| TRAIN | enero 2025 a marzo 2026 | 15 | 71,43 % |
| VALIDATION | abril a junio 2026 | 3 | 14,29 % |
| TEST | julio a septiembre 2026 | 3 | 14,29 % |

Es una aproximación a 70/15/15 que respeta meses completos. Todos los productos y tiendas de un mes permanecerán juntos. No se utilizará split aleatorio. Como comprobación adicional se evaluará TimeSeriesSplit sobre meses únicos dentro de training. Las predicciones se evaluarán mes a mes, usando solo historia disponible al cierre anterior. Eso permite usar abril conocido para pronosticar mayo, sin convertir el experimento en un pronóstico simultáneo de tres meses.

La métrica principal será **MAE**. Si MAE = 2,4, la predicción se desvía en promedio unas 2,4 unidades por producto, tienda y mes. RMSE también se expresa en unidades, pero penaliza más los errores grandes. R² compara el ajuste con una referencia basada en la media, puede ser negativo y no representa un porcentaje de precisión. No se utilizará Accuracy, propia de clasificación. MAPE no será principal porque divide por las ventas observadas y resulta problemática con ceros o cantidades pequeñas. No existen métricas obtenidas todavía.

## 7. Orden de implementación posterior

Cuando el equipo autorice comenzar, se seguirá este orden:

1. Generar el dataset sintético identificado.
2. Validar estructura, cantidades, origen y reproducibilidad.
3. Construir lags, calendario y target.
4. Aplicar el split temporal y preparar transformaciones solo con training.
5. Evaluar el baseline ingenuo.
6. Entrenar LinearRegression.
7. Entrenar RandomForestRegressor.
8. Comparar resultados en validation.
9. Seleccionar la configuración final.
10. Evaluar una vez el test final reservado.
11. Guardar modelo y preprocesamiento.
12. Crear la primera predicción de un mes.
13. Crear la primera visualización.
14. Consolidar el registro del experimento.
15. Consolidar el registro de prompts.

Los registros de experimentos y prompts comenzarán desde la primera actividad. Los últimos pasos reúnen la evidencia, no reconstruyen registros perdidos. Esta revisión solo crea documentación. No genera datos, modelos, predicciones ni integraciones.

## 8. Resumen para exposición

| Pregunta | Respuesta breve |
|---|---|
| ¿Cuál es el plan? | Comprender datos, construir el dataset, prepararlo, comparar modelos y demostrar H4. La integración completa será H5 |
| ¿Qué dataset utilizarán? | DATOS_SINTETICOS_DEMANDA_H4, tabular, temporal, sintético inicial y supervisado. Producto + tienda + mes, 24 meses, seed 42 |
| ¿Qué van a predecir? | Unidades que un producto podría vender el próximo mes en una tienda. Regresión supervisada temporal a un mes |
| ¿Qué tipo de aprendizaje es? | Supervisado. Aprendemos con ventas anteriores y un resultado posterior conocido |
| ¿Qué algoritmo utilizarán? | Compararemos baseline ingenuo, LinearRegression y RandomForestRegressor. Random Forest es el candidato principal |
| ¿Por qué? | Se adapta a tablas, puede captar relaciones no lineales y tiene una complejidad manejable para H4 |
| ¿Por qué no red neuronal de entrada? | Necesita más ajustes, normalización y control del sobreajuste. Una MLP puede compararse después si se solicita |
| ¿Cómo evaluarán el resultado? | Con división temporal y MAE principal, acompañada de RMSE y R². Elegiremos con validation y evaluaremos test al final |

Random Forest es candidato, no ganador. La decisión final dependerá de las métricas, sin presentar resultados sintéticos como precisión comercial real.
