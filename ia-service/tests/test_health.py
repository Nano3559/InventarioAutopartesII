"""Tests del endpoint GET /vision/health.

Cobertura:
- 200 cuando el modelo carga correctamente y campos esperados;
- no expone el path absoluto del modelo ni datos internos;
- verifica 8 clases en el orden esperado de la cabecera del modelo;
- estado degradado (503) cuando el modelo no pudo cargarse.
"""
import re

from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app
from app.services import inference


def test_health_ok_modelo_cargado():
    inference.estado.cargado = False  # recarga limpia del singleton
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/vision/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["modelLoaded"] is True
    assert body["model"] == "YOLO11n"
    assert body["classes"] == 8
    assert re.match(r"^(cuda:\d+|cpu)$", str(body["device"]))


def test_health_no_expone_ruta_modelo():
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/vision/health")

    assert resp.status_code == 200
    raw = resp.text
    assert "best.pt" not in raw
    assert str(settings.model_path) not in raw
    assert "ia-service" not in raw
    assert "runs" not in raw


def test_inferencia_reporta_8_clases_orden_esperado():
    inference.estado.cargado = False
    app = create_app()
    with TestClient(app) as client:
        client.get("/vision/health")

    assert inference.estado.cargado is True
    assert inference.estado.clases == 8
    modelo = inference.obtener_modelo()
    assert list(modelo.names.values()) == inference.CLASSES_ESPERADAS


def test_health_degradado_sin_modelo_503(monkeypatch):
    def _cargar_falla(*_args, **_kwargs):
        inference.estado.cargado = False
        inference.estado.error = "error_de_carga"
        inference.estado.modelo = None
        raise RuntimeError("fallo de carga simulado")

    monkeypatch.setattr(inference, "cargar_modelo", _cargar_falla)

    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/vision/health")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "error"
    assert body["modelLoaded"] is False
    assert body["classes"] == 0
    assert "best.pt" not in resp.text