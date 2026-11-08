> ARCHIVO HISTÓRICO. Esta propuesta dejó de estar vigente el 3 de noviembre de 2026. La guía oficial es [H4_IMPLEMENTACION_MODELO_PREDICTIVO.md](../../H4_IMPLEMENTACION_MODELO_PREDICTIVO.md). Se conserva el contenido anterior como antecedente. Se adaptan los enlaces locales y la puntuación, sin cambiar las decisiones históricas.

# H4. Propuesta detallada del modelo predictivo de RepuestoPro

Fecha: 27 de octubre de 2026. Estado: propuesta. Este documento no contiene un modelo implementado ni resultados de entrenamiento.

Actualización del 3 de noviembre de 2026: existe un dataset sintético local de pruebas, versión 1.1, conservando la versión anterior. No se entrenó ningún modelo. Las referencias anteriores a una tarea que no crea dataset describen la revisión documental inicial. Las correcciones operativas posteriores se detallan en [correcciones para tienda real](../../../H3/cierre_saneamiento/CORRECCIONES_INTEGRALES_TIENDA_REAL.md). Los nuevos traslados quedan en tránsito hasta su recepción. Las nuevas devoluciones solo aumentan stock vendible después de inspección. Su importe reduce primero deuda pendiente y solo el excedente cobrado se registra como reintegro. Ninguno de estos eventos sustituye ventas brutas como target de H4. Los registros legacy requieren revisión y no se reinterpretan automáticamente.

La ampliación comercial del 3 de noviembre agrega Sale.status y voidedAt, evidencia manual de pagos y PurchaseInvoice. En una futura extracción real deben excluirse anulaciones con conocimiento de su fecha, sin reconstruir lags pasados usando información futura. Las referencias bancarias y los datos personales no son features. El dataset sintético 1.1 no se modificó ni se entrenó en esta ampliación. Véanse las [reglas comerciales](../../../H3/cierre_saneamiento/REGLAS_COMERCIALES_FACTURAS_ANULACIONES_Y_PAGOS.md).

## 1. Contexto y propósito

H4 requiere demostrar que el equipo comprende el problema, los datos, el aprendizaje, el entrenamiento, la validación y la evaluación final. Según la explicación del docente transmitida por el equipo, se espera aproximadamente un 70 % de avance funcional. Esto no mide líneas de código. Significa que las partes principales del experimento funcionan, se pueden reproducir y tienen evidencia.

La implementación comenzará cuando el equipo la autorice después de revisar el saneamiento. Esta tarea no crea dataset, entrenamiento, modelo guardado ni servicio de predicción.

La revisión documental actual contrasta el código en a9ff618, posterior al PR 50, con la auditoría y el plan de saneamiento. El cambio reciente de Erika, b20b96a, agrega docs/H4_PLAN_DE_TRABAJO.md. Frente a b1003a1 no cambia código, schema ni migraciones. Aporta distribución de tareas y un cronograma preliminar. No cambia el problema, el target ni el origen sintético inicial. Su checklist todavía menciona el promedio de tres meses y una reposición ilustrativa en H4. Para esta revisión se aclara que el promedio no será una entrada inicial y que las reposiciones quedan para H5. La demostración H4 puede funcionar con un script y una primera visualización, sin exigir la integración completa con Express y React.

Ejercicio 1.pdf describe el sistema comercial, incluido el inventario, las ventas, los reportes y la reposición reactiva. No establece los algoritmos ni el porcentaje funcional de H4. Estos últimos proceden de las indicaciones del equipo sobre la explicación del docente. Los nombres históricos Precio 1 y Precio 2 del PDF no sustituyen la semántica comercial actual POR MENOR y POR MAYOR.

## 2. Ejemplo del docente sobre seguimiento

Durante la explicación se utilizó un sistema de seguimiento físico. Este podría estudiar el progreso de una persona y estimar el tiempo necesario para aumentar masa muscular, reducir grasa o alcanzar un objetivo. El ejemplo no pertenece a RepuestoPro.

