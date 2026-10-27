import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import RoleRoute from "./RoleRoute";
const state = vi.hoisted(() => ({ user: { role: "TIENDA" }, isAuthenticated: true, permissions: [] as string[], permissionsLoading: true }));
vi.mock("../stores/authStore", () => ({ useAuthStore: () => state }));
describe("recuperación de permisos en ruta protegida", () => {
  it("espera sin enviar al dashboard durante la carga", () => {
    render(<MemoryRouter initialEntries={["/ventas"]}><Routes><Route path="/ventas" element={<RoleRoute allowedRoles={["TIENDA"]} module="ventas"><div>Ventas</div></RoleRoute>} /><Route path="/panel" element={<div>Dashboard</div>} /></Routes></MemoryRouter>);
    expect(screen.getByRole("status")).toHaveTextContent("Cargando permisos");
    expect(screen.queryByText("Dashboard")).toBeNull();
  });
});
