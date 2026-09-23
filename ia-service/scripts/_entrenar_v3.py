from pathlib import Path

from ultralytics import YOLO

IA = Path(__file__).resolve().parents[1]


def main():
    v2 = IA / "runs/detect/repuestopro_yolo11n_v2_domain_balanced/weights/best.pt"
    yaml = IA / "datasets/processed_v3/dataset.yaml"
    model = YOLO(v2)
    model.train(
        data=yaml,
        epochs=100,
        imgsz=640,
        batch=16,
        device=0,
        seed=20260923,
        patience=20,
        project=IA / "runs/detect",
        name="repuestopro_yolo11n_v3_webcam_robust",
        exist_ok=True,
        workers=8,
        verbose=True,
    )
    print("TRAIN_FIN_OK")


if __name__ == "__main__":
    main()