# AUDITORIA DE FUENTES DE DATOS PARA DATASET DE VISION

Proyecto: RepuestoPro
Fecha: 2026-09-22
Alcance: auditoria documental, sin descargas, sin entrenamiento y sin cambios de codigo.

## 1. Objetivo

Auditar la disponibilidad publica de datos para las ocho clases congeladas del MVP 1 definido en `docs/modelo-ia/PLAN_DATASET_AUTOPARTES_IA.md`. La fuente de verdad del catalogo es el `productSeed` de RepuestoPro y no se modifican sus clases.

Fuentes investigadas:

- Kaggle: `gpiosenka/car-parts-40-classes`.
- Hugging Face: `DrBimmer/car-parts-and-damage-dataset`, solo `Car Parts`.
- Fuente adicional: Kaggle `khaledchawa/car-engine-bay-pictures`, unicamente para evaluar `air_filter`.
- Fuente adicional de contexto: Ultralytics `Carparts-Seg`, unicamente para evaluar cobertura de `headlight`.

Todos los datos que no pudieron comprobarse directamente en una ficha publica se marcan como `NO VERIFICADO`.

## 2. Clases MVP auditadas

Las clases, IDs y nombres no se cambian:

| ID | Clase RepuestoPro |
|---:|---|
| 0 | brake_pad |
| 1 | brake_rotor |
| 2 | brake_caliper |
| 3 | alternator |
| 4 | oil_filter |
| 5 | air_filter |
| 6 | radiator |
| 7 | headlight |

En el catalogo real existen productos para las ocho clases. El repositorio no contiene imagenes de producto verificables: `Product.image` es opcional y las semillas no lo llenan.

## 3. Auditoria Kaggle

### 3.1 Identidad y estructura

| Campo | Resultado |
|---|---|
| Nombre exacto | `50 Types of Car Parts -Image Classification` en la ficha; slug `gpiosenka/car-parts-40-classes` |
| Plataforma | Kaggle |
| URL | https://www.kaggle.com/datasets/gpiosenka/car-parts-40-classes |
| Autor | gpiosenka, segun el slug; nombre personal completo: NO VERIFICADO |
| Descripcion | Dataset de clasificacion de imagenes de piezas de automovil |
| Numero de clases | **40 VERIFICADO por la lista publicada en fuentes secundarias accesibles; la ficha tiene titulo de 50 tipos** |
| Numero total de imagenes | NO VERIFICADO sin descargar o consultar metadata completa |
| Train/validation/test | **VERIFICADO cualitativamente**: referencias publicas indican carpetas `train`, `valid`, `test`; cantidades: NO VERIFICADO |
| Anotacion | Etiqueta a nivel de imagen por carpeta/clase |
| Bounding boxes | NO VERIFICADO; no se anuncian en la estructura consultada |
| Poligonos | NO VERIFICADO |
| Version/fecha | NO VERIFICADO |
| Licencia | LICENCIA NO VERIFICADA en la ficha consultada |

### 3.2 Por que aparecen 40 y 50

La evidencia publica es inconsistente: el slug contiene `40-classes`, una fuente secundaria reproduce una tabla de 40 etiquetas, mientras que el titulo de Kaggle dice `50 Types of Car Parts`. La explicacion exacta no puede confirmarse sin revisar el archivo/version disponible en Kaggle. Por tanto, este documento no trata como reales las diez clases adicionales: la lista operativa comprobable es la de 40 clases publicada, y el numero final del paquete queda `NO VERIFICADO`.

### 3.3 Clases publicadas verificables

La tabla publicada en la fuente secundaria consultada enumera: `AIR COMPRESSOR`, `ALTERNATOR`, `BATTERY`, `BRAKE CALIPER`, `BRAKE PAD`, `BRAKE ROTOR`, `CAMSHAFT`, `CARBERATOR`, `COIL SPRING`, `CRANKSHAFT`, `CYLINDER HEAD`, `DISTRIBUTOR`, `ENGINE BLOCK`, `FUEL INJECTOR`, `FUSE BOX`, `GAS CAP`, `HEADLIGHTS`, `IDLER ARM`, `IGNITION COIL`, `LOWER CONTROL ARM`, `LEAF SPRING`, `MUFFLER`, `OIL FILTER`, `OIL PAN`, `PISTON`, `RADIATOR`, `RADIATOR FAN`, `RIM`, `SPARK PLUG`, `STARTER`, `TAILLIGHTS`, `THERMOSTAT`, `TORQUE CONVERTER`, `TRANSMISSION`, `VACUUM BRAKE BOOSTER`, `VALVE LIFTER`, `WATER PUMP`, `OXYGEN SENSOR`, mas las etiquetas que la tabla publicada no permite leer con seguridad. El listado completo oficial final: **NO VERIFICADO**.

