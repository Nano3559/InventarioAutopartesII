"""Fixture global de pytest para los tests de ia-service.

Desactiva el warmup del lifespan para que los TestClient que abren la app no
ejecuten una predicción real de GPU en cada arranque (el warmup es un costo de
producción, no de tests).
"""
from app.config import settings

settings.warmup = False