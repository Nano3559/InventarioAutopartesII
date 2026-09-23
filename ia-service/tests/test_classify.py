"""Tests del endpoint POST /vision/classify (CV-6 Paso 4).

Endpoint auxiliar basado en la MISMA inferencia YOLO de /vision/detect.
Cobertura:
- validaciones de upload idénticas a detect;
- selección de la detección de MAYOR confianza;
- sin detecciones -> clasificacion null (200);
- respuesta sin class_id/class_name/bbox, consultadoEn ISO;
- errores 503 (modelo/ inferencia);
- detect y health siguen funcionando tras añadir classify;
- modelo se carga una sola vez.
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


def _post_classify(client: TestClient, nombre: str, data: bytes | None, mime: str):
    if data is None:
        return client.post("/vision/classify")
    return client.post(
        "/vision/classify",
        files={"image": (nombre, data, mime)},
    )


# ---------- Validación de upload (igual a detect) ----------


def test_classify_jpeg_valido():
    with _cliente(FakeModelo([[10, 10, 20, 20, 7, 0.87]])) as client:
        resp = _post_classify(client, "a.jpg", _bytes_imagen("jpg"), "image/jpeg")
    assert resp.status_code == 200
    assert resp.json()["clasificacion"]["categoria"] == "faro"


def test_classify_png_valido():
    with _cliente(FakeModelo()) as client:
        resp = _post_classify(client, "a.png", _bytes_imagen("png"), "image/png")
    assert resp.status_code == 200


def test_classify_webp_valido():
    with _cliente(FakeModelo()) as client:
        resp = _post_classify(client, "a.webp", _bytes_imagen("webp"), "image/webp")
    assert resp.status_code == 200


def test_classify_sin_campo_image_422():
    with _cliente(FakeModelo()) as client:
        resp = _post_classify(client, "a.jpg", None, "image/jpeg")
    assert resp.status_code == 422


def test_classify_archivo_vacio_400():
    with _cliente(FakeModelo()) as client:
        resp = _post_classify(client, "vacio.jpg", b"", "image/jpeg")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "archivo_vacio"


def test_classify_mime_invalido_415():
    with _cliente(FakeModelo()) as client:
        resp = _post_classify(client, "a.txt", b"hola", "text/plain")
    assert resp.status_code == 415
    assert resp.json()["detail"] == "formato_no_soportado"


def test_classify_imagen_corrupta_400():
    with _cliente(FakeModelo()) as client:
        resp = _post_classify(client, "raro.jpg", _bytes_imagen(corrupta=True), "image/jpeg")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "imagen_corrupta"


def test_classify_mas_de_5mb_413():
    with _cliente(FakeModelo()) as client:
        resp = _post_classify(client, "gorda.jpg", _bytes_grandes(), "image/jpeg")
    assert resp.status_code == 413
    assert resp.json()["detail"] == "archivo_demasiado_grande"


# ---------- Selección de la detección principal ----------


def test_classify_una_deteccion():
    fake = FakeModelo([[10, 10, 20, 20, 5, 0.9]])
    with _cliente(fake) as client:
        resp = _post_classify(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    clas = resp.json()["clasificacion"]
    assert clas["categoria"] == "filtro de aire"
    assert clas["confianza"] == pytest.approx(0.9)


def test_classify_multiples_detecciones_responde_principal():
    fake = FakeModelo(
        [
            [10, 10, 20, 20, 6, 0.62],
            [30, 30, 40, 40, 3, 0.91],
            [5, 5, 12, 12, 7, 0.77],
        ]
    )
    with _cliente(fake) as client:
        resp = _post_classify(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    clas = resp.json()["clasificacion"]
    assert clas["categoria"] == "alternador"
    assert clas["confianza"] == pytest.approx(0.91)


def test_classify_selecciona_mayor_confianza():
    fake = FakeModelo(
        [
            [30, 30, 40, 40, 7, 0.5],
            [10, 10, 20, 20, 3, 0.95],  # mayor confianza, NO primera en lista
            [5, 5, 12, 12, 6, 0.8],
        ]
    )
    with _cliente(fake) as client:
        resp = _post_classify(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    clas = resp.json()["clasificacion"]
    assert clas["categoria"] == "alternador"
    assert clas["confianza"] == pytest.approx(0.95)


def test_classify_una_sola_deteccion_por_imagen():
    """classify devuelve la principal, no la lista completa."""
    fake = FakeModelo(
        [
            [10, 10, 20, 20, 6, 0.62],
            [30, 30, 40, 40, 3, 0.91],
        ]
    )
    with _cliente(fake) as client:
        resp = _post_classify(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    body = resp.json()
    assert isinstance(body["clasificacion"], dict)
    assert "clasificacion" in body
    assert "detecciones" not in body


def test_classify_sin_detecciones_null_200():
    with _cliente(FakeModelo([])) as client:
        resp = _post_classify(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    assert resp.status_code == 200
    body = resp.json()
    assert body["clasificacion"] is None
    assert "consultadoEn" in body


def test_classify_categoria_correcta():
    fake = FakeModelo([[10, 10, 20, 20, 0, 0.5]])
    with _cliente(fake) as client:
        resp = _post_classify(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    assert resp.json()["clasificacion"]["categoria"] == "pastilla de freno"


def test_classify_confianza_dentro_0_1():
    fake = FakeModelo([[10, 10, 20, 20, 4, 0.333]])
    with _cliente(fake) as client:
        resp = _post_classify(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    conf = resp.json()["clasificacion"]["confianza"]
    assert 0.0 <= conf <= 1.0
    assert conf == pytest.approx(0.333)


# ---------- Contrato de respuesta ----------


def test_classify_no_expone_campos_internos_ni_bbox():
    fake = FakeModelo([[10, 10, 20, 20, 7, 0.9]])
    with _cliente(fake) as client:
        resp = _post_classify(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    raw = resp.text
    for oculto in ("class_id", "class_name", "boundingBox", "detecciones", "bbox"):
        assert oculto not in raw
    assert "clasificacion" in raw
    assert "categoria" in raw
    assert "confianza" in raw


def test_classify_consultado_en_iso_valido():
    with _cliente(FakeModelo([[10, 10, 20, 20, 7, 0.9]])) as client:
        resp = _post_classify(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    ts = datetime.fromisoformat(resp.json()["consultadoEn"])
    assert ts.tzinfo is not None


# ---------- Errores 503 ----------


def test_classify_modelo_no_disponible_503(monkeypatch):
    def _cargar_falla(*_args, **_kwargs):
        inference.estado.cargado = False
        inference.estado.error = "error_de_carga"
        inference.estado.modelo = None
        raise RuntimeError("fallo de carga simulado")

    monkeypatch.setattr(inference, "cargar_modelo", _cargar_falla)

    app = create_app()
    with TestClient(app) as client:
        resp = _post_classify(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "modelo_no_disponible"


def test_classify_error_inferencia_503():
    fake = FakeModelo(raises="boom clasificacion")
    with _cliente(fake) as client:
        resp = _post_classify(client, "a.jpg", _bytes_imagen(), "image/jpeg")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "error_inferencia"
    assert "boom" not in resp.text


# ---------- Coexistencia con detect y health ----------


def test_detect_classify_health_coexisten_y_carga_unica():
    fake = FakeModelo([[10, 10, 20, 20, 7, 0.9]])
    inference.estado.cargado = True
    inference.estado.error = None
    inference.estado.device = "cuda:0"
    inference.estado.modelo = fake
    inference.estado.cargas = 1

    app = create_app()
    with TestClient(app) as client:
        r_health = client.get("/vision/health")
        r_detect = client.post(
            "/vision/detect", files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")}
        )
        r_classify = client.post(
            "/vision/classify", files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")}
        )

    assert r_health.status_code == 200
    assert r_detect.status_code == 200
    assert r_classify.status_code == 200
    assert inference.contador_cargas() == 1
    top_detect = r_detect.json()["detecciones"][0]
    clas = r_classify.json()["clasificacion"]
    assert clas["categoria"] == top_detect["categoria"]
    assert clas["confianza"] == pytest.approx(top_detect["confianza"])