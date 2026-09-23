import csv
import json
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from rembg import new_session, remove


ROOT = Path(__file__).resolve().parents[2]
REVIEW_MANIFEST = ROOT / "ia-service/datasets/review/review_manifest.csv"
PILOT = ROOT / "ia-service/datasets/synthetic_pilot/brake_pad"
random.seed(20260922)


def read_rows():
    with REVIEW_MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return sorted((r for r in rows if r["target_class"] == "brake_pad" and r["review_status"] == "APPROVED"), key=lambda r: r["original_path"])[:5]


def make_background(size, index):
    colors = [(235, 235, 235), (205, 220, 235), (225, 215, 200), (45, 55, 65), (215, 235, 215)]
    return Image.new("RGB", size, colors[index % len(colors)])


def bbox_from_alpha(alpha):
    bbox = alpha.getbbox()
    if not bbox:
        return None
    return bbox


def main():
    for sub in ["originals", "masks", "cutouts", "composites", "previews", "labels"]:
        (PILOT / sub).mkdir(parents=True, exist_ok=True)
    rows = read_rows()
    if len(rows) != 5:
        raise RuntimeError(f"Expected five approved brake_pad images, got {len(rows)}")
    session = new_session("u2net")
    results = []
    for index, row in enumerate(rows, 1):
        name = f"brake_pad__{index:03d}"
        source = ROOT / row["review_path"]
        image = Image.open(source).convert("RGBA")
        image.convert("RGB").save(PILOT / "originals" / f"{name}.jpg")
        cutout = remove(image, session=session, alpha_matting=False)
        cutout.save(PILOT / "cutouts" / f"{name}.png")
        alpha = cutout.getchannel("A")
        alpha.save(PILOT / "masks" / f"{name}.png")
        bbox = bbox_from_alpha(alpha)
        if not bbox:
            results.append({"image": name + ".jpg", "source": row["review_path"], "mask_status": "MALA", "box_status": "MALA", "bbox": "", "area_fraction": 0, "note": "empty_alpha"})
            continue
        scale = [0.78, 0.86, 0.92, 0.82, 0.88][index - 1]
        angle = [-7, 4, -3, 8, 2][index - 1]
        transformed = cutout.resize((int(cutout.width * scale), int(cutout.height * scale)), Image.Resampling.LANCZOS).rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        canvas_size = image.size
        background = make_background(canvas_size, index)
        x = max(0, min(canvas_size[0] - transformed.width, int(canvas_size[0] * [0.08, 0.16, 0.05, 0.20, 0.10][index - 1])))
        y = max(0, min(canvas_size[1] - transformed.height, int(canvas_size[1] * [0.10, 0.05, 0.14, 0.08, 0.18][index - 1])))
        composed = background.convert("RGBA")
        composed.alpha_composite(transformed, (x, y))
        composed = composed.convert("RGB")
        composed.save(PILOT / "composites" / f"{name}.jpg", quality=95)
        transformed_alpha = transformed.getchannel("A")
        transformed_bbox = transformed_alpha.getbbox()
        if not transformed_bbox:
            results.append({"image": name + ".jpg", "source": row["review_path"], "mask_status": "MALA", "box_status": "MALA", "bbox": "", "area_fraction": 0, "note": "empty_transformed_alpha"})
            continue
        x1, y1, x2, y2 = [value + offset for value, offset in zip(transformed_bbox, (x, y, x, y))]
        width, height = canvas_size
        cx = ((x1 + x2) / 2) / width
        cy = ((y1 + y2) / 2) / height
        bw = (x2 - x1) / width
        bh = (y2 - y1) / height
        label = f"0 {cx:.8f} {cy:.8f} {bw:.8f} {bh:.8f}\n"
        (PILOT / "labels" / f"{name}.txt").write_text(label, encoding="utf-8")
        preview = composed.copy()
        draw = ImageDraw.Draw(preview)
        draw.rectangle((x1, y1, x2, y2), outline=(0, 180, 0), width=4)
        draw.text((8, 8), f"brake_pad | {name}", fill=(0, 120, 0))
        preview.save(PILOT / "previews" / f"{name}.jpg", quality=95)
        results.append({"image": name + ".jpg", "source": row["review_path"], "mask_status": "PENDING_REVIEW", "box_status": "PENDING_REVIEW", "bbox": json.dumps([cx, cy, bw, bh]), "area_fraction": round(bw * bh, 6), "note": "u2net_cutout_composite"})
    with (PILOT / "synthetic_pilot_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps({"images": len(results), "output": str(PILOT), "masks": str(PILOT / "masks"), "previews": str(PILOT / "previews")}, indent=2))


if __name__ == "__main__":
    main()
