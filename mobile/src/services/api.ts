import axios from "axios";
import AsyncStorage from "@react-native-async-storage/async-storage";

declare const process: { env?: { EXPO_PUBLIC_API_URL?: string } };

const API_URL = (typeof process !== "undefined" && process.env?.EXPO_PUBLIC_API_URL) || "http://localhost:3000/api";

export interface User {
  id: number;
  name: string;
  email: string;
  role: "ADMIN" | "TIENDA" | "INVENTARIO" | string;
  locationId: number | null;
}

export interface LoginResponse {
  token: string;
  user: User;
}

export const saveSession = async (session: LoginResponse) => {
  await AsyncStorage.multiSet([
    ["token", session.token],
    ["user", JSON.stringify(session.user)],
  ]);
};

export const clearSession = async () => {
  await AsyncStorage.multiRemove(["token", "user"]);
};

export const getStoredSession = async (): Promise<{ token: string; user: User } | null> => {
  const values = await AsyncStorage.multiGet(["token", "user"]);
  const token = values[0][1];
  const user = values[1][1];
  if (!token || !user) return null;

  try {
    return { token, user: JSON.parse(user) as User };
  } catch {
    await clearSession();
    return null;
  }
};

type UnauthorizedHandler = () => void;

let onUnauthorized: UnauthorizedHandler | null = null;

export const setOnUnauthorized = (handler: UnauthorizedHandler | null) => {
  onUnauthorized = handler;
};

const api = axios.create({
  baseURL: API_URL,
  timeout: 35000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      await clearSession();
      onUnauthorized?.();
    }
    return Promise.reject(error);
  }
);

export default api;

const pendingIds = new Map<string, Promise<string>>();
const operationStorageKey = (userId: number, scope: string) => `repuestopro:pending:${userId}:${scope}`;
export function pendingOperationId(userId: number, scope: string): Promise<string> {
  const key = operationStorageKey(userId, scope);
  const existing = pendingIds.get(key);
  if (existing) return existing;
  const pending = (async () => {
    const saved = await AsyncStorage.getItem(key);
    if (saved) return saved;
    // Identidad de operación, no credencial de autenticación.
    const id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
    await AsyncStorage.setItem(key, id);
    return id;
  })();
  pendingIds.set(key, pending);
  pending.catch(() => pendingIds.delete(key));
  return pending;
}
export async function getPendingOperation(userId: number, scope: string) { return AsyncStorage.getItem(operationStorageKey(userId, scope)); }
export async function completeOperation(userId: number, scope: string) {
  const key = operationStorageKey(userId, scope);
  await AsyncStorage.removeItem(key);
  pendingIds.delete(key);
}
export async function revokeStoredSession() {
  const token = await AsyncStorage.getItem("token");
  if (token) await api.post("/auth/logout", {}, { headers: { Authorization: `Bearer ${token}` } });
}
