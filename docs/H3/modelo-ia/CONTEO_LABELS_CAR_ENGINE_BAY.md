# CONTEO DE LABELS CAR ENGINE BAY

Dataset: `khaledchawa/car-engine-bay-pictures`  
Version: 2  
Licencia: MIT  
Fecha de auditoria: 2026-09-22

## Metodo

Se obtuvo el listado completo mediante Kaggle CLI autenticado con `KAGGLE_API_TOKEN`. Se encontraron 1,201 archivos bajo `labels/labels/*.txt`. Se descargaron individualmente solo esos TXT a una carpeta temporal fuera del repositorio; no se descargaron JPG ni el ZIP del dataset.

Cada linea se valido como YOLO: `class_id x_center y_center width height`. El porcentaje usa 1,201 imagenes etiquetadas como denominador.

| ID | Clase | Imagenes positivas | Instancias | % de imagenes | Min. | Max. | Promedio |
|---:|---|---:|---:|---:|---:|---:|---:|
| 9 | Air Filter Cover | 666 | 740 | 55.45% | 1 | 4 | 1.11 |
| 11 | Alternator | 233 | 240 | 19.40% | 1 | 2 | 1.03 |
| 13 | Radiator | 664 | 672 | 55.29% | 1 | 2 | 1.01 |
| 14 | Air Filter | 49 | 49 | 4.08% | 1 | 1 | 1.00 |
| 25 | Oil Filter | 6 | 6 | 0.50% | 1 | 1 | 1.00 |

## Controles de integridad

- TXT encontrados: 1,201.
- TXT descargados correctamente: 1,201.
- TXT vacios: 0.
- Lineas YOLO invalidas: 0.
- IDs fuera del rango 0–25: 0.
- Coordenadas fuera del rango normalizado: 0 detectadas.
- JPG sin TXT correspondiente: 0 observados por manifiesto.
- TXT sin JPG correspondiente: 0 observados por manifiesto.
- IDs encontrados: todos entre 0 y 25; no se encontraron IDs fuera de rango.
- Imagenes que contienen simultaneamente ID 9 e ID 14: 0.
- Boxes totales de todos los IDs: 10,117.

No se modifico ningun label. Los TXT temporales estan fuera de las carpetas funcionales y no se agregan al control de versiones.

RESULTADO_AUDITORIA: COMPLETA PARA LOS TXT DISPONIBLES

ESTADO_AIR_FILTER: APROBADA_CON_FOTOS_PROPIAS

RIESGOS: ID 14 solo aparece en 49 de 1,201 imagenes (4.08%); no demuestra diversidad suficiente para entrenar. El dataset contiene mayormente escenas de compartimento de motor, no necesariamente productos aislados de RepuestoPro. Air Filter Cover ID 9 es una clase distinta y no debe fusionarse.

RECOMENDACION: Mantener ID 14 como `air_filter`, agregar fotos propias de filtros reales de la tienda y evaluar visualmente una muestra antes de cualquier entrenamiento.