### 3.4 Clases Kaggle frente al MVP

| Clase Kaggle | Coincide con MVP | Clase normalizada | Accion |
|---|---|---|---|
| BRAKE PAD | SI | brake_pad | EVALUAR |
| BRAKE ROTOR | SI | brake_rotor | EVALUAR |
| BRAKE CALIPER | SI | brake_caliper | EVALUAR |
| ALTERNATOR | SI | alternator | EVALUAR |
| OIL FILTER | SI | oil_filter | EVALUAR |
| RADIATOR | SI | radiator | EVALUAR |
| HEADLIGHTS | SI | headlight | EVALUAR |
| AIR FILTER | NO VERIFICADO | air_filter | BUSCAR_OTRO_DATASET |
| BATTERY | NO | - | DESCARTAR |
| FUSE BOX | NO | - | DESCARTAR |
| PISTON | NO | - | DESCARTAR |
| RADIATOR FAN | NO | - | DESCARTAR |
| IGNITION COIL | Fuera del MVP | ignition_coil | No incorporar ahora |
| SPARK PLUG | Fuera del MVP | spark_plug | No incorporar ahora |

Kaggle es una fuente de clasificacion, no una fuente de bounding boxes confirmada. Sus ocho clases MVP no deben declararse `USAR` hasta revisar licencia, imagenes, duplicados y cantidades.

## 4. Auditoria DrBimmer

Dataset: `DrBimmer/car-parts-and-damage-dataset` en Hugging Face.

| Campo | Resultado |
|---|---|
| URL | https://huggingface.co/datasets/DrBimmer/car-parts-and-damage-dataset |
| Autor | DrBimmer / Dr. Bimmer; ficha tambien registra al contribuidor Tommy |
| Total de imagenes | **1,812 VERIFICADO en la tarjeta del dataset** |
| Car Parts | **998 imagenes VERIFICADO** |
| Car Damages | 814 imagenes VERIFICADO; NO SE UTILIZA |
| Clases Car Parts | 21 nombres publicados |
| Anotacion | Poligonos VERIFICADO |
| Formato | Compatible con COCO JSON o VIA/VGG, segun la tarjeta |
| Bounding boxes | No son la anotacion primaria; pueden derivarse de poligonos |
| Tareas declaradas | Image Segmentation y Object Detection |
| Tamano del repositorio | 3.31 GB indicado en la pagina; version exacta: NO VERIFICADO |
| Version/fecha | Commit inicial visible; fecha exacta: NO VERIFICADO |
| Licencia | MIT en la metadata actual de Hugging Face |

Clases `Car Parts` verificadas: `Windshield`, `Back-windshield`, `Front-window`, `Back-window`, `Front-door`, `Back-door`, `Front-wheel`, `Back-wheel`, `Front-bumper`, `Back-bumper`, `Headlight`, `Tail-light`, `Hood`, `Trunk`, `License-plate`, `Mirror`, `Roof`, `Grille`, `Rocker-panel`, `Quarter-panel`, `Fender`.

| Clase DrBimmer | Coincide con MVP | Clase normalizada | Tipo anotacion | Accion |
|---|---|---|---|---|
| Headlight | SI | headlight | Poligono | EVALUAR |
| Front-bumper | NO: fuera de MVP | front_bumper | Poligono | No incorporar ahora |
| Back-bumper | NO: fuera de MVP | rear_bumper | Poligono | No incorporar ahora |
| Mirror | NO: fuera de MVP | side_mirror | Poligono | No incorporar ahora |
| Grille | NO: fuera de MVP | grille | Poligono | No incorporar ahora |
| Resto de Car Parts | NO | - | Poligono | DESCARTAR |
| Car Damages | NO | - | Poligono | DESCARTAR |

