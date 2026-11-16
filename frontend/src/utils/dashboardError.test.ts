import { describe, it, expect } from "vitest";
import { dashboardError } from "./dashboardError";
describe("errores del dashboard", () => {
  it("distingue red, permisos, esquema y servicio sin mostrar detalles privados", () => {
    expect(dashboardError(new Error("private"))).toContain("backend");
    expect(dashboardError({ response: { status: 403 } })).toContain("permiso");
    expect(dashboardError({ response: { status: 503, data: { code: "DASHBOARD_SCHEMA_UNAVAILABLE" } } })).toContain("estructura");
    expect(dashboardError({ response: { status: 503 } })).toContain("temporalmente");
    expect(dashboardError({ response: { status: 500, data: { message: "private SQL" } } })).not.toContain("SQL");
  });
});
