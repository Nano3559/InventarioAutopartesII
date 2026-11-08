# CONSTRUCCION Y VALIDACION DEL DATASET PROCESSED (MVPV1)

Fecha: 2026-09-22  
Script: `ia-service/scripts/build_processed_dataset.py`  
Registro: `ia-service/datasets/processed/processed_manifest.csv`  
Config YOLO: `ia-service/datasets/processed/dataset.yaml`

## Objetivo

Ensamblar el primer dataset de deteccion (YOLO) de 8 clases a partir de las fuentes ya auditadas y generar los splits `train`/`val`/`test` con **cero leakage**, conservando las fotografias multiclase originales. No incluye entrenamiento.

## Unidad de agrupacion: la fotografia original

Para Car Engine Bay la unidad de agrupacion es la **fotografia original**, no la clase.

- Cada fotografia tiene un `source_group_id` unico (SHA-256 de los bytes de la imagen).
- Una fotografia puede contener varias clases objetivo (p. ej. `air_filter + alternator + radiator`); en ese caso se copia **una sola vez** dentro de un unico split y su label procesado contiene **todas** las cajas de las clases objetivo presentes y aprobadas.
- No se crean copias de una misma fotografia para repartirlas en diferentes splits ni para alcanzar el objetivo de 200 por clase.

## Remapeo de Car Engine Bay

Del label original de Car Engine Bay se descartan las clases no objetivo y se remapean las cuatro usadas:

| ID original | Clase | ID final |
|---:|---|---:|
| 11 | alternator | 3 |
| 25 | oil_filter | 4 |
| 14 | air_filter | 5 |
| 13 | radiator | 6 |

## Esquema del manifest y multiclase

El manifest usa **una fila por fotografia procesada**. Para fotografias multiclase, `target_class` y `target_class_id` contienen la union separada por `+`.

Ejemplo real registrado en val:

```text
car_engine_bay__val__264.jpg
target_class:    alternator+oil_filter+radiator
target_class_id: 3+4+6
```

Label procesado (3 cajas en el mismo archivo):

```text
6 0.51415800 0.85709200 0.35521700 0.01815000
3 0.42644200 0.65054200 0.08988300 0.06655000
4 0.66080000 0.68679200 0.06436700 0.05785000
```

Columnas: `processed_image, processed_label, split, target_class, target_class_id, source_dataset, source_image, source_group_id, annotation_origin, is_synthetic, license, source_version, source_label`.

Por la representacion multiclase, la suma de imagenes por clase puede superar el total de imagenes del split (una misma fotografia cuenta en varias clases).

## Fuentes y splits

| Fuente | Registros | Split |
|---|---:|---|
| Sintetico (rembg U2-Net) brake_pad 200, brake_rotor 200, brake_caliper 200, oil_filter 194 | 794 | train solamente |
| Car Engine Bay real (MIT) | 754 | val/test por fotografia + train |
| Carparts-Seg headlight (CC BY 4.0) | 200 | respeta split original (160/20/20) |
| **Total** | **1748** | train 1612 / val 68 / test 68 |

Splits deterministas de Car Engine Bay (por fotografia, ordenados por `source_group_id`):

- `oil_filter` real: 3 val / 3 test (todas las fotos de oil se asignan a val/test; oil en train queda solo sintetico).
- `alternator`, `radiator`: 20 val / 20 test tomando primero fotos de clase unica.
- `air_filter`: 6 val / 6 test tomando primero fotos de clase unica.
- El resto va a `train`.

Las fotos multiclase de oil suman clases extra a val/test (p. ej. alternator val 21, test 23); se documenta como variacion aceptada del objetivo de 200, priorizando zero leakage y conservacion multiclase.

## Deduplicacion dentro de split

El dataset fuente Car Engine Bay contiene 5 pares de fotografias byte-identicas con nombres distintos. Se mantiene una unica copia por `(split, source_group_id)` conservando el primer registro deterministico.

## Resultados finales

| Clase | Train imgs | Train boxes | Val imgs | Val boxes | Test imgs | Test boxes |
|---|---|---:|---:|---:|---:|---:|---:|
| brake_pad | 200 | 200 | 0 | 0 | 0 | 0 |
| brake_rotor | 200 | 200 | 0 | 0 | 0 | 0 |
| brake_caliper | 200 | 200 | 0 | 0 | 0 | 0 |
| alternator | 187 | 190 | 21 | 24 | 23 | 23 |
| oil_filter | 194 | 194 | 3 | 3 | 3 | 3 |
| air_filter | 35 | 35 | 8 | 8 | 6 | 6 |
| radiator | 619 | 624 | 20 | 21 | 20 | 21 |
| headlight | 160 | 276 | 20 | 31 | 20 | 33 |

| Split | Imagenes | Boxes |
|---|---:|---:|
| train | 1612 | 1919 |
| val | 68 | 87 |
| test | 68 | 86 |
| **Total** | **1748** | **2092** |

## Controles de validacion

| Control | Resultado |
|---|---|
| Imagen-label 1:1 | OK (sin faltantes) |
| Labels vacios | 0 |
| Labels invalidos | 0 |
| IDs fuera de 0..7 | 0 |
| Coordenadas fuera de rango | 0 |
| Imagenes corruptas | 0 |
| Duplicados SHA-256 globales | 0 |
| Fotografias multiclase Car Engine Bay | 188 conservadas |
| Sinteticos en train / val / test | 794 / 0 / 0 |
| SOURCE LEAKAGE | 0 |
| SHA256 LEAKAGE | 0 |
| SYNTHETIC IN VAL | 0 |
| SYNTHETIC IN TEST | 0 |

## Salidas

```text
ia-service/datasets/processed/
  images/{train,val,test}/
  labels/{train,val,test}/
  previews/              21 previews con cajas dibujadas
  dataset.yaml
  processed_manifest.csv
```

`dataset.yaml` valido con `nc: 8` y los nombres 0..7 del plan.

## Limitaciones conocidas

- `brake_pad`, `brake_rotor`, `brake_caliper` tienen val/test vacios por no disponer de ground truth real auditado; se miden solo con el rendimiento general del modelo.
- `oil_filter` en train es 100% sintetico (las 6 fotos reales quedaron en val/test).
- `air_filter` tiene muestras reales limitadas (49 fotos totales).
- El desbalance por clase es consciente: se priorizo cero leakage, conservacion multiclase y ground truth real antes que balance.
- Los previews son 21 archivos porque algunas filas multiclase generan el mismo nombre de preview.

## Reproducibilidad

- Script: `ia-service/scripts/build_processed_dataset.py`.
- Fuentes: `synthetic/manifests/synthetic_manifest.csv`, labels auditados de Car Engine Bay (temporal de staging), `converted/headlight/headlight_manifest.csv`.
- Imagenes de Car Engine Bay faltantes localmente descargadas en staging temporal desde `khaledchawa/car-engine-bay-pictures` (MIT); no se modificaron `datasets/raw/` ni `datasets/external/`.

Este documento cierra la construccion de `processed/`. No se entrena YOLO, no se hacen commits ni push sin autorizacion.