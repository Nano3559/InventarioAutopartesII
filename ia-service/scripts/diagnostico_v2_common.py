import csv
import random
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "ia-service/datasets/processed_v2"
V2_MODEL = ROOT / "ia-service/runs/detect/repuestopro_yolo11n_v2_domain_balanced/weights/best.pt"
BASE_MODEL = ROOT / "ia-service/runs/detect/repuestopro_yolo11n_baseline_v1/weights/best.pt"
ART = ROOT / "ia-service/artifacts/diagnostico_v2"

CLASSES = ["brake_pad", "brake_rotor", "brake_caliper", "alternator", "oil_filter", "air_filter", "radiator", "headlight"]
CONF_TECNICO = 0.25
UMBRAL_BACKEND = 0.55

SEED = 20260923


def read_labels(p):
    boxes = []
    for ln in Path(p).read_text(encoding="utf-8").splitlines():
        parts = ln.split()
        if len(parts) == 5:
            boxes.append((int(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])))
    return boxes


def get_image_paths():
    rows = {}
    with (V2 / "processed_v2_manifest.csv").open(newline="", encoding="utf-8") as h:
        for r in csv.DictReader(h):
            rows.setdefault(r["processed_image"], r)
    return rows


def imread(p):
    img = cv2.imread(str(p))
    if img is None:
        raise FileNotFoundError(p)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def det_serializable(det):
    return {
        "cls": int(det.cls.item()),
        "clase": CLASSES[int(det.cls.item())],
        "conf": round(float(det.conf.item()), 4),
        "xyxy": [round(float(v), 4) for v in det.xyxy[0].tolist()],
        "xyxyn": [round(float(v), 4) for v in det.xyxyn[0].tolist()],
    }


def predict_v2(model, img):
    preds = model.predict(img, conf=CONF_TECNICO, imgsz=640, device=0, verbose=False)[0]
    dets = [det_serializable(b) for b in preds.boxes]
    return dets


def gaussian_k(size):
    return cv2.getGaussianKernel(size, 0).dot(cv2.getGaussianKernel(size, 0).T)