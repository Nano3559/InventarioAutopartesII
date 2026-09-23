"""Gestión de carga única del modelo YOLO (best.pt).

La instancia se guarda a nivel de módulo (singleton). El modelo se carga una
sola vez por proceso; los llamados posteriores reutilizan la instancia.
Se inicializa desde el lifespan de FastAPI para no cargar el modelo al
simplemente importar módulos (favorece tests).
"""
from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from app.config import settings

_log = logging.getLogger("vision_ia.inference")

CLASSES_ESPERADAS: list[str] = [
    "brake_pad",
    "brake_rotor",
    "brake_caliper",
    "alternator",
    "oil_filter",
    "air_filter",
    "radiator",
    "headlight",
]

CLASE_YOLO_A_CATEGORIA: dict[str, str] = {
    "brake_pad": "pastilla de freno",
    "brake_rotor": "disco de freno",
    "brake_caliper": "caliper",
    "alternator": "alternador",
    "oil_filter": "filtro de aceite",
    "air_filter": "filtro de aire",
    "radiator": "radiador",
    "headlight": "faro",
}

# Confianza técnica para que YOLO emita candidatos. NO es la política de
# producción del backend (VISION_CONFIDENCE_MIN=0.55 es de CV-8/backend).
# Valor conservador estándar de inferencia; documentado, no definitivo.
CONF_TECNICO_INFERENCIA = 0.25
IMGSZ_INFERENCIA = 640

NOMBRE_MODELO_FALLBACK = "YOLO11n"


@dataclass
class EstadoModelo:
    cargado: bool = False
    error: str | None = None
    nombre_modelo: str | None = None
    version_modelo: str | None = None
    clases: int = 0
    device: str | None = None
    modelo: Any = None
    cargas: int = 0


estado = EstadoModelo()
_lock = threading.Lock()
_lock_inferencia = threading.Lock()


def _nombre_modelo(modelo: YOLO) -> str:
    """Intenta leer el nombre del modelo desde el checkpoint (p. ej. yolo11n.pt)."""
    ckpt = getattr(modelo, "ckpt", None) or {}
    if isinstance(ckpt, dict):
        train_args = ckpt.get("train_args") or {}
        if isinstance(train_args, dict) and train_args.get("model"):
            base = str(train_args["model"]).lower()
            if base.endswith(".pt"):
                base = base[:-3]
            if base.startswith("yolo"):
                return "YOLO" + base[4:]
            # Solo valores simples (arquitectura/nombre). Si el campo registra
            # una ruta (p. ej. los pesos de partida de un reentrenado), no se
            # expone ese path; se usa el nombre generico del YOLO.
            if base and not any(ch in base for ch in "/\\:"):
                return base[0].upper() + base[1:]
    return NOMBRE_MODELO_FALLBACK


def _version_modelo(path: Path) -> str:
    """Etiqueta informativa del checkpoint versionado (p. ej. nombre del run dir).

    Si el peso vive directamente en models/ (checkpoint oficial versionado),
    usa el nombre del archivo (stem). Si vive dentro de runs/detect/<run>/weights/
    usa el nombre del run. Mantiene compatibilidad con health sin exponer rutas
    absolutas ni nombres de archivo internos (véase test_health_no_expone_ruta_modelo).
    """
    ruta = path.resolve()
    if ruta.parent.name == "models":
        return path.stem
    nombre_run = ruta.parent.parent.name
    if nombre_run and nombre_run not in ("weights", "detect", "runs"):
        return nombre_run
    return path.stem


def _resolver_device(device: str) -> torch.device:
    """Traduce el valor de configuración a un torch.device válido.

    Acepta "cpu", "cuda", "cuda:0", "0", etc. Si se pide GPU y no hay CUDA,
    cae a CPU (el health reporta el device realmente usado).
    """
    valor = str(device).strip().lower()
    if valor in ("cpu", "none"):
        return torch.device("cpu")
    if valor == "cuda" or valor.startswith("cuda:"):
        dev = torch.device(valor)
        return dev if torch.cuda.is_available() else torch.device("cpu")
    if valor.isdigit():
        if torch.cuda.is_available():
            return torch.device(f"cuda:{valor}")
        return torch.device("cpu")
    return torch.device(valor)


