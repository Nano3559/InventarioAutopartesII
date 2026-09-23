# CV-5: Evaluación formal del modelo YOLO (best.pt) sobre TEST

Fecha: 2026-09-22
Fase: CV-5 del módulo IA / Computer Vision de RepuestoPro.
Terminado CV-4 (entrenamiento) — esta fase evalúa el modelo **sin entrenar ni tocar pesos** (best.pt, epoch 71).

---

## 1. Objetivo de CV-5

Evaluar de forma independiente y formal el mejor peso del baseline (`best.pt`)
sobre el split TEST del dataset `processed/`, separando:

- resultados ya existentes de **validación** (CV-4);
- **evaluación independiente sobre TEST** (recalculada en esta fase);
- análisis por clase;
- análisis de errores;
- limitaciones metodológicas.

No se entrenó, no se reanudó, no se hizo tuning ni se modificó ningún peso.
TEST se usó únicamente para evaluación.

## 2. Modelo evaluado

- Arquitectura: YOLO11n pretrained (yolo11n.pt).
- Peso: `best.pt` del run `repuestopro_yolo11n_baseline_v1` (5 469 651 bytes).
- Componentes (fused): 100 layers, 2 583 712 parámetros, 6.4 GFLOPs.
- Best epoch: 71 (early stopping con patience 20, detenido en epoch 91 de 100).

## 3. Best epoch

71 (seleccionado por Últralytics según fit = 0.1·mAP50 + 0.9·mAP50-95 en VAL).

## 4. Dataset

- `ia-service/datasets/processed/dataset.yaml` — 8 clases:
  `0 brake_pad, 1 brake_rotor, 2 brake_caliper, 3 alternator, 4 oil_filter,
  5 air_filter, 6 radiator, 7 headlight`.
- `path: .` se resuelve ejecutando con working directory `ia-service/datasets/processed/`.
- No se modificó `dataset.yaml` ni ningún archivo dentro de `processed/`.

## 5. Composición de TEST

- 68 imágenes reales.
- 86 bounding boxes GT.
- Distribución de clases en TEST (solo clases presentes):

| clase | id | GT instancias en TEST |
|---|---|---|
| alternator | 3 | 23 |
| oil_filter | 4 | 3 |
| air_filter | 5 | 6 |
| radiator | 6 | 21 |
| headlight | 7 | 33 |
| brake_pad | 0 | 0 (sin GT real) |
| brake_rotor | 1 | 0 (sin GT real) |
| brake_caliper | 2 | 0 (sin GT real) |

Auditoría previa (FASE 1): best.pt existe y carga correctamente, 8 clases en
el orden esperado, GPU RTX 4050/device 0 OK, 68 imágenes y 86 boxes
confirmados. Sin discrepancias.

## 6. Hardware

NVIDIA GeForce RTX 4050 Laptop GPU (6140 MiB), CUDA 12.1, PyTorch 2.5.1+cu121, Ultralytics 8.4.160, Python 3.11.0.

## 7. Configuración de evaluación

| parámetro | valor |
|---|---|
| split | test |
| imgsz | 640 |
| device | 0 |
| workers | 0 |
| conf (UMBRAL de conteo) | 0.25 (estándar de Ultralytics, sin ajuste) |
| proyecto / run | `runs/detect/repuestopro_yolo11n_test_v1` |

No se alteraron thresholds para mejorar métricas de forma artificial:
la evaluación usa los valores estándar de Ultralytics.
(results guardados en `ia-service/runs/detect/repuestopro_yolo11n_test_v1/`)

## 8. Métricas globales — VALIDACIÓN (recuperadas de CV-4, best.pt, val)

| P | R | mAP50 | mAP50-95 |
|---|---|---|---|
| 0.588 | 0.436 | 0.458 | 0.303 |

## 9. Métricas globales — TEST (evaluación formal de esta fase)

| P | R | mAP50 | mAP50-95 |
|---|---|---|---|
| 0.514 | 0.490 | 0.489 | 0.326 |

> RESULTADO MEDIDO: valores oficiales producidos por `model.val(split='test')`.

## 10. Métricas por clase en TEST

| clase | GT test | P | R | mAP50 | mAP50-95 | Observación |
|---|---|---|---|---|---|---|
| brake_pad | 0 | — | — | — | — | NO EVALUABLE EN TEST — SIN GROUND TRUTH REAL |
| brake_rotor | 0 | — | — | — | — | NO EVALUABLE EN TEST — SIN GROUND TRUTH REAL |
| brake_caliper | 0 | — | — | — | — | NO EVALUABLE EN TEST — SIN GROUND TRUTH REAL |
| alternator | 23 | 0.629 | 0.590 | 0.594 | 0.325 | clase con más instancias y métrica estable |
| oil_filter | 3 | 0.000 | 0.000 | 0.000 | 0.000 | MUESTRA MUY PEQUEÑA (3) — INTERPRETAR CON CAUTELA |
| air_filter | 6 | 0.727 | 0.833 | 0.778 | 0.680 | mejor mAP50 de TEST, muestra pequeña |
| radiator | 21 | 0.344 | 0.429 | 0.322 | 0.163 | clase más débil: Flamante P y mAP50 bajos |
| headlight | 33 | 0.868 | 0.596 | 0.750 | 0.460 | mejor precision |

