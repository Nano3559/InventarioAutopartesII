import csv
import json
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from diagnostico_v2_common import (
    ART, BASE_MODEL, CLASSES, CONF_TECNICO, ROOT, SEED, UMBRAL_BACKEND, V2,
    V2_MODEL, det_serializable, get_image_paths, predict_v2,
)

CLASES_DIAG = ["alternator", "radiator", "headlight", "air_filter"]


def seleccionar():
    rows = get_image_paths()
    seleccion = []
    for c in CLASES_DIAG:
        sub = rows.values() if True else []
        cands = [r for r in rows.values() if r["target_class"] == c]
        product = [r for r in cands if r["domain"] == "product" and r["split"] in ("val", "test")]
        if product:
            items = sorted(product, key=lambda r: (r["split"], r["processed_image"]))
            seleccion.extend(items)
        else:
            ctx = [r for r in cands if r["split"] in ("val", "test")]
            seleccion.extend(sorted(ctx, key=lambda r: (r["split"], r["processed_image"])))
    return seleccion


def main():
    ART.mkdir(parents=True, exist_ok=True)
    sel = seleccionar()
    print("seleccion:", len(sel), Counter(r["target_class"] for r in sel))
    print("splits:", Counter((r["target_class"], r["split"]) for r in sel))

    model = YOLO(V2_MODEL)
    out_rows = []
    anot_dir = ART / "original_anotadas"
    anot_dir.mkdir(parents=True, exist_ok=True)

    for r in sel:
        img_path = ROOT / r["processed_image"]
        if not img_path.exists():
            continue
        dets = predict_v2(model, img_path)
        top = dets[0] if dets else None
        lbl = (ROOT / r["processed_label"]).read_text(encoding="utf-8").strip()
        ok_gt = CLASSES.index(r["target_class"])
        correcta = bool(top and top["cls"] == ok_gt)
        detectada = bool(dets)
        out_rows.append({
            "ruta": r["processed_image"],
            "clase": r["target_class"],
            "split": r["split"],
            "dominio": r["domain"],
            "fuente": r["source_image"],
            "bbox_method": r["bbox_method"],
            "gt_label": lbl,
            "conf_original": top["conf"] if top else None,
            "clase_pred": top["clase"] if top else None,
            "bbox_pred": json.dumps(top["xyxyn"]) if top else None,
            "detectada": detectada,
            "correcta": correcta,
        })

        img = cv2.imread(str(img_path))
        if top:
            c = top["cls"]
            x1, y1, x2, y2 = top["xyxy"]
            color = (60, 220, 60) if c == ok_gt else (60, 60, 255)
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            cv2.putText(img, f"{top['clase']} {top['conf']:.2f}", (int(x1), max(16, int(y1) - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        else:
            cv2.putText(img, "sin deteccion", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imwrite(str(anot_dir / (Path(r["processed_image"]).stem + ".png")), img)

    csv_path = ART / "manifest_seleccion_v2.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(out_rows[0].keys()))
        w.writeheader(); w.writerows(out_rows)

    resumen = {}
    for c in CLASES_DIAG:
        sub = [x for x in out_rows if x["clase"] == c]
        confs = [x["conf_original"] for x in sub if x["conf_original"] is not None]
        resumen[c] = {
            "imgs": len(sub),
            "correctas": sum(1 for x in sub if x["correcta"]),
            "vacias": sum(1 for x in sub if not x["detectada"]),
            "conf_media": round(sum(confs) / len(confs), 4) if confs else None,
            "sobre_umbral_055": sum(1 for x in sub if (x["conf_original"] or 0) >= UMBRAL_BACKEND),
        }
    print(json.dumps(resumen, indent=2))
    (ART / "manifest_resumen.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    print("CSV:", csv_path)


if __name__ == "__main__":
    main()