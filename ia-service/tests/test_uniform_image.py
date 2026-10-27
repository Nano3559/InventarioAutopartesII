"""Capturas uniformes no deben crear candidatos ni invocar el modelo."""
from unittest.mock import patch

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.config import settings


@pytest.mark.parametrize("color", [(0, 0, 0), (255, 255, 255), (255, 0, 0)])
def test_uniform_image_has_no_candidates(color):
    image = np.empty((64, 64, 3), dtype=np.uint8)
    image[:] = color
    ok, data = cv2.imencode(".png", image)
    assert ok
    with patch.object(settings, "ia_key", None), patch.object(settings, "env", "development"), patch("app.services.inference.modelo_cargado", return_value=True), patch("app.services.inference.detectar") as detect:
        response = TestClient(create_app()).post("/vision/detect", files={"image": ("control.png", data.tobytes(), "image/png")})
    assert response.status_code == 200
    assert response.json()["detecciones"] == []
    detect.assert_not_called()
