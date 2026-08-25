import { useState } from "react";
import {
  BarChart3, Search, Download,
  TrendingUp, Package,
} from "lucide-react";
import toast from "react-hot-toast";

interface SalesReport {
  id: number; date: string; productName: string; brand: string; model: string;
  quantity: number; unitPrice: number; subtotal: number; tienda: string;
  customer: string | null;
}

interface InventoryReport {
  id: number; itemCode: string; productName: string; brand: string;
  model: string; tienda: string; stock: number; minStock: number;
}

interface MonthlyReport {
  month: string; tienda: string; totalVentas: number; totalCostos: number;
  utilidad: number; cantidadVentas: number;
}

const MOCK_SALES: SalesReport[] = [
  { id: 1, date: "2026-08-25", productName: "Filtro de Aceite", brand: "Bosch", model: "FIL-200", quantity: 3, unitPrice: 65.00, subtotal: 195.00, tienda: "Tienda Centro", customer: "Juan Pérez" },
  { id: 2, date: "2026-08-25", productName: "Pastillas de Freno", brand: "TRW", model: "DB-1200", quantity: 1, unitPrice: 180.00, subtotal: 180.00, tienda: "Tienda Centro", customer: null },
  { id: 3, date: "2026-08-24", productName: "Amortiguador Delantero", brand: "Monroe", model: "Matic-60", quantity: 2, unitPrice: 525.00, subtotal: 1050.00, tienda: "Tienda Norte", customer: "Taller Los Andes" },
  { id: 4, date: "2026-08-24", productName: "Correa de Distribución", brand: "Gates", model: "T-890", quantity: 5, unitPrice: 133.50, subtotal: 667.50, tienda: "Tienda Sur", customer: "María López" },
  { id: 5, date: "2026-08-23", productName: "Bujía Iridium", brand: "NGK", model: "IR-7", quantity: 8, unitPrice: 52.50, subtotal: 420.00, tienda: "Tienda Centro", customer: null },
  { id: 6, date: "2026-08-23", productName: "Radiador", brand: "Nissens", model: "RD-500", quantity: 1, unitPrice: 870.00, subtotal: 870.00, tienda: "Tienda Norte", customer: "Auto Service" },
  { id: 7, date: "2026-08-22", productName: "Filtro de Aceite", brand: "Bosch", model: "FIL-200", quantity: 10, unitPrice: 65.00, subtotal: 650.00, tienda: "Tienda Sur", customer: "Taller Mecánico" },
];

const MOCK_INVENTORY: InventoryReport[] = [
  { id: 1, itemCode: "FA-001", productName: "Filtro de Aceite", brand: "Bosch", model: "FIL-200", tienda: "Tienda Centro", stock: 45, minStock: 10 },
  { id: 2, itemCode: "FA-001", productName: "Filtro de Aceite", brand: "Bosch", model: "FIL-200", tienda: "Tienda Norte", stock: 0, minStock: 10 },
  { id: 3, itemCode: "PF-023", productName: "Pastillas de Freno", brand: "TRW", model: "DB-1200", tienda: "Tienda Centro", stock: 12, minStock: 5 },
  { id: 4, itemCode: "AD-105", productName: "Amortiguador Delantero", brand: "Monroe", model: "Matic-60", tienda: "Tienda Norte", stock: 8, minStock: 3 },
  { id: 5, itemCode: "CD-078", productName: "Correa de Distribución", brand: "Gates", model: "T-890", tienda: "Tienda Sur", stock: 0, minStock: 5 },
  { id: 6, itemCode: "BI-044", productName: "Bujía Iridium", brand: "NGK", model: "IR-7", tienda: "Tienda Centro", stock: 30, minStock: 10 },
  { id: 7, itemCode: "RA-012", productName: "Radiador", brand: "Nissens", model: "RD-500", tienda: "Tienda Norte", stock: 2, minStock: 2 },
];

