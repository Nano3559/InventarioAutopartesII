# PLAN DE DATASET DE AUTOPARTES PARA IA

Documento de auditoria taxonomica para RepuestoPro. Fecha: 2026-09-22.

## 1. Catalogo real analizado

Fuentes revisadas: `backend/prisma/schema.prisma`, `backend/prisma/seed-data.ts`, `backend/prisma/enrich-data.ts`, modulos de productos/public, frontend y los documentos `AUDITORIA_IMPLEMENTACION_IA_VISION.md` y `PLAN_IMPLEMENTACION_IA_VISION.md`.

La fuente estructurada vigente es `productSeed` en `seed-data.ts`. Contiene **56 productos**. `enrich-data.ts` reutiliza esos mismos productos y no agrega otra taxonomia. El modelo `Product` permite `name`, `detail`, `oemCode`, `factoryCode`, `image` y `categoryId`, pero las semillas no contienen imagenes de producto; `image` queda nulo. La busqueda actual por imagen es OCR, no reconocimiento visual.

| Producto actual | Categoria actual | Tipo de pieza | Interna/Externa | Candidata IA | Observaciones |
|---|---|---|---|---|---|
| Pastillas de Freno Delanteras | Frenos | brake_pad | INTERNA | SI | Variacion delantera |
| Disco de Freno Delantero | Frenos | brake_rotor | INTERNA | SI | Disco ventilado |
| Pastillas de Freno Traseras | Frenos | brake_pad | INTERNA | SI | Misma clase que pastilla |
| Disco de Freno Trasero | Frenos | brake_rotor | INTERNA | SI | Misma clase que disco |
| Caliper de Freno Delantero | Frenos | brake_caliper | INTERNA | SI | Pieza distinguible |
| Manguera de Freno Delantera | Frenos | brake_hose | INTERNA | EVALUAR | Pieza alargada, posible ambiguedad |
| Retenedor de Caliper | Frenos | caliper_hardware | INTERNA | NO | Pequeno y dificil de distinguir |
| Pastillas Ceramicas Premium | Frenos | brake_pad | INTERNA | SI | Misma clase que pastilla |
| Bujia de Encendido (2 productos) | Motor | spark_plug | INTERNA | SI | Dos marcas/modelos, una clase |
| Bobina de Encendido | Motor | ignition_coil | INTERNA | SI | Clase en Kaggle |
| Bomba de Agua | Motor | water_pump | INTERNA | SI | Clase en Kaggle |
| Correa de Distribucion | Motor | timing_belt | INTERNA | EVALUAR | Puede confundirse con otras correas |
| Juego de Juntas | Motor | gasket_set | INTERNA | NO | Kit heterogeneo, sin forma estable |
| Valvula EGR | Motor | egr_valve | INTERNA | EVALUAR | Requiere fotos propias |
| Rodamiento de Ciguenal | Motor | crankshaft_bearing | INTERNA | NO | Pequeno y poco representativo |
| Radiador de Agua | Motor | radiator | INTERNA | SI | Refrigeracion, clase publica util |
| Tapa de Radiador | Motor | radiator_cap | INTERNA | EVALUAR | Pequena, puede agruparse en futuro |
| Correa Serpentina | Motor | serpentine_belt | INTERNA | EVALUAR | Forma similar a timing_belt |
| Soporte de Motor | Motor | engine_mount | INTERNA | EVALUAR | Fotos propias necesarias |
| Manguera de Radiador | Motor | radiator_hose | INTERNA | EVALUAR | Forma variable |
| Deposito de Expansion | Motor | expansion_tank | INTERNA | SI | Silueta relativamente estable |
| Serpentina AC | Motor | serpentine_belt | INTERNA | EVALUAR | Unificar con correas |
| Tensador de Correa | Motor | belt_tensioner | INTERNA | EVALUAR | Pieza mecanica pequena |
| Termostato | Motor | thermostat | INTERNA | EVALUAR | Pequeno, fotos propias |
| Amortiguador Delantero | Suspension | shock_absorber | INTERNA | SI | Una clase con trasero |
| Amortiguador Trasero | Suspension | shock_absorber | INTERNA | SI | Una clase con delantero |
| Brazo de Suspension Inferior | Suspension | control_arm | INTERNA | SI | Clase visualmente diferenciable |
| Rotula Inferior | Suspension | ball_joint | INTERNA | EVALUAR | Pequena |
| Estabilizadora Delantera | Suspension | sway_bar | INTERNA | EVALUAR | Requiere fotos propias |
| Buje de Suspension | Suspension | suspension_bushing | INTERNA | NO | Muy pequeno y ambiguo |
| Alternador | Electrico | alternator | INTERNA | SI | Clase en Kaggle |
| Marcha de Arranque | Electrico | starter_motor | INTERNA | SI | Clase en Kaggle |
| Foco Halogeno H7 | Electrico | headlight_bulb | INTERNA | EVALUAR | No confundir con faro completo |
| Sensor de Oxigeno | Electrico | oxygen_sensor | INTERNA | SI | Clase en Kaggle |
| Modulo de Encendido | Electrico | ignition_module | INTERNA | EVALUAR | Caja pequena, requiere fotos propias |
| Foco LED H11 | Electrico | headlight_bulb | INTERNA | EVALUAR | Unificar con foco, no con headlight |
| Filtro de Aceite | Filtros | oil_filter | INTERNA | SI | Clase en Kaggle |
| Filtro de Aire | Filtros | air_filter | INTERNA | SI | Clase en Kaggle |
| Filtro de Combustible | Filtros | fuel_filter | INTERNA | SI | Clase en Kaggle |
| Filtro de Aire Deportivo | Filtros | air_filter | INTERNA | EVALUAR | Variante de air_filter |
| Filtro de Cabina | Filtros | cabin_filter | INTERNA | SI | Requiere dataset propio/publico |
| Filtro de Aceite Hidraulico | Filtros | hydraulic_filter | INTERNA | EVALUAR | No es oil_filter de motor |
| Parachoque Delantero | Carroceria | front_bumper | EXTERNA | SI | El catalogo si lo utiliza |
| Retrovisor Lateral Izquierdo | Carroceria | side_mirror | EXTERNA | SI | Unificar lados |
| Farola Delantera Derecha | Carroceria | headlight | EXTERNA | SI | Unificar farola/faro |
| Parrilla Delantera | Carroceria | grille | EXTERNA | SI | Clase en DrBimmer |
| Parachoque Trasero | Carroceria | rear_bumper | EXTERNA | SI | Clase en DrBimmer |
| Tapa de Combustible | Carroceria | fuel_door | EXTERNA | EVALUAR | No aparece como clase prioritaria conocida |
| Kit de Embrague (2 productos) | Transmision | clutch_kit | INTERNA | SI | Fotografiar kit y componentes |
| Cilindro Maestro de Embrague | Transmision | clutch_master_cylinder | INTERNA | EVALUAR | Requiere fotos propias |
| Amortiguador de Transmision | Transmision | transmission_mount | INTERNA | NO | Nombre comercial ambiguo |
| Reten de Transmision | Transmision | transmission_seal | INTERNA | NO | Pequeno y sin forma estable |
| Soporte de Transmision | Transmision | transmission_mount | INTERNA | EVALUAR | Unificar solo tras validar imagenes |

