# VERIFICACION DE METADATA DE DATASETS DE IA

Proyecto: RepuestoPro
Fecha: 2026-09-22
Alcance: consulta de metadata y documentacion publica sin descargar imagenes, sin convertir anotaciones y sin entrenar.

## 1. Objetivo

Cerrar, hasta donde permiten las fuentes oficiales, los datos pendientes de la auditoria anterior para las ocho clases congeladas del MVP 1. La consulta uso endpoints publicos de metadata de Kaggle, la tarjeta/API publica de Hugging Face y documentacion oficial de Ultralytics. No se descargaron archivos de imagen.

## 2. Estado de las 8 clases

| ID | Clase | Presencia en catalogo | Estado de metadata |
|---:|---|---|---|
| 0 | brake_pad | Verificada en `seed-data.ts` | Cobertura nominal Kaggle; conteo por clase NO VERIFICADO |
| 1 | brake_rotor | Verificada en `seed-data.ts` | Cobertura nominal Kaggle; conteo por clase NO VERIFICADO |
| 2 | brake_caliper | Verificada en `seed-data.ts` | Cobertura nominal Kaggle; conteo por clase NO VERIFICADO |
| 3 | alternator | Verificada en `seed-data.ts` | Cobertura nominal Kaggle; conteo por clase NO VERIFICADO |
| 4 | oil_filter | Verificada en `seed-data.ts` | Cobertura nominal Kaggle; conteo por clase NO VERIFICADO |
| 5 | air_filter | Verificada en `seed-data.ts` | Cubierta por dataset adicional YOLO; conteo de boxes NO VERIFICADO |
| 6 | radiator | Verificada en `seed-data.ts` | Cobertura nominal Kaggle y adicional YOLO; conteo por clase NO VERIFICADO |
| 7 | headlight | Verificada en `seed-data.ts` | Cubierta por DrBimmer y Carparts-Seg; conteo por clase NO VERIFICADO |

La presencia de un nombre de clase no demuestra por si sola calidad, balance, licencia ni utilidad para el catalogo local.

## 3. Verificacion Kaggle principal

Dataset: `gpiosenka/car-parts-40-classes`.

| Campo | Resultado oficial |
|---|---|
| Nombre actual | `50 Types of Car Parts -Image Classification` |
| Slug | `gpiosenka/car-parts-40-classes` |
| Autor/owner | Gerry; owner ref `gpiosenka` |
| Licencia | Apache 2.0 |
| Version actual | 3 |
| Fecha ultima actualizacion | 2024-02-24T20:55:47.063Z |
| Tamano | 334,048,335 bytes |
| Total de imagenes | NO VERIFICADO en metadata oficial consultada |
| Clases reales actuales | 50, segun descripcion oficial y rutas `car parts 50/` |
| Formato de imagen | JPG, 224 x 224 x 3 |
| Tipo | Image classification / multiclass classification |
| Anotacion | Etiqueta por carpeta/clase; no boxes confirmadas |
| Bounding boxes | NO VERIFICADO como existentes; la descripcion solo declara clasificacion |
| Poligonos | NO VERIFICADO |
| Splits | `train`, `test`, `valid` en la descripcion oficial |
| Imagenes validacion | 5 por clase, segun descripcion oficial |
| Imagenes test | 5 por clase, segun descripcion oficial |
| Imagenes train | No balanceado; minimo publicado 110 y maximo 200 para clases concretas, conteo por clase MVP NO VERIFICADO |

### Resolucion 40 vs 50

El slug historico conserva `40-classes`, pero la version oficial actual es la **version 3**, tiene titulo y subtitulo de 50 clases, descripcion de 50 clases y rutas de archivos bajo `car parts 50/`. La conclusion verificable es que el dataset actual contiene 50 clases; `40-classes` es un slug historico que no refleja el contenido actual.

### Lista completa de clases

La metadata oficial consultada confirma el total 50, pero no expone en el endpoint de vista una lista completa de nombres ni un manifiesto de conteos. El endpoint de listado muestra archivos y el CSV `car parts.csv`, pero no se descargaron esos archivos. Por regla de evidencia, la lista completa y los conteos por clase quedan **NO VERIFICADOS** en este documento.

### Clases MVP en Kaggle

La metadata/listado publico permite confirmar rutas nominales para `ALTERNATOR`, `BRAKE CALIPER`, `BRAKE PAD` y, por la descripcion/listado de clases publicado, `BRAKE ROTOR`, `HEADLIGHTS`, `OIL FILTER` y `RADIATOR`. `AIR FILTER` no aparece confirmado en la metadata oficial revisada.

