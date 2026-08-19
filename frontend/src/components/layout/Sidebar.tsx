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
} from "lucide-react";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/inventario", label: "Inventario", icon: Package },
  { to: "/ventas", label: "Ventas", icon: ShoppingCart },
  { to: "/ventas-mayor", label: "Ventas por Mayor", icon: TrendingUp },
  { to: "/devoluciones", label: "Devoluciones", icon: RotateCcw },
  { to: "/solicitudes", label: "Solicitudes", icon: Send },
  { to: "/movimientos", label: "Movimientos", icon: ArrowLeftRight },
  { to: "/costos", label: "Costos", icon: DollarSign },
  { to: "/precios", label: "Precios", icon: Tags },
  { to: "/reportes", label: "Reportes", icon: BarChart3 },
  { to: "/configuracion", label: "Configuración", icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-lg font-bold">InventarioApp</h1>
      </div>
      <nav className="flex-1 overflow-y-auto p-2">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? "bg-primary-600 text-white"
                  : "text-gray-300 hover:bg-gray-800"
              }`
            }
          >
            <link.icon size={18} />
            <span>{link.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