**Nota:** las cantidades por tipo no son cantidades de imagenes. Son productos del catalogo. No hay imagenes de producto verificables en el repositorio.

## 2. Categorias actuales

El repositorio tiene **7 categorias de producto** usadas por las semillas: Frenos, Motor, Suspension, Electrico, Filtros, Carroceria y Transmision. No existe una categoria persistida llamada `Adicionales`; ese comentario de `seed-data.ts` agrupa productos que se asignan a Motor, Transmision o Electrico.

| Categoria | Productos del catalogo | Piezas reales |
|---|---:|---|
| Frenos | 8 | pastillas, discos, caliper, manguera, retenedor |
| Motor | 17 | bujias, bobina, bomba de agua, correas, juntas, EGR, rodamiento, refrigeracion, soportes, termostato |
| Suspension | 6 | amortiguadores, brazo, rotula, estabilizadora, buje |
| Electrico | 7 | alternador, arranque, focos, sensor, modulo |
| Filtros | 6 | aceite, aire, combustible, cabina, hidraulico |
| Carroceria | 6 | parachoques, retrovisor, farola, parrilla, tapa combustible |
| Transmision | 6 | embrague, cilindro, amortiguador/soporte, reten |

## 3. Taxonomia IA normalizada

Se identifican **45 tipos de pieza comerciales del catalogo** al separar variantes reales del nombre y unificar duplicados obvios. Se agregan cuatro clases externas (`battery`, `fuse_box`, `piston`, `radiator_fan`) solo para comparar fuentes publicas, por eso la tabla contiene 49 filas. Para el primer modelo no todas deben ser clases: una clase se conserva solo si tiene utilidad, forma identificable y posibilidad razonable de obtener imagenes.

