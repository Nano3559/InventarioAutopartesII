import { logger } from "../../shared/utils/logger";

export type VisionMode = "mock" | "http";

const rawMode = (process.env.VISION_MODE || "").toLowerCase().trim();

function resolverModo(): VisionMode {
  if (process.env.VISION_IA_URL) return "http";
  if (rawMode === "http") {
    if (!process.env.VISION_IA_URL) {
      logger.error("VISIÓN: VISION_MODE=http sin VISION_IA_URL; se usará MOCK.", { visionMode: "http" });
      return "mock";
    }
    return "http";
  }
  return "mock";
}

function clampConfianza(value: string | undefined): number {
  const n = Number(value ?? "0.55");
  if (!Number.isFinite(n) || n < 0) return 0.55;
  if (n > 1) return 1;
  return n;
}

const modo = resolverModo();

if (modo === "mock") {
  logger.warn("VISIÓN: modo MOCK activo (detecciones simuladas). Configure VISION_MODE=http y VISION_IA_URL para el modelo real.", {
    visionMode: "mock",
  });
}

export const visionConfig = {
  modo,
  iaUrl: process.env.VISION_IA_URL || null,
  timeoutMs: Math.max(500, parseInt(process.env.VISION_TIMEOUT_MS || "8000", 10) || 8000),
  confianzaMinima: clampConfianza(process.env.VISION_CONFIDENCE_MIN),
};