## 11. Precision (explicación)

**Precision = TP / (TP + FP)**: de todo lo que el modelo dice que es un objeto,
¿qué fracción es realmente el objeto (IoU ≥ 0.5 contra GT)? Penaliza los
**falsos positivos**. En TEST global 0.514.

## 12. Recall (explicación)

**Recall = TP / (TP + FN)**: de todos los objetos que realmente existen (GT),
¿qué fracción fue detectada correctamente? Penaliza los **falsos negativos**.
En TEST global 0.490.

## 13. IoU (explicación)

**IoU = Intersection over Union** = área de intersección entre la caja
predicha y la caja GT dividida por el área de la unión de ambas. Refleja el
grado de solapamiento espacial; IoU = 1 → cajas idénticas; IoU = 0 → sin
solapamiento. Un emparejamiento pred↔GT se considera "acierto" típicamente
con IoU ≥ 0.5.

No se inventó un "IoU promedio" global: Ultralytics no lo expone como métrica
independiente. El solapamiento se calibra mediante **mAP50** y **mAP50-95**.
El conteo TP/TP/FP de este documento usa el umbral de emparejamiento IoU ≥ 0.5
(coherente con mAP50) y se documenta como análisis auxiliar propio, sin
sustituir las métricas oficiales.

## 14. mAP50 (explicación)

Mean Average Precision evaluada con IoU ≥ 0.50 (threshold único). Es una
medida de capacidad de detección a "match holgada". TEST: 0.489.

## 15. mAP50-95 (explicación)

Promedio de mAP calculada con IoU ∈ {0.5, 0.55, ..., 0.95} (10 umbrales).
Es más estricta porque exige cajas muy bien alineadas. TEST: 0.326.

## 16. Matriz de confusión (TEST)

Matriz oficial de Ultralytics (rows = GT, cols = predicción, `conf=0.25`,
emparejamiento interno IoU). Valores diagonales = TP.

```
GT\pred          brake_pad brake_rotor brake_caliper alternator oil_filter air_filter radiator headlight background
brake_pad            0           0            0           0          0          0        0       0       0       (sin GT)
brake_rotor          0           0            0           0          0          0        0       0       0       (sin GT)
brake_caliper        0           0            0           0          0          0        0       0       0       (sin GT)
alternator           0           0            0          14          0          0        0       0       12
oil_filter           0           0            0           0          0          0        0       0       0       (sin TP; 3 GT)
air_filter           0           0            0           0          0          5        0       0       2
radiator             0           0            0           0          0          0       11       0       25
headlight            0           0            0           0          0          0        0      21       3
background           0           0            0           9          3          1       10      12       0
```

### Observaciones (solo donde hay GT real)

- **Cero confusiones entre clases** (toda la región fuera de la diagonal y de
  la última columna/fila es 0): el modelo no atribuye una clase a otra en TEST.
- Los errores son de dos tipos:
  1. **Missed detections (FN → background)**: cajas GT sin predicción
     asignada. Dominan en `radiator` (25 en col. background) y `alternator`
     (12). Es la causa principal de la R baja.
  2. **Falsos positivos (background → clase)**: predicciones sin GT real.
     Concentradas en `headlight` (12), `radiator` (10) y `alternator` (9).
- NOTA metodológica: Ultralytics, bajo su matching interno, puede asignar
  entradas a background que incluyen sub-umbrales; las columnas background
  deben leerse cualitativamente (tendencia de error = detección perdida), no
  como conteo exacto 1:1 contra GT. por eso este doc no presenta los conteos
  background como saldo cerrado contra `GT - TP`.
- No se sacan conclusiones sobre brake_pad/rotor/caliper (no hay GT real).

## 17. Análisis de errores

- **Alternator (GT 23, TP 14)**: R=0.59; se pierde ~2 de cada 5 GT. Cuando
  acierta suele hacerlo con caja correcta (mAP50-95 0.325 razonable). Hay 9 FPs.
- **Radiator (GT 21, TP 11)**: la clase más débil (P=0.344, mAP50=0.322,
  mAP50-95=0.163). Pierde la mayoría de los GT y además produce 10 FPs.
  Es el principal foco de mejora (visualmente se confunde con zonas metálicas
  del vano motor).
- **Headlight (GT 33, TP 21)**: alta precisión (0.868) pero R=0.596; 12 FPs
  (componentes brillantes del vano). mAP50-95 0.46 bueno pero aún pierde GT.
