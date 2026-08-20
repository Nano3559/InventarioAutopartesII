import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { useAuthStore } from "./stores/authStore";
import MainLayout from "./components/layout/MainLayout";
import PublicLayout from "./components/public/PublicLayout";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import PublicProductsPage from "./pages/PublicProductsPage";
import PublicProductDetailPage from "./pages/PublicProductDetailPage";
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
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#1e293b",
            color: "#f1f5f9",
            border: "1px solid #334155",
          },
        }}
      />
      <Routes>
        {/* Public routes with navbar + footer */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/productos" element={<PublicProductsPage />} />
          <Route path="/productos/:id" element={<PublicProductDetailPage />} />
        </Route>

        {/* Login */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected admin routes */}
        <Route
          path="/panel"
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
