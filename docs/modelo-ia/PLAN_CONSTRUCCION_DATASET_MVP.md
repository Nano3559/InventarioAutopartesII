# PLAN DE CONSTRUCCION DEL DATASET MVP

Proyecto: RepuestoPro  
Estado: preparacion previa, sin descarga de imagenes y sin entrenamiento  
Fecha: 2026-09-22

## Clases congeladas

Estas clases no se modifican durante la construccion del MVP:

| ID final | Clase |
|---:|---|
| 0 | brake_pad |
| 1 | brake_rotor |
| 2 | brake_caliper |
| 3 | alternator |
| 4 | oil_filter |
| 5 | air_filter |
| 6 | radiator |
| 7 | headlight |

## Fuentes auditadas

- Kaggle `gpiosenka/car-parts-40-classes`: clasificacion, 50 clases actuales, Apache 2.0; aporta conteos de `brake_pad`, `brake_rotor`, `brake_caliper`, `alternator`, `oil_filter`, `radiator` y `headlight`.
- Kaggle `khaledchawa/car-engine-bay-pictures`: YOLO, MIT; ID 14 `Air Filter` aporta 49 imagenes positivas y 49 boxes; ID 9 `Air Filter Cover` permanece separado.
- Hugging Face `DrBimmer/car-parts-and-damage-dataset`: poligonos de `Car Parts`, MIT; cobertura de `headlight` pendiente de conteo específico.
- Ultralytics `Carparts-Seg`: segmentacion, CC BY 4.0; luces delanteras con clases separadas, pendiente de mapeo posterior.

Los conteos y limitaciones están documentados en `docs/modelo-ia/CONTEO_LABELS_CAR_ENGINE_BAY.md` y en las auditorias previas. No se descargan imagenes en esta etapa.

## Estrategia de construccion

1. Mantener la taxonomia final de ocho clases sin agregar ni eliminar clases.
2. Descargar posteriormente solo una muestra controlada de fuentes aprobadas, conservando licencia, URL, version y procedencia.
3. Incorporar fotografias propias de piezas reales de RepuestoPro, especialmente `air_filter`, que tiene baja cobertura publica.
4. Revisar visualmente duplicados, piezas montadas, empaques, fondos, calidad y confusiones entre clases.
5. Separar por producto o pieza fisica antes de dividir los splits, evitando que fotos casi identicas aparezcan en train y validation.
6. Mantener por separado las fuentes de clasificacion, deteccion y segmentacion hasta definir las transformaciones y anotaciones permitidas.

## Remapeo de IDs

Los datasets usan IDs y nombres propios. Antes de combinar datos se debe crear un mapa explicito hacia los IDs 0–7 del MVP:

| ID final | Clase final | Ejemplos de origen |
|---:|---|---|
| 0 | brake_pad | `BRAKE PAD` |
| 1 | brake_rotor | `BRAKE ROTOR` |
| 2 | brake_caliper | `BRAKE CALIPER` |
| 3 | alternator | `ALTERNATOR`, ID 11 del dataset de motor |
| 4 | oil_filter | `OIL FILTER`, ID 25 del dataset de motor |
| 5 | air_filter | ID 14 `Air Filter` exclusivamente |
| 6 | radiator | `RADIATOR`, ID 13 del dataset de motor |
| 7 | headlight | `HEADLIGHTS`, `Headlight` o luces delanteras aprobadas |

`Air Filter Cover` ID 9 nunca se remapea a `air_filter` ID 5. Las clases sin correspondencia exacta se descartan o se conservan fuera del MVP, pero no se fuerzan a una clase existente.

## Separacion train/val/test

La division propuesta es 70/15/15 como punto de partida, ajustable cuando se conozcan los conteos finales. La unidad de separacion debe ser la pieza o producto, no solamente el archivo: imagenes de una misma pieza, caja o sesion deben permanecer en un solo split.

Reglas:

- validation y test deben contener ejemplos de todas las clases que se intenten entrenar;
- no duplicar imagenes entre splits;
- conservar un test propio de fotografias reales de tienda/taller;
- registrar el origen y el split de cada muestra;
- no mezclar automaticamente clasificacion con bounding boxes.

## Controles de integridad

Antes de construir el dataset final se verificara:

