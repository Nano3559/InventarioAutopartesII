import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from diagnostico_v2_common import (
    ART, CLASSES, CONF_TECNICO, ROOT, SEED, UMBRAL_BACKEND, V2_MODEL, predict_v2,
)


def main():
    with (ART / "variantes_manifest.csv").open(newline="", encoding="utf-8") as h:
        recs = list(csv.DictReader(h))
    model = YOLO(V2_MODEL)
    out_rows = []
    for rec in recs:
        p = ROOT / "ia-service/artifacts/diagnostico_v2" / rec["archivo"]
        if not p.exists():
            continue
        dets = predict_v2(model, p)
        top = dets[0] if dets else None
        gt = CLASSES.index(rec["clase"])
        detectada = bool(dets)
        correcta = bool(top and top["cls"] == gt)
        any_correct = any(d["cls"] == gt for d in dets)
        bbox_gt = json.loads(rec["bbox_gt_px"]) if rec["bbox_gt_px"] != "" else None
        out_rows.append({
            "imagen": rec["archivo"].split("/")[-1],
            "ruta_original": rec["ruta_original"],
            "clase_real": rec["clase"],
            "transformacion": rec["transformacion"],
            "parametros": rec["parametros"],
            "prediccion": top["clase"] if top else None,
            "confianza": top["conf"] if top else None,
            "bbox": json.dumps(top["xyxyn"]) if top else None,
            "detectada": detectada,
            "correcta_top": correcta,
            "correcta_any": any_correct,
            "sobre_055": bool(top and top["conf"] >= UMBRAL_BACKEND),
            "n_detecciones": len(dets),
            "bbox_gt_px": rec["bbox_gt_px"],
        })

    with (ART / "resultados_robustez.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(out_rows[0].keys()))
        w.writeheader(); w.writerows(out_rows)

    # --- Resumen por transformacion ---
    por_tx = defaultdict(list)
    for r in out_rows:
        por_tx[r["transformacion"]].append(r)
    resumen = []
    for tx in sorted(por_tx):
        g = por_tx[tx]
        orig_conf = {}
        for r in g:
            stem = r["imagen"].rsplit("__", 1)[0]
            orig_conf.setdefault(stem, None)
        # caida respecto original: usar manifest_seleccion conf_original
        confs_orig = {}
        with (ART / "manifest_seleccion_v2.csv").open(newline="", encoding="utf-8") as h:
            for rr in csv.DictReader(h):
                confs_orig[Path(rr["ruta"]).stem] = rr["conf_original"]
        caidas = []
        for r in g:
            stem = r["imagen"].rsplit("__", 1)[0]
            co = confs_orig.get(stem)
            if co and r["confianza"]:
                caidas.append(float(co) - r["confianza"])
        correctas = sum(1 for r in g if r["correcta_top"])
        incorrectas = sum(1 for r in g if r["detectada"] and not r["correcta_top"])
        vacias = sum(1 for r in g if not r["detectada"])
        confs = [r["confianza"] for r in g if r["confianza"] is not None]
        above = sum(1 for r in g if r["sobre_055"])
        resumen.append({
            "transformacion": tx,
            "cantidad": len(g),
            "correctas": correctas,
            "incorrectas": incorrectas,
            "vacias": vacias,
            "sobre_umbr_055": above,
            "conf_media": round(sum(confs) / len(confs), 4) if confs else None,
            "caida_media": round(sum(caidas) / len(caidas), 4) if caidas else None,
        })
    with (ART / "resumen_robustez.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(resumen[0].keys()))
        w.writeheader(); w.writerows(resumen)
    print(json.dumps(resumen, indent=2))


if __name__ == "__main__":
    main()