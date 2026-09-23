# ALTERNATIVAS DE ANOTACION Y CONSTRUCCION DEL DATASET IA

Proyecto: RepuestoPro  
Fecha: 2026-09-22  
Alcance: investigacion documental; no se descargaron datasets nuevos, no se generaron labels masivos y no se entreno.

## 1. Objetivo funcional

El objetivo sigue siendo **object detection** para ocho clases congeladas. YOLO debe devolver clase, confianza y bounding box. La compatibilidad por marca/modelo/ano pertenece al backend y no forma parte de las clases visuales.

Clases finales: `brake_pad`, `brake_rotor`, `brake_caliper`, `alternator`, `oil_filter`, `air_filter`, `radiator`, `headlight`.

## 2. Fuentes ya disponibles

### Car Engine Bay Pictures

`khaledchawa/car-engine-bay-pictures` tiene 1,201 imagenes, labels YOLO, 26 clases y licencia MIT. La auditoria local verifico:

- `air_filter` ID 14: 49 imagenes y 49 boxes.
- `alternator` ID 11: 233 imagenes y 240 boxes.
- `radiator` ID 13: 664 imagenes y 672 boxes.
- `oil_filter` ID 25: 6 imagenes y 6 boxes.

Es una fuente real de detection, pero muestra compartimentos de motor y no necesariamente repuestos aislados. Para RepuestoPro solo se deben conservar las clases objetivo y remapear a IDs 0–7 en copias de trabajo.

### DrBimmer Car Parts

Tiene 998 imagenes de `Car Parts`, poligonos y licencia MIT. `Headlight` existe, pero el conteo especifico de instancias no esta publicado en la metadata revisada. Es convertible a cajas envolventes, pero necesita inspeccion de anotaciones antes de incorporarse.

### Carparts-Seg

Tiene 3,833 imagenes, 23 clases, mascaras de instancia y splits 3,156/401/276. Sus clases de luces son `front_left_light`, `front_light` y `front_right_light`, entre otras. Puede aportar `headlight` mediante conversion de mascara a caja, pero no contiene el resto del nucleo mecanico.

### RAW local de RepuestoPro

El RAW contiene 1,295 imagenes de clasificacion para siete clases y 49 imagenes `air_filter` con boxes reales. Las imagenes sin boxes no deben convertirse a ground truth por asumir que el objeto ocupa toda la imagen. La automatizacion por foreground debe validarse con una prueba pequena.

## 3. Matriz por clase

| Clase | Detection existente | Seg->Box | Imagenes aisladas | Auto-box OpenCV | Pseudo-label | Estrategia |
|---|---|---|---|---|---|---|
| brake_pad | Candidato Roboflow `car-parts` con 50 clases; licencia/conteo exacto NO VERIFICADO | No fuente confirmada | RAW: hasta 198 de clasificacion | Posible si fondo uniforme; requiere piloto | No usar GroundingDINO, ya descartado | Verificar fuente detection; si no, auto-box foreground solo tras prueba |
| brake_rotor | NO VERIFICADO en fuente detection aprobada | NO VERIFICADO | RAW: hasta 186 | Posible en fotos aisladas; requiere piloto | Sin modelo especializado verificado | Probar foreground en muestra; reservar fotos propias |
| brake_caliper | Candidato Roboflow `car-parts` con 50 clases; licencia/conteo exacto NO VERIFICADO | NO VERIFICADO | RAW: hasta 184 | Posible si pieza separada | Sin modelo especializado verificado | Auditar candidato; fallback a auto-box con control de calidad |
| alternator | Car Engine Bay: 233 imagenes/240 boxes | NO VERIFICADO | RAW: hasta 200 | No prioritario | Modelo especializado NO VERIFICADO | Usar Car Engine Bay como base y ampliar con RAW aislado |
| oil_filter | Car Engine Bay: 6 imagenes/6 boxes, insuficiente | NO VERIFICADO | RAW: hasta 179 | Buena candidata si aislada | Sin modelo especializado verificado | Auto-box foreground + fotos propias; no depender de 6 boxes |
| air_filter | Car Engine Bay: 49 imagenes/49 boxes | NO VERIFICADO | RAW: 49 con ground truth | No necesario para estas 49 | No usar GroundingDINO | Conservar las 49 boxes reales; sumar fotos propias despues |
| radiator | Car Engine Bay: 664 imagenes/672 boxes | NO VERIFICADO | RAW: hasta 179 | No prioritario | Modelo especializado NO VERIFICADO | Usar Car Engine Bay, revisar dominio y remapear |
| headlight | NO VERIFICADO como fuente detection aprobada | DrBimmer y Carparts-Seg disponibles | RAW: hasta 169 | Posible si pieza aislada | Modelos Roboflow/GoCaRD no equivalentes al repuesto aislado | Convertir segmentacion despues de auditar; complementar con RAW |