- extensiones y archivos legibles;
- labels YOLO con cinco campos numericos;
- IDs dentro de 0–7 despues del remapeo;
- coordenadas normalizadas entre 0 y 1;
- imagen y label con basename correspondiente;
- ausencia de labels vacios no justificados;
- duplicados por nombre, hash y contenido visual;
- balance por clase y por fuente;
- ausencia de fuga entre train, validation y test;
- licencia y atribucion asociadas a cada fuente;
- no fusionar `air_filter` con `air_filter_cover`.

## Clases con menor cobertura

`air_filter` es la clase mas debil: el dataset de motor contiene 49 imagenes positivas y 49 boxes de ID 14 entre 1,201 labels. `oil_filter` tiene solo 6 imagenes y 6 boxes en esa fuente. La cobertura nominal de Kaggle para otras clases no reemplaza la necesidad de fotos propias ni confirma diversidad del dominio.

Se deben priorizar fotos propias de filtros de aire, filtros de aceite, pastillas, discos, calipers, alternadores, radiadores y faros, con varias marcas, angulos, fondos, iluminaciones y estados de uso.

## Politica de Git y almacenamiento

Los datasets, imagenes, labels descargados, ejecuciones, pesos y modelos no se almacenan en Git. Las carpetas protegidas son:

- `ia-service/datasets/`
- `ia-service/runs/`
- `ia-service/weights/`

Tambien se ignoran imagenes de entrenamiento dentro de `ia-service`, pesos `*.pt`, modelos `*.onnx`, labels descargados, credenciales `kaggle.json`, tokens `access_token`, entornos virtuales y caches Python. El archivo `data.yaml` no se ignora, pero todavía no se crea.

## Estructura preparada

```text
ia-service/
  app/
  scripts/
  configs/
  datasets/   # protegido por .gitignore
  runs/       # protegido por .gitignore
  weights/    # protegido por .gitignore
```

Las carpetas de codigo, scripts y configuracion no se ignoran. En esta etapa solo contienen marcadores `.gitkeep`; no hay servicio ni entrenamiento.

## Estado de alcance

No se descargaron imagenes, no se entreno ningun modelo, no se instalo YOLO/PyTorch/OpenCV, no se modifico backend/frontend/mobile/Prisma y no se incluyeron tokens ni credenciales. Erika debe revisar este plan antes de autorizar la descarga de una muestra.

## Resultado de la construccion base

Fecha de descarga controlada: 2026-09-22.

Se construyo una copia RAW local, ignorada por Git, con 1,344 imagenes:

| Clase | Kaggle car-parts | Car Engine Bay | Total |
|---|---:|---:|---:|
| brake_pad | 198 | 0 | 198 |
| brake_rotor | 186 | 0 | 186 |
| brake_caliper | 184 | 0 | 184 |
| alternator | 200 | 0 | 200 |
| oil_filter | 179 | 0 | 179 |
| air_filter | 0 | 49 | 49 |
| radiator | 179 | 0 | 179 |
| headlight | 169 | 0 | 169 |
| **Total** | **1,295** | **49** | **1,344** |

Ubicacion RAW: `ia-service/datasets/raw/`.

Manifiesto: `ia-service/datasets/dataset_manifest.csv`, con 1,344 filas y IDs finales 0–7. Los originales de Kaggle permanecen separados por `train`, `valid` y `test`; las 49 imagenes de Air Filter tienen split `unspecified` porque la fuente complementaria fue auditada como deteccion YOLO, no como split de clasificacion.

Tipo de datos:

- Kaggle principal: clasificacion por carpeta; no aporta bounding boxes. Estas imagenes no deben usarse directamente como deteccion YOLO.
- Car Engine Bay: imagenes con labels YOLO de ID 14; las 49 imagenes seleccionadas corresponden a `air_filter` y sus labels originales se conservaron temporalmente fuera de Git.

Controles realizados: 1,344 filas con archivo local, 0 faltantes, 0 archivos ilegibles por validacion basica JPEG, 0 grupos de duplicados exactos por SHA-256. Los conteos coinciden con la auditoria previa: Kaggle 198/186/184/200/179/179/169 y Air Filter 49.

La descarga no autoriza entrenamiento. Antes de entrenar se requiere revisar visualmente una muestra, definir como se anotaran las clases de clasificacion para detection y ampliar especialmente `air_filter` con fotografias propias.

