# AUDITORÍA DE ROBUSTEZ YOLO V2 — RepuestoPro

Fecha: 2026-09-23
Modelo: `repuestopro_yolo11n_v2_domain_balanced` (YOLO11n)
Umbral backend: `VISION_CONFIDENCE_MIN=0.55` · Umbral técnico: `CONF_TECNICO_INFERENCIA=0.25`
Semilla de diagnóstico: `20260923` (reproducible)
**No se reentrenó. No se tocó sistema funcional. No se inició CV-8.**

---

## 1. ENTRENAMIENTO V2

- **Epochs máximas:** 100 (`args.yaml: epochs: 100`)
- **Epochs ejecutadas:** 65 (CSV del run termina en epoch 65: filas e1..e65)
- **Best epoch:** 45 (val mAP50 0.75937, mAP50-95 0.64233; fitness = mAP50·0.1 + mAP50-95·0.9 = 0.654). El ep33 tiene mAP50 0.7598 pero mAP50-95 0.63497 (fitness 0.647), por lo que fitness eligió ep45.
- **Motivo de parada:** `EarlyStopping` con `patience: 20` (nombre del run con `name=...; exist_ok: true`, `optimizer: auto`). La última mejora fue en ep45 y no hubo mejora en los siguientes 20 epochs → parada en 65.
- **Train losses (evolución):** box 0.952→0.598 · cls 3.133→0.551 (−82.4%) · dfl 1.371→1.097.
- **Val losses (evolución):** box 1.338→1.157 · cls 3.780→1.397 · dfl 1.369→1.224; ligeras fluctuaciones posteriores a ep45 (p. ej. cls val 1.282@45 → 1.397@65), NO divergencia creciente.
- **Métricas finales best (ep45):** P 0.814 · R 0.696 · mAP50 0.759 · mAP50-95 0.642. En ep65: mAP50 0.721, mAP50-95 0.593 (regresión respecto al best guardado).
- **Augmentations usadas (de args.yaml):** `hsv_h 0.015, hsv_s 0.7, hsv_v 0.4`, `translate 0.1`, `scale 0.5`, `fliplr 0.5`, `mosaic 1.0`, `auto_augment randaugment`, `erasing 0.4`, `close_mosaic 10`.
- **Augmentations AUSENTES:** `degrees 0.0` (sin rotación), `shear 0.0`, **`perspective 0.0`**, `flipud 0.0`, `mixup 0.0`, `cutmix 0.0`, `copy_paste 0.0`. No existe configuración de blur ni ruido ni compresión JPEG en el entrenamiento estándar de ultralytics.

### ¿Underfitting? — NO por las métricas de val
Train/cls bajó 82% y val/cls bajó 63% (3.78→1.40), con mAP50 val mejorando hasta 0.759 y estabilizándose. La brecha train/val sigue presente (ratio cls ~2.5 en ep65) pero es consistente y no indica capacidad insuficiente en val.

### ¿Overfitting? — NO
No hay divergencia creciente train/val: val losses oscilan establemente (~1.2–1.6 cls) desde ep30; mAP50 de val no cae hacia el final del entrenamiento (0.759@45, 0.721@65 por estancamiento, no por degradación de val).

### ¿Más epochs resolverían el problema (webcam)? — NO
Evidencia: el run se detuvo por early stopping sin que ninguna de las 20 epochs posteriores al best mejorara val. Las métricas val estaban en meseta desde ~ep32. El problema real (detecciones vacías en webcam) **no aparece en la distribución de validación** (product/context digital), por lo que más epochs sobre el mismo dataset no exponen al modelo a ese tipo de degradación.

---

## 2. BASELINE DIGITAL

Setup: `best.pt` V2 · `conf=0.25` · `imgsz=640` · device cuda:0. Imágenes de TEST/VAL, priorizando holdout product.

