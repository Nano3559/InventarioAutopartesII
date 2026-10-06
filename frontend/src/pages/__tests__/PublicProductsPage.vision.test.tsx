import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PublicProductsPage from "../PublicProductsPage";
import { VisionAnalysis } from "../../types/vision";

vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock("../../services/visionApi", () => ({
  detectarVisionPublica: vi.fn(),
  mensajeErrorVision: vi.fn((error: unknown) => {
    const e = error as { message?: string };
    return e?.message ?? "Error inesperado";
  }),
  recomendacionesVision: vi.fn(() => [] as string[]),
}));

// La medición local de calidad corre en TODOS los paths (cámara y upload). En
// jsdom no hay canvas funcional, así que se mockea para que los flujos sigan
// deterministas y para poder probar el aviso por foto mala.
vi.mock("../../services/imageQuality", () => ({
  analizarCalidadImagen: vi.fn(),
}));

vi.mock("react-hot-toast", () => ({
  default: { success: vi.fn(), error: vi.fn(), loading: vi.fn() },
}));

vi.mock("../../components/camera/CameraCapture", () => ({
  default: ({ onCapture, onClose, captureLabel }: { onCapture: (f: File) => void; onClose: () => void; captureLabel?: string }) => (
    <div>
      <p>Modal cámara simulado</p>
      <button type="button" onClick={() => onCapture(new File(["x"], "foto-vision.jpg", { type: "image/jpeg" }))}>
        {captureLabel ?? "Tomar foto"}
      </button>
      <button type="button" onClick={onClose}>Cerrar mock</button>
    </div>
  ),
}));

vi.mock("../../components/vision/VisionResultsPanel", () => ({
  default: (props: {
    nombreFoto?: string;
    resultado: VisionAnalysis | null;
    loading: boolean;
    error: string | null;
    advertirCalidad?: boolean;
    onCerrar: () => void;
    onLlevarAVenta: (borrador: { origen: string; creadoEn?: string; producto: unknown; entrega: unknown }) => void;
  }) => (
    <div>
      <p>Panel resultados simulado</p>
      <p data-testid="vision-nombre-foto">{props.nombreFoto ?? ""}</p>
      <p data-testid="vision-error">{props.error ?? ""}</p>
      <p data-testid="vision-cargando">{String(props.loading)}</p>
      <p data-testid="vision-advertir">{String(props.advertirCalidad ?? false)}</p>
      <p data-testid="vision-categoria">{props.resultado ? props.resultado.deteccion.categoria : ""}</p>
      <button type="button" onClick={props.onCerrar}>Cerrar panel</button>
      <button
        type="button"
        onClick={() => props.onLlevarAVenta({
          origen: "vision",
          creadoEn: "2026-09-21T00:00:00.000Z",
          producto: { itemCode: "FRN-001", nombre: "Zapata de freno trasera", cantidad: 1 },
          entrega: { modalidad: "recoger", sucursalId: 1, sucursalNombre: "Tienda Norte" },
        })}
      >
        Preparar venta (mock)
      </button>
    </div>
  ),
}));

import { detectarVisionPublica } from "../../services/visionApi";
import { analizarCalidadImagen } from "../../services/imageQuality";

const detectarMock = detectarVisionPublica as ReturnType<typeof vi.fn>;
const analizarCalidadMock = analizarCalidadImagen as ReturnType<typeof vi.fn>;

function renderPublic() {
  return render(
    <MemoryRouter>
      <PublicProductsPage />
    </MemoryRouter>
  );
}

