import csv
import json
from pathlib import Path

import cv2
import numpy as np

from diagnostico_v2_common import ART, CLASSES, CONF_TECNICO, ROOT, SEED, read_labels, imread

RNG = np.random.default_rng(SEED)
OUT = ART / "variantes_640x480"


def warp_with_H(img, H, bbox_px, w, h):
    out = cv2.warpPerspective(img, H, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    if bbox_px is not None:
        x1, y1, x2, y2 = bbox_px
        pts = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32).reshape(-1, 1, 2)
        t = cv2.perspectiveTransform(pts, H).reshape(-1, 2)
        bx1, by1 = t[:, 0].min(), t[:, 1].min()
        bx2, by2 = t[:, 0].max(), t[:, 1].max()
        return out, (bx1, by1, bx2, by2)
    return out, None


def to_px(bbox_norm, w, h):
    cx, cy, bw, bh = bbox_norm
    return (cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h


def rescale_640x480(img, bbox_px, scale=None, canvas=(640, 480)):
    cw, ch = canvas
    ih, iw = img.shape[:2]
    sc = scale if scale else min(cw / iw, ch / ih) * 0.92
    nw, nh = int(round(iw * sc)), int(round(ih * sc))
    if nh > ch or nw > cw:
        sc2 = min(cw / nw, ch / nh)
        nw, nh = int(round(nw * sc2)), int(round(nh * sc2))
        sc = sc * sc2
    res = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_LINEAR)
    out = np.full((ch, cw, 3), 128, dtype=np.uint8)
    ox, oy = (cw - nw) // 2, (ch - nh) // 2
    out[oy:oy + nh, ox:ox + nw] = res
    if bbox_px is not None:
        nb = tuple(v * sc for v in bbox_px)
        return out, (nb[0] + ox, nb[1] + oy, nb[2] + ox, nb[3] + oy)
    return out, None


def make_H_warp(img, k, bbox_px):
    h, w = img.shape[:2]
    rng = np.random.default_rng(int(SEED) ^ (int(k * 7919) % 2 ** 31))
    dx = 0.03 * k * rng.uniform(-0.4, 0.6, 4)
    dy = 0.03 * k * rng.uniform(-0.4, 0.6, 4)
    src = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
    dst = np.float32([[dx[0] * w, dy[0] * h], [w - 1 + dx[1] * w, dy[1] * h],
                      [w - 1 + dx[2] * w, h - 1 + dy[2] * h], [dx[3] * w, h - 1 + dy[3] * h]])
    H = cv2.getPerspectiveTransform(src, dst)
    return warp_with_H(img, H, bbox_px, w, h)


def transforms(img, bbox_px, label_tag):
    res = []
    # A resize/canvas 640x480
    im, bb = rescale_640x480(img, bbox_px)
    res.append(("A_resize_640x480", im, bb, {"canvas": "640x480", "scale_fit": True}))
    # B perspectiva leve
    im, bb = make_H_warp(img, 1, bbox_px)
    res.append(("B_perspectiva_leve", im, bb, {}))
    # C perspectiva moderada
    im, bb = make_H_warp(img, 2, bbox_px)
    res.append(("C_perspectiva_moderada", im, bb, {}))
    # D blur leve
    im = cv2.GaussianBlur(img, (3, 3), 0)
    res.append(("D_blur_leve", im, bbox_px, {"ksize": 3}))
    # E blur moderado
    im = cv2.GaussianBlur(img, (9, 9), 0)
    res.append(("E_blur_moderado", im, bbox_px, {"ksize": 9}))
    # F contraste reducido
    im = cv2.convertScaleAbs(img, alpha=0.6, beta=0)
    res.append(("F_contraste", im, bbox_px, {"alpha": 0.6}))
    # G1 exposicion aumento
    im = cv2.convertScaleAbs(img.astype(np.float32) * 1.5).clip(0, 255).astype(np.uint8)
    res.append(("G1_exposicion_alta", im, bbox_px, {"mul": 1.5}))
    # G2 exposicion reduccion
    im = cv2.convertScaleAbs(img.astype(np.float32) * 0.5).clip(0, 255).astype(np.uint8)
    res.append(("G2_exposicion_baja", im, bbox_px, {"mul": 0.5}))
    # H ruido sensor moderado (gaussiano)
    noise = (RNG.normal(0, 10, img.shape)).astype(np.int16)
    im = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    res.append(("H_ruido_sensor", im, bbox_px, {"sigma": 10}))
    # I compresion JPEG
    ok, enc = cv2.imencode(".jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), 35])
    im = cv2.cvtColor(cv2.imdecode(enc, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    res.append(("I_jpeg_q35", im, bbox_px, {"quality": 35}))
    # J escala dentro del frame (objeto mas pequeno/mas lejos)
    im, bb = rescale_640x480(img, bbox_px, scale=0.45)
    res.append(("J_escala_45", im, bb, {"scale": 0.45, "canvas": "640x480"}))
    # K combinacion realista tipo webcam
    im, bb = rescale_640x480(img, bbox_px, scale=0.7)
    im, bb = make_H_warp(im, 1, bb)
    im = cv2.GaussianBlur(im, (5, 5), 0)
    im = cv2.convertScaleAbs(im.astype(np.float32) * 0.85).clip(0, 255).astype(np.uint8)
    noise = (RNG.normal(0, 6, im.shape)).astype(np.int16)
    im = np.clip(im.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    ok, enc = cv2.imencode(".jpg", cv2.cvtColor(im, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), 60])
    im = cv2.cvtColor(cv2.imdecode(enc, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    res.append(("K_webcam_realista", im, bb, {"scale": 0.7, "persp": "leve", "blur": 5, "contrast": 0.85, "noise": 6, "jpeg": 60}))
    return res


def main():
    with (ART / "manifest_seleccion_v2.csv").open(newline="", encoding="utf-8") as h:
        recs = list(csv.DictReader(h))
    OUT.mkdir(parents=True, exist_ok=True)
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
        bbox_px = to_px(bbox_norm, w, h) if bbox_norm else None
        stem = Path(rec["ruta"]).stem
        for tag, im, bb, params in transforms(img, bbox_px, rec["clase"]):
            fname = f"{stem}__{tag}.png"
            cv2.imwrite(str(OUT / fname), cv2.cvtColor(im, cv2.COLOR_RGB2BGR))
            out_rows.append({
                "ruta_original": rec["ruta"], "clase": rec["clase"], "split": rec["split"],
                "transformacion": tag, "parametros": json.dumps(params), "archivo": "variantes_640x480/" + fname,
                "bbox_gt_px": json.dumps(None if bb is None else [round(float(v), 3) for v in bb]),
                "semilla": SEED,
            })
    with (ART / "variantes_manifest.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(out_rows[0].keys()))
        w.writeheader(); w.writerows(out_rows)
    print("variantes generadas:", len(out_rows))


if __name__ == "__main__":
    main()