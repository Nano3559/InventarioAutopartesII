import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT / "ia-service/datasets/processed_v2"
BASE_RUN = ROOT / "ia-service/runs/detect/repuestopro_yolo11n_baseline_v1/weights/best.pt"
V2_RUN = ROOT / "ia-service/runs/detect/repuestopro_yolo11n_v2_domain_balanced/weights/best.pt"
CLASSES = ["brake_pad", "brake_rotor", "brake_caliper", "alternator", "oil_filter", "air_filter", "radiator", "headlight"]
CONF = 0.25


def load_rows():
    with (V2 / "processed_v2_manifest.csv").open(newline="", encoding="utf-8") as h:
        return list(csv.DictReader(h))


def read_labels(p):
    boxes = []
    for ln in Path(p).read_text(encoding="utf-8").splitlines():
        parts = ln.split()
        if len(parts) == 5:
            boxes.append((int(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])))
    return boxes


def iou(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    return inter / (max(1e-9, (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter))


def match(preds, gts, conf=CONF):
    gt = defaultdict(list)
    for c, cx, cy, w, h in gts:
        gt[c].append((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
    raw = []
    for p in preds:
        if p.conf.item() < conf:
            continue
        x1, y1, x2, y2 = p.xyxyn[0].tolist()
        raw.append(([x1, y1, x2, y2], p.conf.item(), int(p.cls.item())))
    raw.sort(key=lambda t: -t[1])
    gt_used = defaultdict(set)
    tp = Counter()
    fp = Counter()
    m = Counter()
    for box, confv, cls in raw:
        best, best_i = None, 0.5
        for gi, g in enumerate(gt.get(cls, [])):
            if gi not in gt_used[cls] and iou(*box, *g) >= best_i:
                best, best_i = gi, iou(*box, *g)
        if best is not None:
            gt_used[cls].add(best)
            tp[cls] += 1
        else:
            fp[cls] += 1
    for c, boxes in gt.items():
        for gi in [i for i in range(len(boxes)) if i not in gt_used[c]]:
            m[c] += 1
    return tp, fp, m


def main():
    rows = load_rows()
    test_rows = [r for r in rows if r["split"] == "test"]
    test_imgs = []
    for r in test_rows:
        if not (ROOT / r["processed_image"]).exists():
            continue
        lbl = read_labels(ROOT / r["processed_label"])
        test_imgs.append((ROOT / r["processed_image"], lbl))

    baseline = YOLO(BASE_RUN)
    v2 = YOLO(V2_RUN)

    grouped = defaultdict(list)
    for img_path, labels in test_imgs:
        img_name = img_path.name
        dom = "product" if "kaggle" in str(img_path) or (img_name.startswith("alternator") or img_name.startswith("radiator") or img_name.startswith("headlight")) else "context"
        r = next(rr for rr in rows if rr["processed_image"] == str(img_path.relative_to(ROOT)).replace("\\", "/"))
        grouped[r["domain"]].append((img_path, labels))

    def run_split(imgs, tag):
        out = {}
        for mname, model in (("baseline", baseline), ("v2", v2)):
            tp = Counter(); fp = Counter(); fn = Counter(); hits = Counter(); miss = Counter()
            det_labels = Counter()
            for img_path, labels in imgs:
                preds = model.predict(img_path, conf=CONF, verbose=False)[0].boxes
                t, f, m = match(preds, labels)
                tp += t; fp += f; fn += m
                pred_classes = [int(p.cls.item()) for p in preds if p.conf.item() >= CONF and p.cls.item() < 8]
                for c in set(int(b[0]) for b in labels):
                    miss[c] += 1
                    if t[c] > 0:
                        hits[c] += 1
                det_labels.update(pred_classes)
            precision = {CLASSES[c]: (tp[c] / (tp[c] + fp[c]) if tp[c] + fp[c] else None) for c in set(tp) | set(fp)}
            recall = {CLASSES[c]: (hits[c] / miss[c] if miss[c] else None) for c in miss}
            tot_tp = sum(tp.values()); tot_fp = sum(fp.values()); tot_fn = sum(fn.values())
            out[mname] = {
                "images": len(imgs), "instances": sum(len(l) for _, l in imgs),
                "matched": dict(tp), "fp": dict(fp), "fn": dict(fn),
                "precision": precision, "per_class_recall": recall,
                "overall": {
                    "precision": tot_tp / (tot_tp + tot_fp) if tot_tp + tot_fp else None,
                    "recall": tot_tp / (tot_tp + tot_fn) if tot_tp + tot_fn else None,
                    "mAP50": None,
                },
                "predictions_by_class": dict(det_labels),
            }
        return out

    report = {
        "conf": CONF,
        "test_combined": run_split(test_imgs, "combined"),
        "test_by_domain": {k: run_split(v, k) for k, v in grouped.items()},
    }
    for k, v in grouped.items():
        print(k, len(v))

    # --- Holdout regression: Kaggle alternator valid+test (10 imgs, product, unseen) ---
    holdout = []
    for r in rows:
        if r["split"] in ("val", "test") and r["domain"] == "product" and "ALTERNATOR" in r["source_image"]:
            holdout.append((ROOT / r["processed_image"], read_labels(ROOT / r["processed_label"])))
    # dedupe by image (a single kaggle image should be listed once)
    seen = set(); holdout_u = []
    for img, lbl in holdout:
        if img.name not in seen:
            seen.add(img.name); holdout_u.append((img, lbl))
    print("holdout images:", len(holdout_u))

    def predict_one(model, img_path):
        p = model.predict(img_path, conf=CONF, verbose=False)[0]
        dets = []
        for b in p.boxes:
            if b.conf.item() >= CONF:
                dets.append((int(b.cls.item()), round(float(b.conf.item()), 3)))
        dets = [d for d in dets if d[0] < 8]
        return dets

    holdout_report = {"images": [], "summary": {}}
    for model_name, model in (("baseline", baseline), ("v2", v2)):
        stats = {"correct": 0, "wrong_label": 0, "empty": 0, "confusions": Counter(), "per_image": {}}
        for img_path, labels in holdout_u:
            dets = predict_one(model, img_path)
            gt_c = labels[0][0] if labels else None
            alt = [d for d in dets if CLASSES[d[0]] == "alternator"]
            if not dets:
                stats["empty"] += 1
                stats["per_image"][img_path.name] = []
            elif alt:
                stats["correct"] += 1
                stats["per_image"][img_path.name] = ["alt_conf=%.2f" % alt[0][1]] if alt else []
            else:
                stats["wrong_label"] += 1
                stats["confusions"][CLASSES[dets[0][0]]] += 1
                stats["per_image"][img_path.name] = [CLASSES[d[0]] for d in dets]
        holdout_report["summary"][model_name] = {
            "correct": stats["correct"], "wrong_label": stats["wrong_label"], "empty": stats["empty"],
            "confusions": dict(stats["confusions"]), "per_image_conf": stats["per_image"],
        }
    report["alternator_holdout"] = holdout_report

    (V2 / "evaluation_v2.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()