import json
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from diagnostico_v2_common import ART, ROOT, UMBRAL_BACKEND, V2_MODEL, CLASSES

HEATMAP_DIR = ART / "heatmaps"
TARGET_LAYERS = [16, 19, 22]
PRIMARY_LAYER = 16


class EigenCAMExtractor:
    def __init__(self, model, layer_ids=(16, 19, 22)):
        self.model = model
        self.seq = model.model.model
        self.layer_ids = list(layer_ids)
        self.hooks = []
        self.activations = {}
        for li in self.layer_ids:
            layer = self.seq[li]
            h = layer.register_forward_hook(self._make_hook(li))
            self.hooks.append(h)

    def _make_hook(self, lid):
        def hook(_m, _inp, out):
            self.activations[lid] = out
        return hook

    def __enter__(self):
        return self

    def __exit__(self, *a):
        for h in self.hooks:
            h.remove()

    def run(self, img_bgr):
        self.activations = {}
        _ = self.model.predict(img_bgr, conf=0.25, imgsz=640, device=0, verbose=False)
        return self.activations


def eigen_cam(act, target_shape):
    t = act[0].detach().float()
    c, h, w = t.shape
    a = t.reshape(c, h * w)
    a = a - a.mean(dim=1, keepdim=True)
    u, s, vh = torch.linalg.svd(a, full_matrices=False)
    cam = vh[0].reshape(h, w).cpu().numpy()
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-9)
    return cv2.resize(cam, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_LINEAR)


def make_heatmap_overlay(img_bgr, cam):
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-9)
    cam_uint = (cam * 255).astype(np.uint8)
    heat = cv2.applyColorMap(cam_uint, cv2.COLORMAP_JET)
    if img_bgr.shape[:2] != heat.shape[:2]:
        heat = cv2.resize(heat, (img_bgr.shape[1], img_bgr.shape[0]))
    return cv2.addWeighted(img_bgr, 0.6, heat, 0.4, 0)


def casos():
    dic = {}
    for cls in ["alternator", "radiator", "headlight", "air_filter"]:
        dic[cls] = {}
        imgs = [p for p in (ART / "original_anotadas").glob(f"*.png")
                if p.name.startswith(f"kaggle_prod__{cls}__")]
        if imgs:
            dic[cls]["original"] = imgs[0]
    # alternator degradada y vacia (de la campaña de robustez)
    dic["alternator"]["degradada_perspectiva"] = \
        next(iter((ART / "variantes_640x480").glob("kaggle_prod__alternator__test__1__C_perspectiva_moderada.png")), None)
    dic["alternator"]["degradada_webcam"] = \
        next(iter((ART / "variantes_640x480").glob("kaggle_prod__alternator__test__5__K_webcam_realista.png")), None)
    dic["alternator"]["vacia_escala"] = \
        next(iter((ART / "variantes_640x480").glob("kaggle_prod__alternator__test__1__J_escala_45.png")), None)
    dic["alternator"]["vacia_webcam"] = \
        next(iter((ART / "variantes_640x480").glob("kaggle_prod__alternator__val__2__K_webcam_realista.png")), None)
    dic["radiator"]["degradada"] = \
        next(iter((ART / "variantes_640x480").glob("kaggle_prod__radiator__test__1__E_blur_moderado.png")), None)
    dic["headlight"]["degradada"] = \
        next(iter((ART / "variantes_640x480").glob("kaggle_prod__headlight__test__1__K_webcam_realista.png")), None)
    return dic


def main():
    HEATMAP_DIR.mkdir(parents=True, exist_ok=True)
    model = YOLO(V2_MODEL)
    casos_sel = casos()
    report = {}
    with EigenCAMExtractor(model, TARGET_LAYERS) as ex:
        for cls, items in casos_sel.items():
            report[cls] = {}
            for tag, p in items.items():
                if p is None or not p.exists():
                    continue
                img_bgr = cv2.imread(str(p))
                dets = model.predict(img_bgr, conf=0.25, imgsz=640, device=0, verbose=False)[0].boxes
                preds = []
                for d in dets:
                    preds.append({
                        "clase": CLASSES[int(d.cls.item())],
                        "conf": round(float(d.conf.item()), 4),
                        "xyxy": [int(v) for v in d.xyxy[0].tolist()],
                    })
                acts = ex.run(img_bgr)
                cams = {lid: eigen_cam(act, img_bgr.shape) for lid, act in acts.items()}
                out = {}
                for lid, cam in cams.items():
                    overlay = make_heatmap_overlay(img_bgr, cam)
                    fname = f"{cls}__{tag}__layer{lid}_heatmap.png"
                    cv2.imwrite(str(HEATMAP_DIR / fname), overlay)
                    out[lid] = fname
                # dumps por clase/tag
                (HEATMAP_DIR / f"{cls}__{tag}__report.json").write_text(
                    json.dumps({"clase": cls, "tag": tag, "predicciones": preds, "heatmaps": out},
                               indent=2, ensure_ascii=False), encoding="utf-8")
                report[cls][tag] = {"imagen": p.name, "predicciones": preds, "heatmaps": out}
                print(cls, tag, p.name, "->", [(c["clase"], c["conf"]) for c in preds])
    (ART / "heatmaps_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()