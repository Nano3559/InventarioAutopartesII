import csv
import hashlib
import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance
from rembg import new_session, remove


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ia-service/datasets/dataset_manifest.csv"
OUT = ROOT / "ia-service/datasets/synthetic"
SEED = 20260922
TARGETS = {"brake_pad": (0, 200), "brake_rotor": (1, 200), "brake_caliper": (2, 200), "oil_filter": (4, 194)}
CANVAS = (224, 224)


def read_sources():
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {name: [row for row in rows if row["target_class"] == name] for name in TARGETS}


def local_background(index, size=CANVAS):
    width, height = size
    rng = np.random.default_rng(SEED + index * 31)
    style = index % 6
    colors = [(232, 232, 232), (207, 220, 232), (218, 207, 190), (52, 62, 73), (211, 229, 211), (205, 195, 178)]
    base = np.zeros((height, width, 3), dtype=np.uint8)
    color = np.array(colors[style], dtype=np.float32)
    base[:] = color
    if style in (1, 2, 4, 5):
        noise = rng.normal(0, 5, (height, width, 1))
        base = np.clip(base.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    if style == 3:
        for y in range(0, height, 18):
            base[y : y + 2] = np.clip(base[y : y + 2].astype(np.int16) - 12, 0, 255)
    if style == 5:
        for x in range(0, width, 24):
            base[:, x : x + 2] = np.clip(base[:, x : x + 2].astype(np.int16) - 10, 0, 255)
    return Image.fromarray(base, "RGB")


def mask_quality(alpha):
    bbox = alpha.getbbox()
    if not bbox:
        return False, "empty_mask"
    width, height = alpha.size
    area = np.count_nonzero(np.array(alpha) > 20) / (width * height)
    box_area = ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])) / (width * height)
    if area < 0.02:
        return False, "foreground_too_small"
    if area > 0.90 or box_area > 0.95:
        return False, "foreground_too_large"
    return True, f"alpha_area={area:.5f};box_area={box_area:.5f}"


def transform_cutout(cutout, index):
    scale = [0.68, 0.76, 0.84, 0.90, 0.72, 0.82, 0.88][index % 7]
    angle = [-18, -10, -4, 0, 6, 12, 18][index % 7]
    transformed = cutout.resize((max(1, int(cutout.width * scale)), max(1, int(cutout.height * scale))), Image.Resampling.LANCZOS)
    transformed = transformed.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    max_width, max_height = int(CANVAS[0] * 0.88), int(CANVAS[1] * 0.88)
    if transformed.width > max_width or transformed.height > max_height:
        shrink = min(max_width / transformed.width, max_height / transformed.height)
        transformed = transformed.resize((int(transformed.width * shrink), int(transformed.height * shrink)), Image.Resampling.LANCZOS)
    return transformed


