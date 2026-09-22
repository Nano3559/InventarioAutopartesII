import { describe, it, expect, beforeEach, vi } from "vitest";
import { detectarVisionPublica, detectarVisionInterna, mensajeErrorVision, VisionApiError } from "../visionApi";
import { VisionAnalysis } from "../../types/vision";

vi.mock("../api", () => ({
  default: {
    post: vi.fn(),
  },
}));

import api from "../api";

const postMock = api.post as ReturnType<typeof vi.fn>;

beforeEach(() => {
  postMock.mockReset();
});

const RESPUESTA_VALIDA: VisionAnalysis = {
  version: "1.0",
  consultadoEn: "2026-01-01T00:00:00.000Z",
  proveedor: "mock",
  deteccion: {
    categoria: "Frenos",
    confianza: 0.94,
    confianzaBaja: false,
    categoriaMapeada: "Frenos",
    boundingBox: { x: 0.2, y: 0.3, width: 0.6, height: 0.5 },
  },
  vehiculo: null,
  categoriaCatalogo: { id: 1, nombre: "Frenos" },
  candidatos: [],
  compatibilidad: {
    consultada: true,
    fuente: "base_datos_interna",
    metodologia: "baseline-catalog",
    consultadoEn: "2026-01-01T00:00:00.000Z",
    vehiculo: null,
    verificadas: 0,
    noVerificadas: 0,
    nota: "",
  },
  entrega: { modalidades: ["recoger", "delivery"], sucursales: [] },
};

function archivo(): File {
  return new File(["x"], "pieza.jpg", { type: "image/jpeg" });
}

describe("detectarVisionPublica", () => {
  it("envía FormData con la imagen al endpoint público y devuelve la respuesta tipada", async () => {
    postMock.mockResolvedValue({ data: RESPUESTA_VALIDA });

    const res = await detectarVisionPublica(archivo());

    expect(postMock).toHaveBeenCalledTimes(1);
    const [url, data, config] = postMock.mock.calls[0];
    expect(url).toBe("/vision/public/detectar");
    expect(data).toBeInstanceOf(FormData);
    expect(data.get("image")).toBeInstanceOf(File);
    expect(config.timeout).toBe(20000);
    expect(res).toEqual(RESPUESTA_VALIDA);
  });

  it("incluye vehículo y escenario mock en el formulario/headers cuando se pasan", async () => {
    postMock.mockResolvedValue({ data: RESPUESTA_VALIDA });

    await detectarVisionPublica(archivo(), {
      vehiculo: { marca: "Toyota", modelo: "Hilux", anio: "2020" },
      escenarioMock: "default",
    });

    const [url, data, config] = postMock.mock.calls[0];
    expect(url).toBe("/vision/public/detectar");
    expect(data.get("vehiculoMarca")).toBe("Toyota");
    expect(data.get("vehiculoModelo")).toBe("Hilux");
    expect(data.get("vehiculoAnio")).toBe("2020");
    expect(config.headers["x-vision-mock-scenario"]).toBe("default");
  });
});

describe("detectarVisionInterna", () => {
  it("usa el endpoint autenticado /vision/detectar", async () => {
    postMock.mockResolvedValue({ data: RESPUESTA_VALIDA });

    await detectarVisionInterna(archivo());

    expect(postMock).toHaveBeenCalledWith(
      "/vision/detectar",
      expect.any(FormData),
      expect.objectContaining({ timeout: 20000 })
    );
  });
});

describe("mapeo de errores", () => {
  it("propaga el codigo VISION_BAJA_CONFIANZA desde el backend (422)", async () => {
    postMock.mockRejectedValue({
      response: { status: 422, data: { codigo: "VISION_BAJA_CONFIANZA", message: "No se pudo identificar la pieza con suficiente confianza" } },
    });

    await expect(detectarVisionPublica(archivo())).rejects.toMatchObject({
      name: "VisionApiError",
      status: 422,
      codigo: "VISION_BAJA_CONFIANZA",
    });
    expect(mensajeErrorVision(new VisionApiError(422, "VISION_BAJA_CONFIANZA", "x"))).toContain("suficiente confianza");
  });

  it("traduce 429 al código VISION_LIMITE_ALCANZADO", async () => {
    postMock.mockRejectedValue({ response: { status: 429, data: { status: 429 } } });

    const err = await detectarVisionPublica(archivo()).catch((e) => e);
    expect(err).toBeInstanceOf(VisionApiError);
    expect(err.codigo).toBe("VISION_LIMITE_ALCANZADO");
    expect(mensajeErrorVision(err)).toContain("límite");
  });

  it("traduce 503 y 504 a mensajes claros", () => {
    expect(mensajeErrorVision(new VisionApiError(503, "VISION_NO_DISPONIBLE", "x"))).toContain("no está disponible");
    expect(mensajeErrorVision(new VisionApiError(504, "VISION_TIMEOUT", "x"))).toContain("tardó demasiado");
  });

  it("usa mensaje por defecto ante errores de red sin response", async () => {
    postMock.mockRejectedValue(new Error("Network Error"));

    const err = await detectarVisionPublica(archivo()).catch((e) => e);
    expect(err).toBeInstanceOf(VisionApiError);
    expect(mensajeErrorVision(err)).toContain("Error al buscar por visión");
  });
});