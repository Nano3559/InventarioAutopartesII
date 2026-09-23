"""Schemas Pydantic del servicio de visión."""
from app.schemas.vision import (
    BoundingBox,
    Clasificacion,
    ClassifyResponse,
    DetectResponse,
    Deteccion,
)

__all__ = [
    "BoundingBox",
    "Deteccion",
    "DetectResponse",
    "Clasificacion",
    "ClassifyResponse",
]