Las cantidades RAW son limites de imagenes de clasificacion disponibles, no cantidades de cajas. La cantidad realmente entrenable depende de que el objeto este aislado y de que el auto-box pase control humano.

## 4. Candidatos detection y segmentacion

### Verificacion del candidato `team-data/car-parts-ybiev`

Fuente consultada: https://universe.roboflow.com/team-data/car-parts-ybiev.

La pagina publica el nombre `car parts`, autor `team data`, tipo `Object Detection`, 1 version y un tamano aproximado de 8.7k imagenes. Un ejemplo publico del workflow lista `ALTERNATOR`, `BRAKE CALIPER` y `BRAKE PAD` entre las clases seleccionables. La ficha completa devolvio acceso restringido durante esta auditoria, por lo que los siguientes campos quedan sin afirmar:

| Campo | Resultado |
|---|---|
| URL | Verificada |
| Fuente original | Roboflow Universe / team data |
| Nombre | `car parts` |
| Tipo | Object Detection |
| Versiones | 1 publicada segun la ficha indexada |
| Total de imagenes | Aproximadamente 8.7k segun la ficha indexada; exacto NO VERIFICADO |
| Lista completa de 50 clases | NO VERIFICADO |
| Conteo por clase | NO VERIFICADO |
| Train/valid/test | NO VERIFICADO |
| Bounding boxes | Object Detection declarado; anotaciones especificas NO VERIFICADAS |
| Formatos exportables de esta version | NO VERIFICADO; Roboflow documenta soporte general YOLO/COCO/VOC |
| Licencia exacta | NO VERIFICADO |
| Descarga local | NO VERIFICADO; no se uso API key ni se descargo |
| Requiere cuenta/API key | NO VERIFICADO para este proyecto |
| Ejemplos visuales y dominio | NO VERIFICADO por acceso restringido |

Cobertura confirmable:

- `brake_pad`: **SI**, aparece en la ficha y workflow publico; cantidad NO VERIFICADA.
- `brake_caliper`: **SI**, aparece en la ficha y workflow publico; cantidad NO VERIFICADA.
- `alternator`: **SI en el ejemplo publico del workflow**, cantidad NO VERIFICADA.
- `brake_rotor`/`brake_disc`: NO VERIFICADO.
- `oil_filter`: NO VERIFICADO.
- `air_filter`: NO VERIFICADO.
- `radiator`: NO VERIFICADO.
- `headlight`: NO VERIFICADO.

No puede aprobarse legalmente: Roboflow indica que la licencia aparece en la seccion "Cite this Project" y que, si no hay licencia, deben asumirse todos los derechos reservados. Como esa licencia no pudo comprobarse, el candidato queda **PENDIENTE_LICENCIA** y no se descarga.

### Car Engine Bay

Es la fuente de detection mas util ya disponible localmente para `alternator`, `radiator` y `air_filter`. Su debilidad es `oil_filter`, con solo seis positivos, y el dominio de compartimento de motor.

### Carparts-Seg y DrBimmer

Ambos son utiles para `headlight` solo despues de revisar poligonos. La conversion seria:

```text
poligono/mask -> xmin, ymin, xmax, ymax -> normalizacion YOLO
```

No se convierte automaticamente en esta etapa. La conversion debe conservar el origen, version, licencia y categoria original.

## 5. Foreground y OpenCV

Para imagenes realmente aisladas, una prueba local puede intentar:

1. estimar el fondo mediante color/contraste;
2. aplicar threshold o segmentacion foreground/background;
3. eliminar componentes pequenos;
4. seleccionar el componente principal;
5. calcular `boundingRect`;
6. rechazar resultados que cubran casi toda la imagen, tengan area pequena o multiples componentes ambiguos;
7. guardar la propuesta como pendiente de validacion.

