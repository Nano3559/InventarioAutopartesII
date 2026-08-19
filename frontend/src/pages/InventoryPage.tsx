import { Package, Search, Plus, Filter } from "lucide-react";

export default function InventoryPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Inventario</h1>
          <p className="text-gray-400 text-sm mt-1">Gestión de productos y stock</p>
        </div>
        <button className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2 shadow-lg shadow-primary-600/20">
          <Plus size={18} />
          Nuevo Producto
        </button>
      </div>

      {/* Search and filters */}
      <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="Buscar por código, nombre, marca, modelo..."
              className="w-full pl-10 pr-4 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-sm"
            />
          </div>
          <div className="flex items-center gap-2 text-gray-400">
            <Filter size={16} />
            <span className="text-sm">Filtros</span>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
        <div className="p-6 text-center">
          <Package size={48} className="text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400">Sin productos registrados</p>
          <p className="text-gray-500 text-sm mt-1">Agrega productos para comenzar a gestionar el inventario</p>
        </div>
      </div>
    </div>
  );
}
