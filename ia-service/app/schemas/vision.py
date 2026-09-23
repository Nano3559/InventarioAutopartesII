"""Schemas Pydantic del contrato de visión (CV-6 Paso 3).

Nombres JSON EXACTOS requeridos por el backend de Ross:
- detecciones[].categoria
- detecciones[].confianza
- detecciones[].boundingBox.{x,y,width,height}
- consultadoEn (ISO-8601)
No se usa class_id/class_name ni bbox{x1,y1,x2,y2}.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

TOLERANCIA_SUMA = 1e-6


class BoundingBox(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def _dentro_de_limites_de_imagen(self) -> "BoundingBox":
        if self.x + self.width > 1.0 + TOLERANCIA_SUMA:
            raise ValueError("x + width excede los límites de la imagen")
        if self.y + self.height > 1.0 + TOLERANCIA_SUMA:
            raise ValueError("y + height excede los límites de la imagen")
        return self


class Deteccion(BaseModel):
    categoria: str = Field(min_length=1, max_length=120)
    confianza: float = Field(ge=0.0, le=1.0)
    boundingBox: Optional[BoundingBox] = None


class DetectResponse(BaseModel):
    detecciones: list[Deteccion]
    consultadoEn: datetime


class Clasificacion(BaseModel):
    categoria: str = Field(min_length=1, max_length=120)
    confianza: float = Field(ge=0.0, le=1.0)


class ClassifyResponse(BaseModel):
    clasificacion: Optional[Clasificacion] = None
    consultadoEn: datetime