## Preparacion de revision visual

Se seleccionaron **80 imagenes reproduciblemente**, usando orden lexicografico de `original_path`:

| Clase | Cantidad | Seleccion |
|---|---:|---|
| brake_pad | 10 | 4 train, 3 valid, 3 test |
| brake_rotor | 10 | 4 train, 3 valid, 3 test |
| brake_caliper | 10 | 4 train, 3 valid, 3 test |
| alternator | 10 | 4 train, 3 valid, 3 test |
| oil_filter | 10 | 4 train, 3 valid, 3 test |
| air_filter | 10 | split unspecified; fuente YOLO complementaria |
| radiator | 10 | 4 train, 3 valid, 3 test |
| headlight | 10 | 4 train, 3 valid, 3 test |

Distribucion total: 28 train, 21 valid, 21 test y 10 unspecified. Las copias estan en `ia-service/datasets/review/images/` y la seleccion se registra en `ia-service/datasets/review/review_manifest.csv`. Las 10 muestras de `air_filter` conservan una copia de su label original en `ia-service/datasets/review/labels/air_filter/`; los labels siguen usando ID 14 y no se remapean.

La correspondencia RAW de Air Filter fue verificada: 49 imagenes, 49 labels, 0 faltantes y 49 boxes ID 14. No se modificaron las imagenes RAW ni los labels originales.

## Herramienta y estrategia de anotacion

Se recomienda **CVAT local/self-hosted** por su soporte de anotacion de bounding boxes y exportacion YOLO. No se instala en esta etapa y no se suben imagenes a servicios externos.

Flujo propuesto:

1. Importar solo una copia de trabajo, nunca `ia-service/datasets/raw/`.
2. Crear ocho labels con IDs 0–7 y conservar el mapa en el manifiesto.
3. Para cada imagen de Kaggle, dibujar manualmente la caja del objeto de la clase conocida por la carpeta.
4. Si hay varios objetos relevantes, dibujar una caja por instancia de la misma clase; si aparece otra clase MVP, registrarla para revisión y no etiquetarla silenciosamente.
5. Revisar cajas truncadas, oclusiones, objetos pequenos, empaques y fotos sin pieza visible.
6. Exportar YOLO solamente despues de la revision humana y validar IDs/coordenadas.
7. Mantener `air_filter` con sus cajas originales ID 14 como referencia; no fusionar ID 9 `Air Filter Cover`.

Las 1,295 imagenes de clasificacion requieren anotacion manual para detection. Las 49 de `air_filter` ya tienen boxes, pero tambien requieren inspeccion visual y validacion de calidad; no se generan cajas automaticas para ninguna fuente de clasificacion.

## Estructura procesada propuesta

Todavia no se construye el dataset definitivo ni se crean sus splits. La estructura futura sera:

```text
ia-service/datasets/processed/
  images/
    train/
    val/
    test/
  labels/
    train/
    val/
    test/
```

`raw/` permanece inmutable. `processed/` se generara solo despues de completar la anotacion, revisar calidad y aprobar la division final. El futuro `data.yaml` usara exclusivamente IDs 0–7 y no se crea en esta etapa.

En la preparacion inicial no se detectaron problemas visuales; la revision humana quedo pendiente hasta completarse en la etapa siguiente.

## Resultado de la revision visual humana

La muestra completa de 80 imagenes fue revisada manualmente:

- Revisadas: 80.
- Aprobadas: 80.
- Rechazadas: 0.
- Estado: revision visual inicial completada.
- Resultado por clase: 10/10 aprobadas para cada una de las ocho clases.
- `air_filter`: sus labels YOLO reales se conservan sin cambios.

Los 80 registros de `ia-service/datasets/review/review_manifest.csv` tienen ahora `review_status=APPROVED` y la nota `Revision visual humana aprobada`. Esta aprobacion solo valida la muestra; no convierte las 1,295 imagenes de clasificacion en ground truth de deteccion.

## Estrategia propuesta de preanotacion

La opcion mas rapida y segura es una herramienta local de anotacion, preferentemente **CVAT self-hosted**, combinada con un modelo local de propuesta de regiones como GroundingDINO y, si resulta util, SAM/SAM2 para refinar el contorno. No se instala ni se ejecuta en esta etapa.