| ID | Clase IA | Nombre sistema | Categoria sistema | Sinonimos | Mantener |
|---:|---|---|---|---|---|
| 1 | brake_pad | Pastilla de freno | Frenos | brake pads, brakepad | SI |
| 2 | brake_rotor | Disco de freno | Frenos | brake disc, brake rotor | SI |
| 3 | brake_caliper | Caliper de freno | Frenos | brake calliper | SI |
| 4 | brake_hose | Manguera de freno | Frenos | brake line hose | EVALUAR |
| 5 | caliper_hardware | Retenedor de caliper | Frenos | caliper retainer | NO |
| 6 | spark_plug | Bujia | Motor | spark plug, ignition plug | SI |
| 7 | ignition_coil | Bobina de encendido | Motor | ignition coil, coil pack | SI |
| 8 | water_pump | Bomba de agua | Motor | engine water pump | SI |
| 9 | timing_belt | Correa de distribucion | Motor | timing belt | EVALUAR |
| 10 | gasket_set | Juego de juntas | Motor | gasket kit, seal kit | NO |
| 11 | egr_valve | Valvula EGR | Motor | EGR valve | EVALUAR |
| 12 | crankshaft_bearing | Rodamiento de ciguenal | Motor | crank bearing | NO |
| 13 | radiator | Radiador | Motor | water radiator, car radiator | SI |
| 14 | radiator_cap | Tapa de radiador | Motor | radiator lid | EVALUAR |
| 15 | serpentine_belt | Correa serpentina | Motor | serpentine belt, AC belt | EVALUAR |
| 16 | engine_mount | Soporte de motor | Motor | motor mount | EVALUAR |
| 17 | radiator_hose | Manguera de radiador | Motor | coolant hose | EVALUAR |
| 18 | expansion_tank | Deposito de expansion | Motor | coolant reservoir, overflow tank | SI |
| 19 | belt_tensioner | Tensador de correa | Motor | belt tensioner, idler tensioner | EVALUAR |
| 20 | thermostat | Termostato | Motor | engine thermostat | EVALUAR |
| 21 | shock_absorber | Amortiguador | Suspension | shock, strut | SI |
| 22 | control_arm | Brazo de suspension | Suspension | lower control arm | SI |
| 23 | ball_joint | Rotula | Suspension | ball joint | EVALUAR |
| 24 | sway_bar | Barra estabilizadora | Suspension | stabilizer bar, anti-roll bar | EVALUAR |
| 25 | suspension_bushing | Buje de suspension | Suspension | control arm bushing | NO |
| 26 | alternator | Alternador | Electrico | alternator | SI |
| 27 | starter_motor | Marcha de arranque | Electrico | starter, starter motor | SI |
| 28 | headlight_bulb | Foco automotriz | Electrico | headlight bulb, H7, H11, LED bulb | EVALUAR |
| 29 | oxygen_sensor | Sensor de oxigeno | Electrico | O2 sensor, lambda sensor | SI |
| 30 | ignition_module | Modulo de encendido | Electrico | ignition control module | EVALUAR |
| 31 | oil_filter | Filtro de aceite | Filtros | oil filter | SI |
| 32 | air_filter | Filtro de aire | Filtros | air filter, performance air filter | SI |
| 33 | fuel_filter | Filtro de combustible | Filtros | fuel filter | SI |
| 34 | cabin_filter | Filtro de cabina | Filtros | cabin air filter, pollen filter | SI |
| 35 | hydraulic_filter | Filtro hidraulico | Filtros | transmission oil filter | EVALUAR |
| 36 | front_bumper | Parachoque delantero | Carroceria | front bumper | SI |
| 37 | rear_bumper | Parachoque trasero | Carroceria | back bumper, rear bumper | SI |
| 38 | side_mirror | Retrovisor | Carroceria | mirror, side mirror, wing mirror | SI |
| 39 | headlight | Faro/farola | Carroceria | head light, headlamp, front light | SI |
| 40 | grille | Parrilla | Carroceria | grill, front grille | SI |
| 41 | fuel_door | Tapa de combustible | Carroceria | gas cap door, fuel flap | EVALUAR |
| 42 | clutch_kit | Kit de embrague | Transmision | clutch kit | SI |
| 43 | clutch_master_cylinder | Cilindro maestro de embrague | Transmision | clutch master | EVALUAR |
| 44 | transmission_mount | Soporte de transmision | Transmision | transmission mount | EVALUAR |
| 45 | transmission_seal | Reten de transmision | Transmision | transmission oil seal | NO |
| 46 | battery | Bateria | No existe | car battery | NO: no esta en catalogo |
| 47 | fuse_box | Caja de fusibles | No existe | fuse panel | NO: no esta en catalogo |
| 48 | piston | Piston | No existe | engine piston | NO: no esta en catalogo |
| 49 | radiator_fan | Ventilador de radiador | No existe | cooling fan | NO: no esta en catalogo |

