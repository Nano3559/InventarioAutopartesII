# ia-service — RepuestoPro Vision IA

Servicio de visión por computadora de RepuestoPro basado en YOLO11n. Expone la
API que consume el backend Express para reconocer autopartes a partir de
imágenes (detección de la pieza en la foto, usada por la búsqueda por imagen).

## Arquitectura

```text
Frontend React
  -> Backend Express (TypeScript/Prisma)
  -> FastAPI (este servicio, puerto 8000)
  -> YOLO11n V3 (checkpoint versionado en models/)
```

El backend Express no habla con YOLO directamente: llama a los endpoints de
este servicio (`/vision/*`).

## Python recomendado

Python **3.11**. El código y las dependencias están probados contra 3.11.

## Puesta en marcha

Desde la raíz del repositorio, dentro de la carpeta `ia-service`:

```powershell
cd ia-service

# 1. Crear el entorno virtual
python -m venv .venv

# 2. Activarlo (Windows)
.venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt
```

### PyTorch (GPU vs CPU)

`requirements.txt` **no** instala PyTorch a propósito. Al instalar solo con
`requirements.txt` pip baja la rueda CPU de PyPI, que funciona sin GPU.

- Solo CPU: no hace falta nada más.
- Con GPU (recomendado, CUDA 12.1 — es la configuración local):

```powershell
pip install torch==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

No ejecutar `pip install --upgrade torch`: rompería el build CUDA del entorno.

## Modelo oficial V3

- Ubicación versionada: `models/repuestopro_yolo11n_v3_webcam_robust.pt`.
- Es el checkpoint aprobado y en uso (entrenado como
  `repuestopro_yolo11n_v3_webcam_robust`). Se carga por defecto; no hace falta
  descargarlo ni pedirlo por ningún otro medio: está en el repositorio.
- Las 8 clases soportadas:

```text
brake_pad, brake_rotor, brake_caliper, alternator,
oil_filter, air_filter, radiator, headlight
```

## Variables de entorno (prefijo `VISION_`)

| Variable               | Default | Descripción |
|------------------------|---------|-------------|
| `VISION_MODEL_PATH`    | `ia-service/models/repuestopro_yolo11n_v3_webcam_robust.pt` | Ruta al peso YOLO. Si se define, sobrescribe el default. |
| `VISION_DEVICE`        | `0`     | Dispositivo: `"0"` = primera GPU, `"cpu"`, `"cuda:0"`, etc. |
| `VISION_MAX_IMAGE_PIXELS` | `40000000` | Límite de píxeles por imagen (anti image-bomb). |
| `VISION_WARMUP`        | `true`  | Predicción sintética al arrancar para calentar CUDA/Torch. |

Ejemplo con override de modelo:

```powershell
$env:VISION_MODEL_PATH = "<ruta_completa_a_otro_checkpoint>"
$env:VISION_DEVICE = "cpu"
```

El override por entorno siempre tiene prioridad sobre el modelo default.

## Ejecutar FastAPI

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Documentación interactiva de la API en http://localhost:8000/docs.

## Endpoints

- `GET /vision/health` — estado del servicio y del modelo.
- `POST /vision/detect` — detección de autopartes (`multipart/form-data`,
  campo `image`, jpeg/png/webp, máx 5 MB). Devuelve `detecciones[]` con
  `categoria`, `confianza` y `boundingBox` normalizado (0..1).
- `POST /vision/classify` — clasificación auxiliar (la detección de mayor
  confianza como clase).

### Health correcto

```json
{
  "status": "ok",
  "modelLoaded": true,
  "model": "YOLO11n",
  "modelVersion": "repuestopro_yolo11n_v3_webcam_robust",
  "classes": 8,
  "device": "cuda:0"
}
```

Si `modelLoaded` es `false`, revisa que `models/` contenga el .pt o define
`VISION_MODEL_PATH`.

## Tests

```powershell
pytest
```

Esperado: los tests del suite de ia-service pasan (incluye detección,
validación de uploads, health y hardening).

## Conexión con el backend

El backend Express llama a este servicio (p. ej. `http://localhost:8000`)
en las rutas `/vision/*`. No requiere token: la confianza mínima de
producción (`0.55`) la aplica el backend, no este servicio.

## Estructura de carpetas

```text
ia-service/
  app/          Código del servicio (config, routers, schemas, services)
  models/       Checkpoint oficial versionado (V3)
  tests/        Suite de tests + conftest.py
  scripts/      Herramientas de entrenamiento/diagnóstico (requieren datasets locales)
  datasets/     Datasets y manifests (solo locales; NO en Git salvo manifests)
  runs/         Runs de entrenamiento (solo locales; NO en Git)
  artifacts/    Evidencia de diagnósticos (solo local; NO en Git)
  diagnostics/  Pruebas puntuales de inferencia (solo local; NO en Git)
  requirements.txt / Dockerfile / .dockerignore
```

## Qué NO está incluido en Git

`datasets/` (imágenes y etiquetas), `runs/`, `artifacts/`, `diagnostics/`,
`.venv/`, caches y pesos de entrenamiento. Los datasets y los runs son solo
para entrenamiento y evidencia histórica: **no son necesarios para la
inferencia**. Todo lo que el servicio necesita para inferir está en `app/`,
`models/` y las dependencias Python.