import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { useAuthStore } from "./stores/authStore";
import MainLayout from "./components/layout/MainLayout";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import InventoryPage from "./pages/InventoryPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import SalesPage from "./pages/SalesPage";
import WholesalePage from "./pages/WholesalePage";
import ReturnsPage from "./pages/ReturnsPage";
import RequestsPage from "./pages/RequestsPage";
import MovementsPage from "./pages/MovementsPage";
import CostsPage from "./pages/CostsPage";
import PricesPage from "./pages/PricesPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
}

export default function App() {
  return (
    <>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="inventario" element={<InventoryPage />} />
          <Route path="inventario/:id" element={<ProductDetailPage />} />
          <Route path="ventas" element={<SalesPage />} />
          <Route path="ventas-mayor" element={<WholesalePage />} />
          <Route path="devoluciones" element={<ReturnsPage />} />
          <Route path="solicitudes" element={<RequestsPage />} />
          <Route path="movimientos" element={<MovementsPage />} />
          <Route path="costos" element={<CostsPage />} />
          <Route path="precios" element={<PricesPage />} />
          <Route path="reportes" element={<ReportsPage />} />
          <Route path="configuracion" element={<SettingsPage />} />
        </Route>
      </Routes>
    </>
  );
}
