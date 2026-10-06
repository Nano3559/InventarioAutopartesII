"""Auditoría reproducible del estado de dataset y checkpoint (solo lectura).

Mide, sobre lo que realmente existe en disco:
- checkpoint: arquitectura, escala, clases y métricas embebidas;
- manifests: filas declaradas vs. archivos presentes, reparto por clase,
  reparto por split original, rutas rotas y duplicados declarados;
- batches de anotación/revisión: cuántas filas tienen ground truth real.

No escribe ni modifica nada. Uso:
    python scripts/auditar_dataset.py [--raiz RAIZ]
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

MANIFEST_DATASET = RAIZ / "datasets" / "dataset_manifest.csv"
MANIFEST_ANNOT = RAIZ / "datasets" / "annotation_batch" / "annotation_batch_manifest.csv"
MANIFEST_REVIEW = RAIZ / "datasets" / "review" / "review_manifest.csv"
MODELOS = RAIZ / "models"


def leer_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def contar_existentes(rows: list[dict[str, str]], campo: str) -> tuple[int, int, list[str]]:
    presentes = ausentes = 0
    rotas: list[str] = []
    for row in rows:
        crudo = (row.get(campo) or "").strip()
        if not crudo:
            continue
        # Las rutas del manifest son relativas a la raiz del repositorio.
        candidato = RAIZ.parent / crudo if crudo.startswith("ia-service/") else RAIZ.parent / crudo
        if candidato.exists():
            presentes += 1
        else:
            ausentes += 1
            rotas.append(crudo)
    return presentes, ausentes, rotas


def seccion_checkpoint() -> dict:
    info: dict = {"modelos": []}
    if not MODELOS.exists():
        return info
    for ckpt in sorted(MODELOS.glob("*.pt")):
        entrada = {"archivo": ckpt.name, "bytes": ckpt.stat().st_size}
        try:
            from ultralytics import YOLO  # import perezoso: es lento

            m = YOLO(str(ckpt))
            entrada["task"] = m.task
            entrada["arquitectura"] = m.model.yaml.get("yaml_file") or m.model.yaml.get("scale")
            entrada["escala"] = m.model.yaml.get("scale")
            entrada["depth_multiple"] = m.model.yaml.get("depth_multiple")
            entrada["width_multiple"] = m.model.yaml.get("width_multiple")
            entrada["parametros"] = sum(p.numel() for p in m.model.parameters())
            entrada["clases"] = {str(k): v for k, v in sorted(m.names.items())}
            meta = m.ckpt or {}
            entrada["fecha_entrenamiento"] = meta.get("date")
            entrada["ultralytics"] = meta.get("version")
            args = meta.get("train_args") or {}
            entrada["args_entrenamiento"] = {
                k: args.get(k)
                for k in (
                    "model",
                    "data",
                    "epochs",
                    "batch",
                    "imgsz",
                    "seed",
                    "optimizer",
                    "patience",
                    "pretrained",
                    "name",
                )
                if args.get(k) is not None
            }
            res = meta.get("train_results2")
            if isinstance(res, dict):
                entrada["resultados"] = res
        except Exception as exc:  # noqa: BLE001 - el informe no debe romperse
            entrada["error"] = f"{type(exc).__name__}: {exc}"
        info["modelos"].append(entrada)
    return info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="salida en JSON")
    args = ap.parse_args()

    ds = leer_csv(MANIFEST_DATASET)
    an = leer_csv(MANIFEST_ANNOT)
    rv = leer_csv(MANIFEST_REVIEW)

    informe: dict = {"dataset_manifest": {}, "annotation_batch": {}, "review_manifest": {}}

    # --- dataset_manifest -------------------------------------------------
    if ds:
        presentes, ausentes, rotas = contar_existentes(ds, "local_path")
        por_clase = Counter((r.get("target_class") or "").strip() for r in ds)
        por_split = Counter((r.get("original_split") or "").strip() for r in ds)
        por_fuente = Counter((r.get("source") or "").strip() for r in ds)
        ids = defaultdict(set)
        for r in ds:
            ids[(r.get("target_class") or "").strip()].add((r.get("target_class_id") or "").strip())
        # clase x split
        clase_split: dict[str, Counter] = defaultdict(Counter)
        for r in ds:
            clase_split[(r.get("target_class") or "").strip()][(r.get("original_split") or "").strip()] += 1
        # duplicados declarados
        rutas = [(r.get("local_path") or "").strip() for r in ds]
        dup = [k for k, v in Counter(rutas).items() if v > 1 and k]
        informe["dataset_manifest"] = {
            "filas": len(ds),
            "imagenes_presentes": presentes,
            "imagenes_ausentes": ausentes,
            "rutas_rotas_ejemplo": rotas[:5],
            "distribucion_clase": dict(sorted(por_clase.items(), key=lambda kv: -kv[1])),
            "distribucion_split": dict(por_split),
            "distribucion_fuente": dict(por_fuente),
            "ids_por_clase": {k: sorted(v) for k, v in sorted(ids.items())},
            "clase_por_split": {k: dict(v) for k, v in sorted(clase_split.items())},
            "rutas_duplicadas": len(dup),
            "duplicados_ejemplo": dup[:5],
        }

    # --- annotation_batch -------------------------------------------------
    if an:
        presentes, ausentes, _ = contar_existentes(an, "working_path")
        estado = Counter((r.get("annotation_status") or "").strip() for r in an)
        gt = Counter((r.get("has_ground_truth") or "").strip() for r in an)
        con_label = sum(1 for r in an if (r.get("label_path") or "").strip())
        anotadas_por_clase = Counter(
            (r.get("target_class") or "").strip() for r in an
            if (r.get("annotation_status") or "").strip() == "ANNOTATED"
        )
        informe["annotation_batch"] = {
            "filas": len(an),
            "imagenes_presentes": presentes,
            "imagenes_ausentes": ausentes,
            "por_estado": dict(estado),
            "por_ground_truth": dict(gt),
            "con_label_path": con_label,
            "sin_label_path": len(an) - con_label,
            "anotadas_por_clase": dict(anotadas_por_clase),
        }

    # --- review_manifest --------------------------------------------------
    if rv:
        presentes, ausentes, _ = contar_existentes(rv, "review_path")
        estado = Counter((r.get("review_status") or "").strip() for r in rv)
        con_label = sum(1 for r in rv if (r.get("review_label_path") or "").strip())
        informe["review_manifest"] = {
            "filas": len(rv),
            "imagenes_presentes": presentes,
            "imagenes_ausentes": ausentes,
            "por_estado": dict(estado),
            "con_review_label_path": con_label,
            "sin_review_label_path": len(rv) - con_label,
        }

    informe["checkpoints"] = seccion_checkpoint()

    print(json.dumps(informe, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()