DrBimmer cubre directamente solo `headlight` del MVP actual. Los poligonos pueden convertirse en bounding boxes calculando el rectangulo envolvente, pero esa transformacion aun no se ha realizado.

## 5. Datasets adicionales encontrados

Se revisaron fuentes adicionales solo para cubrir huecos del MVP. No se descargo ninguna.

| Dataset | Plataforma | Clase util | Tipo | Licencia | Cantidad verificable | Recomendacion |
|---|---|---|---|---|---:|---|
| Car Engine Bay Pictures | Kaggle, `khaledchawa/car-engine-bay-pictures` | air_filter | Deteccion YOLO | LICENCIA NO VERIFICADA | **1,201 imagenes VERIFICADO**; cantidad por clase NO VERIFICADA | INVESTIGAR licencia y estructura antes de usar |
| Carparts-Seg | Ultralytics | headlight | Segmentacion | LICENCIA NO VERIFICADA en la documentacion consultada | **3,833 imagenes VERIFICADO**, 23 clases, split 3,156/401/276 | Solo fuente secundaria para headlight; revisar licencia |

### Car Engine Bay Pictures

La ficha publica de Kaggle describe dos carpetas: `images` con 1,201 imagenes de compartimentos de motor y `labels` con etiquetas YOLO. La ficha muestra `Air Filter` y `Air Filter Cover` como etiquetas. La cantidad exacta de imagenes para `Air Filter`, la lista completa de clases, autor completo, version y licencia no fueron verificadas. No debe mezclarse automaticamente `Air Filter Cover` con `air_filter`.

### Carparts-Seg

La documentacion de Ultralytics describe 3,833 imagenes, 23 clases, mascaras de instancia y splits train/validation/test. Sus etiquetas incluyen `front_light`, `front_left_light`, `front_right_light`, `back_light` y otras partes de carroceria. Para RepuestoPro solo podria aportar cobertura de `headlight` despues de una decision explicita de normalizacion. No cubre las seis piezas mecanicas restantes del MVP.

No se encontraron, con evidencia suficiente y sin descargar, fuentes adicionales confiables que cubran `brake_pad`, `brake_rotor`, `brake_caliper`, `alternator`, `oil_filter` o `radiator` mejor que la cobertura preliminar de Kaggle. Estado de busqueda: cobertura exacta por clase **NO VERIFICADA**.

## 6. Cobertura por clase

| Clase RepuestoPro | Dataset | Nombre original | Existe | Tipo anotacion | Cantidad verificable | Accion |
|---|---|---|---|---|---:|---|
| brake_pad | Kaggle | BRAKE PAD | SI | Etiqueta de imagen | NO VERIFICADO | EVALUAR |
| brake_rotor | Kaggle | BRAKE ROTOR | SI | Etiqueta de imagen | NO VERIFICADO | EVALUAR |
| brake_caliper | Kaggle | BRAKE CALIPER | SI | Etiqueta de imagen | NO VERIFICADO | EVALUAR |
| alternator | Kaggle | ALTERNATOR | SI | Etiqueta de imagen | NO VERIFICADO | EVALUAR |
| oil_filter | Kaggle | OIL FILTER | SI | Etiqueta de imagen | NO VERIFICADO | EVALUAR |
| air_filter | Kaggle | NO VERIFICADO | NO VERIFICADO | NO VERIFICADO | NO VERIFICADO | BUSCAR_OTRO_DATASET |
| air_filter | Kaggle adicional | AIR FILTER | SI | YOLO, segun ficha | NO VERIFICADO | EVALUAR |
| radiator | Kaggle | RADIATOR | SI | Etiqueta de imagen | NO VERIFICADO | EVALUAR |
| headlight | Kaggle | HEADLIGHTS | SI | Etiqueta de imagen | NO VERIFICADO | EVALUAR |
| headlight | DrBimmer | Headlight | SI | Poligono | NO VERIFICADO por clase | EVALUAR |
| headlight | Carparts-Seg | front_light y variantes | SI parcial | Mascara de instancia | NO VERIFICADO por clase | EVALUAR |

Interpretacion: Kaggle tiene coincidencia nominal para siete clases, pero su cantidad, licencia y calidad por clase no estan verificadas. `air_filter` necesita la auditoria de la fuente adicional y, en cualquier caso, fotografias propias. DrBimmer y Carparts-Seg solo ayudan a `headlight`, que es una pieza externa y no representa el nucleo mecanico.

