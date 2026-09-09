import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import PublicProductsPage from "../PublicProductsPage";

vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const apiMock = await import("../../services/api");
const mockedApiGet = apiMock.default.get as ReturnType<typeof vi.fn>;
const mockedApiPost = apiMock.default.post as ReturnType<typeof vi.fn>;

const mockFilters = {
  brands: [],
  categories: [],
  qualities: [],
};

const mockImageResults = {
  products: [
    {
      id: 10,
      itemCode: "IMG-001",
      name: "Filtro Encontrado por Imagen",
      brand: "Bosch",
      model: "Universal",
      year: "2020",
      detail: "Filtro original",
      detalles: "Premium",
      image: null,
      category: "Motor",
      price1: 30.0,
      availability: "Disponible",
      score: 0.95,
    },
  ],
};

function renderPublic() {
  return render(
    <MemoryRouter>
      <PublicProductsPage />
    </MemoryRouter>
  );
}

function uploadFile(file: File) {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  Object.defineProperty(input, "files", { value: [file], configurable: true });
  fireEvent.change(input);
}

function createFile(name: string, type: string, size: number): File {
  const buffer = new ArrayBuffer(size);
  return new File([buffer], name, { type });
}

describe("PublicProductsPage - Búsqueda por imagen", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "alert").mockImplementation(() => {});
    mockedApiGet.mockImplementation((url: string) => {
      if (url === "/public/filters") {
        return Promise.resolve({ data: mockFilters });
      }
      if (url === "/public/products?limit=4") {
        return Promise.resolve({ data: { products: [] } });
      }
      if (url.startsWith("/public/products")) {
        return Promise.resolve({
          data: { products: [], pagination: { total: 0 } },
        });
      }
      return Promise.resolve({ data: [] });
    });
  });

  it("JPEG válido permite realizar request", async () => {
    mockedApiPost.mockResolvedValue({ data: { products: [] } });

    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("photo.jpg", "image/jpeg", 1024));

    const searchButton = screen.getByRole("button", { name: "Buscar" });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(mockedApiPost).toHaveBeenCalledWith(
        "/public/search-image",
        expect.any(FormData),
        expect.objectContaining({
          headers: { "Content-Type": "multipart/form-data" },
        })
      );
    });
  });

  it("PNG válido permite realizar request", async () => {
    mockedApiPost.mockResolvedValue({ data: { products: [] } });

    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("photo.png", "image/png", 1024));

    const searchButton = screen.getByRole("button", { name: "Buscar" });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(mockedApiPost).toHaveBeenCalled();
    });
  });

  it("WebP válido permite realizar request", async () => {
    mockedApiPost.mockResolvedValue({ data: { products: [] } });

    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("photo.webp", "image/webp", 1024));

    const searchButton = screen.getByRole("button", { name: "Buscar" });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(mockedApiPost).toHaveBeenCalled();
    });
  });

  it("MIME inválido NO realiza request y muestra alert", async () => {
    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("doc.pdf", "application/pdf", 1024));

    const searchButton = screen.getByRole("button", { name: "Buscar" });
    fireEvent.click(searchButton);

    expect(mockedApiPost).not.toHaveBeenCalled();
    expect(window.alert).toHaveBeenCalledWith(
      "Formato no permitido. Usa JPEG, PNG o WebP."
    );
  });

  it("GIF inválido NO realiza request", async () => {
    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("anim.gif", "image/gif", 1024));

    const searchButton = screen.getByRole("button", { name: "Buscar" });
    fireEvent.click(searchButton);

    expect(mockedApiPost).not.toHaveBeenCalled();
  });

  it("Archivo >5MB NO realiza request y muestra alert", async () => {
    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("big.jpg", "image/jpeg", 6 * 1024 * 1024));

    const searchButton = screen.getByRole("button", { name: "Buscar" });
    fireEvent.click(searchButton);

    expect(mockedApiPost).not.toHaveBeenCalled();
    expect(window.alert).toHaveBeenCalledWith(
      "La imagen supera 5 MB. Usa una imagen más pequeña."
    );
  });

  it("Response con productos renderiza resultados", async () => {
    mockedApiPost.mockResolvedValue({ data: mockImageResults });

    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("photo.jpg", "image/jpeg", 1024));

    const searchButton = screen.getByRole("button", { name: "Buscar" });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(
        screen.getByText("Filtro Encontrado por Imagen")
      ).toBeInTheDocument();
    });

    expect(screen.getByText("1 coincidencias")).toBeInTheDocument();
  });

  it("Response sin productos muestra alert", async () => {
    mockedApiPost.mockResolvedValue({ data: { products: [] } });

    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("photo.jpg", "image/jpeg", 1024));

    const searchButton = screen.getByRole("button", { name: "Buscar" });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith(
        "No encontramos productos relacionados con la imagen."
      );
    });
  });

  it("Error del endpoint muestra alert de error", async () => {
    mockedApiPost.mockRejectedValue(new Error("Network error"));

    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("photo.jpg", "image/jpeg", 1024));

    const searchButton = screen.getByRole("button", { name: "Buscar" });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith(
        "No se pudo buscar la imagen. Intenta nuevamente."
      );
    });
  });

  it("llama al endpoint correcto /public/search-image", async () => {
    mockedApiPost.mockResolvedValue({ data: { products: [] } });

    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("photo.jpg", "image/jpeg", 1024));

    const searchButton = screen.getByRole("button", { name: "Buscar" });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(mockedApiPost).toHaveBeenCalledWith(
        "/public/search-image",
        expect.any(FormData),
        expect.any(Object)
      );
    });
  });

  it("muestra Buscando... durante la búsqueda", async () => {
    let resolvePost!: (value: any) => void;
    mockedApiPost.mockImplementation(
      () => new Promise((r) => { resolvePost = r; })
    );

    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });

    uploadFile(createFile("photo.jpg", "image/jpeg", 1024));

    const searchButton = screen.getByRole("button", { name: "Buscar" });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText("Buscando...")).toBeInTheDocument();
    });

    resolvePost({ data: { products: [] } });
  });
});