Flujo propuesto para las 1,295 imagenes sin boxes:

1. Importar copias de trabajo, nunca modificar `raw/`.
2. Leer `dataset_manifest.csv` y agrupar cada imagen por `target_class_id` 0–7.
3. Enviar a la preanotacion solo el prompt de la clase conocida de cada imagen, por ejemplo `brake pad`, `radiator` o `headlight`.
4. Aceptar una caja propuesta solo si el modelo local localiza una region real con confianza suficiente; nunca crear automaticamente una caja que cubra toda la imagen.
5. Si no hay deteccion, hay varias detecciones o la region es ambigua, marcar la imagen para dibujo manual.
6. Revisar manualmente cada caja, ajustar bordes, eliminar falsos positivos y confirmar que la clase coincide con el ID conocido.
7. Exportar despues de la aprobacion humana en YOLO Detection con IDs 0–7.
8. Mantener las 49 anotaciones reales de `air_filter` como referencia separada; no regenerarlas ni mezclarlas automaticamente con preanotaciones.

Conocer la clase por carpeta/manifiesto permite filtrar las propuestas a una sola clase por imagen y evita errores de clasificacion entre las ocho clases. No elimina la necesidad de revisar la localizacion, oclusiones, objetos multiples, empaques y fotos sin pieza visible.

Software/modelos que se evaluarian en una etapa posterior: Docker/CVAT local, Python, PyTorch, GroundingDINO y opcionalmente SAM/SAM2. Alternativamente, una herramienta local con soporte de autoanotacion compatible con YOLO puede sustituir el script, siempre que exporte cajas revisables. No se instala nada ahora.

Estimacion de flujo: importar y mapear el manifiesto, preanotar por clase, hacer una primera revision asistida, corregir manualmente los casos ambiguos y ejecutar controles de IDs/coordenadas antes de crear `processed/`. El tiempo real depende del rendimiento local y de cuantas propuestas sean correctas; no se fija una cifra sin ejecutar una prueba piloto.

Riesgos: GroundingDINO puede confundir piezas parecidas o no localizar repuestos pequenos; las fotos de clasificacion pueden tener recortes, cajas o fondos que oculten la pieza; una confianza alta no garantiza una caja correcta; y el sesgo de las fuentes publicas puede trasladarse al modelo. Por eso toda caja preanotada debe revisarse y las fotos propias deben complementar `air_filter` y las clases con baja diversidad.

## Cierre del piloto GroundingDINO

El piloto de 40 imagenes se cerro sin escalar a las 1,295 imagenes sin boxes. GroundingDINO produjo muchas propuestas casi del tamano completo, marco numerosos casos `NEEDS_MANUAL` y obtuvo IoU promedio de 0.3959 en las cinco imagenes de `air_filter`. La decision es **NO escalar GroundingDINO** para este lote.

No se instalaron CVAT ni SAM/SAM2, no se compilaron extensiones y no se generaron cajas definitivas.

## Lote inicial para anotacion manual

Se preparo `ia-service/datasets/annotation_batch/` con **749 imagenes**:

- 100 de cada clase sin bounding boxes: 90 train, 5 valid y 5 test originales.
- 49 `air_filter` con sus labels YOLO reales.
- Total pendiente de anotacion manual: 700.
- Total ya anotado: 49.

Las copias tienen basenames unicos (`train__clase__001.jpg`, etc.) para evitar colisiones. El manifiesto es `ia-service/datasets/annotation_batch/annotation_batch_manifest.csv`.

En las copias de `air_filter`, se conservaron exclusivamente las lineas cuyo ID original era 14, se remapearon a ID final 5 y se conservaron sus coordenadas. Las anotaciones secundarias de Car Engine Bay se excluyeron del dataset RepuestoPro; no queda ningun ID 14. Los labels RAW no fueron modificados.

Controles del lote: 749 registros, 749 imagenes fisicas, 700 `PENDING`, 49 `ANNOTATED`, 0 rutas duplicadas, 0 grupos duplicados por SHA-256, 0 faltantes, 49 imagenes/49 labels de `air_filter` correspondientes y 0 lineas YOLO invalidas en las copias.

El lote no se divide aun en train/val/test definitivo y no se entrena ningun modelo.