Resultados (41 imágenes: 10 alternator + 10 radiator + 10 headlight → holdout Kaggle; 11 air_filter → contexto val/test porque no hay product aislado en test):

| Clase | Imágenes | Correctas | Vacías | Confianza media | ≥0.55 |
|---|---|---|---|---|---|
| alternator | 10 | 10 | 0 | 0.9411 | 10 |
| radiator | 10 | 10 | 0 | 0.9440 | 10 |
| headlight | 10 | 10 | 0 | 0.9504 | 10 |
| air_filter | 11 | 7 | 2 | 0.7892 | 8 |

_Detalles por imagen: `ia-service/artifacts/diagnostico_v2/manifest_seleccion_v2.csv`. Imágenes con bbox+clase+conf: `artifacts/diagnostico_v2/original_anotadas/`._

**V2 sobre archivo digital funciona; correctas alternator/radiator/headlight 30/30, todas sobre 0.84.**

---

## 3. ROBUSTEZ (variantes controladas)

41 imágenes originales × 12 transformaciones reproducibles (semilla fija 20260923) = **492 variantes**. CSV: `resultados_robustez.csv`; resumen `resumen_robustez.csv`.

| Transformación | Cantidad | Correctas | Incorrectas | Vacías | Conf media | Caída media vs original |
|---|---|---|---|---|---|---|
| A_resize_640x480 | 41 | 36 | 4 | 1 | 0.880 | 0.017 |
| B_perspectiva_leve | 41 | 37 | 2 | 2 | 0.922 | −0.012 |
| C_perspectiva_moderada | 41 | 38 | 2 | 1 | 0.899 | −0.003 |
| D_blur_leve | 41 | 36 | 3 | 2 | 0.910 | −0.000 |
| E_blur_moderado | 41 | 30 | 9 | 2 | 0.866 | 0.043 |
| F_contraste | 41 | 37 | 1 | 3 | 0.925 | 0.001 |
| G1_exposicion_alta | 41 | 37 | 2 | 2 | 0.898 | 0.011 |
| G2_exposicion_baja | 41 | 37 | 1 | 3 | 0.923 | 0.003 |
| H_ruido_sensor | 41 | 37 | 2 | 2 | 0.868 | 0.041 |
| I_jpeg_q35 | 41 | 37 | 1 | 3 | 0.924 | 0.002 |
| **J_escala_45 (objeto 45% del frame)** | 41 | **17** | **9** | **15** | 0.645 | **0.217** |
| **K_webcam_realista (combinación)** | 41 | **27** | **3** | **11** | 0.600 | **0.334** |

**Conclusiones de robustez:**
- Transformaciones individuales leves/moderadas (perspectiva, blur, contraste, exposición, ruido, JPEG) **no** destruyen la detección: 36–38/41 correctas.
- Las transformaciones que producen **`detecciones: []`** son las que **reducen el objeto en el frame** (J: 15 vacías; K: 11 vacías). El factor dominante es la **escala del objeto / resolución efectiva**, y su **combinación acumulativa** (K = escala 70% + perspectiva + blur + contraste + ruido + JPEG, caída media 0.334).
- A escala 45%, incluso con alta similitud digital, la conf pone el objeto por debajo del umbral técnico 0.25 o lo pierde.

---

## 4. ALTERNATOR (progresión de caída, holdout, conf oficial V2)

CSV completo: `artifacts/diagnostico_v2/alternator_progresivo.csv`. Resumen del punto de caída:

