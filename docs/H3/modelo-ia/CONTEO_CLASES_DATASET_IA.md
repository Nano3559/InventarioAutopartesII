# CONTEO DE CLASES DE DATASETS DE IA

Proyecto: RepuestoPro
Fecha: 2026-09-22
Alcance: inspeccion de manifiestos y metadata sin descargar imagenes.

## 1. Objetivo

Cerrar los conteos verificables de las ocho clases congeladas del MVP mediante listados oficiales de archivos, metadata, CSV/YAML disponibles y anotaciones pequenas cuando fueran accesibles. No se entreno, no se convirtieron anotaciones y no se modifico codigo productivo.

Clases congeladas: `brake_pad`, `brake_rotor`, `brake_caliper`, `alternator`, `oil_filter`, `air_filter`, `radiator`, `headlight`.

## 2. Archivos de metadata inspeccionados

Se inspeccionaron sin descargar imagenes:

- Metadata oficial Kaggle v3 de `gpiosenka/car-parts-40-classes`.
- Listado oficial paginado de archivos Kaggle del dataset principal: **16,560 archivos** listados; se contaron rutas JPG, CSV y archivos auxiliares por nombre.
- Metadata oficial Kaggle v2 de `khaledchawa/car-engine-bay-pictures`.
- Listado oficial paginado de archivos del dataset Air Filter: **2,402 archivos**: 1,201 JPG y 1,201 TXT.
- README/front matter y API publica de `DrBimmer/car-parts-and-damage-dataset`.
- Documentacion oficial y YAML publico de Ultralytics `carparts-seg`.

Los manifiestos JSON utilizados para el conteo se guardaron temporalmente fuera del repositorio, en `C:\Users\MSI\AppData\Local\Temp\opencode`. No se descargaron JPG, PNG, ZIP ni otros archivos de imagen.

## 3. Kaggle principal

Dataset: `gpiosenka/car-parts-40-classes`, version 3, licencia Apache 2.0.

El listado oficial contiene actualmente **9,239 JPG** en `car parts 50/train`, `car parts 50/valid` y `car parts 50/test`. El conteo se obtuvo de las rutas del manifiesto, no descargando imagenes.

La discrepancia 40/50 queda resuelta: el slug conserva `40-classes`, pero el contenido actual y sus rutas usan `car parts 50`; hay **50 clases reales**.

Clases completas obtenidas de las rutas del manifiesto:

```text
AIR COMPRESSOR, ALTERNATOR, BATTERY, BRAKE CALIPER, BRAKE PAD,
BRAKE ROTOR, CAMSHAFT, CARBERATOR, CLUTCH PLATE, COIL SPRING,
CRANKSHAFT, CYLINDER HEAD, DISTRIBUTOR, ENGINE BLOCK, ENGINE VALVE,
FUEL INJECTOR, FUSE BOX, GAS CAP, HEADLIGHTS, IDLER ARM,
IGNITION COIL, INSTRUMENT CLUSTER, LEAF SPRING, LOWER CONTROL ARM,
MUFFLER, OIL FILTER, OIL PAN, OIL PRESSURE SENSOR, OVERFLOW TANK,
OXYGEN SENSOR, PISTON, PRESSURE PLATE, RADIATOR, RADIATOR FAN,
RADIATOR HOSE, RADIO, RIM, SHIFT KNOB, SIDE MIRROR, SPARK PLUG,
SPOILER, STARTER, TAILLIGHTS, THERMOSTAT, TORQUE CONVERTER,
TRANSMISSION, VACUUM BRAKE BOOSTER, VALVE LIFTER, WATER PUMP,
WINDOW REGULATOR
```

El dataset es de clasificacion por carpetas. El manifiesto no aporta bounding boxes, poligonos ni labels YOLO.

### Conteo por split de clases MVP

| Clase original | Clase MVP | Train | Valid | Test | Total |
|---|---|---:|---:|---:|---:|
| BRAKE PAD | brake_pad | 188 | 5 | 5 | 198 |
| BRAKE ROTOR | brake_rotor | 176 | 5 | 5 | 186 |
| BRAKE CALIPER | brake_caliper | 174 | 5 | 5 | 184 |
| ALTERNATOR | alternator | 190 | 5 | 5 | 200 |
| OIL FILTER | oil_filter | 169 | 5 | 5 | 179 |
| AIR FILTER | air_filter | NO EXISTE EN RUTAS | NO EXISTE EN RUTAS | NO EXISTE EN RUTAS | 0 |
| RADIATOR | radiator | 169 | 5 | 5 | 179 |
| HEADLIGHTS | headlight | 159 | 5 | 5 | 169 |

Los counts de Kaggle son **VERIFICADOS** desde las rutas oficiales del listado de archivos. `AIR FILTER` no es una de las 50 carpetas actuales.

## 4. Car Engine Bay

