"""Fixture global de pytest para los tests de ia-service.

- Desactiva el warmup del lifespan para que los TestClient que abren la app no
  ejecuten una predicción real de GPU en cada arranque (el warmup es un costo de
  producción, no de tests).
- Fuerza VISION_ENV=development para que la suite sea determinista aunque el
  desarrollador tenga VISION_ENV=production en su entorno. Los tests que
  necesitan produccion lo sobrescriben con monkeypatch.
"""
import pytest

from app.config import settings

settings.warmup = False


@pytest.fixture(autouse=True)
def _entorno_de_desarrollo(monkeypatch):
    monkeypatch.setattr(settings, "env", "development")