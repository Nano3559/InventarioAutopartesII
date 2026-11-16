# H4. Implementación del modelo predictivo de RepuestoPro

## Estado vigente. Calendario unificado 4.0.0

Actualizado el 16 de noviembre de 2026. Esta sección reemplaza las indicaciones activas de 2.2.0 y 3.0.0 que aparecen debajo. Esos apartados se conservan como registro histórico. La interfaz, los datos mostrados y el pronóstico de Escenarios usan ahora el mismo build 4.0.0.

El dataset sintético abarca noviembre de 2024 a octubre de 2026. Sus tres meses iniciales forman los primeros lags. TRAIN comprende febrero de 2025 a abril de 2026, VALIDATION mayo a julio de 2026, TEST agosto a octubre de 2026. Son 15, 3 y 3 meses completos. Las variantes de una misma familia permanecen juntas y comparten un peso total de uno.

Existe una realización DEMO independiente, excluida del ajuste, la selección y las métricas. Sus observaciones BASE de enero a octubre de 2026 alimentan tanto Explorar ventas como la gráfica de Escenarios. Los tres lags de noviembre son agosto, septiembre y octubre de esa misma realización. Noviembre no tiene ventas generadas ni un target conocido. Su punto en la gráfica procede exclusivamente de la inferencia.

El build contiene 14.112 filas supervisadas. De ellas, 5.040 corresponden a TRAIN, 1.008 a VALIDATION, 1.008 a TEST y 7.056 a DEMO. Hay 56 productos del catálogo congelado, tres tiendas y 168 combinaciones. No se agregaron almacenes como tiendas de venta. Las ventas siguen siendo simuladas, no historia comercial certificada.

Se compararon baseline, LinearRegression y dos bosques. El bosque con criterio de error absoluto obtuvo MAE 11,5168 en VALIDATION frente a 19,4067 del baseline. Se fijó antes de abrir TEST. Su configuración utiliza 100 árboles, profundidad máxima 14, mínimo de cuatro muestras por hoja, fracción de variables 0,9 y seed 42. El adaptador conserva las 19 entradas aprobadas, los controles de disponibilidad temporal y el escalado ajustado solo con TRAIN para el modelo lineal. El bosque no necesita escalado numérico.

TEST se evaluó una sola vez para esta nueva versión. El bosque obtuvo MAE 10,2010 unidades, RMSE 18,4046 y R² 0,6201. El baseline obtuvo MAE 17,3581. Esa mejora técnica con datos sintéticos no certifica tolerancia comercial. No se volvió a evaluar el TEST de las versiones anteriores. Tres comprobaciones temporales adicionales se limitaron a TRAIN, sin cambiar la selección fijada.

La consulta de noviembre conserva el stock al cierre de octubre. Precios, costos y cotización se arrastran desde la información conocida de octubre. Una recepción de 50 unidades prevista para el 10 de noviembre es un supuesto sintético explícito, no una recepción real. Los estados de stock del generador son escenarios mensuales independientes, no un libro continuo de inventario certificado. Los campos de logística sirven también para la reposición explicativa, sin crear compras o movimientos.

La revisión de inferencia cubrió las 168 combinaciones. En 136 se obtiene una cifra y en 32 el modelo se abstiene porque el stock supera las 150 unidades observadas como máximo en TRAIN. No se recorta ese stock, no se sustituye una abstención por cero ni se amplían los límites después de TEST. La interfaz avisa del motivo. El historial puede explorarse para todas las combinaciones.

La pantalla mantiene producto y tienda al cambiar de vista. Explorar ventas muestra enero a octubre de 2026. Predecir y comparar ofrece noviembre de 2026, con los controles de cantidades previas, precios, cotización, costo, stock, reservas y entregas. Los cambios son hipótesis, no ediciones de la base operativa. La serie decorativa anterior ya no se usa en estas vistas. La consulta histórica 2.2.0 queda en Versiones anteriores. Los archivos 3.0.0 se conservan sin cambios.

Dataset: `ml/demand/data/repuestopro_v2/4.0.0/calendar-20261116-01/`. Modelo: `ml/demand/models/v2/calendar-model-20261116-01/model.joblib`. Evidencias: `ml/demand/reports/v2/4.0.0/calendar-model-20261116-01/`. El release conserva hashes del modelo y los snapshots. La evaluación final está separada en `test-evaluation.json`, protegida por un registro de intento único. La carga de métricas no vuelve a puntuar TEST.

Se comprobaron 294 pruebas frontend, 184 backend y 29 Python e integridad. En total, 507 pruebas aprobadas. El cierre está registrado en `integration-review.json`. Pasaron la compilación backend y el build frontend. La revisión visual local utilizó una sesión ADMIN ficticia con el router, la API y el artefacto reales. Se observó noviembre de 2026 y una comparación de 87,17 unidades para Tensador de Correa en Tienda 2, sin cambios. Esta evidencia no equivale a una nueva validación de la sesión productiva. Los permisos ADMIN permanecen protegidos en la API.

La integridad de 518 archivos anteriores quedó verificada por SHA-256. No hubo cambios en Neon, Prisma, RAW o versiones previas. No se crearon documentos Markdown nuevos. Automotive continúa excluido por licencia pendiente. El simulador Streamlit sigue separado.

> Estado vigente: la integración local de escenarios 3.0.0 está completada. Consultar la sección final de este documento y el anexo 51 del Plan V2. Las entregas anteriores se conservan como registro del proceso.
**Estado vigente: referencia 2.2.0 validada e integrada. H4 interactivo sigue incompleto.** Los anexos 46 y 47 del Plan V2 corrigen el alcance anterior y definen el contrato y las tareas vigentes. Replay histórico no equivale a edición de precios, cotización, cantidades y planes logísticos.

El administrador consulta /panel/prediccion. La API y la pantalla identifican V2.2.0, el artefacto aceptado y la política NONNEGATIVE_CONTINUOUS_1. El simulador Streamlit permanece separado. El modelo predice ventas observadas de un producto en una tienda a un mes. Sus cinco entradas son los tres lags y dos variables del calendario. El dataset conserva otras variables evaluadas, pero no utilizadas por la configuración elegida.

TEST se evaluó una sola vez después de fijar la selección, sin reentrenar. MAE 9,2046 frente a 12,8690 del baseline, RMSE 16,9085 y R² 0,6466. La mejora del MAE es 28,47 %. Persiste subestimación agregada aproximada del 20,05 %. No se garantiza precisión comercial ni se borran los errores desfavorables de VALIDATION.

Pasaron 84 pruebas Python, 173 backend y 248 frontend, además de tipos backend, build frontend y el control de contrato real Node/Python/frontend. Se revisó la pantalla a 1280 y 390 px con sesión ficticia y la inferencia real. ADMIN tiene acceso. TIENDA e INVENTARIO no pueden consultar esta sección. Se comprobaron sesiones inválidas, revocadas y cambios de rol mediante lecturas de sesión simuladas, sin Neon.

La consulta es ACADEMIC_REPLAY de abril a junio de 2026 con datos sintéticos. No es un pronóstico en vivo del mes actual. Lee métricas finales guardadas y no vuelve a evaluar TEST. No crea compras, calcula reposición o cambia stock. La operación productiva con Neon y el ensayo conjunto no se certifican en esta revisión.

El bloque siguiente conserva la introducción histórica previa al cierre 2.2.0. Sus versiones, métricas y pendientes corresponden a ese momento.

Documento oficial vigente. Integración y revisión de cierre de Ross: 10 de noviembre de 2026, America/La_Paz. La ampliación administrativa vigente está en la sección 22. Las secciones 20 y 21 conservan la revisión previa y su guion. Los apartados anteriores conservan el diseño y las revisiones fechadas.

La ampliación se organiza en el [Plan de trabajo V2](PLAN_DE_TRABAJO_V2.md). V2-11 está cerrado para la pantalla administrativa de reproducción académica, según el anexo 29. Se seleccionan producto, tienda y un mes aprobado de abril a junio de 2026. El horizonte permanece en un mes. El gráfico distingue historia simulada, predicción y baseline, con una tabla accesible. Se muestran métricas guardadas, origen sintético, límites, versión, política y trazabilidad del snapshot.

La pantalla valida las respuestas antes de mostrarlas. Cambiar la selección o actualizar referencias limpia resultados anteriores. Cancela solicitudes del cliente e ignora respuestas o errores tardíos. Los errores de permisos, snapshot, ausencia de historia e integridad se explican sin inventar predicciones. Se mantiene la política fijada y no se presentan métricas TEST como error conocido de esa consulta.

Pasaron 12 pruebas de interfaz, dos controles con catálogo y respuesta reales del adaptador V2, tipos y build frontend. El componente y su gráfico se revisaron con fixtures en escritorio y a 390 píxeles, sin desbordamiento horizontal. No se utilizó una sesión real de Neon o el TEST consumido. La validación global de V2-15 y la aceptación conjunta siguen pendientes. No se afirma revisión de Expo o deploy.

El dataset 2.1.0 ya existe y está completo para el alcance académico inicial aprobado, con ventas sintéticas y referencias de Monash y UCI. No es una unión de los cinco datasets externos. El anexo 30 establece que una ampliación puede abrirse después de este cierre, antes de otro entrenamiento, sin esperar obligatoriamente a H5. Automotive, M5 y Favorita requieren resolver las condiciones pendientes y comprobar compatibilidad. No se garantiza que deban incorporarse todas las fuentes. La ampliación tendrá otra versión, otro protocolo de evaluación y no reutilizará TEST de 2.1.0 como prueba independiente.

El bosque aceptado sigue fijado. Su TEST guardado conserva MAE 7,6327, RMSE 15,4253 y R² 0,6429, con subestimación de la suma observada del 15,46 %. No se reentrenó, repitió TEST, modificó un dataset o conectó Neon en esta tarea. No existe aprobación de compra automática o precisión comercial.

