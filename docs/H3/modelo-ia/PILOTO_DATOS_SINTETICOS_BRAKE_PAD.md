# PILOTO DE DATOS SINTETICOS — BRAKE PAD

Fecha: 2026-09-22  
Clase: `brake_pad` ID 0  
Alcance: experimento de segmentacion foreground y composicion sintetica; no es ground truth final.

## Metodo

Se utilizo `rembg` 2.0.85 con el modelo U2-Net en el entorno aislado `ia-service/.venv`. El modelo realiza foreground removal mediante segmentacion automatica; no se uso GroundingDINO, LabelImg ni el algoritmo OpenCV descartado.

Para cada una de cinco copias de imagenes aprobadas de `brake_pad`:

1. se conservo la imagen original en `originals/`;
2. se genero una mascara alfa y un cutout PNG;
3. se aplico una rotacion leve y una escala moderada;
4. se compuso el objeto sobre un fondo simple local;
5. se calculo la caja desde los pixeles no transparentes de la mascara transformada;
6. se genero un label YOLO experimental con clase 0.

No se modifico RAW, `annotation_batch`, `processed/` ni ningun label real.

## Dependencia y ubicacion

- Dependencia: `rembg[cpu]` 2.0.85.
- Runtime: `ia-service/.venv` Python 3.11.
- Modelo descargado por rembg: U2-Net, almacenado en la cache local del usuario, no en el repositorio.
- Fondos: colores solidos generados localmente; no se descargaron fondos externos.

## Resultados individuales

| Imagen | Mask | Box | Observacion |
|---|---|---|---|
| brake_pad__001.jpg | BUENA | BUENA | Silueta principal conservada |
| brake_pad__002.jpg | BUENA | BUENA | Contorno y pestañas visibles conservados |
| brake_pad__003.jpg | ACEPTABLE | BUENA | Pequena inclusion/artefacto fino en el contorno |
| brake_pad__004.jpg | BUENA | BUENA | Silueta limpia |
| brake_pad__005.jpg | ACEPTABLE | BUENA | Ligera inclusion de fondo en el borde inferior |

Resultado agregado:

- Imagenes evaluadas: 5.
- MASK BUENA: 3.
- MASK ACEPTABLE: 2.
- MASK MALA: 0.
- BOX BUENA: 5.
- BOX MALA: 0.
- Criterio minimo 4/5: cumplido, considerando BUENA o ACEPTABLE para mask y BUENA para box.

## Archivos del piloto

```text
ia-service/datasets/synthetic_pilot/brake_pad/
  originals/
  masks/
  cutouts/
  composites/
  previews/
  labels/
  synthetic_pilot_results.csv
```

Las previews muestran cada composicion, clase `brake_pad` y bounding box final. Las coordenadas se derivaron del alfa transformado y no de una caja que cubra automaticamente la imagen.

## Decision

**DATOS SINTETICOS VIABLES: SI, COMO EXPERIMENTO CONTROLADO.**

El resultado 5/5 cumple el umbral minimo para continuar evaluando la tecnica, pero no autoriza escalarla todavia. Las dos mascaras aceptables presentan pequenas inclusiones de fondo y deben considerarse una limitacion del modelo U2-Net. Los labels generados son datos sinteticos de entrenamiento, no ground truth independiente.

No se procesaron `brake_rotor`, `brake_caliper` ni `oil_filter`. No se generaron cientos de imagenes y no se entreno YOLO.
