# CV4 — YOLO V3 `repuestopro_yolo11n_v3_webcam_robust`

> Mejora de robustez webcam (objeto pequeño + degradaciones tipo cámara) sin perder el rendimiento digital de V2. Entrenado con fine-tune desde V2 (`best.pt`). Uso de V3 **pendiente de autorización** para runtime/FastAPI.

## Resumen ejecutivo

V3 resuelve el problema detectado en la auditoría V2 (objeto pequeño → degradación acumulada → umbral 0.55):

| Métrica (holdout webcam-sim, 41 imgs) | V2 | V3 | Δ |
|---|---|---|---|
| `J_escala_45` — detecciones vacías | 15/41 | **1/41** | −93% |
| `K_webcam_realista` — detecciones vacías | 13/41 | **4/41** | −69% |
| `J` por encima de umbral 0.55 | 15/41 | **33/41** | +18 |
| `K` por encima de umbral 0.55 | 16/41 | **33/41** | +17 |
| `J` confianza media | 0.645 | **0.744** | +0.10 |
| `K` confianza media | 0.626 | **0.799** | +0.17 |

Regresión digital controlada y sin colapso de clase. **Veredicto: CUMPLE los criterios de aceptación (sección 12).**

## 1. Dataset por clase

Dataset independiente `ia-service/datasets/processed_v3/` (se respeta el manifest V2, no se modifica V2).

| Clase | Train V2 | Train V3 | Val | Test |
|---|---|---|---|---|
| brake_pad | 200 | 630 | 3 | 3 |
| brake_rotor | 200 | 630 | 3 | 3 |
| brake_caliper | 200 | 630 | 4 | 2 |
| alternator | 268 | 698 | 21 | 22 |
| oil_filter | 194 | 624 | 5 | 4 |
| air_filter | 0 | 0 | 5 | 6 |
| radiator | 665 | 1095 | 22 | 18 |
| headlight | 369 | 799 | 25 | 25 |
| multi-clase (context) | 182 | 182 | 3 | 2 |
| **Total** | **2278** | **5288** | **91** | **85** |

Total filas V3: **5464** (train 5288, val 91, test 85). Originales V2 copiados: 2454 (2278 train + val + test). Aumentadas: **3010**, todas sobre train.

- `air_filter` sigue **sin imágenes de entrenamiento** (gap preexistente de V2; sin etiquetado manual). Se mantiene: clase congelada, misma semántica; evaluación propia (val 5 / test 6) y smoke OK.
- Las filas multi-clase (imágenes de contexto con varias etiquetas) se copian como originales pero **no se aumentan** (transformar el canvas rompería las etiquetas de los demás objetos). No se modificó ninguna caja: se reutilizan las anotaciones YOLO o se descarta la variante.
- Dominios: originales con su `domain` V2 (synthetic/context/product); variantes con `v3_domain="webcam_aug"`.

## 2. Augmentations (tipo cámara, offline, reproducibles)

Solo sobre imágenes de **train**; val/test intactos. Transformaciones matemáticas de la caja (homografía para perspectiva/rotación/shear, reescala para resize/translate) y **validación** del bbox resultante: `0 <= cx,cy <= 1`, `0 < w,h <= 1`, visibilidad `area >= 1.2%`, corte de borde ≤ 5%; variante descartada si invalida.

Cuotas por clase (total 430/clase): small 90, geo 90, downsample 90, webcam 90, photo 30, blur_noise 20, jpeg 20.

| Tipo | Descripción | En dataset |
|---|---|---|
| `small` | Objeto en canvas 640×480 al 70 / 55 / 45 / 35% (mezcla de tamaños, no todo mínimo) | 630 |
| `geo` | Rotación ±6-12°, shear ±4-7°, perspectiva 0.02 (interpretación offline), translate ±0.1 | 630 |
| `downsample` | Objeto a 70% + reescala 480/416/320 ↑640 (pérdida de resolución webcam) | 630 |
| `photo` | Exposición +15-40% / −25-45% / contraste 0.6-0.85 | 210 |
| `blur_noise` | Gaussiano k=3/5 + ruido sensor σ2-7 | 140 |
| `jpeg` | Calidad 40-70 | 140 |
| `webcam` | Compuesta: scale 35-70%, perspectiva, downsample, blur, ruido, exposición 0.75-1.15, JPEG 40-70 (aleatoriedad controlada, **no** degradación máxima en todas) | 630 |

