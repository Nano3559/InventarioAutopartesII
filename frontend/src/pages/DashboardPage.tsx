import { Package, ShoppingCart, AlertTriangle, Clock } from "lucide-react";

const stats = [
  {
    label: "Total Productos",
    value: "--",
    icon: Package,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/20",
  },
  {
    label: "Ventas del Día",
    value: "--",
    icon: ShoppingCart,
    color: "text-green-400",
    bg: "bg-green-500/10",
    border: "border-green-500/20",
  },
  {
    label: "Productos sin Stock",
    value: "--",
    icon: AlertTriangle,
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/20",
  },
  {
    label: "Solicitudes Pendientes",
    value: "--",
    icon: Clock,
    color: "text-yellow-400",
    bg: "bg-yellow-500/10",
    border: "border-yellow-500/20",
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">Resumen general del sistema</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className={`bg-dark-800/50 border ${stat.border} rounded-2xl p-5 hover:scale-[1.02] transition-all`}
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`w-10 h-10 ${stat.bg} rounded-xl flex items-center justify-center`}>
                <stat.icon size={20} className={stat.color} />
              </div>
            </div>
            <p className="text-3xl font-bold text-white">{stat.value}</p>
            <p className="text-sm text-gray-400 mt-1">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Ventas por Tienda</h3>
          <p className="text-gray-400 text-sm">Sin datos disponibles</p>
        </div>
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Stock por Ubicación</h3>
          <p className="text-gray-400 text-sm">Sin datos disponibles</p>
        </div>
      </div>
    </div>
  );
}