def cargar_modelo(
    path: str | Path | None = None,
    device: str | None = None,
) -> EstadoModelo:
    """Carga best.pt UNA sola vez y verifica las 8 clases esperadas.

    Si ya está cargado (mismo proceso) reutiliza la instancia.
    Ante cualquier error de carga deja el estado degradado y relanza.
    """
    global estado
    path = Path(path) if path is not None else Path(settings.model_path)
    device = device if device is not None else settings.device

    with _lock:
        if estado.cargado and estado.modelo is not None:
            return estado

        if not path.is_file():
            estado.cargado = False
            estado.error = "modelo_no_encontrado"
            estado.nombre_modelo = None
            estado.version_modelo = None
            estado.clases = 0
            estado.device = None
            estado.modelo = None
            raise FileNotFoundError(f"No existe el modelo en: {path}")

        try:
            dispositivo = _resolver_device(device)
            modelo = YOLO(str(path))
            modelo.to(dispositivo)
            nombres = list(modelo.names.values())

            if nombres != CLASSES_ESPERADAS:
                raise RuntimeError(
                    f"Clases del modelo inesperadas ({len(nombres)}): {nombres}"
                )

            estado.cargado = True
            estado.error = None
            estado.nombre_modelo = _nombre_modelo(modelo)
            estado.version_modelo = _version_modelo(path)
            estado.clases = len(nombres)
            estado.device = str(dispositivo)
            estado.modelo = modelo
            estado.cargas += 1
            _log.info(
                "modelo cargado: %s | version=%s | archivo=%s | device=%s | clases=%d | cargas=%d",
                estado.nombre_modelo,
                estado.version_modelo,
                path.resolve(),
                estado.device,
                estado.clases,
                estado.cargas,
            )
        except Exception as exc:  # noqa: BLE001 - cualquier error de carga es degradación
            estado.cargado = False
            estado.error = "error_de_carga"
            estado.nombre_modelo = None
            estado.version_modelo = None
            estado.clases = 0
            estado.device = None
            estado.modelo = None
            raise exc

        return estado


def modelo_cargado() -> bool:
    return estado.cargado and estado.modelo is not None


def obtener_modelo() -> Any:
    if not modelo_cargado():
        raise RuntimeError("Modelo de visión no cargado")
    return estado.modelo


def contador_cargas() -> int:
    """Número de veces que best.pt fue cargado en el proceso (debe ser 1)."""
    return estado.cargas


def calentar_modelo() -> None:
    """Ejecuta una predicción sintética en el arranque (lifespan).

    El primer predict() tras cargar los pesos compila kernels/autotune de CUDA
    (varios segundos) y supera el timeout de 8 s del backend, aunque la carga
    del modelo haya sido rápida. Con el warmup esa inicialización ocurre antes
    de aceptar tráfico y la primera petición real ya encuentra la inferencia en
    caliente. Tolerante: si falla, el servicio sigue degradado y se reintenta
    por petición real (quedando a merced del timeout).
    """
    if not modelo_cargado():
        return
    sintetica = np.zeros((IMGSZ_INFERENCIA, IMGSZ_INFERENCIA, 3), dtype=np.uint8)
    inicio = time.perf_counter()
    try:
        detectar(sintetica)
        _log.info(
            "warmup de inferencia completado en %.2f s",
            time.perf_counter() - inicio,
        )
    except Exception:  # noqa: BLE001 - el warmup es best-effort
        _log.warning(
            "warmup de inferencia fallido en %.2f s; se reintentará en uso",
            time.perf_counter() - inicio,
            exc_info=True,
        )


def decodificar_imagen(contenido: bytes) -> np.ndarray:
    """Decodifica bytes arbitrarios a imagen BGR. Todo en memoria.

    No se confía en la extensión ni en el Content-Type: se valida con OpenCV.
    """
    if not contenido:
        raise ValueError("archivo_vacio")
    arreglo = np.frombuffer(contenido, dtype=np.uint8)
    imagen = cv2.imdecode(arreglo, cv2.IMREAD_COLOR)
    if imagen is None or imagen.size == 0:
        raise ValueError("imagen_corrupta")
    return imagen