Dataset: `khaledchawa/car-engine-bay-pictures`, version 2, MIT, 1,201 JPG y 1,201 TXT listados.

La metadata oficial declara labels YOLO y 26 IDs. El listado confirma correspondencia uno a uno entre los 1,201 nombres de imagen y los 1,201 nombres de label, pero el endpoint publico de descarga individual no entrego el contenido de los TXT sin autenticacion. Por ello no se contaron boxes leyendo anotaciones.

| ID original | Clase | Imagenes con clase | Bounding boxes | Estado |
|---:|---|---:|---:|---|
| 14 | Air Filter | NO VERIFICADO | NO VERIFICADO | Requiere contenido TXT |
| 9 | Air Filter Cover | NO VERIFICADO | NO VERIFICADO | Separar de ID 14 |
| 11 | Alternator | NO VERIFICADO | NO VERIFICADO | Requiere contenido TXT |
| 13 | Radiator | NO VERIFICADO | NO VERIFICADO | Requiere contenido TXT |
| 25 | Oil Filter | NO VERIFICADO | NO VERIFICADO | Requiere contenido TXT |

La lista oficial mantiene `Air Filter` ID 14 separado de `Air Filter Cover` ID 9. No se unifican. No se pudieron verificar labels vacios, IDs fuera de 0–25, cajas multiples, ni boxes por clase porque el contenido de los TXT no fue accesible.

La estructura y la cantidad de TXT son compatibles con YOLO, pero la auditoria de anotaciones queda incompleta. No se autoriza todavia el dataset final.

## 5. DrBimmer

Se inspecciono solamente `Car Parts`. La metadata oficial mantiene 998 imagenes, 21 categorias, licencia MIT y anotaciones poligonales compatibles con COCO/VIA/VGG.

| Clase | Imagenes | Instancias | Tipo anotacion |
|---|---:|---:|---|
| Headlight | NO VERIFICADO | NO VERIFICADO | Poligonos |

El README y la API publica no exponen un conteo por categoria ni un archivo pequeno de anotaciones descargable sin acceder a los datos del repositorio. `Car Damages` no fue inspeccionado ni utilizado. No se convierten poligonos a cajas.

## 6. Carparts-Seg

La fuente publica de Ultralytics declara 3,833 imagenes, 23 clases, splits train 3,156, val 401 y test 276, con segmentacion de instancia. El YAML publico confirma los IDs relevantes:

| ID | Clase original | Clase posterior posible | Conteo |
|---:|---|---|---:|
| 4 | back_left_light | Fuera del MVP actual | NO VERIFICADO |
| 5 | back_light | Fuera del MVP actual | NO VERIFICADO |
| 7 | back_right_light | Fuera del MVP actual | NO VERIFICADO |
| 12 | front_left_light | headlight, solo despues de decision | NO VERIFICADO |
| 13 | front_light | headlight, solo despues de decision | NO VERIFICADO |
| 15 | front_right_light | headlight, solo despues de decision | NO VERIFICADO |

El YAML no contiene conteos por clase. No se puede saber desde el manifiesto si una misma imagen tiene varias clases de luces. No se realiza ninguna unificacion en esta etapa.

## 7. Conteos por clase

| ID MVP | Clase | Fuente | Imagenes disponibles | Instancias | Tipo | Verificado |
|---:|---|---|---:|---:|---|---|
| 0 | brake_pad | Kaggle principal | 198 | NO APLICA | Clasificacion | SI |
| 1 | brake_rotor | Kaggle principal | 186 | NO APLICA | Clasificacion | SI |
| 2 | brake_caliper | Kaggle principal | 184 | NO APLICA | Clasificacion | SI |
| 3 | alternator | Kaggle principal | 200 | NO APLICA | Clasificacion | SI |
| 4 | oil_filter | Kaggle principal | 179 | NO APLICA | Clasificacion | SI |
| 5 | air_filter | Kaggle principal | 0 | 0 | Clasificacion | SI: ausencia en Kaggle |
| 5 | air_filter | Car Engine Bay | NO VERIFICADO | NO VERIFICADO | YOLO Detection | NO |
| 6 | radiator | Kaggle principal | 179 | NO APLICA | Clasificacion | SI |
| 6 | radiator | Car Engine Bay | NO VERIFICADO | NO VERIFICADO | YOLO Detection | NO |
| 7 | headlight | Kaggle principal | 169 | NO APLICA | Clasificacion | SI |
| 7 | headlight | DrBimmer | NO VERIFICADO | NO VERIFICADO | Poligonos | NO |
| 7 | headlight | Carparts-Seg | NO VERIFICADO | NO VERIFICADO | Segmentacion | NO |

No se suman fuentes entre si. Las imagenes pueden representar dominios, productos y duplicados diferentes.

## 8. Matriz de las 8 clases MVP

