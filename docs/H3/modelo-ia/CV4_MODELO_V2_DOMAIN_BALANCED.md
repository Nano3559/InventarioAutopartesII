# CV-4 (V2): Mejora del modelo con dominio "producto aislado" — YOLO11n domain-balanced

Fecha: 2026-09-23
Modelo: `repuestopro_yolo11n_v2_domain_balanced` (`yolo11n.pt` pretrained, reentrenado sobre dataset V2).
Estado: reentrenamiento completado y evaluado. **NO integrado a producción (FastAPI) todavía** — pendiente de decisión de Ross.

## 1. Propósito

El baseline V1 (2026-09-22) alcanzó mAP50 0.473 en val pero **fracasaba en el holdout real de alternador
(0/10 correctos, todos → `brake_caliper`)** y en fotos del catálogo Kaggle aisladas, por gap de dominio:
el modelo solo conocía piezas en contexto de motor (CEB) y sintéticos. Pregunta de la auditoría: ¿el umbral
de confianza era la causa? Respuesta: NO (VISION_CONFIDENCE_MIN 0.30 / CONF_TECNICO_INFERENCIA 0.85
conservadores pero no eran la causa; el gap era de dataset, no de threshold).

Objetivo CV-4-V2: dar al modelo el dominio **"producto aislado"** con bboxes automáticos (sin anotación
manual), val/test reales, sin data leakage, y volver a entrenar partiendo de YOLO11n pretrained (mismo
pipeline que V1) para comparación limpia en los mismos términos.

## 2. Dataset baseline (V1) — resumen

- Origen: `ia-service/datasets/processed/` (CV-3) → 1.748 imágenes (1.612 train / 68 val / 68 test), 8 clases.
- Composición prevalente: contexto de compartimento de motor (CEB, `car_engine_bay__*`) + sintéticos del
  pipeline `generate_synthetic_dataset.py` (brake_pad/rotor/caliper y oil_filter solo sintéticos en train).
- Sin GT real de frenos en val/test V1 → clases 0-2 no evaluables; oil_filter con 3 instancias reales.
- Gap detectado en auditoría: V1 jamás vio fotografía de pieza suelta real en train.

## 3. Dataset V2 — construcción, dominios, leakage

Builder: `ia-service/scripts/build_dataset_v2.py` (no anota a mano; bbox automático vía máscara rembg u2net).

Composición por dominio (V2):

| Dominio | Qué es | Origen |
|---|---|---|
| context | imagen de compartimento/contexto (CEB + demás base) | base `processed/` (tras purga near-dup) |
| product | fotografía real de pieza aislada con bbox automático por máscara | Kaggle `train/valid/test` car-parts (ALTERNATOR, RADIATOR, HEADLIGHTS) + pool limpio de frenos/oil_filter |
| synthetic | composiciones del pipeline (50/alt,50/rad,50/headlight) solo desde Kaggle **train** | `generate_v2_synthetics` con fondos locales |

Totales V2 (registros `processed_v2_manifest.csv`): **2.454 filas**.

| Split | imágenes | boxes |
|---|---|---|
| train | 2.278 | 2.585 |
| val | 91 | 110 |
| test | 85 | 101 |

Per-class (imágenes con al menos un bbox de la clase; boxes):

| Clase | id | Train imgs | Train boxes | Val imgs | Val boxes | Test imgs | Test boxes |
|---|---|---|---|---|---|---|---|
| brake_pad | 0 | 200 (syn) | 200 | 3 (prod) | 3 | 3 (prod) | 3 |
| brake_rotor | 1 | 200 (syn) | 200 | 3 (prod) | 3 | 3 (prod) | 3 |
| brake_caliper | 2 | 200 (syn) | 200 | 4 (prod) | 4 | 2 (prod) | 2 |
| alternator | 3 | 426 (187 ctx + 189 prod + 50 syn) | 429 | 22 (17+5) | 25 | 24 (19+5) | 24 |
| oil_filter | 4 | 194 (syn) | 194 | 8 (3+5 prod) | 8 | 6 (2+4 prod) | 6 |
| air_filter | 5 | 35 (ctx) | 35 | 7 (ctx) | 7 | 6 (ctx) | 6 |
| radiator | 6 | 837 (619+168+50) | 842 | 23 (18+5) | 24 | 18 (13+5) | 19 |
| headlight | 7 | 369 (160+159+50) | 485 | 25 (20+5) | 36 | 25 (20+5) | 38 |

