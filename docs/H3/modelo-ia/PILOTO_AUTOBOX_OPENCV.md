# PILOTO AUTOBOX OPENCV

Proyecto: RepuestoPro  
Fecha: 2026-09-22  
Alcance: experimento controlado, sin incorporar labels al dataset final.

## 1. Objetivo

Evaluar si imagenes de clasificacion con una pieza aparentemente aislada pueden producir bounding boxes automaticamente mediante OpenCV, sin anotacion manual y sin modificar RAW.

Clases evaluadas: `brake_pad`, `brake_rotor`, `brake_caliper` y `oil_filter`.

## 2. Muestra

Se seleccionaron reproduciblemente cinco imagenes aprobadas por clase desde `ia-service/datasets/review/`, para un total de 20 imagenes. Las copias de trabajo se guardaron en:

```text
ia-service/datasets/autobox_pilot/images/
ia-service/datasets/autobox_pilot/previews/
ia-service/datasets/autobox_pilot/labels/
```

No se modificaron `datasets/raw/`, `datasets/annotation_batch/` ni las 49 anotaciones reales de `air_filter`.

## 3. Algoritmo

El script `ia-service/scripts/autobox_pilot.py` uso:

1. estimacion del color de fondo a partir de los bordes;
2. diferencia de color contra el fondo;
3. umbral de Otsu con limites de seguridad;
4. operaciones morfologicas de apertura/cierre;
5. contornos externos y componentes conectados;
6. seleccion del componente significativo mas grande;
7. `cv2.boundingRect` y normalizacion YOLO.

Una propuesta se rechazo si no habia componente significativo o si habia componentes grandes ambiguos. Las propuestas aceptadas no se consideran ground truth; son exclusivamente preanotaciones experimentales.

## 4. Criterios de seguridad

Se rechazo una propuesta cuando:

- no habia componente significativo;
- habia multiples componentes grandes ambiguos;
- el componente tocaba todos los bordes;
- el area de la caja era excesivamente grande o pequena.

Las cajas casi completas o visualmente incorrectas no deben pasar a un dataset final aunque el algoritmo las marque `ACCEPTED`; por eso se realizo inspeccion visual de las previews.

## 5. Resultados

| Clase | Evaluadas | ACCEPTED | REJECTED | Aceptacion | Area media de cajas aceptadas | Evaluacion visual |
|---|---:|---:|---:|---:|---:|---|
| brake_pad | 5 | 4 | 1 | 80% | 39.56% | MALA |
| brake_rotor | 5 | 4 | 1 | 80% | 57.80% | MALA |
| brake_caliper | 5 | 2 | 3 | 40% | 45.04% | MALA |
| oil_filter | 5 | 5 | 0 | 100% | 33.70% | MALA |

Total: 20 imagenes, 15 propuestas marcadas `ACCEPTED` y 5 `REJECTED`.

### Ejemplos observados

- `brake_pad__001.jpg`: la caja captura solo una zona inferior, no toda la pastilla.
- `brake_pad__002.jpg`: la caja ocupa una franja grande y no representa de forma confiable el objeto completo.
- `brake_rotor__006.jpg` y `brake_rotor__007.jpg`: cajas amplias/parciales, con riesgo de incluir fondo o excluir el contorno.
- `brake_caliper__015.jpg`: la caja captura una region pequena, no el caliper completo.
- `oil_filter__017.jpg` y `oil_filter__019.jpg`: se detectaron componentes internos o parciales en vez del filtro completo.

Las previews se encuentran en `ia-service/datasets/autobox_pilot/previews/`. El detalle por imagen, bbox y motivo de rechazo esta en `ia-service/datasets/autobox_pilot/autobox_results.csv`.

## 6. Viabilidad por clase

- `brake_pad`: **NO ESCALAR**. La mascara por diferencia de fondo no delimita consistentemente la pieza.
- `brake_rotor`: **NO ESCALAR**. Los agujeros, textura y fondos producen cajas parciales o demasiado amplias.
- `brake_caliper`: **NO ESCALAR**. La forma compleja y fondos instalados generan componentes ambiguos.
- `oil_filter`: **NO ESCALAR**. Aunque todas las muestras produjeron una propuesta, varias cajas corresponden a componentes parciales y no al objeto completo.

## 7. Limitaciones

- OpenCV no comprende la semantica de una pieza.
- El mayor componente no siempre es el objeto principal.
- Logos, agujeros, sombras y texturas generan componentes separados.
- El fondo puede ser visualmente similar a la pieza.
- Una clase conocida evita clasificacion, pero no resuelve localizacion.
- La aceptacion geometrica no equivale a calidad de la caja.

## 8. Conclusion

El metodo OpenCV evaluado **no es suficientemente fiable para escalar** a las imagenes restantes de estas cuatro clases. No se generaron labels definitivos ni se incorporaron las propuestas al dataset de entrenamiento.

El piloto confirma que la estrategia automatica de foreground puede servir como herramienta exploratoria o para casos muy controlados, pero no reemplaza una fuente object detection ya anotada ni una anotacion validada cuando se necesitan cajas de calidad.