Esto no debe ejecutarse masivamente sin una prueba piloto. Fondo blanco, sombras, cajas, piezas oscuras y fotos con varios objetos pueden producir cajas incorrectas. La caja resultante es una **preanotacion**, no ground truth automatico.

## 6. Modelos preentrenados

- GroundingDINO Tiny fue probado en el piloto y descartado para escalar por cajas casi de imagen completa, muchos casos `NEEDS_MANUAL` e IoU `air_filter` promedio de 0.3959.
- El candidato Roboflow `car-parts` anuncia un modelo, pero su checkpoint descargable, licencia y correspondencia exacta con las ocho clases no estan verificados.
- GoCaRD publica pesos para 29 regiones interiores/exteriores de vehiculos en contexto natural, pero no es un detector de repuestos del catalogo MVP y sus clases no corresponden directamente al nucleo mecanico.
- Carparts-Seg documenta modelos/entrenamiento de segmentacion, pero no ofrece un checkpoint especializado verificado para las ocho clases de RepuestoPro.

No hay actualmente un modelo preentrenado especializado y verificado que cubra de forma confiable las ocho clases MVP. No se recomienda depender de pseudo-labeling generalista.

## 7. Estrategia mas rapida sin anotacion manual masiva

### Fase A: reutilizar detection real

1. Mantener las 49 cajas reales de `air_filter`.
2. Reutilizar `alternator` y `radiator` de Car Engine Bay despues de remapear y revisar una muestra.
3. Buscar/validar una fuente detection para `brake_pad` y `brake_caliper` antes de descargarla.
4. No confiar en las seis cajas de `oil_filter` como cobertura suficiente.

### Fase B: conversion de segmentacion

Auditar DrBimmer y Carparts-Seg para `headlight`; convertir poligonos a cajas solo despues de confirmar clases y licencia. Esto puede aportar detection sin dibujar manualmente, pero exige una inspeccion automatica de cada anotacion convertida.

### Fase C: auto-box de imagenes aisladas

Aplicar OpenCV solamente a una muestra del RAW por clase. Si la tasa de cajas validas es alta, extenderlo al resto de esa clase; si no, no convertir toda la fuente. Las propuestas deben conservar `needs_review` y no entrar como ground truth sin control.

### Fase D: evaluacion realista

Separar una pequena prueba de camara con fondos, orientaciones, escalas, manos y objetos alrededor. No usar solo imagenes limpias de producto para declarar que el detector funciona en webcam.

## 8. Estimacion de imagenes aprovechables sin dibujar manualmente

| Clase | Base detection/segmentacion verificable | RAW aislado potencial | Estimacion responsable |
|---|---:|---:|---|
| brake_pad | 0 verificado | Hasta 198 | NO VERIFICADO hasta probar auto-box |
| brake_rotor | 0 verificado | Hasta 186 | NO VERIFICADO hasta probar auto-box |
| brake_caliper | 0 verificado | Hasta 184 | NO VERIFICADO; candidato Roboflow pendiente |
| alternator | 233 imagenes | Hasta 200 adicionales | 233 base; ampliar solo tras revisar dominio |
| oil_filter | 6 imagenes | Hasta 179 | 6 base; auto-box pendiente |
| air_filter | 49 imagenes | 49 con boxes | 49 verificadas |
| radiator | 664 imagenes | Hasta 179 adicionales | 664 base; revisar sesgo de compartimento |
| headlight | Conteo por clase NO VERIFICADO | Hasta 169 | NO VERIFICADO hasta auditar segmentacion |

Los limites RAW no son promesas de cajas. No se autoriza crear un dataset de entrenamiento con estas cifras hasta verificar cada caja o propuesta.

## 9. Decision

La ruta mas rapida no es completar las 700 imagenes PENDING. Es construir un primer conjunto de deteccion con:

- 49 `air_filter` reales;
- `alternator` y `radiator` de Car Engine Bay, con control de dominio;
- `headlight` desde segmentacion auditada si los conteos y licencias lo permiten;
- candidatos detection de `brake_pad`/`brake_caliper` solo despues de verificar licencia y descarga;
- auto-box OpenCV unicamente para imagenes aisladas que superen un piloto de calidad;
- fotos propias realistas para validar camara, aunque no sean cientos.