Generador: `ia-service/scripts/build_dataset_v3.py` (semilla `20260923`, determinista por imagen).

## 3. Entrenamiento

- Init: **fine-tune desde V2 `best.pt`** (opción A). Justificación: misma tarea/dominio; conserva el conocimiento digital convergido y adapta con las nuevas variantes webcam. (Opción B descartada: resetearía el dominio aprendido.)
- Comando: `YOLO(v2_best).train(data=processed_v3/dataset.yaml, epochs=100, patience=20, imgsz=640, batch=16, device=0, seed=20260923, workers=8)`. Run: `runs/detect/repuestopro_yolo11n_v3_webcam_robust`.
- **Early stop en epoch 21; mejor época = 1** (fitness). best.pt = época 1: mAP50 0.7395, mAP50-95 0.6286, P 0.8146, R 0.7151. Aumentaciones YOLO adicionales activadas por defecto (hsv, fliplr, mosaic, erasing), igual que V2.
- 21 epochs en 0.31 h (RTX 4050 laptop, 6.1 GiB).
- Nota de proceso: los dataloaders de Windows requieren el guard `if __name__ == "__main__":` en el script de entrenamiento (falló la primera vez por spawn de workers).

## 4. Métricas digitales (val, 91 imgs)

| Clase | V2 mAP50 / mAP50-95 | V3 mAP50 / mAP50-95 | Δ mAP50 |
|---|---|---|---|
| all | 0.759 / 0.643 | **0.741 / 0.629** | −0.018 |
| brake_pad | 0.995 / 0.840 | 0.995 / 0.907 | 0.000 |
| brake_rotor | 0.995 / 0.962 | 0.995 / 0.929 | 0.000 |
| brake_caliper | 0.995 / 0.920 | 0.895 / 0.874 | −0.100 |
| alternator | 0.703 / 0.524 | 0.655 / 0.446 | −0.048 |
| oil_filter | 0.625 / 0.574 | 0.625 / 0.610 | 0.000 |
| air_filter | 0.582 / 0.433 | 0.590 / 0.435 | +0.008 |
| radiator | 0.441 / 0.331 | 0.419 / 0.278 | −0.022 |
| headlight | 0.734 / 0.564 | 0.755 / 0.554 | +0.021 |

Recall global sube (0.684 → 0.715). Compresión leve de confianza en fotométricas (reflejada en mAP50-95). Sin colapso de ninguna clase.

## 5. Product holdout (split test, 85 imgs)

| Clase | V2 P / R / mAP50 / mAP50-95 | V3 P / R / mAP50 / mAP50-95 |
|---|---|---|
| all | 0.790 / 0.690 / 0.790 / 0.640 | 0.896 / 0.661 / 0.775 / 0.630 |
| alternator | 0.661 / 0.489 / 0.542 / 0.384 | 0.774 / 0.542 / 0.583 / 0.385 |
| radiator | 0.659 / 0.474 / 0.583 / 0.414 | 1.000 / 0.363 / 0.604 / 0.380 |
| headlight | 0.733 / 0.684 / 0.734 / 0.470 | 0.955 / 0.562 / 0.735 / 0.452 |

Precisión mejora notablemente (menos falsos positivos). Alternator producto mejora.

## 6. Webcam sim holdout (41 imgs, seed holdout 20261922)

Transformaciones A–K idénticas a la auditoría; archivos separados, **no** en train, **sin** semejanza byte a byte con el entrenamiento (leakage 0, sección 11).