| ID | Clase | Fuente principal | Conteo verificable | Fuente de anotacion | Estado |
|---:|---|---|---:|---|---|
| 0 | brake_pad | Kaggle principal | 198 | Etiqueta de imagen | PARCIAL |
| 1 | brake_rotor | Kaggle principal | 186 | Etiqueta de imagen | PARCIAL |
| 2 | brake_caliper | Kaggle principal | 184 | Etiqueta de imagen | PARCIAL |
| 3 | alternator | Kaggle principal | 200 | Etiqueta de imagen | PARCIAL |
| 4 | oil_filter | Kaggle principal | 179 | Etiqueta de imagen | PARCIAL |
| 5 | air_filter | Ninguna aun | 0 en Kaggle | YOLO adicional sin conteo | REQUIERE_INSPECCION_DE_LABELS |
| 6 | radiator | Kaggle principal | 179 | Etiqueta de imagen | PARCIAL |
| 7 | headlight | Kaggle principal | 169 | Etiqueta de imagen | PARCIAL |

Los conteos de Kaggle son suficientes para una muestra posterior de clasificacion, pero no demuestran que las imagenes sean de productos aislados del catalogo RepuestoPro.

## 9. Control de calidad

| Control | Resultado |
|---|---|
| Duplicados por nombre en Kaggle | No observados en las rutas; hash de imagen NO VERIFICADO |
| Duplicados por nombre en Air Filter | No observados entre los nombres listados; hash NO VERIFICADO |
| Labels vacios Air Filter | NO VERIFICADO: no se obtuvo contenido TXT |
| IDs fuera de rango Air Filter | NO VERIFICADO: no se obtuvo contenido TXT |
| Imagen sin label Air Filter | No observado en manifiesto: 1,201 JPG y 1,201 TXT con basename correspondiente |
| Label sin imagen Air Filter | No observado por basename en manifiesto |
| Train/valid/test Kaggle | Consistente en rutas; cada clase tiene valid/test de 5 |
| Nombres duplicados entre splits Kaggle | NO VERIFICADO por hash; las rutas son distintas |
| Multi-clase DrBimmer | NO VERIFICADO sin anotaciones procesables |
| Multi-clase Carparts-Seg | NO VERIFICADO desde YAML |
| Calidad visual, recortes y producto real | REQUIERE_INSPECCION_VISUAL |

## 10. Decisión de descarga

| Dataset | Decision | Motivo |
|---|---|---|
| Kaggle principal | APROBADO_PARA_MUESTRA | Licencia, 50 clases y conteos de 7 clases MVP verificados; es clasificacion y no boxes |
| Car Engine Bay | PENDIENTE | Faltan conteos y validacion del contenido de labels ID 14 |
| DrBimmer Car Parts | PENDIENTE | Falta conteo Headlight y acceso controlado a anotaciones |
| Carparts-Seg | APROBADO_PARA_MUESTRA | Licencia, YAML, splits y formato verificados; headlight requiere mapeo posterior |

Estas decisiones no descargan ni autorizan automaticamente imagenes. `APROBADO_PARA_MUESTRA` significa que puede planificarse una muestra pequena en una etapa posterior.

## 11. Datos todavia no verificables

- Boxes y cantidad de instancias de `air_filter` ID 14.
- Separacion real entre Air Filter y Air Filter Cover en los TXT.
- Conteos de `alternator`, `radiator` y `oil_filter` en Car Engine Bay.
- Conteo de imagenes e instancias Headlight en DrBimmer.
- Conteos por clase de luces en Carparts-Seg.
- Hashes, duplicados de contenido y calidad visual.
- Si las imagenes representan repuestos aislados o piezas montadas.

## 12. Conclusion

La inspeccion de manifiestos cerro los conteos de Kaggle para siete clases MVP: `brake_pad` 198, `brake_rotor` 186, `brake_caliper` 184, `alternator` 200, `oil_filter` 179, `radiator` 179 y `headlight` 169. `air_filter` no existe en Kaggle y requiere el dataset YOLO adicional, cuyo contenido de labels no pudo ser obtenido sin descargar archivos de imagen.

Kaggle queda aprobado solo para muestra de clasificacion. Carparts-Seg queda aprobado solo para muestra secundaria. Air Filter y DrBimmer permanecen pendientes. No se sumaron fuentes distintas ni se modificaron las ocho clases.

## 13. Proximo paso

Obtener, mediante acceso oficial controlado, solamente los archivos TXT de anotaciones de Car Engine Bay y los JSON/VGG de Car Parts de DrBimmer para cerrar `air_filter` y `headlight`, sin descargar imagenes.

Control de alcance: no se descargaron imagenes ni ZIPs con imagenes, no se creo dataset final, no se crearon carpetas train/val/test, no se creo dataset.yaml, no se instalaron herramientas, no se convirtieron anotaciones, no se modifico codigo productivo y no se hicieron commits, pushes ni PR.
