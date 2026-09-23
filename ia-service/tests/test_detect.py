"""Tests del endpoint POST /vision/detect (CV-6 Paso 3).

Cobertura:
- validaciones de upload (formato, vacío, MIME, >5MB, corrupta, dimensión);
- inferencia mockeada: 1..n detecciones, orden, bbox normalizado + clamp,
  mapeo de las 8 clases, confianza 0..1, sin detecciones, errores 503;
- contrato: sin class_id/class_name internos, consultadoEn ISO válido;
- carga UNA sola vez (short-circuit del singleton).
"""
from datetime import datetime

import cv2
import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import inference
from app.services.inference import CLASSES_ESPERADAS

TAMANO = 64


def _bytes_imagen(fmt: str = "jpg", corrupta: bool = False) -> bytes:
    if corrupta:
        return b"esto-no-es-una-imagen-" * 20
    img = np.zeros((TAMANO, TAMANO, 3), dtype=np.uint8)
    img[10:20, 10:20] = 255
    ok, buf = cv2.imencode(f".{fmt}", img)
    assert ok
    return buf.tobytes()


def _bytes_grandes() -> bytes:
    return np.zeros(5 * 1024 * 1024 + 1, dtype=np.uint8).tobytes()


class FakeBoxes:
    def __init__(self, dets: list[list[float]]):
        if not dets:
            self.xyxy = torch.zeros((0, 4))
            self.cls = torch.zeros((0,))
            self.conf = torch.zeros((0,))
        else:
            self.xyxy = torch.tensor([[d[0], d[1], d[2], d[3]] for d in dets])
            self.cls = torch.tensor([d[4] for d in dets])
            self.conf = torch.tensor([d[5] for d in dets])

    def __len__(self) -> int:
        return len(self.xyxy)


class FakeResults:
    def __init__(self, dets: list[list[float]]):
        boxes = FakeBoxes(dets)
        self.boxes = boxes if len(boxes) > 0 else None


class FakeModelo:
    names = {i: n for i, n in enumerate(CLASSES_ESPERADAS)}

    def __init__(self, dets: list[list[float]] | None = None, raises: str | None = None):
        self.dets = dets or []
        self.raises = raises

    def predict(self, *_args, **_kwargs):
        if self.raises:
            raise RuntimeError(self.raises)
        return FakeResults(self.dets)

    def to(self, *_args, **_kwargs):
        return self


def _cliente(fake: FakeModelo):
    inference.estado.cargado = True
    inference.estado.error = None
    inference.estado.device = "cuda:0"
    inference.estado.modelo = fake
    app = create_app()
    return TestClient(app)


def _post(client: TestClient, nombre: str, data: bytes | None, mime: str):
    if data is None:
        return client.post("/vision/detect")
    return client.post(
        "/vision/detect",
        files={"image": (nombre, data, mime)},
    )


# ---------- Validación de upload ----------


def test_detect_jpeg_valido():
    with _cliente(FakeModelo([[10, 10, 20, 20, 7, 0.87]])) as client:
        resp = _post(client, "a.jpg", _bytes_imagen("jpg"), "image/jpeg")
    assert resp.status_code == 200
    assert isinstance(resp.json()["detecciones"], list)


def test_detect_png_valido():
    with _cliente(FakeModelo()) as client:
        resp = _post(client, "a.png", _bytes_imagen("png"), "image/png")
    assert resp.status_code == 200


def test_detect_webp_valido():
    with _cliente(FakeModelo()) as client:
        resp = _post(client, "a.webp", _bytes_imagen("webp"), "image/webp")
    assert resp.status_code == 200


def test_detect_sin_campo_image_422():
    with _cliente(FakeModelo()) as client:
        resp = _post(client, "a.jpg", None, "image/jpeg")
    assert resp.status_code == 422


def test_detect_archivo_vacio_400():
    with _cliente(FakeModelo()) as client:
        resp = _post(client, "vacio.jpg", b"", "image/jpeg")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "archivo_vacio"


def test_detect_mime_no_soportado_415():
    with _cliente(FakeModelo()) as client:
        resp = _post(client, "a.txt", b"hola", "text/plain")
    assert resp.status_code == 415
    assert resp.json()["detail"] == "formato_no_soportado"


def test_detect_imagen_corrupta_mime_valido_400():
    with _cliente(FakeModelo()) as client:
        resp = _post(client, "raro.jpg", _bytes_imagen(corrupta=True), "image/jpeg")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "imagen_corrupta"


def test_detect_mas_de_5mb_413():
    with _cliente(FakeModelo()) as client:
        resp = _post(client, "gorda.jpg", _bytes_grandes(), "image/jpeg")
    assert resp.status_code == 413
    assert resp.json()["detail"] == "archivo_demasiado_grande"


# ---------- Inferencia con modelo mockeado ----------


def test_detect_una_deteccion():
    fake = FakeModelo([[10, 10, 20, 20, 3, 0.9]])
    with _cliente(fake) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["detecciones"]) == 1
    det = body["detecciones"][0]
    assert det["categoria"] == "alternador"
    assert det["confianza"] == pytest.approx(0.9)


