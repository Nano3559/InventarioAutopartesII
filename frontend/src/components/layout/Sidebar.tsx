import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  TrendingUp,
  ArrowLeftRight,
  DollarSign,
  BarChart3,
  Settings,
  RotateCcw,
  Send,
  Tags,
  Car,
  LogOut,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { useNavigate } from "react-router-dom";

const links = [
  { to: "/panel", label: "Dashboard", icon: LayoutDashboard },
  { to: "/panel/inventario", label: "Inventario", icon: Package },
  { to: "/panel/ventas", label: "Ventas", icon: ShoppingCart },
  { to: "/panel/ventas-mayor", label: "Ventas por Mayor", icon: TrendingUp },
  { to: "/panel/devoluciones", label: "Devoluciones", icon: RotateCcw },
  { to: "/panel/solicitudes", label: "Solicitudes", icon: Send },
  { to: "/panel/movimientos", label: "Movimientos", icon: ArrowLeftRight },
  { to: "/panel/costos", label: "Costos", icon: DollarSign },
  { to: "/panel/precios", label: "Precios", icon: Tags },
  { to: "/panel/reportes", label: "Reportes", icon: BarChart3 },
  { to: "/panel/configuracion", label: "Configuración", icon: Settings },
];

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <aside className="w-64 bg-dark-900 border-r border-dark-700/50 flex flex-col">
      {/* Logo */}
      <div className="p-5 border-b border-dark-700/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center shadow-lg shadow-primary-600/20">
            <Car size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">RepuestoPro</h1>
            <p className="text-xs text-gray-500">{user?.role || "Sistema"}</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/panel"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all ${
                isActive
                  ? "bg-primary-600/10 text-primary-400 border border-primary-600/20"
                  : "text-gray-400 hover:bg-dark-800 hover:text-gray-200 border border-transparent"
              }`
            }
          >
            <link.icon size={18} />
            <span>{link.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Logout */}
      <div className="p-3 border-t border-dark-700/50">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm text-gray-400 hover:bg-red-500/10 hover:text-red-400 border border-transparent hover:border-red-500/20 transition-all"
        >
          <LogOut size={18} />
          <span>Cerrar Sesión</span>
        </button>
      </div>
    </aside>
  );
}
