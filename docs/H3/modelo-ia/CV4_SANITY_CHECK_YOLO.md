# CV-4 — SANITY CHECK YOLO (FASES 1 y 2)

Fecha: 2026-09-22  
Script: `ia-service/scripts/train_yolo.py`  
Run: `ia-service/runs/detect/repuestopro_sanity/` (no versionado en Git)

## FASE 1 — Auditoria del entorno

| Item | Valor |
|---|---|
| Python | 3.11.0 |
| PyTorch | 2.5.1+cu121 |
| torch.cuda.is_available() | True |
| CUDA detectada por PyTorch | 12.1 |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU |
| VRAM | 6,438,780,928 bytes (~6.0 GB / 6140 MiB) |
| Ultralytics | 8.4.160 (instalado en `ia-service/.venv`, no se toco torch) |
| OpenCV | 5.0.0 |
| dataset.yaml | Carga correcta: nc=8, names 0..7, train/val/test resueltos a rutas absolutas |

Nota: `dataset.yaml` de `processed/` usa `path: .` (rutas relativas) y Ultralytics las resuelve contra el directorio de trabajo; por eso el entrenamiento se ejecuta con working dir = `ia-service/datasets/processed`. No se modifico `processed/dataset.yaml`.

## FASE 2 — Sanity check

| Parametro | Valor |
|---|---|
| Modelo base | YOLO11n (`yolo11n.pt`, 5.4 MB, 2,591,400 params / 6.5 GFLOPs) |
| Epochs | 3 |
| imgsz | 640 |
| batch | auto (AutoBatch -> 16 en 60% VRAM) |
| device | 0 (CUDA) |
| workers | 0 (seguro en Windows) |
| seed / deterministic | 20260922 / True |
| Tiempo total | 122.7 s (~33 s/epoch, 1.1-3.2 it/s) |

### Ejecucion

- Descarga `yolo11n.pt` desde GitHub assets.
- Scan train: 1612 imagenes, 0 backgrounds, 0 corrupt.
- Scan val: 68 imagenes, 0 corrupt.
- AutoBatch en CUDA (RTX 4050, 5.85G libres) eligio batch 16.
- CUDA realmente usada (columna GPU_mem en cada epoch, log `torch-2.5.1+cu121 CUDA:0`).

### Metricas (solo referencia, 3 epochs)

| Epoch | box_loss | cls_loss | dfl_loss | P | R | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.216 | 3.992 | 1.451 | 0.683 | 0.071 | 0.069 | 0.041 |
| 2 | 1.141 | 2.840 | 1.363 | 0.494 | 0.206 | 0.209 | 0.115 |
| 3 | 1.026 | 2.323 | 1.265 | 0.527 | 0.283 | 0.347 | 0.215 |

Loss decreciente. mAP50 creciente 0.069 -> 0.347. No son rendimiento definitivo (3 epochs no entrenan).

## Verificaciones post-train

| Control | Resultado |
|---|---|
| 3 epochs completadas | Si |
| CUDA utilizada | Si (CUDA:0, GPU_mem en logs) |
| Errores de labels | 0 |
| Imagenes corruptas | 0 (1612 train / 68 val scan ok) |
| NaN | No aparecieron |
| train loss calculada | Si (box/cls/dfl por epoch) |
| val ejecutada | Si (1 por epoch) |
| results.csv | Existe (566 B, 3 filas) |
| weights/last.pt | Existe (5,468,883 B) |
| weights/best.pt | Existe (5,468,883 B) |
| confusion_matrix.png | Generada (+ normalizada) |
| train_batch*.jpg | Generadas (3) |
| val_batch*_labels/pred.jpg | Generadas (3/3) |

## Inspeccion visual

El asistente no soporta lectura directa de imagenes; se realizo verificacion programatica en su lugar:

- Las 17 imagenes del run (curvas, confusion, mosaicos) abren correctamente (PNG/JPG validos, p.ej. mosaicos 1920x1920).
- Predict funcional con `best.pt` sobre `car_engine_bay__val__264.jpg` (GT multiclase: alternator + oil_filter + radiator): detecta `alternator` (x2) y `radiator` con coordenadas plausibles y clases dentro de 0..7.
- Rutas para revision manual por Erika:
  - `ia-service/runs/detect/repuestopro_sanity/val_batch1_pred.jpg`
  - `ia-service/runs/detect/repuestopro_sanity/val_batch1_labels.jpg`
  - `ia-service/runs/detect/repuestopro_sanity/train_batch0.jpg`
  - `ia-service/runs/detect/repuestopro_sanity/confusion_matrix.png`

## Incidencias

- Ultralytics 8.4.160 descargo adicionalmente `yolo26n.pt` a `ia-service/weights/` (artefacto del trainer, ~5.3 MB). Se conserva dentro de una carpeta ignorada por Git; no afecta el sanity.
- Ultralytics creo `.cache` dentro de `processed/labels/`; se eliminaron despues del run para dejar `processed/` intacto.
- Primer uso: Ultralytics genero su `settings.json` (telemetria) y descargo `Arial.ttf`.

## Decision

El pipeline completo funciona: carga de datos, mapeo de clases (nc=8), CUDA, forward/backward, loss, validacion, curvas y pesos se generan sin errores. Las metricas de 3 epochs son solo referencia.

SANITY CHECK YOLO: **APROBADO**
LISTO PARA ENTRENAMIENTO FORMAL: **SI**

No se ejecuto el entrenamiento formal, no hay tuning, no se toco `processed/`, backend, frontend, Prisma, Docker, ni se hizo git add/commit/push.