El principio se adapta al proyecto siguiendo las ventas mensuales de cada producto por tienda. A partir de ese comportamiento se intentará estimar las ventas del siguiente mes. El seguimiento del negocio y el registro de experimentos son actividades relacionadas, pero diferentes.

## 3. Problema predictivo

La pregunta es: ¿cuántas unidades de un producto podrían venderse el próximo mes en una determinada tienda? La unidad de análisis será producto + tienda + mes. El horizonte inicial será un mes y el resultado será una cantidad numérica, por lo que corresponde a regresión.

El objetivo inicial serán unidades vendidas brutas. Las devoluciones se conservarán como eventos separados. Las ventas observadas no representan toda la demanda perdida por falta de stock. Si luego se decide predecir ventas netas, habrá que definir cómo se asignan las devoluciones y cuándo se conocen.

La segunda auditoría establece dos modos comerciales. POR MENOR utiliza Product.price1 y POR MAYOR utiliza Product.wholesalePrice. Product.price2 queda como campo legacy, es decir, conservado por compatibilidad pero fuera de las nuevas decisiones comerciales. No se cambia el historial de SaleItem.unitPrice. Sale.type distingue el flujo NORMAL del módulo MAYOR, no demuestra por sí solo qué modo se eligió dentro de una venta normal. Sin una historia explícita del modo no se debe reconstruir esa variable comparando el precio vendido con precios actuales.

## 4. Datos actuales

La auditoría del 27 de octubre encontró 247 ventas registradas, 520 detalles, 45 productos distintos vendidos y 12 devoluciones. Hay registros de marzo a octubre de 2026, con octubre incompleto. De las 247 ventas, 226 están vinculadas a tiendas y 21 a almacenes.

Estos registros no son ventas reales certificadas. Los generadores demo escribían en las mismas tablas sin un indicador de procedencia. No se puede determinar individualmente su origen con la información disponible. Tampoco existe un historial anual suficiente ni una secuencia completa de stock histórico. La auditoría es el punto de partida y sus cantidades son una observación fechada, no una promesa de que la base no cambiará.

## 5. Datos reales y datos sintéticos

Un dataset real procede de operaciones comerciales verificadas. Uno sintético contiene observaciones fabricadas mediante reglas explícitas para experimentar. Inicialmente se propone el segundo para demostrar el proceso académico, sin presentarlo como historia comercial.

Se llamará `DATOS_SINTETICOS_DEMANDA_H4`. Cubrirá octubre de 2024 a septiembre de 2026, 24 meses completos. Utilizará productos del catálogo y tiendas existentes. Tendrá seed fija 42, orden estable por identificadores y versiones de herramientas registradas. No se insertará en Neon ni se mezclará con Sale o SaleItem.

La simulación incluirá alta, media y baja rotación, meses sin ventas, tendencia moderada, estacionalidad anual, diferencias entre tiendas y ruido controlado. Sus parámetros serán supuestos documentados, no patrones comerciales demostrados. Con 62 productos y tres tiendas serían 4.464 observaciones. Después de reservar tres meses para historia quedarían 3.906 filas supervisadas. Los recuentos deberán recalcularse con el catálogo congelado al generar.

La reproducibilidad requiere conservar el snapshot del catálogo, los parámetros, la seed, las versiones y una huella del archivo generado. Usar el catálogo actual en meses anteriores es una simulación deliberada, no prueba de que esos productos se vendieran entonces. Un buen resultado demuestra que el proceso funciona sobre los supuestos elegidos. No demuestra precisión comercial real.

## 6. Tipo de aprendizaje

En aprendizaje supervisado cada ejemplo incluye entradas y un resultado conocido. En RepuestoPro las ventas anteriores, el producto, la tienda y el calendario se relacionarán con las unidades del mes objetivo. Durante el entrenamiento ese resultado ya estará disponible.

El aprendizaje no supervisado busca estructuras sin una respuesta objetivo, como grupos de productos parecidos. Podría tener otra utilidad, pero no resuelve directamente esta pregunta. El aprendizaje por refuerzo aprende decisiones a través de recompensas al interactuar con un entorno. No es necesario para este primer pronóstico.

## 7. Variables y protección frente a información futura

