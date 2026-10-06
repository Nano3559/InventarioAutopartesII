import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000/api";

// Sin header `Content-Type` por defecto: cada petición debe dejar que axios lo
// fije según su body. Un default `application/json` es destructivo con FormData,
// porque axios detecta el content-type y serializa el FormData a JSON
// (`{"image":{}}`), tirando los bytes del archivo: el backend responde 400
// "Debe subir una imagen" aunque el cliente sí haya enviado el File.
// Para JSON, axios sigue inferiendo `application/json` a partir del body
// (transformRequest), así que el resto de la API no se ve afectado.
const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