| Transformación | correctas V2→V3 | vacías V2→V3 | sobre 0.55 V2→V3 | conf media V2→V3 |
|---|---|---|---|---|
| A_resize_640x480 | 36→34 | 1→3 | 38→35 | 0.880→0.896 |
| B_perspectiva_leve | 38→34 | 1→4 | 38→36 | 0.903→0.903 |
| C_perspectiva_moderada | 37→37 | 2→3 | 37→36 | 0.915→0.894 |
| D_blur_leve | 36→34 | 2→2 | 38→36 | 0.910→0.855 |
| E_blur_moderado | 30→26 | 2→3 | 38→34 | 0.866→0.826 |
| F_contraste | 37→34 | 3→3 | 37→34 | 0.925→0.826 |
| G1_exposicion_alta | 37→34 | 2→4 | 38→33 | 0.898→0.852 |
| G2_exposicion_baja | 37→33 | 3→3 | 37→32 | 0.923→0.812 |
| H_ruido_sensor | 37→32 | 3→3 | 37→34 | 0.895→0.813 |
| I_jpeg_q35 | 37→35 | 3→2 | 37→36 | 0.924→0.858 |
| **J_escala_45** | **17→30** | **15→1** | **15→33** | **0.645→0.744** |
| **K_webcam_realista** | **24→32** | **13→4** | **16→33** | **0.626→0.799** |
| ORIGINAL | 37→35 | 2→2 | 38→36 | 0.909→0.854 |

Resultados por imagen: `artifacts/diagnostico_v3/webcam_holdout_resultados_{v2,v3}.csv`; resumen: `webcam_holdout_resumen_{v2,v3}.csv`.

## 7. J_escala_45

Vacías **15 → 1**, correctas 17 → 30, sobre 0.55 15 → 33. La única vacía restante corresponde a un objeto extremadamente pequeño tras escalado; el resto ahora se detecta por encima del umbral de negocio.

## 8. K_webcam

Vacías **13 → 4**, correctas 24 → 32, sobre 0.55 16 → 33, conf media 0.626 → 0.799. El 80% de las imágenes webcam compuestas pasan el umbral 0.55 (antes 39%).

## 9. Alternator (cascada progresiva)

Progresión por etapas (10 imgs alternator val/test). Comportamiento V2 → V3:

- V2: caída temprana en `RESIZE_640x480`/`ESCALA_45` (varias **vacías** a mitad de cascada); ej. test1 ESCALA_45 = sin detección.
- V3: **sin detecciones vacías intermedias**; `ESCALA_45` conf 0.54-0.88; sólo el paso final `WEBCAM_COMBINADO` baja de 0.55 (conf 0.28-0.43), pero sigue detectando clase correcta.
- Smoke alternator webcam: conf 0.59 (V2) → **0.91** (V3).

CSV: `artifacts/diagnostico_v3/alternator_progresivo_{v2,v3}.csv`.

## 10. Heatmaps (EigenCAM)

Técnica: EigenCAM (PCA sobre activaciones post-convolucionales; sin gradientes — apropiada para cabezales YOLO tipo Detect). Capas 16/19/22 (entradas P3/P4/P5 del head), primaria 16. Resolución ≈ 1/8; no es específica de clase; no implica causalidad.

Caso | Predicción V2 → V3 (conf) | frac_en_bbox (cap 16)
|---|---|---|
| alternator original | 0.970 → 0.972 | 0.869 |
| alt perspectiva moderada | 0.973 → 0.959 | 0.898 |
| alt webcam degradada | 0.665 → 0.912 | 0.956 |
| **alt J_escala_45** | **sin detección → 0.850** | 0.886 |
| **alt K_webcam (val2)** | **sin detección → 0.628** | 1.000 |
| radiator original / degradada | 0.943 → 0.925 / 0.857 → 0.931 | 1.000 |
| headlight original / degradada | 0.958 → 0.960 / 0.532 → 0.878 | 1.000 |

Conclusión: la activación permanece concentrada en la pieza en ambos modelos (V3 no "aprende a mirar mejor", sino que ajusta la decisión/umbral efectivo para las variantes webcam — las cajas deformadas y pequeñas ahora superan 0.55-0.25 que antes quedaban justo por debajo).

## 11. Regresiones por clase