El mes objetivo será m. El pronóstico se emitirá al cierre de m-1. Los nombres siguientes son columnas propuestas del dataset, no nuevos campos de Prisma.

| Variable | Significado | Uso |
|---|---|---|
| productId | Identificador real del producto | Clave y categoría opcional, no cantidad numérica |
| locationId | Identificador real de Location tipo TIENDA | Clave y categoría opcional |
| mes_objetivo | Mes cuyo total se quiere estimar | Identificador temporal |
| ventas_mes_anterior | Unidades observadas en m-1 | Entrada |
| ventas_hace_2_meses | Unidades observadas en m-2 | Entrada |
| ventas_hace_3_meses | Unidades observadas en m-3 | Entrada |
| promedio_3_meses | Media de los tres valores anteriores | Excluida de la versión inicial, experimento opcional posterior |
| mes_sin, mes_cos | Representación cíclica del mes con período 12 | Entradas de calendario |
| target_ventas_mes | Unidades del mes m | Resultado objetivo |

Las cantidades reales futuras se obtendrían de SaleItem.quantity, con Sale.saleDate y Sale.locationId, restringiendo Location.type a TIENDA. La agrupación mensual respetará America/La_Paz, como los reportes actuales. La ubicación será la de la venta, no la ubicación actual del vendedor. Las devoluciones se agregarían por separado para no multiplicarlas al unir tablas con líneas repetidas. Las claves no se interpretarán como si un producto con ID 20 tuviera el doble de demanda que otro con ID 10.

promedio_3_meses equivale a sumar los tres lags y dividir entre tres. No aporta información nueva y crea dependencia lineal entre entradas de LinearRegression. Se excluye del conjunto inicial para simplificar la comparación. Podría evaluarse después como variante, utilizando únicamente validación. Los lags son cantidades de meses anteriores del mismo producto y tienda.

No se usarán como historia el stock actual, minStock actual, price1 actual, price2 actual, wholesalePrice actual o cost actual. Tampoco el total, las cantidades del mes objetivo ni datos personales. Un precio histórico anterior, categoría verificada, devoluciones conocidas o proporción mayorista anterior son opciones futuras, no entradas iniciales obligatorias.

La fuga de información, o data leakage, ocurre cuando se usa algo que aún no se conocía al pronosticar. Por ejemplo, repetir el stock consultado hoy en todas las filas de 2025 incorpora efectos de ventas posteriores. También ocurre al calcular el promedio de todo el dataset antes de separarlo. Los meses sin registros no se convertirán automáticamente en cero si la captura o disponibilidad no están certificadas.

## 8. Entrenamiento, validación y test

Con 80 % para entrenamiento y 20 % para test se dispone de más datos para aprender y una reserva para evaluar. Con 70 % y 30 % la reserva es mayor, pero se reduce el aprendizaje. Ninguna proporción vuelve correcto un experimento por sí sola. Si se eligen parámetros mirando repetidamente el test, deja de ser una prueba independiente. Una alternativa válida sería hacer selección mediante validación temporal interna del training, manteniendo el test intacto.

Para este proyecto se propone separar tres funciones. El entrenamiento ajusta el modelo. La validación ayuda a elegir variables, modelo y parámetros. El test estima el resultado final después de cerrar esas decisiones. La ventaja es una evaluación más independiente. El costo es disponer de menos datos para entrenamiento.

Octubre, noviembre y diciembre de 2024 construirán los tres primeros lags. Las 21 fechas objetivo restantes se repartirán así:

| Conjunto | Rango inclusivo del mes objetivo | Meses | Porcentaje |
|---|---|---:|---:|
| Training | enero 2025 a marzo 2026 | 15 | 71,43 % |
| Validation | abril a junio 2026 | 3 | 14,29 % |
| Test | julio a septiembre 2026 | 3 | 14,29 % |

Es una aproximación a 70/15/15 que conserva meses completos. Todos los productos y tiendas de un mes pertenecen al mismo conjunto. No se utilizará un reparto aleatorio, porque permitiría aprender con el futuro y evaluar sobre el pasado.

