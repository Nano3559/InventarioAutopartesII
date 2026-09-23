# CV-6 — Servicio de inferencia FastAPI para RepuestoPro

## 1. Objetivo

Se implementó un **microservicio independiente** (`ia-service/`) que expone el
modelo YOLO11n entrenado en [CV-4](CV4_ENTRENAMIENTO_YOLO_BASELINE.md) y
evaluado en [CV-5](CV5_EVALUACION_MODELO_YOLO.md) a través de una API HTTP.

El servicio separa la carga del modelo de la aplicación principal: el backend
de RepuestoPro (responsabilidad de Ross) consumirá este servicio por red en
CV-7 (`VISION_MODE=http`). En CV-6 el servicio se desarrolló, endureció y
preparó para despliegue (Docker), pero **no se integró** todavía.

No se reentrenó el modelo en CV-6: se sirve `best.pt` del baseline sin cambios.

## 2. Arquitectura

Flujo de una petición de detección:

```
Cliente / backend
    ↓ POST /vision/detect  (multipart, campo "image")
FastAPI (router)
    ↓ validación: MIME, tamaño acotado, píxeles
OpenCV (cv2.imdecode, en memoria)
    ↓ array BGR
YOLO11n best.pt (ultralytics, instancia única)
    ↓ boxes xyxy + cls + conf (píxeles)
Postprocesamiento (normalización 0..1, fail-safes, orden)
    ↓ categoria / confianza / boundingBox
JSON (contracto establecido)
```

Aspectos clave:

- El modelo se carga **una sola vez** por proceso (lifespan de FastAPI +
  singleton en `app/services/inference.py`). El contador interno
  (`estado.cargas`) debe permanecer en `1`.
- No hay estado por petición: las imágenes se procesan en memoria y no se
  guardan en disco.

## 3. Tecnologías

| Tecnología | Uso |
| --- | --- |
| Python 3.11 | Runtime |
| FastAPI | API y validación de contratos (Pydantic) |
| Uvicorn | Servidor ASGI |
| Pydantic / pydantic-settings | Schemas y configuración por entorno |
| OpenCV (opencv-python) | Decodificación de imágenes |
| Ultralytics YOLO (YOLO11n) | Inferencia de detección |
| PyTorch | Motor de deep learning (CUDA local; CPU en contenedor) |
| Dockerfile | Preparación de imagen de despliegue |

## 4. Modelo utilizado

- Arquitectura: **YOLO11n** (nan).
- Peso: `runs/detect/repuestopro_yolo11n_baseline_v1/weights/best.pt`
  (no versionado; externo al contenedor).
- Entrenado en CV-4, evaluado en CV-5. **Sin reentrenamiento en CV-6.**
- 8 clases con orden fijo:

| índice | clase YOLO |
| --- | --- |
| 0 | brake_pad |
| 1 | brake_rotor |
| 2 | brake_caliper |
| 3 | alternator |
| 4 | oil_filter |
| 5 | air_filter |
| 6 | radiator |
| 7 | headlight |

## 5. Endpoints

### GET `/vision/health`

Estado del servicio y del modelo. No expone paths sensibles.

```json
{ "status": "ok", "modelLoaded": true, "model": "YOLO11n", "classes": 8, "device": "cuda:0" }
```

Sin modelo cargado responde `503` con `modelLoaded: false` y la causa técnica.

### POST `/vision/detect`

**Endpoint de integración con el backend de Ross.** Multipart, campo
`image` (jpeg/png/webp, máx 5 MB). Respuesta:

```json
{
  "detecciones": [
    {
      "categoria": "filtro de aire",
      "confianza": 0.9703167080879211,
      "boundingBox": { "x": 0.347335, "y": 0.123911, "width": 0.288413, "height": 0.236501 }
    }
  ],
  "consultadoEn": "2026-09-23T00:54:11.960418Z"
}
```

- `detecciones[]` ordenadas por `confianza` descendente.
- `boundingBox` normalizado en `0..1`.
- Sin detecciones válidas: `200` con `detecciones: []`.

### POST `/vision/classify`

**Endpoint auxiliar del servicio IA**, actualmente **no consumido por el
backend**. Devuelve la detección de mayor confianza como una clase:

```json
{ "clasificacion": { "categoria": "filtro de aire", "confianza": 0.9703167080879211 }, "consultadoEn": "..." }
```