| Imagen (holdout) | ORIGINAL | RESIZE 640×480 | PERSPECTIVA | BLUR+JPEG+EXP | ESCALA_45 | WEBCAM COMBINADO | Primera caída |
|---|---|---|---|---|---|---|---|
| alt test 1 | alt .97 | .79 | .77 | .59 | **vacía** | — | vacías en ESCALA |
| alt test 2 | .90 | .78 | .80 | .62 | .58 | **vacía** | vacías en COMB |
| alt test 3 | .92 | **vacía** | — | .39 | .39 | .48 | vacías en RESIZE* |
| alt test 4 | .97 | .59 | .68 | .56 | **.38** | — | <0.55 en ESCALA |
| alt test 5 | .97 | .81 | .82 | .65 | **.27** | — | <0.55 en ESCALA |
| alt val 1 | .96 | **vacía** | .33 | — | .27 | — | vacías en RESIZE |
| alt val 2 | .59 | **vacía** | — | — | .25 | — | vacías en RESIZE |
| alt val 3 | .97 | .89 | .84 | .80 | .75 | **.28** | <0.55 en COMB |
| alt val 4 | .95 | **.43** | .65 | .45 | — | .35 | <0.55 en RESIZE |
| alt val 5 | .96 | **.47** | .70 | .42 | — | .55 | <0.55 en RESIZE |

\* test 3 resultó atípico: la primera etapa de la cadena (RESIZE con fondo gris) ya dio vacía, mientras etapas posteriores recuperaban detección.

**Puntos de caída observados:**
- **Bajo 0.55 (umbral backend):** aparece ya en RESIZE/PERSPECTIVA para algunos (val 2, val 4, val 5), y en ESCALA_45 / COMBINADO para el resto.
- **Bajo 0.25 (umbral técnico):** ESCALA_45 en test 5 (0.27) y val 2 (0.25).
- **`detecciones=[]`:** RESIZE en val 1/2 y test 3; ESCALA_45 en test 1; COMBINADO en test 1/2.
- **El punto crítico:** la **reducción de escala del objeto dentro del frame** (RESIZE/ESCALA) — coincide con webcam a 640×480 donde la pieza ocupa una fracción pequeña del sensor, agravada por la combinación de degradaciones.

---

## 5. HEATMAP — técnica, capa y justificación

- **Técnica seleccionada: EigenCAM** (no Grad-CAM).
- **Capa(s):** capas 16 (P3/8), 19 (P4/16) y 22 (P5/32) del neck de YOLO11n, que alimentan directamente el Detach head (`Detect` consume `[16,19,22]`). Se usó capa 16 (P3, stride 8) como referencia primaria por su mayor resolución espacial.
- **Por qué EigenCAM (no Grad-CAM):** para detección con YOLO no existe una función de objetivo escalar por clase simple tras NMS; Grad-CAM requiere backprop del logit de clase y sobre cabezas de detección ancladas es técnicamente frágil y propenso a implementación incorrecta. EigenCAM computa la **primera componente principal** (PCA) de las activaciones 2D de la capa objetivo **sin gradientes**, siendo agnóstico de clase y es la técnica estándar documentada para la familia Ultralytics/YOLO (p. ej. `rigvedrs/YOLO-V11-CAM`, `hotspotyolo`, `pytorch-gradcam` para YOLOv5). Captura las regiones que el modelo "ve" como relevantes en el backbone/neck.
- **Limitaciones:** (1) no es específico de clase — la PCA mezcla la relevancia global, no "por qué es un alternador"; (2) resolución 8× menor que la entrada (upsample bilinear); (3) no representa causalidad, solo correlación; (4) en los casos sin detección no hay clase que atribuir, solo actividad.

---

## 6. HEATMAP ALTERNATOR ORIGINAL (capa 16, overlaid, `alternator__original__layer16_heatmap.png`)

- **Predicción:** alternator · **Confianza:** 0.9696 · bbox [5,1,223,207]
- **Regiones relevantes (estadísticas de masa del cam):** activación concentrada dentro del bbox de la pieza (**frac en bbox 0.869**), centroide de masa en (0.487, 0.518) — centrado en la pieza; var_x 0.093, var_y 0.101 (masa compacta). La atención cubre la silueta/carcasa, no el fondo.

## 7. HEATMAP ALTERNATOR DEGRADADO / VACÍO

