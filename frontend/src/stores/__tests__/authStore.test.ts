import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAuthStore } from "../authStore";

const mockUser = {
  id: 1,
  name: "Test User",
  email: "test@test.com",
  role: "ADMIN",
  locationId: 1,
};

vi.mock("../../services/api", () => ({
  default: {
    get: vi.fn(),
  },
}));

const apiMock = await import("../../services/api");
const mockedApiGet = apiMock.default.get as ReturnType<typeof vi.fn>;

describe("authStore", () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
      permissions: [],
      columnConfig: {},
      allowedCategories: [],
    });
    vi.clearAllMocks();
  });

  describe("login", () => {
    it("guarda token y user en localStorage", async () => {
      mockedApiGet.mockResolvedValue({
        data: { permissions: ["inventario", "ventas"], columnConfig: {} },
      });

      await useAuthStore.getState().login(mockUser, "abc123");

      expect(localStorage.getItem("token")).toBe("abc123");
      expect(JSON.parse(localStorage.getItem("user")!)).toEqual(mockUser);
    });

    it("actualiza isAuthenticated a true", async () => {
      mockedApiGet.mockResolvedValue({
        data: { permissions: [], columnConfig: {} },
      });

      await useAuthStore.getState().login(mockUser, "tok");

      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });

    it("establece user y token en el estado", async () => {
      mockedApiGet.mockResolvedValue({
        data: { permissions: [], columnConfig: {} },
      });

      await useAuthStore.getState().login(mockUser, "tok123");

      expect(useAuthStore.getState().user).toEqual(mockUser);
      expect(useAuthStore.getState().token).toBe("tok123");
    });

    it("carga permisos del backend cuando responde correctamente", async () => {
      mockedApiGet.mockResolvedValue({
        data: {
          permissions: ["inventario", "ventas", "productos"],
          columnConfig: { inventario: ["name", "stock"] },
        },
      });

      await useAuthStore.getState().login(mockUser, "tok");

      expect(useAuthStore.getState().permissions).toContain("inventario");
      expect(useAuthStore.getState().permissions).toContain("ventas");
      expect(useAuthStore.getState().columnConfig).toEqual({
        inventario: ["name", "stock"],
      });
    });

    it("normaliza 'productos' a 'inventario'", async () => {
      mockedApiGet.mockResolvedValue({
        data: { permissions: ["productos"], columnConfig: {} },
      });

      await useAuthStore.getState().login(mockUser, "tok");

      expect(useAuthStore.getState().permissions).toContain("inventario");
      expect(useAuthStore.getState().permissions).not.toContain("productos");
    });

    it("usa fallbackPermissions cuando el request de permisos falla", async () => {
      mockedApiGet.mockRejectedValue(new Error("Network error"));

      await useAuthStore.getState().login(mockUser, "tok");

      expect(useAuthStore.getState().permissions).toContain("inventario");
      expect(useAuthStore.getState().permissions).toContain("ventas");
    });

    it("fallbackPermissions incluye permisos correctos para ADMIN", async () => {
      mockedApiGet.mockRejectedValue(new Error("fail"));

      await useAuthStore.getState().login(mockUser, "tok");

      const perms = useAuthStore.getState().permissions;
      expect(perms).toContain("inventario");
      expect(perms).toContain("ventas");
      expect(perms).toContain("ventas-mayor");
      expect(perms).toContain("devoluciones");
      expect(perms).toContain("reportes");
    });

    it("fallbackPermissions incluye permisos correctos para TIENDA", async () => {
      mockedApiGet.mockRejectedValue(new Error("fail"));

      await useAuthStore
        .getState()
        .login({ ...mockUser, role: "TIENDA" }, "tok");

      const perms = useAuthStore.getState().permissions;
      expect(perms).toContain("inventario");
      expect(perms).toContain("ventas");
      expect(perms).not.toContain("costos");
    });

    it("llama a /permissions/permissions/me", async () => {
      mockedApiGet.mockResolvedValue({
        data: { permissions: [], columnConfig: {} },
      });

      await useAuthStore.getState().login(mockUser, "tok");

      expect(mockedApiGet).toHaveBeenCalledWith("/permissions/permissions/me");
    });
  });

  describe("logout", () => {
    it("limpia token y user de localStorage", () => {
      localStorage.setItem("token", "tok");
      localStorage.setItem("user", JSON.stringify(mockUser));

      useAuthStore.getState().logout();

      expect(localStorage.getItem("token")).toBeNull();
      expect(localStorage.getItem("user")).toBeNull();
    });

    it("resetea el estado a初始", () => {
      useAuthStore.setState({
        user: mockUser,
        token: "tok",
        isAuthenticated: true,
        permissions: ["inventario"],
      });

      useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.token).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.permissions).toEqual([]);
      expect(state.columnConfig).toEqual({});
      expect(state.allowedCategories).toEqual([]);
    });
  });

  describe("loadFromStorage", () => {
    it("restaura sesión válida desde localStorage", () => {
      localStorage.setItem("token", "stored-tok");
      localStorage.setItem("user", JSON.stringify(mockUser));

      useAuthStore.getState().loadFromStorage();

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.token).toBe("stored-tok");
      expect(state.isAuthenticated).toBe(true);
    });

    it("no hace nada si no hay token en localStorage", () => {
      useAuthStore.getState().loadFromStorage();

      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });

    it("no hace nada si user JSON es inválido", () => {
      localStorage.setItem("token", "tok");
      localStorage.setItem("user", "INVALID_JSON");

      useAuthStore.getState().loadFromStorage();

      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });

    it("limpia localStorage si user JSON es inválido", () => {
      localStorage.setItem("token", "tok");
      localStorage.setItem("user", "INVALID_JSON");

      useAuthStore.getState().loadFromStorage();

      expect(localStorage.getItem("token")).toBeNull();
      expect(localStorage.getItem("user")).toBeNull();
    });

    it("intenta recargar permisos desde el backend", async () => {
      localStorage.setItem("token", "tok");
      localStorage.setItem("user", JSON.stringify(mockUser));
      mockedApiGet.mockResolvedValue({
        data: { permissions: ["ventas"], columnConfig: {} },
      });

      useAuthStore.getState().loadFromStorage();

      await vi.waitFor(() => {
        expect(mockedApiGet).toHaveBeenCalledWith("/permissions/permissions/me");
      });
    });
  });
});
