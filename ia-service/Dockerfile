# ==========================================================================
# RepuestoPro Vision IA — imagen portable (CPU)
# ==========================================================================
# Estrategia (CV-6 Paso 6):
#
# - Base: python:3.11-slim (misma versión de Python del entorno local).
# - Torch: instalado EXPLICITAMENTE desde el índice CPU de PyTorch
#   (torch==2.5.1+cpu, torchvision==0.20.1+cpu). El venv local de Erika
#   mantiene 2.5.1+cu121; aqui NO se usa ese build ni se toca el venv.
#   Variante GPU futura: cambiar --index-url por https://download.pytorch.org/whl/cu121
#   con la misma torch==2.5.1; la API del servicio no cambia (VISION_DEVICE
#   lo configura). No se crea imagen GPU ahora.
# - OpenCV: se evaluo opencv-python-headless pero se descarto: ultralytics
#   declara opencv-python como dependencia y mantener ambos paquetes en la
#   misma imagen genera conflicto de archivos cv2. Para conservar requirements.txt
#   como fuente unica de dependencias se usa opencv-python + las 2 libs de
#   sistema minimas (libgl1, libglib2.0-0). Receta clasica de ultralytics/Docker.
# - Workers: 1. Cada worker cargaria su propia copia de YOLO en memoria.
# - Modelo: NO se copia en la imagen. Se monta externamente en /models/best.pt
#   (VISION_MODEL_PATH). Sin modelo montado, /vision/health responde 503
#   degradado (correcto).
# ==========================================================================

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/vision \
    VISION_MODEL_PATH=/models/best.pt \
    VISION_DEVICE=cpu \
    VISION_MAX_IMAGE_PIXELS=40000000

WORKDIR /app

# Dependencias del sistema minimas para opencv-python (libGL) + certs HTTPS.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Torch CPU portable (capa pesada, se cachea por separado de requirements).
RUN pip install --no-cache-dir \
        torch==2.5.1 \
        torchvision==0.20.1 \
    --index-url https://download.pytorch.org/whl/cpu

# Dependencias de la app: requirements del proyecto (fuente unica).
# Se copia antes que app/ para aprovechar el cache de capas de Docker.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Usuario no root para runtime (el servicio solo LEE imagenes en memoria y el
# modelo; no guarda uploads ni escribe sobre best.pt).
RUN groupadd --system vision \
    && useradd --system --gid vision --home-dir /home/vision --create-home vision \
    && mkdir -p /models \
    && chown -R vision:vision /models /home/vision

# Codigo de la app (requiere app/ y requirements.txt; el resto queda fuera).
COPY --chown=vision:vision app ./app

USER vision

EXPOSE 8000

# Healthcheck con stdlib (sin curl): GET /vision/health. Con best.pt ausente
# responde 503 degradado -> contenedor marcado unhealthy (esperado y correcto).
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/vision/health', timeout=3).status == 200 else sys.exit(1)"]

# Un solo worker: cada worker cargaria una copia independiente de YOLO.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]