- **Degradado (K_webcam, `alternator__degradada_webcam...`):** predicción alternator 0.6947 · frac_en_bbox 0.952 · centroide (0.51, 0.50) — la atención sigue **en la pieza**, algo más compacta (0.079/0.084).
- **Vacíos (`alternator__vacia_escala`, `alternator__vacia_webcam`):** predicción [] · **frac_en_bbox 0.886 y 1.000**, centroide ≈ (0.50, 0.50).
- **Interpretación clave:** al degradar, la activación **no se dispersa ni se desplaza al fondo ni a los bordes**; permanece en el objeto. El problema **no es que el modelo "deje de mirar" la pieza**, sino que la confianza cae bajo los umbrales pese a seguir respondiendo a ella. (Heatmaps de radiator/headlight: igual, frac 1.0; headlight degradado conf 0.39 → <0.55.)

---

## 8. CAUSA PRINCIPAL DEL FALLO POR WEBCAM

- **Causa:** degradación por **reducción de escala/resolución efectiva del objeto dentro del frame webcam 640×480**, **combinada acumulativamente** con perspectiva, blur, contraste, ruido y compresión JPEG. El YOLO no ve la pieza "pequeña y degradada" con confianza suficiente: cae bajo 0.55 (→ `VISION_BAJA_CONFIANZA`) y en casos extremos bajo 0.25 (→ `detecciones=[]` → 422).
- **Evidencia:**
  - FASE 5: J_escala_45 → 15/41 vacías; K_webcam → 11/41 vacías; las demás transformaciones individuales → ≤3 vacías.
  - FASE 6: la primera caída de confianza del alternator se dispara en RESIZE/ESCALA (reducción de tamaño), no en blur/perspectiva/JPEG solos.
  - FASE 7: los heatmaps del caso vacío siguen activos sobre el objeto → no es pérdida de atención, es caída de confianza por objeto pequeño+degradado.
  - El threshold backend (0.55) es conservador y amplifica el problema: con 0.55 se rechazan detecciones correctas en el rango 0.45–0.55.
- **Nivel de certeza:** alto para "escala + combinación acumulativa + umbral 0.55"; el envío exacto de webcam (perspectiva real, resolución nativa, moiré de pantalla) no se pudo reproducir byte a byte, pero la simulación controlada reproduce el síntoma (detecciones [] y 422).

---

## 9. ¿EL PROBLEMA ES FALTA DE EPOCHS?

**NO.**

**Justificación:** el run terminó por early stopping (20 epochs sin mejora posterior a ep45) con val en meseta; las métricas val no estaban divergiendo, y el fallo por webcam pertenece a una distribución de dominio (objeto pequeño + degradación compuesta + resolución 640×480) que no está representada en el dataset de validación. Más epochs sobre el mismo dataset no cambian la distribución de entrada y no expondrían al modelo a estas variantes.

---

## 10. ¿SE NECESITA V3?

**SÍ** (si el objetivo es robustez webcam).

**Evidencia de FASE 3–7:** el modelo es excelente en dominio digital (30/30 correctas en holdout product; heatmaps concentrados), pero colapsa ante escala/JS degradados. La mezcla de dominios del dataset V2 (base CEB contexto + product + synthetic) explica que val mAP50 quede en 0.759 (mezclando contextos difíciles) y el entrenamiento no cubra el caso webcam.

## 11. SI SE NECESITA V3 — cambios exactos recomendados

**NO entrenar todavía. Recomendación para cuando se autorice V3:**

1. **Augmentations tipo cámara en entrenamiento** (los parámetros exactos a probar):
   - `perspective: 0.001 – 0.0005` (perspectiva leve; hoy `0.0`)
   - `degrees: 10 – 15` (rotation ligera; hoy `0.0`)
   - `shear: 5 – 10` (hoy `0.0`)
   - `translate: 0.2 – 0.3` (hoy 0.1)
   - `scale: 0.3 – 0.55` (hoy 0.5) + **reducir objeto a <50% del frame** en una fracción de batches
