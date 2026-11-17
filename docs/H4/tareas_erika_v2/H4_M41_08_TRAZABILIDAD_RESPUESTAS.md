# M41-08 · Trazabilidad de respuestas de escenarios

M41-07 verificó que una respuesta previa a M41-06 puede recuperarse íntegra. Su versión de modelo, política y contrato pueden coincidir con las de una respuesta recién calculada. La procedencia de la entrega y la revisión del código son datos distintos.

## API

En un `200` de `POST /api/predictions/scenarios/preview`, el cuerpo conserva el esquema cerrado `demand-scenarios-1.0.0`. Las dos cabeceras se exponen a JavaScript para los orígenes permitidos por el CORS existente.

| Dato | Origen | Interpretación |
| --- | --- | --- |
| Identificador de escenario | `data.scenarioId` | Identificador derivado de la solicitud. Puede coincidir si se vuelve a calcular la misma entrada. |
| Fecha original | `data.recordedAt` | Fecha de generación del cuerpo. Se conserva al recuperar la respuesta. |
| Huella de entrada | `data.scenarioInputSha256` | SHA256 de la entrada que utilizó el runtime. Conservar el valor recibido. |
| Modelo | `data.modelVersion`, `data.artifactSha256` | Identidad del artefacto predictivo. |
| Entrega | `X-Scenario-Delivery` | `computed` al publicar la respuesta calculada para la petición. `replayed` al devolver una publicación previa, incluso si otra petición concurrente acaba de publicarla. |
| Revisión | `X-Scenario-Runtime-Revision` | `sha256:<64 hex minúsculas>` si consta en el registro. `unknown` si el registro carece de una revisión válida. |

La revisión corresponde a los archivos fuente locales de la ejecución Python. En este orden, se calcula el SHA256 binario de `admin_scenarios.py`, `v2/__init__.py`, `v2/calendar2026.py`, `v2/calendar2026_runtime.py`, `v2/scenario_data.py` y `v2/scenario_runtime.py`, con rutas relativas a `ml/demand`. Se serializa el arreglo de pares `[ruta, sha256]` con `JSON.stringify` y se calcula el SHA256 sobre ese JSON UTF-8. El backend comprueba que el manifiesto de fuentes coincida antes y después de ejecutar Python. La huella identifica esas fuentes y queda fuera de su alcance el inventario de dependencias, el intérprete y la configuración de despliegue. Publicar el código en un directorio estable durante la inferencia evita mezclar revisiones.

El archivo de caché nuevo agrega `runtimeRevision` al lado de `input` y `response`. La clave, el hash canónico del cuerpo, la publicación exclusiva y el 409 conservan su semántica. La lectura devuelve los registros históricos sin migrarlos. La revisión de una recuperación procede del archivo guardado. Los errores conservan el sobre vigente.

## Integración para Ross

1. Validar el cuerpo con `checkedScenario` como hasta ahora. Leer las cabeceras de la misma respuesta Axios (`res.headers["x-scenario-delivery"]` y `res.headers["x-scenario-runtime-revision"]`) y conservar los metadatos con el resultado validado.
2. Mostrar **Calculada** o **Recuperada** según la cabecera. Si está ausente o contiene un valor inesperado, mostrar **Procedencia desconocida**. Mostrar la fecha original en ambos casos. No derivar la entrega a partir de la antigüedad.
3. Mostrar **Revisión desconocida** para `unknown`, cabecera ausente o valor inválido. El hash de revisión y la versión de modelo tienen etiquetas distintas.
4. En el export de evidencia, conservar el resultado existente y añadir un objeto `provenance` con `scenarioId`, `recordedAt`, `scenarioInputSha256`, `delivery`, `runtimeRevision` y `modelVersion`. Usar `delivery: "unknown"` y `runtimeRevision: null` cuando corresponda. El estado de entrega describe la petición que produjo la vista exportada. Mantener completos el hash y la fecha originales en el archivo.
5. Si el navegador no puede leer una cabecera por un proxy o despliegue anterior, mantener visible el resultado y presentar el dato de procedencia afectado como desconocido. En el ensayo visual, comprobar un envío, una repetición, una recuperación histórica y su exportación.

## Verificación

Desde `backend`, `npx --no-install tsc --noEmit` terminó sin errores. `node -r ts-node/register --test src/modules/predictions/scenarios.http.test.ts` aprobó 37 casos y subcasos con sesiones y caché simuladas. La prueba de recuperación tras reinicio crea una segunda instancia del servicio sobre la misma caché de prueba y falla si esta vuelve a ejecutar el runtime. El consumidor frontend vigente aceptó el cuerpo y el caso DEMO conservó el pronóstico de 87.17 unidades.

La comprobación binaria antes y después cubrió 554 archivos en `ml/demand/data`, `models`, `reports` y `v2/contracts`. La huella agregada fue `4d5098398a45d8c3879ba08aad7dbc08c3c7696740a5cbbb6fa5e7268991fc27`. El modelo conservó el SHA256 `8d73bbfb769e432461f2a202e37842b47820a76627e46be3e4ba412e64562e1e`.