## 7. Classification vs Detection

| Fuente | Classification | Object Detection | Segmentation | Transformacion necesaria |
|---|---|---|---|---|
| Kaggle car-parts-40-classes | SI, etiqueta por carpeta | NO VERIFICADO | NO VERIFICADO | Para detection, anotar bounding boxes manualmente |
| DrBimmer Car Parts | No es el formato principal | SI, derivable | SI, poligonos | Convertir poligono a caja o conservar segmentacion |
| Car Engine Bay Pictures | NO VERIFICADO como clasificacion | SI, etiquetas YOLO segun ficha | NO VERIFICADO | Auditar clases, licencia y labels |
| Carparts-Seg | No es el formato principal | SI, derivable de mascaras | SI, mascaras de instancia | Mapear etiquetas de luces y decidir conversion |

Classification es imagen completa con una clase; no localiza la pieza. Detection necesita una caja y una clase por objeto. Segmentation necesita una mascara/poligono y puede producir una caja envolvente, con perdida de precision de contorno. No se convertira ningun formato en esta tarea.

## 8. Licencias y restricciones

### LICENCIAS Y RESTRICCIONES

| Dataset | Licencia exacta | Uso academico | Modificacion | Redistribucion | Atribucion | Fuente |
|---|---|---|---|---|---|---|
| Kaggle gpiosenka/car-parts-40-classes | **LICENCIA NO VERIFICADA** | NO ASUMIR | NO ASUMIR | NO ASUMIR | NO VERIFICADO | Ficha Kaggle |
| DrBimmer/car-parts-and-damage-dataset | MIT en metadata de Hugging Face | Permitido por MIT, sujeto al texto exacto | Permitida por MIT | Permitida por MIT con aviso/licencia | Incluir aviso y licencia | Metadata y README del dataset |
| Kaggle Car Engine Bay Pictures | **LICENCIA NO VERIFICADA** | NO ASUMIR | NO ASUMIR | NO ASUMIR | NO VERIFICADO | Ficha Kaggle |
| Ultralytics Carparts-Seg | **LICENCIA NO VERIFICADA** en la fuente consultada | NO ASUMIR | NO ASUMIR | NO ASUMIR | NO VERIFICADO | Documentacion Ultralytics |

El hecho de que un dataset sea publico no concede automaticamente permiso de redistribucion o entrenamiento comercial. Antes de descargar se deben guardar la URL, fecha, version, licencia y texto de atribucion. DrBimmer tiene una discusion publica que cuestiona la disponibilidad de la carpeta `Car Parts`; por ello tambien debe comprobarse que los archivos de partes esten realmente accesibles antes de planificar su uso.

## 9. Fotografias propias necesarias

Las ocho clases requieren fotos propias para adaptar el modelo a la tienda, marcas, empaques y condiciones de Bolivia. La prioridad mas alta es `air_filter`, porque no tiene cobertura confirmada en los dos datasets principales. Tambien se recomiendan fotos propias para `brake_pad`, `brake_rotor`, `brake_caliper`, `alternator`, `oil_filter` y `radiator`, aunque Kaggle tenga coincidencia nominal.

Para cada pieza: varias marcas, nuevos/usados, caja y sin caja, distintos angulos, fondos de tienda/taller, iluminacion natural y artificial, oclusion parcial, mano sosteniendo, pieza montada/desmontada y ejemplos negativos de piezas parecidas. Cada foto debe quedar vinculada a `itemCode`, marca, modelo, ano, `oemCode` y `factoryCode` fuera de la etiqueta visual.

No se deben fotografiar rostros, placas ni documentos con datos personales. No se conoce todavia la cantidad objetivo de fotos propias; queda **NO VERIFICADO** hasta definir protocolo y capacidad de captura.

## 10. Matriz final de las 8 clases

