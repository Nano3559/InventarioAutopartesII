"""Tests de endurecimiento CV-6 Paso 5.

Casos nuevos de robustez (sin cambiar contratos):
- bbox NaN/Inf descartadas;
- confianza fuera de rango / NaN / Inf descartadas (0 y 1 sí son válidas);
- clase inválida (negativa, >7, no entero) — fail-safe sin inventar categoría;
- image bomb: límite de píxeles configurable;
- modelo con path inexistente: estado degradado + health/detect/classify
  controlados y sin filtrar path;
- concurrencia básica de requests sobre una instancia de modelo compartida.
"""
import math
from concurrent.futures import ThreadPoolExecutor

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


def _cliente_modelo(fake: FakeModelo):
    inference.estado.cargado = True
    inference.estado.error = None
    inference.estado.device = "cuda:0"
    inference.estado.modelo = fake
    return TestClient(create_app())


# ---------- Bounding box: NaN / Inf ----------


def test_bbox_nan_descartada():
    fake = FakeModelo(
        [
            [float("nan"), 10, 20, 20, 7, 0.9],
            [10, 10, 20, 20, 7, 0.5],
        ]
    )
    with _cliente_modelo(fake) as client:
        resp = client.post(
            "/vision/detect",
            files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")},
        )
    dets = resp.json()["detecciones"]
    assert len(dets) == 1
    assert dets[0]["categoria"] == "faro"
    assert math.isfinite(dets[0]["confianza"])


def test_bbox_inf_descartada():
    fake = FakeModelo(
        [
            [10, 10, float("inf"), 20, 7, 0.9],
            [10, 10, 20, 20, 7, 0.4],
        ]
    )
    with _cliente_modelo(fake) as client:
        resp = client.post(
            "/vision/detect",
            files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")},
        )
    dets = resp.json()["detecciones"]
    assert len(dets) == 1
    assert dets[0]["confianza"] == pytest.approx(0.4)


# ---------- Confianza ----------


def test_confianza_0_y_1_validas_y_fuera_de_rango_descartadas():
    fake = FakeModelo(
        [
            [5, 5, 10, 10, 7, 0.0],
            [15, 15, 25, 25, 7, 1.0],
            [30, 30, 40, 40, 7, -0.5],
            [45, 45, 55, 55, 7, 1.5],
        ]
    )
    with _cliente_modelo(fake) as client:
        resp = client.post(
            "/vision/detect",
            files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")},
        )
    dets = resp.json()["detecciones"]
    confs = sorted(d["confianza"] for d in dets)
    assert confs == [0.0, 1.0]
    for d in dets:
        assert 0.0 <= d["confianza"] <= 1.0


def test_confianza_nan_inf_descartadas():
    fake = FakeModelo(
        [
            [5, 5, 10, 10, 7, float("nan")],
            [15, 15, 25, 25, 7, float("inf")],
        ]
    )
    with _cliente_modelo(fake) as client:
        resp = client.post(
            "/vision/detect",
            files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")},
        )
    assert resp.json()["detecciones"] == []


# ---------- Clases inválidas (fail-safe) ----------


def test_clase_negativa_descartada():
    fake = FakeModelo([[10, 10, 20, 20, -1, 0.9]])
    with _cliente_modelo(fake) as client:
        resp = client.post(
            "/vision/detect",
            files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")},
        )
    assert resp.json()["detecciones"] == []


def test_clase_mayor_a_7_descartada():
    fake = FakeModelo([[10, 10, 20, 20, 8, 0.9]])
    with _cliente_modelo(fake) as client:
        resp = client.post(
            "/vision/detect",
            files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")},
        )
    assert resp.json()["detecciones"] == []


def test_clase_no_entera_descartada():
    """ID fraccional NaN/Inf/fuera de rango se descarta; nunca se trunca."""
    for cls in (2.7, 3.5):
        fake = FakeModelo([[10, 10, 20, 20, cls, 0.9]])
        with _cliente_modelo(fake) as client:
            resp = client.post(
                "/vision/detect",
                files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")},
            )
        assert resp.json()["detecciones"] == []