Sin detecciones: `200` con `clasificacion: null`.

## 6. Validación de imágenes

| Caso | Resultado |
| --- | --- |
| MIME no permitido (no jpeg/png/webp) | `415 formato_no_soportado` |
| Archivo vacío | `400 archivo_vacio` |
| Supera 5 MB | `413 archivo_demasiado_grande` |
| Bytes corruptos / imagen no decodificable | `400 imagen_corrupta` |
| Dimensiones exceden 40 MP | `400 dimensiones_invalidas` |
| Campo ausente / FastAPI validation | `422` |

Detalles:

- La decodificación se hace con **OpenCV** (`cv2.imdecode`) sobre los bytes en
  memoria; no se confía en la extensión del archivo.
- OpenCV 5.0.0 aplica la orientación EXIF automáticamente; no se requiere
  corrección manual.
- Anti image-bomb: límite configurable `VISION_MAX_IMAGE_PIXELS`
  (default 40 MP) antes de reservar memoria para la inferencia.

## 7. Inferencia

- `imgsz=640`.
- `conf=0.25` (`CONF_TECNICO_INFERENCIA`): umbral técnico para que YOLO
  emita candidatos.

**Importante:** `0.25` **no es la política definitiva de negocio**. Filtro de
producción independiente: `VISION_CONFIDENCE_MIN` (default 0.55) vive en el
backend / CV-8 (pertenece a Ross y a la fase de catálogo, no al servicio IA).
En CV-6 no se aplica ningún umbral de negocio; el servicio devuelve candidatos
técnicos por debajo de la política comercial y el backend decide.

## 8. Mapeo de clases

| clase YOLO | categoría backend |
| --- | --- |
| brake_pad | pastilla de freno |
| brake_rotor | disco de freno |
| brake_caliper | caliper |
| alternator | alternador |
| oil_filter | filtro de aceite |
| air_filter | filtro de aire |
| radiator | radiador |
| headlight | faro |

El mapeo es fijo y no inventa categorías: una clase no esperada provoca
descarte fail-safe de esa detección.

## 9. Bounding boxes

YOLO entrega coordenadas de píxeles `xyxy`. La API entrega esquina superior
izquierda más ancho/alto, normalizado al tamaño de la imagen:

```
ancho  = x2 - x1
alto   = y2 - y1
x      = x1 / W        width  = ancho / W
y      = y1 / H        height = alto / H
```

Se garantiza numéricamente `x + width <= 1` y `y + height <= 1`. Las
coordenadas o confianzas no finitas (NaN/Inf) se descartan.

## 10. Manejo de errores

| Status | Significado |
| --- | --- |
| `400` | archivo vacío, corrupto o dimensiones inválidas |
| `413` | archivo demasiado grande (> 5 MB) |
| `415` | formato no soportado |
| `422` | campo `image` ausente o inválido |
| `503` | modelo no disponible / error de inferencia |

- Los errores internos se registran con `logger.exception` en el servidor y el
  cliente recibe un `detail` estable, **sin tracebacks ni paths**.
- Sin detecciones no es error: `200` con lista vacía (o `null` en classify).

## 11. Concurrencia y rendimiento

- El endpoint ejecuta la inferencia con `run_in_threadpool` (Starlette): la
  operación síncrona pesada `model.predict()` no bloquea el event loop.
- El acceso a la instancia YOLO compartida se serializa con un
  `threading.Lock` (`_lock_inferencia`).
- Recomendado: **1 worker** (cada worker cargaría una copia independiente de
  YOLO). El Dockerfile fija `--workers 1`.
- Prueba básica concurrente (5 requests simultáneos a detect y classify):
  respuestas `200` estables, contrato válido, una única carga de modelo.
  **No se presentan los tiempos como benchmark científico.**

## 12. Seguridad y robustez

- Lectura acotada `read(5MB + 1)`: un archivo descomunal no se carga entero.
- Límite de 40 MP anti image-bomb.
- Sin persistencia de uploads en disco.
- Sin tracebacks ni paths absolutos en respuestas al cliente.
- Fail-safes de robustez: bbox NaN/Inf descartados; confianza NaN/Inf o fuera
  de `[0,1]` descartada; `class_id` debe ser **número finito que represente
  exactamente un entero en 0..7** (los fraccionarios jamás se truncan); clase
  fuera de las 8 esperadas → descarte.
