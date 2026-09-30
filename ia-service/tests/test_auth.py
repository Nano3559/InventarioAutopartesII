"""Tests de autenticación backend -> ia-service (secreto de servicio).

El secreto se define con VISION_IA_KEY. Si NO esta definido el servicio
responde igual en development (solo valido en red interna privada); en
produccion (VISION_ENV=production) la autenticacion es obligatoria y el
servicio falla cerrado con 503 mientras no haya secreto.
"""
import asyncio

import cv2
import numpy as np
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app
from app.routers.vision import verificar_secreto

SECRETO = "secreto-de-servicio-de-prueba"


def _bytes_imagen() -> bytes:
    img = np.zeros((32, 32, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def test_sin_secreto_configurado_el_servicio_responde(monkeypatch):
    monkeypatch.setattr(settings, "ia_key", None)
    monkeypatch.setattr(settings, "env", "development")
    with TestClient(create_app()) as client:
        resp = client.post("/vision/detect", files={"image": ("f.jpg", _bytes_imagen(), "image/jpeg")})
    assert resp.status_code == 200


def test_en_produccion_sin_secreto_falla_cerrado(monkeypatch):
    """Sin VISION_IA_KEY en produccion NO se expone inferencia abierta: 503.

    Es el modo fail-closed: es preferible rechazar el trafico a dejar el
    servicio de inferencia abierto a toda la red.
    """
    monkeypatch.setattr(settings, "ia_key", None)
    monkeypatch.setattr(settings, "env", "production")
    with TestClient(create_app()) as client:
        detect = client.post("/vision/detect", files={"image": ("f.jpg", _bytes_imagen(), "image/jpeg")})
        classify = client.post("/vision/classify", files={"image": ("f.jpg", _bytes_imagen(), "image/jpeg")})
        health = client.get("/vision/health")
    assert detect.status_code == 503
    assert classify.status_code == 503
    assert health.status_code in (200, 503), "/vision/health sigue abierto para sondas"


def test_secreto_no_ascii_devuelve_401_y_no_500(monkeypatch):
    """Un header no ASCII contra un secreto ASCII debe ser 401, no 500.

    secrets.compare_digest() lanza TypeError con str no ASCII, lo que en la
    request terminaba en un HTTP 500 (DoS de informacion). La comparacion se
    hace sobre bytes UTF-8.

    El vector real es un cliente que envie bytes latin-1 crudos en el header
    (ASGI los decodifica como latin-1). httpx no puede construir esa request
    porque codifica los headers en ASCII, por eso se ejercita la dependencia
    `verificar_secreto` directamente.
    """
    monkeypatch.setattr(settings, "ia_key", SECRETO)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(verificar_secreto("clave-\u00e1-\u00f1"))
    assert exc.value.status_code == 401, "un valor no ASCII es credencial invalida, no error interno"


def test_secreto_no_ascii_configurado_acepta_ese_mismo_valor(monkeypatch):
    """Con secreto no ASCII, compararlo correctamente debe pasar (sin 500)."""
    secreto = "clave-\u00e1-\u00f1"
    monkeypatch.setattr(settings, "ia_key", secreto)
    asyncio.run(verificar_secreto(secreto))  # no debe lanzar

    with pytest.raises(HTTPException) as exc:
        asyncio.run(verificar_secreto("otra-clave-\u00e1"))
    assert exc.value.status_code == 401


def test_con_secreto_detect_exige_header(monkeypatch):
    monkeypatch.setattr(settings, "ia_key", SECRETO)
    with TestClient(create_app()) as client:
        sin_header = client.post("/vision/detect", files={"image": ("f.jpg", _bytes_imagen(), "image/jpeg")})
        header_malo = client.post(
            "/vision/detect",
            files={"image": ("f.jpg", _bytes_imagen(), "image/jpeg")},
            headers={"X-Vision-Key": "equivocado"},
        )
        header_bueno = client.post(
            "/vision/detect",
            files={"image": ("f.jpg", _bytes_imagen(), "image/jpeg")},
            headers={"X-Vision-Key": SECRETO},
        )
    assert sin_header.status_code == 401
    assert header_malo.status_code == 401
    assert header_bueno.status_code == 200


def test_con_secreto_classify_exige_header(monkeypatch):
    monkeypatch.setattr(settings, "ia_key", SECRETO)
    with TestClient(create_app()) as client:
        sin_header = client.post("/vision/classify", files={"image": ("f.jpg", _bytes_imagen(), "image/jpeg")})
        header_bueno = client.post(
            "/vision/classify",
            files={"image": ("f.jpg", _bytes_imagen(), "image/jpeg")},
            headers={"X-Vision-Key": SECRETO},
        )
    assert sin_header.status_code == 401
    assert header_bueno.status_code == 200


def test_health_queda_abierto_para_sondas(monkeypatch):
    """El endpoint de salud no exige secreto: lo usan sondas/balanceadores.

    No expone datos sensibles (solo estado del modelo), ver test_health.py.
    """
    monkeypatch.setattr(settings, "ia_key", SECRETO)
    with TestClient(create_app()) as client:
        resp = client.get("/vision/health")
    assert resp.status_code in (200, 503)


def test_la_validacion_de_imagen_sigue_aplicandose_con_secreto(monkeypatch):
    """Con secreto valido, las validaciones de upload se siguen aplicando."""
    monkeypatch.setattr(settings, "ia_key", SECRETO)
    with TestClient(create_app()) as client:
        resp = client.post(
            "/vision/detect",
            files={"image": ("x.txt", b"no soy imagen", "text/plain")},
            headers={"X-Vision-Key": SECRETO},
        )
    assert resp.status_code == 415
