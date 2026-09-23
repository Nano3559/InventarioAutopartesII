"""Smoke test directo del modelo V2 con una imagen holdout de alternador (Kaggle valid, no usada en train)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2  # noqa: E402

from app.config import settings  # noqa: E402
from app.services import inference  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

IMAGEN_HOLDOUT = ROOT / "datasets/processed_v2/images/val/kaggle_prod__alternator__val__1.jpg"


def main() -> int:
    if not IMAGEN_HOLDOUT.is_file():
        print(f"SMOKE FAIL: no existe imagen holdout: {IMAGEN_HOLDOUT}")
        return 1

    estado = inference.cargar_modelo(settings.model_path, settings.device)
    if not estado.cargado:
        print(f"SMOKE FAIL: modelo no cargado ({estado.error})")
        return 1

    pixeles = cv2.imread(str(IMAGEN_HOLDOUT), cv2.IMREAD_COLOR)
    if pixeles is None:
        print(f"SMOKE FAIL: no se pudo leer imagen: {IMAGEN_HOLDOUT}")
        return 1

    detecciones = inference.detectar(pixeles, conf=inference.CONF_TECNICO_INFERENCIA)
    print(f"modelo: {estado.nombre_modelo} | version={estado.version_modelo}")
    print(f"clases: {estado.clases} | device: {estado.device}")
    print(f"imagen: {IMAGEN_HOLDOUT.name}")

    if not detecciones:
        print("SMOKE FAIL: sin detecciones en imagen holdout")
        return 1

    principal = detecciones[0]
    print(f"categoria: {principal['categoria']}")
    print(f"confianza: {principal['confianza']:.4f}")
    bbox = principal["boundingBox"]
    print(f"bbox: x={bbox['x']:.4f} y={bbox['y']:.4f} w={bbox['width']:.4f} h={bbox['height']:.4f}")

    valido_bbox = (
        0.0 <= bbox["x"] < 1.0
        and 0.0 <= bbox["y"] < 1.0
        and bbox["width"] > 0.0
        and bbox["height"] > 0.0
        and bbox["x"] + bbox["width"] <= 1.0
        and bbox["y"] + bbox["height"] <= 1.0
    )
    if principal["categoria"] != "alternador":
        print(f"SMOKE FAIL: categoria esperada 'alternador', obtenida '{principal['categoria']}'")
        return 1
    if valido_bbox is False:
        print("SMOKE FAIL: bbox fuera de rango normalizado")
        return 1

    print("SMOKE PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())