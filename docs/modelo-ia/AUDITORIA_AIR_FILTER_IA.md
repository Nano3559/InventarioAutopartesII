# AUDITORIA ESPECIFICA DE AIR FILTER

Proyecto: RepuestoPro
Fecha: 2026-09-22
Clase objetivo congelada: `air_filter`.

## 1. Objetivo

Inspeccionar exclusivamente las anotaciones del dataset `khaledchawa/car-engine-bay-pictures` para separar `Air Filter` ID 14 de `Air Filter Cover` ID 9 y determinar si la fuente es utilizable para la clase `air_filter` de RepuestoPro.

## 2. Fuente

Fuente oficial: Kaggle, `khaledchawa/car-engine-bay-pictures`.

- Version: 2.
- Licencia: MIT.
- Imagenes declaradas: 1,201.
- Labels declarados: 1,201 archivos TXT.
- Formato declarado: YOLO.
- Clases: 26 IDs.
- `Air Filter`: ID 14.
- `Air Filter Cover`: ID 9.

No se fusionan ID 14 e ID 9. La clase RepuestoPro `air_filter` utiliza exclusivamente ID 14.

## 3. Metodo de acceso

Se utilizo Kaggle CLI autenticado mediante la variable de entorno `KAGGLE_API_TOKEN`. Primero se obtuvo el listado oficial completo y se identificaron los 1,201 archivos bajo `labels/labels/*.txt`. Luego se descargaron individualmente solo esos TXT a una carpeta temporal fuera del repositorio, evitando JPG y ZIP.

Los 1,201 TXT se descargaron correctamente y fueron analizados localmente. No se descargo ninguna imagen.

**ACCESO_LABELS: OK**

## 4. Conteo Air Filter

| Medida | Resultado |
|---|---:|
| ID analizado | 14 |
| Archivos TXT con ID 14 | 49 |
| Imagenes asociadas | 49 |
| Bounding boxes ID 14 | 49 |
| Minimo de boxes por imagen | 1 |
| Maximo de boxes por imagen | 1 |
| Promedio de boxes por imagen | 1.00 |

No se inventan conteos a partir del total de 1,201 imagenes: el total del dataset no equivale al numero de imagenes que contienen Air Filter.

## 5. Comparacion Air Filter Cover

| Medida | ID 9: Air Filter Cover |
|---|---:|
| Imagenes con ID 9 | 666 |
| Bounding boxes ID 9 | 740 |
| Imagenes con ID 9 e ID 14 simultaneamente | 0 |
| Fusion con `air_filter` | NO |

La separacion semantica y numerica fue comprobada directamente en los TXT autenticados. No existe coexistencia de ID 9 e ID 14 en una misma imagen.

## 6. Clases secundarias

Los siguientes conteos fueron obtenidos leyendo los TXT autenticados y son informativos; no modifican las ocho clases MVP:

| ID | Clase | Imagenes | Bounding boxes |
|---:|---|---:|---:|
| 11 | Alternator | 233 | 240 |
| 13 | Radiator | 664 | 672 |
| 25 | Oil Filter | 6 | 6 |

No se modifican las ocho clases MVP.

## 7. Control de labels

| Control | Resultado |
|---|---|
| TXT vacios | 0 |
| Lineas invalidas | 0 |
| IDs fuera de 0–25 | 0 |
| Coordenadas YOLO fuera de rango | 0 detectadas |
| TXT sin JPG correspondiente | No observado por basename en el manifiesto |
| JPG sin TXT correspondiente | No observado por basename en el manifiesto |
| Total de boxes | 10,117 |
| Distribucion general de IDs | IDs 0–25; sin IDs fuera de rango |

La correspondencia de nombres del manifiesto fue completa: 1,201 JPG y 1,201 TXT. Todas las 10,117 lineas YOLO validas tuvieron cinco campos, IDs enteros 0–25 y coordenadas normalizadas dentro de rango.

## 8. Decision

**DECISION AIR_FILTER: APROBADA_CON_FOTOS_PROPIAS**. ID 14 tiene 49 imagenes positivas y 49 boxes, formato YOLO, licencia MIT y no se mezcla con ID 9. La cobertura es baja frente a 1,201 imagenes totales y requiere fotos propias; este resultado no implica suficiencia para entrenamiento.

No se aprueba la descarga del dataset completo. Tampoco se autoriza asumir que las 1,201 imagenes contienen Air Filter.

## 9. Conclusion

La auditoria autenticada confirma 49 imagenes y 49 boxes de Air Filter, frente a 666 imagenes y 740 boxes de Air Filter Cover. No hay imagenes que contengan simultaneamente ID 9 e ID 14. Los labels no presentan errores de integridad en los controles ejecutados.

No se descargaron imagenes, no se descargaron ZIPs, no se modificaron anotaciones, no se instalo software y no se modifico codigo productivo.

## 10. Proximo paso

Conservar las anotaciones temporales fuera del repositorio y diseñar la captura de fotos propias para ampliar `air_filter` sin fusionarlo con `Air Filter Cover`.

## Verificacion autenticada de anotaciones YOLO

Fecha de verificacion: 2026-09-22.

Dataset: `khaledchawa/car-engine-bay-pictures`, version 2, licencia MIT.

Metodo: Kaggle CLI autenticado con `KAGGLE_API_TOKEN`; listado completo de archivos; descarga individual de `labels/labels/*.txt` solamente; analisis de cada linea YOLO en una carpeta temporal fuera del repositorio. Se procesaron 1,201 TXT de 1,201 JPG manifestados.

Controles: 0 labels vacios, 0 lineas invalidas, 0 IDs fuera de 0–25, 0 coordenadas fuera de rango, 1,201 basenames TXT/JPG correspondientes y 10,117 boxes totales.

| ID | Clase | Imagenes positivas | Boxes | Min | Max | Promedio | Porcentaje |
|---:|---|---:|---:|---:|---:|---:|---:|
| 14 | Air Filter | 49 | 49 | 1 | 1 | 1.00 | 4.08% |
| 9 | Air Filter Cover | 666 | 740 | 1 | 4 | 1.11 | 55.45% |
| 11 | Alternator | 233 | 240 | 1 | 2 | 1.03 | 19.40% |
| 13 | Radiator | 664 | 672 | 1 | 2 | 1.01 | 55.29% |
| 25 | Oil Filter | 6 | 6 | 1 | 1 | 1.00 | 0.50% |

Las clases 9 y 14 permanecen separadas. Ningun TXT contiene simultaneamente ambas clases.
