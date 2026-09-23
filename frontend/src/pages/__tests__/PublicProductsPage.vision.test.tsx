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
    onCerrar: () => void;
    onLlevarAVenta: (borrador: { origen: string; creadoEn?: string; producto: unknown; entrega: unknown }) => void;
  }) => (
    <div>
      <p>Panel resultados simulado</p>
      <p data-testid="vision-nombre-foto">{props.nombreFoto ?? ""}</p>
      <p data-testid="vision-error">{props.error ?? ""}</p>
      <p data-testid="vision-cargando">{String(props.loading)}</p>
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

const detectarMock = detectarVisionPublica as ReturnType<typeof vi.fn>;

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
    vi.spyOn(window, "alert").mockImplementation(() => {});
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
      version: "mock-1",
      consultadoEn: "2026-01-01T00:00:00.000Z",
      proveedor: "mock",
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
        fuente: "mock",
        metodologia: "mock",
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
});