const MOCK_MONTHLY: MonthlyReport[] = [
  { month: "Agosto 2026", tienda: "Tienda Centro", totalVentas: 1295.00, totalCostos: 780.00, utilidad: 515.00, cantidadVentas: 3 },
  { month: "Agosto 2026", tienda: "Tienda Norte", totalVentas: 1920.00, totalCostos: 1150.00, utilidad: 770.00, cantidadVentas: 2 },
  { month: "Agosto 2026", tienda: "Tienda Sur", totalVentas: 1317.50, totalCostos: 890.00, utilidad: 427.50, cantidadVentas: 2 },
  { month: "Julio 2026", tienda: "Tienda Centro", totalVentas: 8500.00, totalCostos: 5200.00, utilidad: 3300.00, cantidadVentas: 15 },
  { month: "Julio 2026", tienda: "Tienda Norte", totalVentas: 6200.00, totalCostos: 3800.00, utilidad: 2400.00, cantidadVentas: 11 },
  { month: "Julio 2026", tienda: "Tienda Sur", totalVentas: 4800.00, totalCostos: 3100.00, utilidad: 1700.00, cantidadVentas: 8 },
];

const TABS = [
  { key: "ventas", label: "Ventas", icon: TrendingUp },
  { key: "inventario", label: "Inventario", icon: Package },
  { key: "mensual", label: "Mensual por Tienda", icon: BarChart3 },
];

