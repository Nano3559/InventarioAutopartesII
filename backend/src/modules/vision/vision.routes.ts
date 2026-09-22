import { Router, Request, Response } from "express";
import { imageUpload } from "../products/searchImage.service";
import { authenticate, requireTiendaLocation } from "../../shared/middlewares/auth";
import { visionPublicLimiter, visionAuthenticatedLimiter } from "../../shared/middlewares/rateLimit";
import { AuthRequest } from "../../shared/types";
import { generarRespuestaVision, secureLog, VisionResponse } from "./vision.service";
import { VisionServiceError, VisionErrores } from "./vision.errors";
import { visionConfig } from "./vision.config";
import { VehiculoQuery } from "./compatibility";
import { parseString } from "../../shared/middlewares/validate";
import { logger } from "../../shared/utils/logger";

const router = Router();

const ESCENARIOS_MOCK_PERMITIDOS = new Set(["default", "ninguna", "baja_confianza", "categoria_desconocida", "timeout", "error"]);

function leerEscenarioMock(req: Request): string | null {
  if (visionConfig.modo !== "mock") return null;
  const raw = req.headers["x-vision-mock-scenario"];
  if (typeof raw !== "string") return null;
  return ESCENARIOS_MOCK_PERMITIDOS.has(raw) ? raw : null;
}

function leerVehiculo(body: any): VehiculoQuery {
  let marca: string | null = null;
  let modelo: string | null = null;
  let anio: string | null = null;
  try {
    marca = parseString(body?.vehiculoMarca, "vehiculoMarca", { max: 80 });
    modelo = parseString(body?.vehiculoModelo, "vehiculoModelo", { max: 80 });
    anio = parseString(body?.vehiculoAnio, "vehiculoAnio", { max: 40 });
  } catch (err) {
    throw VisionErrores.requestInvalido((err as Error).message);
  }
  if (!marca && !modelo && !anio) return {};
  return { marca, modelo, anio };
}

function manejarVision(run: (req: AuthRequest) => Promise<VisionResponse>) {
  return async (req: Request, res: Response) => {
    try {
      if (!req.file) throw VisionErrores.imagenRequerida;
      const resultado = await run(req as AuthRequest);
      secureLog(resultado, (req as AuthRequest).user ? "interno" : "publico");
      res.json(resultado);
    } catch (error) {
      if (error instanceof VisionServiceError) {
        return res.status(error.status).json({ message: error.message, codigo: error.codigo });
      }
      logger.error("Error interno en búsqueda por visión.", { error: (error as Error)?.message });
      res.status(500).json({ message: "Error interno del servidor" });
    }
  };
}

// POST /api/vision/public/detectar — Búsqueda por visión sin autenticación.
// Orden: visonPublicLimiter → imageUpload → handler (mismo patrón que /search-image).
router.post(
  "/public/detectar",
  visionPublicLimiter,
  imageUpload.single("image"),
  manejarVision(async (req) => {
    const vehiculo = leerVehiculo(req.body);
    const escenarioMock = leerEscenarioMock(req);
    return generarRespuestaVision({ file: req.file!, modo: "publico", vehiculo, escenarioMock });
  })
);

// POST /api/vision/detectar — Búsqueda por visión autenticada (stock exacto, price2).
// Orden: authenticate → requireTiendaLocation → limiter por usuario → imageUpload → handler.
router.post(
  "/detectar",
  authenticate,
  requireTiendaLocation,
  visionAuthenticatedLimiter,
  imageUpload.single("image"),
  manejarVision(async (req) => {
    const vehiculo = leerVehiculo(req.body);
    const escenarioMock = leerEscenarioMock(req);
    return generarRespuestaVision({
      file: req.file!,
      modo: "interno",
      usuario: (req as AuthRequest).user,
      vehiculo,
      escenarioMock,
    });
  })
);

export default router;