Esta ruta conserva object detection, evita anotacion manual masiva y evita confiar en GroundingDINO. No se descargaron nuevas fuentes, no se generaron labels masivos y no se entreno.

## 10. Siguiente investigacion

La siguiente accion recomendada es verificar desde la interfaz/API oficial de Roboflow la licencia, version, clases completas, conteos, formato y condiciones de descarga del candidato `team-data/car-parts-ybiev`, sin descargarlo. Si no aparece una licencia compatible, descartarlo y no usar sus cajas.

## Cierre de la clase headlight

Se compararon las dos fuentes ya identificadas sin descargar imagenes ni anotaciones.

| Criterio | DrBimmer Car Parts | Ultralytics Carparts-Seg |
|---|---|---|
| Licencia | MIT | CC BY 4.0 |
| Total de imagenes | 998 Car Parts | 3,833 |
| Clase headlight | `Headlight` directa | `front_left_light`, `front_light`, `front_right_light` |
| Instancias headlight | NO VERIFICADO | 4,066 en las tres clases |
| Formato | Poligonos compatibles COCO/VIA/VGG | Instance segmentation, YAML Ultralytics |
| Splits | NO VERIFICADO | train 3,156, val 401, test 276 |
| Conversion | Poligono a caja | Mascara/poligono a caja |
| Complejidad semantica | Menor: clase directa | Mayor: unir tres clases delanteras |
| Trazabilidad publica | Metadata parcial; conteo Headlight no publicado | YAML, splits, clases e instrucciones publicas |

### Fuente seleccionada

Se selecciona **Ultralytics Carparts-Seg** como fuente principal para cerrar `headlight`, condicionada a una inspeccion de los archivos de anotacion antes de descargar. Aunque requiere unificar `front_left_light`, `front_light` y `front_right_light`, tiene licencia clara, estructura, splits y formato documentados publicamente. DrBimmer queda como fuente secundaria porque su clase es semanticamente directa, pero no expone el conteo de Headlight ni una estructura de anotaciones suficientemente verificable en la auditoria actual.

### Justificacion semantica

Las tres clases de Carparts-Seg representan luces delanteras izquierda, frontal y derecha. Se pueden mapear a la clase RepuestoPro `headlight` porque son variantes posicionales del mismo tipo de pieza visual. No se debe incluir `back_light`, `back_left_light` ni `back_right_light`, ya que corresponden a luces traseras.

### Procedimiento de conversion propuesto

Para cada instancia de las clases 12, 13 y 15 del YAML de Carparts-Seg:

1. leer los puntos de la mascara/poligono;
2. calcular `xmin=min(x)`, `ymin=min(y)`, `xmax=max(x)`, `ymax=max(y)` en pixeles;
3. recortar los limites al ancho y alto de la imagen;
4. calcular `cx=(xmin+xmax)/(2*W)` y `cy=(ymin+ymax)/(2*H)`;
5. calcular `bw=(xmax-xmin)/W` y `bh=(ymax-ymin)/H`;
6. escribir la clase remapeada a `headlight` ID 7 y las cuatro coordenadas YOLO normalizadas.

Si una imagen contiene dos faros delanteros, se conservan dos cajas con ID 7. No se convierten aun los archivos ni se unifican labels.

### Resultado

- Fuente principal seleccionada: **Carparts-Seg**.
- Cantidad exacta de imagenes que contienen las tres clases de luces: **2,699**.
- Cantidad exacta de instancias: **4,066**.
- Conversion automatica a YOLO: **tecnicamente posible**, pendiente de inspeccion y licencia/atribucion conservada.
- Descarga y conversion: **no ejecutadas**.

La clase `headlight` puede cerrarse tecnicamente con esta fuente sin dibujo manual, pero todavia no esta lista para descarga masiva: primero debe verificarse el manifiesto de anotaciones y el conteo real de las clases 12/13/15.

## Busqueda dirigida de clases faltantes

Esta busqueda se realizo sin descargar datasets, imagenes ni anotaciones. Se priorizaron fuentes con alguna evidencia publica de deteccion o segmentacion y se marcaron como `PENDIENTE` cuando licencia, conteo o acceso no pudieron verificarse.

