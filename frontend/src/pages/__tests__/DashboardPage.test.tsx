import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import DashboardPage from "../DashboardPage";
import api from "../../services/api";
const session = vi.hoisted(() => ({ user: { role: "ADMIN" } }));
vi.mock("../../stores/authStore", () => ({ useAuthStore: (selector: any) => selector(session) }));
vi.mock("../../services/api", () => ({ default: { get: vi.fn() } }));
beforeEach(() => { session.user.role = "ADMIN"; vi.clearAllMocks(); });
describe("dashboard no bloquea la consulta predictiva administrativa", () => {
  it("explica incompatibilidad de esquema sin sustituirla por cifras ficticias", async () => {
    vi.mocked(api.get).mockRejectedValue({ response: { status: 503, data: { code: "DASHBOARD_SCHEMA_UNAVAILABLE" } } });
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    await screen.findByText(/La estructura de datos no coincide/);
    expect(screen.getByRole("link", { name: /Abrir predicción/ })).toHaveAttribute("href", "/panel/prediccion");
    expect(screen.queryByText("Total Productos")).not.toBeInTheDocument();
  });
  it("no ofrece enlace administrativo a TIENDA y distingue el fallo de red", async () => {
    session.user.role = "TIENDA";
    vi.mocked(api.get).mockRejectedValue(new Error("network"));
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    await screen.findByText(/No se pudo contactar con el backend/);
    expect(screen.queryByRole("link", { name: /Abrir predicción/ })).not.toBeInTheDocument();
  });
  it("carga inventario real disponible sin presentar ventas desconocidas como cero", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: {
      availability: { sales: "SCHEMA_UNAVAILABLE" },
      summary: { totalProducts: 12, productsWithoutStock: 2, productsWithLowStock: 1, salesToday: null, salesTodayTotal: null, salesMonth: null, salesMonthTotal: null, pendingRequests: 4, criticalStock: 0 },
      stockByLocation: [], salesByLocation: [], salesByBrand: [], salesByVehicle: [], recentSales: [], recentMovements: [], pendingRequests: [], criticalStock: [],
    } });
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    await screen.findByText("Total Productos");
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Inventario y solicitudes disponibles");
    expect(screen.getAllByText("No disponible").length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByText("Bs. 0,00")).not.toBeInTheDocument();
    expect(screen.queryByText("Sin ventas recientes")).not.toBeInTheDocument();
  });
});
