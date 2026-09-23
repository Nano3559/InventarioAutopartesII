"""Aplicación FastAPI de RepuestoPro Vision IA.

El modelo se carga UNA sola vez al arrancar (lifespan) y se reutiliza.
Un fallo de carga no tumba el arranque: se refleja en /vision/health con
modelLoaded=false y estado degradado (503).
"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.config import settings
from app.routers.vision import router as vision_router
from app.services import inference

log = logging.getLogger("vision_ia.main")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log.info("servicio de visión iniciando")
    try:
        inference.cargar_modelo()
    except Exception as exc:  # noqa: BLE001 - degradación visible en /health
        inference.estado.error = inference.estado.error or "error_de_carga"
        log.error(
            "error al cargar el modelo: %s (ver /vision/health)",
            type(exc).__name__,
        )
    log.info(
        "servicio listo | modelLoaded=%s | device=%s",
        inference.estado.cargado,
        inference.estado.device,
    )
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="RepuestoPro Vision IA",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(vision_router)
    return application


app = create_app()