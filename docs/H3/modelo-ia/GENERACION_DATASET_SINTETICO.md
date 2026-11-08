# GENERACION CONTROLADA DEL DATASET SINTETICO

Fecha: 2026-09-22  
Metodo: `rembg[cpu]` 2.0.85 con U2-Net  
Semilla: `20260922`

## Objetivo

Generar datos sintéticos de entrenamiento para las cuatro clases aprobadas por los pilotos de segmentación: `brake_pad`, `brake_rotor`, `brake_caliper` y `oil_filter`. Este lote no se incorpora todavía a `processed/` ni se utiliza como ground truth de test.

## Cantidades

| Clase | Composiciones |
|---|---:|
| brake_pad | 200 |
| brake_rotor | 200 |
| brake_caliper | 200 |
| oil_filter | 194 |
| **Total sintético** | **794** |

`oil_filter` conserva además 6 imágenes reales con boxes de Car Engine Bay fuera de este lote sintético.

## Fuentes RAW y filtrado

Se procesaron las fuentes RAW locales de `dataset_manifest.csv` mediante rembg. Se aceptaron máscaras con foreground no vacio, area razonable y caja no extrema. Las fuentes aceptadas y utilizadas fueron:

| Clase | Fuentes aceptadas | Fuentes rechazadas |
|---|---:|---:|
| brake_pad | 114 | 84 |
| brake_rotor | 81 | 105 |
| brake_caliper | 84 | 100 |
| oil_filter | 95 | 84 |

Todas las composiciones registran `source_group_id` SHA-256 de la imagen RAW para evitar perder trazabilidad y permitir splits posteriores sin leakage por pieza fuente.

## Fondos y transformaciones

No se utilizaron fondos de Internet. Los fondos fueron generados localmente mediante patrones procedurales: gris, azul grisaceo, carton, metal, verde grisaceo y banco de trabajo. Su licencia/origen es `NONE_LOCAL_GENERATED`.

Transformaciones moderadas y reproducibles:

- rotacion entre -18 y +18 grados;
- escalas entre 0.68 y 0.90;
- posiciones aleatorias dentro del canvas sin cortar deliberadamente;
- sin deformacion no uniforme;
- sin efectos agresivos de color.

La caja se calcula despues de todas las transformaciones desde el canal alfa final. No se usa una caja de imagen completa por defecto.

## Salida

```text
ia-service/datasets/synthetic/
  images/
  labels/
  masks/
  previews/
  manifests/
    synthetic_manifest.csv
    rejected_sources.csv
```

Se generaron 40 previews, 10 por clase. Los labels son experimentales y usan IDs finales 0, 1, 2 y 4.

## Controles

- Imagenes sinteticas: 794.
- Labels: 794.
- Labels vacios: 0.
- Labels invalidos: 0.
- Coordenadas fuera de rango: 0.
- Imagenes faltantes: 0.
- Duplicados exactos SHA-256: 0.
- Fuentes distintas: brake_pad 114, brake_rotor 81, brake_caliper 84, oil_filter 95.
- `processed/`: intacto y no creado.

## Rechazos y limitaciones

Se rechazaron 373 fuentes por mascara vacia, foreground demasiado pequeno o foreground/caja demasiado grande. El rechazo fue automatico, sin corregir mascaras manualmente. U2-Net puede conservar artefactos de fondo o perder detalles finos; por ello las composiciones siguen siendo datos sintéticos y requieren validacion antes de entrenar.

El lote no demuestra rendimiento real de webcam. El test real debe mantenerse separado y contener escenarios no sinteticos.

## Reproducibilidad

Script: `ia-service/scripts/generate_synthetic_dataset.py`.  
Semilla: `20260922`.  
Manifest principal: `ia-service/datasets/synthetic/manifests/synthetic_manifest.csv`.

Este lote no se integra aun a `processed/`, no se entrena YOLO y no se modifican RAW, `annotation_batch`, `converted/headlight`, backend, frontend, Prisma ni Docker.
