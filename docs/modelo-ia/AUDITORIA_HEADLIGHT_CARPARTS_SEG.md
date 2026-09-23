# AUDITORIA HEADLIGHT — CARPARTS-SEG

Fecha: 2026-09-22  
Fuente: Ultralytics Carparts-Seg  
Fuente original citada: Roboflow Universe `car-seg` de Gianmarco Russo

## 1. Fuente y licencia

La documentacion oficial es:

```text
https://docs.ultralytics.com/datasets/segment/carparts-seg/
```

La documentacion publica indica licencia **CC BY 4.0**, 3,833 imagenes y 23 clases. El YAML oficial referencia el archivo publicado por Ultralytics:

```text
https://github.com/ultralytics/assets/releases/download/v0.0.0/carparts-seg.zip
```

No se realizo una descarga masiva en esta auditoria.

## 2. Clases e IDs

El YAML real verificado contiene:

| ID | Clase |
|---:|---|
| 12 | front_left_light |
| 13 | front_light |
| 15 | front_right_light |

No se incluyen IDs 4, 5 ni 7 (`back_left_light`, `back_light`, `back_right_light`) porque son luces traseras. La lista completa y los splits del YAML fueron verificados en la fuente oficial.

## 3. Conteos reales

Auditoria local del archivo descargado desde la URL oficial:

| Clase original | ID | Imagenes con clase | Instancias |
|---|---:|---:|---:|
| front_left_light | 12 | 504 | 504 |
| front_light | 13 | 2,057 | 3,088 |
| front_right_light | 15 | 474 | 474 |
| **Union de las tres** | — | **2,699** | **4,066** |

Una imagen puede pertenecer a mas de una clase original, por eso la union no es la suma simple de 504 + 2,057 + 474.

En la union de las tres clases, 1,356 imagenes tienen un faro, 1,331 tienen dos faros y 12 tienen cuatro instancias. En total, **1,343 imagenes** contienen mas de una instancia; esas instancias se conservaran como cajas independientes.

Splits comprobados:

- train: 3,156 imagenes y 3,156 labels.
- val: 401 imagenes y 401 labels.
- test: 276 imagenes y 276 labels.

## 4. Formato y conversion

El dataset usa **Ultralytics instance segmentation**. Cada label contiene el ID seguido de puntos de poligono normalizados. La auditoria comprobo que los labels son parseables y que los tres IDs objetivo aparecen en los archivos.

Conversion propuesta, sin ejecutar masivamente:

```text
xmin = min(x)

cx = (xmin + xmax) / 2
cy = (ymin + ymax) / 2
width = xmax - xmin
height = ymax - ymin
```

Como los puntos ya estan normalizados entre 0 y 1, no se requiere dividir nuevamente por ancho/alto. La clase final para cada poligono es `headlight`, ID 7. Si una imagen contiene dos faros, se generan dos cajas independientes con ID 7.

## 5. Piloto de conversion

Se seleccionaron cinco anotaciones representativas y se generaron previews unicamente en:

```text
ia-service/datasets/headlight_conversion_pilot/
```

El piloto produjo:

- 5 previews.
- 5 poligonos inspeccionados.
- 5 bounding boxes experimentales.
- ID original conservado en el manifiesto.
- ID final experimental: 7.
- 0 conversiones masivas.

Las previews muestran poligonos naranjas y bounding boxes verdes. En los cinco casos observados, la caja contiene completamente el poligono correspondiente. No se modifico RAW ni se incorporo nada a `processed/`.

## 6. Validacion semantica

Las tres clases corresponden a luces delanteras del vehiculo:

- `front_left_light`: faro delantero izquierdo.
- `front_light`: faro delantero frontal.
- `front_right_light`: faro delantero derecho.

Se unifican justificadamente como `headlight` porque representan el mismo tipo comercial de pieza con variantes de posicion. Las clases traseras fueron excluidas.

## 7. Conclusion

Carparts-Seg es una fuente adecuada para construir automaticamente `headlight` sin dibujo manual: tiene licencia CC BY 4.0, anotaciones de segmentacion, estructura verificable, 2,699 imagenes con alguna de las tres clases y 4,066 instancias. La conversion poligono a bounding box es determinista y las cinco pruebas piloto resultaron geometricamente correctas.

## 8. Estado

La fuente queda **APROBADA PARA CONVERSION CONTROLADA**, no para conversion masiva inmediata. Falta conservar atribucion, ejecutar controles completos de etiquetas antes de exportar y revisar muestras adicionales de cada split. No se entreno ni se modifico ningun dataset del proyecto.
