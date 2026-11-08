# H4. Fallas posibles y dataset con casos positivos, negativos y grises

Fecha: 3 de noviembre de 2026. Alcance: revisión de riesgos y primera generación local de datos sintéticos. No se entrenó ningún modelo.

La [auditoría posterior de cobertura y preparación](H4_AUDITORIA_COBERTURA_Y_PREPARACION_ENTRENAMIENTO.md) distingue los controles aprobados de los casos que todavía solo tienen una descripción conceptual. Su dictamen precisa el alcance de la validación inicial registrada aquí.

## Qué se revisó y qué cambió

La [Fase 1](H4_FASE1_ESTRUCTURA_DATASET_Y_RIESGOS.md) ya describía 30 escenarios de riesgo. Eso no significaba que estuvieran resueltos en código ni representados en un dataset. Al comenzar esta revisión no se encontró un dataset de demanda generado, solo su estructura propuesta. Por eso esta es la primera generación local basada en esa propuesta, no la sustitución de un archivo previo.

La nueva solicitud permite avanzar desde la definición documental hasta generar datos de prueba. Se conservan el problema de regresión, las nueve columnas propuestas, la seed 42 y el horizonte de un mes. No se implementa inferencia, integración con pantallas ni entrenamiento. Los archivos de búsqueda por imagen pertenecen a otro problema y no se modificaron.

Se interpreta positivos como casos válidos normales, negativos como situaciones adversas o entradas incorrectas, y grises como situaciones cuya interpretación necesita información adicional. Estas etiquetas describen pruebas, no clases que el modelo de demanda deba predecir. El target sigue siendo una cantidad numérica de ventas brutas.

## Positivos, negativos y grises

| Grupo | Ejemplo | Tratamiento aplicado |
|---|---|---|
| POSITIVO | Venta mensual habitual con ruido, tendencia y estacionalidad moderada | Incluido en el panel válido |
| NEGATIVO válido | Caída confirmada, pico, venta mayorista grande, cero real simulado o serie constante | Incluido en el panel válido, conservando cantidades no negativas |
| NEGATIVO_INVALIDO | Cantidad negativa, producto inexistente, almacén usado como tienda, target faltante o lag incorrecto | Archivo separado. El validador debe rechazarlo |
| GRIS | Cero con falta de stock, captura incompleta, producto nuevo o procedencia dudosa | Archivo separado con respuesta esperada. No se inventa demanda real ni se utiliza para entrenamiento |

Una situación negativa no obliga a poner una venta de -5 unidades en el entrenamiento. Las cantidades negativas solo aparecen como entradas deliberadamente incorrectas para probar el rechazo. Las devoluciones tampoco convierten el target bruto en ventas negativas. Los casos grises no se rellenan con ceros para completar una tabla.

## Fallas que podrían aparecer durante la implementación

La tabla distingue lo representado en los datos de lo que todavía necesita una solución de aplicación. Una prueba del generador no demuestra que la API o la pantalla manejen el escenario.