Las clases 46–49 se documentan solo para comparar fuentes publicas; no deben entrar al dataset de RepuestoPro hasta que exista producto real en el catalogo.

## 4. Piezas internas

Se consideran internas o de compartimiento mecanico: `brake_pad`, `brake_rotor`, `brake_caliper`, `brake_hose`, `spark_plug`, `ignition_coil`, `water_pump`, `timing_belt`, `egr_valve`, `radiator`, `radiator_cap`, `serpentine_belt`, `engine_mount`, `radiator_hose`, `expansion_tank`, `belt_tensioner`, `thermostat`, `shock_absorber`, `control_arm`, `ball_joint`, `sway_bar`, `alternator`, `starter_motor`, `headlight_bulb`, `oxygen_sensor`, `ignition_module`, `oil_filter`, `air_filter`, `fuel_filter`, `cabin_filter`, `hydraulic_filter`, `clutch_kit`, `clutch_master_cylinder`, `transmission_mount` y `transmission_seal`.

La etiqueta visual no debe codificar marca, modelo, ano, lado ni OEM. Esos atributos deben seguir viniendo del catalogo (`brand`, `model`, `year`, `oemCode`, `factoryCode`) despues de la deteccion.

## 5. Piezas externas aceptadas

El catalogo real contiene seis tipos externos que si son relevantes para repuestos: `front_bumper`, `rear_bumper`, `side_mirror`, `headlight`, `grille` y `fuel_door`. Los cinco primeros son prioritarios por utilidad comercial y por existir con nombres claros en el catalogo. `fuel_door` queda como evaluacion porque solo existe un producto y su disponibilidad publica en datasets no fue confirmada.

No se incluira carroceria estructural completa. La deteccion debe reconocer el repuesto aislado o la pieza visible, no clasificar el vehiculo completo.