def generate():
    rng = random.Random(SEED)
    for folder in ["images", "labels", "masks", "previews", "manifests"]:
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    sources = read_sources()
    session = new_session("u2net")
    accepted = {}
    rejected = []
    for class_name, rows in sources.items():
        accepted[class_name] = []
        for row in sorted(rows, key=lambda item: item["local_path"]):
            source_path = ROOT / row["local_path"]
            image = Image.open(source_path).convert("RGBA")
            cutout = remove(image, session=session, alpha_matting=False)
            ok, reason = mask_quality(cutout.getchannel("A"))
            if ok:
                source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
                accepted[class_name].append((row, cutout, source_hash))
            else:
                rejected.append({"class": class_name, "source": row["local_path"], "reason": reason})
    records = []
    preview_candidates = defaultdict(list)
    for class_name, (class_id, target_count) in TARGETS.items():
        candidates = accepted[class_name]
        if not candidates:
            raise RuntimeError(f"No accepted sources for {class_name}")
        for output_index in range(target_count):
            row, cutout, source_hash = candidates[output_index % len(candidates)]
            generated_index = sum(TARGETS[name][1] for name in TARGETS if list(TARGETS).index(name) < list(TARGETS).index(class_name)) + output_index
            transformed = transform_cutout(cutout, generated_index)
            background = local_background(generated_index)
            position_x = rng.randint(8, max(8, CANVAS[0] - transformed.width - 8))
            position_y = rng.randint(8, max(8, CANVAS[1] - transformed.height - 8))
            composed = background.convert("RGBA")
            composed.alpha_composite(transformed, (position_x, position_y))
            alpha = Image.new("L", CANVAS, 0)
            transformed_alpha = transformed.getchannel("A")
            alpha.paste(transformed_alpha, (position_x, position_y), transformed_alpha)
            bbox = alpha.getbbox()
            if not bbox:
                raise RuntimeError(f"Empty transformed alpha for {class_name} {output_index}")
            x1, y1, x2, y2 = bbox
            cx = ((x1 + x2) / 2) / CANVAS[0]
            cy = ((y1 + y2) / 2) / CANVAS[1]
            width = (x2 - x1) / CANVAS[0]
            height = (y2 - y1) / CANVAS[1]
            if not (0 <= cx <= 1 and 0 <= cy <= 1 and 0 < width <= 1 and 0 < height <= 1):
                raise RuntimeError(f"Invalid bbox for {class_name} {output_index}")
            name = f"{class_name}__{output_index + 1:04d}"
            image_path = OUT / "images" / f"{name}.jpg"
            label_path = OUT / "labels" / f"{name}.txt"
            mask_path = OUT / "masks" / f"{name}.png"
            composed.convert("RGB").save(image_path, quality=95)
            alpha.save(mask_path)
            label_path.write_text(f"{class_id} {cx:.8f} {cy:.8f} {width:.8f} {height:.8f}\n", encoding="utf-8")
            background_name = ["gray", "blue_gray", "cardboard", "metal", "green_gray", "workbench"][generated_index % 6]
            records.append({
                "synthetic_image": str(image_path.relative_to(ROOT)).replace("\\", "/"),
                "synthetic_label": str(label_path.relative_to(ROOT)).replace("\\", "/"),
                "target_class": class_name,
                "target_class_id": class_id,
                "source_image": row["local_path"],
                "source_group_id": source_hash,
                "background": background_name,
                "background_source": "local_generated",
                "background_license": "NONE_LOCAL_GENERATED",
                "rotation": [-18, -10, -4, 0, 6, 12, 18][generated_index % 7],
                "scale": [0.68, 0.76, 0.84, 0.90, 0.72, 0.82, 0.88][generated_index % 7],
                "position_x": position_x,
                "position_y": position_y,
                "mask_status": "ACCEPTED_AUTOMATED",
                "box_status": "VALIDATED_GEOMETRICALLY",
                "generation_seed": SEED + generated_index,
            })
            if len(preview_candidates[class_name]) < 10:
                preview_candidates[class_name].append((image_path, label_path))
    fields = list(records[0])
    with (OUT / "manifests/synthetic_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    # Generate 10 deterministic previews per class.
    for class_name, items in preview_candidates.items():
        for image_path, label_path in items:
            image = Image.open(image_path).convert("RGB")
            fields = label_path.read_text().split()
            width, height = image.size
            cx, cy, box_width, box_height = [float(value) for value in fields[1:]]
            bbox = ((cx - box_width / 2) * width, (cy - box_height / 2) * height, (cx + box_width / 2) * width, (cy + box_height / 2) * height)
            draw = ImageDraw.Draw(image)
            draw.rectangle(bbox, outline=(0, 180, 0), width=3)
            draw.text((6, 6), f"{class_name} synthetic", fill=(0, 120, 0))
            image.save(OUT / "previews" / f"{image_path.stem}.jpg", quality=95)
    (OUT / "manifests/rejected_sources.csv").write_text("class,source,reason\n" + "\n".join(f"{r['class']},{r['source']},{r['reason']}" for r in rejected) + "\n", encoding="utf-8")
    print(json.dumps({"generated": len(records), "accepted_sources": {k: len(v) for k, v in accepted.items()}, "rejected_sources": len(rejected), "manifest": str(OUT / 'manifests/synthetic_manifest.csv')}, indent=2))


if __name__ == "__main__":
    generate()
