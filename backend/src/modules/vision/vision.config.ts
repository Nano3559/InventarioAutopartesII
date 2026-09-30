import { logger } from "../../shared/utils/logger";

export type VisionMode = "mock" | "http";

export interface VisionEnv {
  VISION_MODE?: string;
  VISION_IA_URL?: string;
  NODE_ENV?: string;
}

export interface ModoResuelto {
  modo: VisionMode;
  /** true cuando el modo remoto no tiene URL configurada: el endpoint debe responder 503, nunca simular. */
  requiereIA: boolean;
  produccion: boolean;
  motivo: string;
}

function esProduccion(env: VisionEnv): boolean {
  return (env.NODE_ENV || "").toLowerCase().trim() === "production";
}

function modoExplicito(env: VisionEnv): VisionMode | null {
  const raw = (env.VISION_MODE || "").toLowerCase().trim();
  if (raw === "mock") return "mock";
  if (raw === "http" || raw === "remote") return "http";
  return null;
}

/**
 * Regla de resolucion del proveedor de vision:
 *
 * - `VISION_MODE` explicito manda (mock | http | remote).
 * - Sin `VISION_MODE`, si hay `VISION_IA_URL` se usa el modelo real.
 * - Sin `VISION_MODE` y sin URL:
 *   - fuera de produccion -> mock (desarrollo/pruebas).
 *   - en produccion -> modo remoto SIN URL: el proveedor responde 503
 *     VISION_NO_DISPONIBLE. Nunca se entregan detecciones simuladas.
 */
export function resolverVisionMode(env: VisionEnv): ModoResuelto {
  const produccion = esProduccion(env);
  const tieneUrl = Boolean((env.VISION_IA_URL || "").trim());
  const explicito = modoExplicito(env);

  if (explicito) {
    return {
      modo: explicito,
      requiereIA: explicito === "http" && !tieneUrl,
      produccion,
      motivo: "VISION_MODE explicito",
    };
  }

  if (tieneUrl) {
    return { modo: "http", requiereIA: false, produccion, motivo: "VISION_IA_URL presente" };
  }

  if (produccion) {
    return { modo: "http", requiereIA: true, produccion, motivo: "produccion sin VISION_IA_URL: mock prohibido" };
  }

  return { modo: "mock", requiereIA: false, produccion, motivo: "desarrollo sin VISION_IA_URL" };
}

function clampConfianza(value: string | undefined): number {
  const n = Number(value ?? "0.55");
  if (!Number.isFinite(n) || n < 0) return 0.55;
  if (n > 1) return 1;
  return n;
}

const resuelto = resolverVisionMode(process.env);

if (resuelto.modo === "mock") {
  const mensaje = "VISIÓN: modo MOCK activo (detecciones simuladas, no provienen del modelo).";
  if (resuelto.produccion) {
    logger.error(`${mensaje} VISION_MODE=mock en produccion es una decision explicita del operador.`, {
      visionMode: "mock",
      motivo: resuelto.motivo,
    });
  } else {
    logger.warn(`${mensaje} Configure VISION_MODE=http y VISION_IA_URL para usar el modelo real.`, {
      visionMode: "mock",
      motivo: resuelto.motivo,
    });
  }
}

if (resuelto.requiereIA) {
  logger.error(
    "VISIÓN: se espera IA real pero falta VISION_IA_URL. El endpoint de visión respondera 503 VISION_NO_DISPONIBLE; no se simulara ninguna deteccion.",
    { visionMode: resuelto.modo, motivo: resuelto.motivo }
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
