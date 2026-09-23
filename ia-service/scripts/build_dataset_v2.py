import csv
import hashlib
import json
import random
import shutil
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

ROOT = Path(__file__).resolve().parents[2]
IA = ROOT / "ia-service"
PROCESSED = IA / "datasets/processed"
V2 = IA / "datasets/processed_v2"
KAGGLE = IA / "datasets/raw/kaggle-car-parts"
SYNTH_SRC_MANIFEST = IA / "datasets/synthetic/manifests/synthetic_manifest.csv"
SEED = 20260922

CLASS_IDS = {"brake_pad": 0, "brake_rotor": 1, "brake_caliper": 2, "alternator": 3, "oil_filter": 4, "air_filter": 5, "radiator": 6, "headlight": 7}

KAGGLE_CLASS = {"ALTERNATOR": "alternator", "RADIATOR": "radiator", "HEADLIGHTS": "headlight"}
KAGGLE_BRAKES = {"BRAKE PAD": "brake_pad", "BRAKE ROTOR": "brake_rotor", "BRAKE CALIPER": "brake_caliper", "OIL FILTER": "oil_filter"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_synthetic_sources():
    sources = set()
    with SYNTH_SRC_MANIFEST.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            sources.add((Path(row["source_image"]), row["source_group_id"]))
    return sources


def read_processed_rows():
    with (PROCESSED / "processed_manifest.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def copy_base():
    for split in ["train", "val", "test"]:
        src_img = PROCESSED / "images" / split
        dst_img = V2 / "images" / split
        src_lbl = PROCESSED / "labels" / split
        dst_lbl = V2 / "labels" / split
        dst_img.mkdir(parents=True, exist_ok=True)
        dst_lbl.mkdir(parents=True, exist_ok=True)
        for f in src_img.glob("*.jpg"):
            shutil.copy2(f, dst_img / f.name)
        for f in src_lbl.glob("*.txt"):
            shutil.copy2(f, dst_lbl / f.name)


def compute_mask_box(image_path, session, max_dim=640):
    """rembg u2net -> alpha -> bbox (normalized in original coords). Returns (cx,cy,w,h,area,status,note)."""
    from rembg import remove

    image = Image.open(image_path).convert("RGB")
    ow, oh = image.size
    scale = min(1.0, max_dim / max(ow, oh))
    if scale < 1.0:
        work = image.resize((max(1, int(ow * scale)), max(1, int(oh * scale))), Image.Resampling.LANCZOS)
    else:
        work = image
    cutout = remove(work, session=session, alpha_matting=False)
    alpha = cutout.getchannel("A")
    ww, wh = alpha.size
    arr = np.array(alpha)
    area = float(np.count_nonzero(arr > 20) / (ww * wh))
    bbox = alpha.getbbox()
    if bbox is None:
        return None, None, "REJECTED", "empty_mask"
    x1, y1, x2, y2 = bbox
    box_w = (x2 - x1) / ww
    box_h = (y2 - y1) / wh
    box_area = box_w * box_h
    if area < 0.02 or box_area < 0.04:
        return None, None, "REJECTED", f"foreground_too_small area={area:.4f} box={box_area:.4f}"
    if area > 0.90 or box_area > 0.95:
        # Piece (virtually) fills the frame -> full-image fallback is appropriate.
        return None, None, "FULL_IMAGE", f"foreground_too_large area={area:.4f} box={box_area:.4f}"
    cx, cy, bw, bh = ((x1 + x2) / 2) / ww, ((y1 + y2) / 2) / wh, box_w, box_h
    return [cx, cy, bw, bh], area, "ACCEPTED", f"mask_area={area:.4f}"


def full_image_box(image_path):
    image = Image.open(image_path)
    w, h = image.size
    return [0.5, 0.5, 1.0, 1.0], None, "FULL_IMAGE", "full_frame_piece"


def build_product(split_pool, source_with_group, session):
    """split_pool: list of (class_name, kaggle_folder, split_name, Path)"""
    records = []
    rejected = []
    for index, (class_name, folder, split, img_path) in enumerate(split_pool):
        group = sha256(img_path)
        box, area, status, note = compute_mask_box(img_path, session)
        if status == "REJECTED":
            rejected.append({"class": class_name, "split": split, "source": str(img_path.relative_to(ROOT)), "reason": note})
            continue
        if status == "FULL_IMAGE":
            box, area, status, note = full_image_box(img_path)
            bbox_method = "full_image_fallback"
        else:
            bbox_method = "mask"
        if not (0 <= box[0] <= 1 and 0 <= box[1] <= 1 and 0 < box[2] <= 1 and 0 < box[3] <= 1):
            rejected.append({"class": class_name, "split": split, "source": str(img_path.relative_to(ROOT)), "reason": "invalid_box"})
            continue
        name = f"kaggle_prod__{class_name}__{split}__{img_path.stem}"
        image_dst = V2 / "images" / split / f"{name}.jpg"
        label_dst = V2 / "labels" / split / f"{name}.txt"
        shutil.copy2(img_path, image_dst)
        label_dst.write_text(f"{CLASS_IDS[class_name]} {box[0]:.8f} {box[1]:.8f} {box[2]:.8f} {box[3]:.8f}\n", encoding="utf-8")
        records.append({
            "processed_image": str(image_dst.relative_to(ROOT)).replace("\\", "/"),
            "processed_label": str(label_dst.relative_to(ROOT)).replace("\\", "/"),
            "split": split,
            "target_class": class_name,
            "target_class_id": CLASS_IDS[class_name],
            "source_dataset": "gpiosenka/car-parts-40-classes",
            "source_image": str(img_path.relative_to(ROOT)).replace("\\", "/"),
            "source_group_id": group,
            "annotation_origin": "PRODUCT_AUTO_MASK_TO_BOX" if bbox_method == "mask" else "PRODUCT_FULL_IMAGE_FALLBACK",
            "is_synthetic": "false",
            "license": "Apache-2.0",
            "source_version": "v3",
            "source_label": "",
            "domain": "product",
            "bbox_method": bbox_method,
        })
    return records, rejected


def generate_v2_synthetics(class_list, n_per_class=50):
    """Moderate synthetic variants for alt/rad/head from Kaggle TRAIN only. Reuses local_background/transform."""
    from rembg import new_session, remove

    session = new_session("u2net")
    CANVAS = (224, 224)
    records = []
    rng = random.Random(SEED + 7)

    def local_background(index, size=CANVAS):
        width, height = size
        rr = np.random.default_rng(SEED + index * 31)
        style = index % 6
        colors = [(232, 232, 232), (207, 220, 232), (218, 207, 190), (52, 62, 73), (211, 229, 211), (205, 195, 178)]
        base = np.zeros((height, width, 3), dtype=np.uint8)
        base[:] = np.array(colors[style], dtype=np.uint8)
        if style in (1, 2, 4, 5):
            noise = rr.normal(0, 5, (height, width, 1))
            base = np.clip(base.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        if style == 3:
            for y in range(0, height, 18):
                base[y : y + 2] = np.clip(base[y : y + 2].astype(np.int16) - 12, 0, 255)
        if style == 5:
            for x in range(0, width, 24):
                base[:, x : x + 2] = np.clip(base[:, x : x + 2].astype(np.int16) - 10, 0, 255)
        return Image.fromarray(base, "RGB")

    rejected = []
    for class_name in class_list:
        folder = KAGGLE / "train" / {"alternator": "ALTERNATOR", "radiator": "RADIATOR", "headlight": "HEADLIGHTS"}[class_name]
        sources = sorted(folder.glob("*.jpg"))
        rng.shuffle(sources)
        cuts = []
        for src in sources[:40]:
            image = Image.open(src).convert("RGBA")
            cutout = remove(image, session=session, alpha_matting=False)
            alpha = cutout.getchannel("A")
            arr = np.array(alpha)
            area = float(np.count_nonzero(arr > 20) / (cutout.width * cutout.height))
            bbox = alpha.getbbox()
            if not bbox or area < 0.02 or area > 0.92:
                rejected.append({"class": class_name, "source": src.name, "reason": "mask_fail"})
                continue
            cuts.append(cutout)
        if not cuts:
            rejected.append({"class": class_name, "source": "ALL", "reason": "no_cutouts"})
            continue
        for i in range(n_per_class):
            cut = cuts[i % len(cuts)]
            scales = [0.55, 0.62, 0.7, 0.78, 0.6, 0.66, 0.74, 0.82, 0.58, 0.8]
            angles = [-12, -6, 0, 6, 12, -9, 3, 9, -3, 0]
            sc = scales[i % len(scales)]
            ang = angles[i % len(angles)]
            tr = cut.resize((max(1, int(cut.width * sc)), max(1, int(cut.height * sc))), Image.Resampling.LANCZOS)
            tr = tr.rotate(ang, expand=True, resample=Image.Resampling.BICUBIC)
            maxw, maxh = int(CANVAS[0] * 0.9), int(CANVAS[1] * 0.9)
            if tr.width > maxw or tr.height > maxh:
                sh = min(maxw / tr.width, maxh / tr.height)
                tr = tr.resize((int(tr.width * sh), int(tr.height * sh)), Image.Resampling.LANCZOS)
            bg = local_background(i + CLASS_IDS[class_name] * 1000)
            x = rng.randint(6, max(6, CANVAS[0] - tr.width - 6))
            y = rng.randint(6, max(6, CANVAS[1] - tr.height - 6))
            comp = bg.convert("RGBA")
            comp.alpha_composite(tr, (x, y))
            alpha = Image.new("L", CANVAS, 0)
            ta = tr.getchannel("A")
            alpha.paste(ta, (x, y), ta)
            bbox = alpha.getbbox()
            if not bbox:
                continue
            x1, y1, x2, y2 = bbox
            cx, cy = (x1 + x2) / 2 / CANVAS[0], (y1 + y2) / 2 / CANVAS[1]
            bw, bh = (x2 - x1) / CANVAS[0], (y2 - y1) / CANVAS[1]
            if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 < bw <= 1 and 0 < bh <= 1):
                continue
            name = f"v2synth__{class_name}__{i + 1:04d}.jpg"
            image_dst = V2 / "images" / "train" / name
            label_dst = V2 / "labels" / "train" / name.replace(".jpg", ".txt")
            comp.convert("RGB").save(image_dst, quality=95)
            label_dst.write_text(f"{CLASS_IDS[class_name]} {cx:.8f} {cy:.8f} {bw:.8f} {bh:.8f}\n", encoding="utf-8")
            records.append({
                "processed_image": str(image_dst.relative_to(ROOT)).replace("\\", "/"),
                "processed_label": str(label_dst.relative_to(ROOT)).replace("\\", "/"),
                "split": "train",
                "target_class": class_name,
                "target_class_id": CLASS_IDS[class_name],
                "source_dataset": "gpiosenka/car-parts-40-classes",
                "source_image": "SYNTHETIC_PRODUCT_VARIANTS",
                "source_group_id": sha256(image_dst),
                "annotation_origin": "SYNTHETIC_MASK_TO_BOX",
                "is_synthetic": "true",
                "license": "NONE_LOCAL_GENERATED",
                "source_version": "v3",
                "source_label": "",
                "domain": "synthetic",
                "bbox_method": "mask_synthetic",
            })
    return records, rejected


def dedupe_check():
    """Exact & near-duplicate (dhash) detection across final V2 splits."""
    from PIL import Image

    def dhash(path, size=8):
        im = Image.open(path).convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
        px = list(im.getdata())
        bits = []
        for y in range(size):
            for x in range(size):
                bits.append(px[(y) * (size + 1) + x] > px[y * (size + 1) + x + 1])
        return int("".join("1" if b else "0" for b in bits), 2)

    exact = defaultdict(list)
    near = defaultdict(list)
    for split in ["train", "val", "test"]:
        for f in sorted((V2 / "images" / split).glob("*.jpg")):
            exact[sha256(f)].append((split, f.name))
            near[dhash(f)].append((split, f.name))
    exact_cross = {k: v for k, v in exact.items() if len({s for s, _ in v}) > 1}
    near_cross = []
    hashes = sorted(near)
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            if (hashes[i] ^ hashes[j]).bit_count() <= 1:
                a, b = near[hashes[i]], near[hashes[j]]
                if {s for s, _ in a} != {s for s, _ in b} or len({s for s, _ in a + b}) > 1:
                    near_cross.append((a, b))
    return {"exact_cross": exact_cross, "near_cross": near_cross}


def purge_cross_split_near_dupes():
    """Remove from V2 val/test any image whose near-duplicate already lives in train (pre-existing base leak)."""
    from PIL import Image

    def dhash(path, size=8):
        im = Image.open(path).convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
        px = list(im.getdata())
        bits = []
        for y in range(size):
            for x in range(size):
                bits.append(px[(y) * (size + 1) + x] > px[y * (size + 1) + x + 1])
        return int("".join("1" if b else "0" for b in bits), 2)

    train_hashes = [dhash(f) for f in (V2 / "images" / "train").glob("*.jpg")]
    removed = []
    for split in ["val", "test"]:
        for f in list((V2 / "images" / split).glob("*.jpg")):
            h = dhash(f)
            if any((h ^ th).bit_count() <= 1 for th in train_hashes):
                label = V2 / "labels" / split / f.with_suffix(".txt").name
                f.unlink(missing_ok=True)
                label.unlink(missing_ok=True)
                removed.append((split, f.name))
    return removed


def main():
    t0 = time.time()
    for sub in ["images/train", "images/val", "images/test", "labels/train", "labels/val", "labels/test"]:
        (V2 / sub).mkdir(parents=True, exist_ok=True)

    copy_base()
    base_rows = read_processed_rows()
    for row in base_rows:
        row["domain"] = "synthetic" if row["is_synthetic"] == "true" else "context"
        row["bbox_method"] = "mask_synthetic" if row["is_synthetic"] == "true" else "original"
        row["processed_image"] = row["processed_image"].replace("datasets/processed", "datasets/processed_v2")
        row["processed_label"] = row["processed_label"].replace("datasets/processed", "datasets/processed_v2")

    pool = []
    for folder, class_name in KAGGLE_CLASS.items():
        for kg_split, v2_split in [("train", "train"), ("valid", "val"), ("test", "test")]:
            for f in sorted((KAGGLE / kg_split / folder).glob("*.jpg")):
                pool.append((class_name, folder, v2_split, f))

    # Brakes + oil_filter: ONLY val/test product, restricted to CLEAN images (not synthetic sources).
    synth_src = load_synthetic_sources()
    clean_pool = []
    for folder, class_name in KAGGLE_BRAKES.items():
        for split in ["valid", "test"]:
            for f in sorted((KAGGLE / split / folder).glob("*.jpg")):
                rel = Path("ia-service/datasets/raw/kaggle-car-parts") / split / folder / f.name
                if (rel, None) in synth_src or any(src == rel for src, _ in synth_src):
                    continue
                final_split = "val" if split == "valid" else "test"
                clean_pool.append((class_name, folder, final_split, f))

    from rembg import new_session as _new_session
    _session = _new_session("u2net")
    product_rows, rejected_product = build_product(pool, synth_src, _session)
    extra_rows, extra_rejected = build_product(clean_pool, synth_src, _session)
    product_rows += extra_rows
    rejected_product += extra_rejected
    synth_rows, rejected_synth = generate_v2_synthetics(["alternator", "radiator", "headlight"], n_per_class=50)

    records = base_rows + product_rows + synth_rows
    removed = purge_cross_split_near_dupes()
    removed_names = {f"{split}/{name}" for split, name in removed}
    records = [r for r in records if not any(rn in r["processed_image"] for rn in removed_names)]
    fields = list(base_rows[0].keys())
    with (V2 / "processed_v2_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)

    (V2 / "dataset.yaml").write_text("path: .\ntrain: images/train\nval: images/val\ntest: images/test\n\nnc: 8\nnames:\n  0: brake_pad\n  1: brake_rotor\n  2: brake_caliper\n  3: alternator\n  4: oil_filter\n  5: air_filter\n  6: radiator\n  7: headlight\n", encoding="utf-8")

    with (V2 / "rejected_bboxes.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["class", "split", "source", "reason"])
        writer.writeheader()
        writer.writerows(rejected_product + rejected_synth)

    dedupe = dedupe_check()
    counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for r in records:
        counts[r["target_class"]][r["split"]][r["domain"]] += 1

    report = {
        "elapsed_s": round(time.time() - t0, 1),
        "total_records": len(records),
        "base_records": len(base_rows),
        "product_records": len(product_rows),
        "synthetic_records": len(synth_rows),
        "rejected_product": len(rejected_product),
        "rejected_synthetic": len(rejected_synth),
        "purged_near_dupe_cross_split": len(removed),
        "duplicates_exact_cross_split": len(dedupe["exact_cross"]),
        "duplicates_near_cross_split": len(dedupe["near_cross"]),
        "per_class": {k: dict(v) for k, v in counts.items()},
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()