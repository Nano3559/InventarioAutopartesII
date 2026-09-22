import api from "./api";
import { VisionAnalysis, VisionRequestOptions } from "../types/vision";

export class VisionApiError extends Error {
  readonly status: number;
  readonly codigo?: string;

  constructor(status: number, codigo: string | undefined, message: string) {
    super(message);
    this.name = "VisionApiError";
    this.status = status;
    this.codigo = codigo;
  }
}

const CODIGOS_POR_STATUS: Record<number, string> = {
  400: "VISION_IMAGEN_INVALIDA",
  401: "VISION_NO_AUTENTICADO",
  403: "VISION_SIN_PERMISO",
  422: "VISION_NO_CLASIFICADA",
  429: "VISION_LIMITE_ALCANZADO",
  503: "VISION_NO_DISPONIBLE",
  504: "VISION_TIMEOUT",
};

const MENSAJES: Record<string, string> = {
  VISION_IMAGEN_REQUERIDA: "Debe subir una imagen.",
  VISION_IMAGEN_INVALIDA: "La imagen no es válida (JPEG, PNG o WebP, máximo 5 MB).",
  VISION_NO_CLASIFICADA: "No se pudo identificar la pieza en la imagen.",
  VISION_BAJA_CONFIANZA: "No se pudo identificar la pieza con suficiente confianza. Intenta con otra foto.",
  VISION_NO_DISPONIBLE: "El servicio de visión no está disponible en este momento.",
  VISION_TIMEOUT: "El servicio de visión tardó demasiado. Intenta nuevamente.",
  VISION_RESPUESTA_INVALIDA: "El servicio de visión devolvió una respuesta inválida.",
  VISION_LIMITE_ALCANZADO: "Alcanzaste el límite de búsquedas por visión. Intenta en unos minutos.",
};

export function mensajeErrorVision(error: unknown): string {
  if (error instanceof VisionApiError) {
    if (error.codigo && MENSAJES[error.codigo]) return MENSAJES[error.codigo];
    return error.message || "No se pudo buscar por visión. Intenta nuevamente.";
  }
  return "No se pudo buscar por visión. Intenta nuevamente.";
}

function armarFormData(file: File, opts?: VisionRequestOptions): FormData {
  const data = new FormData();
  data.append("image", file);
  if (opts?.vehiculo) {
    if (opts.vehiculo.marca) data.append("vehiculoMarca", opts.vehiculo.marca);
    if (opts.vehiculo.modelo) data.append("vehiculoModelo", opts.vehiculo.modelo);
    if (opts.vehiculo.anio) data.append("vehiculoAnio", opts.vehiculo.anio);
  }
  return data;
}

function armarHeaders(opts?: VisionRequestOptions): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "multipart/form-data" };
  if (opts?.escenarioMock) headers["x-vision-mock-scenario"] = opts.escenarioMock;
  return headers;
}

function extraerErrorVision(error: unknown): VisionApiError {
  const e = error as { response?: { status?: number; data?: { message?: string; codigo?: string } } };
  const status = e?.response?.status || 0;
  const codigo = e?.response?.data?.codigo || CODIGOS_POR_STATUS[status];
  const mensaje = e?.response?.data?.message || (codigo && MENSAJES[codigo]) || "Error al buscar por visión.";
  return new VisionApiError(status, codigo, mensaje);
}

/**
 * Búsqueda por visión pública (sin token). Nunca expone precios internos ni
 * stock exacto (el backend ya serializa la respuesta segura).
 */
export async function detectarVisionPublica(file: File, opts?: VisionRequestOptions): Promise<VisionAnalysis> {
  try {
    const res = await api.post<VisionAnalysis>("/vision/public/detectar", armarFormData(file, opts), {
      headers: armarHeaders(opts),
      signal: opts?.signal,
      timeout: 20000,
    });
    return res.data;
  } catch (error) {
    throw extraerErrorVision(error);
  }
}

/**
 * Búsqueda por visión autenticada (stock exacto por sucursal). Requiere token
 * del panel/móvil; se envía automáticamente por el interceptor de axios.
 */
export async function detectarVisionInterna(file: File, opts?: VisionRequestOptions): Promise<VisionAnalysis> {
  try {
    const res = await api.post<VisionAnalysis>("/vision/detectar", armarFormData(file, opts), {
      headers: armarHeaders(opts),
      signal: opts?.signal,
      timeout: 20000,
    });
    return res.data;
  } catch (error) {
    throw extraerErrorVision(error);
  }
}