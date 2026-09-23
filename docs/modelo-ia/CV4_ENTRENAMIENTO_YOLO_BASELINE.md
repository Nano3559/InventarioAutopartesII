# CV-4: Entrenamiento formal YOLO baseline

Fecha: 2026-09-22
Modelo: `yolo11n.pt` (pretrained) — baseline formal del módulo IA.

## Configuración

| Parámetro | Valor |
|---|---|
| Modelo | YOLO11n pretrained (yolo11n.pt) |
| GPU | NVIDIA GeForce RTX 4050 Laptop (6 GB, CUDA 12.1) |
| Epochs | máx 100 · ejecutadas 91 (early stopping) |
| Best epoch | 71 |
| imgsz | 640 |
| batch | 16 |
| device | 0 (CUDA) |
| workers | 0 |
| patience | 20 |
| seed | 20260922 |
| deterministic | True |
| Tiempo | 1.149 h (~4148 s) |
| Run dir | `ia-service/runs/detect/repuestopro_yolo11n_baseline_v1` |

## Dataset

- `ia-service/datasets/processed/` (CV-3 cerrado): train 1.612 imgs / 1.919 boxes; val 68 / 87; test 68 / 86. 8 clases fijas (`dataset.yaml`, `nc: 8`).
- Sintéticos (no en CV-4 metría de val/test) solo en train.
- Ejecutado con `wd = datasets/processed/` para que `path: .` resuelva correctamente (Ultralytics 8.4 resuelve `path` contra el CWD).

## Métricas BEST MODEL (val, sobre `best.pt`)

| early stopping | best epoch | P | R | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| Sí (91/100) | 71 | 0.588 | 0.436 | 0.458 | 0.303 |

### Por clase (val real)

| clase | id | imgs | inst | P | R | mAP50 | mAP50-95 |
|---|---|---|---|---|---|---|---|
| alternator | 3 | 21 | 24 | 0.732 | 0.542 | 0.603 | 0.326 |
| oil_filter | 4 | 3 | 3 | 0.000 | 0.000 | 0.000 | 0.000 |
| air_filter | 5 | 8 | 8 | 0.795 | 0.487 | 0.564 | 0.489 |
| radiator | 6 | 20 | 21 | 0.449 | 0.476 | 0.425 | 0.223 |
| headlight | 7 | 20 | 31 | 0.964 | 0.677 | 0.699 | 0.478 |
| brake_pad | 0 | — | — | NO EVALUABLE EN VAL (sin GT real) |
| brake_rotor | 1 | — | — | NO EVALUABLE EN VAL (sin GT real) |
| brake_caliper | 2 | — | — | NO EVALUABLE EN VAL (sin GT real) |

## Verificaciones

- `results.csv`: 91 filas (epoch 1..91), sin NaN/inf en box/cls/dfl loss ni métricas.
- `results.png`, `confusion_matrix.png`, `confusion_matrix_normalized.png`, `BoxPR_curve.png`, `BoxP_curve.png`, `BoxR_curve.png`, `BoxF1_curve.png`, `labels.jpg`, `val_batch*_pred/labels.jpg` generados.
- Predicción de control sobre 4 imágenes reales de val con `best.pt` (imgsz 640, conf 0.25): 5 detecciones, `class_id` en 0..7, `conf` en 0..1, cajas dentro de la imagen (1 imagen sin detecciones, normal a ese umbral).
- Sin errores CUDA, sin fallos de carga de dataset.
- `.cache` de Ultralytics eliminados de `processed/labels/`.

## Limitaciones

- `brake_pad/rotor/caliper` (ids 0-2) sin ground-truth real en val ni test → **no son evaluables** cuantitativamente en CV-4. No afirmar rendimiento de estas clases.
- `oil_filter` solo 3 instancias reales en val y 3 en test; métricas en 0.000 con solo 3 muestras no son representativas.
- `radiator` mAP50 bajo (0.425), P=0.449: principal candidato a atención en CV-5.
- Modelo entrenado completo → BEST.PT LISTO PARA CV-5: SÍ.

## Archivos generados

- `ia-service/runs/detect/repuestopro_yolo11n_baseline_v1/weights/best.pt` (5.47 MB)
- `ia-service/runs/detect/repuestopro_yolo11n_baseline_v1/weights/last.pt` (5.47 MB)
- `results.csv`, pngs de curvas/confusion/labels en el run dir.
- `scripts/train_yolo.py` (ahora acepta `--patience`).