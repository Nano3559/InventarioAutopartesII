import csv
import hashlib
import json
import shutil
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
REVIEW_MANIFEST = ROOT / "ia-service/datasets/review/review_manifest.csv"
PILOT = ROOT / "ia-service/datasets/autobox_pilot"
CLASSES = {
    "brake_pad": 0,
    "brake_rotor": 1,
    "brake_caliper": 2,
    "oil_filter": 4,
}


def read_manifest():
    with REVIEW_MANIFEST.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def choose_rows(rows):
    chosen = []
    for class_name in CLASSES:
        candidates = sorted(
            (row for row in rows if row["target_class"] == class_name and row["review_status"] == "APPROVED"),
            key=lambda row: row["original_path"],
        )
        chosen.extend(candidates[:5])
    if len(chosen) != 20:
        raise RuntimeError(f"Expected 20 approved images, got {len(chosen)}")
    return chosen


def candidate_mask(image):
    height, width = image.shape[:2]
    border = np.concatenate(
        [image[: max(2, height // 20), :, :].reshape(-1, 3), image[-max(2, height // 20) :, :, :].reshape(-1, 3), image[:, : max(2, width // 20), :].reshape(-1, 3), image[:, -max(2, width // 20) :, :].reshape(-1, 3)]
    )
    background = np.median(border, axis=0)
    difference = np.linalg.norm(image.astype(np.float32) - background, axis=2).astype(np.uint8)
    threshold, mask = cv2.threshold(difference, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    threshold = max(12, min(70, threshold))
    mask = np.where(difference >= threshold, 255, 0).astype(np.uint8)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    return mask


def find_box(image):
    height, width = image.shape[:2]
    mask = candidate_mask(image)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = float(width * height)
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < image_area * 0.005 or area > image_area * 0.85:
            continue
        x, y, box_width, box_height = cv2.boundingRect(contour)
        box_area = box_width * box_height / image_area
        touches = x <= 1 and y <= 1 and x + box_width >= width - 1 and y + box_height >= height - 1
        if touches or box_area > 0.92 or box_area < 0.01:
            continue
        candidates.append((area, x, y, box_width, box_height, box_area))
    candidates.sort(reverse=True)
    if not candidates:
        return None, "REJECTED", "no_meaningful_component"
    if len(candidates) > 1 and candidates[1][0] >= candidates[0][0] * 0.55:
        return None, "REJECTED", "multiple_large_components"
    _, x, y, box_width, box_height, box_area = candidates[0]
    return [x / width, y / height, box_width / width, box_height / height], "ACCEPTED", f"largest_component_area={box_area:.4f}"


def main():
    rows = choose_rows(read_manifest())
    for sub in ["images", "labels", "previews"]:
        (PILOT / sub).mkdir(parents=True, exist_ok=True)
    results = []
    for index, row in enumerate(rows, 1):
        source = ROOT / row["review_path"]
        work_name = f"{row['target_class']}__{index:03d}.jpg"
        work_image = PILOT / "images" / work_name
        shutil.copy2(source, work_image)
        image = cv2.imread(str(work_image))
        if image is None:
            raise RuntimeError(f"Cannot read {work_image}")
        bbox, status, note = find_box(image)
        label_path = PILOT / "labels" / work_name.replace(".jpg", ".txt")
        if bbox:
            label_path.write_text(f"{CLASSES[row['target_class']]} {' '.join(f'{v:.6f}' for v in [bbox[0] + bbox[2] / 2, bbox[1] + bbox[3] / 2, bbox[2], bbox[3]])}\n", encoding="utf-8")
        preview = image.copy()
        if bbox:
            h, w = preview.shape[:2]
            x, y, bw, bh = [bbox[0] * w, bbox[1] * h, bbox[2] * w, bbox[3] * h]
            color = (0, 180, 0) if status == "ACCEPTED" else (0, 0, 255)
            cv2.rectangle(preview, (int(x), int(y)), (int(x + bw), int(y + bh)), color, 2)
        cv2.putText(preview, f"{row['target_class']} {status}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255) if status == "REJECTED" else (0, 180, 0), 2)
        preview_path = PILOT / "previews" / work_name
        cv2.imwrite(str(preview_path), preview)
        results.append({
            "image": work_name,
            "source_image": row["review_path"],
            "target_class": row["target_class"],
            "target_class_id": CLASSES[row["target_class"]],
            "status": status,
            "bbox": json.dumps(bbox) if bbox else "",
            "area_fraction": f"{bbox[2] * bbox[3]:.6f}" if bbox else "",
            "method": "border_color_difference_otsu_morphology_largest_component",
            "note": note,
            "preview": str(preview_path.relative_to(ROOT)).replace("\\", "/"),
        })
    with (PILOT / "autobox_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps({"processed": len(results), "accepted": sum(r["status"] == "ACCEPTED" for r in results), "rejected": sum(r["status"] == "REJECTED" for r in results), "output": str(PILOT)}, indent=2))


if __name__ == "__main__":
    main()
