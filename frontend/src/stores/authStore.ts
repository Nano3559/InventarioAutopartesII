import { create } from "zustand";
import type { User } from "../types";
import api from "../services/api";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  permissions: string[];
  columnConfig: Record<string, string[]>;
  login: (user: User, token: string) => Promise<void>;
  logout: () => void;
  loadFromStorage: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("token"),
  isAuthenticated: !!localStorage.getItem("token"),
  permissions: [],
  columnConfig: {},
  login: async (user, token) => {
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(user));
    set({ user, token, isAuthenticated: true });

    try {
      const res = await api.get("/permissions/permissions/me");
      const perms = res.data.permissions || [];
      set({ permissions: perms, columnConfig: res.data.columnConfig || {} });
    } catch {
      // Si falla, ADMIN tiene todos los permisos
      if (user.role === "ADMIN") {
        set({
          permissions: [
            "inventario", "ventas", "ventas-mayor", "devoluciones",
            "solicitudes", "movimientos", "costos", "precios", "reportes", "configuracion",
          ],
        });
      }
    }
  },
  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    set({ user, token, isAuthenticated: false, permissions: [], columnConfig: {} });
  },
  loadFromStorage: () => {
    const token = localStorage.getItem("token");
    const userStr = localStorage.getItem("user");
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr);
        set({ user, token, isAuthenticated: true });

        // Reload permissions from backend
        api
          .get("/permissions/permissions/me")
          .then((res) => {
            set({ permissions: res.data.permissions || [], columnConfig: res.data.columnConfig || {} });
          })
          .catch(() => {
            if (user.role === "ADMIN") {
              set({
                permissions: [
                  "inventario", "ventas", "ventas-mayor", "devoluciones",
                  "solicitudes", "movimientos", "costos", "precios", "reportes", "configuracion",
                ],
              });
            }
          });
      } catch {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
      }
    }
  },
}));
