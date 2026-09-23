import csv
import json
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw
from rembg import new_session, remove


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "ia-service/datasets/review/review_manifest.csv"
CLASSES = {"brake_rotor": 1, "brake_caliper": 2, "oil_filter": 4}
random.seed(20260922)


def read_rows():
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def bbox_from_alpha(alpha):
    return alpha.getbbox()


def main():
    session = new_session("u2net")
    all_results = []
    colors = [(235, 235, 235), (205, 220, 235), (225, 215, 200), (45, 55, 65), (215, 235, 215)]
    rows = read_rows()
    for class_index, (class_name, class_id) in enumerate(CLASSES.items()):
        pilot = ROOT / "ia-service/datasets/synthetic_pilot" / class_name
        for sub in ["originals", "masks", "cutouts", "composites", "previews", "labels"]:
            (pilot / sub).mkdir(parents=True, exist_ok=True)
        selected = sorted((r for r in rows if r["target_class"] == class_name and r["review_status"] == "APPROVED"), key=lambda r: r["original_path"])[:5]
        if len(selected) != 5:
            raise RuntimeError(f"Expected 5 approved images for {class_name}, got {len(selected)}")
        for index, row in enumerate(selected, 1):
            name = f"{class_name}__{index:03d}"
            source = ROOT / row["review_path"]
            image = Image.open(source).convert("RGBA")
            image.convert("RGB").save(pilot / "originals" / f"{name}.jpg")
            cutout = remove(image, session=session, alpha_matting=False)
            cutout.save(pilot / "cutouts" / f"{name}.png")
            alpha = cutout.getchannel("A")
            alpha.save(pilot / "masks" / f"{name}.png")
            bbox = bbox_from_alpha(alpha)
            result = {"class": class_name, "image": f"{name}.jpg", "mask_status": "MALA", "box_status": "MALA", "bbox": "", "area_fraction": 0, "note": "empty_alpha"}
            if bbox:
                scale = [0.78, 0.86, 0.92, 0.82, 0.88][index - 1]
                angle = [-7, 4, -3, 8, 2][index - 1]
                transformed = cutout.resize((int(cutout.width * scale), int(cutout.height * scale)), Image.Resampling.LANCZOS).rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
                background = Image.new("RGB", image.size, colors[(index + class_index) % len(colors)])
                composed = background.convert("RGBA")
                x = max(0, min(image.width - transformed.width, int(image.width * [0.08, 0.16, 0.05, 0.20, 0.10][index - 1])))
                y = max(0, min(image.height - transformed.height, int(image.height * [0.10, 0.05, 0.14, 0.08, 0.18][index - 1])))
                composed.alpha_composite(transformed, (x, y))
                composed.convert("RGB").save(pilot / "composites" / f"{name}.jpg", quality=95)
                transformed_bbox = transformed.getchannel("A").getbbox()
                if transformed_bbox:
                    x1, y1, x2, y2 = [value + offset for value, offset in zip(transformed_bbox, (x, y, x, y))]
                    cx = ((x1 + x2) / 2) / image.width
                    cy = ((y1 + y2) / 2) / image.height
                    bw = (x2 - x1) / image.width
                    bh = (y2 - y1) / image.height
                    pilot / "labels" / f"{name}.txt"
                    (pilot / "labels" / f"{name}.txt").write_text(f"{class_id} {cx:.8f} {cy:.8f} {bw:.8f} {bh:.8f}\n", encoding="utf-8")
                    preview = composed.convert("RGB")
                    ImageDraw.Draw(preview).rectangle((x1, y1, x2, y2), outline=(0, 180, 0), width=4)
                    ImageDraw.Draw(preview).text((8, 8), f"{class_name} | {name}", fill=(0, 120, 0))
                    preview.save(pilot / "previews" / f"{name}.jpg", quality=95)
                    result.update({"mask_status": "PENDING_REVIEW", "box_status": "PENDING_REVIEW", "bbox": json.dumps([cx, cy, bw, bh]), "area_fraction": round(bw * bh, 6), "note": "u2net_cutout_composite"})
            all_results.append(result)
        with (pilot / "synthetic_pilot_results.csv").open("w", newline="", encoding="utf-8") as handle:
            class_rows = [r for r in all_results if r["class"] == class_name]
            writer = csv.DictWriter(handle, fieldnames=list(class_rows[0]))
            writer.writeheader()
            writer.writerows(class_rows)
    print(json.dumps({"processed": len(all_results), "classes": {c: sum(r["class"] == c for r in all_results) for c in CLASSES}}, indent=2))


if __name__ == "__main__":
    main()
