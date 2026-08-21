import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Package, ShoppingCart, TrendingUp,
  ArrowLeftRight, DollarSign, BarChart3, Settings,
  RotateCcw, Send, Tags, Car, LogOut,
} from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import { useNavigate } from "react-router-dom";

const allLinks = [
  { to: "/panel", label: "Dashboard", icon: LayoutDashboard, roles: ["ADMIN", "INVENTARIO", "TIENDA"] },
  { to: "/panel/inventario", label: "Inventario", icon: Package, roles: ["ADMIN", "INVENTARIO"] },
  { to: "/panel/ventas", label: "Ventas", icon: ShoppingCart, roles: ["ADMIN", "TIENDA"] },
  { to: "/panel/ventas-mayor", label: "Ventas por Mayor", icon: TrendingUp, roles: ["ADMIN", "TIENDA"] },
  { to: "/panel/devoluciones", label: "Devoluciones", icon: RotateCcw, roles: ["ADMIN", "TIENDA"] },
  { to: "/panel/solicitudes", label: "Solicitudes", icon: Send, roles: ["ADMIN", "INVENTARIO", "TIENDA"] },
  { to: "/panel/movimientos", label: "Movimientos", icon: ArrowLeftRight, roles: ["ADMIN", "INVENTARIO"] },
  { to: "/panel/costos", label: "Costos", icon: DollarSign, roles: ["ADMIN", "INVENTARIO"] },
  { to: "/panel/precios", label: "Precios", icon: Tags, roles: ["ADMIN", "INVENTARIO"] },
  { to: "/panel/reportes", label: "Reportes", icon: BarChart3, roles: ["ADMIN", "TIENDA"] },
  { to: "/panel/configuracion", label: "Configuración", icon: Settings, roles: ["ADMIN"] },
];

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const role = user?.role || "";

  const links = allLinks.filter((l) => l.roles.includes(role));

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <aside className="w-64 bg-dark-900 border-r border-dark-700/50 flex flex-col">
      <div className="p-5 border-b border-dark-700/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center shadow-lg shadow-primary-600/20">
            <Car size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">RepuestoPro</h1>
            <p className="text-xs text-gray-500">{role || "Sistema"}</p>
          </div>
        </div>
      </div>

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
