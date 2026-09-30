"""Configuración del servicio de visión RepuestoPro.

Variables de entorno (prefijo VISION_), con soporte de archivo .env local
(ia-service/.env, ignorado por git; las variables del proceso tienen prioridad):

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
- VISION_IA_KEY: secreto compartido opcional para autenticar las llamadas
  del backend mediante el header `X-Vision-Key`. Si NO se define, el servicio
  queda abierto y solo debe exponerse en red interna privada; se registra una
  advertencia al arrancar. Se compara en tiempo constante (sobre bytes) y nunca
  se loguea.
- VISION_ENV: entorno de ejecucion ("development" por defecto). En
  "production"/"prod" la autenticacion pasa a ser OBLIGATORIA: si falta
  VISION_IA_KEY el servicio falla cerrado y responde 503 en /vision/detect y
  /vision/classify en vez de exponer inferencia abierta.

No se almacenan secretos.
"""
import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "repuestopro_yolo11n_v3_webcam_robust.pt"
)


def _env_file_local() -> Path | None:
    """Archivo .env local del servicio, o None cuando no debe usarse.

    Bajo pytest NUNCA se lee el .env del desarrollador: la suite asume que
    no hay secreto ni dispositivo de maquina local, y depender de un archivo
    ignorado por git haria los tests no reproducibles.
    """
    if "pytest" in sys.modules or os.environ.get("VISION_LOAD_DOTENV", "1") == "0":
        return None
    return PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # env_file permite configurar el servicio con un .env local ignorado por git;
    # las variables de entorno reales del proceso siguen teniendo prioridad.
    model_config = SettingsConfigDict(
        env_prefix="VISION_",
        env_file=_env_file_local(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    model_path: Path = DEFAULT_MODEL_PATH
    device: str = "0"
    max_image_pixels: int = 40_000_000
    warmup: bool = True
    ia_key: str | None = None
    env: str = "development"

    @property
    def es_produccion(self) -> bool:
        return self.env.strip().lower() in {"production", "prod"}

    @property
    def auth_obligatoria(self) -> bool:
        """La autenticacion es obligatoria si hay secreto configurado o si el
        servicio corre en produccion. En produccion sin `VISION_IA_KEY` el
        servicio falla cerrado (503) en lugar de exponer inferencia abierta."""
        return bool(self.ia_key) or self.es_produccion


settings = Settings()