- El modelo no vive en el contenedor: se monta externamente
  (`VISION_MODEL_PATH`). Sin modelo montado, health degradado `503` (correcto).

## 13. Tests

Suite unitaria (pytest, `ia-service/tests/`) — **66 tests**:

| Grupo | Cantidad |
| --- | --- |
| health | 4 |
| detect | 30 |
| classify | 20 |
| hardening | 12 |
| **total** | **66** |

Resultado: **66 passed, 0 failed**. Adicionalmente se ejecutaron pruebas reales
con uvicorn: secuencial (health → detect → classify → detect → classify →
health), concurrente (5 requests a detect y a classify, estabilidad y contrato),
confirmando carga única del modelo (`cargas == 1`) y 0 procesos residuales.

## 14. Docker

- Imagen base: `python:3.11-slim`.
- CPU por defecto (portable): `torch==2.5.1` + `torchvision==0.20.1` desde el
  índice CPU de PyTorch. `VISION_DEVICE` configura el dispositivo en runtime
  (por ejemplo `cpu` o `0`); no se hardcodea `cuda:0`.
- Modelo externo: esperado en `/models/best.pt` (`VISION_MODEL_PATH`); el
  Dockerfile **no copia** pesos ni dataset.
- Usuario runtime no-root (`vision`), HOME configurado, `/models` legible.
- `HEALTHCHECK` con stdlib (urllib → GET `/vision/health`), sin depender de
  curl.
- `--workers 1`, sin `--reload`, `EXPOSE 8000`, escucha `0.0.0.0:8000`.
- `.dockerignore` protege el contexto: datasets, runs, weights, `.venv`,
  `.annotation-venv`, `.env`/tokens/credenciales Kaggle, caches, tests y docs
  quedan fuera; `app/` y `requirements.txt` se conservan.

> **Validación:** El Dockerfile fue **validado estáticamente**. No se ejecutó
> `docker build` ni `docker run` en el entorno local debido a que **Docker no se
> encuentra instalado**. Aún no se puede afirmar que la imagen Docker funciona
> experimentalmente; requiere validación build/run en una máquina con Docker
> antes del despliegue real.

## 15. Variables de entorno

| Variable | default local | default contenedor | Descripción |
| --- | --- | --- | --- |
| `VISION_MODEL_PATH` | `runs/.../best.pt` (pathlib) | `/models/best.pt` | Peso YOLO; no rompe el flujo local |
| `VISION_DEVICE` | `"0"` | `cpu` | GPU local (cuda:0) o CPU portable |
| `VISION_MAX_IMAGE_PIXELS` | `40000000` | `40000000` | Límite anti image-bomb |

No se almacenan secretos en la configuración.

## 16. Integración futura

CV-7 conectará el backend (Ross) mediante `VISION_MODE=http` y
`VISION_IA_URL`, apuntando a `POST /vision/detect`. El backend ya resuelve el
path `{url}/vision/detect`, envía el campo `image` y valida el contrato
`detecciones[]/categoria/confianza/boundingBox/consultadoEn`. **El servicio
aún no está integrado.**

## 17. Limitaciones

- El modelo hereda las limitaciones de CV-5 (métricas de detección del baseline).
- `brake_pad`, `brake_rotor`, `brake_caliper`: sin ground truth real en TEST
  (validación limitada).
- `oil_filter`: la muestra real es muy pequeña.
- `air_filter`: limitada en el conjunto real.
- `radiator`: desempeño menor que el resto.
- Umbral de producción (`VISION_CONFIDENCE_MIN`) pendiente de CV-8/backend.
- Docker build/run pendiente de validación en un entorno con Docker.
- Se recomienda una sola instancia/worker (cada worker duplicaría YOLO).

## 18. Estado final

El servicio de inferencia de CV-6 está **funcional, endurecido y documentado**:
contratos estables, 66 tests pasando, smoke real verificado (carga única y sin
procesos residuales) y Dockerfile preparado con validación estática. El modelo
no es "perfecto": CV-7 deberá integrarlo con el backend y CV-8 podrá re-evaluar
políticas de confianza de producción. El servicio está listo para iniciar la
integración con el backend en CV-7.