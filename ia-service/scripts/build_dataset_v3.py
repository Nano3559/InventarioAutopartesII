import csv
import hashlib
import json
import random
import shutil
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
IA = ROOT / "ia-service"
V2 = IA / "datasets/processed_v2"
V3 = IA / "datasets/processed_v3"
SEED = 20260923

CLASS_IDS = {"brake_pad": 0, "brake_rotor": 1, "brake_caliper": 2, "alternator": 3, "oil_filter": 4, "air_filter": 5, "radiator": 6, "headlight": 7}
CANVAS = (640, 480)  # webcam-like frame

# Variantes permitidas por clase de train (además del original): cuota POR TIPO para
# garantizar cobertura webcam balanceada. min_area relajado (objetos pequeños válidos).
QUOTA = {"small": 90, "geo": 90, "downsample": 90, "webcam": 90, "photo": 30, "blur_noise": 20, "jpeg": 20}
AUG_CAP_PER_CLASS = sum(QUOTA.values())  # 430

VARIANT_TYPES = ["small", "geo", "downsample", "photo", "blur_noise", "jpeg", "webcam"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows():
    with (V2 / "processed_v2_manifest.csv").open(newline="", encoding="utf-8") as h:
        return list(csv.DictReader(h))


def imread_bgr(path):
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(path)
    return img


def box_bbox(bbox_norm, w, h):
    cx, cy, bw, bh = bbox_norm
    return (cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h


def norm_box(bbox_px, w, h):
    x1, y1, x2, y2 = bbox_px
    if x2 <= x1 or y2 <= y1:
        return None
    return (x1 + x2) / 2 / w, (y1 + y2) / 2 / h, (x2 - x1) / w, (y2 - y1) / h


def valid_box(box_norm, min_area=0.012):
    if box_norm is None:
        return False
    cx, cy, bw, bh = box_norm
    if not (0 <= cx <= 1 and 0 <= cy <= 1):
        return False
    if not (0 < bw <= 1 and 0 < bh <= 1):
        return False
    area = bw * bh
    vis = area >= min_area
    # que la caja no quede cortada por el borde más de un 40%
    x1, y1 = cx - bw / 2, cy - bh / 2
    x2, y2 = cx + bw / 2, cy + bh / 2
    return vis and x1 >= -0.05 and y1 >= -0.05 and x2 <= 1.05 and y2 <= 1.05


def make_canvas(img, bbox_px, scale):
    """Place object scaled on webcam-like canvas; return (canvas, bbox_px) or None."""
    cw, ch = CANVAS
    ih, iw = img.shape[:2]
    nw, nh = max(1, int(round(iw * scale))), max(1, int(round(ih * scale)))
    if nh > ch or nw > cw:
        s2 = min(cw / nw, ch / nh)
        nw, nh = int(round(nw * s2)), int(round(nh * s2))
        scale = scale * s2
    res = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    # fondo: claro, uniforme con leve gradiente/ruido (estilo mostrador limpio)
    rng = np.random.default_rng(int(SEED) ^ 11)
    base = np.full((ch, cw, 3), 235, dtype=np.uint8)
    base = base.astype(np.float32)
    base += rng.normal(0, 4, (ch, cw, 1))
    if rng.random() < 0.5:
        g = np.linspace(0, 10, cw).astype(np.float32)[None, :, None]
        base = base + g
    bg = np.clip(base, 0, 255).astype(np.uint8)
    ox, oy = (cw - nw) // 2, (ch - nh) // 2
    bg[oy:oy + nh, ox:ox + nw] = res
    if bbox_px is not None:
        nb = tuple(v * scale for v in bbox_px)
        return bg, (nb[0] + ox, nb[1] + oy, nb[2] + ox, nb[3] + oy)
    return bg, None


def warp_perspective(img, bbox_px, strength):
    """Perspective: corner displacement ~ strength fraction of dims (offline interpretation)."""
    h, w = img.shape[:2]
    rng = np.random.default_rng(int(SEED) ^ int(strength * 991) ^ 7)
    dx = strength * rng.uniform(0.2, 1.0, 4)
    dy = strength * 0.6 * rng.uniform(0.2, 1.0, 4)
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[dx[0] * w, dy[0] * h],
                      [w - dx[1] * w, dy[1] * h],
                      [w - dx[2] * w, h - dy[2] * h],
                      [dx[3] * w, h - dy[3] * h]])
    H = cv2.getPerspectiveTransform(src, dst)
    out = cv2.warpPerspective(img, H, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    if bbox_px is not None:
        x1, y1, x2, y2 = bbox_px
        pts = np.float32([[x1, y1], [x2, y1], [x2, y2], [x1, y2]]).reshape(-1, 1, 2)
        t = cv2.perspectiveTransform(pts, H).reshape(-1, 2)
        nb = (t[:, 0].min(), t[:, 1].min(), t[:, 0].max(), t[:, 1].max())
        return out, nb
    return out, None


def rotate_shear_translate(img, bbox_px, angle_deg, shear, tx_frac, ty_frac):
    """Rotate (center), shear y translate compuestos; devuelve (canvas, bbox actualizado)."""
    h, w = img.shape[:2]
    cx, cy = w / 2, h / 2
    sh = np.deg2rad(shear)
    R3 = np.vstack([cv2.getRotationMatrix2D((cx, cy), angle_deg, 1.0), [0.0, 0.0, 1.0]])
    S3 = np.float32([[1, np.tan(sh), 0], [0, 1, 0], [0, 0, 1]])
    T3 = np.float32([[1, 0, tx_frac * w], [0, 1, ty_frac * h], [0, 0, 1]])
    M3 = T3 @ S3 @ R3
    out = cv2.warpAffine(img, M3[:2], (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

    if bbox_px is not None:
        x1, y1, x2, y2 = bbox_px
        pts = np.float32([[x1, y1], [x2, y1], [x2, y2], [x1, y2]]).reshape(-1, 2)
        ones = np.ones((pts.shape[0], 1), dtype=np.float32)
        p = np.concatenate([pts, ones], axis=1)
        t = (M3 @ p.T).T[:, :2]
        nb = (t[:, 0].min(), t[:, 1].min(), t[:, 0].max(), t[:, 1].max())
        return out, nb
    return out, None


def downsample_upscale(img, bbox_px, target):
    """Simulate webcam res loss: resize down then back to original size."""
    h, w = img.shape[:2]
    if target >= min(h, w):
        return img, bbox_px
    small = cv2.resize(img, (target, target), interpolation=cv2.INTER_AREA)
    back = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    return back, bbox_px


def hsv_color(img, bbox_px, hd, sv, vv):
    im = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    im[..., 0] = np.clip(im[..., 0] + hd, 0, 179)
    im[..., 1] = np.clip(im[..., 1] * sv, 0, 255)
    im[..., 2] = np.clip(im[..., 2] * vv, 0, 255)
    return cv2.cvtColor(im.astype(np.uint8), cv2.COLOR_HSV2BGR), bbox_px


def blur_noise(img, bbox_px, k, sigma):
    b = cv2.GaussianBlur(img, (k, k), 0)
    if sigma <= 0:
        return b, bbox_px
    rng = np.random.default_rng(int(SEED) ^ k ^ 19)
    noise = rng.normal(0, sigma, b.shape).astype(np.int16)
    return np.clip(b.astype(np.int16) + noise, 0, 255).astype(np.uint8), bbox_px


def jpeg_compress(img, bbox_px, quality):
    ok, enc = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    return cv2.imdecode(enc, cv2.IMREAD_COLOR), bbox_px


def zlib_crc(s):
    import zlib
    return zlib.crc32(s.encode("utf-8"))


def img_fp(im):
    import hashlib
    return hashlib.sha256(np.ascontiguousarray(im).tobytes()).hexdigest()


def build_variant(stem, cls, img, bbox_norm, tag, attempt=0):
    h, w = img.shape[:2]
    bbox_px = box_bbox(bbox_norm, w, h)
    rngvar = np.random.default_rng(((SEED ^ zlib_crc(stem)) & 0xFFFFFFFF) ^ (attempt * 2654435761))

    def norm_after(im, bb, tag2):
        ih, iw = im.shape[:2]
        nb = norm_box(bb, iw, ih)
        if nb is None or not valid_box(nb, min_area=0.012):
            return None
        return im, nb

    if tag == "small":
        scale = float(rngvar.choice([0.70, 0.55, 0.45, 0.35]))
        im, bb = make_canvas(img, bbox_px, scale)
        return norm_after(im, bb, tag)
    if tag == "geo":
        # objeto en canvas a ~65%, luego rot+shear+transleve
        im, bb = make_canvas(img, bbox_px, 0.65)
        angle = float(rngvar.choice([-12, -9, -6, 6, 9, 12]))
        shear = float(rngvar.choice([-7, -4, 4, 7]))
        tx, ty = rngvar.uniform(-0.12, 0.12), rngvar.uniform(-0.10, 0.10)
        im, bb = rotate_shear_translate(im, bb, angle, shear, tx, ty)
        im, bb = warp_perspective(im, bb, strength=0.02)
        return norm_after(im, bb, tag)
    if tag == "downsample":
        im, bb = make_canvas(img, bbox_px, 0.7)
        target = int(rngvar.choice([320, 416, 480]))
        im, bb = downsample_upscale(im, bb, target)
        return norm_after(im, bb, tag)
    if tag == "photo":
        im, bb = make_canvas(img, bbox_px, 0.75)
        style = int(rngvar.integers(0, 3))
        if style == 0:
            im, bb = hsv_color(im, bb, 0, 1.0, float(rngvar.uniform(1.15, 1.4)))
        elif style == 1:
            im, bb = hsv_color(im, bb, 0, 1.0, float(rngvar.uniform(0.55, 0.75)))
        else:
            alpha = float(rngvar.uniform(0.6, 0.85))
            im = cv2.convertScaleAbs(im, alpha=alpha, beta=0)
        return norm_after(im, bb, tag)
    if tag == "blur_noise":
        im, bb = make_canvas(img, bbox_px, 0.75)
        k = int(rngvar.choice([3, 5]))
        sigma = float(rngvar.uniform(2, 7))
        im, bb = blur_noise(im, bb, k, sigma)
        return norm_after(im, bb, tag)
    if tag == "jpeg":
        im, bb = make_canvas(img, bbox_px, 0.75)
        q = int(rngvar.choice([40, 50, 60, 70]))
        im, bb = jpeg_compress(im, bb, q)
        return norm_after(im, bb, tag)
    if tag == "webcam":
        # compuesta con aleatoriedad controlada (no siempre máxima)
        scale = float(rngvar.choice([0.35, 0.45, 0.55, 0.70]))
        im, bb = make_canvas(img, bbox_px, scale)
        im, bb = warp_perspective(im, bb, strength=float(rngvar.uniform(0.01, 0.025)))
        im, bb = downsample_upscale(im, bb, int(rngvar.choice([320, 416, 480])))
        im, bb = blur_noise(im, bb, 5, float(rngvar.uniform(1.5, 5)))
        im = cv2.convertScaleAbs(im.astype(np.float32) * float(rngvar.uniform(0.75, 1.15))).clip(0, 255).astype(np.uint8)
        im, bb = jpeg_compress(im, bb, int(rngvar.choice([40, 55, 70])))
        return norm_after(im, bb, tag)
    return None


def main():
    if V3.exists():
        shutil.rmtree(V3)
    for sub in ["images/train", "labels/train", "images/val", "labels/val", "images/test", "labels/test"]:
        (V3 / sub).mkdir(parents=True, exist_ok=True)

    rows = read_rows()
    records = []
    counters = defaultdict(lambda: defaultdict(int))  # cls -> tag -> count
    seen_ids = set()  # sha256 por imagen
    seen_fps = set()  # fingerprint de variantes generadas (evita duplicados byte-idénticos)

    # 1) copiar todos los originales V2 tal cual (mismo split)
    for row in rows:
        src_img = ROOT / row["processed_image"]
        src_lbl = ROOT / row["processed_label"]
        if not src_img.exists() or not src_lbl.exists():
            continue
        split = row["split"]
        stem = Path(row["processed_image"]).stem
        # mantener naming: prefijo v3solo en train/v3 en val/test? Simplemente conservar
        # el nombre salvo colisiones
        dst_img = V3 / "images" / split / f"{stem}.jpg"
        dst_lbl = V3 / "labels" / split / f"{stem}.txt"
        n = 1
        while dst_img.exists():
            dst_img = V3 / "images" / split / f"{stem}__{n}.jpg"
            dst_lbl = V3 / "labels" / split / f"{stem}__{n}.txt"
            n += 1
        shutil.copy2(src_img, dst_img)
        shutil.copy2(src_lbl, dst_lbl)
        nrow = dict(row)
        nrow["processed_image"] = str(dst_img.relative_to(ROOT)).replace("\\", "/")
        nrow["processed_label"] = str(dst_lbl.relative_to(ROOT)).replace("\\", "/")
        nrow["augmentation"] = ""
        nrow["v3_domain"] = row["domain"]
        records.append(nrow)
        seen_ids.add(sha256(dst_img))
        seen_fps.add(img_fp(imread_bgr(src_img)))

    # 2) generación de variantes SOLO sobre train, cuota por tipo y por clase
    # (las filas multi-clase del manifest V2 se copian como originales pero no se aumentan,
    #  porque transformar el canvas rompería las etiquetas de los demás objetos)
    train_rows = [r for r in records if r["split"] == "train"]
    raw_count = len(records)
    generated = 0
    rejected = {t: 0 for t in VARIANT_TYPES}
    single_cls_rows = [r for r in train_rows if r["target_class"] in CLASS_IDS]
    multi_cls_rows = len(train_rows) - len(single_cls_rows)

    for cls in CLASS_IDS:
        class_rows = sorted(
            [r for r in single_cls_rows if r["target_class"] == cls],
            key=lambda r: zlib_crc(r["processed_image"]),
        )
        if not class_rows:
            continue
        for tag, quota in QUOTA.items():
            rng_cycle = random.Random((SEED ^ (CLASS_IDS[cls] * 1009) ^ zlib_crc(tag)) & 0xFFFFFFFF)
            start = rng_cycle.randrange(len(class_rows))
            order = class_rows[start:] + class_rows[:start]
            produced = 0
            i = 0
            max_attempts = len(order) * 4
            while produced < quota and i < max_attempts:
                row = order[i % len(order)]
                src_img = ROOT / row["processed_image"]
                img = imread_bgr(src_img)
                lbl = (ROOT / row["processed_label"]).read_text(encoding="utf-8").splitlines()
                bbox_norm = None
                for ln in lbl:
                    p = ln.split()
                    if len(p) == 5 and int(p[0]) == CLASS_IDS[cls]:
                        bbox_norm = (float(p[1]), float(p[2]), float(p[3]), float(p[4]))
                        break
                if bbox_norm is None:
                    i += 1
                    continue
                stem = Path(src_img).stem
                attempt = i // len(order)
                out = build_variant(stem, cls, img, bbox_norm, tag, attempt=attempt)
                i += 1
                if out is None:
                    rejected[tag] += 1
                    continue
                im, nb = out
                fp = img_fp(im)
                if fp in seen_fps:
                    rejected[tag] += 1
                    continue
                seen_fps.add(fp)
                name = f"{stem}__v3_{tag}__{generated:05d}.jpg"
                dst_img = V3 / "images" / "train" / name
                dst_lbl = V3 / "labels" / "train" / name.replace(".jpg", ".txt")
                ok = cv2.imwrite(str(dst_img), im)
                if not ok:
                    rejected[tag] += 1
                    continue
                dst_lbl.write_text(f"{CLASS_IDS[cls]} {nb[0]:.8f} {nb[1]:.8f} {nb[2]:.8f} {nb[3]:.8f}\n", encoding="utf-8")
                records.append({
                    "processed_image": str(dst_img.relative_to(ROOT)).replace("\\", "/"),
                    "processed_label": str(dst_lbl.relative_to(ROOT)).replace("\\", "/"),
                    "split": "train",
                    "target_class": cls,
                    "target_class_id": CLASS_IDS[cls],
                    "source_dataset": "V3_WEBCAM_AUGMENTED",
                    "source_image": row["processed_image"],
                    "source_group_id": sha256(src_img),
                    "annotation_origin": "V3_WEBCAM_AUG",
                    "is_synthetic": "true",
                    "license": row["license"],
                    "source_version": "v3",
                    "source_label": "",
                    "domain": "webcam_aug",
                    "bbox_method": row["bbox_method"],
                    "augmentation": tag,
                    "v3_domain": "webcam_aug",
                })
                counters[cls][tag] += 1
                produced += 1
                generated += 1
                seen_ids.add(sha256(dst_img))

    fields = list(records[0].keys())
    with (V3 / "processed_v3_manifest.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(records)

    (V3 / "dataset.yaml").write_text(
        "path: .\ntrain: images/train\nval: images/val\ntest: images/test\n\nnc: 8\nnames:\n  0: brake_pad\n  1: brake_rotor\n  2: brake_caliper\n  3: alternator\n  4: oil_filter\n  5: air_filter\n  6: radiator\n  7: headlight\n", encoding="utf-8")

    # 3) leakage: exact cross-split
    exact = defaultdict(list)
    for r in records:
        exact[sha256(ROOT / r["processed_image"])].append((r["split"], Path(r["processed_image"]).name))
    exact_cross = {k: v for k, v in exact.items() if len({s for s, _ in v}) > 1}
    dup_rows = [(names, h) for h, names in exact.items() if len(names) > 1]

    per_class = defaultdict(lambda: defaultdict(int))
    for r in records:
        per_class[r["target_class"]][r["split"]] += 1

    counts_by_aug = defaultdict(int)
    for r in records:
        counts_by_aug[r.get("augmentation") or "original"] += 1

    report = {
        "quota_por_tipo": QUOTA,
        "v2_rows": raw_count,
        "v3_total": len(records),
        "train": sum(1 for r in records if r["split"] == "train"),
        "val": sum(1 for r in records if r["split"] == "val"),
        "test": sum(1 for r in records if r["split"] == "test"),
        "train_originales_v2": len([1 for r in records if r["split"] == "train" and not r.get("augmentation")]),
        "train_multi_clase_no_augmentadas": multi_cls_rows,
        "augmentadas": generated,
        "air_filter_en_train": sum(1 for r in records if r["split"] == "train" and r["target_class"] == "air_filter"),
        "rejected_por_tipo": rejected,
        "por_tipo": sorted((k, v) for k, v in counts_by_aug.items()),
        "por_clase_split": {k: dict(v) for k, v in per_class.items()},
        "aug_por_clase": {k: dict(v) for k, v in counters.items()},
        "exact_cross_split": len(exact_cross),
        "duplicates_exact": len(dup_rows),
        "duplicates_detalle": dup_rows[:10],
    }
    (V3 / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()