| Fuente | Clase nuestra | Clase original | Tipo anotacion | Cantidad | Licencia | Convertible YOLO | Estado |
|---|---|---|---|---:|---|---|---|
| Hugging Face `ybli/yolo-car-brake-pad-flaw-detection` | brake_pad | 7 clases especificas de brake lining | YOLO/Object Detection declarado | NO VERIFICADO | NO VERIFICADA | SI, tecnicamente | DESCARTADO |
| Roboflow `xbkaishui/brake_disc_v2` | brake_rotor | Clases `hl`, `ps`, `sk` | Object Detection declarado | NO VERIFICADO | NO VERIFICADA | SI, tecnicamente | PENDIENTE |
| Paper brake disc defect detection | brake_rotor | defectos de disco, no rotor como pieza | YOLO/Object Detection descrito | 800 fotos propias del estudio | CC BY-NC-ND 4.0 para el articulo; dataset NO VERIFICADO | NO confirmado para datos | DESCARTADO |
| Roboflow `team-data/car-parts-ybiev` | brake_caliper | BRAKE CALIPER | Object Detection declarado | aprox. 8.7k total, clase NO VERIFICADA | NO VERIFICADA | NO se autoriza aun | DESCARTADO_TEMPORAL |
| Car Engine Bay Pictures | oil_filter | ID 25 Oil Filter | YOLO/Object Detection | 6 imagenes, 6 boxes | MIT | SI | APROBABLE |
| DrBimmer Car Parts | headlight | Headlight | Poligonos | total Car Parts 998; clase NO VERIFICADA | MIT | SI, por caja envolvente | PENDIENTE |
| Ultralytics Carparts-Seg | headlight | front_left_light/front_light/front_right_light | Segmentacion de instancia | 3,833 total; por clase NO VERIFICADO | CC BY 4.0 | SI, despues de conversion | APROBABLE |

### Observaciones por clase

#### brake_pad

La fuente Hugging Face encontrada es un dataset de defectos con siete subclases de revestimiento (`Brake-Lining...`) y no una clase comercial unica `brake_pad`. La licencia y los conteos no fueron verificables en la ficha consultada. No se aprueba.

#### brake_rotor

`brake_disc_v2` anuncia object detection, pero la ficha publica no expone licencia, cantidades ni semantica suficiente para confirmar que sus clases sean discos de freno completos. Queda pendiente, no aprobable.

#### brake_caliper

El candidato Roboflow `team-data/car-parts-ybiev` anuncia `BRAKE CALIPER`, pero su licencia y conteo por clase siguen sin verificarse. Se mantiene descartado temporalmente por la politica del proyecto.

#### oil_filter

La mejor fuente verificable sigue siendo Car Engine Bay, con solo 6 positivos y 6 boxes. Es util como semilla, pero insuficiente como fuente unica. No se encontro otra fuente con licencia y anotaciones confirmadas.

#### headlight

DrBimmer tiene la clase semantica `Headlight` directa y licencia MIT, pero no publica conteo por clase. Carparts-Seg tiene licencia CC BY 4.0, YAML y mascaras verificables, aunque separa las luces delanteras por lado/clase. DrBimmer es semanticalmente mas sencillo; Carparts-Seg tiene mejor trazabilidad tecnica de formato. Ambos requieren inspeccion antes de convertir.

### Resultado de la busqueda

No se encontro una fuente nueva, simultaneamente verificable en licencia, cantidad y anotaciones, que cierre `brake_pad`, `brake_rotor` o `brake_caliper` sin anotacion manual. Tampoco se encontro una fuente suficiente para `oil_filter`; sus 6 boxes de Car Engine Bay son aprovechables pero no equilibran la clase.

La ruta sin anotacion manual queda condicionada a obtener primero fuentes con licencia clara o a aceptar una fuente `PENDIENTE` despues de una verificacion directa de su metadata. No se descargaron datos ni se generaron labels.

## Ultima busqueda de clases faltantes

Fecha: 2026-09-22. Esta fue la ultima ronda documental para `brake_pad`, `brake_rotor`, `brake_caliper` y `oil_filter`. No se descargaron datasets ni anotaciones.

