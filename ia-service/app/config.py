"""Configuración del servicio de visión RepuestoPro.

Variables de entorno (prefijo VISION_):

- VISION_MODEL_PATH: ruta al peso YOLO. Por defecto apunta al checkpoint
  oficial versionado V3
  (ia-service/models/repuestopro_yolo11n_v3_webcam_robust.pt), resuelto a
  partir de la ubicacion real del proyecto (pathlib), sin depender del
  working directory de uvicorn ni de rutas personales.
- VISION_DEVICE: dispositivo de inferencia ("0" para la primera GPU, "cpu",
  "cuda:0", etc.). Por defecto "0".
- VISION_MAX_IMAGE_PIXELS: límite técnico de píxeles de una imagen decodificada
  (anti image-bomb). Valor por defecto 40_000_000 (~40 MP): amplio para fotos
  normales de celular (típico 8-50 MP) y suficientemente bajo para evitar
  reservas de memoria absurdas por imágenes comprimidas con dimensiones enormes.
- VISION_WARMUP: si se ejecuta una predicción sintética al arrancar (lifespan)
  para absorber la inicialización de Torch/CUDA antes de aceptar tráfico. El
  primer predict() en frío puede tardar varios segundos y superaría el timeout
  de 8 s del backend. Por defecto True.

No se almacenan secretos.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "repuestopro_yolo11n_v3_webcam_robust.pt"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VISION_", extra="ignore")

    model_path: Path = DEFAULT_MODEL_PATH
    device: str = "0"
    max_image_pixels: int = 40_000_000
    warmup: bool = True


settings = Settings()