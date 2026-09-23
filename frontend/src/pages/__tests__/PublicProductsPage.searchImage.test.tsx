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
  default: () => (
    <div>
      <p>Modal cámara simulado</p>
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
  }) => (
    <div>
      <p>Panel resultados simulado</p>
      <p data-testid="vision-nombre-foto">{props.nombreFoto ?? ""}</p>
      <p data-testid="vision-error">{props.error ?? ""}</p>
      <p data-testid="vision-cargando">{String(props.loading)}</p>
      <p data-testid="vision-categoria">{props.resultado ? props.resultado.deteccion.categoria : ""}</p>
      <button type="button" onClick={props.onCerrar}>Cerrar panel</button>
    </div>
  ),
}));

import { detectarVisionPublica } from "../../services/visionApi";

const detectarMock = detectarVisionPublica as ReturnType<typeof vi.fn>;

const resultadoAlternador: VisionAnalysis = {
  version: "mock-1",
  consultadoEn: "2026-01-01T00:00:00.000Z",
  proveedor: "mock",
  deteccion: {
    categoria: "alternador",
    confianza: 0.9,
    confianzaBaja: false,
    categoriaMapeada: "Eléctrico",
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

function renderPublic() {
  return render(
    <MemoryRouter>
      <PublicProductsPage />
    </MemoryRouter>
  );
}

function uploadFile(file: File) {
  const input = document.getElementById("buscar-imagen-input") as HTMLInputElement;
  Object.defineProperty(input, "files", { value: [file], configurable: true });
  fireEvent.change(input);
}

function createFile(name: string, type: string, size: number): File {
  const buffer = new ArrayBuffer(size);
  return new File([buffer], name, { type });
}

describe("PublicProductsPage - Búsqueda por imagen (YOLO)", () => {
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

    // jsdom no implementa URL.createObjectURL: se polifillea para la preview.
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:mock-buscar-imagen"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  it("sin imagen: muestra Buscar por imagen y no hay preview", async () => {
    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: "Buscar por cámara" })).toBeInTheDocument();
    expect(screen.queryByTestId("buscar-imagen-preview")).not.toBeInTheDocument();
    expect(screen.queryByText("Analizar imagen")).not.toBeInTheDocument();
  });

  it.each([
    ["JPEG", "photo.jpg", "image/jpeg"],
    ["PNG", "photo.png", "image/png"],
    ["WebP", "photo.webp", "image/webp"],
  ])("selecciona %s: muestra preview, llama detectarVisionPublica y renderiza el panel", async (_label, name, type) => {
    detectarMock.mockResolvedValue(resultadoAlternador);

    renderPublic();
    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile(name, type, 1024));

    const preview = await waitFor(() => screen.getByTestId("buscar-imagen-preview"));
    expect(screen.getByTestId("buscar-imagen-filename")).toHaveTextContent(name);
    expect(preview.querySelector("img")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Analizar imagen" }));

    await waitFor(() => {
      expect(screen.getByText("Panel resultados simulado")).toBeInTheDocument();
    });

    expect(detectarMock).toHaveBeenCalledTimes(1);
    expect(detectarMock).toHaveBeenCalledWith(expect.any(File), expect.anything());
    expect(screen.getByTestId("vision-nombre-foto")).toHaveTextContent(name);
    expect(screen.getByTestId("vision-categoria")).toHaveTextContent("alternador");
    expect(screen.getByTestId("vision-cargando")).toHaveTextContent("false");
  });

  it("formato inválido: NO crea preview ni llama a la API y muestra toast de error", async () => {
    renderPublic();
    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("doc.pdf", "application/pdf", 1024));

    expect(screen.queryByTestId("buscar-imagen-preview")).not.toBeInTheDocument();
    expect(detectarMock).not.toHaveBeenCalled();

    const toastMock = (await import("react-hot-toast")).default as unknown as { error: ReturnType<typeof vi.fn> };
    expect(toastMock.error).toHaveBeenCalledWith("Formato no permitido. Usa JPEG, PNG o WebP.");
  });

  it("archivo >5MB: NO crea preview ni llama a la API y muestra toast de error", async () => {
    renderPublic();
    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("big.jpg", "image/jpeg", 6 * 1024 * 1024));

    expect(screen.queryByTestId("buscar-imagen-preview")).not.toBeInTheDocument();
    expect(detectarMock).not.toHaveBeenCalled();

    const toastMock = (await import("react-hot-toast")).default as unknown as { error: ReturnType<typeof vi.fn> };
    expect(toastMock.error).toHaveBeenCalledWith("La imagen supera 5 MB. Usa una imagen más pequeña.");
  });

  it("cambiar imagen: reemplaza la preview por la nueva selección", async () => {
    detectarMock.mockResolvedValue(resultadoAlternador);

    renderPublic();
    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("primera.jpg", "image/jpeg", 1024));
    await waitFor(() => screen.getByTestId("buscar-imagen-preview"));
    expect(screen.getByTestId("buscar-imagen-filename")).toHaveTextContent("primera.jpg");

    uploadFile(createFile("segunda.png", "image/png", 2048));

    await waitFor(() => {
      expect(screen.getByTestId("buscar-imagen-filename")).toHaveTextContent("segunda.png");
    });
    expect(screen.getByTestId("buscar-imagen-preview")).toBeInTheDocument();
  });

  it("quitar imagen: vuelve al estado sin imagen", async () => {
    renderPublic();
    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("photo.jpg", "image/jpeg", 1024));
    await waitFor(() => screen.getByTestId("buscar-imagen-preview"));

    fireEvent.click(screen.getByRole("button", { name: "Quitar imagen" }));

    expect(screen.queryByTestId("buscar-imagen-preview")).not.toBeInTheDocument();
    expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
  });

  it("muestra Analizando... y deshabilita el botón mientras la detección está en curso", async () => {
    let resolveDetectar!: (value: VisionAnalysis) => void;
    detectarMock.mockImplementation(
      () => new Promise<VisionAnalysis>((resolve) => { resolveDetectar = resolve; })
    );

    renderPublic();
    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("photo.jpg", "image/jpeg", 1024));
    await waitFor(() => screen.getByTestId("buscar-imagen-preview"));

    fireEvent.click(screen.getByRole("button", { name: "Analizar imagen" }));

    await waitFor(() => {
      expect(screen.getByTestId("vision-cargando")).toHaveTextContent("true");
    });

    resolveDetectar(resultadoAlternador);

    await waitFor(() => {
      expect(screen.getByTestId("vision-cargando")).toHaveTextContent("false");
    });
  });

  it("error de detección: muestra el mensaje traducido de visionApi en el panel", async () => {
    detectarMock.mockRejectedValue(new Error("No se pudo identificar la pieza en la imagen."));

    renderPublic();
    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("photo.jpg", "image/jpeg", 1024));
    await waitFor(() => screen.getByTestId("buscar-imagen-preview"));

    fireEvent.click(screen.getByRole("button", { name: "Analizar imagen" }));

    await waitFor(() => {
      expect(screen.getByTestId("vision-error")).toHaveTextContent(
        "No se pudo identificar la pieza en la imagen."
      );
    });
    expect(screen.getByTestId("vision-categoria")).toHaveTextContent("");
  });

  it("NO usa el endpoint OCR legacy /public/search-image", async () => {
    detectarMock.mockResolvedValue(resultadoAlternador);

    renderPublic();
    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("alternador.jpg", "image/jpeg", 1024));
    await waitFor(() => screen.getByTestId("buscar-imagen-preview"));

    fireEvent.click(screen.getByRole("button", { name: "Analizar imagen" }));

    await waitFor(() => {
      expect(screen.getByText("Panel resultados simulado")).toBeInTheDocument();
    });

    const api = (await import("../../services/api")).default;
    const apiPost = api.post as ReturnType<typeof vi.fn>;
    expect(apiPost).not.toHaveBeenCalled();
    expect(detectarMock).toHaveBeenCalledTimes(1);
  });
});