No se declara cantidad exacta por clase para ninguna de las siete clases porque el endpoint no entrego el manifiesto completo sin descargar archivos. La unica cantidad oficial por split que se puede afirmar es 5 en `valid` y 5 en `test` por clase.

## 4. Verificacion Air Filter

Dataset: `khaledchawa/car-engine-bay-pictures`.

| Campo | Resultado oficial |
|---|---|
| Nombre actual | `Car Engine Bay Images with YOLO Annotations` |
| Slug | `khaledchawa/car-engine-bay-pictures` |
| Autor | Khaled Chawa |
| Licencia | MIT |
| Version actual | 2 |
| Fecha ultima actualizacion | 2024-10-15T03:18:28.667Z |
| Tamano | 524,504,032 bytes |
| Total de imagenes | 1,201 |
| Carpetas declaradas | `images` y `labels` |
| Formato labels | YOLO |
| Bounding boxes | SI, segun la descripcion oficial del dataset |
| Splits train/val/test | NO VERIFICADO en metadata oficial |
| Lista de clases | 26 IDs, publicada completa abajo |
| Cantidad de boxes Air Filter | NO VERIFICADO |
| Cantidad de imagenes con Air Filter | NO VERIFICADO |

Clases e IDs oficiales:

```text
0 Inverter Coolant Reservoir
1 Battery
2 Radiator Cap
3 Windshield Wiper Fluid
4 Fuse Box
5 Power Steering Reservoir
6 Brake Fluid
7 Engine Oil Fill Cap
8 Engine Oil Dip Stick
9 Air Filter Cover
10 ABS Unit
11 Alternator
12 Engine Coolant Reservoir
13 Radiator
14 Air Filter
15 Engine Cover
16 Cold Air Intake
17 Clutch Fluid Reservoir
18 Transmission Oil Dip Stick
19 Intercooler Coolant Reservoir
20 Oil Filter Housinig
21 ATF Oil Reservoir
22 Cabin Air Filter Housng
23 Secondary Coolant Reservoir
24 Electric Motor
25 Oil Filter
```

`Air Filter` es el ID 14 y representa el filtro segun el nombre original. `Air Filter Cover` es el ID 9 y representa la tapa/carcasa. No se deben unificar. La clase RepuestoPro `air_filter` puede usar solamente instancias ID 14; las instancias ID 9 deben quedar fuera o etiquetarse aparte durante una futura auditoria.

El dataset es tecnicamente compatible con YOLO por la estructura y labels anunciadas, pero todavia no esta listo para descarga: faltan conteos por clase, verificacion de los archivos de labels y confirmacion de splits.

## 5. Verificacion DrBimmer

Dataset: `DrBimmer/car-parts-and-damage-dataset`, solamente `Car Parts`.

| Campo | Resultado oficial |
|---|---|
| Car Parts disponible | SI en la tarjeta/API publica; existe carpeta `Car parts dataset` |
| Licencia | MIT en front matter oficial de README y metadata de Hugging Face |
| Total dataset | 1,812 imagenes |
| Car Parts | 998 imagenes |
| Car Damages | 814 imagenes; excluido |
| Anotaciones | Poligonos de segmentacion |
| Formato | Compatible con COCO JSON o VIA/VGG, segun README |
| Headlight por imagen | NO VERIFICADO |
| Instancias Headlight | NO VERIFICADO |
| Archivo de conteo por clase | NO VERIFICADO sin procesar/descargar anotaciones |

La API publica muestra archivos y metadata del repositorio, pero no publica un resumen por clase para `Headlight`. No se puede convertir el numero total de Car Parts en un conteo de Headlight.

## 6. Verificacion Carparts-Seg

Fuente: documentacion oficial de Ultralytics, que atribuye el dataset original a `car-seg` de Gianmarco Russo en Roboflow Universe.