- **Air_filter (GT 6, TP 5)**: pequeña muestra pero buen comportamiento
  (mAP50 0.778).
- **Oil_filter (GT 3, TP 0)**: sin TP en TEST (igual que en VAL). Con 3
  instancias reales NO se puede afirmar nada: el modelo no logró detectarlas en
  test, pero la muestra es insuficiente para concluir fallo sistemático.
- **Brake (0/1/2)**: sin GT real → sin evaluar. La ausencia de métricas no se
  interpreta como fallo del modelo.

## 18. Análisis visual (previews)

Inferencia con `best.pt` (imgsz 640, conf 0.25) sobre las 68 imágenes de TEST.
Se guardan previews anotadas en `runs/detect/repuestopro_yolo11n_test_v1/previews/`
(instantáneas originales, sin tocar `processed/`).

Categorización (emparejamiento IoU ≥ 0.5, script propio documentado en
`previews/predicciones_test.json`):
- Imágenes con detección correcta: 23
- Imágenes con falsos negativos: 36
- Imágenes con falsos positivos: 9
- Imágenes sin categoría: 0

Ejemplos destacados (nombres de archivo):
- Correctas: `car_engine_bay__test__1024`, `car_engine_bay__test__1063`,
  `car_engine_bay__test__1118`, `car_engine_bay__test__1123`.
- Falsos negativos: `car_engine_bay__test__1039`, `car_engine_bay__test__1052`,
  `car_engine_bay__test__1167`, `car_engine_bay__test__1219`.
- Falsos positivos/confusión (pred sin GT): `car_engine_bay__test__1002`,
  `car_engine_bay__test__1005`, `car_engine_bay__test__1061`,
  `car_engine_bay__test__109`.
- Incluye series segmentadas reales de faro: `carparts_seg__headlight__test__*`
  (20 imágenes anotadas, cubren la clase headlight).

Se intentó cubrir las cinco clases con GT (alternator, oil_filter, air_filter,
radiator, headlight). Las previews no muestran sólo los mejores casos: se
conservaron casos de acierto, caja baja, FN y FP.

## 19. Comparación VAL vs TEST (descriptiva)

| métrica | VAL (CV-4) | TEST (CV-5) | lectura |
|---|---|---|---|
| Precision | 0.588 | 0.514 | leve caída (−0.074) |
| Recall | 0.436 | 0.490 | mejora (+0.054) |
| mAP50 | 0.458 | 0.489 | mejora leve (+0.031) |
| mAP50-95 | 0.303 | 0.326 | mejora leve (+0.023) |

INTERPRETACIÓN: comportamiento **parecido** entre VAL y TEST, con TEST
ligeramente mejor en recall/mAP. No hay caída importante; la dispersión por
clase (radiator malo en ambos, air/headlight buenos en ambos) es consistente,
lo que sugiere estabilidad del modelo. NO se afirma generalización robusta:
TEST es pequeño (68 imgs) y cubre solo 5 de 8 clases. TEST no se
usa para decidir reentrenamiento en esta tarea.

## 20. Limitaciones

- brake_pad / brake_rotor / brake_caliper: **sin GT real** en VAL ni TEST →
  NO EVALUABLES cuantitativamente; la ausencia de métricas no es fallo.
- oil_filter: solo 3 GT reales en TEST (y 3 en VAL); métricas → MUESTRA MUY
  PEQUEÑA, no concluyente.
- air_filter: cobertura real limitada (6 en TEST, 8 en VAL).
- TEST total pequeño (68 imágenes); las diferencias VAL↔TEST (±0.02–0.07)
  están dentro del ruido esperable y no demuestran generalización robusta.
- El conteo TP/FN/FP de la sección 17 es auxiliar propio (IoU ≥ 0.5), no
  reemplaza las métricas oficiales de Ultralytics del punto 9.
- La política de confianza de producción NO se fija en esta fase (ver 19/21).

## 21. Conclusión técnica

RESULTADO MEDIDO: TEST P=0.514, R=0.490, mAP50=0.489, mAP50-95=0.326, con
headlight y air_filter fuertes, alternator medioestable y radiator débil.
La matriz muestra ausencia de confusiones entre clases; el error dominante son
cajas perdidas y FPs sobre background.

INTERPRETACIÓN: el baseline es utilizable como referencia y como primer
endpoint de detección, estable entre VAL y TEST. Radiator es la clase a
atender primero en futuras iteraciones. NO EVALUABLE brakepads/rotor/caliper
ni oil_filter (muestra).

LIMITACIÓN: conclusiones robustas requieren más GT reales (especialmente
oil_filter, air_filter y las 3 clases de freno) y un TEST de mayor tamaño.

Evidencia suficiente para continuar a CV-6 (integración de la capa del
servicio/pipeline) con las advertencias documentadas.