2. **Downsampling / resize controlado:** entrenar con `imgsz: 640` pero añadir pasos de **downscale a 320–416** en una fracción de los batches (simular objeto pequeño en sensor webcam).
3. **Compresión JPEG realista:** incorporar pasos de **encode JPEG con calidad 40–70** como transformación (vía preproceso/dataset custom) porque ultralytics no la incluye nativamente.
4. **Blur + ruido de sensor:** `mosaic`, `erasing` ya activos; añadir blur gaussiano leve y ruido gaussiano leve **compuesto** con las anteriores (K simulado) para cubrir el caso combinado.
5. **No subir VISION_CONFIDENCE_MIN** durante el rediseño; evaluar en la validación manual webcam si un ajuste fino del umbral (0.50) es necesario una vez el modelo mejore. (No recomendado cambiar sin evidencia nueva.)
6. **Evaluación con split tipo webcam:** añadir un pequeño split de validación simulado con la transformación K para medir la mejora objetivamente antes de declarar V3 lista.

---

## 12. ARTEFACTOS GENERADOS

- **CSV:**
  - `ia-service/artifacts/diagnostico_v2/manifest_seleccion_v2.csv`
  - `ia-service/artifacts/diagnostico_v2/variantes_manifest.csv`
  - `ia-service/artifacts/diagnostico_v2/resultados_robustez.csv` (492 filas)
  - `ia-service/artifacts/diagnostico_v2/resumen_robustez.csv`
  - `ia-service/artifacts/diagnostico_v2/alternator_progresivo.csv`
- **Manifest/JSON:** `manifest_resumen.json`, `heatmaps_report.json`, `heatmap_stats.json`
- **Predicciones/imágenes:** `original_anotadas/*.png` (41), `variantes_640x480/*.png` (492)
- **Heatmaps:** `heatmaps/*__layer{16,19,22}_heatmap.png` + reports (alternator orig/degradadas/vacías; radiator orig/degradada; headlight orig/degradada)
- **Documentación:** este archivo (`docs/modelo-ia/CV4_AUDITORIA_ROBUSTEZ_V2.md`)

## 13. ARCHIVOS MODIFICADOS / NUEVOS (solo scripts + artefactos + doc)

Nuevos: `ia-service/scripts/diagnostico_v2_common.py`, `diagnostico_v2_01_seleccion_baseline.py`, `diagnostico_v2_02_variantes.py`, `diagnostico_v2_03_robustez.py`, `diagnostico_v2_04_alternator.py`, `diagnostico_v2_05_heatmaps.py`, `diagnostico_v2_06_heatmap_stats.py`, carpeta `ia-service/artifacts/diagnostico_v2/**`, `docs/modelo-ia/CV4_AUDITORIA_ROBUSTEZ_V2.md`.

No se modificó backend funcional, frontend, FastAPI, contratos, umbrales, modelo V2, dataset V2 ni el logging temporal `[DIAG-VISION]` previo.

## 14. GIT

**NO se ejecutó `git add`, `commit`, `push` ni ninguna operación de git.**

## 15. CONCLUSIÓN

```
MODELO DIGITAL V2 FUNCIONA:                    SÍ  (holdout 30/30, conf alt 0.84–0.97)
ROBUSTEZ WEBCAM SUFICIENTE:                    NO  (J: 15/41 vacías; K: 11/41 vacías; calor en objeto, conf cae)
MÁS EPOCHS CON EL MISMO DATASET:               NO RECOMENDADO  (early stop; val en meseta; el problema es de dominio)
AUGMENTATIONS TIPO CÁMARA:                     RECOMENDADAS    (escala/objeto pequeño, perspectiva, JPEG, blur, ruido compuestos)
V3:                                            RECOMENDADA     (solo con dataset/augmentations webcam; parám. en §11)
```

**DETENERSE. No reentrenar. No iniciar CV-8.**