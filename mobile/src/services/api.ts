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

const api = axios.create({
  baseURL: API_URL,
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
    }
    return Promise.reject(error);
  }
);

export default api;
