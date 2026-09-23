import argparse
import json
import time
from pathlib import Path

from ultralytics import YOLO

IA = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Entrenamiento YOLO RepuestoPro (CV-4)")
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--data", default=str(IA / "datasets/processed/dataset.yaml"))
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=-1)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--project", default=str(IA / "runs/detect"))
    parser.add_argument("--name", default="repuestopro_sanity")
    parser.add_argument("--seed", type=int, default=20260922)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--device", default=0)
    args = parser.parse_args()

    started = time.time()
    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        project=args.project,
        name=args.name,
        device=args.device,
        seed=args.seed,
        deterministic=True,
        patience=args.patience,
        plots=True,
        exist_ok=True,
        verbose=True,
    )
    elapsed = round(time.time() - started, 1)
    print(json.dumps({"train_finished": True, "elapsed_s": elapsed, "run_dir": f"{args.project}/{args.name}"}))


if __name__ == "__main__":
    main()