La evaluación inicial será mensual y de un paso. Para pronosticar mayo, las ventas de abril ya conocidas pueden ser entradas aunque abril pertenezca a validación. Esto no equivale a pronosticar tres meses a la vez desde marzo. No se cambiarán parámetros usando el test.

Como comprobación adicional se usará TimeSeriesSplit sobre meses únicos dentro del training. Con tres bloques de prueba interna de tres meses, los entrenamientos se expandirían desde enero-junio de 2025 hasta enero-diciembre de 2025. No se dividirán directamente las filas del panel si eso separa un mes entre conjuntos. Se revisará si el horizonte y el retraso de etiquetas requieren dejar una separación temporal adicional.

## 9. Normalización

Escalar significa expresar variables en magnitudes comparables. Un precio de 800, cuatro ventas y un mes número ocho tienen escalas diferentes. Algunos algoritmos son sensibles a esa diferencia. El ejemplo no significa que el precio actual deba incorporarse al dataset histórico.

StandardScaler resta la media del training y divide por su desviación. Se hará `fit` solo con training. Después se aplicará `transform` a training, validation y test. En cada división temporal interna se ajustará de nuevo usando únicamente su entrenamiento. Nunca se calcularán media o desviación con validación o test.

LinearRegression ordinaria no requiere StandardScaler para funcionar, aunque puede mejorar estabilidad numérica y comparación de coeficientes. RandomForestRegressor no necesita escalado numérico para formar divisiones de árboles. Una red neuronal sí suele necesitarlo para que el ajuste sea estable. El escalado, cuando corresponda, se aplicará a entradas numéricas como los lags. mes_sin y mes_cos ya tienen un rango acotado. Las categorías requieren una codificación apropiada, ajustada solo con training, no convertir IDs a magnitudes. El promedio de tres lags queda fuera de la versión inicial.

## 10. Baseline y LinearRegression

Antes de Machine Learning se evaluará la regla `predicción = ventas del mes anterior`. Esta referencia ingenua permite comprobar si un modelo complejo aporta una mejora. Todos se compararán con los mismos meses y métricas.

LinearRegression estima una combinación lineal de las entradas. Es rápida, reproducible y permite examinar coeficientes. Será la primera referencia de Machine Learning. Tiene limitaciones ante relaciones complejas y puede producir valores negativos. Se conservarán métricas de su salida original. Para una recomendación operativa se podrá usar `max(0, predicción)`, registrando también el efecto de esa regla. No se llamará a esto un porcentaje de precisión.

## 11. RandomForestRegressor

Un bosque combina varios árboles de decisión. Cada árbol aprende divisiones de las entradas y el regresor combina sus predicciones. Puede representar interacciones y relaciones no lineales en datos tabulares sin escalado numérico. RandomForestRegressor será el candidato principal por su adecuación a esta estructura y su complejidad manejable para H4, no un ganador anticipado.

Puede sobreajustarse, memorizar grupos escasos y tener dificultad para extrapolar tendencias fuera del rango aprendido. Se evaluará una búsqueda pequeña y documentada sobre `n_estimators`, `max_depth`, `min_samples_leaf` y `max_features`. La validación servirá para elegir, con apoyo de la comprobación temporal interna. El test permanecerá separado. No se declara ganador antes de medir.

## 12. Red neuronal para regresión

Una MLP conecta capas de neuronas que transforman las entradas mediante pesos aprendidos. Si se prueba, será una red de regresión, no de clasificación. Una propuesta inicial es entrada procesada, capa oculta de 64 neuronas con ReLU, otra de 32 con ReLU y salida de una neurona con activación lineal.

ReLU permite representar relaciones no lineales en las capas ocultas. La salida lineal permite estimar una cantidad sin convertirla en probabilidad de clase. Es la elección inicial para esta regresión, no una afirmación de que toda regresión deba usar siempre esa salida. Una salida lineal también puede producir negativos y necesitaría la política operativa ya descrita.