def _a_numpy(tensor_o_array: Any) -> np.ndarray:
    if torch.is_tensor(tensor_o_array):
        return tensor_o_array.cpu().numpy()
    return np.asarray(tensor_o_array)


def detectar(
    pixeles: np.ndarray,
    imgsz: int = IMGSZ_INFERENCIA,
    conf: float = CONF_TECNICO_INFERENCIA,
    device: str | None = None,
) -> list[dict[str, Any]]:
    """Ejecuta YOLO sobre píxeles BGR y devuelve detecciones del contrato.

    Devuelve lista de dicts ya normalizadas (0..1) y ordenadas por confianza
    descendente. Si YOLO no produce objetos válidos devuelve lista vacía.
    No expone class_id/class_name internos del modelo.
    """
    modelo = obtener_modelo()
    dispositivo = device or estado.device or "cpu"

    # La instancia YOLO es compartida: se serializa el acceso a predict con un
    # lock. Es la protección mínima contra uso concurrente de la misma instancia
    # (el endpoint ya ejecuta detectar() en threadpool, por lo que esperar aquí
    # no bloquea el event loop de FastAPI).
    with _lock_inferencia:
        resultado = modelo.predict(
            pixeles,
            imgsz=imgsz,
            conf=conf,
            device=dispositivo,
            verbose=False,
        )
    # predict() devuelve list[Results]; se normaliza al objeto Results.
    if isinstance(resultado, (list, tuple)):
        resultado = resultado[0]
    boxes = getattr(resultado, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    altura, ancho, *_ = pixeles.shape

    xyxy = _a_numpy(boxes.xyxy)
    clases = _a_numpy(boxes.cls).astype(float)
    confianzas = _a_numpy(boxes.conf).astype(float)
    nombres = getattr(modelo, "names", {}) or {}

    salida: list[dict[str, Any]] = []

    for fila in range(len(xyxy)):
        cls_valor = float(clases[fila])
        confianza = float(confianzas[fila])
        x1p, y1p, x2p, y2p = (float(v) for v in xyxy[fila])

        if not all(math.isfinite(v) for v in (x1p, y1p, x2p, y2p)):
            continue
        if not math.isfinite(confianza) or not (0.0 <= confianza <= 1.0):
            continue
        # Un class_id valido es un numero finito que representa EXACTAMENTE un
        # entero en rango 0..7. Fracciones (2.7), no finitos (NaN/Inf) y fuera
        # de rango se descartan fail-safe: nunca se trunca a un indice distinto.
        if not math.isfinite(cls_valor) or cls_valor != float(int(cls_valor)):
            continue
        clase_id = int(cls_valor)
        if not (0 <= clase_id < len(nombres)):
            continue
        categoria = CLASE_YOLO_A_CATEGORIA.get(nombres[clase_id])
        if categoria is None:
            # Clase fuera de las 8 esperadas: descarte explícito fail-safe.
            continue

        x1 = min(float(ancho), max(0.0, x1p))
        y1 = min(float(altura), max(0.0, y1p))
        x2 = min(float(ancho), max(0.0, x2p))
        y2 = min(float(altura), max(0.0, y2p))
        if x2 <= x1 or y2 <= y1:
            continue

        a_x = round(x1 / ancho, 6)
        a_y = round(y1 / altura, 6)
        a_w = round((x2 - x1) / ancho, 6)
        a_h = round((y2 - y1) / altura, 6)

        # Garantiza x+width<=1 y y+height<=1 sin depender de redondeo.
        a_w = min(a_w, 1.0 - a_x)
        a_h = min(a_h, 1.0 - a_y)
        if a_w <= 0.0 or a_h <= 0.0:
            continue

        salida.append(
            {
                "categoria": categoria,
                "confianza": confianza,
                "boundingBox": {
                    "x": a_x,
                    "y": a_y,
                    "width": a_w,
                    "height": a_h,
                },
            }
        )

    salida.sort(key=lambda d: d["confianza"], reverse=True)
    return salida