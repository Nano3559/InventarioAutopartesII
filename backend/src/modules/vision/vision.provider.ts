import { VisionProviderResult, VisionDetection, validarRespuestaVision } from "./contract";
import { VisionErrores } from "./vision.errors";
import { visionConfig } from "./vision.config";
import { logger } from "../../shared/utils/logger";

export interface VisionInput {
  buffer: Buffer;
  mimetype: string;
  originalName: string;
}

export interface VisionProvider {
  readonly tipo: string;
  detectar(input: VisionInput, escenario?: string): Promise<VisionProviderResult>;
}

const ESCENARIOS_MOCK = new Set(["default", "ninguna", "baja_confianza", "categoria_desconocida", "timeout", "error"]);

const MOCK_DETECCIONES: Record<string, VisionDetection[]> = {
  default: [
    { categoria: "Frenos", confianza: 0.94, boundingBox: { x: 0.2, y: 0.3, width: 0.6, height: 0.5 } },
  ],
  baja_confianza: [{ categoria: "Frenos", confianza: 0.31 }],
  categoria_desconocida: [{ categoria: "Instrumento desconocido XXYZ", confianza: 0.9 }],
  ninguna: [],
};

export class MockVisionProvider implements VisionProvider {
  readonly tipo = "mock";

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async detectar(input: VisionInput, escenario?: string): Promise<VisionProviderResult> {
    const escenarioValido =
      visionConfig.modo === "mock" && escenario && ESCENARIOS_MOCK.has(escenario) ? escenario : "default";

    if (escenarioValido === "timeout") {
      await this.sleep(visionConfig.timeoutMs + 1500);
      throw VisionErrores.tiempoAgotado();
    }
    if (escenarioValido === "error") {
      await this.sleep(50);
      throw VisionErrores.servicioNoDisponible();
    }

    logger.info("Visión (mock): imagen recibida para detección simulada.", {
      bytes: input.buffer.length,
      mimetype: input.mimetype,
      escenario: escenarioValido,
      sizeOk: input.buffer.length <= 5 * 1024 * 1024,
    });

    const detecciones = MOCK_DETECCIONES[escenarioValido] ?? MOCK_DETECCIONES.default;
    const { valida } = validarRespuestaVision(detecciones);
    if (!valida) throw VisionErrores.respuestaInvalida();

    return {
      proveedor: "mock",
      consultadoEn: new Date().toISOString(),
      detecciones,
    };
  }
}

export class HttpVisionProvider implements VisionProvider {
  readonly tipo = "http";

  private async llamarIA(input: VisionInput): Promise<Response> {
    const url = visionConfig.iaUrl;
    if (!url) throw VisionErrores.servicioNoDisponible();

    const extension = (input.mimetype.split("/")[1] || "jpg").replace(/[^a-z0-9]/gi, "");
    const nombreArchivo = `vision_${Date.now()}.${extension || "jpg"}`;

    const form = new FormData();
    form.append("image", new Blob([new Uint8Array(input.buffer)], { type: input.mimetype }), nombreArchivo);

    return fetch(`${url.replace(/\/$/, "")}/vision/detect`, {
      method: "POST",
      body: form,
      signal: AbortSignal.timeout(visionConfig.timeoutMs),
    });
  }

  async detectar(input: VisionInput, _escenario?: string): Promise<VisionProviderResult> {
    let response: Response;
    try {
      response = await this.llamarIA(input);
    } catch (error) {
      if (error instanceof Error) {
        if (error.name === "TimeoutError" || error.name === "AbortError") throw VisionErrores.tiempoAgotado();
      }
      logger.warn("Visión (http): fallo de red hacia la IA.", { error: String(error) });
      throw VisionErrores.servicioNoDisponible();
    }

    if (!response.ok) {
      logger.warn(`Visión (http): la IA respondió status=${response.status}.`, { status: response.status });
      if (response.status === 408 || response.status === 504) throw VisionErrores.tiempoAgotado();
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

function crearProvider(): VisionProvider {
  return visionConfig.modo === "http" ? new HttpVisionProvider() : new MockVisionProvider();
}

export const visionProvider: VisionProvider = crearProvider();