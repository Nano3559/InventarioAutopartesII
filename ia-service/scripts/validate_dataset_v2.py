import csv
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "ia-service/datasets/processed_v2"
CLASS_NAMES = {0: "brake_pad", 1: "brake_rotor", 2: "brake_caliper", 3: "alternator", 4: "oil_filter", 5: "air_filter", 6: "radiator", 7: "headlight"}


def read_rows():
    with (V2 / "processed_v2_manifest.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_label(path):
    boxes = []
    if not path.exists():
        return None, boxes
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 5:
            return "invalid_line", boxes
        try:
            c, cx, cy, w, h = int(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
        except ValueError:
            return "non_numeric", boxes
        if c not in CLASS_NAMES or not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 < w <= 1 and 0 < h <= 1):
            return "invalid_coords", boxes
        boxes.append((c, cx, cy, w, h))
    return "ok", boxes


def main():
    rows = read_rows()
    per_class = defaultdict(lambda: defaultdict(lambda: {"imgs": 0, "boxes": 0, "context": 0, "product": 0, "synthetic": 0}))
    errors = []
    images_seen = set()
    for r in rows:
        rel_img = r["processed_image"]
        split = r["split"]
        img_path = ROOT / rel_img
        label_path = ROOT / r["processed_label"]
        if img_path.name in images_seen:
            errors.append(f"DUPLICATE_IMAGE_NAME: {rel_img}")
        images_seen.add(img_path.name)
        if not img_path.exists():
            errors.append(f"MISSING_IMAGE: {rel_img}")
            continue
        status, boxes = parse_label(label_path)
        if status != "ok":
            errors.append(f"LABEL_{status}: {r['processed_label']}")
            continue
        domains = set()
        for c in set(b[0] for b in boxes):
            per_class[CLASS_NAMES[c]][split]["imgs"] += 1
            per_class[CLASS_NAMES[c]][split]["boxes"] += sum(1 for b in boxes if b[0] == c)
            domains.add(c)
        dom = r.get("domain", "context")
        for c in domains:
            per_class[CLASS_NAMES[c]][split][dom] += 1

    total = defaultdict(lambda: defaultdict(int))
    for cls in CLASS_NAMES.values():
        for split in ["train", "val", "test"]:
            d = per_class[cls][split]
            total[split]["imgs"] += d["imgs"]
            total[split]["boxes"] += d["boxes"]
            total[split][cls] = d

    # Split-level checks
    all_labels = list((V2 / "labels" / s).glob("*.txt") for s in ["train", "val", "test"])
    for split in ["train", "val", "test"]:
        imgs = {f.name for f in (V2 / "images" / split).glob("*.jpg")}
        lbls = {f.name.replace(".txt", ".jpg") for f in (V2 / "labels" / split).glob("*.txt")}
        if imgs != lbls:
            errors.append(f"SPLIT_MISMATCH {split}: only_imgs={sorted(imgs - lbls)} only_labels={sorted(lbls - imgs)}")

    # Duplicate images across splits (name + hash)
    from collections import Counter
    nam = Counter()
    import hashlib as _hl
    hashes = defaultdict(list)
    for split in ["train", "val", "test"]:
        for f in (V2 / "images" / split).glob("*.jpg"):
            nam[f.name] += 1
            hashes[_hl.sha256(f.read_bytes()).hexdigest()].append((split, f.name))
    dup_names = {k: v for k, v in nam.items() if v > 1}
    dup_hashes = {k: v for k, v in hashes.items() if len({s for s, _ in v}) > 1}

    report = {
        "classes": len(CLASS_NAMES),
        "rows": len(rows),
        "total": {"train": dict(total["train"]), "val": dict(total["val"]), "test": dict(total["test"])},
        "per_class": {cls: {split: dict(per_class[cls][split]) for split in ["train", "val", "test"]} for cls in CLASS_NAMES.values()},
        "errors": errors,
        "duplicate_image_names": len(dup_names),
        "duplicate_images_across_splits": len(dup_hashes),
    }
    out = V2 / "dataset_v2_validation.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Sanity previews: 4 per class (mix of domains/splits)
    (V2 / "diagnostics").mkdir(exist_ok=True)
    picked = defaultdict(int)
    for r in rows:
        cls = r["target_class"].split("+")
        for c in cls:
            if picked[c] < 4:
                img_path = ROOT / r["processed_image"]
                label_path = ROOT / r["processed_label"]
                image = Image.open(img_path).convert("RGB")
                draw = ImageDraw.Draw(image)
                ok, boxes = parse_label(label_path)
                for cid, cx, cy, w, h in boxes:
                    W, H = image.size
                    draw.rectangle(((cx - w / 2) * W, (cy - h / 2) * H, (cx + w / 2) * W, (cy + h / 2) * H), outline=(0, 200, 0), width=3)
                draw.text((6, 6), f"{c} | {r['split']} | {r.get('domain','')}", fill=(220, 30, 30))
                image.save(V2 / "diagnostics" / f"preview__{c}__{r['split']}__{picked[c] + 1}.jpg", quality=92)
                picked[c] += 1
                break
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()