| Fuente | Clase nuestra | Clase original | Tipo | Imagenes/instancias | Licencia | Formato | Estado |
|---|---|---|---|---:|---|---|---|
| Hugging Face `ybli/yolo-car-brake-pad-flaw-detection` | brake_pad | 7 subclases de brake lining y `Lubang` | Object Detection/YOLO declarado | NO VERIFICADO | NO VERIFICADA | YOLO declarado | DESCARTADO |
| Roboflow `xbkaishui/brake_disc_v2` | brake_rotor | `hl`, `ps`, `sk` | Object Detection declarado | NO VERIFICADO | NO VERIFICADA | NO VERIFICADO | PENDIENTE |
| Roboflow `team-data/car-parts-ybiev` | brake_pad / brake_caliper | `BRAKE PAD` / `BRAKE CALIPER` | Object Detection declarado | 8.7k total; por clase NO VERIFICADO | NO VERIFICADA | NO VERIFICADO | DESCARTADO |
| Car Engine Bay Pictures | oil_filter | ID 25 `Oil Filter` | Object Detection YOLO | 6 imagenes / 6 boxes | MIT | YOLO | APROBABLE |
| Roboflow `car-parts-detection-owvwe` | brake_pad / brake_caliper | NO VERIFICADO | Object Detection | 6,345 total; por clase NO VERIFICADO | NO VERIFICADA | NO VERIFICADO | PENDIENTE |
| Roboflow `ajay-k4fpo/oil-detection-sda8o` | oil_filter | `oil`, semantica exacta NO VERIFICADA | Object Detection | 170 total | NO VERIFICADA | YOLO segun ficha | DESCARTADO |

### brake_pad

No se encontro una fuente aprobable. El dataset de Hugging Face trata defectos/subtipos de revestimiento y no demuestra una clase unica de pieza comercial; su licencia tampoco esta verificada. Los candidatos Roboflow con `BRAKE PAD` siguen bloqueados por licencia y conteos.

**MEJOR OPCION:** ninguna aprobada. Estado: **BLOQUEADA POR FUENTE LEGAL/ANOTACION**.

### brake_rotor

`brake_disc_v2` anuncia object detection, pero no expone licencia, clases semanticas completas ni cantidades verificables. Los papers encontrados describen datasets propios o defectos superficiales del disco, no una fuente reutilizable de la pieza `brake_rotor` con licencia clara.

**MEJOR OPCION:** `brake_disc_v2` solo como candidato pendiente, no aprobable. Estado: **BLOQUEADA**.

### brake_caliper

El candidato con clase directa sigue siendo `team-data/car-parts-ybiev`, pero su licencia y conteos no fueron verificables. Los trabajos academicos encontrados tratan inspeccion de defectos o contextos industriales especificos y no publican una fuente reutilizable con licencia clara y boxes de caliper comercial.

**MEJOR OPCION:** ninguna aprobada. Estado: **BLOQUEADA POR LICENCIA**.

### oil_filter

La mejor fuente sigue siendo `khaledchawa/car-engine-bay-pictures`, MIT, con 6 imagenes y 6 boxes. Es legal y util como semilla, pero insuficiente para una clase equilibrada. El candidato Roboflow de aceite no demuestra que detecte filtros automotrices ni ofrece licencia verificable.

**MEJOR OPCION:** Car Engine Bay, 6 boxes reales. Estado: **APROBABLE, PERO INSUFICIENTE**.

### Decision final

No se encontro una fuente nueva que cierre `brake_pad`, `brake_rotor` o `brake_caliper` con licencia y anotaciones verificables. La investigacion documental de estas clases queda cerrada por ahora.

Sin dibujar cajas manualmente, RepuestoPro ya puede construir legalmente material anotado para **4 clases con cobertura util**: `alternator`, `air_filter`, `radiator` y `headlight`. `oil_filter` tiene material legal pero solo 6 instancias, por lo que puede considerarse una quinta clase disponible de forma limitada, no una clase equilibrada.

No existe material suficiente y aprobado para construir un baseline completo de las ocho clases. Permanecen bloqueadas `brake_pad`, `brake_rotor` y `brake_caliper`; `oil_filter` permanece con cobertura insuficiente.
