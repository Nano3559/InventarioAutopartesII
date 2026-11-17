# Evaluación exploratoria pareada · DEMO histórico 4.0.0 frente a D

RepuestoPro · Rama `erika` · 17 de noviembre de 2026.

**Resultado descriptivo:** en las 504 filas DEMO BASE predefinidas, D obtuvo el menor MAE (**9.8026**) y RMSE (**19.1457**). Frente a 4.0.0, el MAE bajó **0.5184 unidades (5.02 %)** y el RMSE **0.0349 unidades (0.18 %)**. Los tres métodos emitieron en todas las filas. La exclusión de la coincidencia predefinida con TEST no cambió el orden. 4.0.0 se conserva como modelo oficial.

## 1. Objetivo

Comparar Random Forest oficial 4.0.0, candidato 4.1.1 D y Lag1 sobre las mismas ventas mensuales sintéticas, usando modelos congelados y el mismo corte. La evaluación es retrospectiva y exploratoria.

## 2. Procedencia

El build `calendar-20261116-01` contiene DEMO como realización sintética separada. La cohorte usa **56 productos × 3 tiendas × 3 meses**, agosto, septiembre y octubre de 2026. Se incluyó solo BASE, una fila por par y mes. Las ventas realizadas se obtuvieron de `base_mensual.csv`, con identidad y cierre verificados. [Auditoría de independencia](AUDITORIA_INDEPENDENCIA_DEMO_HISTORICO.md) · [Auditoría de calidad](AUDITORIA_DATASET_Y_PRUEBAS_MODELO.md)

## 3. Límites de independencia

Las filas tienen familias e identificadores distintos de TRAIN, VALIDATION y TEST. La realización comparte perfiles, productos, tiendas, calendario y mecanismo generador. Los tres meses coinciden con las fechas de TEST oficial y ya se publicaron como historial DEMO. El panel histórico mostró observados de ese mundo. El estudio carece de la independencia de una validación externa, prospectiva o ciega. Las 504 filas repiten los mismos 168 pares durante tres meses.

## 4. Protocolo predefinido

- Cohorte principal: `realization_id == DEMO`, sufijo `-BASE` y los tres meses fijados. Orden por mes, producto numérico y tienda numérica.
- 4.0.0 y D usan los mismos cortes y la puerta oficial de rango. D aplica la función de entrenamiento sobre los tres lags, con media, desviación estándar poblacional y fracción de ceros. Lag1 copia t−1 cerrado y disponible.
- MAE primario. RMSE, R² y error firmado complementan el análisis. Las métricas se calculan sobre la intersección de emisiones. Cobertura y abstenciones se contabilizan sobre todas las filas de cada población.
- Sensibilidad: excluir únicamente `family-DEMO-52-7-2026-08-BASE`, como constaba en la auditoría. No se repite inferencia ni se modifica la población según el error.

## 5. Manifiesto y evidencias selladas

| Archivo | SHA256 |
| --- | --- |
| [Manifiesto de cohorte](../../ml/demand/experiments/model_4_1_1/evaluation_demo/cohort_manifest.json) | `d83e6958562e6e58090b16300bb1d86469a66a2f598661060424dc8031609b90` |
| Lista canónica de IDs, serializada en el manifiesto | `b7c90b92d7da4579c41059abdead8825d598b75cb16231cdcb12740c71fd3394` |
| [Entradas sin resultado](../../ml/demand/experiments/model_4_1_1/evaluation_demo/inputs_without_outcomes.json) | `ae181b5b4d8e79ab7fa8200bbfcc7cabe6efc7ed2df0bd3e062022d6945e47f1` |
| [Emisiones y abstenciones](../../ml/demand/experiments/model_4_1_1/evaluation_demo/predictions.json) | `62aecd939dc573a57c4a4f5d065d2e15d537a09715416d4d32724ec354084d23` |
| [Métricas, segmentos y cruce observado](../../ml/demand/experiments/model_4_1_1/evaluation_demo/metrics.json) | `02b74dbb3d1e77b6db6ebb5ed73ad65773e2da0fbeabe814fd3a0fda47ffb031` |

Cada JSON se creó con apertura exclusiva y atributo de solo lectura. Las sucesivas etapas verificaron sus huellas. Las marcas UTC del manifiesto, emisiones y métricas fueron 13:21:27, 13:21:37 y 13:21:46, respectivamente. Lag1 es una regla y carece de artefacto entrenado. Se usó Python 3.11.0, scikit-learn 1.9.1, NumPy 2.4.6, pandas 3.1.0 y joblib 1.6.0. El [ejecutor](../../ml/demand/experiments/model_4_1_1/evaluation_demo/evaluate_demo.py) tiene SHA256 `0b63cdd6848a6bcde723986a1b3ce566dcae2110f1459a2071d2a4f274b19c30`.

