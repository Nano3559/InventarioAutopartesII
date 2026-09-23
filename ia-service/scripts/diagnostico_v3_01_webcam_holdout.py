import csv
import json
from pathlib import Path

import cv2
import numpy as np

import diagnostico_v2_02_variantes as variantes  # reutiliza transforms A-K
from diagnostico_v2_common import ART, CLASSES, ROOT, SEED, read_labels, imread

V3_ART = ROOT / "ia-service/artifacts/diagnostico_v3"
HOLDOUT = V3_ART / "webcam_sim_holdout"
SEED_HOLDOUT = SEED + 999  # mismos transforms, semilla/parámetros distintos (independiente del train)


def main():
    with (ROOT / "ia-service/artifacts/diagnostico_v2/manifest_seleccion_v2.csv").open(newline="", encoding="utf-8") as h:
        recs = list(csv.DictReader(h))
    HOLDOUT.mkdir(parents=True, exist_ok=True)

    # parámetros distintos para el holdout
    variantes.SEED = SEED_HOLDOUT
    variantes.RNG = np.random.default_rng(SEED_HOLDOUT)

    out_rows = []
    for rec in recs:
        img_path = ROOT / rec["ruta"]
        if not img_path.exists():
            continue
        img = imread(img_path)
        h, w = img.shape[:2]
        lbl_path = ROOT / Path(rec["ruta"].replace("images", "labels").rsplit(".", 1)[0] + ".txt")
        labels = read_labels(lbl_path) if lbl_path.exists() else []
        bbox_norm = None
        for ln in labels:
            if ln[0] == CLASSES.index(rec["clase"]):
                bbox_norm = (ln[1], ln[2], ln[3], ln[4]); break
        bbox_px = variantes.to_px(bbox_norm, w, h) if bbox_norm else None
        stem = Path(rec["ruta"]).stem
        row_base = {"clase": rec["clase"], "split": rec["split"], "ruta_original": rec["ruta"]}

        # original (baseline, mismo recorte)
        f_orig = f"{stem}__ORIGINAL.png"
        cv2.imwrite(str(HOLDOUT / f_orig), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        out_rows.append({**row_base, "transformacion": "ORIGINAL", "archivo": "webcam_sim_holdout/" + f_orig,
                         "parametros": "{}",
                         "bbox_gt_px": json.dumps(None if bbox_px is None else [round(float(v), 3) for v in bbox_px])})

        for tag, im, bb, params in variantes.transforms(img, bbox_px, rec["clase"]):
            fname = f"{stem}__{tag}.png"
            cv2.imwrite(str(HOLDOUT / fname), cv2.cvtColor(im, cv2.COLOR_RGB2BGR))
            out_rows.append({**row_base, "transformacion": tag,
                             "archivo": "webcam_sim_holdout/" + fname,
                             "parametros": json.dumps(params),
                             "bbox_gt_px": json.dumps(None if bb is None else [round(float(v), 3) for v in bb])})

    with (V3_ART / "webcam_holdout_manifest.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(out_rows[0].keys()))
        w.writeheader(); w.writerows(out_rows)
    print("holdout generado:", len(out_rows), "archivos (semilla", SEED_HOLDOUT, ")")


if __name__ == "__main__":
    main()