Para estudiar la exposición, utilizar la [sección 21. Presentación al docente](#21-presentación-de-h4-al-docente). El reporte técnico y sus resultados están en la [sección 20](#20-reporte-de-integración-y-cierre-técnico-de-ross). El guion prepara una demostración, no registra una defensa ya realizada.

Esta guía reúne las decisiones para estudiar, presentar e implementar H4. La indicación del docente resumida por el equipo en la solicitud de consolidación define la entrega. El código y los archivos locales respaldan el estado técnico. Las auditorías conservan observaciones fechadas. Si una propuesta anterior difiere de esta guía, se utiliza esta versión.

**Estado comprobado al 10 de noviembre:** los cambios de Erika ya están integrados. Existen motor, baseline, LinearRegression, RandomForest V1, resultados congelados, inferencia, reentrenamiento local, comparación, rollback y trazabilidad. Ross conectó las tres referencias a la aplicación normal y completó el análisis por escenario. La revisión ejecutó 473 pruebas sin fallos, cargó los artefactos reales y verificó escritorio, pantalla estrecha y descarga de sesión. Los 29 archivos protegidos permanecen intactos. No se reentrenó V1 ni se repitió su TEST oficial. La promoción de candidatos reales sigue bloqueada por evidencia insuficiente y no se declara aceptación académica del equipo ni validación comercial.


## 1. Base del modelo predictivo

Queremos estimar cuántas unidades de un producto podrían venderse durante el siguiente mes en una determinada tienda. Esto podría ayudar a estudiar rotación, anticipar necesidades y apoyar decisiones posteriores de abastecimiento. La implementación comercial y las recomendaciones de reposición corresponden a H5.

La unidad de análisis es **PRODUCTO + TIENDA + MES**. El horizonte inicial es un mes, un paso hacia adelante. El tipo de predicción es **regresión supervisada temporal**, también presentado como pronóstico de demanda a un mes. Buscamos una cantidad numérica, por ejemplo 17 unidades, no una clase de demanda alta, media o baja.

El target se llama **target_ventas_mes** y representa unidades vendidas brutas del mes objetivo. Aunque el nombre del proyecto hable de demanda, **ventas observadas no son iguales a demanda total**. Si faltó stock, cero ventas puede ocultar clientes que quisieron comprar. El modelo inicial estima ventas observadas bajo los supuestos del experimento. No estima demanda perdida ni mide causalmente el efecto de precios o promociones.

Es aprendizaje supervisado porque, al entrenar, cada ejemplo contiene ventas anteriores y un resultado posterior conocido. El aprendizaje no supervisado buscaría grupos o estructuras sin ese target. El aprendizaje por refuerzo aprendería decisiones mediante recompensas. Ninguno de esos dos enfoques es necesario para esta primera pregunta.

## 2. Datos reales y compatibilidad con el proyecto actual

La [auditoría del 27 de octubre de 2026](historico/AUDITORIA_MODELO_PREDICTIVO_H4.md) registró 247 Sale, 520 SaleItem, 45 productos vendidos y 12 Return por 14 unidades. Las ventas abarcan del 8 de marzo al 13 de octubre de 2026, ocho meses calendario con registros. Son 226 ventas asociadas a tiendas y 21 a almacenes. Marzo comienza el día 8 y octubre tiene cobertura parcial. Estas cifras son una fotografía histórica, no conteos actuales consultados para esta consolidación.

La procedencia comercial o demo no puede certificarse individualmente con esos registros. Los datos demo históricos se escribieron en las mismas tablas sin una marca suficiente de origen. Hay poca historia por combinación y no existe una serie anual certificada. No sabemos cuántas de las 247 ventas son operaciones comerciales reales verificadas. Eso no significa que sean cero. El experimento inicial utilizará simulaciones separadas de las tablas comerciales.

La revisión local del schema y los módulos actuales confirma lo siguiente. Los nombres de la tabla son reales de Prisma. Las columnas del dataset que se definen después son nombres derivados, no nuevos campos de la base.

| Fuente actual | Utilidad y límite para H4 |
|---|---|
| Sale.id, saleDate, createdAt, locationId y status | Identidad, fecha comercial, fecha de registro y ubicación de la venta. status distingue CONFIRMED y VOIDED en el código local |
| Sale.voidedAt, voidReason y voidedById | Evidencia de anulación. La fecha permite revisar cuándo se conoció ese evento, sin convertir motivo o responsable en features |
| SaleItem.saleId, productId y quantity | Fuente de cantidades brutas. unitPrice y subtotal conservan valores de la transacción, pero los del mes objetivo son futuros al pronosticar |
| Product.id, itemCode, name y categoryId | Referencia del catálogo. La categoría es opcional. brand, model, year, manufacturer, detail y detalles no son entradas iniciales ni demuestran atributos históricos |
| Location.id, name y type | Las sucursales elegibles son type TIENDA. No se utiliza la ubicación actual del usuario para reasignar ventas antiguas |
| Inventory.productId, locationId, stock y minStock | Estado actual del par. No representan stock histórico ni demanda perdida. minStock no equivale automáticamente a stock de seguridad estadístico |
| Return.saleId, productId, quantity, amount y date | Devoluciones separadas del target bruto. disposition, restockedQuantity y discardedQuantity registran inspección. debtReduction y refundAmount separan reducción de deuda de reintegro |
| Product.price1 y wholesalePrice | POR MENOR y POR MAYOR, respectivamente. Product.price2 es legacy. Ninguno de los precios actuales se reutiliza como historia mensual |
| Reportes y fechas | Los agregados actuales excluyen VOIDED y aplican America/La_Paz. Esto no certifica por sí solo una extracción histórica con disponibilidad temporal |

Sale.type distingue los flujos NORMAL y MAYOR. Una venta normal también puede usar POR MAYOR. SaleItem no persiste un campo propio del modo comercial elegido. No se reconstruirá ese modo comparando unitPrice con precios actuales.

Los traslados nuevos permanecen en tránsito hasta recepción. Las devoluciones nuevas solo ingresan a stock vendible después de inspección. Ninguno de esos ingresos es una venta de cliente. ProductRequest representa reposición interna, no clientes que no pudieron comprar. El código local también incorpora verificación bancaria manual e identidad de facturas. Esos controles mejoran el proceso, pero no certifican automáticamente los datos antiguos.

Una extracción real futura agruparía cantidades por producto, Sale.locationId y mes local. Usaría ventas comerciales elegibles y revisaría anulaciones con su fecha de conocimiento. Las líneas repetidas no se borrarían sin analizar su origen. Se sumarían cantidades legítimas y se agregarían devoluciones, pagos o proveedores por separado antes de unirlos, evitando multiplicar unidades por relaciones de uno a muchos. El intervalo mensual será desde el primer día a las 00:00 inclusive hasta el primer día siguiente exclusivo, convertido a UTC según la convención del sistema.

El schema revisado es local. No se consultó Neon para actualizar estos datos ni se afirma que producción tenga las mismas migraciones. Los antecedentes y controles comerciales se conservan en [saneamiento](../H3/cierre_saneamiento/PLAN_SANEAMIENTO_REPUESTOPRO_PRE_H4.md) y [reglas comerciales](../H3/cierre_saneamiento/REGLAS_COMERCIALES_FACTURAS_ANULACIONES_Y_PAGOS.md).

## 3. Dataset elegido y estado existente

El dataset se llama **DATOS_SINTETICOS_DEMANDA_H4**. Las cuatro descripciones siguientes se complementan, no son alternativas.

| Concepto | Qué describe |
|---|---|
| Tabular | La estructura. Cada fila tiene columnas definidas |
| Temporal | El orden. Las observaciones pertenecen a meses consecutivos |
| Sintético inicial | El origen. Las cantidades se simulan, aunque los identificadores proceden del catálogo del proyecto |
| Supervisado | El aprendizaje. Cada ejemplo contiene entradas y un resultado conocido para entrenar |

Se utilizan 24 meses, de octubre de 2024 a septiembre de 2026, con seed 42. La seed fija la secuencia aleatoria para repetir la simulación con los mismos insumos y versiones. Se incluyen rotación alta, media y baja, meses con cero, efecto tienda, estacionalidad anual, tendencia moderada y ruido controlado. Son supuestos de prueba. Los IDs no determinan la magnitud de las ventas.

La referencia del catálogo corresponde al 27 de octubre de 2026 en La Paz. El manifiesto conserva el instante 2026-10-28T01:08:41.263Z, que es el 27 por la noche en UTC-4. No hubo una lectura nueva para esta guía. La selección usa productos 1 a 56 y tiendas 5, 6 y 7, llamadas Tienda 1, Tienda 2 y Tienda 3. Se reservan 57 a 62. Sus dudas de categoría, aplicación comercial o condición de prueba permanecen en la [evidencia de Fase 1](historico/H4_FASE1_ESTRUCTURA_DATASET_Y_RIESGOS.md). No se asignaron categorías ni se repararon registros por inferencia.

La versión vigente está en [ml/demand/data/escenarios_v1_1](../../ml/demand/data/escenarios_v1_1). Conserva 56 productos × 3 tiendas = 168 series. Hay **4.032 filas mensuales y 3.528 filas supervisadas**. Los conteos antiguos calculados con 62 productos, 4.464 y 3.906, eran ejemplos condicionales. No describen la selección guardada.

| Archivo existente | Función |
|---|---|
| base_mensual.csv | Mes, productId, locationId y ventas_mes durante 24 meses |
| dataset_supervisado.csv | Nueve columnas finales para los 21 meses objetivo |
| escenarios_metadatos.csv | Rotación, escenario, clase y corte temporal. Solo sirve para diagnóstico |
| casos_invalidos.json | Quince entradas deliberadamente incorrectas para comprobar rechazo |
| casos_grises.json | Diez fichas de situaciones ambiguas, separadas del entrenamiento |
| validacion.json y manifest.json | Estadísticas, origen, parámetros, versiones, hashes y ausencia de entrenamiento |
| catalog_reference.json | Referencia del catálogo, productos incluidos o reservados y procedencia |

La base contiene 2.897 observaciones normales y 1.135 adversas válidas. El panel supervisado contiene 2.525 normales y 1.003 adversas válidas. No deben intercambiarse ambos conteos. El target supervisado tiene mínimo 0, máximo 69, media aproximada 10,11, mediana 7 y 422 ceros. Son estadísticas del archivo, no métricas de un modelo. El máximo observado no es un límite comercial ni una restricción universal de 69 o 150 unidades.

La versión 1.0 permanece en escenarios_v1, junto con su generador conservado en versions/generate_v1_0_0.py. La versión 1.1 añadió comprobación de IDs contra catálogo, reservados, duplicados, tipos, campos mínimos y límite int64. Los CSV de cantidades no cambiaron para favorecer a un algoritmo. Las diez pruebas de su ronda anterior tienen evidencia, pero no se ejecutan en esta tarea porque algunas regeneran copias temporales.

Los grises incluyen evidencia incompleta y fechas de disponibilidad, pero siguen siendo fichas alternativas que comparten una clave de ejemplo. No representan diez observaciones reales independientes ni una política de abstención implementada. Sus banderas y fechas no prueban que una futura API sepa resolverlos. No se unen al CSV supervisado.

El dataset permite construir, entrenar, validar y demostrar un proceso académico reproducible. Eso es **validación técnica**. La **validación comercial** exigirá historia real certificada, disponibilidad conocida y evaluación posterior en la tienda. Una buena métrica sintética no permite afirmar que el modelo predice correctamente las ventas reales de la empresa. Los datos permanecen en archivos locales, sin insertarse en Sale, SaleItem o Neon.

## 4. Estructura y diccionario de variables

Se confirma este orden exacto de nueve columnas:

```text
mes_objetivo,productId,locationId,ventas_mes_anterior,ventas_hace_2_meses,ventas_hace_3_meses,mes_sin,mes_cos,target_ventas_mes
```

Se pronostica el mes m al cierre de m-1, cuando la captura anterior está completa. Los ejemplos son didácticos, no una fila real consultada.

| Columna | Significado | Función | Tipo esperado | Disponible | Ejemplo |
|---|---|---|---|---|---|
| mes_objetivo | Mes m que se quiere estimar | IDENTIFICADOR temporal | Texto YYYY-MM | Antes de comenzar m | 2025-01 |
| productId | Clave de Product.id | IDENTIFICADOR | int32 positivo del catálogo | Al fijar catálogo | 15 |
| locationId | Clave de Location.id con type TIENDA | IDENTIFICADOR | int32 positivo del catálogo | Al fijar sucursales | 5 |
| ventas_mes_anterior | Unidades de m-1 del mismo par | FEATURE | int64 no negativo | Cierre de m-1 | 12 en diciembre |
| ventas_hace_2_meses | Unidades de m-2 | FEATURE | int64 no negativo | Cierre de m-2 | 10 en noviembre |
| ventas_hace_3_meses | Unidades de m-3 | FEATURE | int64 no negativo | Cierre de m-3 | 8 en octubre |
| mes_sin | Seno del ciclo mensual de m | FEATURE | float64 finito, de -1 a 1 | Conocido de antemano | 0 para enero |
| mes_cos | Coseno del ciclo mensual de m | FEATURE | float64 finito, de -1 a 1 | Conocido de antemano | 1 para enero |
| target_ventas_mes | Unidades brutas observadas en m | TARGET | int64 no negativo | Cierre completo de m, solo conocido al entrenar o evaluar | 17 en enero |

El conjunto inicial tiene **cinco features**, tres identificadores y un target. productId y locationId sirven para construir series, seleccionar ejemplos y mostrar resultados. No se entregan como cantidades al modelo. Si después se evalúan como entradas categóricas, se registrará una variante con codificación ajustada solo en training. Esa variante no es la configuración inicial de cinco features. Manejar una categoría desconocida técnicamente no acredita historia suficiente para pronosticar.

Los lags son ventas anteriores del mismo producto y tienda. Se verificará el mes exacto, no solo la fila previa. Para enero de 2025 se utilizan diciembre, noviembre y octubre de 2024. El target es la cantidad de enero, sin desplazarla otra vez. Para k entre 1 y 12, el calendario utiliza mes_sin = sin(2π(k-1)/12) y mes_cos = cos(2π(k-1)/12). Así diciembre y enero quedan próximos en el ciclo.

promedio_3_meses queda fuera. Es la suma de los tres lags dividida entre tres, por lo que no aporta información nueva y crea dependencia lineal exacta. Una variante posterior necesitaría justificación y comparación mediante validación.

Estas cinco features forman una base sencilla porque reúnen comportamiento reciente y posición dentro del año sin exigir una historia comercial que el proyecto todavía no puede certificar. Los tres lags permiten estudiar continuidad o cambios recientes. Seno y coseno representan un calendario conocido antes de vender. Esta elección facilita revisar errores y comparar algoritmos con las mismas entradas, pero no explica por sí sola promociones, disponibilidad o cambios permanentes del negocio.

## 5. Información excluida y protección temporal

Data leakage significa utilizar información que todavía no se conocía al pronosticar. Por ejemplo, repetir el stock consultado hoy como si fuera el de enero de 2025 incorpora ventas posteriores. Ajustar un scaler con todos los meses permite que validation y test influyan en la preparación del entrenamiento.

| Información no utilizada inicialmente | Motivo |
|---|---|
| Inventory.stock y minStock actuales | No reconstruyen disponibilidad o reglas históricas |
| Product.price1, wholesalePrice y cost actuales | No son los precios o costos conocidos en cada mes anterior |
| Product.price2 | Campo legacy, fuera de los modos comerciales actuales |
| Sale.total, SaleItem.quantity, unitPrice y subtotal del mes objetivo como features | Se conocen después de las transacciones que se pretende anticipar. quantity es fuente del target, no entrada del mismo mes |
| Devoluciones, anulaciones o cargas retroactivas conocidas después del corte | No deben reescribir las entradas que estaban disponibles antes |
| Personas, NIT, contactos, vendedor y referencias bancarias | No forman parte del conjunto mínimo justificado |
| Promedios calculados con todo el periodo o ventanas centradas | Incluyen futuro |
| Rotación simulada, clase, escenario, tasas internas y parámetros latentes | Revelan el mecanismo de generación o son metadatos de diagnóstico |

Sale.status existe ahora, pero su valor actual no basta para reconstruir el pasado. Una anulación posterior exige revisar voidedAt y cuándo se conoció. saleDate y createdAt tampoco son intercambiables. Una carga con fecha antigua puede haber sido registrada después del pronóstico. Un backtest real necesitará cierres o copias de estado verificables. Las devoluciones permanecen separadas del target bruto, sin convertirlo en ventas negativas.

Categoría, marca, modelo de vehículo, fabricante, precio histórico anterior, devoluciones previas e índice temporal son posibles variantes posteriores. No se agregan automáticamente. Product.year describe aplicaciones de vehículos, a veces mediante rangos, y no es el año de venta. Product.detail y detalles son textos fuera de las entradas iniciales. Product.quality no pertenece al contrato Prisma revisado.

## 6. División temporal y preparación

Training ajusta el modelo. Validation permite comparar modelos y configuraciones. Test mide el resultado final después de congelar las decisiones. Si solo se reservan training y test y se consulta test repetidamente para elegir, deja de existir una evaluación independiente. Una validación temporal interna también puede apoyar esa selección, conservando siempre el test final.

| Uso | Meses incluidos | Meses | Filas | Proporción supervisada |
|---|---|---:|---:|---:|
| Historia inicial | Octubre a diciembre de 2024 | 3 | 504 de apoyo | Fuera del reparto de targets |
| TRAIN | Enero de 2025 a marzo de 2026 | 15 | 2.520 | 71,43 % |
| VALIDATION | Abril a junio de 2026 | 3 | 504 | 14,29 % |
| TEST | Julio a septiembre de 2026 | 3 | 504 | 14,29 % |

Es la aproximación a **70/15/15** con meses completos. El denominador es 21 meses supervisados, no los 24 meses base. Todos los productos y tiendas del mismo mes permanecen juntos. No se usa train_test_split aleatorio. Entrenar con agosto para intentar evaluar abril introduciría futuro en el pasado.

La evaluación es mensual de un paso. Para mayo se permite usar abril ya observado. Para agosto se permite usar julio ya cerrado, aunque julio pertenezca a test. Se incorpora el dato observado como historia al avanzar el reloj, sin usar el error de test para cambiar parámetros. Esto no equivale a emitir tres pronósticos desde marzo sin conocer los meses intermedios. Si el cierre real tarda, se retrasa la emisión o se revisa el contrato.

Como comprobación adicional se propone [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) dentro de TRAIN, aplicado a meses únicos y trasladado a todas sus filas. Con tres validaciones internas de tres meses se usarían enero-junio de 2025 para julio-septiembre, enero-septiembre para octubre-diciembre y enero-diciembre para enero-marzo de 2026. Los entrenamientos crecen. Cada transformación se aprende de nuevo solo en el entrenamiento de ese corte. No se divide directamente una lista de filas si eso parte un mes. Cualquier separación adicional entre bloques dependerá del retraso real de disponibilidad, no de una regla arbitraria.

## 7. Normalización y representación

Normalizar o escalar expresa entradas en magnitudes comparables. [StandardScaler](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.StandardScaler.html) utiliza media y desviación del entrenamiento. Cuando corresponda, fit se hará **solo con TRAIN**. Después se aplica transform a training, validation y test con esos mismos valores. Nunca se aprende la media con todo el dataset. La misma regla se repite por corte interno.

LinearRegression por mínimos cuadrados ordinarios puede trabajar sin escalado. StandardScaler es opcional para estabilidad numérica y comparación de coeficientes. Random Forest no necesita escalado numérico para sus divisiones. Para MLP se recomienda escalar los lags. mes_sin y mes_cos ya están entre -1 y 1 y no necesitan una escala adicional obligatoria. Las cantidades del target se conservan en unidades para interpretar los errores.

Los identificadores no se escalan como números. Si se prueba una variante categórica, el codificador se ajusta únicamente con training y se guarda con el modelo. Ceros válidos no se eliminan ni se confunden con faltantes. Las filas inválidas se rechazan antes de preparar matrices. Los casos ambiguos no se completan con ceros o medias inventadas.

## 8. Algoritmos, comparación y decisión

Se comparan opciones de distinta complejidad para comprobar si un mayor costo aporta una mejora útil. Todas utilizan las mismas fechas, target y política de evaluación.

| Alternativa | Papel y ventaja | Límites y costo |
|---|---|---|
| Baseline ingenuo | Predicción = ventas_mes_anterior. Referencia mínima, sin ajuste de parámetros | Muy simple, no representa otros cambios. Costo mínimo |
| LinearRegression | Primer modelo de Machine Learning, rápido e interpretable mediante coeficientes | Relación lineal, sensibilidad a entradas dependientes y posibles predicciones negativas. Costo bajo |
| RandomForestRegressor | Candidato principal. Combina árboles y representa relaciones no lineales en tablas | Puede memorizar, sobreajustar y extrapolar mal tendencias. Más árboles y profundidad aumentan costo |
| MLP de regresión, opcional | Red neuronal capaz de representar relaciones complejas | Más configuración, escalado, tiempo e inestabilidad con poca diversidad. Menor interpretabilidad |

Como referencia adicional opcional se podrá evaluar el baseline estacional, predicción igual al mismo mes del año anterior. Solo se calcula donde exista ese mes conocido, con cobertura explícita y comparación sobre las mismas filas. No se inventará el año faltante ni se alterará el split para favorecerlo. No añade una sexta feature al contrato inicial ni reemplaza el baseline obligatorio del último mes.

[LinearRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html) aprende una combinación lineal de las entradas buscando reducir errores cuadrados. Sus coeficientes facilitan explicar el modelo. Se conservarán sus predicciones originales y métricas. Si la demostración muestra max(0, predicción), esa política se registrará también con sus métricas comparables. No se recortan targets ni se redondean salidas antes de calcular el error principal.

[RandomForestRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html) aprende varios árboles y combina sus predicciones mediante un promedio. Es el candidato principal por la estructura tabular, su capacidad no lineal y una complejidad manejable. En la configuración inicial aprende de lags y calendario, no de IDs numéricos. Podrían explorarse n_estimators, max_depth, min_samples_leaf y max_features mediante una búsqueda pequeña documentada. **Random Forest es candidato, no ganador.**

La MLP se consideró por la explicación del docente. Una arquitectura de prueba sería entrada procesada → 64 neuronas ReLU → 32 neuronas ReLU → 1 salida lineal. ReLU introduce una transformación no lineal en capas ocultas. La salida lineal permite estimar cantidades, aunque también puede producir negativos. 64 y 32 son hiperparámetros, es decir, configuraciones elegidas antes de aprender. No hay obligación de usar neuronas pares, un número par de capas o una arquitectura universal. Debe validarse. Por escalado, configuración, sobreajuste e interpretabilidad no es la primera elección. Si se solicita probar [MLPRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPRegressor.html), su selección y parada respetarán validación temporal. Una partición interna aleatoria no reemplaza los cortes del proyecto.

Se seleccionará con MAE de validation como criterio principal, acompañado de RMSE, R², estabilidad mensual, cobertura por grupo y costo. La validación temporal interna apoya el control del sobreajuste. Si el modelo complejo no mejora de forma útil al baseline, se conservará la referencia simple o se declarará que no existe mejora suficiente. El umbral de mejora útil se documentará antes de comparar, sin inventar un valor comercial. Solo después se abrirá test con decisiones congeladas. No se cambiará el generador para hacer ganar a un candidato.

## 9. Métricas y resultados pendientes

MAE es el promedio del error absoluto. **MAE = 2,4** significa una desviación media de unas **2,4 unidades por producto, tienda y mes**. Es la métrica principal. RMSE eleva errores al cuadrado, los promedia y toma la raíz. También se expresa en unidades, pero penaliza más los errores grandes.

[R²](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.r2_score.html) compara el error con una referencia basada en la media de los valores evaluados. Puede ser negativo. Un R² de 0,80 no es 80 % de precisión. Con pocas observaciones o un target constante puede no ser informativo. Se indicará esa condición, sin ocultarla mediante un valor finito por defecto. No se utiliza Accuracy. MAPE no será principal porque divide por las ventas observadas y presenta problemas con ceros o valores pequeños.

Se mostrarán métricas globales, por tienda, producto cuando haya soporte, rotación, mes y escenarios. Cada desglose incluirá número de casos y cobertura, incluidos aquellos sin predicción. Solo 24 meses y dos ciclos anuales simulados no equivalen a miles de meses independientes, aunque el panel tenga miles de filas.

La tabla de resultados permanece pendiente. No se llenan valores de ejemplo como si fueran métricas obtenidas.

| Modelo | Configuración | MAE validation | RMSE validation | R² validation | Decisión |
|---|---|---|---|---|---|
| Baseline | Último mes | Pendiente | Pendiente | Pendiente | Referencia |
| LinearRegression | Por registrar | Pendiente | Pendiente | Pendiente | Por evaluar |
| RandomForestRegressor | Por registrar | Pendiente | Pendiente | Pendiente | Candidato principal |
| MLP, si se autoriza el experimento | Por registrar | No ejecutado | No ejecutado | No ejecutado | Opcional |

La evaluación final de test se registrará después de seleccionar, con fecha, configuración congelada, MAE, RMSE, R², cantidad de filas y limitaciones. Si se decide volver a ajustar con TRAIN y VALIDATION antes del test, debe quedar acordado previamente y se reajustarán transformaciones solo con esa unión. No se mezclan métricas del modelo anterior con las del artefacto reajustado. No se ha realizado ese ajuste.

## 10. Escenarios que pueden afectar la predicción

Los casos normales son observaciones válidas. Los adversos válidos también forman parte del aprendizaje. Los inválidos se rechazan. Los ambiguos requieren una respuesta según lo que falta, no cantidades negativas o etiquetas inventadas. Las clases POSITIVO, NEGATIVO y GRIS describen pruebas, no el target de una clasificación.

Los problemas se agrupan en calidad de datos, situaciones comerciales válidas o ambiguas y cambios que afectan al modelo. Un mes incompleto, una captura caída o un registro retroactivo pueden parecer una caída de ventas sin que el negocio haya cambiado. Primero se confirma el cierre y la disponibilidad del registro. Un producto o una tienda nuevos necesitan tres meses completos y una incorporación evaluada en una versión posterior. No se inventan lags ni se trasladan inmediatamente los patrones de otra tienda.

La falta de stock y la descontinuación también pueden producir ceros con significados distintos. La primera oculta demanda no satisfecha. La segunda requiere verificar que el producto siga comercializándose. Un historial confiable de stockout, es decir, periodos sin disponibilidad, permitiría estudiar una mejora futura. No existe esa señal en las cinco features iniciales.

| Escenario | Tipo | Efecto y respuesta prevista |
|---|---|---|
| Mes incompleto, faltante, captura caída o carga retroactiva | ERROR DE DATOS o CASO AMBIGUO | Puede producir una falsa caída. No utilizar el periodo hasta confirmar cierre, completitud y momento de conocimiento |
| Producto nuevo | CASO AMBIGUO | Marcar HISTORIAL INSUFICIENTE. Sin lags inventados ni pronóstico forzado. Incorporar en otro entrenamiento cuando reúna historia suficiente |
| Tienda o combinación nuevas | CASO AMBIGUO | Aplicar la misma comprobación de historia y cobertura. No asumir que otra tienda representa su comportamiento |
| Falta de stock | CASO AMBIGUO | Ventas cero no demuestran demanda cero. Mantener el objetivo de ventas observadas y estudiar disponibilidad histórica cuando exista |
| Producto descontinuado o sustitución dudosa | CAMBIO DEL NEGOCIO o CASO AMBIGUO | Verificar vigencia y equivalencias. No interpretar automáticamente los ceros como baja demanda ni trasladar historia entre productos |
| Mayorista extraordinaria válida | CASO VÁLIDO | Conservar la operación. Medir su impacto sobre MAE y RMSE, sin eliminarla por ser grande |
| Devolución o anulación posterior | CASO VÁLIDO con revisión temporal | Mantener la definición bruta y revisar elegibilidad según fecha de conocimiento. No usar eventos futuros para modificar entradas antiguas |
| Precio, promoción o proveedor cambian | CAMBIO DEL NEGOCIO | Documentar la limitación inicial. Evaluar una feature temporal solo cuando haya historia verificable, sin reutilizar precios actuales como históricos |
| Tendencia o estacionalidad cambian persistentemente | CAMBIO DEL NEGOCIO | Investigar drift, descartar errores de captura y evaluar reentrenamiento si hay datos suficientes |
| Duplicados, cantidades inválidas, IDs inexistentes o unidades incompatibles | ERROR DE DATOS | Rechazar o corregir mediante un proceso autorizado antes de entrenar. Revisar también uniones que multiplican filas |
| Demo, sintéticos y reales mezclados | ERROR DE DATOS | Separar origen y versiones. Nunca insertar simulación en Sale o SaleItem. Reentrenar con la mezcla no corrige el problema |
| Overfitting | CAMBIO DEL MODELO | Buen training y mal resultado posterior indican posible sobreajuste. Limitar complejidad, validar temporalmente, mantener test separado y comparar con baseline |
| Se aprende el generador sintético | CAMBIO DEL MODELO y límite experimental | Excluir parámetros internos, revisar adversos y distinguir validación técnica de comercial |
| Buen MAE global pero mal resultado local | CAMBIO DEL MODELO o cobertura insuficiente | Mostrar errores por tienda, rotación, mes y producto cuando haya soporte, sin esconder grupos escasos |
| Catálogo, formatos, versiones o contrato incompatibles | ERROR DE DATOS o CAMBIO DEL NEGOCIO | Comprobar identidad, hashes y contrato. Categorías siguen fuera de las features iniciales. No activar un artefacto incompatible |
| Predicción negativa o no finita | CAMBIO DEL MODELO o fallo técnico | Bloquear no finitos y registrar tratamiento de negativos con métricas originales. Investigar la causa antes de sustituir el modelo |

CAMBIO DEL MODELO agrupa problemas de ajuste o representación que requieren revisar el modelo, no significa que ya exista uno modificándose automáticamente. La misma señal puede tener varias causas y necesita diagnóstico.

Por ejemplo, pasar de unas 10 unidades habituales a unas 25 durante varios meses puede ser un cambio del negocio. Data drift significa que los datos actuales empiezan a comportarse de manera distinta a los utilizados para entrenar. También puede cambiar la relación entre historia y ventas posteriores. Un aumento aislado no demuestra drift ni obliga a reentrenar. Se revisan procedencia, captura, disponibilidad, mezcla de productos y contexto comercial antes de atribuir el cambio al modelo.

La cobertura adversa guardada incluye picos, caídas mensuales, ceros y series constantes. No cubre suficientemente caídas persistentes, recuperación después de crisis, cierres, disponibilidad física o estacionalidad cambiante. Los grises tampoco son un resolvedor implementado. Antes de afirmar robustez integral se diseñarán suites independientes con evidencia, disponibilidad temporal y respuesta esperada. No es necesario convertirlas en filas de la misma tabla limpia.

La versión 1.1 es utilizable para un experimento académico básico con estas limitaciones. Antes de entrenar se debe verificar integridad, fijar features, split, criterios de selección y política de negativos. Si falla un contrato estructural, se detiene la preparación. Si una distribución es extraña, se revisan supuestos sin borrar ejemplos para conseguir mejores métricas. La aprobación comercial continúa pendiente.

## 11. Ciclo de vida y reentrenamiento

El modelo no se entrenará una sola vez para utilizarlo indefinidamente. Su ciclo propuesto es datos nuevos → validación de calidad → predicciones → medición del error → monitoreo → detección de cambios → reentrenamiento cuando corresponda → candidato → comparación → activación o rechazo. Este ciclo está documentado, no implementado. En H4 se comprenderá y ensayará localmente. Su gestión administrativa productiva pertenece a H5.

El monitoreo consiste en revisar cómo funciona el modelo después de emitir predicciones. Se conservarían producto, tienda, mes objetivo, fecha de emisión, versión, origen del dataset, resultado previsto y estado de cobertura. Cuando cierre el mes y se valide el total observado, se calcularían MAE, RMSE y los desgloses. Sin un mes cerrado no se presentará un error parcial como definitivo. La [definición de MAE](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_error.html) permite expresar ese error en unidades, pero su interpretación requiere considerar el volumen y la composición de las series.

Se observarán errores globales y por tienda, rotación, mes y producto con suficientes casos. También se registrarán series sin pronóstico, faltantes y abstenciones. Una mejora global que reduzca cobertura o empeore un grupo importante no se aceptará sin revisión. Comparar el error reciente con el baseline del mismo periodo ayuda a distinguir si el modelo aporta valor. El cambio de mezcla de productos o un mes mayorista extraordinario puede alterar el promedio sin demostrar que todo el modelo se deterioró.

Puede recomendarse evaluar reentrenamiento cuando haya información nueva suficiente, aumento sostenido del MAE reciente, drift, cambios persistentes del patrón temporal, varios productos con comportamiento nuevo, cambios importantes del catálogo, una tienda que ya reunió historia o disminución de cobertura. No se fija todavía un porcentaje, una cantidad de meses o un umbral de alarma comercial. Se acordarán con evidencia de validación y operación. La demo local tendrá sus propios parámetros visibles, definidos en la sección 13 y sin valor de política comercial.

**No todo se soluciona reentrenando.** Duplicados, demo mezclado, meses incompletos, cantidades inválidas, IDs inexistentes, errores de stock o ventas repetidas se investigan y corrigen primero en su fuente mediante un procedimiento autorizado. Después se valida una versión nueva de datos si corresponde. Un candidato entrenado con errores solo aprendería esos errores. Tampoco se corrige un fallo del servicio o un archivo incompatible cambiando pesos del modelo.

En H4 habrá una acción local **ENSAYAR REENTRENAMIENTO**. Su recorrido será validar historial simulado → congelar una versión local de datos → fijar cortes temporales → preparar features → entrenar CANDIDATE → evaluar una ventana apropiada → comparar con ACTIVE → habilitar promoción o registrar rechazo. Se mostrará progreso y se impedirá iniciar otra ejecución mientras esté pendiente. No cambia ACTIVE por entrenar o terminar una tarea. Si falla la preparación, el entrenamiento o la evaluación, se conserva la versión activa. El botón ADMIN productivo REENTRENAR MODELO, sus permisos y jobs de backend pertenecen a H5.

Champion significa modelo activo. Challenger significa nuevo candidato. En una primera entrega todavía no hay champion. Se compara contra baseline y modelos candidatos para elegir la primera versión. En versiones siguientes ambos se evaluarán con las mismas features compatibles, meses, filas elegibles, origen y política de métricas. La ventana de comparación debe ser posterior a los datos usados por ambos para aprender. El champion conserva sus transformaciones originales, sin volver a ajustarlas sobre los datos de evaluación. El candidato aprende las suyas solo con su training. Comparar el MAE de un modelo en una ventana fácil con el de otro en una ventana distinta no demuestra mejora.

Antes de promover se revisarán MAE principal, RMSE, R², estabilidad, errores locales, cobertura, complejidad y reproducibilidad. El criterio de mejora suficiente se definirá antes de comparar, sin inventar ahora un umbral. El candidato podrá rechazarse por regresiones relevantes, poca evidencia o incompatibilidad aunque sea más reciente o tenga mejor promedio global. La decisión debe conservar responsable, motivo y reporte. El paso de datos sintéticos a comerciales exige además certificar procedencia y suficiencia. Una versión sintética no se convierte en comercial por cambiar su estado.

El test inicial de julio a septiembre de 2026 se utiliza una sola vez para evaluar la configuración V1 congelada. Sus resultados, artefacto y hashes quedarán conservados. El ensayo del día 13 será un experimento distinto en una rama local de simulación. No reutilizará targets del test inicial para ajustar candidatos ni escoger una versión mejor. La [guía de validación](https://scikit-learn.org/stable/modules/cross_validation.html) respalda separar selección de evaluación final.

Para el ensayo se acumularán meses nuevos simulados, posteriores al panel 1.1. Se fijará un corte T antes de entrenar. CANDIDATE aprenderá únicamente con datos elegibles hasta T y sus transformaciones se ajustarán solo en ese entrenamiento. ACTIVE mantendrá las suyas. Ambos se compararán después de congelarlos, sobre los mismos meses posteriores a T y las mismas filas elegibles. Esos meses de comparación no entran en su ajuste. Si falta historia nueva o una ventana comparable, se mostrará ENSAYO NO DISPONIBLE, sin fabricar una mejora. Se conservarán las predicciones de ambos, incluidos casos sin cobertura. Ninguna edición posterior modifica la evaluación de V1 ya entregada.

La ventana local sirve para decidir una promoción demostrativa, no constituye otro test final independiente ni valida ventas comerciales. Al activar V2 localmente se abre un tramo nuevo de seguimiento, sin mezclarlo con métricas de V1. La presentación conservará V1 y su test original, aunque la sesión demuestre promoción, rechazo o retorno. Si se desea medir independientemente V2 después de escogerla, harán falta otros meses aún no utilizados para esa decisión.

Se propone un registro local simple de modelos para H4, con versiones v1, v2 y v3, identificador de ejecución, contrato, hashes, datos, transformaciones, métricas y ubicación del artefacto. Puede representarse mediante carpetas versionadas y un archivo JSON. Todavía no existe ese registro. Su persistencia y gestión productiva desde backend quedan para H5, sin crear ahora tablas Prisma.

| Estado propuesto | Significado |
|---|---|
| CANDIDATE | Entrenado, pendiente de comparación o aprobación |
| ACTIVE | Versión elegida para inferencia en el entorno indicado |
| REJECTED | Evaluado y descartado, con motivo conservado |
| ARCHIVED | Versión anterior retirada de uso, conservada para trazabilidad o retorno |

Como ejemplo conceptual, v1 podría estar ARCHIVED, v2 ACTIVE y v3 REJECTED. No son versiones existentes ni resultados obtenidos. En una demo, ACTIVE significa activa localmente, no desplegada en producción. Solo habrá una referencia activa por entorno y contrato.

**ACTIVAR CANDIDATO** será una acción explícita del simulador H4, habilitada solo si hay comparación válida, criterios cumplidos, contrato compatible y evidencia conservada. Un mejor MAE aislado no permite omitir cobertura, errores por grupos y validación. REJECTED no puede activarse. El cambio afecta solo la referencia de esa sesión local, no a otras sesiones ni a producción. Entrenar nunca promueve automáticamente.

Rollback significa volver a una versión anterior si la nueva presenta problemas. En H4, **VOLVER A VERSIÓN ANTERIOR** comprobará compatibilidad de features, preprocesador, artefacto y entorno, solicitará motivo y restaurará la referencia local completa. No se borrará el modelo anterior al activar el siguiente. No se mezclará un modelo viejo con un scaler nuevo. Se conservarán las decisiones y predicciones anteriores con sus versiones originales. Si ninguna versión es compatible o segura, se informará que no hay predicción disponible. La activación, rollback y sus permisos productivos desde la UI de RepuestoPro pertenecen a H5.

## 12. Stack tecnológico de H4

La revisión del 3 de noviembre distingue lo instalado de lo propuesto. Se consultaron package.json, paquetes locales de backend y frontend, metadatos del Python general y del entorno de visión, requisitos de ia-service y archivos de ml/demand. No se instalaron dependencias. Una dependencia detectada en un intérprete no equivale a un entorno H4 fijado y reproducible.

| Tecnología | Estado comprobado | Papel y decisión para H4 |
|---|---|---|
| PostgreSQL y Neon | EXISTENTES como base operativa, según proyecto y auditorías. Herramienta PostgreSQL local 16.14. Versión del servidor Neon no consultada | Fuente comercial futura. El sintético sigue en archivos separados. Sin conexión a Neon en esta tarea |
| Prisma CLI y @prisma/client | EXISTENTES, ambos 5.22.0 instalados. package.json declara rangos, no esos números exactos | Acceso operativo desde backend. No se necesita modificar Prisma para el experimento local |
| CSV y JSON | EXISTENTES en ml/demand | Datos tabulares, catálogo, manifiestos, hashes y metadatos |
| Python | EXISTENTE, 3.11.9 en el intérprete general consultado y en la generación registrada | Lenguaje del proceso de datos, modelos e inferencia local |
| NumPy | EXISTENTE 2.4.6 en Python general | Operaciones numéricas. Su uso y fijación como dependencia H4 son PROPUESTOS |
| pandas | EXISTENTE 3.0.6 en Python general | Lectura y preparación tabular. Su adopción en H4 es PROPUESTA |
| scikit-learn | EXISTENTE 1.9.1 en Python general | Preprocesamiento, modelos, validación y métricas. Integración H4 PROPUESTA, sin entrenamiento realizado |
| joblib | EXISTENTE 1.6.0 en Python general | Persistencia del conjunto entrenado si se adopta. Uso en H4 PROPUESTO |
| Matplotlib | EXISTENTE 3.11.2 en Python general | PROPUESTO para gráficos y exportaciones. Complementa la interfaz Streamlit, no sustituye la interacción requerida |
| Streamlit | EXISTENTE 1.66.1 desde el 4 de noviembre, instalado solo en ml/demand/.venv | Primera interfaz local de Ross con controles, edición, gráficos y validaciones. Sin motor ni modelo conectados |
| Node.js | EXISTENTE, v24.16.0 consultado | Runtime del backend. No hace falta integrar inferencia a Express para demostrar el experimento H4 |
| Express y TypeScript de backend | EXISTENTES, 4.22.3 y 5.9.3 instalados | API operativa actual. Adaptador predictivo completo previsto para H5 |
| React, Vite y TypeScript de frontend | EXISTENTES, 18.3.1, 5.4.21 y 5.9.3 instalados | Interfaz web actual. La administración completa del ciclo de modelos queda para H5 |
| Recharts | EXISTENTE, 2.15.4 instalado en frontend | Utilizado en la consulta administrativa sintética de H4. La ampliación autorizada está en la sección 22. Streamlit continúa separado |
| Git y GitHub | EXISTENTES. Git 2.54.0.windows.1 y remoto GitHub configurado localmente | Historia del proyecto y revisión del equipo. No se ejecutan commit, push o cambios de historia en esta tarea |
| Markdown, hashes y log de prompts | EXISTENTES | Documentación y trazabilidad. experiments.csv y los modelos guardados siguen PROPUESTOS y pendientes |

Las versiones generales son observaciones del 3 de noviembre, no una promesa de compatibilidad probada para entrenamiento. La entrega de Ross del día 4 creó ml/demand/.venv con Python 3.11.9, Streamlit 1.66.1 y pandas 3.1.0, sin modificar Python general ni visión. requirements-ui.txt declara dependencias directas y requirements-ui.lock.txt conserva las 34 versiones del entorno probado. Ese entorno es de interfaz, todavía no un entorno de entrenamiento certificado. scikit-learn, joblib y Matplotlib no se instalaron allí para esta tarea.

ia-service/requirements.txt pertenece a visión H3. Declara FastAPI, Uvicorn, NumPy y otras dependencias de imágenes. En su entorno se detectaron Python 3.11.9, NumPy 2.4.6 y Matplotlib 3.11.2, pero no pandas, scikit-learn o joblib. No se presenta ese entorno como el entorno de demanda ni se modifica para compartir entrenamiento con YOLO. Tampoco se propone una red neuronal o GPU como requisito inicial.

Si se utiliza joblib se guardará el modelo con sus transformaciones y versiones verificadas. La [documentación de persistencia](https://scikit-learn.org/stable/model_persistence.html) advierte que la compatibilidad entre versiones no debe suponerse y que solo se carguen artefactos de procedencia confiable. Conservar un archivo sin sus dependencias no basta para garantizar rollback.

Se eligió **Streamlit para la primera interfaz local H4** y se comprobó esa entrega en el entorno aislado. No se modifica el stack de la aplicación. El simulador se ejecuta localmente, sin credenciales de Neon, conexión a ventas ni despliegue. La ampliación autorizada en la sección 22 agrega una consulta administrativa en React, manteniendo separado el simulador. Consultar una predicción no genera datos ni entrena.

| Criterio | Streamlit aislado | React existente + servicio Python local |
|---|---|---|
| Tiempo en tres semanas | Formularios y vistas desde Python, un proceso local de interfaz | Requiere acordar API, iniciar servicio y web, manejar errores entre ambos |
| Edición y respuesta | Controles editables y botón explícito sin entrenar | Buen control de interfaz, pero requiere sincronizar estado con el servicio |
| Integración con modelos | Llama directamente a funciones Python | Necesita serialización y contrato HTTP con Python |
| Gráficos | Tablas y gráficos integrados, con Matplotlib para exportar | Reutiliza Recharts, con integración de respuestas y estados |
| Mantenimiento | Una dependencia exclusiva H4 y código Python separado | Reutiliza React, pero añade un servicio y coordinación entre dos capas |
| Riesgo para RepuestoPro | No cambia rutas, sesión, ventas o frontend productivo | Puede aislarse, aunque aumenta el alcance y riesgo de tocar la aplicación |

La elección prioriza plazo y aislamiento, no apariencia. Los [formularios de Streamlit](https://docs.streamlit.io/develop/concepts/architecture/forms) permiten enviar varias entradas mediante un botón. Su [estado de sesión](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state) permite conservar la simulación entre interacciones. Un refresco o desconexión puede perder ese estado, por lo que no se promete persistencia comercial. Una exportación voluntaria a archivos locales deberá identificarse como SIMULACIÓN.

## 13. Simulador interactivo y arquitectura local

La demo obligatoria de H4 será un **simulador local editable**. Un generador de CSV o un script estático no cumplen este requisito. El generador 1.1 sigue como evidencia reproducible, sin alteraciones. El simulador trabajará con copias de sesión y meses nuevos separados. No guardará cambios sobre el dataset histórico, Sale, SaleItem o Neon. Todo resultado mostrará origen **SIMULACIÓN**.

El validate actual de generate_synthetic.py comprueba un panel completo de 24 meses y los meses supervisados guardados. No es todavía un validador de sesiones extensibles. Se desarrollará un validador de entrada local con el mismo contrato de cantidades, IDs y calendario, pero con controles de cierre y disponibilidad propios de cada sesión. No se eliminarán las restricciones del validador histórico para permitir meses nuevos ni se ejecutará el generador al refrescar la pantalla.

La pantalla reunirá selectores, historia reciente, editor, predicción, avance temporal, gráfico y monitoreo. Separará tres acciones: **EDITAR ESCENARIO** modifica entradas de la sesión, **PREDECIR** aplica el modelo ACTIVE sin aprender y **ENSAYAR REENTRENAMIENTO** entrena otro CANDIDATE con historia actualizada. Editar o predecir nunca ejecutan fit. Una recomendación de revisión tampoco inicia entrenamiento.

| Control o información | Comportamiento previsto |
|---|---|
| PRODUCTO | Selector de productos válidos del catálogo de referencia. IDs reservados o inexistentes no se aceptan como productos nuevos |
| TIENDA | Tienda 1, Tienda 2 y Tienda 3, con locationId 5, 6 y 7. La elección consulta la historia de ese par |
| MES OBJETIVO | Mes válido YYYY-MM y reloj simulado explícito. Cambiar de mes recupera los tres meses consecutivos correspondientes, no mueve lags arbitrariamente |
| VENTAS HACE 3 MESES, HACE 2 MESES y MES ANTERIOR | Cantidades enteras no negativas editables. Los campos se etiquetan con sus meses para evitar invertir el orden |
| mes_sin y mes_cos | Derivados automáticamente del mes objetivo con la fórmula del contrato. Solo lectura en la demo, sin edición manual |
| ESCENARIO | Precarga supuestos en una copia de trabajo. Luego permite edición manual, sin restaurar valores por una simple actualización de pantalla |
| VENTA OBSERVADA DEL MES | Resultado posterior a la predicción, separado visualmente de las entradas. Solo se revela o acepta después de emitir el pronóstico |
| Estado de datos y cobertura | Mes completo, meses de historia disponibles, validez y motivo de abstención. Son controles de elegibilidad, no features |

productId y locationId seleccionan historia y cobertura. **No son features numéricas.** En la configuración inicial, cambiar producto o tienda conservando exactamente los mismos cinco valores puede producir la misma predicción. Tampoco el nombre del escenario causa por sí solo una respuesta distinta. No se atribuirá al modelo una sensibilidad que no está en su contrato.

**PREDECIR** validará controles y elegibilidad, construirá exactamente las cinco features en el orden del artefacto, resolverá la referencia ACTIVE de la sesión y ejecutará inferencia. Mostrará unidades estimadas, algoritmo, versión, corte simulado, features y origen. Si no hay artefacto compatible, indicará MODELO NO DISPONIBLE. Durante la primera semana solo se podrá verificar entradas y calendario. Desde la segunda habrá una referencia baseline claramente etiquetada y luego candidatos entrenados. No se presentará una salida ficticia como predicción ML.

Se elige un **botón explícito PREDECIR**, sin recalcular ni entrenar con cada pulsación del teclado. Las entradas se envían juntas y la respuesta se muestra al terminar la inferencia local. No se promete una latencia todavía no medida. La versión, mes y features utilizados quedan asociados a esa predicción. Los cambios pendientes se confirmarán con el mismo formulario antes de predecir, avanzar o generar, sin perder valores por accionar otro botón. Si una edición invalida un resultado anterior, se mostrará como pendiente de recalcular y no se usará para medir error.

| Escenario preconfigurado | Precarga y propósito |
|---|---|
| NORMAL | Historia estable con variación moderada |
| CRECIMIENTO | Historia ascendente, por ejemplo lag3=8, lag2=12, lag1=17 |
| CAÍDA | Descenso de ventas observadas, sin valores negativos |
| PICO MAYORISTA | Mes extraordinario válido. No se borra por ser alto |
| STOCKOUT | Resultado limitado por disponibilidad, con demanda interna separada |
| PRODUCTO NUEVO | Producto válido sin tres meses de historia en esta rama de simulación. Debe abstenerse |
| CAMBIO PERSISTENTE | Varios meses nuevos con otro nivel o patrón, para observar deterioro y revisión |
| RECUPERACIÓN | Retorno gradual tras una caída o falta de disponibilidad |

Las ocho opciones ya aparecen en el selector de revisión, pero sus precargas y evolución dinámica siguen pendientes del motor. Hoy seleccionarlas no modifica automáticamente cantidades. PRODUCTO NUEVO sí bloquea la validación como caso sin historia. La elegibilidad no se sortea rellenando tres casillas. Una tienda nueva se ensaya como caso sin cobertura, sin inventar un Location.id. Para historia menor de tres meses completos se muestra **PREDICCIÓN NO DISPONIBLE: HISTORIAL INSUFICIENTE**. Si falta el cierre o un mes consecutivo, se muestra **DATOS INCOMPLETOS**. Cero conocido es válido, mes desconocido no equivale a cero.

El motor puede conservar demanda_latente, factor_rotación, factor_tienda, tendencia interna, ruido y nombre o clase del escenario como **metadatos internos**. No entran en X ni en las funciones del modelo. En STOCKOUT se podrá revelar después del pronóstico un panel explicativo: demanda simulada 15, disponibilidad 6 y venta observada 6. La demanda latente no es una medida de demanda comercial conocida. El modelo recibe ventas observadas previas. Para el mes objetivo, ni demanda interna, disponibilidad ni venta observada son features. Si la venta observada manual supera la disponibilidad declarada, se solicitará corregir el resultado o el supuesto de disponibilidad, sin recortarlo silenciosamente.

El mes objetivo estará abierto hasta cerrar su resultado. **GENERAR SIGUIENTE MES** generará el resultado observado del mes objetivo abierto, no saltará un mes sin evaluarlo. Se usará una secuencia aleatoria de sesión con seed 42, escenario y parámetros registrados. El resultado se conservará para que un rerun no lo cambie. La alternativa manual será ingresar VENTA OBSERVADA DEL MES. Ambas formas pasan por el mismo validador. No se permite ver el resultado y después sustituir la predicción oficial de ese mismo mes. Si se desea explorar otra hipótesis después de revelarlo, se abrirá una rama nueva identificada, sin sobrescribir el registro anterior.

**AVANZAR MES** validará el resultado y cerrará una sola vez el mes abierto. Guardará la predicción emitida antes de conocerlo, el baseline y la venta observada. Después avanzará un mes calendario y actualizará lags: de 8, 10, 12 con observado 17 se pasa a 10, 12, 17. Recalculará seno y coseno y dejará pendiente la predicción siguiente. Si hubo abstención, podrá cerrarse con resultado válido, dejando predicción y error vacíos y contabilizando la falta de cobertura. Sin resultado o con mes incompleto no se cierra. Repetir el clic no duplica el mes ni consume otra muestra aleatoria.

La tabla de sesión conservará producto, tienda, mes, predicho, observado, error absoluto, baseline, modelo, versión, origen, estado y revisión de entradas. El gráfico tendrá meses en X y unidades en Y, con observados y predicciones diferenciados. Los valores futuros no se mostrarán como observados. Error absoluto será abs(predicho-observado). MAE será su media y RMSE la raíz de la media de errores cuadrados, sin redondear predicciones antes de medir. La comparación con baseline usará los mismos meses cerrados con ambas salidas. Se mostrará el número de casos y las métricas separadas por versión. No se mezclarán artificialmente V1 y V2 como si fueran un único modelo.

La cobertura será meses cerrados con predicción válida divididos entre todos los meses cerrados solicitados para ese par y versión, incluyendo abstenciones en el denominador. Se mostrarán también intentos sin resultado y motivos, sin contarlos como errores cero. Si no hay casos comparables, las métricas indicarán NO DISPONIBLE. Los indicadores son de la sesión o rama seleccionada, no métricas globales del panel de 168 series.

El monitoreo mostrará **NORMAL**, **REVISIÓN RECOMENDADA** o **EVIDENCIA INSUFICIENTE**. NORMAL solo significa que no se activa el criterio demostrativo. Se propone, exclusivamente para la demo, comparar dos ventanas consecutivas no superpuestas de tres meses cerrados por versión. Con seis meses comparables se recomendará revisión si el MAE de la segunda ventana supera al de la primera y al menos dos de sus tres errores absolutos superan el MAE anterior. Otra señal será que el baseline tenga menor MAE que ACTIVE en ambas ventanas. Los tamaños, cortes y resultados se mostrarán. Son parámetros demostrativos revisables antes del experimento, no umbrales comerciales ni una prueba estadística de drift. Un error aislado no dispara la recomendación. Mala calidad se muestra primero como problema de datos, sin recomendar aprender de ella. Haber acumulado suficientes meses nuevos habilita evaluar un candidato, no garantiza su necesidad o mejora.

La historia, borrador de entradas, reloj, generador aleatorio, predicciones, candidato y referencia ACTIVE serán independientes por sesión y por par producto-tienda. Cambiar el selector no trasladará las ventas de otro par. Cambiar de escenario sobre una historia ya cerrada abrirá una rama nueva o pedirá un reset explícito. **RESTABLECER SIMULACIÓN** devolverá escenario, seed, reloj, historia inicial y referencia V1 local, limpiando el ensayo de esa sesión, sin borrar archivos históricos. Una misma secuencia de acciones y ediciones deberá reproducir los mismos resultados. Las exportaciones opcionales se separarán por sesión, sin rutas de escritura sobre escenarios_v1_1.

Se rechazarán cantidades negativas, decimales en unidades, booleanos, NaN, Infinity, IDs inválidos y meses mal formados. El límite int64 del dataset no garantiza que cualquier modelo convierta esa magnitud con seguridad. El adaptador comprobará también rango exacto de la interfaz y valores finitos representables por el pipeline elegido. Los límites técnicos se registrarán con su justificación, sin máximos comerciales arbitrarios. Se validará la salida y se mantendrá la política de negativos de la sección 8. Estas reglas y el rechazo de doble ejecución se aplicarán en el motor, no solo en los widgets.

El [estado de sesión](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state) alojará los datos editables. No se utilizará una caché global mutable para ACTIVE o para historia. La [documentación de caché](https://docs.streamlit.io/develop/concepts/architecture/caching) distingue recursos compartidos y estado de sesión. Si se comparte la carga de un artefacto, será de solo lectura y con clave de versión o hash. Cada promoción cambiará la referencia de sesión y la clave de carga correspondiente. El entrenamiento no se ejecutará por el rerun de la interfaz y no mutará un modelo compartido.

```text
USUARIO → SIMULADOR INTERACTIVO → EDITOR DE ESCENARIO
  → VALIDADOR → FEATURE BUILDER → MODELO ACTIVE → PREDICCIÓN
  → RESULTADO OBSERVADO SIMULADO → CIERRE Y AVANCE → MONITOREO
  → ¿EVALUAR REENTRENAMIENTO? → NUEVO CANDIDATE
  → COMPARACIÓN → ACTIVACIÓN LOCAL O REJECTED
  → ACTIVE LOCAL → INFERENCIA SIGUIENTE

VOLVER A VERSIÓN ANTERIOR → VERIFICAR COMPATIBILIDAD → ACTIVE LOCAL
```

| Bloque | Función |
|---|---|
| Datos | Mantener 1.1 inmutable y copias de sesión, origen, versión y corte, sin mezclar simulación con historia comercial |
| Editor y motor | Precargar escenarios, aceptar edición, generar resultados y mover el reloj de cada sesión |
| Validación | Revisar calidad, claves, meses, tipos, cantidades y procedencia antes de aprender |
| Feature engineering | Preparar las cinco entradas del mismo producto y tienda utilizando solo historia disponible |
| Training | Ajustar modelos y transformaciones con el entrenamiento de cada corte |
| Validation | Comparar configuraciones sin utilizar test para decidir |
| Registro simple | Relacionar artefacto, estado, contrato, datos y resultados de cada versión |
| Inferencia | Aplicar una versión elegida a un caso con historia suficiente |
| Monitoreo | Asociar predicciones emitidas con resultados posteriormente cerrados, comparar baseline y revisar error y cobertura |
| Reentrenamiento | Crear un candidato con información válida suficiente, sin sobrescribir al activo |
| Comparación y activación | Aprobar o rechazar según el protocolo, conservando la versión anterior |

El test final es posterior a congelar la selección, no un bloque de optimización. H4 requiere interfaz local editable, monitoreo local, entrenamiento de candidato, comparación, promoción y rollback locales demostrables. API administrativa, jobs, permisos productivos, Neon, model registry persistente integrado y alertas automáticas del negocio pertenecen a H5. El diagrama define lo que se desarrollará, no funciones existentes hoy.

**Primera entrega de Ross, semana 1:** streamlit_app.py contiene los controles, estado de sesión y vistas. simulator_inputs.py carga la referencia local con comprobación de hashes y valida entradas, IDs, calendario, completitud y rango técnico. No importa el generador ni escribe archivos de datos. Cada producto, tienda y mes conserva un borrador independiente. Una edición invalida su confirmación previa. El gráfico compara referencia y edición, no simula un pronóstico. El selector temporal llega hasta octubre de 2026, primer mes posterior al panel, con tres meses conocidos. Extender el reloj dependerá del motor.

Para abrir la interfaz desde la raíz del proyecto en PowerShell:

```powershell
python -m venv ml/demand/.venv
.\ml\demand\.venv\Scripts\python.exe -m pip install -r ml/demand/requirements-ui.lock.txt
.\ml\demand\.venv\Scripts\python.exe -m streamlit run ml/demand/streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

La creación e instalación se realizan una vez. Después basta el último comando y abrir http://127.0.0.1:8501. El entorno está ignorado por la configuración existente del repositorio. No se reutiliza el entorno de visión. La lectura de meses históricos sirve para revisar entradas, no es una nueva evaluación de test ni muestra el target del mes seleccionado.

La revisión del 4 de noviembre aprobó 16 pruebas de contrato e interacción con AppTest. Incluyen orden de features, cantidades inválidas, IDs reservados, meses, abstención, edición, confirmación, restauración de borradores, reset y aislamiento entre sesiones. Los hashes de los datos y el generador se comprobaron antes y después de las interacciones. Se revisaron visualmente pantalla y gráfico en navegador local. No se declara todavía revisada una interfaz móvil ni integrado el motor. El aviso ScriptRunContext del hilo principal durante AppTest es propio de esa ejecución de pruebas, sin fallos en la suite.

La ampliación posterior de Ross mantiene esa primera entrega y añade tres módulos. ui_runtime.py conecta el proveedor de Erika y conserva emisiones y cierres. ui_analysis.py calcula métricas, coberturas, errores agrupados y criterios de revisión. ui_panels.py presenta predicción, observado, monitoreo y comparación. La interfaz habilita PREDECIR únicamente con un ACTIVE válido, cinco features compatibles y un mes posterior al entrenamiento. Nunca llama fit. Un CANDIDATE no puede atender como ACTIVE.

Después de emitir, se puede registrar manualmente el observado si el mes objetivo está cerrado. La emisión conserva modelo, versión, huella, entradas y fecha UTC explícita. Editar antes del cierre invalida la emisión pendiente. Cerrar bloquea su edición y los reintentos no duplican el mes. También se permite registrar una abstención para medir falta de cobertura. No equivale a generar o avanzar el reloj de Erika. Los observados y predicciones permanecen en la sesión, sin cambiar paneles 1.1 o datos comerciales.

El monitoreo permite elegir modelo y huella, luego una serie producto-tienda. Presenta histórico, predicción, baseline del último mes, error absoluto, MAE, RMSE, R² y cobertura. Los errores se desglosan por tienda, producto, mes y rotación cuando el metadato existe. No se mezclan versiones para aparentar mejora. Las dos ventanas de tres meses y sus errores se muestran junto al estado demostrativo. Un mes aislado, una serie con huecos o una ventana sin cobertura no certifican drift ni disparan entrenamiento.

Un fallo de inferencia se registra como abstención de su versión, sin valor numérico inventado. Si se cierra con observado, afecta a la cobertura. El monitoreo muestra PROBLEMA TÉCNICO antes de recomendar reentrenamiento. Los problemas de completitud muestran PROBLEMA DE DATOS. Se mantienen separados los errores de operación, la falta de evidencia y una posible variación persistente del comportamiento.

La comparación recibe un reporte local validado de Erika o un JSON importado, siempre de solo lectura. Recalcula las métricas desde observados y predicciones. Cada modelo informa cobertura, pero la comparación de errores usa únicamente filas comunes. Si no hay casos comunes, no se declara mejora. ACTIVE y CANDIDATE se distinguen por su papel, sin promover versiones desde esta vista. La decisión y motivo del proveedor se muestran separados del resultado numérico. Importar un archivo no certifica su procedencia o la correcta ejecución experimental.

| Responsabilidad de Ross | Estado de código | Validación conjunta pendiente |
|---|---|---|
| Semana 1. Interfaz, controles, edición, gráficos y validaciones | Implementada, con estado aislado y referencia inmutable | Conectar precargas, generación y reloj de Erika |
| Semana 2. Integración de predicción, métricas, errores y visualización | Implementada contra contrato y probada con dobles | Ejecutar contra baseline, LinearRegression, RandomForest y V1 reales de Erika |
| Semana 3. Monitoreo, drift y comparación visual | Implementada con criterios demostrativos y reportes validados | Recibir inferencia, versiones, candidato y resultados de comparación de Erika |

Las pruebas de interfaz y análisis se ejecutan sin regenerar datasets ni entrenar:

```powershell
.\ml\demand\.venv\Scripts\python.exe -m unittest discover -s ml/demand -p 'test_*ui*.py' -v
```

La primera validación de esta ampliación aprobó **50 pruebas**, incluidas las 16 anteriores. Se comprobaron inferencia contra un doble, bloqueo de CANDIDATE, fechas de entrenamiento, entradas congeladas, cierres únicos, cobertura, errores conocidos, R² indefinido, monitoreo persistente, fallos técnicos y reportes incompatibles. Los archivos guardados de 1.1, el catálogo, generador y schema conservaron sus hashes. Se revisaron visualmente las pestañas y estados sin datos. Las vistas con predicciones y comparaciones se verificaron mediante AppTest con datos exclusivos de prueba. Eso no sustituye la revisión conjunta con modelos reales.

**Segunda revisión de coherencia de Ross, 4 de noviembre.** Se corrigieron cuatro problemas que las primeras pruebas no cubrían. Ingresar el observado congela de inmediato las entradas y la emisión, incluso antes de cerrar, para impedir predecir otra vez conociendo el resultado. El valor congelado se conserva al cambiar de tienda y volver. Un archivo de comparación se procesa solo cuando cambia, sin sustituir silenciosamente un reporte elegido del runtime en cada actualización de pantalla. Los enteros enormes se rechazan antes de convertirlos a float, evitando desbordamientos. El monitoreo contrasta lags contra observados ya cerrados y bloquea una recomendación de drift si la historia es incoherente.

Esta revisión amplía la suite a **59 pruebas**. Incluye cierre después de revelar el observado, protección del registro, permanencia de valores al cambiar de serie, cambio y retirada de archivos, prioridad del reporte seleccionado y cantidades extremas. No elimina pruebas anteriores ni utiliza un modelo de ejemplo en la aplicación. Comparar casos editados de forma independiente sigue siendo posible, pero no se presentan como una trayectoria temporal coherente para justificar reentrenamiento.

**Qué sigue para Ross.** No falta agregar otro algoritmo o duplicar el motor. El cierre requiere trabajo con los componentes reales de Erika:

1. Confirmar con Erika el contrato del runtime y conectar sus artefactos, preprocesamiento, corte de entrenamiento y huellas reales.
2. Verificar predicción, métricas y gráficos contra baseline, LinearRegression y RandomForest reales. Revisar la evidencia de selección V1, sin seleccionar por resultados de test.
3. Cuando exista el motor, recorrer al menos seis meses coherentes, stockout, producto nuevo, mes incompleto y cambio persistente. Comprobar que generación, avance, observado y lags coincidan. Revisar la comparación y lo que muestra la interfaz después de promoción o rollback de Erika.
4. Completar revisión visual con esos resultados en computadora y pantalla estrecha, conservar evidencia, actualizar tracking y prompts y preparar la demostración conjunta.

Los controles de generación y avance siguen bloqueados hasta integrar el motor. La primera revisión visual y los dobles validan partes de Ross, no declaran completas estas cuatro comprobaciones. El siguiente paso es la integración conjunta, sin volver a entrenar o rehacer el dataset desde la interfaz.

## 14. Plan de trabajo H4 por fases y tres semanas

| Fase | Objetivo y actividades | Resultado esperado | Evidencia y estado actual |
|---|---|---|---|
| 1. Comprensión | Precisar problema, catálogo, tiendas, cantidades, fechas, calidad y target | Contrato de datos definido | Esta guía y auditorías. Definición existente |
| 2. Dataset | Generar y validar simulación identificada, catálogo, seed, distribución y hashes | Base reproducible | Versión 1.1 ya existe. No regenerar sin cambio justificado y autorizado |
| 3. Preparación y simulador | Revisar lags, target, split y transformaciones. Construir editor local, escenarios y avance temporal | Entradas sin fuga temporal y simulación editable | CSV y asignación temporal existentes. Primera interfaz y validación de Ross disponibles. Motor, integración y preprocesamiento pendientes |
| 4. Comparación | Evaluar baseline, entrenar LinearRegression y RandomForest, registrar configuraciones y métricas | Experimentos comparables | Pendiente. MLP es opcional |
| 5. Selección y demo H4 | Seleccionar con validation, evaluar test, guardar V1, integrar inferencia, monitoreo, candidato y retorno locales | Simulador interactivo y experimento reproducible | Pendiente, sin métricas ni ganador. La interfaz inicial no sustituye esas evidencias |
| 6. Integración H5 | Completar backend, frontend, ranking, reposición, monitoreo y seguimiento real | Integración comercial evaluada | Futuro, fuera del mínimo H4 |

La implementación seguirá este orden: verificar dataset y hashes, validar contrato, separar motor dinámico del generador conservado, construir interfaz editable y avance temporal, revisar features y split, preparar transformaciones, conectar baseline, entrenar LinearRegression y RandomForest, comparar validation, congelar V1, evaluar test, guardar artefacto e integrar inferencia estable. Después se completarán monitoreo, candidato, comparación, promoción y rollback locales. Una nueva versión de datos o una sesión no sobrescriben 1.1. Experimentos y prompts se registran desde el inicio. Esta actualización establece el trabajo pendiente, no ejecuta esas fases.

Los documentos del equipo confirman los nombres Erika y Ross. Erika liderará motor de simulación, preparación ML, entrenamiento, modelos, inferencia y artefactos. Ross liderará experiencia e interfaz local, validación funcional, escenarios de negocio, análisis de errores, visualización y documentación. Coordinarán el contrato entre interfaz y motor. Ambos revisarán selección, test final, reentrenamiento, promoción, rollback, demo y defensa. La interfaz Streamlit pertenece al experimento local, sin modificar el frontend o móvil productivos a cargo de Erika.

El plan dura **tres semanas de cinco días de trabajo**, quince días relativos al inicio autorizado. No se reutiliza como fecha vigente el antiguo cronograma del 28 de octubre al 17 de noviembre. Mientras Erika desarrolla el motor y los modelos, Ross implementa la interfaz local, validación, monitoreo y evidencia sobre el contrato compartido. Se acuerda quién edita cada archivo compartido. Se priorizan funcionalidades obligatorias sobre MLP, diseño avanzado o integración web. Si falta tiempo, se registra el pendiente, sin declarar completa una demo estática.

| Semana | Día | Erika | Ross | Entregable y revisión conjunta |
|---|---|---|---|---|
| 1 | 1–2 | Revisar generador 1.1 y hashes. Definir motor separado, contrato ML y generación dinámica | Definir experiencia, controles editables, escenarios, validaciones y recorrido de usuario | Ambos cierran entradas, alcance de Streamlit y contrato de estado sin alterar el generador histórico |
| 1 | 3–4 | Implementar motor, escenarios, lectura, reloj, shift de lags y generador aleatorio de sesión | Implementar interfaz local, selectores, formularios, edición y gráficos iniciales | Editor y motor independientes, calendario correcto y sesiones aisladas |
| 1 | 5 | Integrar motor y comprobar reproducibilidad | Integrar interfaz y ejecutar validaciones y casos ambiguos | Ambos prueban edición, avance, escenarios y reset. Simulador funcional de datos, sin fingir un modelo ya entrenado. Dataset, validadores, tests y documentación |
| 2 | 6 | Implementar baseline último mes y evaluar baseline estacional solo si hay cobertura | Conectar flujo PREDECIR, origen, versión y visualización de métricas | Baseline interactivo etiquetado. Referencia estacional opcional con soporte informado |
| 2 | 7–8 | Entrenar LinearRegression, preparar pipeline y registrar experimentos | Integrar inferencia con el simulador, mostrar features, resultado, versión y errores | Predicción tras editar, sin reentrenamiento implícito ni consulta de test |
| 2 | 9–10 | Entrenar RandomForest con configuraciones limitadas y validation | Preparar comparación visual y errores por tienda, rotación y mes | Ambos eligen y congelan configuración V1 con validation. Simulador responde, métricas, gráficos y tracking |
| 3 | 11 | Congelar parámetros, transformaciones y artefacto V1 | Verificar protocolo y separación de test | Ambos evalúan test final una vez y guardan V1 y resultados, incluso si no mejora al baseline |
| 3 | 12 | Integrar inferencia estable y registro local de versiones | Integrar historial, observados, predicciones, cobertura y MAE/RMSE recientes | Simulación editable conectada a ACTIVE y monitoreo por versión |
| 3 | 13 | Implementar ensayo local y creación de CANDIDATE sin sobrescribir ACTIVE | Implementar revisión recomendada y comparación visual ACTIVE/CANDIDATE | Ambos prueban promoción y rechazo sobre ventana nueva comparable, sin reutilizar el test de V1 |
| 3 | 14 | Comprobar rollback compatible, carga y aislamiento de artefactos | Probar drift demostrativo, stockout, producto nuevo, mes incompleto, errores y sesiones | Ambos verifican retorno, abstenciones, reset y trazabilidad, sin reajustar por test |
| 3 | 15 | Presentar motor, modelos, configuración e inferencia | Presentar interfaz, escenarios, métricas, gráficos y trazabilidad | Ambos cierran demo interactiva, documentación, prompts, experiments.csv y defensa |

La semana 1 entrega simulador editable, ocho escenarios, avance temporal, dataset reproducible sin modificaciones, validadores, tests y documentación. La semana 2 entrega baseline, LinearRegression, RandomForest, configuración V1, predicción interactiva, métricas, gráficos y tracking. La semana 3 entrega V1 evaluada, monitoreo, drift demostrativo, otro candidato, comparación, promoción o rechazo, rollback y demo completa. No se garantiza que V2 mejore. Un rechazo fundamentado también demuestra el ciclo. MLP sigue opcional y no desplaza estas obligaciones.

La carga se reparte entre desarrollo técnico y validación independiente. Ross no queda esperando el primer entrenamiento para definir reportes, validadores o casos de negocio. Erika revisa también la interpretación de errores. Las decisiones importantes y la defensa requieren a ambos, no dos entregas aisladas.

Los siguientes criterios son una lista de cierre pendiente, no un avance ya alcanzado:

- [ ] Dataset validado con estadísticas, distribución y ejemplos identificados como sintéticos.
- [ ] Pipeline de lectura, features y preprocesamiento reproducible.
- [ ] Baseline evaluado.
- [ ] LinearRegression entrenada y registrada.
- [ ] RandomForestRegressor entrenado y registrado.
- [ ] experiments.csv con ejecuciones, parámetros y resultados.
- [ ] Validation temporal y análisis por grupos.
- [ ] Modelo seleccionado con justificación.
- [ ] Test final reservado y evaluado después de congelar decisiones.
- [ ] Artefacto y transformaciones guardados.
- [ ] Simulador interactivo con selectores y edición manual de los tres lags.
- [ ] Ocho escenarios, modo manual y generación automática local reproducible.
- [ ] Predicción interactiva con ACTIVE, sin fit al editar o predecir.
- [ ] Avance temporal con shift correcto y resultado posterior separado de features.
- [ ] Visualización actualizable de histórico, pronóstico, comparación y errores.
- [ ] Monitoreo local, baseline comparable y revisión recomendada identificada como demostrativa.
- [ ] CANDIDATE entrenado en un ensayo separado, comparación y rechazo o promoción locales.
- [ ] Rollback local compatible y trazable, conservando V1 y su evaluación.
- [ ] Sesiones aisladas, abstenciones, reset reproducible y dataset 1.1 inmutable.
- [ ] Riesgos y fallas encontrados documentados.
- [ ] Stack existente y propuesto documentado.
- [ ] Plan y ensayo local de reentrenamiento documentados.
- [ ] Prompts con procedencia.
- [ ] Versiones, hashes y configuraciones conservados.
- [ ] Demo reproducible.
- [ ] Exposición y defensa preparadas por ambos.

El **70 % de H4** requiere ahora simulador interactivo, edición en tiempo real mediante PREDECIR, escenarios, avance temporal, dataset validado, features, split, baseline, LinearRegression, RandomForest, V1 seleccionada y evaluada, predicción interactiva, métricas, gráficos y monitoreo local. Incluye ensayo de reentrenamiento, CANDIDATE, comparación, promoción o rechazo, rollback local, tracking, prompts y documentación. No se mide por líneas, archivos o casillas. Un CSV o script estático ya no acreditan esa entrega. El estado actual todavía no cumple ese conjunto.

La demo comenzará con producto y tienda válidos, historia reciente y mes objetivo. Se editarán lags, se pulsará PREDECIR y se explicará la respuesta de ACTIVE. Después se revelará o ingresará un observado, se avanzará el mes y se mostrarán gráfico y error. Se ensayarán stockout, historial insuficiente y un cambio persistente, seguido de candidato, comparación, promoción o rechazo y retorno compatible. Octubre de 2026 sería el primer mes posterior al último septiembre del panel. Su observado no existe en 1.1, se obtiene solo en la rama de simulación. No se inventa una métrica antes de revelarlo ni se presenta como pronóstico comercial actual.

Para H5 se propone, sin implementarlo, backend/src/modules/predictions/demand/ con inferencia Python y una sección Predictivo en frontend. La entrada conceptual contendría productId, locationId y mes objetivo. La respuesta distinguiría unidades previstas, modelo, versiones, origen y métrica de referencia. El contrato final, permisos y manejo de errores se acordarán en esa etapa. Se contempla historial frente a predicción, stock disponible, ranking y reposición revisada por una persona.

También quedan para H5 la vista administrativa integrada, botón productivo REENTRENAR MODELO, jobs, permisos, Neon, registro persistente integrado, activación y rollback productivos, alertas automáticas y reentrenamiento comercial certificado. H4 sí incluye botones, gestión de versiones, monitoreo, promoción y rollback dentro del simulador local. Esa funcionalidad no declara lista la administración productiva.

La fórmula ilustrativa max(0, ceil(ventas previstas + seguridad - stock disponible)) daría 14 con valores 18, 5 y 9. No es un resultado entrenado ni un requisito H4. minStock no se asume seguridad estadística. Compras en curso, tránsito, reservas, plazos del proveedor, pedido mínimo, presupuesto y disponibilidad física necesitan una política completa. Ni H4 ni una fórmula aislada autorizan compras, movimientos o ajustes automáticos.

## 15. Registro de experimentos, prompts y artefactos

Al comenzar entrenamiento se creará **ml/demand/reports/experiments.csv**, todavía inexistente. Cada fila registrará una ejecución identificada, dataset y hash, seed, features, target, split, modelo, parámetros, métricas, duración, versiones y observaciones. Se conservarán nombre de artefacto, preprocesamiento y política de negativos. Una propuesta de columnas es experiment_id, timestamp, dataset_version, dataset_hash, catalog_hash, generator_version, seed, features, target, train_range, validation_range, test_range, model, parameters, preprocessing, mae_val, rmse_val, r2_val, mae_test, rmse_test, r2_test, training_seconds, tool_versions, artifact_path y notes.

**Contrato de conexión Erika–Ross.** Erika proporcionará ml/demand/demand_runtime.py con create_runtime(), que devuelve una instancia local por sesión. Hoy ese archivo no existe. El adaptador no busca paquetes externos con ese nombre, no carga modelos subidos por el usuario y no modifica código productivo. RECONECTAR RUNTIME permite iniciar el proveedor cuando esté disponible. Su inicialización y métodos deben ser de uso local, sin entrenamiento implícito ni conexión a Neon.

| Método del proveedor | Contrato utilizado por Ross |
|---|---|
| get_active_model() | Devuelve None si no hay ACTIVE, o un diccionario de metadatos válido. role, cuando se incluye, debe ser ACTIVE |
| predict(features) | Recibe un diccionario con las cinco features en el orden oficial. Devuelve exactamente prediction, numérico finito o None, y reason, texto. No recibe target, observado, IDs numéricos como features o escenarios internos |
| get_comparison_report(), opcional | Devuelve un objeto JSON compatible con h4-comparison-1. La interfaz lo consulta con una acción explícita y no ejecuta entrenamiento |

Los metadatos contienen name y version como textos, artifact_hash como SHA256 de 64 caracteres hexadecimales, trained_through como YYYY-MM, origin igual a SIMULACION y feature_names igual a la lista ordenada oficial. La huella identifica el conjunto de modelo, preprocesador y configuración, no solo el nombre de archivo. trained_through debe ser anterior al mes emitido. La interfaz comprueba que ACTIVE no cambie durante la llamada. Una salida negativa se conserva sin recorte para medir su error original. Salidas no finitas o fuera del rango técnico se rechazan. Para abstenciones se conservan los motivos seguros HISTORIAL INSUFICIENTE, DATOS INCOMPLETOS o FUERA DE COBERTURA. Otros textos se muestran como ABSTENCIÓN DEL MODELO, sin revelar mensajes internos.

El reporte de comparación no contiene código ejecutable ni exige instalar un serializador de modelos. El límite técnico de carga es 2 MiB. Se rechazan NaN, Infinity, claves JSON repetidas, filas duplicadas, IDs fuera del catálogo, meses inválidos y comparaciones con meses utilizados por cualquiera de los modelos para aprender.

| Campo de h4-comparison-1 | Contenido |
|---|---|
| schema_version y origin | Textos exactos h4-comparison-1 y SIMULACION |
| purpose | VALIDATION, COMPARACION_LOCAL o TEST_FINAL. TEST_FINAL exige frozen_selection igual a true |
| models | Lista de dos o más metadatos distintos, con huellas únicas y contrato de cinco features. role admite ACTIVE, CANDIDATE, BASELINE o REFERENCE. Por defecto es REFERENCE. Como máximo un ACTIVE y un CANDIDATE |
| rows | Lista de filas con productId y locationId enteros válidos, mes_objetivo YYYY-MM, observed entero no negativo y predictions |
| predictions de cada fila | Diccionario cuyas claves son exactamente las huellas de models. Cada valor es una predicción numérica finita o null como abstención explícita |
| rotation de cada fila, opcional | ALTA, MEDIA, BAJA o SIN DATO, solo para diagnóstico. No se convierte en feature |
| decision y reason | Decisión registrada por Erika: PENDIENTE, APROBADO o RECHAZADO, acompañada de su motivo. Ross no la sustituye con un ganador automático |

La descarga h4-session-1 conserva session_id, emisiones, escenarios como metadatos, observados y versiones de la sesión. generator_seed permanece null porque Ross no implementa un generador. No es experiments.csv ni un nuevo dataset supervisado, tampoco restaura automáticamente una sesión o modifica modelos. La tabla distingue esta evidencia interactiva de métricas de validation y test. Los valores de los dobles en test_ross_ui.py son exclusivos de pruebas y nunca se importan por la aplicación como resultados de H4.

Las métricas de test permanecen vacías durante selección. Se completan en el registro de evaluación final con decisiones congeladas. Se anotarán también resultados por grupos y número de casos. No se crea ahora un CSV con resultados inventados.

El registro simple del ciclo relacionará cada versión con experiment_id, estado, versión activa de referencia, rango comparable, decisión, motivo y responsables. Un rechazo o rollback también conservará evidencia. Ese registro de versiones sigue pendiente de Erika. Ross ya conserva emisiones y cierres en la sesión y permite descargar su JSON. Los parámetros demostrativos de la sección 13 no son umbrales comerciales. No se crearon tablas o archivos productivos de seguimiento.

Para las sesiones se registrarán también session_id, rama, producto, tienda, escenario como metadato, seed y estado aleatorio, mes, revisión de entradas, fecha de emisión, features congeladas, predicción, baseline y versión. El observado se adjunta al cerrar, indicando si fue manual o generado. Se conservarán abstenciones, cambios de ACTIVE y motivos de rechazo o rollback. Los parámetros demostrativos de monitoreo se guardarán con la ejecución. Los experimentos de entrenamiento, el seguimiento interactivo y el test de V1 serán registros diferenciados. No se sobrescribirá una métrica final con datos editados durante la demo.

Se guardarán el modelo y las transformaciones necesarias como un mismo conjunto reproducible, orden de columnas, parámetros, versión de Python, NumPy, pandas y scikit-learn que realmente se utilicen. El manifiesto existente registra Python 3.11.9 para la generación guardada. No fija un entorno propio H4 ni demuestra un entrenamiento ejecutado, aunque ya existan bibliotecas instaladas en el Python general. Los hashes se calculan sobre bytes de los archivos, sin confundir la fecha variable del manifiesto con cambios en cantidades.

[PROMPTS_MODELO_PREDICTIVO_H4.md](PROMPTS_MODELO_PREDICTIVO_H4.md) es un **log cronológico**, no otra propuesta. Registra solicitudes y ajustes de auditoría, dataset, entrenamiento, pruebas, integración y documentación cuando ocurren. Se distingue texto literal, extracto y resumen. Lo no recuperado se marca NO RECUPERADO. No se inventan prompts de entrenamiento ni fechas anteriores. Su existencia separada permite conservar el proceso sin duplicar esta guía.

## 16. Tabla de decisiones

| Decisión | Elección | Justificación |
|---|---|---|
| Problema | Estimar ventas observadas del próximo mes | Pregunta útil y medible, sin prometer demanda perdida |
| Dataset | Tabular, temporal, sintético inicial y supervisado | Separa estructura, orden, origen y aprendizaje |
| Tipo de aprendizaje | Supervisado | Hay entradas y resultado conocido al entrenar |
| Tipo de predicción | Regresión temporal de un paso | Resultado numérico con horizonte de un mes |
| Unidad de análisis | Producto + tienda + mes | Respeta diferencias entre series |
| Target | target_ventas_mes, unidades brutas | No mezcla devoluciones con ventas negativas |
| Periodo | Octubre 2024 a septiembre 2026, seed 42 | Dos ciclos simulados reproducibles |
| Split | 15/3/3 meses objetivo | Aproxima 70/15/15 sin romper meses |
| Normalización | Solo se aprende con TRAIN, según modelo | Evita futuro en las transformaciones |
| Baseline | Último mes observado | Referencia mínima de utilidad |
| Modelo lineal | LinearRegression | Simple, rápido e interpretable |
| Modelo de árboles | RandomForestRegressor, candidato | No lineal y manejable, requiere evidencia para ganar |
| Red neuronal | MLP opcional, 64/32 ilustrativo | Comparación conceptual, mayor costo de ajuste |
| Métrica principal | MAE, junto a RMSE y R² | Error en unidades con controles complementarios |
| Alcance H4 | Simulador interactivo local y experimento reproducible | Edición, inferencia, monitoreo y ciclo local demostrables |
| Alcance H5 | Integración comercial y reposición | Requiere datos, políticas y seguimiento adicionales |
| Reentrenamiento | Crear y comparar candidato, nunca sobrescribir al activo directamente | La novedad de una versión no demuestra mejora |
| Monitoreo | Calidad, error sostenido y cobertura por grupos | Distingue cambios del negocio de errores de datos |
| Versionado y retorno | Estados explícitos y conservación del conjunto anterior compatible | Permite rechazar o revertir una versión problemática |
| Interfaz del simulador | Streamlit local, PROPUESTO | Aísla la demo Python y evita añadir API o cambios al React productivo |
| Editar y predecir | Edición de copia de sesión y botón PREDECIR, sin entrenamiento | Respuesta sobre entradas confirmadas, con origen y versión visibles |
| Cierre temporal | Observado posterior, cierre único y shift de lags | Impide fuga del resultado al pronóstico del mismo mes |
| Revisión local | Dos ventanas de tres meses como configuración demostrativa | Expone error sostenido, sin definir una política comercial de reentrenamiento |

## 17. Evidencia para presentación y cierre H4

**Lo que debemos presentar antes de implementar** es el diseño que ya puede defenderse. Tener el dataset existente permite mostrarlo como avance previo, sin afirmar que hubo entrenamiento.

| N.º | Evidencia de diseño |
|---:|---|
| 1 | Problemática de ventas mensuales |
| 2 | Objetivo predictivo a un mes |
| 3 | Unidad producto + tienda + mes |
| 4 | Dataset elegido y origen sintético |
| 5 | Estructura exacta de nueve columnas |
| 6 | Cinco features iniciales y disponibilidad |
| 7 | Target bruto y exclusiones |
| 8 | Aprendizaje supervisado |
| 9 | Split temporal con meses y filas |
| 10 | Normalización ajustada solo con training |
| 11 | Algoritmos a comparar |
| 12 | Random Forest como candidato principal |
| 13 | MAE, RMSE y R², sin métricas inventadas |
| 14 | Seis fases con evidencia esperada |
| 15 | Riesgos y límites de cobertura |
| 16 | Justificación de decisiones de la tabla anterior |
| 17 | Diseño del simulador, tecnología, controles y separación EDITAR/PREDECIR/REENTRENAR |
| 18 | Plan de avance, sesiones, monitoreo, promoción y rollback locales con pruebas previstas |

**Lo que debemos mostrar al finalizar H4** son resultados verificables. Ninguna casilla se considera cumplida solo porque esta guía la menciona.

| N.º | Evidencia funcional al cierre |
|---:|---|
| 1 | Dataset generado, versión y hash |
| 2 | Estadísticas descriptivas |
| 3 | Distribución del target |
| 4 | Ejemplos de filas identificadas como sintéticas |
| 5 | Fechas, filas y comprobación del split |
| 6 | Resultado del baseline |
| 7 | LinearRegression entrenada |
| 8 | RandomForest entrenado |
| 9 | Configuraciones probadas |
| 10 | Métricas de validation |
| 11 | Modelo elegido y justificación |
| 12 | Evaluación final en test |
| 13 | Comparación gráfica entre modelos |
| 14 | Errores encontrados y tratamiento |
| 15 | Primera predicción funcional |
| 16 | Primera visualización con historia y pronóstico |
| 17 | Modelo y preprocesamiento guardados |
| 18 | experiments.csv |
| 19 | Prompts utilizados, con procedencia |
| 20 | Configuraciones, seed y versiones |
| 21 | Limitaciones técnicas y comerciales |
| 22 | Evidencia del conjunto funcional aproximado del 70 % |
| 23 | Stack comprobado y dependencias propuestas claramente separados |
| 24 | Reentrenamiento local con CANDIDATE, comparación, promoción o rechazo y rollback demostrados |
| 25 | Plan de monitoreo, versionado y rollback con límites H4/H5 |
| 26 | Participación de Erika y Ross en demo y defensa |
| 27 | Simulador editable con ocho escenarios, selectores, lags y calendario derivado |
| 28 | Predicción interactiva después de editar, sin reentrenamiento implícito |
| 29 | Generación automática y observado manual, cierre y avance mensual correctos |
| 30 | Historial, gráfico actualizado, error reciente, cobertura y baseline comparable |
| 31 | Revisión recomendada demostrativa, casos ambiguos, sesiones aisladas y reset reproducible |
| 32 | Evidencia de pruebas del simulador y conservación de los hashes de 1.1 |

Las pruebas siguientes definen el cierre conjunto, no una suite aprobada en su totalidad. Ross conserva las 16 pruebas iniciales y añade test_ross_ui.py para contrato de inferencia, emisiones, observados, métricas, drift y reportes. Se prueban con dobles exclusivos, sin entrenar ni inventar resultados experimentales. La ejecución contra modelos reales, el reloj, la generación dinámica y la gestión de versiones de Erika siguen pendientes. El conjunto anterior del dataset debe mantenerse sin modificar sus archivos guardados.

| Grupo de prueba | Resultado que deberá comprobarse |
|---|---|
| Edición y contrato | Cambiar cada lag, aplicar el formulario y recalcular exactamente cinco features. Seno y coseno corresponden al mes. La inferencia utiliza lo ingresado, no una precarga anterior |
| Predicción tras editar | La salida se recalcula con ACTIVE compatible, sin fit. Se registra el nuevo corte de entradas. No se exige que siempre cambie el número, porque un árbol puede dar la misma salida |
| Selectores y escenario | Historia del par correcto, ocho precargas editables y metadatos excluidos de X. Cambiar escenario no borra silenciosamente una edición confirmada |
| Validación numérica | Negativos, booleanos, decimales de unidades, NaN, Infinity, overflow, IDs y meses inválidos se rechazan también en el motor |
| Tiempo y doble clic | Avance de diciembre a enero, calendario correcto y shift 8/10/12 + 17 → 10/12/17. Reintentar cerrar no duplica historia ni genera otra muestra |
| Resultado posterior | Cambiar el observado no afecta la predicción ya emitida del mismo mes. Solo entra como lag tras cierre. Editar después de revelarlo crea otra rama, sin sustituir el pronóstico evaluado |
| Modos manual y automático | Mismo contrato de cantidades y cierre. La generación conserva el resultado entre reruns y no consume azar por dibujar la pantalla |
| Ambiguos | Producto nuevo, tienda sin cobertura o menos de tres meses bloquean con HISTORIAL INSUFICIENTE. Mes faltante o incompleto bloquea con DATOS INCOMPLETOS, sin convertirlo en cero |
| Stockout | Se diferencian demanda interna, disponibilidad y venta observada. La latente no llega al modelo y no se permite una venta superior a la disponibilidad declarada sin corregir el supuesto |
| Error y cobertura | MAE/RMSE conocidos con ejemplos controlados, baseline sobre los mismos meses y denominadores con abstenciones. Sin métricas ficticias cuando faltan casos |
| Revisión recomendada | Un solo error no dispara revisión. Las dos ventanas cerradas y reglas demostrativas producen el estado esperado. Datos inválidos no motivan entrenamiento |
| Candidato | Cortes futuros comparables, sin reutilizar test V1. Entrenar o fallar no sobrescribe ACTIVE. Se puede rechazar aunque sea una versión más nueva |
| Promoción local | Solo candidato aprobado y compatible. Cambio completo de referencia, conservando artefactos, métricas y decisiones de V1 |
| Rollback | Restauración compatible de modelo y preprocesador con motivo. Rechazo seguro si falta una versión válida, sin cambiar resultados históricos |
| Sesiones y reset | Dos sesiones no comparten historia, azar, candidatos o ACTIVE mutable. Reset restaura seed y escenario base, de forma reproducible y solo en la sesión actual |
| Inmutabilidad y visual | Hashes de 1.1 iguales antes y después. Sin llamadas a base. Interfaz muestra origen SIMULACIÓN, versión, unidades, estados pendientes, errores, gráfico y acciones separadas |

## 18. Fuentes y consolidación documental

Las auditorías de [datos](historico/AUDITORIA_MODELO_PREDICTIVO_H4.md), [Fase 1](historico/H4_FASE1_ESTRUCTURA_DATASET_Y_RIESGOS.md), [generación inicial y escenarios](historico/H4_FALLAS_Y_ESCENARIOS_DATASET.md) y [cobertura versión 1.0](historico/H4_AUDITORIA_COBERTURA_Y_PREPARACION_ENTRENAMIENTO.md) se conservan como fotografías fechadas. Sus frases «no existe dataset», «siete pruebas» o «no existe anulación» describen su momento. El estado vigente es el de esta guía contrastado con los archivos actuales. La referencia del catálogo guarda la huella del documento original de Fase 1. Para mantenerla sin cambiar el dataset se conserva su copia exacta en [originales](historico/originales/H4_FASE1_ESTRUCTURA_DATASET_Y_RIESGOS.md.txt). La copia Markdown tiene enlaces adaptados a las carpetas nuevas. El [mapa de traslados](historico/traslados_documentales.json) relaciona las rutas antiguas con las actuales.

También se conservan [saneamiento](../H3/cierre_saneamiento/PLAN_SANEAMIENTO_REPUESTOPRO_PRE_H4.md), [segunda revisión integral](../H3/cierre_saneamiento/SEGUNDA_REVISION_INTEGRAL_TIENDA_REAL.md), [correcciones integrales](../H3/cierre_saneamiento/CORRECCIONES_INTEGRALES_TIENDA_REAL.md) y [reglas comerciales](../H3/cierre_saneamiento/REGLAS_COMERCIALES_FACTURAS_ANULACIONES_Y_PAGOS.md). No se fusionan por completo porque documentan hallazgos y pruebas reales de la plataforma, con una función distinta de esta propuesta. Los documentos de YOLO, OCR y datasets de imágenes pertenecen a visión, no al dataset mensual de demanda.

| Archivo revisado | Contenido vigente incorporado | Disposición y motivo |
|---|---|---|
| H4_MODELO_PREDICTIVO_PROPUESTA_DETALLADA.md | Problema, datos, modelos, evaluación, registro y H4/H5 | Propuesta anterior archivada. Su redirección queda archivada junto a las referencias históricas |
| H4_PLAN_FASES_DATASET_PREDICCION_ALGORITMO.md | Fases, decisiones y exposición | Síntesis anterior archivada. Su redirección también queda archivada |
| H4_PLAN_DE_TRABAJO.md | Responsables preliminares, controles y evidencia | Retirado de la ruta activa y archivado. Promedio, reposición H4 y cronograma sin confirmar no son instrucciones vigentes |
| H4_FASE1_ESTRUCTURA_DATASET_Y_RIESGOS.md | Diccionario, disponibilidad, catálogo, escenarios y validaciones | Conservado íntegro como evidencia fechada y fuente con hash del catálogo |
| H4_FALLAS_Y_ESCENARIOS_DATASET.md | Normales, adversos, inválidos, grises y cantidades | Conservado íntegro como registro de la primera generación |
| H4_AUDITORIA_COBERTURA_Y_PREPARACION_ENTRENAMIENTO.md | Límites, probes y cobertura insuficiente | Conservado íntegro. Sus fallas del validador se distinguen de las correcciones de 1.1 |
| AUDITORIA_MODELO_PREDICTIVO_H4.md | Historia, procedencia y relaciones del dominio | Conservado íntegro como auditoría |
| PLAN_SANEAMIENTO_REPUESTOPRO_PRE_H4.md | Reglas y pendientes del proyecto | Conservado íntegro como trazabilidad del saneamiento |
| PROMPTS_MODELO_PREDICTIVO_H4.md | Procedencia de solicitudes | Log separado, sin propuesta paralela |
| ml/demand/README.md y README.md | Entrada de navegación | Enlazan esta guía. El README técnico no repite otra definición de H4 |

Las tres propuestas anteriores están en [historico/h4](historico/propuestas). No son guías activas. La documentación de visión y saneamiento previo está separada en ../H3 y la documentación general del equipo en ../GENERAL. El contenido útil está integrado en las secciones temáticas y en el resumen final. Se conservaron fechas, responsables y antecedentes en archivo. Las dos redirecciones se conservan en historico/redirecciones. El original exacto de Fase 1 permite verificar la huella registrada en el catálogo, aunque source_document mantenga la ruta de la consulta histórica. No se mantienen dos propuestas activas ni se elimina evidencia del catálogo. El inventario de revisión, las huellas y las comprobaciones están en [la validación documental](historico/evidencias/2026-11-03/consolidacion-h4-validacion.json).

Se corrigieron el promedio reintroducido, las reposiciones e integración completa en H4, las cifras condicionales de 62 productos, el dataset descrito como inexistente, los IDs tratados ambiguamente como features, los hallazgos de 1.0 presentados como actuales y la falta de anulación atribuida al schema actual. También se separó validación académica de uso comercial. No se cambiaron datasets para corregir el relato.

La indicación posterior del simulador reemplaza el mínimo de script estático de la ampliación anterior. Ahora H4 requiere interfaz local editable, avance temporal, monitoreo, candidato, promoción y rollback locales. La exclusión anterior de gestión productiva sigue vigente para H5. Se mantiene el contrato de cinco features, dataset 1.1, cantidades, split y condición de Random Forest como candidato. La entrega del 4 de noviembre implementa únicamente la interfaz inicial de Ross y sus validaciones. No modifica evidencia histórica ni completa el motor o la predicción.

## 19. Resumen para defensa

| Pregunta | Respuesta para estudiar |
|---|---|
| ¿Cuál es la base del modelo? | Regresión supervisada temporal por producto, tienda y mes, con tres lags y dos variables de calendario |
| ¿Qué datos usa? | Dataset sintético 1.1, 56 productos, tres tiendas y 24 meses. Tiene 3.528 ejemplos supervisados con split 15/3/3 |
| ¿Qué predice? | Unidades brutas observadas el próximo mes. No demanda perdida. Comparamos baseline, LinearRegression y RandomForest, que sigue como candidato |
| ¿Qué problemas consideramos? | Datos incompletos, nuevos productos o tiendas, falta de stock, cambios comerciales, duplicados, mezcla de origen, sobreajuste y errores locales |
| ¿Qué corregimos antes de entrenar? | Duplicados, cantidades o IDs inválidos, meses incompletos, mezclas demo y errores operativos. Reentrenar no los elimina |
| ¿Qué puede justificar reentrenamiento? | Datos nuevos suficientes, cambios persistentes, aumento sostenido del error o menor cobertura, después de validar calidad |
| ¿Cómo lo detectamos? | Medimos error con meses cerrados, baseline y cobertura. En la demo comparamos dos ventanas de tres meses, como criterio demostrativo visible, no política comercial |
| ¿Cómo se reentrena? | Validamos datos nuevos, fijamos versión y cortes, preparamos features y entrenamos un candidato separado |
| ¿Cómo evitamos activar uno peor? | Champion y challenger se comparan en la misma ventana nueva válida. ACTIVAR CANDIDATO exige evidencia. Conservamos una versión compatible para rollback local |
| ¿Qué stack utilizamos? | Python y bibliotecas detectadas, con entorno H4 por fijar. Streamlit propuesto para interfaz local, CSV/JSON y gráficos. Express, Prisma y React siguen como plataforma |
| ¿Cómo interactuamos? | Editamos lags y escenarios, pulsamos PREDECIR sin entrenar, revelamos el observado y avanzamos el mes. La historia, error y gráfico se actualizan localmente |
| ¿Qué hacemos en tres semanas? | Primera: simulador editable y datos. Segunda: modelos e inferencia interactiva. Tercera: test V1, monitoreo, candidato, promoción o rechazo, rollback y defensa |
| ¿Qué presenta cada integrante? | Erika: motor, pipeline, modelos y artefactos. Ross: interfaz, escenarios, monitoreo y trazabilidad. Ambos: selección, test, ciclo local y demo |
| ¿Qué queda para H5? | Administración integrada, jobs, permisos, Neon, registro y rollback productivos, ranking, reposiciones, alertas automáticas y reentrenamiento comercial |

El 70 % requiere simulador interactivo, modelos comparados, V1, métricas, monitoreo, candidato, rollback y evidencia reproducible. Un CSV estático no basta. Una buena métrica sintética no certifica ventas reales ni reemplaza decisiones humanas.

## 20. Reporte de integración y cierre técnico de Ross

Revisión del 10 de noviembre de 2026, America/La_Paz. Se revisó el código integrado en 632bbf5, que incorpora el trabajo de Erika d07fcdd mediante el PR 52. El estado inicial del checkout estaba limpio. No se ejecutaron fetch, merge, commit, push o deploy durante esta revisión. Las consultas Git fueron de lectura. No se conectó con Neon.

La evidencia actual está en [cierre_ross_2026-11-10](evidencias/cierre_ross_2026-11-10/). Los informes T10–T21 se conservan como antecedentes, sin sustituir sus resultados por esta revisión. Las cifras de noviembre 4 describen una entrega anterior a los modelos de Erika y no deben utilizarse como estado actual.

| Componente | Implementación actual y comprobación |
|---|---|
| Dataset | 1.1 sintético, seed 42, 56 productos, tiendas 5/6/7, 24 meses, 4.032 filas base y 3.528 supervisadas. No se regeneró |
| Contrato | Tres lags y seno/coseno del mes. IDs seleccionan la serie. Escenario, latente y observado del mes no entran al modelo |
| Motor | Ocho escenarios, precargas, edición, seed y azar por par, resultado manual o generado, cierre único y avance de lags |
| Situaciones ambiguas | Producto nuevo e historia insuficiente producen abstención. STOCKOUT distingue disponibilidad, observado y latente |
| Preparación ML | Split temporal 15/3/3. Transformaciones de LinearRegression ajustadas en TRAIN. Sin split aleatorio |
| Modelos y experimentos | Baseline, LinearRegression y RandomForest ya entrenados o evaluados por Erika. Tres registros en experiments.csv |
| V1 | RandomForest seleccionado por validation, con configuración y artefacto congelados. Comienza disponible, sin ACTIVE |
| TEST | Reporte oficial existente con 504 observaciones. Se leyó el resultado, sin ejecutar nuevamente su evaluación |
| Inferencia | Carga local con hashes y contrato comprobados. Activación V1 explícita por par. Editar y predecir no entrenan |
| Referencias de Ross | Botón COMPARAR TRES REFERENCIAS conectado a la aplicación normal. Baseline y LR REFERENCE funcionan sin ACTIVE. RF exige V1 activa |
| Presentación de referencias | Tabla y gráfico con salidas o abstenciones, versión y corte. Una edición marca la comparación anterior como desactualizada, sin sobrescribirla |
| Observados | Emisión congelada antes de revelar el resultado, cierre confirmado y coherencia entre diario y motor |
| Errores y monitoreo | MAE, RMSE, R², cobertura y casos comunes con baseline. Desgloses por tienda, producto, mes, rotación y escenario |
| Drift | Criterio demostrativo con dos ventanas de tres meses. No inicia entrenamiento y no confunde fallos técnicos con cambios del negocio |
| Reentrenamiento | Ensayo independiente con nuevos cierres. Tres meses iniciales, seis filas de ajuste y tres reservadas. Los fixtures prueban esta ruta sin reemplazar V1 |
| Candidato y decisión | Comparación local con ACTIVE, rechazo con motivo e identificación de evidencia insuficiente. JSON no otorga autoridad de promoción |
| Rollback | Referencia local anterior verificada. Se conservaron los seis cierres visuales después de retornar al estado sin ACTIVE |
| Contextos | Runtime, candidatos, decisiones y referencias por producto-tienda, aislados entre sesiones. Reset no activa modelos automáticamente |
| Exportación | Descarga real h4-session-1 con h4-traceability-1. El archivo contiene seis cierres y su verificador devuelve True |
| Evidencia | Prompts, configuraciones, hashes, versiones, registros de ciclo, reportes originales y capturas separadas de archivos oficiales |

**Resultados existentes de Erika.** La siguiente tabla procede del registro congelado de validation, abril a junio de 2026. No contiene entrenamientos de esta revisión.

| Modelo | MAE validation | RMSE validation | R² validation |
|---|---:|---:|---:|
| Baseline lag1 | 6,1587 | 10,9727 | -0,1042 |
| LinearRegression | 5,4732 | 8,7926 | 0,2910 |
| RandomForest V1 | 5,1587 | 8,4416 | 0,3465 |

El TEST oficial de V1, julio a septiembre de 2026, registra MAE 4,8142, RMSE 8,1829, R² 0,4230 y cobertura 100 % sobre 504 filas. Son resultados académicos del dataset sintético. No se presentan como porcentaje de precisión ni desempeño comercial certificado. La validación tiene errores importantes por rotación y algunos R² negativos por grupo. Eso limita su uso, aunque RandomForest tenga el mejor promedio global de las alternativas registradas. No se ajustaron modelos después de leer TEST.

**Problemas encontrados y resueltos.** La ruta absoluta del candidato archivado apuntaba al equipo de Erika. El código ahora localiza únicamente ese paquete de identidad fija dentro del checkout, después de validar el hash independiente del manifiesto. Conserva intacta su ruta original en el archivo histórico y vuelve a verificar los cuatro archivos del conjunto antes de cargar el modelo. Un upload no puede elegir otra carpeta ni sustituir hashes.

La interfaz tenía un adaptador funcional de tres referencias que no se invocaba en la aplicación normal. Se conectó mediante una acción explícita, con valores, motivos de abstención, roles y gráficos. No convierte LR REFERENCE en un modelo activable ni mezcla estas emisiones puntuales con métricas de validation, TEST o promoción de candidatos.

Faltaba el desglose por escenario. Ahora informa cantidad de casos, predicciones, cobertura, MAE y RMSE, manteniendo abstenciones en el denominador. Los reportes pueden aportar scenario como metadato validado. Si falta se conserva NO REGISTRADO. No se infiere a partir del producto ni se añade una feature.

Una prueba comparaba rutas temporales cortas de Windows con sus equivalentes largos. La comprobación se corrigió para comparar ambas rutas resueltas y mantener la misma exigencia de aislamiento. No se eliminaron pruebas ni se modificaron expectativas de negocio para ocultar fallos.

**Pruebas y entorno.** La colección previa contenía 464 pruebas. La primera ejecución completa, tras preparar dependencias, terminó con dos errores de ruta archivada y una aserción de ruta temporal. Se ejecutaron 454 casos porque el error de preparación de una clase impidió iniciar sus casos. Tras las correcciones y nueve regresiones nuevas, la suite final ejecutó **473/473 sin fallos ni omisiones**. Los fixtures ajustan modelos temporales como parte de sus propias pruebas. Ningún entrenamiento reemplazó V1 ni escribió sobre los reportes oficiales.

El entorno local utiliza Python 3.11.9, Streamlit 1.66.1, pandas 3.1.0, NumPy 2.4.6, scikit-learn 1.9.1, SciPy 1.17.1 y joblib 1.6.0. Al comenzar faltaban las dependencias de inferencia. Se instalaron las versiones ya declaradas por Erika en requirements-training.txt, sin cambiar locks, Python general o visión.

**Revisión visual.** Se utilizó la aplicación real en 127.0.0.1:8502, con eventos separados mediante app_verificacion.py. No hubo modelos falsos. En 1366 × 900 se observaron controles, activación V1, las tres referencias reales, seis predicciones de octubre de 2026 a marzo de 2027, generación, cierre y avance a abril. El monitoreo mostró seis cierres, seis predicciones y cobertura 100 %. Su MAE de sesión fue 1,032, distinto del MAE de TEST. El baseline de esa misma sesión tuvo MAE 1,000. Una demo puntual favorable o desfavorable no reemplaza la evaluación congelada.

Se comparó el candidato archivado, se observó INSUFFICIENT_EVIDENCE, se registró rechazo con motivo y se comprobó que PROMOVER CANDIDATE siguiera deshabilitado. La descarga real se conservó como sesion_visual.json y pasó verify_session_export. El rollback preservó cierres y emisiones previas. En 390 × 844 los selectores y métricas se apilan, los textos son legibles y las tablas usan desplazamiento horizontal. La resolución del navegador se restauró al terminar. Las capturas y revision_visual.json describen exactamente el recorrido NORMAL. Los demás escenarios se verifican mediante la suite, sin atribuirles capturas inexistentes.

**Estado final y pendientes.** La integración técnica de Ross con los componentes disponibles de Erika quedó operativa y verificada. No necesita duplicar su motor o entrenar modelos nuevos. La promoción de candidatos reales permanece pendiente de un protocolo aprobado, porque seis filas de ajuste y tres observaciones de comparación no acreditan elegibilidad. No se retiró esa protección para declarar completo el proyecto.

Quedan la aceptación del equipo sobre la demo y el consumo de la exportación, el ensayo de exposición, la recuperación de prompts originales no disponibles y la decisión de promoción. Esta revisión automatizada con navegador no certifica que Erika o Ross ya hayan realizado una defensa o firmado aceptación. La integración comercial, datos reales certificados, monitoreo productivo y reposiciones permanecen en H5. Los conteos de la matriz son cumplimiento documental y técnico, no una medida exacta del 70 % académico ni de precisión predictiva.

## 21. Presentación de H4 al docente

Material preparado el 10 de noviembre de 2026. Este apartado reúne el guion, responsables, evidencias y respuestas dentro de la misma documentación oficial. No sustituye el ensayo conjunto. El recorrido principal dura aproximadamente quince minutos, más preguntas. Si el docente dispone de menos tiempo, priorizar problema, datos, predicción interactiva, evaluación y límites.

### 21.1. Preparación antes de la exposición

Trabajar desde la raíz del repositorio con el entorno H4 preparado. No utilizar la ruta antigua del equipo de Erika. En PowerShell:

```powershell
$h4Python = Join-Path (Get-Location).Path 'ml/demand/.venv/Scripts/python.exe'
& $h4Python --version
& $h4Python -m pip check
& $h4Python -B -m streamlit run ml/demand/streamlit_app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
```

Abrir la URL que muestre ese proceso. Si 8501 está ocupado, cambiar el puerto explícitamente, por ejemplo a 8503, y abrir la nueva URL. No usar una instancia antigua sin comprobar qué versión muestra. Mantener abierta la consola propia. No detener procesos ajenos. La instalación del entorno se explica en el [README técnico](../../ml/demand/README.md) y se prepara antes de la clase, no durante la exposición.

Abrir esta sección, el simulador, el registro de experimentos y el reporte TEST. Tener disponibles las capturas y el JSON de respaldo. La aplicación usa archivos locales y puede demostrarse sin Neon o Internet una vez instalado el entorno. No ejecutar generadores, seeds, entrenadores ni evaluate_v1 para preparar una pantalla. Los artefactos congelados ya existen.

Si el código cambió después de la última validación, ejecutar con anticipación `& $h4Python -B ml/demand/run_tests.py`. La evidencia disponible del 10 de noviembre acredita 473 pruebas aprobadas. Mostrar ese log con su fecha, sin presentarlo como una ejecución nueva. La preparación de este guion no volvió a entrenar ni repetir TEST.

### 21.2. Qué explica cada integrante

| Responsable | Explicación principal | Evidencia que presenta |
|---|---|---|
| Ross | Problema de la tienda, interacción, edición, validaciones y diferencia entre observado y predicción | Interfaz, cinco features y estados bloqueados |
| Erika | Dataset sintético, motor, escenarios, lags, split temporal, preprocesamiento y algoritmos | CSV, manifiesto, artefactos y experimentos |
| Erika | Por qué se eligió RandomForest V1 y cómo se protegió TEST | Comparación de validation y reporte final congelado |
| Ross | Errores por grupos, cobertura, monitoreo y comparación visual | Seis meses de sesión, tablas, gráficos y desgloses |
| Erika | Diferencia entre inferencia y reentrenamiento, candidato y versiones | Activación local, comparación y restricción de promoción |
| Ross | Trazabilidad, exportación y límites de la demostración | JSON descargado, capturas y matriz |
| Ambos | Decisiones, riesgos, trabajo compartido y alcance H5 | Respuestas de defensa y aceptación del ensayo |

Ross puede abrir con: «Queremos estimar cuántas unidades de un producto podrían venderse el siguiente mes en una tienda. Esto puede ayudar a estudiar la rotación y preparar decisiones de reposición. En H4 demostramos el proceso con datos sintéticos, todavía no una predicción comercial certificada».

Erika continúa: «Usamos una tabla mensual por producto y tienda. Cada ejemplo contiene tres ventas anteriores y dos variables del calendario. Conocemos el resultado posterior para entrenar, pero ese resultado nunca se entrega como entrada de la predicción del mismo mes».

Ambos deben comprender el trabajo completo. El reparto indica quién conduce cada parte, no quién puede responder las preguntas de esa parte.

### 21.3. Guion de la demostración principal

| Tiempo orientativo | Responsable y acción | Qué explicar y comprobar |
|---|---|---|
| 0–2 min | Ross presenta problema. Erika muestra origen y estructura del dataset | 56 productos, tres tiendas, 24 meses, seed 42, 4.032 filas mensuales y 3.528 supervisadas. Los IDs son reales del catálogo de referencia, las ventas son simuladas |
| 2–4 min | Erika muestra columnas y split. Ross abre el simulador | TRAIN enero 2025–marzo 2026, validation abril–junio 2026, TEST julio–septiembre 2026. Octubre–diciembre 2024 aportan los primeros lags. Al iniciar no hay ACTIVE |
| 4–5 min | Ross selecciona producto 1, Tienda 1, mes octubre 2026 y pulsa COMPARAR TRES REFERENCIAS | Baseline y LR REFERENCE emiten sin ACTIVE. RF indica V1_NO_ACTIVE. La comparación puntual no entrena ni selecciona un ganador |
| 5–6 min | Erika escribe un motivo, por ejemplo «Demostración académica H4», y pulsa ACTIVAR V1 CONGELADA. Ross compara otra vez | Leer nombre, versión y origen. Ahora aparecen las tres salidas reales. Activar V1 disponible no equivale a entrenar o promover un candidato nuevo |
| 6–8 min | Ross anota los tres lags iniciales, modifica uno, valida y pulsa PREDECIR | Mostrar las features realmente utilizadas. La predicción no usa el observado. No prometer que un árbol cambiará su salida ante cualquier cambio pequeño. Volver a los valores iniciales y predecir antes de revelar el resultado |
| 8–10 min | Ross ejecuta PREDECIR → GENERAR SIGUIENTE MES → AVANZAR MES durante seis meses del mismo par | GENERAR revela el observado del mes abierto. AVANZAR cierra y mueve el reloj. Repetir de octubre 2026 a marzo 2027 sin reset, conservando V1. El mes abierto final debe ser abril 2027 |
| 10–11 min | Ross abre Errores y monitoreo. Erika muestra los resultados congelados del experimento | Leer casos, cobertura, MAE, RMSE y baseline de la sesión. Distinguirlos de validation y TEST. Mostrar desgloses por producto, tienda, mes, rotación y escenario |
| 11–13 min | Erika explica el candidato archivado. Ross pulsa COMPARAR CANDIDATE y muestra su resultado | Sin candidato nuevo de la sesión, producto 1/Tienda 1 permite comparar el archivo verificado. Es otra ejecución, con seis filas de ajuste y tres reservadas en julio–septiembre 2027. No fingir que procede de los seis meses recorridos en vivo |
| 13–14 min | Ross escribe un motivo, por ejemplo «Muestra insuficiente para promoción», y pulsa RECHAZAR CANDIDATE. Descarga la sesión | Mostrar INSUFFICIENT_EVIDENCE, rechazo y PROMOVER CANDIDATE deshabilitado. El JSON conserva evidencia, no autoriza activación. Guardar el archivo antes de resetear |
| 14–15 min | Erika aplica ROLLBACK LOCAL con motivo. Ross muestra que el historial permanece. Ambos cierran | En este recorrido se vuelve de V1 a SIN ACTIVE, su referencia anterior. No afirmar que se ejecutó V2 → V1. Separar entrega técnica H4, aceptación del equipo e integración comercial H5 |

Los resultados en vivo se leen de la pantalla. No se modifican datos o escenarios para obtener un MAE más atractivo. En la revisión guardada, seis meses NORMAL produjeron MAE de sesión 1,032 frente a 1,000 del baseline. Otra secuencia de edición puede dar otros errores. Ese MAE de sesión no reemplaza el MAE TEST de V1, 4,8142 sobre 504 filas.

**Ensayo opcional de reentrenamiento.** Solo si hay tiempo y se acordó demostrarlo, continuar el mismo par hasta completar doce cierres nuevos de octubre 2026 a septiembre 2027. ENSAYAR REENTRENAMIENTO crea un candidato independiente. Octubre–diciembre aportan historia, enero–junio ofrecen seis targets de ajuste y julio–septiembre quedan reservados. Mostrar carpeta y versión nuevas, comparación y conservación de ACTIVE. No sobrescribir V1 ni ejecutar los entrenadores oficiales. El candidato puede rechazarse y no se garantiza mejora. El recorrido principal puede usar el candidato archivado para evitar convertir el entrenamiento en una dependencia de la exposición.

**Casos adicionales para preguntas.** Realizarlos después de guardar la sesión principal, porque cambiar de escenario tras cerrar meses exige RESTABLECER EDICIÓN. Cada reset deja V1 disponible pero sin ACTIVE. Si el caso necesita RF, activar de nuevo con motivo.

| Caso | Recorrido corto | Respuesta esperada |
|---|---|---|
| STOCKOUT | Reset, elegir STOCKOUT, emitir o registrar abstención y generar el observado | Mostrar demanda latente interna, disponibilidad y venta observada. La venta no supera disponibilidad. La latente no es feature ni verdad comercial |
| PRODUCTO NUEVO | Reset, elegir PRODUCTO NUEVO, validar y comparar referencias | HISTORIAL INSUFICIENTE y abstenciones. No llenar meses inexistentes con ceros para forzar una salida |
| Historia incompleta | Desmarcar «Los tres meses anteriores están completos» antes de emitir | DATOS INCOMPLETOS. Se bloquea la predicción válida, no se fabrica un target |
| Cierre manual incompleto | Emitir, ingresar observado manual y dejar sin marcar «El mes objetivo está cerrado y completo» | No registrar ni avanzar hasta confirmar. El observado revelado ya bloquea la entrada y la predicción de ese mes |
| Cambio persistente | Reset, elegir CAMBIO PERSISTENTE antes de generar y recorrer meses suficientes | Revisar error y baseline, sin prometer que siempre se encenderá una alarma o mejorará otro modelo |

**Si algo falla en clase.** Detener la acción y leer el estado. Modelo no disponible puede significar falta de activación, dependencias o integridad. No reinstalar versiones al azar, editar hashes, reentrenar V1 o usar db push. Conservar el error y mostrar las evidencias fechadas de respaldo. Si el candidato archivado no está disponible, reconocerlo y explicar su comparación desde el informe. No anunciar que una captura es una ejecución en vivo. Si el docente exige una promoción positiva de un candidato, declarar ese requisito pendiente y acordar primero un protocolo de elegibilidad. No desbloquear el botón durante la defensa.

### 21.4. Evidencias que deben estar abiertas o localizables

| Qué demostrar | Archivo o evidencia | Explicación breve |
|---|---|---|
| Dataset y ejemplos | [base mensual](../../ml/demand/data/escenarios_v1_1/base_mensual.csv), [tabla supervisada](../../ml/demand/data/escenarios_v1_1/dataset_supervisado.csv) y [validación](../../ml/demand/data/escenarios_v1_1/validacion.json) | Mostrar pocas filas, tipos y distribución. No confundir estadísticas del target con métricas de modelo |
| Procedencia y reproducción | [catálogo de referencia](../../ml/demand/catalog_reference.json) y [manifiesto](../../ml/demand/data/escenarios_v1_1/manifest.json) | Referencia fechada, seed, periodo y hashes. No presentarlo como una consulta actual de Neon |
| Comparación de algoritmos | [experiments.csv](../../ml/demand/reports/experiments.csv) | Tres registros, parámetros, versiones y métricas de validation. Baseline 6,1587, LR 5,4732 y RF 5,1587 de MAE |
| Selección V1 | [manifiesto de selección](../../ml/demand/reports/v1_selection_manifest.json) | Elección por validation y configuración congelada. Los artefactos permanecen en ml/demand/models |
| Evaluación final | [v1_test_evaluation.json](../../ml/demand/reports/v1_test_evaluation.json) | 504 filas, MAE 4,8142, RMSE 8,1829, R² 0,4230, cobertura 100 %. No repetir TEST para producir otra cifra |
| Funcionamiento visual | [referencias en escritorio](evidencias/cierre_ross_2026-11-10/escritorio_referencias.png), [monitoreo](evidencias/cierre_ross_2026-11-10/escritorio_monitoreo.png) y [vista estrecha](evidencias/cierre_ross_2026-11-10/estrecha_controles.png) | Capturas reales de una revisión del 10 de noviembre, no sustitutos ocultos de la demo |
| Sesión y trazabilidad | [sesion_visual.json](evidencias/cierre_ross_2026-11-10/sesion_visual.json) | Respaldo descargado con seis cierres y extensión h4-traceability-1. Compararlo con la nueva descarga sin sobrescribirlo |
| Pruebas e integridad | [log de 473 pruebas](evidencias/cierre_ross_2026-11-10/pruebas_finales.txt) y [verificación final](evidencias/cierre_ross_2026-11-10/verificacion_final.json) | Fecha, alcance, 29 archivos protegidos intactos y límites. No afirmar que cero fallos elimina todo riesgo |
| Alcance y pendientes | [matriz vigente](H4_MATRIZ_CUMPLIMIENTO_FINAL.md), [checklist de aceptación](H4_CHECKLIST_VALIDACION_ROSS.md) y [prompts](PROMPTS_MODELO_PREDICTIVO_H4.md) | Distinguir implementación, verificación, aceptación humana y registros originales faltantes |

Para mostrar ejemplos y los resultados sin ejecutar entrenamiento, desde la raíz:

```powershell
Import-Csv -LiteralPath 'ml/demand/data/escenarios_v1_1/dataset_supervisado.csv' | Select-Object -First 5
Import-Csv -LiteralPath 'ml/demand/reports/experiments.csv' | Select-Object model, mae_val, rmse_val, r2_val
$h4Test = Get-Content -LiteralPath 'ml/demand/reports/v1_test_evaluation.json' -Raw | ConvertFrom-Json
$h4Test.metrics
Get-Content -LiteralPath 'docs/H4/evidencias/cierre_ross_2026-11-10/pruebas_finales.txt' -Tail 5
```

No es necesario abrir todo el código. Si preguntan por responsabilidades técnicas, Erika señala demand_engine.py, ml_pipeline.py y demand_runtime.py. Ross señala streamlit_app.py, ui_panels.py y ui_analysis.py. Los dos explican la conexión, las pruebas y la separación entre datos simulados y comerciales.

### 21.5. Preguntas probables del docente

| Pregunta | Respuesta para defender |
|---|---|
| ¿Qué predicen exactamente? | Unidades brutas observadas de un producto en una tienda durante el siguiente mes. Es regresión supervisada temporal de un paso |
| ¿Por qué no clasifican alta, media o baja demanda? | Necesitamos una cantidad numérica para estudiar ventas y una reposición futura. La clasificación respondería otra pregunta |
| ¿Por qué datos sintéticos? | La historia disponible no permite certificar todavía un pronóstico comercial. La simulación permite demostrar el proceso técnico con origen explícito |
| ¿Tabular, temporal y supervisado significan lo mismo? | No. Tabular describe columnas, temporal indica orden cronológico, sintético identifica el origen y supervisado significa que tenemos entradas y resultados conocidos al aprender |
| ¿Cuáles son las entradas? | Tres lags de ventas y seno/coseno del mes objetivo. El target es target_ventas_mes. promedio_3_meses queda fuera porque se deriva de esos lags |
| ¿Cómo distinguen productos y tiendas si no usan los IDs como features? | Los IDs seleccionan su historia. Las diferencias llegan mediante los lags. Con las mismas cinco entradas un mismo modelo puede dar la misma salida, aunque cambien los IDs |
| ¿Por qué seno y coseno? | Representan el mes como un ciclo. Diciembre y enero quedan próximos, sin usar información futura |
| ¿Por qué 70/15/15? | Training aprende, validation selecciona y test evalúa una configuración ya congelada. Se usan meses completos: 15/3/3 sobre 21 meses supervisados |
| ¿Por qué no dividir al azar? | Porque usar meses futuros para aprender y evaluar meses pasados produciría una evaluación engañosa. Todas las filas de un mes permanecen juntas |
| ¿Hay fuga al usar julio para predecir agosto del TEST? | No si julio ya cerró al emitir agosto y no se ajustan parámetros con el error de TEST. Es evaluación mensual de un paso, no tres meses pronosticados desde un único corte |
| ¿Qué sería data leakage aquí? | Entregar el observado del mes objetivo como entrada, ajustar el scaler con todo el dataset o usar información que todavía no se conocía al emitir |
| ¿Qué normalizan? | El preprocesador del modelo lineal usa estadísticas aprendidas solo en TRAIN y se conserva con el artefacto. RandomForest no requiere escalado numérico |
| ¿Por qué compararon varios algoritmos? | Para comprobar si más complejidad aporta una mejora frente al baseline. No elegimos un modelo solo por ser más complejo |
| ¿Por qué RandomForest V1? | Tuvo el menor MAE de validation entre las alternativas registradas. Después se evaluó en TEST sin cambiar su configuración. Eso no demuestra que siempre sea el mejor modelo posible |
| ¿Por qué no una red neuronal? | Se consideró una MLP, pero añade escalado, ajustes y riesgo de sobreajuste. Era opcional y no se entrenó. No atribuimos resultados a una red inexistente |
| ¿MAE 4,8142 significa 4,8 % de error? | No. Significa unas 4,8 unidades de desviación absoluta media por fila producto-tienda-mes del TEST sintético |
| ¿R² 0,423 significa 42,3 % de precisión? | No. Compara el error con una referencia basada en la media. Puede ser negativo y no es Accuracy |
| ¿Por qué también RMSE y por qué no MAPE? | RMSE da más peso a errores grandes. MAPE presenta problemas cuando las ventas observadas son cero, por eso no es principal |
| ¿Un mejor error en la demo prueba que el modelo mejoró? | No. La demo contiene pocos meses de una serie. Debe distinguirse de validation y de las 504 filas del TEST congelado |
| ¿Cómo tratan ventas cero o falta de stock? | Un cero observado válido se conserva. Un mes faltante no se rellena con cero. STOCKOUT demuestra que ventas observadas no equivalen a toda la demanda |
| ¿El modelo recibe la demanda latente del simulador? | No. Se usa únicamente como metadato explicativo. Tampoco recibe escenario, ruido o parámetros internos del generador |
| ¿Editar o predecir vuelve a entrenar? | No. PREDECIR utiliza ACTIVE. ENSAYAR REENTRENAMIENTO es otra acción, con datos nuevos y un candidato separado |
| ¿Cómo detectan que conviene revisar el modelo? | Comparan dos ventanas de tres meses cerrados, error, baseline y cobertura. El criterio es demostrativo. Una señal no prueba drift ni inicia fit automáticamente |
| ¿Por qué el candidato no se promueve? | La comparación disponible tiene seis filas de ajuste y tres reservadas de una sola serie. Falta evidencia y un protocolo aprobado. Un mejor promedio no basta para habilitarlo |
| ¿Qué rollback demostraron? | El retorno local de V1 a la referencia anterior sin ACTIVE, conservando el historial. No fingimos una promoción real de V2 seguida de retorno a V1 |
| ¿Qué pasa con una predicción negativa? | Se registra la salida original y se aplica la política declarada de cada ruta. La comparación de referencias muestra abstención con motivo y conserva el valor original, sin ocultarlo con un cero inventado |
| ¿Puede aprender la fórmula sintética? | Es un riesgo. Excluimos parámetros internos, evaluamos temporalmente y reconocemos que buenas métricas sintéticas no certifican ventas reales |
| ¿Con 3.528 filas ya tienen muchos años de evidencia? | No. Son 168 series durante 21 meses objetivo, con dependencias temporales. No son 3.528 meses independientes ni historia comercial certificada |
| ¿El sistema compra o repone automáticamente? | No. En H4 no se alteran ventas, inventario o Neon. La reposición comercial necesita políticas de stock, tránsito, plazos y supervisión, previstas para H5 |
| ¿Qué prueban los 473 tests? | Verifican contratos, flujos y regresiones del alcance ejecutado. La revisión visual añade otra evidencia. Ninguna equivale a demostrar que no existen más errores o a aceptar la entrega por los estudiantes |
| ¿Cómo registraron el proceso y la IA utilizada? | Conservamos experimentos, versiones, hashes, configuraciones, evidencia y log de prompts. Los originales no recuperados se declaran faltantes, sin reconstruir citas o fechas |
| ¿Qué representa el 70 % de H4? | Un experimento funcional con dataset, modelos, evaluación, simulador y evidencia. No es porcentaje de líneas ni de precisión. La aceptación académica corresponde al docente |

### 21.6. Cierre y ensayo del equipo

Antes de presentar, Erika y Ross deben recorrer la demo completa una vez, intercambiar preguntas y comprobar que las evidencias abren en el equipo que llevarán. Registrar la fecha del ensayo y cualquier incidente cuando realmente ocurra. Esta sección preparada no modifica las casillas de aceptación humana ni declara realizada la defensa.

- [ ] Ambos explican problema, dataset, features, target y split sin depender de leer código.
- [ ] La demo funciona desde una sesión inicial y se distingue predicción, observado, generación y entrenamiento.
- [ ] Las evidencias, métricas congeladas, capturas y respaldo JSON están disponibles localmente.
- [ ] Se explica el bloqueo de promoción y se confirma antes de la clase si el docente exige una ruta positiva adicional.
- [ ] Ambos revisan la distribución de la exposición y aceptan el consumo de la exportación.

Ross puede cerrar con: «Tenemos una implementación local que permite editar entradas, observar predicciones y medir errores sin modificar la operación comercial. Sus límites están registrados y podemos seguir cada resultado hasta sus datos y versión».

Erika completa: «V1 fue elegida con validation y evaluada en un TEST separado. El siguiente paso es trabajar con datos comerciales certificados y completar la integración H5. Un candidato nuevo necesita evaluación y aprobación, no activación automática».

## 22. Consulta predictiva dentro del administrador

Ampliación autorizada el 10 de noviembre de 2026. La consulta de predicciones está disponible en **Panel → Predicción de ventas**, en `/panel/prediccion`. Es una pantalla React de RepuestoPro, no una ventana de Streamlit insertada. El simulador editable conserva su ejecución independiente. Esta ampliación reemplaza la decisión inicial de dejar toda integración web para H5. La integración con historia comercial certificada, las reposiciones y el monitoreo productivo continúan pendientes.

La pantalla permite seleccionar un producto del catálogo de referencia, una tienda, consultar V1 y ver un gráfico del historial frente a la predicción. Presenta unidades previstas, baseline, versión, MAE, RMSE y R² del TEST sintético ya guardado. No vuelve a evaluar TEST. Tampoco calcula el error de una venta futura todavía desconocida.

El historial utilizado termina en septiembre de 2026. Por tanto, esta demostración pronostica octubre de 2026, aunque el calendario del equipo marque otro mes. No se desplaza ese historial ni se fabrican ventas recientes. Producto 1 y Tienda 1, con locationId 5, producen aproximadamente 22,07 unidades con la referencia congelada. El valor es una estimación numérica, no una orden de compra.

### 22.1. Conexión, permisos y límites

React consulta `GET /api/predictions/catalog` y `POST /api/predictions/demand`. El backend exige una sesión válida y rol ADMIN en ambas rutas. No basta con ocultar el enlace del menú. Los IDs se validan antes de ejecutar Python. Una selección inexistente devuelve 400. Un modelo o entorno no disponible devuelve 503, sin exponer rutas internas o credenciales.

El backend ejecuta `ml/demand/admin_prediction.py` con un proceso Python limitado por tiempo y tamaño de respuesta. No ejecuta comandos construidos con los valores recibidos. Se utiliza el entorno `ml/demand/.venv` o la ruta de intérprete definida por `DEMAND_PYTHON` en el proceso. No es necesario modificar archivos de secretos para la ejecución local actual.

El adaptador comprueba las huellas del catálogo, la base sintética, el reporte TEST y los controles existentes del artefacto V1. Acepta diferencias de finales de línea LF/CRLF en archivos de texto, sin aceptar contenido distinto. Construye los tres lags desde meses completos consecutivos. Conserva ventas cero, rechaza cantidades negativas, meses faltantes y duplicados. Solo utiliza los cinco campos ya definidos para el modelo.

Cada consulta utiliza una instancia aislada de V1 para inferencia. No comparte ACTIVE con Streamlit, no promueve candidatos ni altera sus sesiones. La autenticación normal del sistema sigue utilizando su base configurada. El cálculo predictivo utiliza archivos locales y no escribe información comercial. Durante las pruebas de esta ampliación se sustituyó la conexión de base por una dirección local inválida y las sesiones de las aplicaciones de prueba por fixtures. No se consultó Neon ni se debilitó la autenticación de la aplicación normal.

### 22.2. Dashboard y diagnóstico local

Se identificaron dos aplicaciones distintas utilizando los puertos 3000 y 5173 en direcciones de red diferentes. RepuestoPro atiende en localhost y la otra aplicación usa IPv4. No se detuvieron procesos ajenos. No se debe cambiar a 127.0.0.1 sin comprobar qué aplicación responderá.

El dashboard leía todas las columnas de ventas recientes, detalles y movimientos aunque solo mostraba algunos campos. Se reemplazaron esas lecturas por selecciones explícitas de los campos necesarios. Se mantiene el filtro CONFIRMED, los permisos y el alcance por tienda. No se eliminan controles para hacer funcionar un esquema incompatible.

El mensaje de error anterior ocultaba la diferencia entre una API inaccesible, falta de permiso, conexión de base no disponible o estructura incompatible. Ahora se distinguen esos casos. Los errores Prisma P2021/P2022 producen un 503 con código DASHBOARD_SCHEMA_UNAVAILABLE, sin inventar estadísticas ni mostrar SQL. ADMIN conserva un enlace a la consulta predictiva incluso si el dashboard falla.

La causa concreta de la captura original no quedó certificada. No se ejecutó una consulta autenticada del dashboard contra Neon, porque esta tarea prohíbe tocar esa base. Las pruebas locales comprueban la respuesta correcta con datos controlados y el fallo explícito ante una columna ausente. No equivalen a afirmar que el dashboard comercial real ya respondió correctamente. Si persiste una incompatibilidad física, su reconciliación requiere una tarea posterior autorizada. No se aplicaron migraciones ni cambios de datos para ocultarla.

### 22.3. Cómo presentar la nueva pantalla

En la sesión ADMIN, abrir `http://localhost:5173/panel/prediccion`. Si el servidor local fue reiniciado, iniciar sesión mediante el acceso habitual. El backend y el frontend deben estar ejecutándose. No hace falta iniciar Streamlit para consultar esta pantalla. No desplegar la aplicación para esta demostración local.

Ross puede decir: «Esta es la consulta predictiva dentro del administrador. Seleccionamos producto y tienda. El backend obtiene su historial sintético guardado y consulta el modelo V1. La pantalla muestra la estimación del siguiente mes después del cierre disponible. El gráfico permite comparar ese valor con el historial. Las métricas corresponden al TEST sintético, no al error conocido de esta predicción futura».

Consultar producto 1, Tienda 1. Mostrar octubre de 2026, las unidades previstas, baseline y gráfico. Explicar el aviso de datos sintéticos. Cambiar el producto para comprobar que se limpia el resultado anterior. Después abrir Streamlit para demostrar edición, escenarios, reloj y monitoreo. Reservar unos tres minutos para la pantalla administrativa, luego continuar con las partes principales de la sección 21. Si falta tiempo, reducir los casos opcionales.

Erika puede explicar: «La pantalla reutiliza el modelo elegido, no vuelve a entrenarlo al pulsar el botón. Los tres meses anteriores y el calendario forman las entradas. Los datos comerciales reales todavía necesitan una validación separada».

### 22.4. Verificación y evidencia

La suite backend utiliza una URL local inválida para impedir conexiones accidentales a Neon. Incluye permisos, IDs inválidos, catálogo, fallos y el recorrido HTTP → Node → Python → V1 con el artefacto real. Las pruebas de dashboard utilizan un cliente de datos controlado. Las pruebas frontend comprueban selección, consulta, métricas, limpieza de resultados, errores y acceso administrativo desde el dashboard.

Las ejecuciones de esta ampliación se guardan en [backend_integracion_admin.txt](evidencias/cierre_ross_2026-11-10/backend_integracion_admin.txt), [frontend_integracion_admin.txt](evidencias/cierre_ross_2026-11-10/frontend_integracion_admin.txt), [frontend_build_admin.txt](evidencias/cierre_ross_2026-11-10/frontend_build_admin.txt) y [pruebas_integracion_admin.txt](evidencias/cierre_ross_2026-11-10/pruebas_integracion_admin.txt). El intento de regresión detenido por restricciones locales de AppTest se conserva aparte. Los archivos muestran el resultado efectivo de cada ejecución. No representan una revisión visual manual nueva ni aceptación del docente.

Resultado final: 168 pruebas backend, 233 frontend y 479 H4 aprobadas, 880 en total, sin fallos finales. Typecheck backend y build frontend aprobados. La [verificación de integración](evidencias/cierre_ross_2026-11-10/verificacion_integracion_admin.json) registra resultados, rutas HTTP y límites. Continúan los avisos de entorno de pruebas sobre Canvas, navegación de jsdom, actualizaciones fuera de act y ScriptRunContext. No se instalaron dependencias para ocultarlos. El [estado Git](evidencias/cierre_ross_2026-11-10/git_status_admin.txt) y el [resumen de diferencias](evidencias/cierre_ross_2026-11-10/git_diff_stat_admin.txt) incluyen también el trabajo previo que ya existía en el checkout.

No se regeneró el dataset, no se reentrenó V1, no se repitió su evaluación TEST, no se modificó Prisma ni se aplicaron migraciones. Los ajustes de modelos que realizan los fixtures de la suite H4 permanecen en archivos temporales de prueba. El funcionamiento comercial completo no se declara al 100 % a partir de estas comprobaciones locales.

## Ampliación V2: reglas para las referencias externas

El diseño vigente para aprovechar M5 y Favorita está en el [anexo 35 del Plan V2](PLAN_DE_TRABAJO_V2.md) y en el [contrato de transformación](../../ml/demand/v2/contracts/retail_transformations.v2.json). Se utilizarán patrones por fuente, sin trasladar ventas a los IDs propios. Los negativos, fracciones, promociones desconocidas y días ausentes conservarán su significado. M5 aportará referencias de ventas y precio semanal. Favorita aportará cantidades positivas registradas y cobertura de promociones. Ninguna fuente acredita cotización Bs/USD, stock, modalidades comerciales o tiempos de proveedor.

Esta especificación no cambia el dataset 2.1.0, las features del modelo fijado o su TEST cerrado. Las ventanas externas definidas no sustituyen el split del futuro experimento ni son pruebas ciegas. Al definir esa especificación todavía no se habían ejecutado transformaciones. El estado posterior de external_curated se describe a continuación. Al cierre de esa etapa, la calibración ampliada y la construcción de otro build seguían pendientes. Automotive permanece pendiente de licencia. Las condiciones de publicación de derivados permanecen como revisión previa a distribuirlos.

## Referencias externas procesadas para la ampliación V2

M5 y Favorita tienen salidas privadas transformadas y validadas en external_curated. El [anexo 36 del Plan V2](PLAN_DE_TRABAJO_V2.md) conserva rutas, resultados y límites. Se separaron signos, fracciones, promociones desconocidas, meses parciales y cohortes de referencia sin convertir ventas externas en historia propia. La validación no significa que exista otro dataset RepuestoPro o que se haya calibrado o entrenado un modelo nuevo. El dataset 2.1.0, el modelo fijado y su TEST permanecen intactos. Automotive sigue pendiente de licencia.

## Decisiones vigentes para ampliar las referencias

El [anexo 37 del Plan V2](PLAN_DE_TRABAJO_V2.md) reúne las decisiones de los cinco riesgos principales sin cambiar el contrato utilizado por las transformaciones privadas ya registradas.

| Punto | Tratamiento definitivo para la siguiente etapa |
| --- | --- |
| M5 repetido | Solo sales_train_evaluation.csv aporta ventas. No concatenar el histórico de validación o la plantilla. |
| Ausencias de Favorita | Permanecen desconocidas. No rellenar con ceros ni inferir intermitencia o falta de stock. |
| Devoluciones y fracciones | Conservar signos y decimales por separado. No convertirlos directamente en el target bruto entero de RepuestoPro. |
| Variables faltantes | Cotización, disponibilidad y modalidades serán supuestos académicos explícitos o requerirán evidencia propia. No se fabricará respaldo externo. |
| Dominios distintos | Referencias de patrones por fuente, sin sustituir IDs o presentar ventas ajenas como propias. |

M5 aportará referencias de ceros observados, volumen, diferencias entre tiendas, cambios relativos de precio y calendario. Favorita aportará variabilidad de cantidades positivas registradas, colas por cohorte de unidades y cobertura de promociones conocidas. Sus eventos se mantendrán como diagnóstico. No se trasladarán feriados extranjeros, precios nominales, elasticidades o etiquetas mayoristas inventadas al simulador.

La definición de reglas ya está disponible. Existen referencias privadas procesadas de una etapa anterior, pero al cierre de esa revisión aún no había otro dataset final ni calibración ampliada. Aquella revisión fue documental. No cambia código, contratos fijados, datos, modelos o resultados. Los valores numéricos nuevos se decidirán al autorizar la calibración, manteniendo su origen, corte temporal y límites.

## Calibración ampliada de referencias, sin dataset nuevo

El [anexo 38 del Plan V2](PLAN_DE_TRABAJO_V2.md) registra la calibración de M5 y Favorita. Su [configuración](../../ml/demand/reports/v2/calibration/calibration-retail-20261115-03/calibration.json) conserva el código, las versiones de entrada y parámetros derivados solo de la ventana de referencia. Las comparaciones posteriores son descriptivas y no cambian esos parámetros.

M5 aporta una frecuencia media entre series de cambios de precio de 1.20 % por semana elegible y una magnitud típica de 8.59 %. Son referencias académicas para escenarios, sin elasticidad identificada. Favorita aporta una razón típica p95/mediana de cantidades positivas de 2.80 en su cohorte de unidades enteras. No significa que esos registros sean ventas mayoristas.

Se utilizaron cuantiles exactos por serie, separando cohortes y ventanas. Las promociones permanecen como diagnóstico condicionado a registros conocidos. Monash y UCI conservan su papel inicial. Cotización, stock, modalidades y plazos no adquieren respaldo real por esta ampliación. Automotive sigue fuera por licencia pendiente.

La calibración está calculada, pero aún no fue incorporada al generador y no existe un nuevo build por esta tarea. El dataset 2.1.0, sus modelos y el TEST cerrado permanecen intactos. La siguiente etapa requiere autorizar el consumo de esta configuración, su implementación y la construcción posterior del dataset.

## Generador ampliado preparado, sin build nuevo

La calibración ampliada ya está incorporada en retail-reference-generator-1.0.0. El [anexo 39 del Plan V2](PLAN_DE_TRABAJO_V2.md) registra la receta, el código separado y sus comprobaciones. Los generadores anteriores, el dataset 2.1.0 y el modelo fijado permanecen intactos.

La nueva versión aplica referencias de cambios de precio, factores de tienda, calendario positivo y picos de cantidades minoristas. Conserva intermitencia automotriz, tránsito, recepción física, stock vendible y ventas atendidas como target. Las promociones no se convierten en features futuras ni se atribuye una elasticidad comercial al precio. Los mecanismos de simulación y sus frecuencias supuestas están identificados.

Pasaron 74 pruebas, incluidas 16 nuevas. Solo se ejecutaron fixtures reducidos en memoria. No existe un nuevo build por esta tarea y su publicación está bloqueada. La siguiente etapa requiere autorizar la versión del dataset y la ejecución completa, con validación independiente de precios, cantidades, tiempos, cobertura y trazabilidad antes de publicarlo. Automotive continúa pendiente de licencia.

## Dataset ampliado 2.2.0 publicado localmente

El [anexo 40 del Plan V2](PLAN_DE_TRABAJO_V2.md) registra el build [calibrated-20261115-01](../../ml/demand/data/repuestopro_v2/2.2.0/calibrated-20261115-01/manifest.json). Contiene 4.032 filas mensuales y 3.528 supervisadas para 56 productos, tres tiendas y 24 meses. El split cronológico conserva 2.520 filas de TRAIN, 504 de VALIDATION y 504 de TEST.

El generador 1.1.0 conserva la calibración ampliada y añade una revisión administrativa sintética auditada cuando una propuesta de precio viola el costo. Hubo seis intervenciones. No se cambiaron costos o precios reales. Se conservaron los generadores anteriores y el dataset 2.1.0.

El build pasó validación física y temporal independiente, reproducción completa, relectura de archivos y checksums antes de publicarse en la carpeta local privada. Pasaron 83 pruebas del alcance. No se entrenó un modelo ni se evaluó predictivamente TEST. El administrador continúa usando el artefacto 2.1.0. Automotive permanece pendiente de licencia y no forma parte del dataset.

La ampliación sigue siendo académica y sintética. La preparación y el entrenamiento de un experimento 2.2.0 requieren autorización posterior. No equivale a una validación comercial de la demanda real de la empresa.

## Experimento 2.2.0 preparado, sin modelos entrenados

El [anexo 41 del Plan V2](PLAN_DE_TRABAJO_V2.md) registra la adaptación separada del preprocesamiento y la preparación experimental. Se verificaron TRAIN, VALIDATION, los targets, los tres lags y tres folds internos de meses completos. El cargador rechaza TEST y no interpreta sus filas. Solo se utilizan sus metadatos de separación y hashes de integridad.

El plan contempla el baseline, LinearRegression y ambos criterios de RandomForest, con seis grupos de features. Hay 54 candidatos y hasta 174 ajustes futuros. Hoy se ejecutaron cero ajustes reales o métricas predictivas. El escalado solo se comprobó con fixtures artificiales. Pasaron 35 pruebas y no se crearon artefactos o experimentos ficticios.

Al cierre de la preparación, V2-08 seguía pendiente de entrenamiento para el nuevo dataset. La ejecución posterior figura en la sección siguiente. La construcción de 2.2.0 está terminada, pero aún falta autorizar y ejecutar su entrenamiento, revisar los resultados de VALIDATION y seleccionar una configuración antes de la evaluación final. El administrador conserva el modelo 2.1.0. Automotive continúa pendiente de licencia.

## Comparación entrenada 2.2.0, selección todavía abierta

El 15 de noviembre de 2026 se autorizó y ejecutó el entrenamiento del build calibrated-20261115-01 con TRAIN. Se compararon baseline, LinearRegression y RandomForest en VALIDATION. El [anexo 42 del Plan V2](PLAN_DE_TRABAJO_V2.md) registra el procedimiento, evidencia y pendientes. Las secciones anteriores conservan el estado histórico de publicación y preparación.

Se completaron 174 ajustes sin fallos: 162 en tres ventanas internas de TRAIN y doce finalistas entrenados con las 2.520 filas de TRAIN. Las métricas externas utilizan las mismas 504 filas de VALIDATION. TEST permanece reservado, sin cargar sus features o targets. Cada pipeline ajustó su preprocesamiento exclusivamente sobre TRAIN.

| Mejor opción por familia | MAE VALIDATION | RMSE VALIDATION | R² VALIDATION |
| --- | --- | --- | --- |
| Baseline del último mes | 12,7480 | 23,4697 | 0,3310 |
| LinearRegression con 14 features | 10,7059 | 17,3132 | 0,6359 |
| RandomForest absoluto con tres lags y calendario | 9,7604 | 17,1857 | 0,6413 |

La candidata de menor MAE tiene 200 árboles, profundidad 4, mínimo de cinco filas por hoja y seed 42. Mejora el MAE del baseline un 23,44 %. Añadir las 17 features no mejoró ese MAE en esta realización sintética. No significa que las variables económicas sean irrelevantes en datos reales. Las predicciones se limitan a cero por una política explícita, sin redondeo para las métricas.

La candidata queda en REVIEW_REQUIRED. Trece productos y 36 combinaciones producto-tienda empeoran frente al baseline, aunque mejoran las medias por tienda y rotación. Son grupos solapados. Falta revisar esos errores antes de aceptar un modelo definitivo. No se selecciona usando TEST ni se modifica el modelo del administrador, que conserva 2.1.0.

Se guardaron doce pipelines con hashes y estados. Su recarga reprodujo las predicciones de VALIDATION con tolerancia absoluta de 1e-12. El [registro 2.2.0](../../ml/demand/reports/v2/2.2.0/calibrated-20261115-01/experiments.csv) contiene 175 entradas, incluido el baseline. Pasaron 40 pruebas del alcance, cinco nuevas. No se alteraron datasets, RAW, curated, modelos anteriores o Neon.

De las trece tareas exclusivas de Ross, diez están completas en el alcance académico aprobado, dos siguen en progreso para 2.2.0 y una corresponde a reposición en H5. Falta adaptar la pantalla al modelo nuevo una vez aceptado y cerrar la validación global. Entrenamiento, aceptación final y defensa son tareas compartidas. Automotive continúa pendiente de licencia, fuera del dataset.

## Diagnóstico completado de los grupos desfavorables 2.2.0

El [anexo 43 del Plan V2](PLAN_DE_TRABAJO_V2.md) registra los trece productos y las 36 combinaciones que empeoran frente al baseline. Se revisaron todas sus observaciones de VALIDATION, las alternativas guardadas y cuatro casos a nivel de árboles. No hubo entrenamiento o acceso a TEST.

El deterioro se concentra en niveles persistentes que el bosque global suaviza, algunas series intermitentes y ventas mayoristas de volumen estable. Hay 70 meses de las 108 observaciones de las combinaciones desfavorables donde las ventas quedan a cinco unidades o menos del último mes. En ese contexto el baseline tiene una ventaja clara. También hay saltos mayoristas que ambos métodos fallan casi por igual. Se comprobaron asociaciones con stock observado, sin convertir datos posteriores al corte en features o atribuir causas comerciales que no están demostradas.

Las alternativas con más variables mejoran algunos productos, pero no solucionan el problema global. El bosque principal mantiene el menor MAE global. Se recomienda conservarlo como candidata, con baseline visible y límites explícitos. Si se autoriza otra comparación antes de fijar, debe probarse una corrección del baseline o una combinación simple definida con los folds de TRAIN. No se debe seleccionar un modelo distinto por producto después de consultar estos errores.

El dataset 2.2.0 ya está construido y validado. No hace falta regenerarlo para cerrar este diagnóstico. Sigue pendiente aceptar y fijar la política, evaluar TEST una sola vez y adaptar la integración administrativa al nuevo artefacto. El administrador conserva 2.1.0. Presentar resultados académicos no equivale a garantizar precisión comercial o afirmar que toda la integración está terminada.

## Cierre vigente 2.2.0 para la presentación H4

El [anexo 44 del Plan V2](PLAN_DE_TRABAJO_V2.md) registra la selección fijada antes de TEST y su evaluación única de 504 filas. El modelo mantiene el mismo artefacto entrenado exclusivamente con TRAIN. No se reajustó con VALIDATION o TEST. El [contrato de inferencia](../../ml/demand/v2/contracts/inference.v2_2.json) conserva versión, features, política y métricas finales vinculadas por hash.

La predicción está conectada al administrador. Permite producto, tienda, mes aprobado y horizonte fijo de un mes. Presenta histórico, baseline, unidades previstas, métricas guardadas, límites y trazabilidad. Rechaza respuestas de versiones anteriores, snapshots incorrectos y solicitudes con features o targets enviados por el cliente. Los permisos se comprueban tanto en API como en menú y ruta. El simulador permanece separado.

Para explicar la demo: “Utilizamos un dataset sintético 2.2.0 construido y validado. Comparamos una regla sencilla, regresión lineal y Random Forest con orden temporal. Aceptamos el bosque antes de evaluar TEST. Su error medio final es aproximadamente 9,20 unidades frente a 12,87 del baseline. La pantalla consulta el modelo guardado, no lo entrena. El resultado apoya una revisión, no garantiza ventas ni autoriza compras. Algunos productos empeoran y los pedidos grandes siguen siendo difíciles”.

Mostrar la sección administrativa, elegir producto y tienda, consultar abril, mayo o junio de 2026, explicar el gráfico y abrir los datos de modelo y snapshot. Aclarar que esas fechas son una reproducción académica. Las métricas pertenecen a la evaluación final guardada, no al error conocido de esa fila. TEST de julio a septiembre no se ofrece como opción del administrador.

El alcance local solicitado está comprobado. La [evidencia técnica](../../ml/demand/reports/v2/integration/admin-2.2-20261115-01/binding.json) contiene 505 pruebas aprobadas de las suites ejecutadas y revisión visual aislada. No equivale a certificar toda la plataforma productiva o cada sesión real sin consultar la base. Reposición y operación comercial definitiva corresponden a H5 o a una ampliación autorizada.

## Corrección de alcance por el audio del docente

La revisión completa del audio confirma que deben probarse cambios de precio con valor actual y nuevo, ver su efecto en la predicción y considerar costo, cotización de compra y tiempos de llegada/reposición. Los mensajes del usuario añaden cantidades, fechas y los controles acordados. El [anexo 46 del Plan V2](PLAN_DE_TRABAJO_V2.md) distingue qué existe y qué falta.

La referencia 2.2.0 sigue conservada y su evaluación es válida para su alcance. Sin embargo, el bosque activo solo usa tres lags y calendario. El generador incluye cambios de precios sin una elasticidad de ventas identificada. Poner más campos en el formulario no arregla esas limitaciones. Deben revisarse primero contrato de escenarios, mecanismos y disponibilidad de cada variable, después diseñar otra realización versionada y validar su uso. No se cambian el dataset, el artefacto o TEST consumido para aparentar cumplimiento.

Se necesitan dos recorridos claramente identificados: consultar un snapshot histórico y comparar un escenario base con cambios hipotéticos. Cada escenario debe registrar precio/costo/cotización con unidad y fecha, cantidades con significado, plazos, disponibilidad y supuestos. El target no se edita como entrada. Las fechas reales futuras no se utilizan en un corte anterior. El modelo no debe prometer un efecto causal que los datos no permiten estimar.

La recuperación local entre 2.2.0 y 2.1.0 ya está implementada y comprobada mediante configuración explícita del servidor, con contratos y snapshots por versión. El README técnico está actualizado. El dashboard funcionó en el fixture local después de aplicar allí las migraciones existentes, sin modificar Neon. Esto cierra esos pendientes técnicos locales, pero no los requisitos interactivos del docente ni la reconciliación productiva.

## Contrato de escenarios y tareas de implementación

El [anexo 47 del Plan V2](PLAN_DE_TRABAJO_V2.md) es la guía vigente de la ampliación interactiva. El [contrato scenarios.v1.json](../../ml/demand/v2/contracts/scenarios.v1.json) define entradas, respuestas, 21 reglas y trazabilidad de lo solicitado. Está documentado y comprobado estructuralmente, pero la nueva API y el motor todavía no están implementados.

Ross tiene a su cargo frontend y dataset: diccionario, fuentes, supuestos, calibración, generador, features, split, validación y publicación, además de controles, gráficos, comparación, reposición visual y pruebas de pantalla. Erika tiene backend y servicio del modelo: validación semántica, snapshots, reglas económicas, motor de escenarios, cálculo de reposición, API, preprocesamiento de entrenamiento, experimentos, inferencia, permisos y recuperación. El plan asigna nueve tareas backend y diez tareas frontend/dataset, con dependencias y entregas. Las revisiones conjuntas no cambian esa propiedad.

La pantalla deberá comparar precio base y nuevo, cotización, costo, cantidades con significado, fechas, plazos y disponibilidad. El servidor resolverá los valores base. Cada cambio indicará si actúa como feature, derivación, validación o reposición. Si un modelo no admite el cambio, debe responder que no lo soporta. Un input editable por sí solo no demuestra que el modelo utilice esa información.

La reposición explicativa entra en H4: requerimiento mensual, stock, reservas, tránsito, compromisos, seguridad, mínimo y múltiplos, con llegada y límites del horizonte. No es una compra ni cambia inventario. Las operaciones automáticas y validación comercial siguen para H5. No se promete cubrir tiempos superiores al horizonte mensual o stockouts diarios con una fórmula mensual.

La referencia 2.2.0 y su TEST quedan intactos. El diseño del dataset siguiente y sus mecanismos económicos deben revisarse antes de autorizar construcción o entrenamiento. Once pruebas del contrato comprueban estructura, sin entrenar o abrir datos. Las reglas semánticas y pruebas funcionales de API y pantalla siguen pendientes de implementación.

## Diccionario ampliado H4-R01

Ross completó el diseño del [diccionario de escenarios](../../ml/demand/v2/contracts/dataset_dictionary.scenarios.v1.json). El [anexo 48 del Plan V2](PLAN_DE_TRABAJO_V2.md) explica sus tipos, unidades, fuentes y disponibilidad. Cubre los 48 campos de entrada, 14 tablas propuestas y una proyección supervisada de 43 campos. Las 16 variables ampliadas son candidatas, no una selección final del modelo.

Se conservan los 24 campos de referencia y el target de ventas brutas observadas. Se separan historia, planes conocidos al corte, resultados posteriores y salidas del modelo. Cantidades, stock, pedidos y reposición no son intercambiables. Los planes de precios usan intervalos temporales, nunca ventas futuras como ponderación. El costo ya puesto no se convierte o recarga otra vez. Los datos reales sin procedencia o fechas certificadas permanecen desconocidos, sin inventar 6.96, 1 o cero.

R01 cierra el diccionario de diseño. R02 y R03 continúan con fuentes y mecanismos. Erika implementará la validación semántica y el pipeline después. No hay otro dataset construido, modelo entrenado o API de escenarios implementada por esta tarea. La referencia 2.2.0 permanece intacta.

## Entrega de Ross para los escenarios ampliados

La entrega vigente se detalla en el [anexo 49 del Plan V2](PLAN_DE_TRABAJO_V2.md). R02 queda cerrado para el alcance sintético académico. El registro de fuentes distingue las aprobaciones posteriores de M5 y Favorita de su bloqueo histórico. Automotive sigue pendiente. Monash aporta una referencia de intermitencia, M5 una referencia de frecuencia de cambios de precio. UCI y Favorita respaldan decisiones de interpretación, pero no se afirma que el generador nuevo haya estimado coeficientes con ellas. La sensibilidad al precio, cotización, costos, stock y plazos son supuestos explícitos, no historia comercial certificada.

Se construyó el dataset 3.0.0, build `scenarios-20261115-02`, con 7.056 filas y 3.528 familias base/hipótesis. Sus 43 campos incluyen 33 candidatas, un target de ventas brutas enteras y controles fuera del modelo. Las cantidades latentes y resultados futuros quedan separados. El calendario simulado nuevo va de octubre de 2026 a septiembre de 2028. TRAIN cubre enero de 2027 a marzo de 2028. VALIDATION cubre abril a junio de 2028. TEST queda reservado de julio a septiembre de 2028, sin evaluación de modelos. El primer build se conserva como respaldo no aprobado por sus marcas de auditoría. 2.2.0 no cambió.

El generador permite comparar cambios de precio sin cambiar el ruido del caso base. Un precio mayor no obliga a una caída en perfiles inelásticos. Una cotización o un costo distinto no fuerza un cambio de ventas sin otro mecanismo. El stock limita ventas atendidas, las reservas posteriores no se venden y solo una recepción dentro del mes incorpora unidades. Los pedidos grandes conservan unidades solicitadas y atendidas por separado. La validación estructural aprobada no acredita respuesta comercial ni sustituye la selección de variables de Erika.

La pantalla administrativa incorpora **Escenarios**, con precios, cotización, costos, cantidades, fechas y reposición. Ya existen controles, validaciones, comparación, tabla, exportación y manejo de nulos. Las pruebas visuales usaron fixtures claramente identificados. La API de capacidades y comparación aún pertenece al trabajo pendiente de Erika. Sin ella no se envían escenarios ni se muestra una predicción inventada. El bosque 2.2.0 mantiene su función de reproducción histórica con cinco variables.

El entrenamiento ampliado no se ejecutó en esta entrega. Corresponde a E04, después del adaptador y la revisión conjunta de reglas. La autorización condicional del usuario permite avanzar cuando esas condiciones estén resueltas. La presentación del avance puede mostrar fuentes, diccionario, nuevo dataset validado y pantalla probada con fixtures. No debe presentarse como una comparación ampliada funcional de extremo a extremo. La evidencia y el estado de cada tarea están en el [traspaso de Ross](../../ml/demand/reports/v2/contracts/ross-scenarios-20261115-01/handoff.json).

La revisión de TRAIN detectó cuatro candidatas constantes, detalladas en el anexo 49. Deben excluirse del ajuste del modelo. Los controles de reposición no necesitan entrar todos al predictor. Los retrasos simulados son planes conocidos, no una estimación de retrasos imprevistos. Los casos ambiguos requieren comprobar las respuestas reales del backend antes de declarar la integración completa.

## Actualización de la interfaz administrativa

El [anexo 50 del Plan V2](PLAN_DE_TRABAJO_V2.md) registra la reparación de disponibilidad del dashboard y la simplificación visual de predicciones. Consulta histórica y escenarios aparecen separados. El origen sintético sigue visible, mientras que ayudas, límites y trazabilidad quedan desplegables. Los formularios de escenarios se ocultan cuando su servicio no está habilitado. Esto no implementa la API ampliada ni convierte el modelo 2.2.0 en un modelo de precios.

La reconciliación de Neon terminó el 15 de noviembre de 2026, después del ensayo aislado, la aprobación de conservar quality como LEGACY, el respaldo persistente y la revalidación productiva. Las diez migraciones están aplicadas. El dashboard devuelve ventas disponibles para los tres roles. Pasaron 58 comprobaciones en ensayo y 46 lecturas posteriores en producción. Se conservan dos diferencias LEGACY conocidas, sin ejecutar el SQL de limpieza del diff. La evidencia está en el [reporte de reconciliación](../../ml/demand/reports/v2/closure/neon-reconcile-20261115-01/review.json). La revisión visual anterior fue con fixtures. La API y el modelo de escenarios ampliados siguen pendientes, por lo que este cierre no acredita todo H4 al 100 %.

## Estado vigente: escenarios funcionales con dataset 3.0.0

La continuación autorizada completó el backend necesario y conectó la pantalla de Ross con el modelo ampliado. El [anexo 51 del Plan V2](PLAN_DE_TRABAJO_V2.md) reúne tareas, comparación de modelos, evaluación final, pruebas y límites. Sus resultados reemplazan el estado pendiente de la entrega inicial de escenarios, conservada en las secciones anteriores como historia.

El dataset sintético 3.0.0 se conservó sin modificaciones. Se entrenó exclusivamente con TRAIN, se eligió el bosque con error absoluto mediante VALIDATION y se fijó antes de evaluar TEST una sola vez. Su MAE final fue 10,16 unidades frente a 15,57 del baseline. R² fue 0,4507, no un porcentaje de precisión. Se abstuvo en seis de las 1.008 filas por estar fuera del rango de entrenamiento. Las métricas no certifican ventas futuras reales de la empresa.

La pestaña Escenarios utiliza el modelo 3.0.0. Consulta histórica conserva 2.2.0, con su TEST anterior intacto. El simulador Streamlit continúa separado. Escenarios permite precios con fecha de vigencia, cantidades por modalidad, cotización, costos, stock vendible, reservas, pedidos, entregas y reposición. Los precios y la historia base llegan del servidor. El backend valida cada cambio, calcula las entradas derivadas y explica su papel. No todo campo debe entrar directamente al modelo. Cotización y costo se usan para compras hipotéticas y coherencia económica. El plazo de proveedor participa en reposición.

Para demostrarlo, iniciar backend y frontend con los comandos normales del proyecto. Entrar como ADMIN y actualizar la página. Abrir Predicción de ventas, elegir Escenarios y comprobar la etiqueta V3.0.0. Se puede usar Farola Delantera Derecha, Tienda 1, abril de 2028. Activar Precios, cambiar por menor de 120 a 150, por mayor de 102 a 127,5, utilizando punto decimal al escribir. Mantener vigencia al primero de abril. Comparar muestra 22,52 unidades base frente a 22,405 con cambios. Es un ejemplo ilustrativo tomado de entradas de VALIDATION, no una prueba de exactitud comercial. Activar reposición con seguridad cinco muestra sus componentes. No es necesario entrenar para abrir la pantalla.

El dashboard permite consultar meses con actividad sin introducir datos nuevos. Septiembre de 2026 permite mostrar historia existente. El filtro de ubicación respeta permisos, mientras que el inventario se identifica como actual. Los totales se contrastaron con Neon exclusivamente en READ ONLY.

Pasaron 526 pruebas y las dos compilaciones. La revisión visual integrada utilizó la API y el modelo reales con una sesión local de prueba, en escritorio y celular. No equivale a un ensayo personal del equipo. El [reporte de cierre](../../ml/demand/reports/v2/closure/scenario-integration-20261115-01/review.json) conserva capturas y verificaciones. Las tareas técnicas de este alcance están completadas localmente. Antes de exponer corresponde que ambos integrantes recorran la demo en su sesión. H5 mantiene las operaciones comerciales y el seguimiento con datos reales. No se presenta la plataforma completa o su precisión como garantizada al 100 %.


## Verificación en la sesión ADMIN de Ross, 16 de noviembre de 2026

Se completó el recorrido en Brave con la sesión real del usuario, sin sustituirla por una sesión de prueba. La recarga del navegador conservó ADMIN y recuperó el dashboard. La consulta histórica 2.2.0 respondió. Escenarios cargó las capacidades y referencias 3.0.0. Se verificaron cambios de producto y tienda, cantidades por modalidad, precios con vigencia, cotización con fecha, costo, stock, un pedido por mayor de diez unidades con dos reservadas, entregas y reposición.

El ejemplo de Depósito de Expansión, Tienda 3, abril de 2028, produjo 27,57 unidades tanto en la base como en la hipótesis. La pantalla explicó que el modelo puede mantener su estimación pese a cambios válidos. Al reducir el plazo del proveedor de 35 a siete días, con dos días internos, la reposición pasó de fuera del horizonte a estimación mensual. Mostró 33 unidades requeridas, 175 de posición disponible y cero sugeridas. Las 150 unidades previstas en tránsito se distinguieron del stock físico. La llegada calculada del nuevo pedido fue el 10 de abril, en America/La_Paz. Son hipótesis sintéticas, no cambios comerciales ni una nueva evaluación del modelo.

El precio por mayor de 800 frente a 750 por menor fue rechazado. El resultado anterior se retiró. Tras restaurar 637,5, la comparación volvió a responder. Se corrigió un aviso inicial prematuro de indisponibilidad para mostrar carga mientras se reciben las capacidades. Una prueba nueva cubre esa transición.

Pasaron las 278 pruebas frontend y su compilación con TypeScript. Las 184 pruebas backend y 68 de Python del cierre anterior siguen como evidencia previa, no como suites repetidas en esta revisión. Los 199 archivos protegidos conservaron sus hashes. No se modificó Neon, datasets, RAW o modelos. No se entrenó ni se repitió TEST.

Exportar abrió el diálogo de guardado JSON de Brave. La herramienta no consiguió dirigir entradas a ese diálogo nativo, por lo que se canceló. Se comprobó la generación del Blob en las pruebas automatizadas, pero no se afirma haber guardado esa descarga en el recorrido manual. Las capturas y el registro están en `ml/demand/reports/v2/closure/scenario-integration-20261115-01/actual-admin-walkthrough-20261116.json`, desde la raíz del proyecto. Esta revisión sustituye únicamente el pendiente de comprobación en la sesión personal. El ensayo conjunto del equipo y la aceptación del docente conservan su función propia.


La ampliación visual del 16 de noviembre de 2026 incorpora una serie de demostración de enero a octubre de 2026, calculada en memoria mediante `frontend/src/services/demonstrationHistory.ts`, versión `display-history-2026-v1`, semilla 42. Usa las referencias de producto y tienda seleccionadas para obtener ejemplos reproducibles de rotación, tendencia moderada, estacionalidad, ruido y meses con cero. Sus importes no representan historia comercial ni pronósticos del artefacto. No se extraen del dataset entrenado ni se envían a inferencia, ordenamiento por ventas o reposición. El botón «Historial del modelo» conserva por separado los tres meses del snapshot de 2028 y el pronóstico autorizado de un mes. La demostración no altera el periodo aprobado del modelo ni amplía su horizonte.

Pasaron 288 pruebas frontend y la compilación. Se comprobó visualmente la curva de diez meses con el arnés local de prueba. No se afirma una nueva revisión de la sesión personal ADMIN. Los 203 archivos protegidos comparados, incluidos datasets, modelos y reportes de la versión fijada, conservaron sus hashes. No se utilizó Neon, entrenamiento o una nueva evaluación de TEST. La evidencia de esta ampliación está en `ml/demand/tmp/demo-october-2026-check.json` y su captura en `ml/demand/tmp/demo-october-2026-visual.png`.


La revisión de coherencia del 16 de noviembre de 2026 reemplaza el selector interno que mezclaba la demostración de 2026 con la inferencia de 2028. El acceso normal abre «Explorar ventas», donde producto, tienda y mes corresponden exclusivamente a los ejemplos de enero a octubre de 2026. Cambiar el mes limita la curva a ese periodo, actualiza las unidades del mes y el acumulado. La búsqueda y el orden por ventas usan esa misma tienda y mes. No se llama a inferencia desde este recorrido.

«Predecir y comparar» conserva el modelo 3.0.0 con sus meses aprobados de abril a junio de 2028. Muestra solo su historia de entrada y los pronósticos del modelo. Los datos ilustrativos de 2026 no entran en sus controles, cálculos, gráfica o peticiones. La consulta 2.2.0 permanece en «Versiones anteriores». Incorporar octubre de 2026 como mes predictivo requeriría otras entradas aprobadas. No se simula ese soporte cambiando fechas del experimento.

Se comprobaron las 168 combinaciones aprobadas de 56 productos por tres tiendas, con diez meses, enteros no negativos, reproducibilidad y suma de modalidades. Los 1.680 puntos son ilustraciones calculadas en memoria, no filas añadidas al dataset publicado. Pasaron 292 pruebas frontend y la compilación. La tabla de cambios se oculta cuando está vacía y sus detalles se despliegan a pedido. El contenedor administrativo limita el desplazamiento a su área de contenido. La revisión visual local con fixtures confirmó el fin de la página sin el espacio desplazable excesivo. No equivale a una nueva prueba de la sesión personal del usuario.

Los 203 archivos protegidos comparados conservaron sus hashes. No hubo entrenamiento, evaluación de TEST, cambios de dataset, modelos, RAW, Prisma o Neon. No se crearon Markdown. El registro de esta revisión está en `ml/demand/tmp/ux-coherence-review.json`.