- Kaggle alt/rad/headlight: split oficial Kaggle respetado (train→train, valid→val, test→test).
- Frenos/oil_filter: solo imágenes **limpias** (que NO fueron fuente de ningún síntético V1) entran a
  val/test; las usadas como fuente quedaron en train, evitando que un derivado sintético y su fuente
  original se repartan entre splits.
- `per_class` agrega por fila-bbox, no por imagen única: una imagen multi-clase (p. ej. CEB con
  alternator+radiator) cuenta en cada clase, por eso la suma de "imgs" por clase no es el total de archivos.

### Bbox automático (sin anotación manual)

1. rembg `u2net` → máscara de alpha → bbox de la componente más grande de la máscara.
2. Normalización y validación geométrica: si área<0.02 o lado box<0.04 o bbox inválido → rechazo.
3. Fallback `full_image` (pieza llena el frame, área>0.90 o box>0.95) o si falla la máscara.
4. `bbox_method` por fila en el manifest: `mask` | `full_image_fallback` | `mask_synthetic`.
5. Rechazos registrados en `processed_v2/rejected_bboxes.csv` (2 producto + 2 sintético, p. ej.
   `ALTERNATOR/train/065.jpg` área 0.0106, `RADIATOR/train/035.jpg` área 0.0066).

### Leakage

- Dedupe exacto (sha256) y near-dup (dhash ≤1 bit) a nivel V2 final: **0 exactos / 0 near entre splits**.
- **Purga near-dup preexistente**: el CEB base tenía 17 fotos casi idénticas repartidas entre train y
  val/test (misma foto, resguardos distintos). V2 eliminó de val/test las imágenes cuyo near-dup vive en
  train (no se toca `processed/` V1). Post-purga: 0 duplicados cruzados.
- Los 573 product de alt/rad/headlight provienen de 0 imágenes fuente sintética V1 (pool limpio verificado).
- Holdout de alternador = Kaggle valid+test completo (10 imgs), **nunca en train** (train solo usa Kaggle
  `train/`).

## 4. Entrenamiento

| Parámetro | Valor |
|---|---|
| Modelo | yolo11n.pt pretrained (mismo origen que V1) |
| data | `ia-service/datasets/processed_v2/dataset.yaml` (path absoluto; Ultralytics 8.4 resuelve `path` contra CWD) |
| epochs | 100 ejecutadas (65, early stop) |
| best epoch | 45 |
| imgsz | 640 |
| batch | 16 |
| device | 0 (CUDA RTX 4050 6 GB) · workers 0 |
| patience | 20 |
| seed | 20260922 · deterministic True |
| Tiempo | 3.196 s (~0.89 h) |
| Run dir | `ia-service/runs/detect/repuestopro_yolo11n_v2_domain_balanced` |

## 5. Resultados

### Val (best.pt, split val real, solo 91 imgs)

| early stop | best epoch | P | R | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| Sí (65/100) | 45 | 0.814 | 0.696 | 0.759 | 0.643 |

Por clase (val):

| clase | imgs | inst | P | R | mAP50 | mAP50-95 |
|---|---|---|---|---|---|---|
| brake_pad | 3 | 3 | 0.971 | 1.00 | 0.995 | 0.840 |
| brake_rotor | 3 | 3 | 0.951 | 1.00 | 0.995 | 0.962 |
| brake_caliper | 4 | 4 | 1.00 | 0.64 | 0.995 | 0.920 |
| alternator | 22 | 25 | 0.706 | 0.672 | 0.705 | 0.518 |
| oil_filter | 8 | 8 | 0.910 | 0.625 | 0.625 | 0.574 |
| air_filter | 7 | 7 | 0.558 | 0.571 | 0.583 | 0.433 |
| radiator | 23 | 24 | 0.577 | 0.333 | 0.443 | 0.332 |
| headlight | 25 | 36 | 0.840 | 0.731 | 0.734 | 0.562 |

Nota: al incluir val real nuevo (product+TBE), P/R global suben vs V1 (0.588/0.436 → 0.814/0.696).

### Test combinado (85 imgs, 101 boxes, conf 0.25)