| Campo | Resultado oficial |
|---|---|
| Fuente original | Roboflow Universe, proyecto `car-seg` de Gianmarco Russo |
| Documentacion | https://docs.ultralytics.com/datasets/segment/carparts-seg/ |
| Imagenes | 3,833 |
| Clases | 23: 22 clases nombradas y `object` |
| Splits | train 3,156; val 401; test 276 |
| Formato | Instance segmentation con mascaras; YAML Ultralytics |
| Licencia | CC BY 4.0 en la pagina/documentacion de Ultralytics |
| Luces | `back_left_light`, `back_light`, `back_right_light`, `front_left_light`, `front_light`, `front_right_light` |
| Headlight exacto | No existe como etiqueta unica; debe mapearse desde luces delanteras |
| Cantidad por clase de luces | NO VERIFICADO |
| Restricciones | Requiere atribucion CC BY 4.0; revisar tambien condiciones de la fuente original |

Carparts-Seg no es una fuente directa de `headlight` con una sola clase. Es una fuente secundaria para posibles partes de vehiculo y requiere una decision de mapeo antes de usarla.

## 7. Conteos por clase

| Dataset | Clase | Imagenes verificadas | Anotaciones/instancias verificadas |
|---|---|---:|---:|
| Kaggle principal | brake_pad | NO VERIFICADO | Etiqueta de imagen; box NO VERIFICADO |
| Kaggle principal | brake_rotor | NO VERIFICADO | Etiqueta de imagen; box NO VERIFICADO |
| Kaggle principal | brake_caliper | NO VERIFICADO | Etiqueta de imagen; box NO VERIFICADO |
| Kaggle principal | alternator | NO VERIFICADO | Etiqueta de imagen; box NO VERIFICADO |
| Kaggle principal | oil_filter | NO VERIFICADO | Etiqueta de imagen; box NO VERIFICADO |
| Kaggle principal | radiator | NO VERIFICADO | Etiqueta de imagen; box NO VERIFICADO |
| Kaggle principal | headlight | NO VERIFICADO | Etiqueta de imagen; box NO VERIFICADO |
| Air Filter dataset | air_filter ID 14 | NO VERIFICADO | Boxes YOLO por clase: NO VERIFICADO |
| Air Filter dataset | air_filter cover ID 9 | NO VERIFICADO | Boxes YOLO por clase: NO VERIFICADO |
| DrBimmer | headlight | NO VERIFICADO | Poligonos por clase: NO VERIFICADO |
| Carparts-Seg | luces delanteras | NO VERIFICADO | Mascaras por clase: NO VERIFICADO |

El unico conteo verificable de imagenes de clases no es suficiente para esta tabla: Kaggle declara 5 imagenes de `valid` y 5 de `test` por cada una de sus 50 clases, pero no entrega el conteo train por clase en la metadata consultada. No se infiere un total por clase.

## 8. Licencias verificadas

| Dataset | Licencia | Entrenamiento academico | Modificacion | Redistribucion | Atribucion | Estado |
|---|---|---|---|---|---|---|
| Kaggle principal | Apache 2.0 | Permitido bajo la licencia | Permitida | Permitida bajo condiciones de Apache 2.0 | Aviso y texto de licencia | VERIFICADA |
| Air Filter dataset | MIT | Permitido bajo la licencia | Permitida | Permitida con aviso/licencia | Incluir aviso MIT | VERIFICADA |
| DrBimmer Car Parts | MIT | Permitido bajo la licencia | Permitida | Permitida con aviso/licencia | Incluir aviso MIT | VERIFICADA |
| Carparts-Seg | CC BY 4.0 | Permitido con atribucion | Permitida | Permitida con atribucion | Obligatoria | VERIFICADA |

La licencia Apache 2.0 fue devuelta por la metadata oficial de Kaggle para la version 3. MIT fue devuelta por la metadata oficial de Kaggle para version 2 del dataset Air Filter y por el front matter oficial de DrBimmer. CC BY 4.0 aparece en la documentacion oficial de Ultralytics. Aun deben conservarse los textos de licencia y atribucion junto con cualquier copia futura.

## 9. Tabla de disponibilidad final

