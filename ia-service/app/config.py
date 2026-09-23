"""Configuración del servicio de visión RepuestoPro.

Variables de entorno (prefijo VISION_):

- VISION_MODEL_PATH: ruta al peso YOLO. Por defecto apunta al best.pt del
  baseline actual, resuelto a partir de la ubicación del proyecto (pathlib),
  sin depender del working directory de uvicorn.
- VISION_DEVICE: dispositivo de inferencia ("0" para la primera GPU, "cpu",
  "cuda:0", etc.). Por defecto "0".
- VISION_MAX_IMAGE_PIXELS: límite técnico de píxeles de una imagen decodificada
  (anti image-bomb). Valor por defecto 40_000_000 (~40 MP): amplio para fotos
  normales de celular (típico 8-50 MP) y suficientemente bajo para evitar
  reservas de memoria absurdas por imágenes comprimidas con dimensiones enormes.

No se almacenan secretos.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MODEL_PATH = (
    PROJECT_ROOT
    / "runs"
    / "detect"
    / "repuestopro_yolo11n_baseline_v1"
    / "weights"
    / "best.pt"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VISION_", extra="ignore")

    model_path: Path = DEFAULT_MODEL_PATH
    device: str = "0"
    max_image_pixels: int = 40_000_000


settings = Settings()