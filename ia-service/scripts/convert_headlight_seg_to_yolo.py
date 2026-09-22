import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "ia-service/datasets/external/carparts_seg/extracted"
DEST = ROOT / "ia-service/datasets/converted/headlight"
TARGET_IDS = {12: "front_left_light", 13: "front_light", 15: "front_right_light"}


def parse_label(path):
    records = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fields = raw.split()
        if not fields:
            continue
        if len(fields) < 7 or (len(fields) - 1) % 2:
            raise ValueError(f"invalid segmentation line {path}:{line_number}")
        values = [float(value) for value in fields]
        class_id = int(values[0])
        points = list(zip(values[1::2], values[2::2]))
        records.append((class_id, points))
    return records


def box_from_polygon(points):
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    box = [(xmin + xmax) / 2, (ymin + ymax) / 2, xmax - xmin, ymax - ymin]
    return box, xmin, ymin, xmax, ymax


def main():
    rows = []
    previews = []
    for original_split in ["train", "val", "test"]:
        labels_dir = SOURCE / "labels" / original_split
        images_dir = SOURCE / "images" / original_split
        final_split = original_split
        if original_split == "val":
            final_split = "val"
        for label_path in sorted(labels_dir.glob("*.txt")):
            records = parse_label(label_path)
            selected = [(class_id, points) for class_id, points in records if class_id in TARGET_IDS]
            if not selected:
                continue
            source_image = images_dir / f"{label_path.stem}.jpg"
            if not source_image.exists():
                raise FileNotFoundError(source_image)
            destination_image = DEST / "images" / final_split / source_image.name
            destination_label = DEST / "labels" / final_split / f"{label_path.stem}.txt"
            destination_image.parent.mkdir(parents=True, exist_ok=True)
            destination_label.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_image, destination_image)
            output_lines = []
            source_classes = []
            boxes = []
            image_width, image_height = Image.open(source_image).size
            for class_id, points in selected:
                box, xmin, ymin, xmax, ymax = box_from_polygon(points)
                if not (0 <= xmin <= xmax <= 1 and 0 <= ymin <= ymax <= 1):
                    raise ValueError(f"polygon outside normalized range: {label_path}")
                cx, cy, width, height = box
                if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 < width <= 1 and 0 < height <= 1):
                    raise ValueError(f"invalid converted box: {label_path}")
                output_lines.append(f"7 {cx:.8f} {cy:.8f} {width:.8f} {height:.8f}")
                source_classes.append(f"{class_id}:{TARGET_IDS[class_id]}")
                boxes.append(box)
            destination_label.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
            rows.append({
                "source": "Ultralytics Carparts-Seg",
                "source_image": str(source_image.relative_to(ROOT)).replace("\\", "/"),
                "destination_image": str(destination_image.relative_to(ROOT)).replace("\\", "/"),
                "original_split": original_split,
                "final_split": final_split,
                "original_class_id": ";".join(source_classes),
                "original_class_name": ";".join(TARGET_IDS[int(item.split(":")[0])] for item in source_classes),
                "final_class_id": 7,
                "final_class_name": "headlight",
                "instance_count": len(output_lines),
                "license": "CC BY 4.0",
                "conversion_status": "CONVERTED_PILOT_READY",
            })
            if len([r for r in rows if r["final_split"] == final_split]) <= 5:
                previews.append((source_image, destination_image, boxes, final_split, label_path.stem))

    DEST.mkdir(parents=True, exist_ok=True)
    with (DEST / "headlight_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = list(rows[0])
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    preview_dir = DEST / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    # Keep exactly five previews per final split.
    selected_previews = []
    for split in ["train", "val", "test"]:
        selected_previews.extend([item for item in previews if item[3] == split][:5])
    for source_image, _, boxes, split, stem in selected_previews:
        image = Image.open(source_image).convert("RGB")
        draw = ImageDraw.Draw(image)
        width, height = image.size
        for box in boxes:
            cx, cy, box_width, box_height = box
            xy = ((cx - box_width / 2) * width, (cy - box_height / 2) * height, (cx + box_width / 2) * width, (cy + box_height / 2) * height)
            draw.rectangle(xy, outline=(0, 190, 0), width=4)
        image.save(preview_dir / f"{split}__{stem}.jpg")

    split_stats = Counter()
    for row in rows:
        split_stats[row["final_split"]] += int(row["instance_count"])
    print(json.dumps({"images": len(rows), "boxes": sum(split_stats.values()), "split_boxes": dict(split_stats), "previews": len(selected_previews)}, indent=2))


if __name__ == "__main__":
    main()
