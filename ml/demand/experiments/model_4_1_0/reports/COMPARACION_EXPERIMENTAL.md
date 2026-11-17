# Comparación experimental 4.1.0 · exploratorio-01

**Dictamen para la defensa:** conservar Random Forest 4.0.0. Los cuatro candidatos quedan `EXPERIMENTAL_NOT_ACTIVE`. Cada candidato mejoró los baselines de esta cohorte, pero quedó por detrás de 4.0.0 en MAE en ambas comparaciones pareadas. Hay margen para investigar el error cuadrático en otra cohorte. La evidencia disponible no justifica un reemplazo.

## Datos y protocolo

El build sintético `calendar-20261116-01` proporcionó 5.040 filas TRAIN (febrero de 2025 a abril de 2026, 2.520 familias) y 1.008 filas VALIDATION (mayo a julio de 2026, 504 familias), correspondientes a 56 productos y tres tiendas. El objetivo fue `target_ventas_mes`, ventas observadas en el simulador. Se conservaron las 19 características en el orden oficial. El lector limita los registros por realización y fecha, comprueba corte, calidad, identidad y agrupación y excluye TEST y DEMO de las matrices. El CSV contenedor se verificó por SHA256.

La procedencia temporal de cada feature se apoya en el build publicado. El experimento comprueba el corte de cada fila y no reconstruye las fuentes del generador. Los lags y planes proceden del conjunto autorizado al corte. Los imputadores y el codificador se ajustaron solo en TRAIN, con peso total uno por familia. Los resultados descriptivos dan el mismo peso a cada fila, como el reporte oficial. Las dos variantes de una familia comparten historia y no son observaciones independientes.

VALIDATION ya intervino en la selección de 4.0.0. M41-02 y M41-03 documentan la falta de una cohorte independiente elegible y noviembre DEMO carece de objetivo. Los builds 3.0.0 quedan fuera por falta de autorización y compatibilidad verificada para este propósito. TEST oficial (agosto a octubre de 2026) quedó excluido de ajuste, selección y evaluación.

La [configuración fijada antes del ajuste](../configs/protocolo.json) registra parámetros y huellas. La ejecución utilizó semilla 42, Python 3.11.0, scikit-learn 1.9.1, NumPy 2.4.6, pandas 3.1.0 y joblib 1.6.0. Se comparó MAE como criterio primario, con RMSE, R², error firmado y cobertura como complementos. La referencia se calculó en la misma VALIDATION cargando el artefacto congelado tras verificar el hash binario contra el release fijado.

## Candidatos

| Candidato | Configuración |
| --- | --- |
| Random Forest alternativo | 128 árboles, error cuadrático, profundidad 18, mínimo 3 por hoja, fracción de variables 0.75 |
| HistGradientBoosting | 140 iteraciones fijas, tasa 0.07, 23 hojas, mínimo 24 por hoja y regularización L2 de 1 |
| Hurdle | HistGradientBoosting para probabilidad de venta y magnitud condicional positiva en filas TRAIN con algún lag cero. El producto de ambas estimaciones se aplica en ese segmento. En filas con tres lags positivos se usa el Hist general. |
| Híbrido | 75 % del Hist entrenado y 25 % de lag1. La mezcla se fijó antes de evaluar. |

Lag1 usó el mes anterior y MA3 los tres lags consecutivos al corte, incluidos ceros observados. Se revisó M41-04. SBA, TSB y estacional ingenuo quedaron fuera de esta corrida acotada y el experimento evita extender artificialmente los tres lags para aplicarlos.

## VALIDATION completa · comparación de estimadores

Las 1.008 filas recibieron un valor numérico de cada estimador offline (100 % de cobertura de cálculo). Esta tabla reproduce el criterio de VALIDATION documentado y omite la puerta operativa de rango. La tabla siguiente aplica esa puerta.

