import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from ultralytics import YOLO

from diagnostico_v2_common import ROOT, UMBRAL_BACKEND, V2_MODEL, predict_v2

V3_ART = ROOT / "ia-service/artifacts/diagnostico_v3"


def pick(recs, clase, transformacion):
    return next((r for r in recs if r["clase"] == clase and r["transformacion"] == transformacion), None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default=str(V2_MODEL))
    args = ap.parse_args()
    with (V3_ART / "webcam_holdout_manifest.csv").open(newline="", encoding="utf-8") as h:
        recs = list(csv.DictReader(h))
    model = YOLO(args.modelo)

    casos = {
        "alternator_digital": pick(recs, "alternator", "ORIGINAL"),
        "alternator_webcam": pick(recs, "alternator", "K_webcam_realista"),
        "radiator": pick(recs, "radiator", "ORIGINAL"),
        "headlight": pick(recs, "headlight", "ORIGINAL"),
        "air_filter": pick(recs, "air_filter", "ORIGINAL"),
    }
    out = []
    for nombre, rec in casos.items():
        if rec is None:
            print("FALTA", nombre)
            continue
        p = ROOT / "ia-service/artifacts/diagnostico_v3" / rec["archivo"]
        dets = predict_v2(model, p)
        top = dets[0] if dets else None
        sobre = bool(top and top["conf"] >= UMBRAL_BACKEND)
        row = {"caso": nombre, "archivo": rec["archivo"],
               "prediccion": top["clase"] if top else None,
               "conf": top["conf"] if top else None,
               "sobre_055": sobre, "n_detecciones": len(dets),
               "detecciones": [{"clase": d["clase"], "conf": d["conf"]} for d in dets]}
        out.append(row)
        print(f"{nombre:18s} -> {row['prediccion']} conf={row['conf']} >=0.55:{sobre} n={row['n_detecciones']}")
    (V3_ART / f"smoke_{Path(args.modelo).stem}.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()