## 6. Piezas descartadas

### Descartadas para el MVP

`caliper_hardware`, `gasket_set`, `crankshaft_bearing`, `suspension_bushing`, `transmission_seal`, `fuel_door`, `ignition_module`, `clutch_master_cylinder`, `hydraulic_filter`, `radiator_cap`, `belt_tensioner`, `sway_bar` y `brake_hose` se dejan fuera del MVP por tamano, ambiguedad, poca representacion o falta de imagenes verificadas.

### Descartadas por no existir en el catalogo

`battery`, `fuse_box`, `piston` y `radiator_fan` aparecen en la lista publica del dataset de Kaggle consultada, pero no son productos de RepuestoPro. No deben incorporarse solo porque existan en un dataset.

### Descartadas como objetivo de negocio

Puertas, ventanas, parabrisas, techo, capot, paneles laterales, quarter-panel y placa son piezas de carroceria del dataset DrBimmer, pero no son foco del inventario actual y se excluyen.

## 7. Sinonimos y renombrado

| Nombre original o variante | Clase normalizada |
|---|---|
| brake pad, brakepad, pastillas de freno | brake_pad |
| brake disc, brake rotor, disco de freno | brake_rotor |
| shock, strut, amortiguador | shock_absorber |
| alternator | alternator |
| starter, starter motor, marcha de arranque | starter_motor |
| oil filter, filtro de aceite | oil_filter |
| air filter, performance air filter | air_filter |
| fuel filter | fuel_filter |
| cabin filter, pollen filter | cabin_filter |
| headlight, head lamp, headlamp, front light, farola | headlight |
| tail-light, taillight, rear light | tail_light; NO existe en catalogo actual |
| mirror, side mirror, wing mirror, retrovisor | side_mirror |
| grille, grill, front grille, parrilla | grille |
| front bumper, parachoque delantero | front_bumper |
| back bumper, rear bumper, parachoque trasero | rear_bumper |
| spark plug, bujia | spark_plug |
| ignition coil, coil pack | ignition_coil |
| radiator, water radiator | radiator |
| serpentine belt, AC belt | serpentine_belt |
| clutch kit | clutch_kit |

No se deben crear clases separadas por `front/rear`, `left/right`, marca o modelo salvo que una futura auditoria de imagen demuestre una necesidad operacional.

## 8. Comparacion Kaggle

Dataset: `gpiosenka/car-parts-40-classes`.

La ficha publica consultada lo describe como **image classification** y una fuente secundaria accesible lista 40 etiquetas, con carpetas `train`, `valid` y `test`. La ficha tambien aparece titulada como 50 tipos; existe una discrepancia de nombre que debe resolverse revisando el archivo descargado antes de cualquier uso. Por eso no se afirma aqui un numero final de clases o imagenes del paquete local.

Clases publicadas que coinciden o son utiles para RepuestoPro: `ALTERNATOR`, `BRAKE CALIPER`, `BRAKE PAD`, `BRAKE ROTOR`, `IGNITION COIL`, `HEADLIGHTS`, `OIL FILTER`, `OXYGEN SENSOR`, `RADIATOR`, `RADIATOR HOSE`, `SPARK PLUG`, `STARTER`, `THERMOSTAT`, `WATER PUMP`, `TAIL LIGHTS`, `RIM` y `FUEL INJECTOR` si el catalogo futuro los incorpora.

| Dataset | Tipo | Formato | Utilidad |
|---|---|---|---|
| Kaggle car-parts-40-classes | Clasificacion | Carpetas por clase, train/valid/test; sin bounding boxes confirmadas | Alta para clasificacion de piezas aisladas; no sirve directamente para YOLO Detection |

No se debe convertir automaticamente una imagen clasificada en bounding box: las cajas tendrian que anotarse manualmente.

## 9. Comparacion Hugging Face DrBimmer

