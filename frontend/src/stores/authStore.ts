import { create } from "zustand";
import type { User } from "../types";
import api from "../services/api";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  permissions: string[];
  permissionsLoading: boolean;
  columnConfig: Record<string, string[]>;
  allowedCategories: string[];
  login: (user: User, token: string) => Promise<void>;
  logout: () => void;
  loadFromStorage: () => void;
}

const getCategoriesFromConfig = (cc: Record<string, string[]> | Record<string, unknown>): string[] => {
  const cats = (cc as any)?.__categorias;
  return Array.isArray(cats) ? (cats as string[]) : [];
};

const normalizePermissions = (permissions: string[]): string[] =>
  permissions.map((permission) => permission === "productos" ? "inventario" : permission);

const getAllowedCategories = (role: string, config: Record<string, unknown>): string[] => {
  const configured = getCategoriesFromConfig(config);
  return configured.length || role !== "TIENDA" ? configured : ["Frenos", "Motor", "Eléctrico"];
};

const fallbackPermissions = (role: string): string[] => {
  if (role === "ADMIN") return ["inventario", "ventas", "ventas-mayor", "devoluciones", "solicitudes", "movimientos", "costos", "precios", "reportes", "configuracion"];
  return [];
};

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem("token"),
  isAuthenticated: !!localStorage.getItem("token"),
  permissions: [],
  permissionsLoading: false,
  columnConfig: {},
  allowedCategories: [],
  login: async (user, token) => {
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(user));
    set({ user, token, isAuthenticated: true, permissionsLoading: true, permissions: [] });

    try {
      const res = await api.get("/permissions/permissions/me");
      if (get().token !== token) return;
      const perms = res.data.permissions || [];
      const cc = res.data.columnConfig || {};
      set({ permissionsLoading: false, permissions: normalizePermissions(perms), columnConfig: cc, allowedCategories: getAllowedCategories(user.role, cc) });
    } catch (error: any) {
      if (error.response?.status === 401) { get().logout(); return; }
      if (get().token !== token) return;
      set({ permissionsLoading: false, permissions: fallbackPermissions(user.role), allowedCategories: getAllowedCategories(user.role, {}) });
    }
  },
  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    set({ user: null, token: null, isAuthenticated: false, permissionsLoading: false, permissions: [], columnConfig: {}, allowedCategories: [] });
  },
  loadFromStorage: () => {
    const token = localStorage.getItem("token");
    const userStr = localStorage.getItem("user");
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr);
        set({ user, token, isAuthenticated: true, permissionsLoading: true, permissions: [] });

        // Reload permissions from backend
        api
          .get("/permissions/permissions/me")
          .then((res) => {
            if (get().token !== token) return;
            const cc = res.data.columnConfig || {};
            set({ permissionsLoading: false, permissions: normalizePermissions(res.data.permissions || []), columnConfig: cc, allowedCategories: getAllowedCategories(user.role, cc) });
          })
          .catch((error: any) => {
            if (error.response?.status === 401) { get().logout(); return; }
            if (get().token !== token) return;
            set({ permissionsLoading: false, permissions: fallbackPermissions(user.role), allowedCategories: getAllowedCategories(user.role, {}) });
          });
      } catch {
        get().logout();
      }
    } else { get().logout(); }
  },
}));
