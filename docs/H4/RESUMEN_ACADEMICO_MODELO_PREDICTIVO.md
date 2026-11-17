# Resumen académico del modelo predictivo H4

## 1. Descripción del módulo

RepuestoPro incorpora un módulo que estima ventas mensuales de repuestos por producto y tienda. El panel permite comparar un estado base con hipótesis de inventario, precios y logística. La predicción expresa unidades que se espera vender bajo los supuestos de abastecimiento del escenario. La reposición usa esa cifra junto con stock, reservas, compromisos y entregas elegibles para obtener una sugerencia explicativa.

## 2. Metodología

Se generó un calendario sintético reproducible a partir de un catálogo congelado de 56 productos y tres tiendas. El build 4.0.0 contiene 14.112 filas supervisadas. Se asignaron 5.040 a TRAIN (febrero de 2025 a abril de 2026), 1.008 a VALIDATION (mayo a julio de 2026), 1.008 a TEST (agosto a octubre de 2026) y 7.056 a la realización DEMO. Las variantes de una familia se mantuvieron juntas. El próximo pronóstico publicado usa noviembre de 2026, con 168 snapshots DEMO sin objetivo conocido. [Guía y alcance del dataset](H4_IMPLEMENTACION_MODELO_PREDICTIVO.md)

## 3. Preparación de datos

Se validaron los meses cerrados, la correspondencia producto–tienda y la disponibilidad de entradas al inicio del mes objetivo. Se construyeron tres rezagos con ventas de los meses anteriores y se combinaron con calendario, información histórica de stock y planes conocidos. El preprocesamiento se ajustó con TRAIN. Aplicó imputación mediana con indicadores de faltantes y codificación de categoría. La demanda latente, las recepciones realizadas después del corte y el resultado del mes objetivo quedaron fuera de las variables predictoras.

## 4. Entrenamiento

El modelo seleccionado es un Random Forest de 100 árboles con criterio de error absoluto, profundidad máxima 14, mínimo cuatro observaciones por hoja, fracción de características 0.90 y semilla 42. Durante el ajuste cada familia representó un peso total de uno. Se compararon Lag1, regresión lineal y bosques con error cuadrático y absoluto. La variante de error absoluto se seleccionó por su menor MAE de VALIDATION y se congeló como `calendar-model-20261116-01`. [Registro de selección](../../ml/demand/reports/v2/4.0.0/calendar-model-20261116-01/experiments.csv)

## 5. Evaluación

| Partición | Método | MAE | RMSE | R² |
| --- | --- | ---: | ---: | ---: |
| VALIDATION | Random Forest | 11.5168 | 20.3483 | 0.5883 |
| VALIDATION | Lag1 | 19.4067 | 36.0517 | −0.2923 |
| TEST guardado | Random Forest | 10.2010 | 18.4046 | 0.6201 |
| TEST guardado | Lag1 | 17.3581 | 33.0549 | −0.2256 |

TEST se evaluó una vez tras fijar el estimador. El MAE de 10.2010 representa un error absoluto promedio de unas 10.2 unidades. RMSE enfatiza errores grandes y R² mide desempeño cuadrático relativo a una referencia basada en la media. La cobertura de servicio fue 1.002/1.008, con seis abstenciones, y se registró por separado de las métricas del estimador. [Evaluación oficial guardada](../../ml/demand/reports/v2/4.0.0/calendar-model-20261116-01/test-evaluation.json)

## 6. Integración

El panel React y TypeScript consulta una API Express que valida identidad, permisos y contrato. Python ejecuta el pipeline congelado sobre los snapshots. El panel presenta BASE, hipótesis, diferencias, impactos, advertencias, reposición y exportación. La recuperación idempotente conserva la respuesta original y su fecha. Las cabeceras del runtime permiten distinguir una entrega nueva de una recuperada. Cuando una entrada excede el dominio o no existe historia utilizable, el flujo comunica la indisponibilidad o abstención según el caso. Las simulaciones carecen de efectos comerciales. [Ensayo técnico J02B](H4_J02B_CONTINUACION_ACEPTACION.md)

## 7. Resultados

4.0.0 obtuvo menor MAE que Lag1 en 50 de los 56 productos del TEST sintético. En noviembre DEMO emitió 136 de 168 pronósticos. Los cuatro candidatos 4.1.0 quedaron por encima del MAE del release en VALIDATION. En 4.1.1, D bajó el MAE promedio interno de 11.8022 a 11.6559, con mayor RMSE y peor resultado en el grupo de alta variabilidad. Quedó experimental. Para Tensador de Correa, Tienda 2, noviembre DEMO, el comparador muestra 87.17 unidades en 4.0.0 y 80.02 en D. La cifra observada de referencia está ausente.

## 8. Limitaciones

Los datos son sintéticos y las ventas observadas dependen del stock. Los resultados describen este calendario, sus productos y sus condiciones simuladas. Las muestras por producto son limitadas y las variantes de una familia están correlacionadas. Los candidatos carecen de una cohorte nueva e independiente y el proyecto carece de evidencia suficiente para declarar cobertura predictiva calibrada del 95 %. La aceptación personal de H4-J02 sigue pendiente.

## 9. Conclusiones

La evidencia académica respalda mantener 4.0.0 como referente para la demostración. La mejora interna de D motiva una investigación con una reserva futura autorizada, observados cerrados y entradas verificadas al corte. La adopción de otro artefacto requiere acordar de antemano los grupos críticos, la cobertura, el desempeño frente a Lag1 y las condiciones de promoción. [Informe técnico y trazabilidad](INFORME_TECNICO_COMPLETO_MODELO_PREDICTIVO.md)
