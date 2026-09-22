export const VISION_API_VERSION = "1.0";

export interface VisionBoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface VisionDetection {
  categoria: string;
  confianza: number;
  boundingBox?: VisionBoundingBox | null;
}

export interface VisionProviderResult {
  proveedor: string;
  consultadoEn: string;
  detecciones: VisionDetection[];
}

export function esBoundingBoxValido(value: unknown): value is VisionBoundingBox {
  if (!value || typeof value !== "object") return false;
  const box = value as Record<string, unknown>;
  return (
    typeof box.x === "number" &&
    Number.isFinite(box.x) &&
    typeof box.y === "number" &&
    Number.isFinite(box.y) &&
    typeof box.width === "number" &&
    Number.isFinite(box.width) &&
    typeof box.height === "number" &&
    Number.isFinite(box.height)
  );
}

export function esVisionDetection(value: unknown): value is VisionDetection {
  if (!value || typeof value !== "object") return false;
  const det = value as Record<string, unknown>;
  if (typeof det.categoria !== "string" || det.categoria.trim().length === 0 || det.categoria.length > 120) return false;
  if (typeof det.confianza !== "number" || !Number.isFinite(det.confianza) || det.confianza < 0 || det.confianza > 1) {
    return false;
  }
  if (det.boundingBox !== undefined && det.boundingBox !== null && !esBoundingBoxValido(det.boundingBox)) return false;
  return true;
}

/**
 * Validación runtime del payload de detecciones (TC-1): no basta con los tipos
 * TypeScript. Si el array no es un array o algún ítem no cumple el contrato, la
 * respuesta del proveedor se considera inválida (→ 503 VISION_RESPUESTA_INVALIDA).
 */
export function validarRespuestaVision(value: unknown): { valida: boolean; detecciones: VisionDetection[] } {
  if (!Array.isArray(value)) return { valida: false, detecciones: [] };
  const detecciones: VisionDetection[] = [];
  for (const item of value) {
    if (!esVisionDetection(item)) return { valida: false, detecciones };
    detecciones.push(item);
  }
  return { valida: true, detecciones };
}