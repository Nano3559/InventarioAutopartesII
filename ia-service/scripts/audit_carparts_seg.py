import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "ia-service/datasets/external/carparts_seg/extracted"
PILOT = ROOT / "ia-service/datasets/headlight_conversion_pilot"
TARGET_IDS = {12: "front_left_light", 13: "front_light", 15: "front_right_light"}


def parse_label(path):
    result = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fields = raw.split()
        if not fields:
            continue
        if len(fields) < 7 or (len(fields) - 1) % 2:
            raise ValueError(f"{path}:{line_number}: invalid segmentation line")
        values = [float(value) for value in fields]
        class_id = int(values[0])
        points = list(zip(values[1::2], values[2::2]))
        result.append((class_id, points))
    return result


def box_from_polygon(points):
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    return [(xmin + xmax) / 2, (ymin + ymax) / 2, xmax - xmin, ymax - ymin]


def main():
    yaml_text = (DATASET / "carparts-seg.yaml").read_text(encoding="utf-8")
    names = dict((int(key), value) for key, value in re.findall(r"^\s+(\d+):\s+(.+)$", yaml_text, re.MULTILINE))
    counts = Counter()
    image_counts = defaultdict(set)
    invalid = []
    labels_total = 0
    images_total = 0
    split_counts = Counter()
    candidates = []
    for split in ["train", "val", "test"]:
        label_dir = DATASET / "labels" / split
        image_dir = DATASET / "images" / split
        for label_path in sorted(label_dir.glob("*.txt")):
            labels_total += 1
            image_path = image_dir / (label_path.stem + ".jpg")
            if image_path.exists():
                images_total += 1
            try:
                polygons = parse_label(label_path)
            except ValueError as error:
                invalid.append(str(error))
                continue
            for class_id, points in polygons:
                counts[class_id] += 1
                image_counts[class_id].add((split, label_path.name))
                if class_id in TARGET_IDS:
                    candidates.append((split, label_path, image_path, class_id, points))
    for split in ["train", "val", "test"]:
        split_counts[split] = len(list((DATASET / "images" / split).glob("*.jpg")))

    # Select at most five distinct images, preserving class and split variety.
    selected = []
    seen = set()
    for candidate in candidates:
        key = (candidate[0], candidate[1].name)
        if key in seen:
            continue
        selected.append(candidate)
        seen.add(key)
        if len(selected) == 5:
            break

    PILOT.mkdir(parents=True, exist_ok=True)
    preview_dir = PILOT / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    for index, (split, label_path, image_path, _, _) in enumerate(selected, 1):
        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)
        polygons = parse_label(label_path)
        candidate_count = 0
        for class_id, points in polygons:
            if class_id not in TARGET_IDS:
                continue
            candidate_count += 1
            width, height = image.size
            pixel_points = [(int(x * width), int(y * height)) for x, y in points]
            draw.polygon(pixel_points, outline=(255, 165, 0), width=3)
            box = box_from_polygon(points)
            x, y, box_width, box_height = box
            draw.rectangle((int((x - box_width / 2) * width), int((y - box_height / 2) * height), int((x + box_width / 2) * width), int((y + box_height / 2) * height)), outline=(0, 200, 0), width=3)
            manifest_rows.append({
                "image": str(image_path.relative_to(ROOT)).replace("\\", "/"),
                "split": split,
                "original_class": TARGET_IDS[class_id],
                "original_class_id": class_id,
                "target_class": "headlight",
                "target_class_id": 7,
                "polygons": 1,
                "boxes": 1,
                "status": "PILOT_ONLY",
            })
        image.save(preview_dir / f"{index:02d}_{split}_{label_path.stem}.jpg")
    with (PILOT / "conversion_pilot_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]) if manifest_rows else ["image"])
        writer.writeheader()
        writer.writerows(manifest_rows)
    report = {
        "yaml_classes": names,
        "images_by_split": dict(split_counts),
        "labels_by_split": {split: len(list((DATASET / "labels" / split).glob("*.txt"))) for split in ["train", "val", "test"]},
        "target_counts": {str(class_id): {"name": TARGET_IDS[class_id], "images": len(image_counts[class_id]), "instances": counts[class_id]} for class_id in TARGET_IDS},
        "all_instance_counts": dict(sorted(counts.items())),
        "invalid_labels": invalid,
        "pilot_images": len(selected),
        "pilot_polygons": len(manifest_rows),
    }
    (PILOT / "audit_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
