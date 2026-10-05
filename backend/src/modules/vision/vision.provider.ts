import { VisionProviderResult, validarRespuestaVision } from "./contract";
import { VisionErrores, VisionServiceError } from "./vision.errors";
import { visionConfig } from "./vision.config";
import { logger } from "../../shared/utils/logger";

export interface VisionInput {
  buffer: Buffer;
  mimetype: string;
  originalName: string;
}

/**
 * Proveedor de detecciones.
 *
 * Existe una sola implementacion: `HttpVisionProvider`, que llama a `ia-service`
 * (FastAPI + YOLO) por HTTP real. El runtime no incluye ningun proveedor
 * simulado; si la IA no esta disponible el endpoint falla cerrado con 503/504 en
 * lugar de devolver detecciones inventadas.
 *
 * Los dobles de prueba viven en `src/testing/` y se ejercitan por HTTP real,
 * sin reemplazar esta clase en produccion.
 */
export interface VisionProvider {
  readonly tipo: string;
  detectar(input: VisionInput): Promise<VisionProviderResult>;
}

export class HttpVisionProvider implements VisionProvider {
  readonly tipo = "http";

  private async llamarIA(input: VisionInput): Promise<Response> {
    const url = visionConfig.iaUrl;
    if (!url) {
      logger.error("VISIÓN: se requiere IA real pero VISION_IA_URL no esta configurada; se responde 503 sin simular detecciones.");
      throw VisionErrores.servicioNoDisponible();
    }

    const extension = (input.mimetype.split("/")[1] || "jpg").replace(/[^a-z0-9]/gi, "");
    const nombreArchivo = `vision_${Date.now()}.${extension || "jpg"}`;

    const form = new FormData();
    form.append("image", new Blob([new Uint8Array(input.buffer)], { type: input.mimetype }), nombreArchivo);

    const headers: Record<string, string> = {};
    if (visionConfig.iaKey) {
      headers["X-Vision-Key"] = visionConfig.iaKey;
    }

    return fetch(`${url.replace(/\/$/, "")}/vision/detect`, {
      method: "POST",
      body: form,
      headers,
      signal: AbortSignal.timeout(visionConfig.timeoutMs),
    });
  }

  async detectar(input: VisionInput): Promise<VisionProviderResult> {
    let response: Response;
    try {
      response = await this.llamarIA(input);
    } catch (error) {
      // `llamarIA` ya lanza errores del dominio (503 sin URL): se respetan tal cual
      // en vez de reportarlos como fallo de red.
      if (error instanceof VisionServiceError) throw error;
      if (error instanceof Error) {
        if (error.name === "TimeoutError" || error.name === "AbortError") throw VisionErrores.tiempoAgotado();
      }
      logger.warn("Visión (http): fallo de red hacia la IA.", { error: String(error) });
      throw VisionErrores.servicioNoDisponible();
    }

    if (!response.ok) {
      logger.warn(`Visión (http): la IA respondió status=${response.status}.`, { status: response.status });
      if (response.status === 408 || response.status === 504) throw VisionErrores.tiempoAgotado();
      // 401/403: la IA exige X-Vision-Key y el backend no la envio (o es incorrecta).
      // Se degrada a 503 controlado, nunca a detecciones simuladas.
      throw VisionErrores.servicioNoDisponible();
    }

    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      throw VisionErrores.respuestaInvalida();
    }

    const deteccionesCampo = (payload as Record<string, unknown>)?.detecciones;
    const { valida, detecciones } = validarRespuestaVision(deteccionesCampo);
    if (!valida) throw VisionErrores.respuestaInvalida();

    logger.info("Visión (http): detección recibida del modelo.", { detecciones: detecciones.length });

    return {
      proveedor: "http",
      consultadoEn: (payload as Record<string, unknown>)?.consultadoEn
        ? String((payload as Record<string, unknown>).consultadoEn)
        : new Date().toISOString(),
      detecciones,
    };
  }
}

export function withVisionTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => reject(VisionErrores.tiempoAgotado()), ms);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      (error) => {
        clearTimeout(timer);
        reject(error);
      }
    );
  });
}

/** El proveedor es siempre HTTP real: no hay selector de modo en el runtime. */
export const visionProvider: VisionProvider = new HttpVisionProvider();