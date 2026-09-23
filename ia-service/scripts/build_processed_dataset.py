import csv
import hashlib
import json
import os
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "ia-service/datasets/processed"
RAW_ROOT = ROOT / "ia-service/datasets/raw"
_TEMP_BASE = Path(os.environ.get("TEMP", tempfile.gettempdir())) / "opencode"
ENGINE_TEMP = _TEMP_BASE / "engine-images"
ENGINE_LABEL_TEMP = _TEMP_BASE / "air-labels"
CONVERTED = ROOT / "ia-service/datasets/converted/headlight"
DATASET_MANIFEST = ROOT / "ia-service/datasets/dataset_manifest.csv"
SYNTH_MANIFEST = ROOT / "ia-service/datasets/synthetic/manifests/synthetic_manifest.csv"
TARGETS = {"brake_pad": 0, "brake_rotor": 1, "brake_caliper": 2, "alternator": 3, "oil_filter": 4, "air_filter": 5, "radiator": 6, "headlight": 7}
NAME_BY_ID = {value: key for key, value in TARGETS.items()}
RAW_IDS = {"alternator": 11, "oil_filter": 25, "air_filter": 14, "radiator": 13}
REMAP = {11: 3, 25: 4, 14: 5, 13: 6}


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_yolo(path, source_id=None, target_id=None):
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"Invalid YOLO line: {path}")
        values = [float(value) for value in fields]
        if source_id is not None and int(values[0]) != source_id:
            continue
        if target_id is not None:
            values[0] = target_id
        result.append(values)
    return result


def read_yolo_multi(path):
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5:
            raise ValueError(f"Invalid YOLO line: {path}")
        values = [float(value) for value in fields]
        source_id = int(values[0])
        if source_id not in REMAP:
            continue
        values[0] = REMAP[source_id]
        result.append(values)
    return result


def add_record(records, source, source_version, source_image, source_group, source_label, target_class, split, annotation_origin, synthetic, license_name, name_base, boxes, image_source_path=None, target_class_id=None):
    image_source = Path(image_source_path) if image_source_path else ROOT / source_image
    image_name = f"{name_base}.jpg"
    label_name = f"{name_base}.txt"
    image_dest = PROCESSED / "images" / split / image_name
    label_dest = PROCESSED / "labels" / split / label_name
    image_dest.parent.mkdir(parents=True, exist_ok=True)
    label_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(image_source, image_dest)
    label_dest.write_text("\n".join(" ".join(f"{value:.8f}" if index else str(int(value)) for index, value in enumerate(box)) for box in boxes) + "\n", encoding="utf-8")
    records.append({
        "processed_image": str(image_dest.relative_to(ROOT)).replace("\\", "/"),
        "processed_label": str(label_dest.relative_to(ROOT)).replace("\\", "/"),
        "split": split,
        "target_class": target_class,
        "target_class_id": target_class_id if target_class_id is not None else TARGETS[target_class],
        "source_dataset": source,
        "source_image": source_image,
        "source_group_id": source_group,
        "annotation_origin": annotation_origin,
        "is_synthetic": str(synthetic).lower(),
        "license": license_name,
        "source_version": source_version,
        "source_label": source_label,
    })


