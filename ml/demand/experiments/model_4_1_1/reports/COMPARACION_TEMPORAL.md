# Random Forest 4.1.1 · Evaluación temporal interna

**Dictamen para la defensa:** mantener Random Forest 4.0.0. La variante D se guardó como candidato experimental sin activar. Redujo el MAE promedio del bosque de referencia por fold en **0.1463 unidades (1.24 %)**. Mejoró en dos de tres folds, empeoró el RMSE y el MAE del grupo de alta variabilidad y presentó mayor dispersión entre folds.

## Diagnóstico y datos

4.0.0 pronostica ventas mensuales observadas en el simulador. Su bosque de error absoluto usa 100 árboles, profundidad 14, mínimo cuatro muestras por hoja y fracción 0.90 de características. Las 19 entradas ya incluyen tres lags, calendario seno/coseno, stock vendible al corte, días sin stock del mes anterior, reservas y planes conocidos de precio, pedidos y entregas. En 4.1.0, Hist y el RF alternativo redujeron RMSE en VALIDATION histórica, pero empeoraron el MAE agregado y el de cada tienda frente a 4.0.0. El hurdle tampoco mejoró el MAE del segmento intermitente. El nuevo ensayo conserva el criterio de error absoluto y aísla el efecto de regularización y resúmenes de rezagos.

Se verificaron SHA256 del manifiesto temporal, tabla supervisada, historial cerrado y tabla de resultados. El cargador admite exclusivamente las 5.040 filas TRAIN, febrero de 2025 a abril de 2026. Se verificaron para cada lag su producto, tienda, escenario, snapshot, mes exacto, cierre, disponibilidad al corte e igualdad con la cantidad publicada. Las etiquetas se contrastaron con el resultado cerrado y solo entraron en el ajuste si estaban disponibles al comienzo del primer mes del bloque evaluado. No se usaron demanda latente, ventas del mes objetivo, recepciones realizadas ni stock posterior como predictores.

Se derivaron únicamente media, desviación estándar poblacional y proporción de ceros de los tres lags. La media resume nivel, la desviación resume dispersión y la proporción de ceros identifica intermitencia observable. No se añadieron tendencia de tres puntos, nuevos calendarios, stock adicional ni IDs de tienda. El calendario y stock preexistentes ya aportan contexto. Las tiendas se analizaron por separado. Un cero observado no identifica por sí solo demanda nula porque el stock puede limitar ventas.

## Protocolo y configuraciones

| Fold | Ajuste expansivo dentro de TRAIN | Evaluación interna | Filas de ajuste / evaluación |
| --- | --- | --- | ---: |
| 1 | Feb–jul 2025 | Ago–oct 2025 | 2.016 / 1.008 |
| 2 | Feb–oct 2025 | Nov 2025–ene 2026 | 3.024 / 1.008 |
| 3 | Feb 2025–ene 2026 | Feb–abr 2026 | 4.032 / 1.008 |

Cada familia permanece junta y tiene peso total uno durante ajuste. Los bloques evaluados no se solapan. Cada modelo de fold se ajusta una vez. Los lags de cada predicción posterior reflejan lo disponible al corte de ese mes. Se ajustó la imputación y la codificación dentro del prefijo de cada fold. Lag1 y media móvil de tres meses usan los mismos lags verificados. El MAE en todas las filas decide el orden exploratorio según el [protocolo fijado](../configs/protocolo.json).

| Variante | Entradas | Profundidad / mínimo por hoja |
| --- | --- | --- |
| A | 19 oficiales | 14 / 4 |
| B | 19 oficiales | 11 / 8 |
| C | 19 oficiales + 3 derivadas | 14 / 4 |
| D | 19 oficiales + 3 derivadas | 11 / 8 |

Todos los bosques usan semilla 42, 100 árboles y fracción 0.90. A es una implementación experimental de la configuración oficial, ajustada únicamente a los prefijos. Sus métricas coinciden con el diagnóstico histórico temporal sobre TRAIN. No se cargó ni reajustó el artefacto oficial. El MAE histórico oficial de VALIDATION, 11.5168, corresponde a otras filas y queda como contexto. La VALIDATION histórica, TEST y DEMO quedaron fuera del ajuste y la puntuación.

## Resultados pareados

Cada celda por fold contiene **MAE / RMSE / R²**. Las 1.008 filas por fold recibieron estimación de todos los métodos offline, con 100 % de cobertura de cálculo y cero abstenciones de estimador.