describe("PublicProductsPage - Visión por cámara", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    localStorage.clear();
    // Por defecto la medición "no se pudo hacer" (null): la búsqueda procede
    // igual, como en un navegador sin canvas o con imagen indecodificable.
    analizarCalidadMock.mockResolvedValue(null);
    vi.spyOn(window, "alert").mockImplementation(() => {});
    // jsdom no implementa URL.createObjectURL: la página crea una URL de objeto para
    // la foto capturada, que el panel usa para dibujar el bounding box.
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:mock-captura-vision"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    const api = (await import("../../services/api")).default;
    const apiGet = api.get as ReturnType<typeof vi.fn>;
    apiGet.mockImplementation((url: string) => {
      if (url === "/public/filters") {
        return Promise.resolve({ data: { brands: [], categories: [], qualities: [] } });
      }
      if (url === "/public/products?limit=4") {
        return Promise.resolve({ data: { products: [] } });
      }
      if (url.startsWith("/public/products")) {
        return Promise.resolve({ data: { products: [], pagination: { total: 0 } } });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it("abre la cámara al pulsar Buscar por cámara", async () => {
    renderPublic();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Buscar por cámara" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Buscar por cámara" }));

    expect(screen.getByText("Modal cámara simulado")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tomar foto" })).toBeInTheDocument();
  });

  it("captura la foto, llama detectarVisionPublica y muestra resultados", async () => {
    const resultado: VisionAnalysis = {
version: "1.0",
  consultadoEn: "2026-01-01T00:00:00.000Z",
  proveedor: "http",
      deteccion: {
        categoria: "freno de tambor",
        confianza: 0.9,
        confianzaBaja: false,
        categoriaMapeada: "frenos",
        boundingBox: { x: 0, y: 0, width: 100, height: 100 },
      },
      vehiculo: { marca: null, modelo: null, anio: null },
      categoriaCatalogo: null,
      candidatos: [],
      compatibilidad: {
        consultada: false,
fuente: "base_datos_interna",
    metodologia: "baseline-catalog",
        consultadoEn: "2026-01-01T00:00:00.000Z",
        vehiculo: null,
        verificadas: 0,
        noVerificadas: 0,
        nota: "",
      },
      entrega: { modalidades: ["recoger"], sucursales: [] },
      nota: "",
    };

    detectarMock.mockResolvedValue(resultado);

    renderPublic();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Buscar por cámara" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Buscar por cámara" }));
    fireEvent.click(screen.getByRole("button", { name: "Tomar foto" }));

    await waitFor(() => {
      expect(screen.getByText("Panel resultados simulado")).toBeInTheDocument();
    });

    expect(detectarMock).toHaveBeenCalledTimes(1);
    expect(detectarMock).toHaveBeenCalledWith(
      expect.any(File),
      expect.objectContaining({ vehiculo: expect.any(Object) })
    );

    expect(screen.getByTestId("vision-nombre-foto")).toHaveTextContent("foto-vision.jpg");
    expect(screen.getByTestId("vision-categoria")).toHaveTextContent("freno de tambor");
    expect(screen.getByTestId("vision-cargando")).toHaveTextContent("false");
  });

  it("muestra el error traducido cuando la detección falla", async () => {
    const apierror = new Error("No se pudo clasificar la imagen. Reintentá con otra foto.");
    detectarMock.mockRejectedValue(apierror);

    renderPublic();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Buscar por cámara" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Buscar por cámara" }));
    fireEvent.click(screen.getByRole("button", { name: "Tomar foto" }));

    await waitFor(() => {
      expect(screen.getByTestId("vision-error")).toHaveTextContent(
        "No se pudo clasificar la imagen. Reintentá con otra foto."
      );
    });
  });

  it("cierra la cámara sin capturar y conserva la página", async () => {
    renderPublic();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Buscar por cámara" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Buscar por cámara" }));
    fireEvent.click(screen.getByRole("button", { name: "Cerrar mock" }));

    expect(screen.queryByText("Modal cámara simulado")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Buscar por cámara" })).toBeInTheDocument();
  });

  it("prepara la venta: guarda el borrador en localStorage y cierra el panel", async () => {
    renderPublic();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Buscar por cámara" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Buscar por cámara" }));
    fireEvent.click(screen.getByRole("button", { name: "Tomar foto" }));

    await waitFor(() => {
      expect(screen.getByText("Panel resultados simulado")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Preparar venta (mock)" }));

    await waitFor(() => {
      expect(screen.queryByText("Panel resultados simulado")).not.toBeInTheDocument();
    });

    const guardado = JSON.parse(localStorage.getItem("borrador_venta_vision") || "null");
    expect(guardado).toMatchObject({
      origen: "vision",
      producto: { itemCode: "FRN-001" },
      entrega: { modalidad: "recoger", sucursalId: 1, sucursalNombre: "Tienda Norte" },
    });

    const toastMock = (await import("react-hot-toast")).default as unknown as { success: ReturnType<typeof vi.fn> };
    expect(toastMock.success).toHaveBeenCalledWith(expect.stringContaining("Punto de Venta"));
  });

  it("mide la calidad local en la captura de cámara antes de buscar", async () => {
    const resultado: VisionAnalysis = {
      version: "1.0",
      consultadoEn: "2026-01-01T00:00:00.000Z",
      proveedor: "http",
      deteccion: {
        categoria: "freno de tambor",
        confianza: 0.9,
        confianzaBaja: false,
        categoriaMapeada: "frenos",
        boundingBox: { x: 0, y: 0, width: 100, height: 100 },
      },
      vehiculo: { marca: null, modelo: null, anio: null },
      categoriaCatalogo: null,
      candidatos: [],
      compatibilidad: {
        consultada: false,
        fuente: "base_datos_interna",
        metodologia: "baseline-catalog",
        consultadoEn: "2026-01-01T00:00:00.000Z",
        vehiculo: null,
        verificadas: 0,
        noVerificadas: 0,
        nota: "",
      },
      entrega: { modalidades: ["recoger"], sucursales: [] },
      nota: "",
    };
    detectarMock.mockResolvedValue(resultado);

    renderPublic();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Buscar por cámara" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Buscar por cámara" }));
    fireEvent.click(screen.getByRole("button", { name: "Tomar foto" }));

    await waitFor(() => {
      expect(detectarMock).toHaveBeenCalledTimes(1);
    });

    // TODO antes medía "Calidad n/d": hoy la medición corre en el mismo punto de
    // entrada que la cámara y llega al panel (sin advertencia si no hay problema).
    expect(analizarCalidadMock).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("vision-advertir")).toHaveTextContent("false");
    expect(screen.getByTestId("vision-nombre-foto")).toHaveTextContent("foto-vision.jpg");
  });

  it("advierte por foto mala en la cámara sin gastar inferencia", async () => {
    analizarCalidadMock.mockResolvedValue({
      brillo: 0.1,
      contraste: 0.2,
      nitidez: 0.01,
      resolucion: { ancho: 800, alto: 600, megapixeles: 0.48 },
      bytesArchivo: 300 * 1024,
      estado: "mala",
      problemas: ["La foto está muy oscura (brillo 10%)."],
      recomendaciones: ["Buscá más luz o acercá la pieza a una fuente de luz."],
    });

    renderPublic();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Buscar por cámara" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Buscar por cámara" }));
    fireEvent.click(screen.getByRole("button", { name: "Tomar foto" }));

    await waitFor(() => {
      expect(screen.getByTestId("vision-advertir")).toHaveTextContent("true");
    });

    expect(detectarMock).not.toHaveBeenCalled();
  });

  it("el path de subir imagen también mide la calidad y avanza la búsqueda", async () => {
    const resultado: VisionAnalysis = {
      version: "1.0",
      consultadoEn: "2026-01-01T00:00:00.000Z",
      proveedor: "http",
      deteccion: {
        categoria: "bujía",
        confianza: 0.88,
        confianzaBaja: false,
        categoriaMapeada: "encendido",
        boundingBox: { x: 0.1, y: 0.1, width: 0.4, height: 0.4 },
      },
      vehiculo: { marca: null, modelo: null, anio: null },
      categoriaCatalogo: null,
      candidatos: [],
      compatibilidad: {
        consultada: false,
        fuente: "base_datos_interna",
        metodologia: "baseline-catalog",
        consultadoEn: "2026-01-01T00:00:00.000Z",
        vehiculo: null,
        verificadas: 0,
        noVerificadas: 0,
        nota: "",
      },
      entrega: { modalidades: ["recoger"], sucursales: [] },
      nota: "",
    };
    detectarMock.mockResolvedValue(resultado);

    renderPublic();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Buscar por cámara" })).toBeInTheDocument();
    });

    const input = document.getElementById("buscar-imagen-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["x"], "bujia.jpg", { type: "image/jpeg" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Analizar imagen" }));

    await waitFor(() => {
      expect(detectarMock).toHaveBeenCalledTimes(1);
    });

    expect(analizarCalidadMock).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("vision-advertir")).toHaveTextContent("false");
    expect(screen.getByTestId("vision-nombre-foto")).toHaveTextContent("bujia.jpg");
    expect(screen.getByTestId("vision-categoria")).toHaveTextContent("bujía");
  });

  it("advierte por foto mala también en el path de subir imagen", async () => {
    analizarCalidadMock.mockResolvedValue({
      brillo: 0.05,
      contraste: 0.01,
      nitidez: 0.0001,
      resolucion: { ancho: 320, alto: 240, megapixeles: 0.08 },
      bytesArchivo: 12 * 1024,
      estado: "mala",
      problemas: ["Resolución baja (320×240)."],
      recomendaciones: ["Acercá la pieza para que la foto tenga más detalle."],
    });

    renderPublic();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Buscar por cámara" })).toBeInTheDocument();
    });

    const input = document.getElementById("buscar-imagen-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["x"], "borrosa.jpg", { type: "image/jpeg" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Analizar imagen" }));

    await waitFor(() => {
      expect(screen.getByTestId("vision-advertir")).toHaveTextContent("true");
    });

    expect(detectarMock).not.toHaveBeenCalled();
  });
});