Dataset: `DrBimmer/car-parts-and-damage-dataset`. La pagina publica describe 1,812 imagenes totales y una seccion `Car Parts` de 998 imagenes, con anotaciones poligonales. Es un dataset de partes y danos; solo se considera la seccion de partes. No se usara la seccion de danos para clases de repuestos.

Clases de partes verificadas en la ficha: `Windshield`, `Back-windshield`, `Front-window`, `Back-window`, `Front-door`, `Back-door`, `Front-wheel`, `Back-wheel`, `Front-bumper`, `Back-bumper`, `Headlight`, `Tail-light`, `Hood`, `Trunk`, `License-plate`, `Mirror`, `Roof`, `Grille`, `Rocker-panel`, `Quarter-panel` y `Fender`.

| Dataset | Tipo | Formato | Utilidad |
|---|---|---|---|
| DrBimmer Car Parts | Segmentacion / deteccion | Poligonos, compatibles con COCO JSON o VIA/VGG | Util para partes externas y para generar mascaras/cajas; solo parcialmente util para RepuestoPro |
| DrBimmer Car Damages | Segmentacion de danos | Poligonos | DESCARTAR para el dataset de piezas |

Clases aprovechables para este catalogo: `Front-bumper` → `front_bumper`, `Back-bumper` → `rear_bumper`, `Headlight` → `headlight`, `Mirror` → `side_mirror` y `Grille` → `grille`. `Front-wheel` y `Back-wheel` no corresponden a un producto vigente del seed, por lo que quedan como futuras, no como clases actuales.

## 10. Mapeo dataset → catalogo

| Clase dataset | Dataset | Existe en sistema | Accion | Clase final |
|---|---|---|---|---|
| Brake Pad | Kaggle | SI | RENOMBRAR | brake_pad |
| Brake Rotor | Kaggle | SI | RENOMBRAR | brake_rotor |
| Brake Caliper | Kaggle | SI | RENOMBRAR | brake_caliper |
| Alternator | Kaggle | SI | RENOMBRAR | alternator |
| Ignition Coil | Kaggle | SI | RENOMBRAR | ignition_coil |
| Headlights | Kaggle | SI | RENOMBRAR | headlight |
| Oil Filter | Kaggle | SI | RENOMBRAR | oil_filter |
| Oxygen Sensor | Kaggle | SI | RENOMBRAR | oxygen_sensor |
| Radiator | Kaggle | SI | RENOMBRAR | radiator |
| Radiator Hose | Kaggle | SI | RENOMBRAR | radiator_hose |
| Spark Plug | Kaggle | SI | RENOMBRAR | spark_plug |
| Starter | Kaggle | SI | RENOMBRAR | starter_motor |
| Thermostat | Kaggle | SI | RENOMBRAR | thermostat |
| Water Pump | Kaggle | SI | RENOMBRAR | water_pump |
| Battery | Kaggle | NO | DESCARTAR | - |
| Fuse Box | Kaggle | NO | DESCARTAR | - |
| Piston | Kaggle | NO | DESCARTAR | - |
| Radiator Fan | Kaggle | NO | DESCARTAR | - |
| Front-bumper | DrBimmer | SI | RENOMBRAR | front_bumper |
| Back-bumper | DrBimmer | SI | RENOMBRAR | rear_bumper |
| Headlight | DrBimmer | SI | RENOMBRAR | headlight |
| Mirror | DrBimmer | SI | RENOMBRAR | side_mirror |
| Grille | DrBimmer | SI | RENOMBRAR | grille |
| Front-wheel | DrBimmer | NO | EVALUAR | - |
| Back-wheel | DrBimmer | NO | EVALUAR | - |
| Tail-light | DrBimmer | NO | DESCARTAR | - |
| Front-door / Back-door | DrBimmer | NO relevante | DESCARTAR | - |
| Windshield / windows / roof | DrBimmer | NO relevante | DESCARTAR | - |
| Hood / trunk / fender / quarter-panel | DrBimmer | NO relevante | DESCARTAR | - |
| Damage classes | DrBimmer | NO aplica | DESCARTAR | - |