| Método | Fold 1 | Fold 2 | Fold 3 | MAE medio | RMSE agrupado | R² agrupado |
| --- | --- | --- | --- | ---: | ---: | ---: |
| Lag1 | 17.322 / 33.143 / −0.384 | 20.374 / 37.146 / −0.321 | 19.695 / 35.695 / −0.238 | 19.1306 | 35.3666 | −0.3040 |
| Media móvil | 15.252 / 28.713 / −0.039 | 17.941 / 31.724 / 0.037 | 18.635 / 32.456 / −0.024 | 17.2761 | 31.0069 | −0.0023 |
| A | 10.911 / 19.519 / 0.520 | 12.474 / 22.640 / 0.509 | 12.022 / 22.646 / 0.502 | 11.8022 | 21.6519 | 0.5113 |
| B | 10.712 / 20.566 / 0.467 | 12.813 / 24.115 / 0.443 | 12.082 / 23.526 / 0.462 | 11.8688 | 22.7888 | 0.4586 |
| C | 10.804 / 19.444 / 0.524 | 12.518 / 23.084 / 0.490 | 11.673 / 22.771 / 0.496 | 11.6646 | 21.8288 | 0.5032 |
| **D** | 10.777 / 20.746 / 0.458 | 12.505 / 23.887 / 0.454 | 11.686 / 23.381 / 0.469 | **11.6559** | 22.7130 | 0.4622 |

D tuvo una desviación de MAE entre folds de 0.7056 frente a 0.6568 de A. Su peor MAE fue 12.5046 frente a 12.4739 de A. La ventaja media de D sobre C fue de 0.0088 unidades. C y D mejoraron el MAE de A en dos folds. El ajuste por variante tomó entre 1.61 y 4.52 segundos por fold. El reajuste final de D sobre todo TRAIN tomó 5.06 segundos. Sus datos de ajuste incluyen los bloques exploratorios y el artefacto final queda sin evaluación independiente.

### Cobertura con control de rango

También se aplicó a todos los métodos una máscara común con los mínimos y máximos de las 18 entradas numéricas oficiales de cada prefijo. Su alcance es diagnóstico. En los folds 1 y 2 cubrió **0 de 1.008** filas cada uno y las métricas quedan nulas. En el fold 3 cubrió **1.004 de 1.008 (99.60 %)**, con cuatro abstenciones. En ese subconjunto, A obtuvo MAE 11.9213 y D 11.5763. Esta máscara de prefijos cortos no mide la cobertura de despliegue de 4.0.0 ni acredita una política de abstención de 4.1.1.

La caída de cobertura en los primeros folds se explicó por el calendario: `mes_sin` excedió el rango del prefijo en cada fila del fold 1 y `mes_cos` lo excedió en cada fila del fold 2. En el fold 3 se excluyeron cuatro filas por rezagos fuera de rango. Se mantuvo la máscara predefinida.

### Productos y tiendas

| Grupo | Filas | MAE A | MAE D |
| --- | ---: | ---: | ---: |
| Tienda 5 | 1.008 | 11.0489 | 10.8438 |
| Tienda 6 | 1.008 | 11.5459 | 11.5412 |
| Tienda 7 | 1.008 | 12.8117 | 12.5827 |
| Lags con ceros y positivos | 1.780 | 12.6102 | 12.2859 |
| Tres lags cero | 484 | 8.9390 | 9.1042 |
| Alta variabilidad | 756 | 18.1194 | 18.1928 |

Alta variabilidad identifica productos cuyo valor mediano de desviación de rezagos, una observación por familia del prefijo TRAIN, alcanza el percentil 75 de ese prefijo. D mejoró el MAE en 32 de 56 productos. Entre los de mayor MAE de A, el producto 14 mejoró de 23.2838 a 22.3244, mientras el producto 29 empeoró de 23.0883 a 23.5964. El [JSON de resultados](../evaluation/temporal-01.json) contiene desgloses por fold, producto, tienda, patrón de rezagos y variabilidad, además de tiempos, configuración, versiones y hashes.

## Integridad y decisión

Pasaron las verificaciones de fechas, tamaños y familias por fold, rechazo de una etiqueta tardía y de lags faltantes, fórmulas de características, abstenciones, R² con objetivos constantes, denominadores por segmento, coincidencia de A con el diagnóstico guardado y recarga del candidato por huella con inferencia finita. Los desgloses de tiempo son mediciones de una corrida. Versiones: Python 3.11.0, scikit-learn 1.9.1, NumPy 2.4.6, pandas 3.1.0 y joblib 1.6.0.

Los 554 archivos protegidos de 4.0.0 conservaron su huella agregada `4d5098398a45d8c3879ba08aad7dbc08c3c7696740a5cbbb6fa5e7268991fc27`. El artefacto oficial mantuvo SHA256 `8d73bbfb769e432461f2a202e37842b47820a76627e46be3e4ba412e64562e1e`. El candidato experimental es `candidates/temporal-01/candidate.joblib` y permanece `EXPERIMENTAL_NOT_ACTIVE`.

**GO de investigación** para contrastar C y D con A bajo un protocolo fijado de antemano y una cohorte independiente, incluyendo alta variabilidad y cobertura. **NO-GO de sustitución.** El margen de MAE es pequeño, los meses comparten un generador sintético y las variantes de cada familia están correlacionadas. Para la defensa, presentar 4.0.0 como oficial y 4.1.1 como experimento interno con resultados mixtos.