| modelo | P | R | matched | FP | FN |
|---|---|---|---|---|---|
| baseline V1 | 0.558 | 0.475 | 48 | 38 | 53 |
| **V2** | **0.639** | **0.683** | 69 | 39 | 32 |

### Test por dominio

**Producto aislado (27 imgs, 27 boxes):**

| modelo | P | R | alternator | radiator | headlight | frenos+oil |
|---|---|---|---|---|---|---|
| baseline V1 | 0.44 | 0.407 | 0/5 | 0/5 | 0/5 | pad 2/3, rotor 3/3, cal 2/2, oil 4/4 |
| **V2** | **0.93** | **0.963** | **5/5** | **5/5** | **5/5** | pad 2/3, rotor 3/3, cal 2/2, oil 4/4 |

**Contexto (58 imgs, 74 boxes):**

| modelo | P | R | alternator | radiator | air_filter | headlight |
|---|---|---|---|---|---|---|
| baseline V1 | 0.607 | 0.500 | 0.421 | 0.538 | 0.833 | 0.70 |
| **V2** | 0.538 | 0.581 | 0.579 | 0.462 | 0.833 | 0.85 |

## 6. Regresión del holdout real de alternador (10 imgs Kaggle valid+test, nunca en train)

| modelo | correctos | incorrectos | vacíos | confusión principal |
|---|---|---|---|---|
| baseline V1 | 0/10 | 10/10 | 0 | 10 → `brake_caliper` |
| **V2** | **10/10** | 0/10 | 0 | ninguna (conf 0.84–0.97) |

## 7. Criterios de aceptación → estado

| Criterio | Umbral | Resultado V2 | Cumple |
|---|---|---|---|
| Recall producto aislado | ≥0.80 | 0.963 (26/27) | ✅ |
| Recall contexto (clases con GT suficiente) | ≥0.60 | headlight 0.85, air 0.833, alternator 0.579, radiator 0.462 (globales mixtos) | ⚠️ parcial (alternator 0.58, radiator 0.46) |
| alternator no colapsa a brake_caliper | 0 confusión | 0 confusiones en holdout y test producto | ✅ |
| Reducción de "vacíos" en producto | significativa | baseline 0 detecciones en 15/15 alt+rad+head test → V2 15/15 | ✅ |
| Sin degradación grave de frenos | no regresión | pad/rotor/caliper iguales o mejores | ✅ |
| Sin leakage | 0 dup cruzados | 0 exactos + 0 near tras purga | ✅ |

## 8. Pruebas del ia-service

`pytest` desde `ia-service/`: **66 passed** (health, hardening, detect, classify).

## 9. Limitaciones y pendientes

- `radiator` producto aislado mejora (0→5/5 en test) pero en **contexto** recall baja 0.538→0.462 y P baja;
  radar es la clase con más tensión contexto/aislado en val/test. Candidata a atención posterior.
- `alternator` contexto recall sube de 0.42 a 0.58 pero P baja (más FP por sobre-detección) — no regresión
  severa, seguimiento recomendado.
- `air_filter` sigue sin dominio aislado: solo contexto CEB local (no hay fuente Kaggle limpia/aislada
  verificada); reportado, no descargado (no se incorporan fuentes externas no auditadas).
- Modelo nuevo **NO está conectado a FastAPI** (`VISION_CONFIDENCE_MIN` y `CONF_TECNICO_INFERENCIA` sin
  cambios; `best.pt` de producción sigue siendo el V1). Aprobación de Ross requerida para el swap.

## 10. Archivos generados/modificados

- Nuevo: `ia-service/scripts/build_dataset_v2.py`, `ia-service/scripts/validate_dataset_v2.py`,
  `ia-service/scripts/evaluate_v2.py`.
- Nuevo dataset: `ia-service/datasets/processed_v2/` (images/labels train·val·test, `dataset.yaml`,
  `processed_v2_manifest.csv`, `rejected_bboxes.csv`, `dataset_v2_validation.json`, `evaluation_v2.json`,
  `diagnostics/preview__*.jpg`).
- Run: `ia-service/runs/detect/repuestopro_yolo11n_v2_domain_balanced/` (weights best/last, results.*, curvas).
- No se modificó `processed/`, ni el run V1, ni FastAPI, ni `schema.prisma`, ni backend/frontend/mobile.
- Commits/push: NO (manual, Ross).