- Digital: caídas menores en brake_caliper (mAP50 0.995→0.895, n=4) y alternator (0.703→0.655); estables/mejores en el resto. Recuperación por recall.
- Product holdout: alternator y radiator mejoran; headlight estable.
- Fotometrías sueltas (F/G/H, ±3-5 correctas) levemente por debajo de V2: trade-off aceptado por la ganancia en J/K (las 2 transformaciones que definían el fracaso webcam).
- `air_filter`: sin regresión (0.582→0.590 digital; smoke correcta).

## 12. Criterios de aceptación (todos juntos)

| Criterio | Estado |
|---|---|
| A. webcam_sim mejora claramente | ✅ J y K: vacías 15→1 y 13→4; conf media +0.10/+0.17 |
| B. detecciones vacías bajan significativamente | ✅ −93%/−69% en J/K; total A–K 52→37 vacías |
| C. alternator webcam mejora | ✅ sin vacías en cascada; smoke 0.59→0.91 |
| D. sin colapso de clase | ✅ 8/8 clases operativas; métricas digitales y smoke OK |
| E. sin regresión digital grave | ✅ mAP50 0.759→0.741 (−2%); recall sube; P product +0.10 |
| F. 0 leakage | ✅ exact cross-split 0, duplicados 0, holdout→train sha 0 |
| G. inferencia YOLO11n/FastAPI | ✅ `.pt` carga en YOLO; misma API/umbrales (sin cambios al sistema) |

## 13. Resultado

**APROBADO (condicional)**. V3 cumple los 7 criterios. Ganancia webcam real sin sacrificio grave de lo digital. **Pendiente e implementación en runtime**: no se cambió FastAPI a V3, no se tocaron cervezas de backend/frontend, no se modificaron umbrales (técnico 0.25 / negocio 0.55). La activación en producción y la prueba E2E real requieren **autorización explícita** (próxima etapa CV-8).

## 14. Archivos

Nuevos:
- `ia-service/scripts/build_dataset_v3.py`, `diagnostico_v3_01_webcam_holdout.py`, `diagnostico_v3_02_eval_webcam.py`, `diagnostico_v3_03_alternator.py`, `diagnostico_v3_04_heatmaps.py`, `diagnostico_v3_05_heatmap_stats.py`, `diagnostico_v3_06_smoke.py`, `launch_train.py`, `_entrenar_v3.py`.
- `ia-service/datasets/processed_v3/` (imágenes + labels + manifest + `report.json` + `dataset.yaml`).
- `ia-service/runs/detect/repuestopro_yolo11n_v3_webcam_robust/` (best.pt, results.csv, args.yaml, curvas).
- `ia-service/artifacts/diagnostico_v3/` (holdout 533 archivos, manifiestos, resultados v2/v3, alternator, heatmaps, stats, smoke, val logs, entrenamiento_v3.log).
- `docs/modelo-ia/CV4_MODELO_V3_WEBCAM_ROBUST.md` (este documento).

No modificados en esta tarea: backend/frontend/mobile, contratos, umbrales, migrations, V2.

## 15. Git

Sin `git add/commit/push` (los ejecuta Ross manualmente). Estado actual sin cambios de esta tarea sobre archivos trackeados (los `M` de `backend/src/modules/vision/vision.service.ts`, `ia-service/app/*` y `frontend/*` provienen de tareas previas E2E/auditoría). `datasets/processed_v3/`, `runs/detect/...v3.../` y `artifacts/diagnostico_v3/` están dentro de `.gitignore`/son voluminosos y no se commitean.

## Recomendaciones / limitaciones

1. `air_filter` sigue sin datos de entrenamiento (V2 y V3): para cerrar esa brecha se necesita nuevo dataset (autorizado) o síntesis acordada — no se hace ahora.
2. Las fotometrías aisladas (F/G/H) perdieron ~3-5 aciertos: si se prioriza el catálogo digital, evaluar aumentar peso de variantes `small` con exposición controlada.
3. `J_escala_45` aún tiene 1 vacía (objeto mínimamente pequeño): aceptable; monitorear en la prueba webcam real.
4. Próximo paso (CV-8, NO iniciado): prueba E2E real con webcam previa autorización.