64 y 32 son opciones de experimento. No existe obligación de usar números pares, potencias de dos ni una cantidad universal de capas. La arquitectura es un hiperparámetro y se compara mediante validación. Con pocos datos puede sobreajustarse y exige más decisiones que una regresión lineal o un bosque. Por eso no será la primera opción.

Una implementación posterior podría usar MLPRegressor. Su partición interna aleatoria para parada temprana no sustituirá la validación temporal del proyecto. Se documentarán `hidden_layer_sizes`, activación, solver, learning rate, batch size, seed, número máximo de iteraciones y criterio de parada. Si se controla por épocas, el procedimiento mantendrá los mismos cortes temporales sin incorporar test a la selección.

## 13. Comparación y selección

Una red neuronal también pertenece a Machine Learning. La comparación correcta es entre modelos lineales, árboles y una red, no entre categorías mutuamente excluyentes.

| Aspecto | LinearRegression | RandomForestRegressor | MLP |
|---|---|---|---|
| Dificultad y explicación | Baja, coeficientes accesibles | Media, varios árboles | Mayor, capas y optimización |
| Datos necesarios | Menor exigencia relativa | Mayor diversidad para interacciones | Mayor volumen y diversidad |
| Escalado | Opcional en OLS | No necesario | Recomendable |
| Entrenamiento | Generalmente rápido | Más costo según árboles | Sensible a iteraciones y arquitectura |
| Interpretación | Alta con entradas claras | Media | Menor |
| Sobreajuste | Depende de variables e historia | Riesgo con profundidad y hojas pequeñas | Alto con pocos datos |
| Adecuación inicial | Baseline de Machine Learning | Candidato principal | Alternativa si aporta valor |

MAE será el criterio principal, acompañado de RMSE, R², estabilidad entre meses, comportamiento con ceros y complejidad. Si el modelo más complejo no mejora de forma útil a la referencia, se conservará el simple. El ganador no está decidido. Un resultado sintético favorable no certifica utilidad comercial.

## 14. Métricas

MAE es el promedio del error absoluto. MAE = 2,4 significa que el modelo se desvía en promedio unas 2,4 unidades por producto, tienda y mes. Será la métrica principal.

RMSE eleva errores al cuadrado, los promedia y toma su raíz. Sigue expresado en unidades y penaliza más los errores grandes. R² compara el error con una referencia basada en la media del conjunto evaluado. R² = 0,80 no significa automáticamente 80 % de precisión y puede ser negativo. En series constantes o evaluaciones diminutas puede no ser informativo.

MAPE divide por la cantidad observada y presenta problemas cuando es cero o muy pequeña. No será la métrica principal de productos de baja rotación. Accuracy corresponde a clasificación y no se utilizará para esta regresión. Las métricas se mostrarán globalmente y por tienda o grupo de rotación, con el número de observaciones evaluadas.

## 15. Registro de experimentos, prompts y configuraciones

Cuando comience H4 se creará `ml/demand/reports/experiments.csv`. Tendrá `experiment_id`, `timestamp`, `model`, `features`, `train_range`, `validation_range`, `test_range`, `parameters`, `seed`, `mae_val`, `rmse_val`, `r2_val`, `mae_test`, `rmse_test`, `r2_test`, `training_seconds` y `notes`. Las métricas de test permanecerán vacías en experimentos de selección. Se completarán solo al evaluar la configuración final congelada.

Cada ejecución conservará versión y huella del dataset, seed, parámetros, entradas y observaciones. Esto permite comparar cambios y repetir resultados sin confundir modelos o datos diferentes. También se anotarán versiones de Python, pandas, NumPy y scikit-learn, fechas, target, split, scaler, encoder, arquitectura si existe, activaciones, learning rate, épocas o iteraciones, duración y nombre del artefacto.

El registro textual de prompts conservará auditoría, generación de datos, entrenamiento, correcciones, integración, pruebas y documentación. Se propone `docs/H4/PROMPTS_MODELO_PREDICTIVO_H4.md` para el momento de implementación. Un prompt no recuperable se marcará `NO RECUPERADO`. No se reconstruirá para presentarlo como original. La solicitud actual y la auditoría ya disponibles deberán archivarse con su procedencia cuando se abra ese registro.

