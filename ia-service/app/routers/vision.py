"""Router de visión (RepuestoPro Vision IA).

CV-6 Paso 2: GET  /vision/health
CV-6 Paso 3: POST /vision/detect (object detection con best.pt)
CV-6 Paso 4: POST /vision/classify (clasificación auxiliar = detección principal)
"""
from datetime import datetime, timezone
import logging
from typing import Any

import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.schemas.vision import ClassifyResponse, DetectResponse
from app.services import inference

_log = logging.getLogger("vision_ia.router")

router = APIRouter(prefix="/vision", tags=["vision"])

FORMATOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


async def _validar_upload(image: UploadFile) -> bytes:
    """Valida MIME/tamaño y devuelve bytes; lanza HTTPException estable.

    La lectura está acotada a MAX_UPLOAD_BYTES + 1: si el archivo supera el
    límite no se carga entero en memoria, basta con exceder MAX para devolver
    413.
    """
    if image.content_type not in FORMATOS_PERMITIDOS:
        raise HTTPException(status_code=415, detail="formato_no_soportado")
    contenido = await image.read(MAX_UPLOAD_BYTES + 1)
    if not contenido:
        raise HTTPException(status_code=400, detail="archivo_vacio")
    if len(contenido) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="archivo_demasiado_grande")
    return contenido


def _decodificar_contenido(contenido: bytes) -> np.ndarray:
    try:
        pixeles = inference.decodificar_imagen(contenido)
    except ValueError:
        raise HTTPException(status_code=400, detail="imagen_corrupta")
    alto, ancho = pixeles.shape[:2]
    if ancho <= 0 or alto <= 0:
        raise HTTPException(status_code=400, detail="dimensiones_invalidas")
    if ancho * alto > settings.max_image_pixels:
        raise HTTPException(status_code=400, detail="dimensiones_invalidas")
    return pixeles


async def _inferir(image: UploadFile) -> list[dict[str, Any]]:
    contenido = await _validar_upload(image)
    if not inference.modelo_cargado():
        raise HTTPException(status_code=503, detail="modelo_no_disponible")
    pixeles = _decodificar_contenido(contenido)
    try:
        # model.predict() es síncrono y pesado: se ejecuta en el threadpool de
        # FastAPI para no bloquear el event loop; el acceso a la instancia
        # compartida de YOLO queda serializado por el lock interno del servicio.
        return await run_in_threadpool(inference.detectar, pixeles)
    except Exception:  # noqa: BLE001 - error interno sin exponer detalles
        _log.exception("error de inferencia")
        raise HTTPException(status_code=503, detail="error_inferencia")


@router.get("/health")
def health() -> JSONResponse:
    est = inference.estado
    if not est.cargado:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "modelLoaded": False,
                "model": None,
                "modelVersion": None,
                "classes": 0,
                "device": est.device,
                "error": est.error or "modelo_no_cargado",
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "modelLoaded": True,
            "model": est.nombre_modelo,
            "modelVersion": est.version_modelo,
            "classes": est.clases,
            "device": est.device,
        },
    )


@router.post("/detect", response_model=DetectResponse)
async def detect(image: UploadFile = File(...)):
    """Detección de autopartes con YOLO.

    Recibe una imagen multipart/form-data en el campo ``image``
    (jpeg/png/webp, máx 5 MB) y responde con el contrato del backend:
    detecciones[] con categoria, confianza y boundingBox normalizado (0..1),
    ordenadas por confianza descendente.
    """
    detecciones = await _inferir(image)

    return DetectResponse(
        detecciones=detecciones,
        consultadoEn=datetime.now(timezone.utc),
    )


@router.post("/classify", response_model=ClassifyResponse)
async def classify(image: UploadFile = File(...)):
    """Clasificación auxiliar: la detección de MAYOR confianza como clase.

    Reutiliza la misma inferencia YOLO de /vision/detect (misma capa de
    servicio, mismo modelo, mismo conf técnico). Endpoint auxiliar: el
    backend actualmente solo consume /vision/detect.
    """
    detecciones = await _inferir(image)

    if not detecciones:
        return ClassifyResponse(
            clasificacion=None,
            consultadoEn=datetime.now(timezone.utc),
        )

    principal = detecciones[0]  # ya ordenadas por confianza descendente
    return ClassifyResponse(
        clasificacion={
            "categoria": principal["categoria"],
            "confianza": principal["confianza"],
        },
        consultadoEn=datetime.now(timezone.utc),
    )