const formatBs = (v: number) =>
  `Bs. ${v.toLocaleString("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState("ventas");
  const [filterBrand, setFilterBrand] = useState("");
  const [filterTienda, setFilterTienda] = useState("");
  const [filterMonth, setFilterMonth] = useState("");
  const [filterSearch, setFilterSearch] = useState("");

  const tiendas = ["Tienda Centro", "Tienda Norte", "Tienda Sur"];

  const filteredSales = MOCK_SALES.filter((s) =>
    (!filterBrand || s.brand === filterBrand) &&
    (!filterTienda || s.tienda === filterTienda) &&
    (!filterMonth || s.date.startsWith(filterMonth)) &&
    (!filterSearch || s.productName.toLowerCase().includes(filterSearch.toLowerCase()) || s.brand.toLowerCase().includes(filterSearch.toLowerCase()))
  );

  const filteredInventory = MOCK_INVENTORY.filter((i) =>
    (!filterBrand || i.brand === filterBrand) &&
    (!filterTienda || i.tienda === filterTienda) &&
    (!filterSearch || i.productName.toLowerCase().includes(filterSearch.toLowerCase()))
  );

  const filteredMonthly = MOCK_MONTHLY.filter((m) =>
    (!filterTienda || m.tienda === filterTienda) &&
    (!filterMonth || m.month.toLowerCase().includes(filterMonth.toLowerCase()))
  );

  const totalVentas = filteredSales.reduce((sum, s) => sum + s.subtotal, 0);
  const totalInventory = filteredInventory.reduce((sum, i) => sum + i.stock, 0);
  const stockCritico = filteredInventory.filter((i) => i.stock <= i.minStock).length;

  const exportCSV = (data: Record<string, any>[], filename: string) => {
    if (!data.length) { toast.error("No hay datos para exportar"); return; }
    const headers = Object.keys(data[0]);
    const rows = data.map((r) => headers.map((h) => r[h]));
    const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${filename}.csv`; a.click();
    URL.revokeObjectURL(url);
    toast.success("Exportado correctamente");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Reportes</h1>
        <p className="text-gray-400 text-sm mt-1">Informes y estadísticas del sistema</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 bg-dark-800/50 border border-dark-700/50 rounded-xl p-1">
        {TABS.map((tab) => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.key
                ? "bg-primary-600/20 text-primary-400 border border-primary-600/30"
                : "text-gray-400 hover:text-gray-200 border border-transparent"
            }`}>
            <tab.icon size={16} /> {tab.label}
          </button>
        ))}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-1">Total Ventas</p>
          <p className="text-2xl font-bold text-amber-400">{formatBs(totalVentas)}</p>
          <p className="text-xs text-gray-500 mt-1">{filteredSales.length} registros</p>
        </div>
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-1">Stock Total</p>
          <p className="text-2xl font-bold text-blue-400">{totalInventory} unidades</p>
          <p className="text-xs text-gray-500 mt-1">{filteredInventory.length} ubicaciones</p>
        </div>
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-1">Stock Crítico</p>
          <p className={`text-2xl font-bold ${stockCritico > 0 ? "text-red-400" : "text-green-400"}`}>{stockCritico}</p>
          <p className="text-xs text-gray-500 mt-1">{stockCritico > 0 ? "Requiere atención" : "Todo en orden"}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input value={filterSearch} onChange={(e) => setFilterSearch(e.target.value)} placeholder="Buscar..."
            className="pl-9 pr-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500 w-48" />
        </div>
        <select value={filterBrand} onChange={(e) => setFilterBrand(e.target.value)}
          className="px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500">
          <option value="">Todas las marcas</option>
          <option value="Bosch">Bosch</option>
          <option value="TRW">TRW</option>
          <option value="Monroe">Monroe</option>
          <option value="Gates">Gates</option>
          <option value="NGK">NGK</option>
          <option value="Nissens">Nissens</option>
        </select>
        <select value={filterTienda} onChange={(e) => setFilterTienda(e.target.value)}
          className="px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500">
          <option value="">Todas las tiendas</option>
          {tiendas.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <input type="month" value={filterMonth} onChange={(e) => setFilterMonth(e.target.value)}
          className="px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
      </div>

      {/* Sales report */}
      {activeTab === "ventas" && (
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-700/50 flex items-center justify-between">
            <h3 className="text-white font-medium">Reporte de Ventas</h3>
            <button onClick={() => exportCSV(filteredSales.map((s) => ({
              Fecha: s.date, Producto: s.productName, Marca: s.brand, Modelo: s.model,
              Cantidad: s.quantity, "Precio Unit.": s.unitPrice, Subtotal: s.subtotal,
              Tienda: s.tienda, Cliente: s.customer || "N/A",
            })), "reporte_ventas")}
              className="flex items-center gap-1 px-3 py-1.5 bg-green-600/20 text-green-400 hover:bg-green-600/30 rounded-lg text-xs transition-all border border-green-600/30">
              <Download size={14} /> Exportar
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-700/50">
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Fecha</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Producto</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Marca</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Modelo</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium">Cant.</th>
                  <th className="text-right px-4 py-3 text-gray-400 font-medium">P. Unit.</th>
                  <th className="text-right px-4 py-3 text-gray-400 font-medium">Subtotal</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Tienda</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Cliente</th>
                </tr>
              </thead>
              <tbody>
                {filteredSales.length === 0 ? (
                  <tr><td colSpan={9} className="px-4 py-8 text-center text-gray-500">No hay ventas para los filtros seleccionados</td></tr>
                ) : filteredSales.map((s) => (
                  <tr key={s.id} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                    <td className="px-4 py-3 text-gray-300">{s.date}</td>
                    <td className="px-4 py-3 text-white font-medium">{s.productName}</td>
                    <td className="px-4 py-3 text-gray-300">{s.brand}</td>
                    <td className="px-4 py-3 text-gray-300">{s.model}</td>
                    <td className="px-4 py-3 text-gray-300 text-center">{s.quantity}</td>
                    <td className="px-4 py-3 text-gray-300 text-right">{formatBs(s.unitPrice)}</td>
                    <td className="px-4 py-3 text-amber-400 font-medium text-right">{formatBs(s.subtotal)}</td>
                    <td className="px-4 py-3 text-gray-300">{s.tienda}</td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{s.customer || "N/A"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Inventory report */}
      {activeTab === "inventario" && (
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-700/50 flex items-center justify-between">
            <h3 className="text-white font-medium">Reporte de Inventario</h3>
            <button onClick={() => exportCSV(filteredInventory.map((i) => ({
              Código: i.itemCode, Producto: i.productName, Marca: i.brand, Modelo: i.model,
              Tienda: i.tienda, Stock: i.stock, "Mínimo": i.minStock,
              Estado: i.stock === 0 ? "SIN STOCK" : i.stock <= i.minStock ? "CRÍTICO" : "OK",
            })), "reporte_inventario")}
              className="flex items-center gap-1 px-3 py-1.5 bg-green-600/20 text-green-400 hover:bg-green-600/30 rounded-lg text-xs transition-all border border-green-600/30">
              <Download size={14} /> Exportar
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-700/50">
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Código</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Producto</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Marca</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Modelo</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Tienda</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium">Stock</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium">Mínimo</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody>
                {filteredInventory.length === 0 ? (
                  <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-500">No hay datos para los filtros seleccionados</td></tr>
                ) : filteredInventory.map((i) => (
                  <tr key={i.id} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                    <td className="px-4 py-3 text-gray-300 font-mono text-xs">{i.itemCode}</td>
                    <td className="px-4 py-3 text-white font-medium">{i.productName}</td>
                    <td className="px-4 py-3 text-gray-300">{i.brand}</td>
                    <td className="px-4 py-3 text-gray-300">{i.model}</td>
                    <td className="px-4 py-3 text-gray-300">{i.tienda}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        i.stock === 0 ? "bg-red-500/20 text-red-400" :
                        i.stock <= i.minStock ? "bg-yellow-500/20 text-yellow-400" :
                        "bg-green-500/20 text-green-400"
                      }`}>{i.stock}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-center text-xs">{i.minStock}</td>
                    <td className="px-4 py-3 text-center">
                      {i.stock === 0 ? (
                        <span className="text-red-400 text-xs font-medium">SIN STOCK</span>
                      ) : i.stock <= i.minStock ? (
                        <span className="text-yellow-400 text-xs font-medium">CRÍTICO</span>
                      ) : (
                        <span className="text-green-400 text-xs font-medium">OK</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Monthly report */}
      {activeTab === "mensual" && (
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-700/50 flex items-center justify-between">
            <h3 className="text-white font-medium">Reporte Mensual por Tienda</h3>
            <button onClick={() => exportCSV(filteredMonthly.map((m) => ({
              Mes: m.month, Tienda: m.tienda, "Ventas": m.totalVentas,
              Costos: m.totalCostos, Utilidad: m.utilidad, "N° Ventas": m.cantidadVentas,
            })), "reporte_mensual")}
              className="flex items-center gap-1 px-3 py-1.5 bg-green-600/20 text-green-400 hover:bg-green-600/30 rounded-lg text-xs transition-all border border-green-600/30">
              <Download size={14} /> Exportar
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-700/50">
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Mes</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Tienda</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium">N° Ventas</th>
                  <th className="text-right px-4 py-3 text-gray-400 font-medium">Total Ventas</th>
                  <th className="text-right px-4 py-3 text-gray-400 font-medium">Total Costos</th>
                  <th className="text-right px-4 py-3 text-gray-400 font-medium">Utilidad</th>
                </tr>
              </thead>
              <tbody>
                {filteredMonthly.length === 0 ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No hay datos para los filtros seleccionados</td></tr>
                ) : filteredMonthly.map((m, idx) => (
                  <tr key={idx} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                    <td className="px-4 py-3 text-gray-300">{m.month}</td>
                    <td className="px-4 py-3 text-white font-medium">{m.tienda}</td>
                    <td className="px-4 py-3 text-gray-300 text-center">{m.cantidadVentas}</td>
                    <td className="px-4 py-3 text-amber-400 font-medium text-right">{formatBs(m.totalVentas)}</td>
                    <td className="px-4 py-3 text-gray-300 text-right">{formatBs(m.totalCostos)}</td>
                    <td className="px-4 py-3 text-green-400 font-medium text-right">{formatBs(m.utilidad)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
