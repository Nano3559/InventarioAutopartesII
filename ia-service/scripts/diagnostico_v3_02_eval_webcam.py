import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from ultralytics import YOLO

from diagnostico_v2_common import (
    ART, CLASSES, CONF_TECNICO, ROOT, UMBRAL_BACKEND, V2_MODEL, predict_v2,
)

V3_ART = ROOT / "ia-service/artifacts/diagnostico_v3"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default=str(V2_MODEL))
    ap.add_argument("--salida", default="webcam_holdout_resultados.csv")
    args = ap.parse_args()

    with (V3_ART / "webcam_holdout_manifest.csv").open(newline="", encoding="utf-8") as h:
        recs = list(csv.DictReader(h))
    model = YOLO(args.modelo)
    out_rows = []
    for rec in recs:
        p = ROOT / "ia-service/artifacts/diagnostico_v3" / rec["archivo"]
        if not p.exists():
            continue
        dets = predict_v2(model, p)
        top = dets[0] if dets else None
        gt = CLASSES.index(rec["clase"])
        out_rows.append({
            "imagen": rec["archivo"].split("/")[-1],
            "ruta_original": rec["ruta_original"],
            "clase_real": rec["clase"],
            "transformacion": rec["transformacion"],
            "parametros": rec["parametros"],
            "prediccion": top["clase"] if top else None,
            "confianza": top["conf"] if top else None,
            "bbox": json.dumps(top["xyxyn"]) if top else None,
            "detectada": bool(dets),
            "correcta_top": bool(top and top["cls"] == gt),
            "sobre_055": bool(top and top["conf"] >= UMBRAL_BACKEND),
            "n_detecciones": len(dets),
            "bbox_gt_px": rec["bbox_gt_px"],
        })

    salida = V3_ART / args.salida
    with salida.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(out_rows[0].keys()))
        w.writeheader(); w.writerows(out_rows)

    orig_conf = {}
    for r in out_rows:
        if r["transformacion"] == "ORIGINAL":
            for rr in out_rows:
                if rr["imagen"].rsplit("__", 1)[0] == r["imagen"].rsplit("__", 1)[0]:
                    orig_conf[Path(rr["imagen"]).stem] = r["confianza"]

    por_tx = defaultdict(list)
    for r in out_rows:
        por_tx[r["transformacion"]].append(r)
    resumen = []
    for tx in sorted(por_tx):
        g = por_tx[tx]
        caidas = []
        for r in g:
            oc = orig_conf.get(Path(r["imagen"]).stem)
            if oc is not None and r["confianza"] is not None:
                caidas.append(oc - r["confianza"])
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
    resumen_name = args.salida.replace("resultados", "resumen")
    with (V3_ART / resumen_name).open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(resumen[0].keys()))
        w.writeheader(); w.writerows(resumen)
    print(json.dumps(resumen, indent=2))


if __name__ == "__main__":
    main()