| Riesgo | Efecto posible | Cobertura actual y pendiente |
|---|---|---|
| Cero por falta de stock | Confundir ventas observadas con demanda perdida | Caso gris SIN_STOCK. No se estima demanda perdida ni se inventa una historia de inventario |
| Mes incompleto o caída de captura | Entrenar con un total parcial como si fuera definitivo | Caso gris CAPTURA_INCOMPLETA y rechazo de target desconocido. Falta un cierre comercial verificable |
| Producto, tienda o combinación nueva | No disponer de tres meses anteriores | Casos grises sin historia. Falta implementar la respuesta de historial insuficiente en una futura API |
| Producto descontinuado | Recomendar reponer algo retirado | Caso gris DESCATALOGACION_DUDOSA. Prisma no define una historia completa de vigencia comercial |
| Venta mayorista extraordinaria válida | Borrar un pico útil al tratarlo como error | Se simulan pedidos adicionales de 20 a 40 unidades. No se eliminan automáticamente |
| Devolución registrada después | Filtrar futuro hacia una etiqueta histórica | Caso gris DEVOLUCION_TARDIA. Se conserva el target bruto, sin restas retroactivas |
| Promoción o sustitución no documentada | Atribuir cambios de ventas a un patrón inexistente | Casos grises separados. No se finge que existe una historia de campañas o equivalencias |
| Cambios permanentes de mercado | El modelo deja de representar la situación actual | Las caídas y picos simulados son temporales. No se afirma haber cubierto todos los cambios de régimen. Se necesitarán escenarios adicionales y seguimiento real |
| Duplicados o uniones de uno a muchos | Multiplicar cantidades al unir ventas, pagos o devoluciones | Se rechazan claves duplicadas del panel. La futura extracción real deberá agregar cada fuente por separado |
| ID correcto en una base, incorrecto en otra | Asociar ventas con otro catálogo | Referencia congelada de IDs. Antes de usarla en otro entorno hay que verificar identidad comercial y versión |
| Cantidad en cajas frente a unidades sueltas | Sumar magnitudes comerciales diferentes | No se encontró una unidad de medida explícita en el contrato revisado. No se simulan conversiones. Hace falta una regla comercial antes de mezclar fuentes |
| Precio actual usado como histórico | Introducir información posterior o explicar falsamente la demanda | Precios y costos excluidos del panel. No se reconstruye modo mayorista comparando tarifas actuales |
| Cambio de fecha o carga retroactiva | Evaluar con registros que aún no se conocían | Caso gris CARGA_RETROACTIVA. Falta conservar cortes de disponibilidad en una extracción real |
| Desfase entre UTC y La Paz | Asignar una venta al mes equivocado | Los meses sintéticos son etiquetas de negocio. Una futura extracción deberá convertir America/La_Paz antes de agrupar |
| Uso de etiquetas del generador como features | El modelo conoce la fórmula de la respuesta | Escenario, rotación y clase quedan en un archivo de metadatos separado de las nueve columnas |
| Comparar repetidamente usando test | Elegir una configuración adaptada a la evaluación final | Cortes cronológicos definidos, pero ningún modelo evaluado. El protocolo deberá respetarse al entrenar |
| Buen MAE global, mal resultado en una tienda o baja rotación | Ocultar fallas relevantes para reposición | Informe descriptivo por producto y tienda. Las métricas predictivas y los criterios de aceptación todavía están pendientes |
| R² sobre series constantes | Interpretar una métrica poco útil como precisión | Se conservan dos series constantes y dos completamente cero como pruebas difíciles. No se calcula R² durante esta generación |
| Una predicción negativa o no finita | Mostrar cantidades imposibles | Las entradas se validan. El tratamiento de salidas del modelo queda pendiente porque todavía no hay modelo |
| Dataset demasiado fácil o favorable a un algoritmo | Métricas altas sin utilidad comercial | Ruido, ceros y eventos variados, sin entrenamiento ni selección de parámetros por resultados. Sigue existiendo el límite de aprender una simulación |
| Catálogo desactualizado | Usar productos cuya vigencia cambió | Se declara el corte del 27 de octubre. No se presenta como una lectura nueva del 3 de noviembre |
| Pronóstico para una fecha ya pasada | Presentar una demostración histórica como pronóstico comercial actual | El periodo simulado termina en septiembre de 2026. No se presenta como una predicción real para noviembre o diciembre |
| Cambios de schema, unidades o reglas después del entrenamiento | Reutilizar un artefacto incompatible | Se guardan versiones y hashes. Sigue pendiente verificar compatibilidad cuando exista un modelo |
| Falta de umbrales de negocio para aceptar el modelo | Elegir por una mejora pequeña sin valor práctico | No se inventa un MAE aceptable. El equipo deberá acordarlo por rotación y costo del error antes de seleccionar modelo |

Las unidades comerciales, la portabilidad de IDs, la fecha efectiva de la demostración y la falta de umbrales de aceptación no estaban desarrolladas de forma suficiente en la propuesta anterior. Se agregan aquí. Otros riesgos ya estaban identificados, pero siguen pendientes de una solución operativa. No se declara que todos estén implementados.

## Dataset construido

Se utilizó una referencia mínima del catálogo registrado en el documento de Fase 1. Incluye los 62 IDs leídos entonces, pero la generación usa solamente los 56 candidatos con IDs 1 a 56 y las tiendas 5, 6 y 7. Los productos 57 a 62 continúan reservados por las dudas documentadas. No se consultó ni modificó Neon en esta tarea.

