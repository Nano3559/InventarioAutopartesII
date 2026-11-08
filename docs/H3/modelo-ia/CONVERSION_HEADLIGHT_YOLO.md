# CONVERSION HEADLIGHT A YOLO DETECTION

Fecha: 2026-09-22  
Fuente: Ultralytics Carparts-Seg  
Licencia: CC BY 4.0

## Fuente

Dataset externo descargado desde la URL documentada por el YAML oficial de Ultralytics:

```text
https://github.com/ultralytics/assets/releases/download/v0.0.0/carparts-seg.zip
```

Ubicacion de trabajo:

```text
ia-service/datasets/external/carparts_seg/
```

El dataset externo original se mantuvo separado y no fue modificado.

## Clases originales

Se utilizaron exclusivamente:

- ID 12: `front_left_light`.
- ID 13: `front_light`.
- ID 15: `front_right_light`.

Se excluyeron `back_left_light`, `back_light` y `back_right_light`, porque son luces traseras.

## Clase final

Las tres clases delanteras se unificaron en:

```text
7 headlight
```

Cada instancia original genera una bounding box independiente. Si una imagen contiene dos o mas faros, no se fusionan.

## Algoritmo de conversion

Las coordenadas de segmentacion estaban normalizadas entre 0 y 1. Para cada poligono se calcularon:

```text
xmin = min(x)
ymin = min(y)

cx = (xmin + xmax) / 2
cy = (ymin + ymax) / 2
width = xmax - xmin
height = ymax - ymin
```

El label final usa únicamente:

```text
7 cx cy width height
```

No se dividieron nuevamente las coordenadas entre el ancho o alto porque ya estaban normalizadas.

## Conteos convertidos

| Split final | Imagenes | Bounding boxes |
|---|---:|---:|
| train | 2,200 | 3,324 |
| val | 284 | 429 |
| test | 215 | 313 |
| **Total** | **2,699** | **4,066** |

Conteo por clase original:

| Clase original | ID | Imagenes | Instancias |
|---|---:|---:|---:|
| front_left_light | 12 | 504 | 504 |
| front_light | 13 | 2,057 | 3,088 |
| front_right_light | 15 | 474 | 474 |

## Manifest y estructura

```text
ia-service/datasets/converted/headlight/
  images/train/
  images/val/
  images/test/
  labels/train/
  labels/val/
  labels/test/
  previews/
  headlight_manifest.csv
```

El manifest conserva fuente, imagen original, destino, split original/final, IDs y nombres originales, ID final 7, cantidad de instancias, licencia y estado de conversion.

## Validaciones

- Correspondencia imagen/label: correcta para 2,699/2,699.
- Labels vacios: 0.
- Labels invalidos: 0.
- IDs distintos de 7: 0.
- Coordenadas fuera de rango: 0.
- Cajas con width o height no positivos: 0.
- Bounding boxes que no contienen completamente su poligono: 0; la caja se calculo con min/max del mismo poligono.
- Duplicados SHA-256 entre splits: 0.
- Misma imagen en mas de un split: 0 observado.

## Previews

Se generaron 15 previews, cinco por split:

```text
ia-service/datasets/converted/headlight/previews/
```

La inspeccion de la muestra mostro los poligonos originales y sus cajas envolventes correctamente alineadas en los cinco casos piloto. El piloto no reemplaza una revision visual mas amplia antes de entrenar.

## Estado

La conversion completa controlada de `headlight` esta preparada fuera de `processed/`. No se entreno YOLO, no se modificaron RAW, `annotation_batch`, `processed`, backend, frontend, Prisma ni Docker.