## 16. Qué representa aproximadamente el 70 % de H4

El avance funcional requiere problema definido, auditoría disponible, justificación supervisada, dataset preparado y análisis básico. Deben funcionar las entradas y target, el split temporal, el baseline ingenuo, LinearRegression y RandomForestRegressor. Debe existir comparación con métricas y normalización documentada, registro de experimentos y configuraciones, modelo guardado, una predicción mediante script o endpoint simple y una primera visualización. Los prompts deben quedar registrados.

No basta escribir esos apartados ni contar archivos. La evidencia debe permitir reproducir el experimento. Tampoco significa que el sistema comercial esté terminado al 100 %.

## 17. Demo H4 e integración H5

La demo H4 permitiría elegir producto y tienda, ver meses recientes, mes objetivo, modelo, unidades previstas, MAE de referencia y origen de datos. Un gráfico diferenciaría historia simulada y pronóstico. La primera salida posterior a una historia que termina en septiembre de 2026 correspondería a octubre de 2026. Sería una demostración basada en simulaciones, no una predicción comercial certificada. Se puede presentar mediante script y visualización inicial. La integración completa con backend y frontend queda para H5.

La reposición predictiva se estudiará en H5. Su regla conceptual será `max(0, ceil(demanda prevista + stock de seguridad - stock actual))`. Por ejemplo, 18 unidades previstas, stock actual 9 y seguridad 5 darían 14 unidades de reposición. Son números ilustrativos, no resultados obtenidos. Stock actual corresponde a Inventory del producto y tienda. minStock no equivale automáticamente a seguridad estadística. Una recomendación no moverá inventario ni generará compras por sí sola. Este cálculo no será un requisito de la demostración H4.

H5 podrá completar integración definitiva con Express y React, filtros, gráficos, ranking, permisos, pruebas completas, seguimiento de error real, reentrenamiento y versionado. El módulo propuesto es `backend/src/modules/predictions/demand/` con inferencia interna Python. Es una ruta futura, no un módulo existente. Frontend se coordinará con Erika. La reposición reactiva existente seguirá siendo distinta del pronóstico.

## 18. Riesgos y discusión para la clase

Los riesgos principales son procedencia incierta, poca historia anual, demanda perdida no observada, fuga de información y aprendizaje de la fórmula sintética. El rendimiento deberá volver a evaluarse con ventas reales suficientes. Los datos actuales no se usarán como historia comercial certificada. El modelo no automatizará compras en H4.

Para la clase se explicará que se quiere estimar unidades por producto y tienda. Es regresión supervisada porque hay un resultado numérico conocido al entrenar. Se usarán inicialmente simulaciones por la falta de historia certificada. Validation separa selección de evaluación final, el orden temporal evita usar el futuro y el escalado se ajusta solo en training. Se compararán varios modelos por sus resultados, no por preferencia previa hacia redes. El 70 % implica un experimento funcional y reproducible.

## 19. Fuentes

Las decisiones del proyecto se basan en Ejercicio 1.pdf, la solicitud actual del equipo, la [auditoría de datos](../AUDITORIA_MODELO_PREDICTIVO_H4.md), el [plan de saneamiento](../../../H3/cierre_saneamiento/PLAN_SANEAMIENTO_REPUESTOPRO_PRE_H4.md) y el código real. El [plan de trabajo de Erika](H4_PLAN_DE_TRABAJO.md) aporta coordinación preliminar. La [síntesis para exposición](H4_PLAN_FASES_DATASET_PREDICCION_ALGORITMO.md) reúne las decisiones de esta revisión. Las referencias técnicas son:

- [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).
- [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html).
- [LinearRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html).
- [RandomForestRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html).
- [MLPRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPRegressor.html).
- [Métricas de regresión](https://scikit-learn.org/stable/modules/model_evaluation.html).
- Goodfellow, I., Bengio, Y. y Courville, A. (2016). [Deep Learning](https://www.deeplearningbook.org/). MIT Press.

La decisión actual es terminar y revisar el saneamiento. No comenzar H4 hasta que el equipo autorice el siguiente paso.