La accion `USAR` queda reservada para despues de inspeccionar licencia, duplicados, calidad, distribucion por clase y compatibilidad de anotaciones. En esta etapa se propone `RENOMBRAR` y auditar antes de incorporar.

## 11. MVP recomendado

### MVP 1: 8 clases

1. `brake_pad`
2. `brake_rotor`
3. `brake_caliper`
4. `alternator`
5. `oil_filter`
6. `air_filter`
7. `radiator`
8. `headlight`

Estas clases combinan utilidad comercial, productos reales, nombres claros y disponibilidad parcial en Kaggle/DrBimmer. El modelo inicial debe clasificar una pieza aislada. No se deben mezclar lados, marcas o modelos como clases.

### MVP 2: 16 clases

Agregar: `spark_plug`, `ignition_coil`, `water_pump`, `starter_motor`, `oxygen_sensor`, `shock_absorber`, `control_arm` y `side_mirror`.

El paso a MVP 2 queda condicionado a medir balance, licencia, calidad y variacion visual. La existencia de una clase en un dataset no garantiza que haya suficientes imagenes utiles para RepuestoPro.

## 12. Clases futuras

Despues del MVP se pueden evaluar `front_bumper`, `rear_bumper`, `grille`, `clutch_kit`, `fuel_filter`, `cabin_filter`, `radiator_hose`, `expansion_tank`, `thermostat`, `egr_valve`, `timing_belt`, `serpentine_belt`, `engine_mount`, `ball_joint`, `sway_bar`, `headlight_bulb`, `clutch_master_cylinder`, `transmission_mount` y `fuel_door`.

No se agregan `battery`, `fuse_box`, `piston`, `radiator_fan`, `tail_light`, ruedas ni piezas estructurales hasta que aparezcan productos reales o se apruebe una ampliacion del catalogo.

## 13. Huecos de dataset

No existe un repositorio local de fotos de productos: `Product.image` es opcional, las semillas no lo llenan y `enrich-data.ts` conserva `image: null`. Por tanto, la cantidad de imagenes disponibles del sistema es **0 verificadas**.

| Clase requerida | Imagenes publicas disponibles | Cantidad local | Accion |
|---|---|---:|---|
| brake_pad | MEDIA/ALTA en Kaggle, verificar licencia | 0 | Auditar publicas + fotos propias |
| brake_rotor | MEDIA en Kaggle | 0 | Auditar publicas + fotos propias |
| brake_caliper | MEDIA en Kaggle | 0 | Auditar publicas + propias |
| alternator | MEDIA en Kaggle | 0 | Auditar publicas + propias |
| oil_filter | MEDIA/ALTA en Kaggle | 0 | Auditar publicas + propias |
| air_filter | NO VERIFICADO en los dos datasets evaluados | 0 | Fotos propias o dataset adicional |
| radiator | MEDIA en Kaggle | 0 | Auditar publicas + propias |
| headlight | MEDIA en DrBimmer | 0 | Convertir poligonos a cajas si aplica + propias |
| shock_absorber | NO VERIFICADO en los dos datasets evaluados | 0 | Dataset adicional/sesión propia |
| control_arm | NO VERIFICADO en los dos datasets evaluados | 0 | Dataset adicional/sesión propia |
| side_mirror | MEDIA en DrBimmer | 0 | Auditar publicas + propias |
| filtros restantes | NO VERIFICADO | 0 | Fotos propias y dataset de filtros |

Las etiquetas MEDIA/ALTA son disponibilidad cualitativa de la ficha o de clases conocidas, no conteo de imagenes descargadas. No se realizaron descargas ni conteos locales.

## 14. Fotografias propias necesarias

Prioridad alta: pastillas, discos, calipers, filtros de aceite/aire/combustible/cabina, alternadores, radiador, amortiguadores, brazo de suspension, bujias, bobinas, bomba de agua, kit de embrague, farolas y retrovisores.

