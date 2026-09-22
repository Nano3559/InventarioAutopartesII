import csv
import json
import shutil
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor


ROOT = Path(__file__).resolve().parents[2]
REVIEW_MANIFEST = ROOT / "ia-service/datasets/review/review_manifest.csv"
PILOT_ROOT = ROOT / "ia-service/datasets/pilot_preannotation"
PREVIEW_ROOT = PILOT_ROOT / "preview"
MODEL_ID = "IDEA-Research/grounding-dino-tiny"

CLASSES = {
    "brake_pad": (0, "brake pad"),
    "brake_rotor": (1, "brake rotor"),
    "brake_caliper": (2, "brake caliper"),
    "alternator": (3, "alternator"),
    "oil_filter": (4, "oil filter"),
    "air_filter": (5, "air filter"),
    "radiator": (6, "radiator"),
    "headlight": (7, "headlight"),
}


def read_manifest():
    with REVIEW_MANIFEST.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def iou_xyxy(left, right):
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_left = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    area_right = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = area_left + area_right - intersection
    return intersection / union if union else 0.0


def yolo_boxes(label_path):
    if not label_path or not label_path.exists():
        return []
    boxes = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != 5 or int(fields[0]) != 14:
            continue
        _, cx, cy, width, height = map(float, fields)
        boxes.append((cx, cy, width, height))
    return boxes


def to_xyxy(box, width, height):
    cx, cy, box_width, box_height = box
    return [
        (cx - box_width / 2) * width,
        (cy - box_height / 2) * height,
        (cx + box_width / 2) * width,
        (cy + box_height / 2) * height,
    ]


def draw_preview(source, destination, boxes, ground_truth):
    image = cv2.imread(str(source))
    if image is None:
        raise RuntimeError(f"Cannot read image: {source}")
    height, width = image.shape[:2]
    for box, score in boxes:
        x1, y1, x2, y2 = to_xyxy(box, width, height)
        cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
        cv2.putText(image, f"proposal {score:.2f}", (int(x1), max(20, int(y1) - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
    for box in ground_truth:
        x1, y1, x2, y2 = to_xyxy(box, width, height)
        cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 180, 0), 2)
        cv2.putText(image, "ground truth", (int(x1), min(height - 8, int(y2) + 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 180, 0), 2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destination), image)


def main():
    rows = read_manifest()
    selected = []
    for class_name in CLASSES:
        candidates = sorted((row for row in rows if row["target_class"] == class_name and row["review_status"] == "APPROVED"), key=lambda row: row["original_path"])
        selected.extend(candidates[:5])
    if len(selected) != 40:
        raise RuntimeError(f"Expected 40 approved pilot images, got {len(selected)}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(MODEL_ID).to(device)
    model.eval()
    results = []
    for row in selected:
        class_name = row["target_class"]
        class_id, prompt = CLASSES[class_name]
        source = ROOT / row["review_path"]
        image = Image.open(source).convert("RGB")
        inputs = processor(images=image, text=prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**inputs)
        processed = processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            box_threshold=0.20,
            text_threshold=0.15,
            target_sizes=[image.size[::-1]],
        )[0]
        width, height = image.size
        proposed = []
        for box, score in zip(processed["boxes"], processed["scores"]):
            x1, y1, x2, y2 = box.detach().cpu().tolist()
            proposed.append(([
                ((x1 + x2) / 2) / width,
                ((y1 + y2) / 2) / height,
                (x2 - x1) / width,
                (y2 - y1) / height,
            ], float(score.detach().cpu())))
        label_path = ROOT / row["review_label_path"] if row["review_label_path"] else None
        ground_truth = yolo_boxes(label_path) if class_name == "air_filter" else []
        iou = None
        if ground_truth and proposed:
            iou = max(iou_xyxy(to_xyxy(box, 1, 1), to_xyxy(gt, 1, 1)) for box, _ in proposed for gt in ground_truth)
        detection_found = bool(proposed)
        full_frame = any(box[2] >= 0.95 or box[3] >= 0.95 or box[2] * box[3] >= 0.90 for box, _ in proposed)
        needs_manual = not detection_found or len(proposed) != 1 or full_frame or (iou is not None and iou < 0.5)
        preview_name = f"{class_id:02d}_{source.stem}.jpg"
        draw_preview(source, PREVIEW_ROOT / preview_name, proposed, ground_truth)
        results.append({
            "image": row["review_path"],
            "target_class": class_name,
            "target_class_id": class_id,
            "prompt": prompt,
            "detection_found": detection_found,
            "confidence": max((score for _, score in proposed), default=None),
            "bbox": json.dumps([box for box, _ in proposed]),
            "needs_manual_review": needs_manual,
            "ground_truth_available": bool(ground_truth),
            "iou_with_ground_truth": iou,
        })

    PILOT_ROOT.mkdir(parents=True, exist_ok=True)
    with (PILOT_ROOT / "pilot_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps({"device": device, "processed": len(results), "preview": str(PREVIEW_ROOT), "results": str(PILOT_ROOT / 'pilot_results.csv')}, indent=2))


if __name__ == "__main__":
    main()
