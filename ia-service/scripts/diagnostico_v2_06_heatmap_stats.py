import json
import csv
from pathlib import Path

import cv2
import numpy as np

from diagnostico_v2_common import ART, ROOT, V2, CLASSES, read_labels

HEAT = ART / "heatmaps"


def heatmap_stats(cam_path, img_path, bbox_norm):
    cam = cv2.imread(str(cam_path), cv2.IMREAD_GRAYSCALE).astype(np.float32)
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-9)
    h, w = cam.shape
    total = cam.sum() + 1e-9
    # concentración: fracción de masa dentro del bbox GT
    if bbox_norm:
        x1, y1, x2, y2 = [bbox_norm[0] - bbox_norm[2]/2, bbox_norm[1] - bbox_norm[3]/2,
                          bbox_norm[0] + bbox_norm[2]/2, bbox_norm[1] + bbox_norm[3]/2]
        xs, ys, xe, ye = int(x1*w), int(y1*h), int(x2*w), int(y2*h)
        xs, ys = max(0, xs), max(0, ys)
        in_box = cam[ys:ye, xs:xe].sum()
    else:
        in_box = 0.0
    frac = float(in_box / total)
    # centroide de masa
    yys, xxs = np.mgrid[0:h, 0:w]
    cx = float((xxs * cam).sum() / total)
    cy = float((yys * cam).sum() / total)
    cx_n, cy_n = cx / w, cy / h
    # dispersión (radio de giro normalizado)
    rg = float(np.sqrt((( (xxs - cx)**2 + (yys - cy)**2 ) ** 1) * cam).sum() if False else 0)
    var_x = float(((xxs - cx)**2 * cam).sum() / total) / (w**2)
    var_y = float(((yys - cy)**2 * cam).sum() / total) / (h**2)
    return {"frac_en_bbox": round(frac, 4), "centroide_n": [round(cx_n, 3), round(cy_n, 3)],
            "var_x_n": round(var_x, 5), "var_y_n": round(var_y, 5)}


def get_bbox_norm(ruta):
    lbl = ROOT / (ruta.replace("images", "labels").rsplit(".", 1)[0] + ".txt")
    if not lbl.exists():
        return None
    for ln in lbl.read_text(encoding="utf-8").splitlines():
        p = ln.split()
        if len(p) == 5:
            return tuple(float(v) for v in p[1:5])
    return None


def main():
    report = json.loads((ART / "heatmaps_report.json").read_text(encoding="utf-8"))
    # stems origen por clase+tag
    stems = {
        ("alternator", "original"): "kaggle_prod__alternator__test__1",
        ("alternator", "degradada_perspectiva"): "kaggle_prod__alternator__test__1",
        ("alternator", "degradada_webcam"): "kaggle_prod__alternator__test__5",
        ("alternator", "vacia_escala"): "kaggle_prod__alternator__test__1",
        ("alternator", "vacia_webcam"): "kaggle_prod__alternator__val__2",
        ("radiator", "original"): "kaggle_prod__radiator__test__1",
        ("radiator", "degradada"): "kaggle_prod__radiator__test__1",
        ("headlight", "original"): "kaggle_prod__headlight__test__1",
        ("headlight", "degradada"): "kaggle_prod__headlight__test__1",
    }
    with (V2 / "processed_v2_manifest.csv").open(newline="", encoding="utf-8") as h:
        man = list(csv.DictReader(h))
    rows = []
    for (cls, tag), stem in stems.items():
        rec = next((r for r in man if Path(r["processed_image"]).stem == stem), None)
        bbox = get_bbox_norm(rec["processed_image"]) if rec else None
        entry = report.get(cls, {}).get(tag)
        if not entry:
            continue
        fname = entry.get("heatmaps", {}).get("16")
        if not fname:
            continue
        heat_path = HEAT / fname
        if not heat_path.exists():
            continue
        st = heatmap_stats(heat_path, None, bbox)
        rows.append({"caso": f"{cls}_{tag}", "bbox_gt": str(bbox),
                     "predicciones": entry.get("predicciones"), **st})
    for r in rows:
        print(r)
    (ART / "heatmap_stats.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()