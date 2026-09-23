import argparse
import csv
import json
from pathlib import Path

from ultralytics import YOLO

from diagnostico_v2_common import (
    ART, CLASSES, CONF_TECNICO, ROOT, UMBRAL_BACKEND, V2_MODEL, imread, predict_v2,
)
from diagnostico_v2_02_variantes import make_H_warp, rescale_640x480
from diagnostico_v2_04_alternator import etapa_kg

V3_ART = ROOT / "ia-service/artifacts/diagnostico_v3"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default=str(V2_MODEL))
    ap.add_argument("--salida", default="alternator_progresivo.csv")
    args = ap.parse_args()

    orig = []
    with (ART / "manifest_seleccion_v2.csv").open(newline="", encoding="utf-8") as h:
        for r in csv.DictReader(h):
            if r["clase"] == "alternator" and r["split"] in ("val", "test"):
                orig.append(r)
    model = YOLO(args.modelo)
    gt = CLASSES.index("alternator")
    out = []
    for rec in orig:
        p = ROOT / rec["ruta"]
        img = imread(p)
        h0, w0 = img.shape[:2]
        lbl = ROOT / (rec["ruta"].replace("images", "labels").rsplit(".", 1)[0] + ".txt")
        lines = [ln for ln in lbl.read_text(encoding="utf-8").splitlines() if ln.strip()]
        bbox_norm = None
        for ln in lines:
            parts = ln.split()
            if int(parts[0]) == gt:
                cx, cy, bw, bh = map(float, parts[1:5]); break
        bbox_px = ((cx - bw / 2) * w0, (cy - bh / 2) * h0, (cx + bw / 2) * w0, (cy + bh / 2) * h0)

        etapas = [("ORIGINAL", img, bbox_px, {})]
        im, bb = rescale_640x480(img, bbox_px, scale=0.7)
        etapas.append(("RESIZE_640x480", im, bb, {"scale": 0.7}))
        im, bb = make_H_warp(im, 1, bb)
        etapas.append(("PERSPECTIVA", im, bb, {}))
        im = etapa_kg(im, bb)
        etapas.append(("BLUR_JPEG_EXP", im, bb, {}))
        im, bb = rescale_640x480(im, bb, scale=0.45)
        etapas.append(("ESCALA_45", im, bb, {"scale": 0.45}))
        im = etapa_kg(im, bb)
        etapas.append(("WEBCAM_COMBINADO", im, bb, {}))

        row = {"imagen": Path(rec["ruta"]).stem, "split": rec["split"]}
        for nombre, im, bb, params in etapas:
            dets = predict_v2(model, im)
            top = dets[0] if dets else None
            row[nombre] = {
                "clase_pred": top["clase"] if top else None,
                "conf": top["conf"] if top else None,
                "clase_correcta": bool(top and top["cls"] == gt),
                "detecciones": len(dets),
                "bbox": json.dumps(top["xyxyn"]) if top else None,
            }
        puntos = []
        for nombre in [e[0] for e in etapas]:
            f = row[nombre]
            if f["detecciones"] == 0:
                puntos.append(("vacias", nombre)); break
            if (f["conf"] or 0) < 0.55:
                puntos.append(("bajo 0.55", nombre)); break
            if (f["conf"] or 0) < 0.25:
                puntos.append(("bajo 0.25", nombre)); break
        row["primera_caida"] = puntos[0][1] if puntos else "nunca cae"
        row["tipo_caida"] = puntos[0][0] if puntos else "sin caida"
        pm = [(n, (r.get("conf") if r.get("conf") is not None else None))
              for n, r in row.items() if isinstance(r, dict) and "conf" in r]
        row["progresion"] = "; ".join(f"{n}:{c}" for n, c in pm if c is not None)
        out.append(row)

    with (V3_ART / args.salida).open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=["imagen", "split", "ORIGINAL", "RESIZE_640x480", "PERSPECTIVA",
                                          "BLUR_JPEG_EXP", "ESCALA_45", "WEBCAM_COMBINADO",
                                          "primera_caida", "tipo_caida", "progresion"])
        w.writeheader()
        for r in out:
            w.writerow({k: json.dumps(v) if isinstance(v, dict) else v for k, v in r.items()})
    print(json.dumps([{"imagen": r["imagen"], "primera_caida": r["primera_caida"], "tipo_caida": r["tipo_caida"],
                       "progresion": r["progresion"]} for r in out], indent=2))


if __name__ == "__main__":
    main()