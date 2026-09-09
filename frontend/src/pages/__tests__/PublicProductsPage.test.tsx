import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

const mockProducts = {
  products: [
    {
      id: 1,
      itemCode: "FILT-001",
      name: "Filtro de Aceite",
      brand: "Bosch",
      model: "Universal",
      year: "2020-2024",
      detalles: null,
      image: null,
      category: "Motor",
      availability: "Disponible",
      price1: 25.0,
      price2: 35.0,
    },
    {
      id: 2,
      itemCode: "BAL-002",
      name: "Balatas Delanteras",
      brand: "TRW",
      model: "Sedán",
      year: "2018-2023",
      detalles: "Premium",
      image: null,
      category: "Frenos",
      availability: "Pocas unidades",
      price1: 45.0,
      price2: 65.0,
    },
  ],
  pagination: { total: 2 },
};

const mockFilters = {
  brands: ["Bosch", "TRW"],
  categories: ["Motor", "Frenos"],
  qualities: ["Premium", "Estándar"],
};

function renderPublic() {
  return render(
    <MemoryRouter>
      <PublicProductsPage />
    </MemoryRouter>
  );
}

describe("PublicProductsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedApiGet.mockImplementation((url: string) => {
      if (url === "/public/filters") {
        return Promise.resolve({ data: mockFilters });
      }
      if (url === "/public/products?limit=4") {
        return Promise.resolve({ data: { products: mockProducts.products } });
      }
      if (url.startsWith("/public/products")) {
        return Promise.resolve({ data: mockProducts });
      }
      if (url.startsWith("/public/filters/models")) {
        return Promise.resolve({ data: [] });
      }
      if (url.startsWith("/public/filters/years")) {
        return Promise.resolve({ data: [] });
      }
      return Promise.resolve({ data: {} });
    });
  });

  it("muestra estado de carga inicialmente", () => {
    renderPublic();
    expect(screen.getByText("Cargando productos...")).toBeInTheDocument();
  });

  it("renderiza productos después de carga exitosa", async () => {
    renderPublic();

    await waitFor(() => {
      expect(screen.getAllByText("Filtro de Aceite").length).toBeGreaterThan(0);
    });

    expect(screen.getAllByText("Balatas Delanteras").length).toBeGreaterThan(0);
  });

  it("muestra cantidad de productos encontrados", async () => {
    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("2 productos encontrados")).toBeInTheDocument();
    });
  });

  it("muestra 'no encontramos productos' cuando la respuesta está vacía", async () => {
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

    renderPublic();

    await waitFor(() => {
      expect(
        screen.getByText("No encontramos productos con estos criterios")
      ).toBeInTheDocument();
    });
  });

  it("muestra filtros disponibles", async () => {
    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Filtros")).toBeInTheDocument();
    });

    expect(screen.getByText("Bosch")).toBeInTheDocument();
    expect(screen.getByText("TRW")).toBeInTheDocument();
  });

  it("renderiza campo de búsqueda", async () => {
    renderPublic();

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText(
          /Buscar por nombre, código OEM o código de fábrica/i
        )
      ).toBeInTheDocument();
    });
  });

  it("muestra botón limpiar filtros cuando hay filtros activos", async () => {
    const user = userEvent.setup();
    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Filtros")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(
      /Buscar por nombre, código OEM/i
    );
    await user.type(searchInput, "filtro");

    await waitFor(() => {
      expect(screen.getByText("Limpiar filtros")).toBeInTheDocument();
    });
  });

  it("limpiar filtros resetea el campo de búsqueda", async () => {
    const user = userEvent.setup();
    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Filtros")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(
      /Buscar por nombre, código OEM/i
    );
    await user.type(searchInput, "filtro");

    await waitFor(() => {
      expect(screen.getByText("Limpiar filtros")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Limpiar filtros"));

    await waitFor(() => {
      expect(searchInput).toHaveValue("");
    });
  });

  it("muestra label de búsqueda por imagen", async () => {
    renderPublic();

    await waitFor(() => {
      expect(screen.getByText("Buscar por imagen")).toBeInTheDocument();
    });
  });

  it("renderiza enlace de producto correctamente", async () => {
    renderPublic();

    await waitFor(() => {
      expect(screen.getAllByText("Filtro de Aceite").length).toBeGreaterThan(0);
    });

    const links = screen.getAllByRole("link");
    const productLink = links.find((l) =>
      l.getAttribute("href")?.includes("/productos/1")
    );
    expect(productLink).toBeTruthy();
  });
});