La referencia contiene id, itemCode, name y categoryId, además de las ubicaciones. No usa atributos de vehículo, precios ni personas. Esta selección mínima es una precisión respecto al snapshot más amplio que se había propuesto. Conservar un producto del catálogo no certifica su historia comercial. Tampoco implica que todas las tiendas lo vendieran desde 2024. El panel completo es un supuesto de simulación.

| Archivo dentro de ml/demand/data/escenarios_v1 | Contenido |
|---|---|
| base_mensual.csv | 4.032 observaciones mensuales de octubre de 2024 a septiembre de 2026 |
| dataset_supervisado.csv | 3.528 filas con los tres lags, calendario y target de enero de 2025 a septiembre de 2026 |
| escenarios_metadatos.csv | Identidad, escenario, clase, rotación simulada y conjunto. Sirve para revisar cobertura, nunca se concatena a las features |
| casos_invalidos.json | 15 pruebas negativas deliberadamente incorrectas con el error esperado |
| casos_grises.json | 10 situaciones ambiguas con respuesta esperada, origen sintético y apto_entrenamiento false |
| validacion.json | Distribución de cantidades, resumen por producto y tienda, escenarios y comprobaciones |
| manifest.json | Origen, seed, versiones, fecha, parámetros, referencia del catálogo y hashes |

La base mensual contiene 2.897 casos positivos y 1.135 casos adversos válidos. Estas cantidades corresponden a las 4.032 observaciones base, no a las filas supervisadas. Los 10 grises y los 15 inválidos son pruebas separadas, no observaciones agregadas al entrenamiento.

El panel supervisado tiene estas nueve columnas: mes_objetivo, productId, locationId, ventas_mes_anterior, ventas_hace_2_meses, ventas_hace_3_meses, mes_sin, mes_cos y target_ventas_mes. Los IDs siguen siendo identificadores. El mes es conocido de antemano. La etiqueta del escenario y los parámetros que produjeron las cantidades no entran al modelo.

Se conservan los cortes previstos: TRAIN enero de 2025 a marzo de 2026 con 2.520 filas, VALIDATION abril a junio de 2026 con 504 y TEST julio a septiembre de 2026 con 504. Cada mes permanece completo. Son asignaciones temporales, no modelos ya entrenados ni matrices normalizadas.

El target sintético supervisado tiene mínimo 0, máximo 69, mediana 7 y 422 ceros. Son estadísticas del archivo generado, no resultados predictivos. La estacionalidad moderada, tendencia, diferencias entre tiendas y ruido son supuestos. No se utilizaron cantidades de ventas comerciales para calibrarlos. Las series especiales y los eventos difíciles no se colocaron exclusivamente en test.

## Reproducción y comprobaciones

Desde la raíz del proyecto, con Python disponible:

```text
python ml/demand/generate_synthetic.py
python -m unittest discover -s ml/demand -p "test_*.py" -v
```

El generador no necesita dependencias externas, credenciales ni acceso a bases de datos. El argumento --output permite generar en otra carpeta. Se niega a sobrescribir artefactos diferentes en el mismo destino. Dos ejecuciones con los mismos insumos y versión de Python producen archivos de datos y hashes iguales. La hora real del manifiesto puede cambiar y no forma parte del hash del CSV.

Se aprobaron siete pruebas locales. Cubren panel completo, fechas y split, cantidades válidas adversas, quince errores deliberados, meses ausentes, duplicados, dependencias de lags y reproducibilidad. Se comprobó que cambiar un target posterior no altera los lags anteriores. Los grises quedan fuera del archivo supervisado. La primera ejecución de la prueba temporal falló por permisos de Windows y la ejecución con acceso a la carpeta temporal aprobó las siete.

No se ejecutó baseline, LinearRegression, Random Forest o MLP. Los archivos solo permiten preparar esas etapas más adelante. Falta evaluar los modelos, fijar umbrales de negocio e implementar respuestas reales para casos grises. Los datos sintéticos no validan por sí solos la utilidad comercial de la propuesta.