| ID | Clase | Dataset | Imagenes verificadas | Anotaciones verificadas | Licencia | ¿Utilizable? |
|---:|---|---|---:|---|---|---|
| 0 | brake_pad | Kaggle principal | NO VERIFICADO | Etiqueta de clasificacion; boxes NO VERIFICADO | Apache 2.0 | SI_CON_CONDICIONES |
| 1 | brake_rotor | Kaggle principal | NO VERIFICADO | Etiqueta de clasificacion; boxes NO VERIFICADO | Apache 2.0 | SI_CON_CONDICIONES |
| 2 | brake_caliper | Kaggle principal | NO VERIFICADO | Etiqueta de clasificacion; boxes NO VERIFICADO | Apache 2.0 | SI_CON_CONDICIONES |
| 3 | alternator | Kaggle principal | NO VERIFICADO | Etiqueta de clasificacion; boxes NO VERIFICADO | Apache 2.0 | SI_CON_CONDICIONES |
| 4 | oil_filter | Kaggle principal | NO VERIFICADO | Etiqueta de clasificacion; boxes NO VERIFICADO | Apache 2.0 | SI_CON_CONDICIONES |
| 5 | air_filter | Air Filter dataset | 1,201 total, clase NO VERIFICADA | YOLO declarado; ID 14, conteo NO VERIFICADO | MIT | SI_CON_CONDICIONES |
| 6 | radiator | Kaggle principal / Air Filter dataset | NO VERIFICADO por clase | Clasificacion Kaggle; YOLO adicional declarado | Apache 2.0 / MIT | SI_CON_CONDICIONES |
| 7 | headlight | DrBimmer / Carparts-Seg / Kaggle | 998 Car Parts totales; clase NO VERIFICADA | Poligonos/masks; Kaggle etiqueta de imagen | MIT / CC BY 4.0 / Apache 2.0 | SI_CON_CONDICIONES |

`SI_CON_CONDICIONES` significa que la licencia es conocida, pero falta inspeccionar conteos, calidad, duplicados y archivos antes de autorizar una descarga para el proyecto.

## 10. Decision por dataset

| Dataset | Decision | Motivo |
|---|---|---|
| Kaggle principal | APROBADO_CON_CONDICIONES | Apache 2.0 y version 3 verificadas; faltan conteos por clase y manifiesto completo antes de descargar |
| Air Filter dataset | APROBADO_CON_CONDICIONES | MIT, 1,201 imagenes y YOLO verificables; falta comprobar boxes, splits y separacion Air Filter/Air Filter Cover |
| DrBimmer Car Parts | APROBADO_CON_CONDICIONES | MIT, 998 imagenes y poligonos verificables; conteo Headlight y disponibilidad real de archivos pendientes |
| Carparts-Seg | APROBADO_CON_CONDICIONES | CC BY 4.0, estructura y splits verificables; no tiene una clase unica `headlight` y falta validar la atribucion original |

Estas decisiones no autorizan la descarga inmediata. Son decisiones de elegibilidad condicionada para una posterior inspeccion controlada.

## 11. Riesgos pendientes

- Kaggle usa un slug historico de 40 clases pero el contenido actual es version 3 con 50 clases.
- Kaggle no expone en la metadata consultada los conteos train por clase ni el total de imagenes.
- No se puede afirmar que las cajas esten ausentes en Kaggle solo por no aparecer en la descripcion; se marca NO VERIFICADO.
- En Air Filter dataset no estan publicados los conteos de boxes por clase ni splits.
- Air Filter y Air Filter Cover tienen IDs distintos y no deben fusionarse.
- DrBimmer no publica conteo de instancias Headlight en el README.
- Carparts-Seg representa luces delanteras con varias clases, no con `headlight` unica.
- El conteo de imagenes no equivale a diversidad de productos RepuestoPro.
- Aun se necesitan fotos propias de las ocho clases para adaptar el dominio.

## 12. Conclusion

La metadata oficial cierra varios datos que antes estaban pendientes: Kaggle version 3 tiene 50 clases, Apache 2.0, 334,048,335 bytes y clasificacion; el dataset de motor tiene 1,201 imagenes, 26 IDs YOLO, MIT y distingue `Air Filter` ID 14 de `Air Filter Cover` ID 9; DrBimmer tiene 998 imagenes de Car Parts, MIT y poligonos; Carparts-Seg tiene 3,833 imagenes, 23 clases, mascaras, splits publicados y CC BY 4.0.

Todavia no hay cantidades por clase verificadas para las ocho clases y ninguna fuente queda aprobada sin condiciones. No se modifica el MVP.

## 13. Proximo paso

Solicitar una inspeccion controlada de metadata/manifiestos y licencias, sin descargar imagenes, para obtener los conteos por clase faltantes y confirmar los archivos de anotacion antes de autorizar cualquier descarga.

Control de alcance: no se descargaron imagenes, no se crearon carpetas dataset/train/val/test, no se instalaron YOLO/Ultralytics/OpenCV/PyTorch, no se convirtieron anotaciones, no se entreno ningun modelo y no se modificaron backend, frontend, mobile, Prisma, productos, categorias ni clases MVP.