## 6. Separación temporal y de etiquetas

La preparación proyectó solo identificadores, corte y 19 características del CSV autenticado. Comprobó el producto cartesiano exacto y contrastó **1.512 rezagos** cerrados con su fuente, mes y fecha de disponibilidad. Verificó disponibilidad al corte de 504 precios BASE, 504 stocks, 504 políticas logísticas y 373 planes de recepción. La cohorte BASE no tiene filas de pedidos pendientes. El contraste del contenido con la coincidencia TEST en la preparación verificó únicamente las entradas. La coincidencia de etiqueta procede de la auditoría previa.

En un proceso distinto, la etapa de inferencia leyó las entradas sin objetivos selladas, los manifiestos de los modelos, el código de transformación y los artefactos autenticados. No consultó `base_mensual.csv`, el CSV supervisado ni los snapshots de noviembre que contienen historial mostrado. El código de evaluación abrió las etiquetas una vez verificada la huella de las emisiones selladas. Exigió coincidencia de ID, producto, tienda y mes, cierre al mes siguiente y ventas no negativas. La comprobación posterior rederivó MAE, RMSE y R² con scikit-learn sobre el cruce sellado, sin ejecutar otra inferencia.

## 7. Resultados generales

| Método | Filas pareadas | MAE | RMSE | R² | Error firmado |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4.0.0 | 504 | 10.3210 | 19.1805 | 0.3711 | −2.5165 |
| **4.1.1 D** | 504 | **9.8026** | **19.1457** | **0.3734** | −2.6204 |
| Lag1 | 504 | 14.9643 | 27.5775 | −0.3001 | −1.0992 |

El error firmado es pronóstico menos observado. Los tres métodos subestiman en promedio en esta ventana. D tiene menor error absoluto medio y una subestimación media ligeramente mayor que 4.0.0.

## 8. Comparación pareada

| Comparación | Diferencia absoluta MAE | Cambio relativo MAE | Diferencia absoluta RMSE | Cambio relativo RMSE |
| --- | ---: | ---: | ---: | ---: |
| D frente a 4.0.0 | 0.5184 | −5.02 % | 0.0349 | −0.18 % |
| 4.0.0 frente a Lag1 | 4.6433 | −31.03 % | 8.3969 | −30.45 % |
| D frente a Lag1 | 5.1617 | −34.49 % | 8.4318 | −30.57 % |

El cambio relativo usa el método de referencia de cada fila como denominador. Un signo negativo indica reducción de error.

## 9. Segmentos

| Segmento | n | MAE 4.0.0 | MAE D | MAE Lag1 | RMSE 4.0.0 | RMSE D |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Agosto | 168 | 10.0338 | 9.2530 | 13.9881 | 18.4106 | 17.6869 |
| Septiembre | 168 | 10.3600 | 10.1166 | 15.4762 | 18.8047 | 19.4027 |
| Octubre | 168 | 10.5692 | 10.0382 | 15.4286 | 20.2759 | 20.2577 |
| Tienda 1 · ID 5 | 168 | 10.3992 | 9.6677 | 15.4524 | 20.9797 | 20.5004 |
| Tienda 2 · ID 6 | 168 | 10.7005 | 10.1765 | 14.7143 | 19.6281 | 19.4709 |
| Tienda 3 · ID 7 | 168 | 9.8633 | 9.5636 | 14.7262 | 16.6814 | 17.3288 |
| Lags intermitentes, ceros y positivos | 308 | 12.3868 | 12.0122 | 17.4253 | 21.9185 | 22.1226 |
| Tres lags cero | 89 | 5.5507 | 5.2285 | **5.1461** | 14.1105 | 14.2971 |
| Tres lags positivos | 107 | 8.3423 | 7.2469 | 16.0467 | 13.5785 | 12.1568 |
| Alta variabilidad | 126 | 13.1377 | 12.2646 | 21.6270 | 20.0340 | 20.3286 |
| Variabilidad restante | 378 | 9.3821 | 8.9819 | 12.7434 | 18.8875 | 18.7348 |

Intermitencia describe el patrón observable al corte. Alta variabilidad usa los **14 IDs** ya fijados en el último fold TRAIN de `temporal-01`, según el percentil 75 de la mediana por producto de la dispersión de lags. Se conserva ese grupo para los tres meses. El MAE baja con D en los tres meses y tiendas. El RMSE sube en septiembre, tienda 3, intermitencia y alta variabilidad. Tienda 2 tuvo el mayor MAE de ambos bosques.

