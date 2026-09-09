import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("../../services/api", async () => {
  const actual = await vi.importActual<typeof import("../../services/api")>(
    "../../services/api"
  );
  return actual;
});

const apiMock = await import("../../services/api");
const api = apiMock.default;

describe("api interceptors", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  describe("request interceptor", () => {
    it("agrega Authorization cuando hay token", async () => {
      localStorage.setItem("token", "test-token-123");

      const config = {
        headers: {} as Record<string, string>,
        url: "/test",
      };

      const interceptors = (api.interceptors.request as any).handlers;
      const fulfilled = interceptors[0].fulfilled;
      const result = await fulfilled(config);

      expect(result.headers.Authorization).toBe("Bearer test-token-123");
    });

    it("no agrega Authorization cuando no hay token", async () => {
      const config = {
        headers: {} as Record<string, string>,
        url: "/test",
      };

      const interceptors = (api.interceptors.request as any).handlers;
      const fulfilled = interceptors[0].fulfilled;
      const result = await fulfilled(config);

      expect(result.headers.Authorization).toBeUndefined();
    });
  });

  describe("response interceptor", () => {
    it("pasa la respuesta exitosa sin modificar", async () => {
      const response = { data: { ok: true }, status: 200 };

      const interceptors = (api.interceptors.response as any).handlers;
      const fulfilled = interceptors[0].fulfilled;
      const result = fulfilled(response);

      expect(result).toEqual(response);
    });

    it("en 401 limpia token de localStorage", async () => {
      localStorage.setItem("token", "tok-to-remove");

      const error = {
        response: { status: 401 },
      };

      const interceptors = (api.interceptors.response as any).handlers;
      const rejected = interceptors[0].rejected;

      try {
        await rejected(error);
      } catch {
        // Se rechaza
      }

      expect(localStorage.getItem("token")).toBeNull();
    });

    it("en 401 redirige a /login", async () => {
      const originalHref = window.location.href;
      const mockHref = vi.fn();
      Object.defineProperty(window, "location", {
        value: { ...window.location, set href(v: string) { mockHref(v); }, get href() { return originalHref; } },
        writable: true,
        configurable: true,
      });

      const error = {
        response: { status: 401 },
      };

      const interceptors = (api.interceptors.response as any).handlers;
      const rejected = interceptors[0].rejected;

      try {
        await rejected(error);
      } catch {
        // Se rechaza
      }

      expect(mockHref).toHaveBeenCalledWith("/login");

      Object.defineProperty(window, "location", {
        value: { href: originalHref },
        writable: true,
        configurable: true,
      });
    });

    it("en error distinto de 401 NO limpia token", async () => {
      localStorage.setItem("token", "tok-keep");

      const error = {
        response: { status: 500 },
      };

      const interceptors = (api.interceptors.response as any).handlers;
      const rejected = interceptors[0].rejected;

      try {
        await rejected(error);
      } catch {
        // Se rechaza
      }

      expect(localStorage.getItem("token")).toBe("tok-keep");
    });

    it("en error distinto de 401 NO redirige", async () => {
      const mockHref = vi.fn();
      Object.defineProperty(window, "location", {
        value: { ...window.location, set href(v: string) { mockHref(v); }, get href() { return "http://localhost/login"; } },
        writable: true,
        configurable: true,
      });

      const error = {
        response: { status: 400 },
      };

      const interceptors = (api.interceptors.response as any).handlers;
      const rejected = interceptors[0].rejected;

      try {
        await rejected(error);
      } catch {
        // Se rechaza
      }

      expect(mockHref).not.toHaveBeenCalled();

      Object.defineProperty(window, "location", {
        value: { href: "http://localhost/login" },
        writable: true,
        configurable: true,
      });
    });

    it("en error sin response NO limpia token", async () => {
      localStorage.setItem("token", "tok-network");

      const error = new Error("Network Error");

      const interceptors = (api.interceptors.response as any).handlers;
      const rejected = interceptors[0].rejected;

      try {
        await rejected(error);
      } catch {
        // Se rechaza
      }

      expect(localStorage.getItem("token")).toBe("tok-network");
    });
  });
});
