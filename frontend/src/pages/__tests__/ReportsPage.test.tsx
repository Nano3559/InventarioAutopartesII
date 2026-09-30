import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ReportsPage from "../ReportsPage";

vi.mock("../../services/api", () => ({
  default: { get: vi.fn() },
}));

const useAuthStoreMock = vi.fn(() => ({
  user: { id: 1, name: "Admin", role: "ADMIN", locationId: 1 },
  allowedCategories: [],
  columnConfig: {},
}));

vi.mock("../../stores/authStore", () => ({
  useAuthStore: () => useAuthStoreMock(),
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

vi.mock("xlsx", () => ({
  utils: { json_to_sheet: vi.fn(() => ({})) },
  writeFile: vi.fn(),
}));

const apiMock = await import("../../services/api");
const mockedApiGet = apiMock.default.get as ReturnType<typeof vi.fn>;

const hoy = new Date();

const reporteMensual = (conCostos: boolean) => ({
  period: { year: hoy.getFullYear(), month: hoy.getMonth() + 1 },
  locations: [
    {
      location: { id: 1, name: "Tienda Central", type: "TIENDA" },
      summary: {
        totalSales: 1000,
        totalReturns: 0,
        netSales: 1000,
        saleCount: 5,
        averagePerSale: 200,
      },
      ...(conCostos
        ? { costs: { productsCost: 500, storeCost: 550 } }
        : {}),
      topProducts: [
        { product: { id: 5, name: "Filtro de aceite", brand: "Bosch" }, quantitySold: 3, totalRevenue: 300 },
      ],
    },
  ],
  summary: {
    totalSales: 1000,
    totalReturns: 0,
    netSales: 1000,
    totalLocations: 1,
    activeLocations: 1,
    ...(conCostos
      ? { costs: { totalProductsCost: 500, totalStoreCost: 550 } }
      : {}),
  },
});

/** Mismo formato que formatBs() en ReportsPage, delegando en el locale del runtime. */
const bs = (v: number) => `Bs. ${v.toLocaleString("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function mockReportes(conCostos: boolean, vacio = false) {
  const cuerpo = vacio
    ? { locations: [], summary: { totalSales: 0, totalReturns: 0, netSales: 0, totalLocations: 0, activeLocations: 0 } }
    : reporteMensual(conCostos);
  mockedApiGet.mockImplementation(async (url: string) => {
    if (url.includes("/reports/monthly")) return { data: { period: reporteMensual(true).period, ...cuerpo } };
    if (url.includes("/reports/inventory")) {
      return { data: { products: [], totalProducts: 0, totalStock: 0, lowStockCount: 0 } };
    }
    if (url.includes("/reports/sales")) {
      return { data: { sales: [], summary: { totalSales: 0, count: 0, average: 0 } } };
    }
    if (url.includes("/locations")) return { data: [] };
    if (url.includes("/categories")) return { data: [] };
    return { data: [] };
  });
}

async function abrirPestanaMensual() {
  render(
    <MemoryRouter>
      <ReportsPage />
    </MemoryRouter>
  );
  await userEvent.click(screen.getByRole("button", { name: /mensual/i }));
  await waitFor(() => expect(screen.getByText(/Tienda Central/)).toBeTruthy());
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStoreMock.mockReturnValue({
    user: { id: 1, name: "Admin", role: "ADMIN", locationId: 1 },
    allowedCategories: [],
    columnConfig: {},
  });
});

describe("ReportsPage — aislamiento de costos por rol", () => {
  it("ADMIN ve las columnas de costo de mercadería, costo de tienda y utilidad", async () => {
    mockReportes(true);
    await abrirPestanaMensual();

    expect(screen.getByText("Costo Mercadería")).toBeTruthy();
    expect(screen.getByText("Costo Tienda (+10%)")).toBeTruthy();
    expect(screen.getByText("Utilidad")).toBeTruthy();
    expect(screen.getByText(bs(500))).toBeTruthy();
    expect(screen.getByText(bs(550))).toBeTruthy();
    expect(screen.getByText(bs(450))).toBeTruthy();
  });

  it("TIENDA no ve las columnas de costo ni de utilidad aunque el backend las enviara", async () => {
    useAuthStoreMock.mockReturnValue({
      user: { id: 7, name: "Vendedor", role: "TIENDA", locationId: 1 },
      allowedCategories: [],
      columnConfig: {},
    });
    // Payload con costos: el frontend no debe mostrarlos ni exportarlos.
    mockReportes(true);
    await abrirPestanaMensual();

    expect(screen.queryByText("Costo Mercadería")).toBeNull();
    expect(screen.queryByText("Costo Tienda (+10%)")).toBeNull();
    expect(screen.queryByText("Utilidad")).toBeNull();
    expect(screen.queryByText(bs(500))).toBeNull();
    expect(screen.queryByText(bs(550))).toBeNull();
    expect(screen.queryByText(bs(450))).toBeNull();

    // La información operativa sí permanece (con y sin devoluciones, 1.000 va en
    // la columna Total Ventas y en Neto: son dos celdas distintas).
    expect(screen.getByText("Tienda Central")).toBeTruthy();
    const tabla = screen.getByText("Tienda Central").closest("table") as HTMLTableElement;
    expect(within(tabla).getAllByText(bs(1000)).length).toBe(2);
  });

  it("TIENDA sigue viendo la tabla con el colSpan correcto cuando no hay datos", async () => {
    useAuthStoreMock.mockReturnValue({
      user: { id: 7, name: "Vendedor", role: "TIENDA", locationId: 1 },
      allowedCategories: [],
      columnConfig: {},
    });
    mockReportes(true, true);
    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>
    );
    await userEvent.click(screen.getByRole("button", { name: /mensual/i }));

    const celdaVacia = await screen.findByText(/No hay datos para los filtros seleccionados/i);
    expect(celdaVacia.getAttribute("colspan")).toBe("5");
  });

  it("ADMIN mantiene el colSpan completo cuando no hay datos", async () => {
    mockReportes(true, true);
    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>
    );
    await userEvent.click(screen.getByRole("button", { name: /mensual/i }));

    const celdaVacia = await screen.findByText(/No hay datos para los filtros seleccionados/i);
    expect(celdaVacia.getAttribute("colspan")).toBe("8");
  });
});