def main():
    for folder in ["images/train", "images/val", "images/test", "labels/train", "labels/val", "labels/test", "previews"]:
        (PROCESSED / folder).mkdir(parents=True, exist_ok=True)
    records = []

    synth = read_csv(SYNTH_MANIFEST)
    for row in synth:
        class_name = row["target_class"]
        add_record(records, "synthetic_local", "seed-20260922", row["synthetic_image"], row["source_group_id"], row["synthetic_label"], class_name, "train", "SYNTHETIC_MASK_TO_BOX", True, "NONE_LOCAL_GENERATED", f"synthetic__{class_name}__{Path(row['synthetic_image']).stem}", read_yolo(ROOT / row["synthetic_label"]))

    # Car Engine Bay: the grouping unit is the ORIGINAL PHOTOGRAPH (source_group_id = SHA-256).
    # A photo may contain several target classes; all its target boxes stay together in ONE label
    # and the photo goes to a SINGLE split (zero leakage). Remap: 11->3, 25->4, 14->5, 13->6.
    def class_ids_of(boxes):
        return sorted({int(box[0]) for box in boxes})

    def photo_units():
        units = []
        for label_path in sorted(ENGINE_LABEL_TEMP.glob("*.txt"), key=lambda p: p.name):
            image_path = RAW_ROOT / "car-engine-bay/images" / f"{label_path.stem}.jpg"
            temp_image = ENGINE_TEMP / f"{label_path.stem}.jpg"
            actual_image = temp_image if temp_image.exists() else image_path
            if not actual_image.exists():
                continue
            boxes = read_yolo_multi(label_path)
            if not boxes:
                continue
            units.append((actual_image, label_path, boxes, sha256(actual_image)))
        units.sort(key=lambda unit: unit[3])
        return units

    def assign_ceb(unit, split):
        image_path, label_path, boxes, group_id = unit
        class_ids = class_ids_of(boxes)
        target_class = "+".join(NAME_BY_ID[cid] for cid in class_ids)
        target_class_id = "+".join(str(cid) for cid in class_ids)
        name_base = f"car_engine_bay__{split}__{label_path.stem}"
        add_record(records, "khaledchawa/car-engine-bay-pictures", "v2", f"images/images/{label_path.stem}.jpg", group_id, f"labels/labels/{label_path.name}", target_class, split, "REAL_YOLO", False, "MIT", name_base, boxes, image_path, target_class_id)

    pool = photo_units()
    # Deterministic tiers: oil first (its photos are multi-class), then single-class photos for alt/rad/air.
    tiers = [
        ("oil_filter", lambda c: 4 in c, 3, 3),
        ("alternator", lambda c: c == [3], 20, 20),
        ("radiator", lambda c: c == [6], 20, 20),
        ("air_filter", lambda c: c == [5], 6, 6),
    ]
    assignments = []
    for _, predicate, val_target, test_target in tiers:
        chosen, kept = [], []
        for unit in pool:
            if predicate(class_ids_of(unit[2])) and len(chosen) < val_target + test_target:
                chosen.append(unit)
            else:
                kept.append(unit)
        pool = kept
        for index, unit in enumerate(chosen):
            assignments.append((unit, "val" if index < val_target else "test"))
    for unit in pool:
        assignments.append((unit, "train"))
    seen_split_groups = set()
    for unit, split in assignments:
        if (split, unit[3]) in seen_split_groups:
            continue
        seen_split_groups.add((split, unit[3]))
        assign_ceb(unit, split)

    # Headlight: select inside each original split and normalize valid -> val.
    headlight_rows = read_csv(CONVERTED / "headlight_manifest.csv")
    for original_split, final_split, limit in [("train", "train", 160), ("val", "val", 20), ("test", "test", 20)]:
        selected = sorted((row for row in headlight_rows if row["final_split"] == original_split), key=lambda row: row["source_image"])[:limit]
        for index, row in enumerate(selected):
            source_image = row["destination_image"]
            source_label = str(CONVERTED / "labels" / original_split / f"{Path(row['source_image']).stem}.txt").replace("\\", "/")
            boxes = read_yolo(ROOT / source_label, 7, 7)
            add_record(records, "Ultralytics Carparts-Seg", "v0.0.0", source_image, sha256(ROOT / source_image), source_label, "headlight", final_split, "SEGMENTATION_TO_BOX", False, "CC BY 4.0", f"carparts_seg__headlight__{original_split}__{index + 1:03d}", boxes)

    manifest_path = PROCESSED / "processed_manifest.csv"
    fields = list(records[0])
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    (PROCESSED / "dataset.yaml").write_text("path: .\ntrain: images/train\nval: images/val\ntest: images/test\n\nnc: 8\nnames:\n  0: brake_pad\n  1: brake_rotor\n  2: brake_caliper\n  3: alternator\n  4: oil_filter\n  5: air_filter\n  6: radiator\n  7: headlight\n", encoding="utf-8")

    # Two train previews per available class and two real val/test previews.
    preview_rows = []
    for class_name in TARGETS:
        matches = [row for row in records if class_name in row["target_class"].split("+")]
        preview_rows.extend([row for row in matches if row["split"] == "train"][:2])
        preview_rows.extend([row for row in matches if row["split"] in ("val", "test") and row["is_synthetic"] == "false"][:2])
    for row in preview_rows:
        image = Image.open(ROOT / row["processed_image"]).convert("RGB")
        draw = ImageDraw.Draw(image)
        for line in (ROOT / row["processed_label"]).read_text(encoding="utf-8").splitlines():
            _, cx, cy, width, height = map(float, line.split())
            image_width, image_height = image.size
            bbox = ((cx - width / 2) * image_width, (cy - height / 2) * image_height, (cx + width / 2) * image_width, (cy + height / 2) * image_height)
            draw.rectangle(bbox, outline=(0, 190, 0), width=3)
        image.save(PROCESSED / "previews" / Path(row["processed_image"]).name, quality=95)
    print(json.dumps({"records": len(records), "preview_count": len(preview_rows)}, indent=2))


if __name__ == "__main__":
    main()
