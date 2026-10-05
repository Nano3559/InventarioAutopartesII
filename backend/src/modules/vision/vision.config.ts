import { logger } from "../../shared/utils/logger";

/**
 * Proveedor unico de vision: HTTP real contra `ia-service` (FastAPI + YOLO).
 *
 * No existe ningun modo simulado ni selector de entorno. Si `VISION_IA_URL` no
 * esta definida, el proveedor responde 503 VISION_NO_DISPONIBLE; el endpoint
 * nunca entrega detecciones inventadas.
 */
export type VisionModo = "http";

export interface VisionEnv {
  VISION_IA_URL?: string;
  NODE_ENV?: string;
}

export interface ModoResuelto {
  modo: VisionModo;
  /** true cuando falta VISION_IA_URL: el endpoint debe responder 503, nunca simular. */
  requiereIA: boolean;
  produccion: boolean;
  motivo: string;
}

function esProduccion(env: VisionEnv): boolean {
  return (env.NODE_ENV || "").toLowerCase().trim() === "production";
}

/**
 * Resolucion del proveedor de vision. El modo es siempre `http`; lo unico que
 * se decide aqui es si la IA esta configurada (`requiereIA`) o el endpoint debe
 * fallar cerrado con 503.
 *
 * - Con `VISION_IA_URL` -> modelo real.
 * - Sin `VISION_IA_URL` -> `requiereIA: true`: se responde 503, tanto en
 *   produccion como en desarrollo. No hay degradacion a datos simulados.
 */
export function resolverVisionModo(env: VisionEnv): ModoResuelto {
  const produccion = esProduccion(env);
  const tieneUrl = Boolean((env.VISION_IA_URL || "").trim());

  if (tieneUrl) {
    return { modo: "http", requiereIA: false, produccion, motivo: "VISION_IA_URL presente" };
  }

  return {
    modo: "http",
    requiereIA: true,
    produccion,
    motivo: "sin VISION_IA_URL: la vision falla cerrado con 503, no hay proveedor simulado",
  };
}

function clampConfianza(value: string | undefined): number {
  const n = Number(value ?? "0.55");
  if (!Number.isFinite(n) || n < 0) return 0.55;
  if (n > 1) return 1;
  return n;
}

const resuelto = resolverVisionModo(process.env);

if (resuelto.requiereIA) {
  logger.error(
    "VISIÓN: falta VISION_IA_URL. El endpoint de visión respondera 503 VISION_NO_DISPONIBLE; no se simulara ninguna deteccion.",
    { visionMode: resuelto.modo, motivo: resuelto.motivo }
  );
} else if (resuelto.produccion && !((process.env.VISION_IA_KEY || "").trim())) {
  // El backend puede hablar con la IA sin secreto (red privada), pero si el
  // ia-service exige `X-Vision-Key` cada llamada respondersa 401/403 -> 503.
  logger.warn(
    "VISIÓN: VISION_IA_URL esta definida pero VISION_IA_KEY no. Si ia-service exige autenticacion, el endpoint respondera 503.",
    { visionMode: resuelto.modo }
  );
}

export const visionConfig = {
  modo: resuelto.modo,
  requiereIA: resuelto.requiereIA,
  produccion: resuelto.produccion,
  iaUrl: (process.env.VISION_IA_URL || "").trim() || null,
  /** Secreto de servicio opcional para autenticar backend -> ia-service (header X-Vision-Key). */
  iaKey: (process.env.VISION_IA_KEY || "").trim() || null,
  timeoutMs: Math.max(500, parseInt(process.env.VISION_TIMEOUT_MS || "8000", 10) || 8000),
  confianzaMinima: clampConfianza(process.env.VISION_CONFIDENCE_MIN),
};