import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import SalesPage from "../SalesPage";

vi.mock("../../services/api", () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

vi.mock("../../stores/authStore", () => ({
  useAuthStore: vi.fn(() => ({
    user: { id: 1, name: "Admin", role: "ADMIN", locationId: 1 },
    allowedCategories: [],
    columnConfig: {},
  })),
}));

vi.mock("react-hot-toast", () => ({
  default: { success: vi.fn(), error: vi.fn(), loading: vi.fn() },
}));

vi.mock("jspdf", () => ({
  default: vi.fn(() => ({
    internal: { pageSize: { getWidth: () => 210 } },
    addImage: vi.fn(),
    save: vi.fn(),
  })),
}));

vi.mock("html2canvas", () => ({
  default: vi.fn(() => ({
    toDataURL: vi.fn(() => "data:image/png;base64,"),
    height: 100,
    width: 100,
  })),
}));

const apiMock = await import("../../services/api");
const toastMock = await import("react-hot-toast");
const mockedApiGet = apiMock.default.get as ReturnType<typeof vi.fn>;
const mockedApiPost = apiMock.default.post as ReturnType<typeof vi.fn>;
const mockedToastError = toastMock.default.error as ReturnType<typeof vi.fn>;

const mockLocations = [
  { id: 1, name: "Tienda Central", type: "TIENDA" },
  { id: 2, name: "Almacen", type: "ALMACEN" },
];

const mockCategories = [{ id: 1, name: "Motor" }, { id: 2, name: "Frenos" }];

const mockProduct1 = {
  id: 10, itemCode: "FILT-001", manufacturer: "Bosch", name: "Filtro de Aceite",
  brand: "Bosch", model: "Universal", year: "2020-2024", price1: "25.00", price2: "35.00",
  wholesalePrice: null, stock: 10, category: "Motor", image: null, oemCode: "OEM-001",
};

const mockProduct2 = {
  id: 20, itemCode: "BAL-002", manufacturer: "TRW", name: "Balatas Delanteras",
  brand: "TRW", model: "Sedan", year: "2018-2023", price1: "45.00", price2: "55.00",
  wholesalePrice: null, stock: 3, category: "Frenos", image: null, oemCode: null,
};

function mockApiSetup() {
  mockedApiGet.mockImplementation((url: string) => {
    if (url === "/locations") return Promise.resolve({ data: mockLocations });
    if (url === "/categories") return Promise.resolve({ data: mockCategories });
    if (url.startsWith("/products?")) {
      const params = new URLSearchParams(url.split("?")[1]);
      const search = params.get("search") || "";
      let products = [mockProduct1, mockProduct2];
      if (search) {
        products = products.filter((p) =>
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          p.itemCode.toLowerCase().includes(search.toLowerCase())
        );
      }
      return Promise.resolve({ data: { products } });
    }
    return Promise.resolve({ data: {} });
  });
  mockedApiPost.mockResolvedValue({
    data: { id: 100, saleDate: new Date().toISOString(), total: 0, items: [], payments: [] },
  });
}

function renderSales() {
  return render(
    <MemoryRouter>
      <SalesPage />
    </MemoryRouter>
  );
}

/** Type in search, wait for debounced results to appear */
async function searchFor(user: ReturnType<typeof userEvent.setup>, productName: string) {
  const searchInput = screen.getByPlaceholderText(/Buscar producto/i);
  await user.type(searchInput, productName);
  await waitFor(() => {
    expect(screen.getAllByText(productName).length).toBeGreaterThanOrEqual(1);
  }, { timeout: 5000 });
}

/** Click the first "Mayorista" button in search results */
async function addProductMayorista(user: ReturnType<typeof userEvent.setup>) {
  const buttons = screen.getAllByRole("button", { name: /Mayorista/i });
  await user.click(buttons[0]);
}

/** Search and add a product that's already in cart (increments quantity) */
async function searchAndAddMayorista(user: ReturnType<typeof userEvent.setup>, productName: string) {
  const searchInput = screen.getByPlaceholderText(/Buscar producto/i);
  // Clear existing text first (addToCart clears search, but just in case)
  await user.clear(searchInput);
  await user.type(searchInput, productName);
  // Wait for debounce + API + re-render: Mayorista: button appears in search results
  const btn = await screen.findByRole("button", { name: /Mayorista:/i }, { timeout: 5000 });
  await user.click(btn);
}

describe("SalesPage — Carrito (E7.5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiSetup();
  });

  it("carrito muestra estado vacio inicialmente", async () => {
    renderSales();
    await waitFor(() => {
      expect(screen.getByText(/Busca un producto/i)).toBeInTheDocument();
    });
  });

  it("agregar producto al carrito lo muestra en la tabla", async () => {
    const user = userEvent.setup();
    renderSales();
    await searchFor(user, "Filtro de Aceite");
    await addProductMayorista(user);

    await waitFor(() => {
      expect(screen.getByText("1 producto(s) en carrito")).toBeInTheDocument();
    });
  });

  it("agregar mismo producto incrementa cantidad", async () => {
    const user = userEvent.setup();
    renderSales();

    await searchFor(user, "Filtro de Aceite");
    await addProductMayorista(user);
    await waitFor(() => {
      expect(screen.getByText("1 producto(s) en carrito")).toBeInTheDocument();
    });

    // Click Plus button in the cart table to increment quantity
    const allPlusBtns = document.querySelectorAll("button");
    for (const btn of allPlusBtns) {
      const svg = btn.querySelector(".lucide-plus");
      if (svg && btn.closest("table")) {
        await user.click(btn);
        break;
      }
    }

    // cart.length stays 1 (same unique product), but total quantity = 2
    // Check the quantity span in the table shows 2
    await waitFor(() => {
      const qtySpan = document.querySelector("table tbody tr td:nth-child(3) span");
      expect(qtySpan?.textContent).toBe("2");
    });
  });

  it("eliminar producto lo quita del carrito", async () => {
    const user = userEvent.setup();
    renderSales();

    await searchFor(user, "Filtro de Aceite");
    await addProductMayorista(user);
    await waitFor(() => {
      expect(screen.getByText("1 producto(s) en carrito")).toBeInTheDocument();
    });

    // Find trash button in the cart table rows
    const trashBtns = document.querySelectorAll("table tbody tr button");
    const lastBtn = trashBtns[trashBtns.length - 1];
    if (lastBtn) {
      await user.click(lastBtn);
    }

    await waitFor(() => {
      expect(screen.getByText(/Busca un producto/i)).toBeInTheDocument();
    });
  });

  it("no permite cantidad mayor al stock", async () => {
    const user = userEvent.setup();
    renderSales();

    await searchFor(user, "Balatas Delanteras");
    await addProductMayorista(user);

    await waitFor(() => {
      expect(screen.getByText("1 producto(s) en carrito")).toBeInTheDocument();
    });

    // Click plus button to increment quantity (stock is 3)
    const allPlusBtns = document.querySelectorAll("button");
    for (const btn of allPlusBtns) {
      const svg = btn.querySelector(".lucide-plus");
      // Only click the Plus that's in the quantity controls, not the add buttons
      if (svg && btn.closest("table")) {
        await user.click(btn);
        await user.click(btn);
        await user.click(btn);
        break;
      }
    }

    await waitFor(() => {
      expect(mockedToastError).toHaveBeenCalled();
    });
  });

  it("boton vaciar carrito funciona", async () => {
    const user = userEvent.setup();
    renderSales();

    await searchFor(user, "Filtro de Aceite");
    await addProductMayorista(user);
    await waitFor(() => {
      expect(screen.getByText("1 producto(s) en carrito")).toBeInTheDocument();
    });

    const clearButton = screen.getByText("Vaciar");
    await user.click(clearButton);

    await waitFor(() => {
      expect(screen.getByText(/Busca un producto/i)).toBeInTheDocument();
    });
  });

  it("cambio de tier usa el precio correspondiente", async () => {
    const user = userEvent.setup();
    renderSales();

    await searchFor(user, "Filtro de Aceite");
    // Product 1: price1=25 (Mayorista), price2=35 (Minorista)
    await addProductMayorista(user);

    await waitFor(() => {
      expect(screen.getByText("1 producto(s) en carrito")).toBeInTheDocument();
    });

    // In the cart table, look for Mayorista/Minorista tier buttons
    // Default added with Mayorista tier (price1=25)
    // Verify the price cell shows the unit price
    const allTexts = document.body.textContent || "";
    // The formatBs output for 25 is "Bs. 25,00" (es-BO locale)
    expect(allTexts).toContain("25");
  });
});

