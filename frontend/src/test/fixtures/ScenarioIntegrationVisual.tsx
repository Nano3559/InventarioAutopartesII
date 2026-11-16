// Opt-in local review. Actual API/model, fixture session, no operational writes.
import{createRoot}from"react-dom/client";import api from"../../services/api";import PredictionsPage from"../../pages/PredictionsPage";import{MemoryRouter}from"react-router-dom";import"../../index.css";
api.defaults.baseURL="http://127.0.0.1:5192/api";
createRoot(document.getElementById("root")!).render(<MemoryRouter><main className="mx-auto max-w-6xl p-4 space-y-4"><p className="text-xs text-amber-200">Revisión local · Sesión de prueba · API y modelo 4.0.0 reales · Dataset sintético</p><PredictionsPage/></main></MemoryRouter>);
