import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { useAuthStore } from "./stores/authStore";
import MainLayout from "./components/layout/MainLayout";
import PublicLayout from "./components/public/PublicLayout";
import RoleRoute from "./components/RoleRoute";
const LandingPage = lazy(() => import("./pages/LandingPage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const ContactPage = lazy(() => import("./pages/ContactPage"));
const PublicProductsPage = lazy(() => import("./pages/PublicProductsPage"));
const PublicProductDetailPage = lazy(() => import("./pages/PublicProductDetailPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const ProductDetailPage = lazy(() => import("./pages/ProductDetailPage"));
const SalesPage = lazy(() => import("./pages/SalesPage"));
const WholesalePage = lazy(() => import("./pages/WholesalePage"));
const ReturnsPage = lazy(() => import("./pages/ReturnsPage"));
const RequestsPage = lazy(() => import("./pages/RequestsPage"));
const MovementsPage = lazy(() => import("./pages/MovementsPage"));
const CostsPage = lazy(() => import("./pages/CostsPage"));
const PricesPage = lazy(() => import("./pages/PricesPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
import ErrorBoundary from "./components/ErrorBoundary";

const ALL = ["ADMIN", "INVENTARIO", "TIENDA"];

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
      <ErrorBoundary>
      <Suspense fallback={<div role="status" className="p-6 text-gray-400">Cargando pantalla…</div>}>
      <Routes>
        {/* Public routes */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/contacto" element={<ContactPage />} />
          <Route path="/productos" element={<PublicProductsPage />} />
          <Route path="/productos/:id" element={<PublicProductDetailPage />} />
        </Route>

        <Route path="/login" element={<LoginPage />} />

        {/* Protected admin panel */}
        <Route
          path="/panel"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          {/* Dashboard — todos los roles */}
          <Route index element={<DashboardPage />} />

          {/* Inventario — ADMIN + INVENTARIO + TIENDA (solo lectura) */}
          <Route path="inventario" element={
            <RoleRoute allowedRoles={["ADMIN", "INVENTARIO", "TIENDA"]} module="inventario">
              <InventoryPage />
            </RoleRoute>
          } />
          <Route path="inventario/:id" element={
            <RoleRoute allowedRoles={["ADMIN", "INVENTARIO", "TIENDA"]} module="inventario">
              <ProductDetailPage />
            </RoleRoute>
          } />

          {/* Ventas — ADMIN + TIENDA */}
          <Route path="ventas" element={
            <RoleRoute allowedRoles={["ADMIN", "TIENDA"]} module="ventas">
              <SalesPage />
            </RoleRoute>
          } />

          {/* Ventas por Mayor — ADMIN + TIENDA */}
          <Route path="ventas-mayor" element={
            <RoleRoute allowedRoles={["ADMIN", "TIENDA"]} module="ventas-mayor">
              <WholesalePage />
            </RoleRoute>
          } />

          {/* Devoluciones — ADMIN + TIENDA */}
          <Route path="devoluciones" element={
            <RoleRoute allowedRoles={["ADMIN", "TIENDA"]} module="devoluciones">
              <ReturnsPage />
            </RoleRoute>
          } />

          {/* Solicitudes — todos */}
          <Route path="solicitudes" element={
            <RoleRoute allowedRoles={ALL} module="solicitudes">
              <RequestsPage />
            </RoleRoute>
          } />

          {/* Movimientos — ADMIN + INVENTARIO */}
          <Route path="movimientos" element={
            <RoleRoute allowedRoles={["ADMIN", "INVENTARIO"]} module="movimientos">
              <MovementsPage />
            </RoleRoute>
          } />

          {/* Costos — solo ADMIN */}
          <Route path="costos" element={
            <RoleRoute allowedRoles={["ADMIN"]} module="costos">
              <CostsPage />
            </RoleRoute>
          } />

          {/* Precios — solo ADMIN */}
          <Route path="precios" element={
            <RoleRoute allowedRoles={["ADMIN"]} module="precios">
              <PricesPage />
            </RoleRoute>
          } />

          {/* Reportes — ADMIN + TIENDA */}
          <Route path="reportes" element={
            <RoleRoute allowedRoles={["ADMIN", "TIENDA"]} module="reportes">
              <ReportsPage />
            </RoleRoute>
          } />

          {/* Configuración — solo ADMIN */}
          <Route path="configuracion" element={
            <RoleRoute allowedRoles={["ADMIN"]} module="configuracion">
              <SettingsPage />
            </RoleRoute>
          } />
        </Route>
      </Routes>
      </Suspense>
      </ErrorBoundary>
    </>
  );
}