| Método | MAE | RMSE | R² | MAE intermitente, n=584 | MAE con tres lags cero, n=186 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Random Forest 4.0.0 | 11.51679 | 20.34831 | 0.58830 | 12.78362 | 8.62575 |
| Lag1 | 19.40675 | 36.05169 | -0.29233 | 20.67979 | 11.78495 |
| MA3 | 17.22156 | 30.81106 | 0.05608 | 17.63413 | 11.78495 |
| RF alternativo | 12.57483 | 20.18484 | 0.59489 | 13.31666 | 12.02693 |
| HistGradientBoosting | 12.57307 | 20.06586 | 0.59965 | 13.29265 | 12.29597 |
| Hurdle | 12.83233 | 20.59043 | 0.57845 | 13.36917 | 13.46072 |
| Híbrido | 13.19901 | 21.65287 | 0.53382 | 14.09423 | 11.22290 |

Demanda intermitente aquí significa que los tres lags mezclan ceros y positivos. La etiqueta solo describe la historia disponible al corte. En datos sintéticos, un cero observado puede coincidir con falta de stock.

## VALIDATION con política de rango de 4.0.0

Los mismos **995 casos de 1.008** entraron en cada comparación. Los **13 excluidos** equivalen a una cobertura común del **98.71 %** y corresponden a abstenciones por rango bajo esa política. Los candidatos evalúan esa máscara de referencia, sin política propia de activación.

| Método | MAE | RMSE | R² |
| --- | ---: | ---: | ---: |
| Random Forest 4.0.0 | 11.37442 | 20.28180 | 0.58308 |
| Lag1 | 19.22010 | 35.79526 | -0.29864 |
| MA3 | 16.85360 | 30.45306 | 0.06006 |
| RF alternativo | 12.47073 | 20.15818 | 0.58815 |
| HistGradientBoosting | 12.50472 | 20.03351 | 0.59323 |
| Hurdle | 12.74930 | 20.54293 | 0.57228 |
| Híbrido | 13.11194 | 21.64712 | 0.52506 |

El [registro de evaluación](../evaluation/exploratorio-01.json) incluye MAE, RMSE, R², error firmado y denominadores por producto, tienda, mes y patrón de lags para cada método y cohorte. Los descensos de RMSE de Hist y del RF alternativo son descriptivos y se acompañaron de un MAE mayor. El hurdle no redujo el MAE en el segmento intermitente frente a 4.0.0.

En VALIDATION completa, el MAE de 4.0.0 fue menor que el de Hist y el RF alternativo en cada tienda. Para las ubicaciones 5, 6 y 7, los valores de 4.0.0 fueron 12.227, 10.764 y 11.559, frente a 13.163, 12.491 y 12.065 de Hist. En el desglose por producto, Hist, RF alternativo y hurdle mejoraron individualmente en 17 de 56 productos cada uno. El híbrido mejoró en 15. Estos conteos no establecen superioridad en esos productos.

## Verificación

Terminó la ejecución exploratoria y se recargaron los cuatro paquetes con verificación de huella. Cada uno reprodujo su MAE registrado y emitió valores finitos y no negativos. Pasaron las comprobaciones de particiones, separación de familias, exclusión de una fila sintética marcada TEST con objetivo inválido, R² indefinido para objetivos constantes y sumas de denominadores por grupo. La referencia 4.0.0 reprodujo el MAE guardado de VALIDATION al redondear a cuatro decimales.

## Límites y siguiente decisión

- La reutilización de VALIDATION y la correlación entre variantes impiden usar el ranking como confirmación independiente. Las cifras por producto se basan en muestras pequeñas y los datos sintéticos pueden favorecer mecanismos del generador.
- **GO para continuar la investigación** si se registra una cohorte independiente con objetivo cerrado y entradas disponibles al corte. Fijar el protocolo de comparación pareada y sus grupos antes de evaluar esa reserva.
- **NO-GO para promoción o sustitución.** Presentar 4.0.0 como versión oficial en la defensa. Si se muestran cifras 4.1.0, etiquetarlas como exploratorias de VALIDATION.

Los artefactos y hashes de los cuatro candidatos figuran en el registro de evaluación. El modelo oficial mantuvo SHA256 `8d73bbfb769e432461f2a202e37842b47820a76627e46be3e4ba412e64562e1e`. La huella agregada de los 554 archivos protegidos de datos, modelos, reportes y contratos permaneció en `4d5098398a45d8c3879ba08aad7dbc08c3c7696740a5cbbb6fa5e7268991fc27`.