Para cada pieza se deben capturar varias marcas, tamanos/modelos, piezas nuevas y usadas, distintos angulos, fondo de tienda/taller, iluminacion natural y artificial, oclusion parcial, mano sosteniendo la pieza, pieza en caja, pieza montada y desmontada. Tambien se requieren fotos negativas de piezas parecidas para medir confusiones.

La fotografia debe conservar el vinculo con `itemCode`, marca, modelo, ano, `oemCode` y `factoryCode` sin convertir esos atributos en etiquetas visuales. No deben fotografiarse placas, rostros ni datos personales.

## 15. Recomendacion Classification vs Detection

La recomendacion es **ambas, en dos etapas**:

1. **Classification primero:** una foto de una pieza aislada, fondo controlado o moderadamente real, devuelve una clase candidata. Es el MVP mas coherente con el dataset Kaggle y permite validar la taxonomia con menos anotacion.
2. **Detection despues:** cuando el usuario fotograf ie varias piezas, una pieza dentro del vehiculo o un entorno desordenado. DrBimmer aporta poligonos de carroceria que pueden convertirse en cajas, pero no cubre el nucleo mecanico del catalogo.

No se debe entrenar YOLO con imagenes de clasificacion sin anotar bounding boxes. La conversion de poligonos a cajas debe conservar una auditoria y las fotos propias deben anotarse directamente en el formato objetivo.

## 16. Proximos pasos

1. Confirmar con el equipo la lista de 8 clases del MVP 1.
2. Revisar licencias y terminos de Kaggle y DrBimmer antes de usar imagenes.
3. Sin descargar aun, preparar una matriz de clases, fuente, licencia, formato y riesgo de duplicado.
4. Obtener una muestra manual pequena solo despues de aprobar la taxonomia y la licencia.
5. Capturar fotos propias vinculadas a `itemCode` y separar train/validation/test por producto, no solo por imagen.
6. Definir si el primer entregable sera clasificacion aislada; dejar detection para una segunda iteracion.
7. Medir balance, calidad y confusiones antes de decidir clases adicionales.
8. Solo despues de completar esos pasos evaluar librerias, entrenamiento y servicio de inferencia.

### Resumen de auditoria

- Productos analizados: **56**.
- Categorias actuales: **7**.
- Tipos de autoparte identificados en el catalogo: **45**; 49 filas incluyendo cuatro clases externas solo comparativas.
- Clases candidatas IA del catalogo: **45**; cuatro clases de comparacion (`battery`, `fuse_box`, `piston`, `radiator_fan`) no pertenecen al catalogo.
- Clases descartadas para el MVP: **13** de las clases del catalogo, por tamano, ambiguedad o baja prioridad; quedan documentadas para reevaluacion.
- MVP recomendado: **8 clases**: `brake_pad`, `brake_rotor`, `brake_caliper`, `alternator`, `oil_filter`, `air_filter`, `radiator`, `headlight`.
- MVP ampliado: **16 clases**, agregando `spark_plug`, `ignition_coil`, `water_pump`, `starter_motor`, `oxygen_sensor`, `shock_absorber`, `control_arm`, `side_mirror`.
- Kaggle aprovechable: `brake_pad`, `brake_rotor`, `brake_caliper`, `alternator`, `ignition_coil`, `headlight`, `oil_filter`, `oxygen_sensor`, `radiator`, `radiator_hose`, `spark_plug`, `starter_motor`, `thermostat`, `water_pump`; licencia y conteos: **NO VERIFICADOS localmente**.
- DrBimmer aprovechable: `front_bumper`, `rear_bumper`, `headlight`, `side_mirror`, `grille`; son poligonos de partes externas, no el nucleo mecanico.
- Fotografias propias: todas las clases MVP, especialmente `air_filter`, `shock_absorber`, `control_arm`, filtros restantes, embrague y piezas pequenas.
- Recomendacion: **Classification primero y Detection despues**.

Este documento no descarga datasets, no entrena modelos y no modifica codigo productivo.