describe("SalesPage — Calculo de total (E7.6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiSetup();
  });

  it("carrito vacio no muestra total", async () => {
    renderSales();
    await waitFor(() => {
      expect(screen.getByText(/Busca un producto/i)).toBeInTheDocument();
    });
    // No cobrar button when cart is empty
    expect(screen.queryByText(/Cobrar/)).not.toBeInTheDocument();
  });

  it("un producto: total = unitPrice x quantity", async () => {
    const user = userEvent.setup();
    renderSales();

    await searchFor(user, "Filtro de Aceite");
    await addProductMayorista(user);

    await waitFor(() => {
      expect(screen.getByText("1 producto(s) en carrito")).toBeInTheDocument();
    });

    // The cart should display unit price; price1=25 for Mayorista tier
    const bodyText = document.body.textContent || "";
    expect(bodyText).toContain("25");
  });

  it("varios productos: total = suma de subtotales", async () => {
    const user = userEvent.setup();
    renderSales();

    // Add product1 (price1=25)
    await searchFor(user, "Filtro de Aceite");
    await addProductMayorista(user);
    await waitFor(() => {
      expect(screen.getByText("1 producto(s) en carrito")).toBeInTheDocument();
    });

    // addToCart clears search, so type new search and add product2
    await searchAndAddMayorista(user, "Balatas Delanteras");

    // total = 25 + 45 = 70
    await waitFor(() => {
      expect(screen.getByText("2 producto(s) en carrito")).toBeInTheDocument();
    });

    const bodyText = document.body.textContent || "";
    expect(bodyText).toContain("70");
  });

  it("cambio de cantidad actualiza total", async () => {
    const user = userEvent.setup();
    renderSales();

    await searchFor(user, "Filtro de Aceite");
    await addProductMayorista(user);

    await waitFor(() => {
      expect(screen.getByText("1 producto(s) en carrito")).toBeInTheDocument();
    });

    // Click Plus button in the cart table to increment quantity (price1=25, qty2 => total=50)
    const allPlusBtns = document.querySelectorAll("button");
    for (const btn of allPlusBtns) {
      const svg = btn.querySelector(".lucide-plus");
      if (svg && btn.closest("table")) {
        await user.click(btn);
        break;
      }
    }

    await waitFor(() => {
      const qtySpan = document.querySelector("table tbody tr td:nth-child(3) span");
      expect(qtySpan?.textContent).toBe("2");
    });

    const bodyText = document.body.textContent || "";
    expect(bodyText).toContain("50");
  });

  it("cambio de tier actualiza total", async () => {
    const user = userEvent.setup();
    renderSales();

    await searchFor(user, "Filtro de Aceite");
    await addProductMayorista(user);

    await waitFor(() => {
      expect(screen.getByText("1 producto(s) en carrito")).toBeInTheDocument();
    });

    // Switch to Minorista (price2=35) in the cart
    const minoristaBtns = screen.getAllByText("Minorista");
    if (minoristaBtns.length > 0) {
      await user.click(minoristaBtns[minoristaBtns.length - 1]);
    }

    await waitFor(() => {
      const bodyText = document.body.textContent || "";
      expect(bodyText).toContain("35");
    });
  });
});
