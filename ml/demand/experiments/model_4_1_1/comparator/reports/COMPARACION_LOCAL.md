# Comparación local · Random Forest 4.0.0 y 4.1.1

**GO** para comparar 4.0.0 y D en DEMO. **NO-GO** para una comparación de los tres modelos: la variante C se entrenó por fold durante la investigación y su artefacto no se conservó. El registro de evaluación guarda sus métricas históricas. Estas métricas no se utilizan para fabricar una predicción de C.

## Compatibilidad e integridad

- Se verifica el SHA256 fijado del manifiesto oficial y del registro de evaluación 4.1.1. Sus referencias fijan los hashes de snapshots y artefactos. La deserialización de cada modelo usa los mismos bytes previamente verificados. El cargador también confirma identidad, columnas de entrada, parámetros de Random Forest, orden de preprocesamiento, imputación y codificación.
- El entorno verificado para D es Python 3.11.0, scikit-learn 1.9.1, NumPy 2.4.6, pandas 3.1.0 y joblib 1.6.0. El manifiesto 4.0.0 declara Python 3.11.9 y scikit-learn 1.9.1. Para el modelo oficial se admite la misma versión mayor y menor de Python con scikit-learn exacto. La equivalencia de inferencia se comprobó contra el runtime oficial.
- Los modelos reciben las mismas 19 características del mismo snapshot. D agrega la media, desviación estándar poblacional y fracción de ceros de los tres rezagos mediante la función utilizada en el entrenamiento. Se valida el orden de las columnas y la correspondencia con las ventas de los tres meses previos del historial publicado.
- El comparador aplica la puerta común de rango del release 4.0.0 a ambos estimadores. En los 168 snapshots, 136 quedan dentro de esa puerta y 32 fuera. Esto describe las entradas DEMO y no establece una política de producción para D.
- El modelo oficial conserva SHA256 `8d73bbfb769e432461f2a202e37842b47820a76627e46be3e4ba412e64562e1e`. El candidato D conserva `affafcffd98b4f67cd73416f803b4e062a487850a0465115174007692f52703c`.

## Ejemplos reproducibles

| Snapshot | 4.0.0 | 4.1.1 C | 4.1.1 D | Diferencia D en unidades / porcentaje |
| --- | ---: | --- | ---: | ---: |
| `calendar-2026-53-6-november` · Tensador de Correa, Tienda 2 | 87.1700 | Sin artefacto | 80.0200 | −7.1500 / −8.20 % |
| `calendar-2026-6-5-november` · stock fuera de rango | Abstención | Sin artefacto | Abstención | Sin valor |

La interfaz muestra diferencias absolutas y porcentajes con signo. Con denominador cero o pronóstico ausente, el porcentaje queda nulo. Ningún snapshot publicado de noviembre contiene un observado autorizado. El error individual queda nulo y las diferencias anteriores no clasifican la exactitud ni la calidad de los modelos.

## Verificación

Pasaron siete pruebas focalizadas. Verificaron la carga y la integridad antes de deserializar, los 168 esquemas de snapshots, la transformación de rezagos, el orden común, el determinismo, la equivalencia con el runtime oficial, las abstenciones, los rechazos y las tarjetas mediante AppTest de Streamlit. La prueba de interfaz usó el socket interno de loopback. No se validó visualmente en navegador.

Las huellas antes y después coincidieron para los 554 archivos protegidos y para el artefacto D, su registro de evaluación y la transformación 4.1.1. La corrida no ejecutó entrenamiento, TEST, escrituras operativas ni integraciones de red.