def test_clase_nan_inf_descartadas():
    fake = FakeModelo(
        [
            [5, 5, 10, 10, float("nan"), 0.9],
            [15, 15, 25, 25, float("inf"), 0.8],
            [30, 30, 40, 40, 7, 0.7],
        ]
    )
    with _cliente_modelo(fake) as client:
        resp = client.post(
            "/vision/detect",
            files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")},
        )
    dets = resp.json()["detecciones"]
    assert len(dets) == 1
    assert dets[0]["categoria"] == "faro"


def test_clase_entera_exacta_valida():
    """IDs numericos que representan exactamente un entero 0..7 son validos."""
    caso_esperado = [
        (3.0, "alternador"),
        (3, "alternador"),
        (0, "pastilla de freno"),
    ]
    for cls, categoria in caso_esperado:
        fake = FakeModelo([[10, 10, 20, 20, cls, 0.9]])
        with _cliente_modelo(fake) as client:
            resp = client.post(
                "/vision/detect",
                files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")},
            )
        det = resp.json()["detecciones"][0]
        assert det["categoria"] == categoria
        assert det["confianza"] == pytest.approx(0.9)


# ---------- Image bomb: límite de píxeles ----------


def test_imagen_dimensiones_excesivas_400():
    # 7000x7000 = 49 MP > VISION_MAX_IMAGE_PIXELS (40 MP). JPEG sólido: bytes
    # pequeños pero decodificados a dimensiones enormes (anti image-bomb).
    img = np.zeros((7000, 7000, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    fake = FakeModelo([[10, 10, 20, 20, 7, 0.9]])
    with _cliente_modelo(fake) as client:
        resp = client.post(
            "/vision/detect",
            files={"image": ("bomba.jpg", buf.tobytes(), "image/jpeg")},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "dimensiones_invalidas"


# ---------- Modelo: path inexistente / estado degradado ----------


def test_cargar_modelo_path_inexistente_degrada_sin_filtrar_ruta(monkeypatch):
    inference.estado.cargado = False
    inference.estado.modelo = None
    inference.estado.error = None

    with pytest.raises(FileNotFoundError):
        inference.cargar_modelo(path="no/existe/este/best.pt")

    assert inference.estado.cargado is False
    assert inference.estado.error == "modelo_no_encontrado"

    def _cargar_falla(*_args, **_kwargs):
        raise FileNotFoundError("no existe")

    monkeypatch.setattr(inference, "cargar_modelo", _cargar_falla)
    app = create_app()
    with TestClient(app) as client:
        r_health = client.get("/vision/health")
        r_detect = client.post(
            "/vision/detect",
            files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")},
        )
        r_classify = client.post(
            "/vision/classify",
            files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")},
        )

    assert r_health.status_code == 503
    assert r_health.json()["modelLoaded"] is False
    assert r_health.json()["status"] == "error"
    assert "best.pt" not in r_health.text
    assert r_detect.status_code == 503
    assert r_detect.json()["detail"] == "modelo_no_disponible"
    assert r_classify.status_code == 503
    assert r_classify.json()["detail"] == "modelo_no_disponible"


# ---------- Concurrencia básica ----------


def test_concurrencia_basica_5_requests_estable():
    fake = FakeModelo([[10, 10, 20, 20, 7, 0.9]])
    inference.estado.cargado = True
    inference.estado.error = None
    inference.estado.device = "cuda:0"
    inference.estado.modelo = fake
    inference.estado.cargas = 1
    app = create_app()

    def _enviar(_i):
        with TestClient(app) as client:
            return client.post(
                "/vision/detect",
                files={"image": ("a.jpg", _bytes_imagen(), "image/jpeg")},
            )

    with ThreadPoolExecutor(max_workers=5) as ex:
        respuestas = list(ex.map(_enviar, range(5)))

    assert len(respuestas) == 5
    for r in respuestas:
        assert r.status_code == 200
        body = r.json()
        assert len(body["detecciones"]) == 1
        assert body["detecciones"][0]["categoria"] == "faro"
        assert "consultadoEn" in body
        assert body["detecciones"][0]["confianza"] <= 1.0

    assert inference.contador_cargas() == 1