D redujo el MAE en **36 de 56 productos** y lo elevó en **20**, con nueve filas por producto. Entre los mayores errores de los dos bosques quedaron los productos **53** (22.8056 → 21.9567), **6** (22.4317 → 20.4311) y **17** (22.1211 → 20.9339). Destaca la reducción del producto **12** (21.1717 → 16.3639) y el deterioro del **22** (15.9000 → 18.8172) y **31** (14.3572 → 16.6356). Los resultados completos por producto están en el JSON.

## 10. Sensibilidad · 504 frente a 503

| Método | MAE 504 | MAE 503 | RMSE 504 | RMSE 503 | R² 503 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4.0.0 | 10.3210 | 10.3415 | 19.1805 | 19.1996 | 0.3706 |
| D | 9.8026 | 9.8221 | 19.1457 | 19.1647 | 0.3729 |
| Lag1 | 14.9643 | 14.9940 | 27.5775 | 27.6049 | −0.3010 |

Se retiró únicamente la fila predefinida. Los tres métodos habían pronosticado cero para un observado cero. La reducción de MAE de D frente a 4.0.0 permanece en **5.02 %** y la de RMSE en **0.18 %**. El orden se conserva.

## 11. Cobertura y abstenciones

Los tres métodos emitieron **504/504** en la población principal y **503/503** en sensibilidad, con **cero abstenciones** en ambas. Esta cobertura se refiere a DEMO histórico BASE y no sustituye la cobertura del TEST guardado ni la de noviembre publicado.

## 12. Interpretación académica

| Evidencia | Uso y valores de referencia |
| --- | --- |
| TEST oficial 4.0.0 | Resultado congelado de otra realización. MAE **10.2010**, RMSE **18.4046**, R² **0.6201** sobre 1.008 filas. Quedó intacto. |
| Folds TRAIN 4.1.1 | Selección experimental interna. MAE **11.6559** para D frente a **11.8022** de A, una configuración de referencia ajustada por prefijo. |
| DEMO histórico BASE | Esta comparación pareada sobre 504 filas. MAE **9.8026** para D frente a **10.3210** de 4.0.0 congelado. |

Las poblaciones y propósitos difieren. El menor MAE DEMO describe una ventaja local. La diferencia de RMSE agregado es pequeña y algunos segmentos muestran empeoramientos. La cobertura de emisión indica cuántas cifras se entregaron. Esta evaluación carece de un intervalo de predicción calibrado.

## 13. Conclusión e integridad

D logró el menor MAE y RMSE de los tres métodos en DEMO histórico BASE y mantuvo ese resultado en sensibilidad. La evidencia justifica registrar el resultado como exploratorio. El modelo oficial 4.0.0 permanece activo y D permanece experimental sin activar. Se verificaron los mismos 554 archivos protegidos, con huella agregada `4d5098398a45d8c3879ba08aad7dbc08c3c7696740a5cbbb6fa5e7268991fc27`. Las huellas de 4.0.0 y D permanecen en `8d73bbfb769e432461f2a202e37842b47820a76627e46be3e4ba412e64562e1e` y `affafcffd98b4f67cd73416f803b4e062a487850a0465115174007692f52703c`, respectivamente. No hubo entrenamiento ni reevaluación de TEST.

## 14. Recomendaciones y reproducción

Registrar una cohorte independiente según M41-03. Fijar umbrales y criterios pareados antes de abrirla. Revisar error de cola por tienda, intermitencia y alta variabilidad. Los resultados actuales no sustentan activar D.

En una copia aislada que conserve las rutas y huellas de origen y solo el ejecutor en `evaluation_demo/`, correr las tres etapas desde PowerShell. El ejecutor rechaza sobrescribir archivos sellados:

```powershell
$script = 'ml/demand/experiments/model_4_1_1/evaluation_demo/evaluate_demo.py'
& ml/demand/.venv/Scripts/python.exe -B $script prepare
$huellaCohorte = Read-Host 'SHA256 que imprimió prepare'
& ml/demand/.venv/Scripts/python.exe -B $script predict $huellaCohorte
$huellaEmisiones = Read-Host 'SHA256 que imprimió predict'
& ml/demand/.venv/Scripts/python.exe -B $script score $huellaCohorte $huellaEmisiones
```

Las fechas y las huellas de los JSON que incluyan esas fechas cambian por corrida. La regla de inclusión, el orden canónico y las métricas son reproducibles.