def test_detect_multiples_detecciones():
    fake = FakeModelo(
        [
            [10, 10, 20, 20, 7, 0.95],
            [30, 30, 40, 40, 3, 0.8],
            [5, 5, 12, 12, 0, 0.6],
        ]
    )
    with _cliente(fake) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    assert resp.status_code == 200
    assert len(resp.json()["detecciones"]) == 3


def test_detect_orden_confianza_descendente():
    fake = FakeModelo(
        [
            [30, 30, 40, 40, 7, 0.7],
            [10, 10, 20, 20, 3, 0.9],
            [5, 5, 12, 12, 6, 0.55],
        ]
    )
    with _cliente(fake) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    confs = [d["confianza"] for d in resp.json()["detecciones"]]
    assert confs == sorted(confs, reverse=True)


def test_detect_sin_detecciones_200_vacio():
    with _cliente(FakeModelo([])) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    assert resp.status_code == 200
    body = resp.json()
    assert body["detecciones"] == []
    assert "consultadoEn" in body


def test_detect_bbox_normalizado():
    fake = FakeModelo([[10, 10, 30, 30, 7, 0.9]])
    with _cliente(fake) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    box = resp.json()["detecciones"][0]["boundingBox"]
    assert box["x"] == pytest.approx(10 / TAMANO)
    assert box["y"] == pytest.approx(10 / TAMANO)
    assert box["width"] == pytest.approx(20 / TAMANO)
    assert box["height"] == pytest.approx(20 / TAMANO)
    assert box["x"] + box["width"] <= 1.0
    assert box["y"] + box["height"] <= 1.0


def test_detect_bbox_clamp_dentro_0_1():
    fake = FakeModelo([[-10, -10, 80, 80, 7, 0.9]])
    with _cliente(fake) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    box = resp.json()["detecciones"][0]["boundingBox"]
    for v in (box["x"], box["y"], box["width"], box["height"]):
        assert 0.0 <= v <= 1.0
    assert box["x"] == 0.0
    assert box["y"] == 0.0
    assert box["width"] == 1.0
    assert box["height"] == 1.0


def test_detect_bbox_degenerada_descartada():
    fake = FakeModelo([[20, 20, 10, 10, 7, 0.9]])
    with _cliente(fake) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    assert resp.json()["detecciones"] == []


@pytest.mark.parametrize(
    ("clase_id", "categoria"),
    [
        (0, "pastilla de freno"),
        (1, "disco de freno"),
        (2, "caliper"),
        (3, "alternador"),
        (4, "filtro de aceite"),
        (5, "filtro de aire"),
        (6, "radiador"),
        (7, "faro"),
    ],
)
def test_detect_mapeo_8_clases(clase_id, categoria):
    fake = FakeModelo([[10, 10, 20, 20, clase_id, 0.9]])
    with _cliente(fake) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    det = resp.json()["detecciones"][0]
    assert det["categoria"] == categoria


def test_detect_confianza_dentro_0_1():
    fake = FakeModelo([[10, 10, 20, 20, 7, 0.12345]])
    with _cliente(fake) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    conf = resp.json()["detecciones"][0]["confianza"]
    assert 0.0 <= conf <= 1.0
    assert conf == pytest.approx(0.12345)


def test_detect_clase_fuera_de_8_descartada():
    fake = FakeModelo([[10, 10, 20, 20, 99, 0.9]])
    with _cliente(fake) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    assert resp.status_code == 200
    assert resp.json()["detecciones"] == []


def test_detect_modelo_no_disponible_503(monkeypatch):
    def _cargar_falla(*_args, **_kwargs):
        inference.estado.cargado = False
        inference.estado.error = "error_de_carga"
        inference.estado.modelo = None
        raise RuntimeError("fallo de carga simulado")

    monkeypatch.setattr(inference, "cargar_modelo", _cargar_falla)

    app = create_app()
    with TestClient(app) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "modelo_no_disponible"


def test_detect_error_inferencia_503():
    fake = FakeModelo(raises="boom interno")
    with _cliente(fake) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "error_inferencia"
    assert "boom" not in resp.text


# ---------- Contrato de respuesta ----------


def test_detect_no_expone_campos_internos():
    fake = FakeModelo([[10, 10, 20, 20, 7, 0.9]])
    with _cliente(fake) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    raw = resp.text
    for oculto in ("class_id", "class_name", "x1", "y1", "x2", "y2", "bbox"):
        assert oculto not in raw
    assert "detecciones" in raw
    assert "categoria" in raw
    assert "boundingBox" in raw


def test_detect_consultado_en_iso_valido():
    with _cliente(FakeModelo([[10, 10, 20, 20, 7, 0.9]])) as client:
        resp = _post(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    ts = datetime.fromisoformat(resp.json()["consultadoEn"])
    assert ts.tzinfo is not None


# ---------- Carga única ----------


def test_modelo_no_se_recarga(monkeypatch, tmp_path):
    ruta = tmp_path / "modelo.pt"
    ruta.write_bytes(b"no es un modelo real, solo para short-circuit")

    inference.estado.cargado = False
    inference.estado.modelo = None
    inference.estado.cargas = 0

    fake = FakeModelo()
    monkeypatch.setattr(inference, "YOLO", lambda *a, **k: fake)

    inference.cargar_modelo(path=ruta, device="cpu")
    assert inference.contador_cargas() == 1

    inference.cargar_modelo(path=ruta, device="cpu")
    assert inference.contador_cargas() == 1