| ID | Clase | Fuente principal | Fuente secundaria | Classification | Detection | Fotos propias | Estado |
|---:|---|---|---|---|---|---|---|
| 0 | brake_pad | Kaggle, nominal | Propias | Parcial, etiquetas de imagen | No verificada | SI | COBERTURA_PARCIAL |
| 1 | brake_rotor | Kaggle, nominal | Propias | Parcial, etiquetas de imagen | No verificada | SI | COBERTURA_PARCIAL |
| 2 | brake_caliper | Kaggle, nominal | Propias | Parcial, etiquetas de imagen | No verificada | SI | COBERTURA_PARCIAL |
| 3 | alternator | Kaggle, nominal | Propias | Parcial, etiquetas de imagen | No verificada | SI | COBERTURA_PARCIAL |
| 4 | oil_filter | Kaggle, nominal | Propias | Parcial, etiquetas de imagen | No verificada | SI | COBERTURA_PARCIAL |
| 5 | air_filter | Car Engine Bay Pictures, nominal | Propias | NO VERIFICADO | YOLO segun ficha, no auditado | SI | REQUIERE_DATASET |
| 6 | radiator | Kaggle, nominal | Propias | Parcial, etiquetas de imagen | No verificada | SI | COBERTURA_PARCIAL |
| 7 | headlight | DrBimmer Car Parts | Kaggle / Carparts-Seg | Poligono, no classification directa | Poligono convertible | SI | COBERTURA_PARCIAL |

Ninguna clase se considera lista para entrenamiento. La cobertura nominal no equivale a datos suficientes, limpios o legalmente utilizables.

## 11. Estrategia recomendada del primer modelo

Se mantiene la recomendacion del plan: **Classification primero y Detection despues**.

Classification es la primera etapa porque Kaggle esta descrito como clasificacion de pieza aislada y el objetivo inicial es validar si las ocho clases son visualmente separables. Las clases con coincidencia nominal para clasificacion son `brake_pad`, `brake_rotor`, `brake_caliper`, `alternator`, `oil_filter`, `radiator` y `headlight`. Para todas, la cantidad real por clase, balance y licencia siguen pendientes.

Detection no esta listo para las piezas mecanicas: Kaggle no confirma bounding boxes. DrBimmer tiene poligonos, pero cubre del MVP solo `headlight`. La fuente de `air_filter` anuncia etiquetas YOLO, aunque su lista de clases y licencia aun no fueron auditadas. Las clases que pasen a detection necesitaran bounding boxes verificadas o anotacion manual.

Por tanto, la secuencia tecnica recomendada es:

1. Verificar licencia, archivos y conteos sin mezclar fuentes.
2. Auditar una muestra y eliminar duplicados o etiquetas incorrectas.
3. Reunir fotos propias de las ocho clases.
4. Construir primero un experimento de clasificacion aislada.
5. Anotar manualmente cajas solo cuando exista el requisito de localizar piezas en una escena.

## 12. Riesgos encontrados

- La ficha de Kaggle presenta una discrepancia entre el slug de 40 clases y el titulo de 50 tipos.
- La lista completa, el numero total de imagenes, los conteos por clase y la licencia de Kaggle no estan verificadas.
- DrBimmer tiene licencia MIT en la metadata, pero existe una discusion sobre la disponibilidad efectiva de `Car Parts`; debe comprobarse antes de usarlo.
- DrBimmer es principalmente segmentacion de carroceria, no un dataset de repuestos mecanicos.
- No hay imagenes propias en el repositorio RepuestoPro.
- No hay evidencia suficiente de `air_filter` en las dos fuentes principales.
- Las etiquetas de clase no garantizan que una pieza aislada se parezca a los productos y empaques de la tienda.
- Las clases de clasificacion no generan bounding boxes automaticamente.
- Las fuentes adicionales pueden tener licencia, procedencia, duplicados o calidad no comprobados.
- La cobertura aparente no implica cantidad suficiente para un modelo; todas las cantidades no verificadas deben medirse antes de entrenar.

## 13. Proximo paso recomendado

**Una sola accion:** obtener y conservar la metadata oficial y las licencias de Kaggle, DrBimmer y Car Engine Bay Pictures, sin descargar imagenes, y registrar para cada una la lista exacta de archivos, clases y conteos verificables.

### Control de alcance

En esta auditoria no se descargaron datasets ni imagenes, no se crearon carpetas de entrenamiento, no se instalaron librerias, no se etiquetaron ni convirtieron anotaciones, no se entreno ningun modelo y no se modificaron backend, frontend, mobile, Prisma, productos o categorias.
