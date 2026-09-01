import { useState, useEffect, useCallback } from "react";
import {
  BarChart3, Search, Download,
  TrendingUp, Package, RefreshCw, CalendarDays,
} from "lucide-react";
import toast from "react-hot-toast";
import api from "../services/api";

interface SalesReport {
  id: number; date: string; type: string; total: number;
  location: { name: string } | null;
  customer: { name: string } | null;
  user: { name: string } | null;
  itemCount: number;
  payments: { method: string; amount: number }[];
}

interface InventoryItem {
  id: number; stock: number; minStock: number;
  product: { id: number; name: string; itemCode: string; brand: string; model: string; manufacturer: string };
  location: { id: number; name: string; type: string };
  status: string;
}

interface MonthlyReport {
  location: { id: number; name: string; type: string };
  summary: { totalSales: number; totalReturns: number; netSales: number; saleCount: number; averagePerSale: number };
  topProducts: { product: { name: string; brand: string }; quantitySold: number; totalRevenue: number }[];
}

interface Location {
  id: number; name: string;
}

interface DailyStore {
  locationName: string;
  total: number;
  saleCount: number;
  returns: number;
  products: { name: string; quantity: number; subtotal: number }[];
}

interface DailyGroup {
  date: string;
  stores: DailyStore[];
  total: number;
  saleCount: number;
}

const TABS = [
  { key: "ventas", label: "Ventas", icon: TrendingUp },
  { key: "diario", label: "Diario por Tienda", icon: CalendarDays },
  { key: "inventario", label: "Inventario", icon: Package },
  { key: "mensual", label: "Mensual por Tienda", icon: BarChart3 },
];

const formatBs = (v: number) =>
  `Bs. ${v.toLocaleString("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState("ventas");
  const [locations, setLocations] = useState<Location[]>([]);

  const [salesData, setSalesData] = useState<SalesReport[]>([]);
  const [salesSummary, setSalesSummary] = useState({ totalSales: 0, count: 0, average: 0 });
  const [salesLoading, setSalesLoading] = useState(false);

  const [inventoryData, setInventoryData] = useState<{ locations: any[]; totalProducts: number; totalStock: number; lowStockCount: number } | null>(null);
  const [inventoryLoading, setInventoryLoading] = useState(false);

  const [monthlyData, setMonthlyData] = useState<{ period: any; locations: MonthlyReport[]; summary: any } | null>(null);
  const [monthlyLoading, setMonthlyLoading] = useState(false);

  const [filterLocation, setFilterLocation] = useState("");
  const [filterMonth, setFilterMonth] = useState("");
  const [filterFrom, setFilterFrom] = useState("");
  const [filterTo, setFilterTo] = useState("");
  const [filterNoInvoice, setFilterNoInvoice] = useState(false);
  const [filterSearch, setFilterSearch] = useState("");

  const [dailyData, setDailyData] = useState<DailyGroup[]>([]);
  const [dailyLoading, setDailyLoading] = useState(false);

  useEffect(() => {
    api.get("/locations").then((res) => setLocations(res.data.locations || res.data)).catch(() => {});
  }, []);

  const fetchSales = useCallback(async () => {
    try {
      setSalesLoading(true);
      const params = new URLSearchParams();
      if (filterLocation) params.set("locationId", filterLocation);
      if (filterFrom) params.set("startDate", filterFrom);
      if (filterTo) params.set("endDate", filterTo);
      if (filterNoInvoice) params.set("noInvoice", "true");
      const res = await api.get(`/reports/sales?${params.toString()}`);
      setSalesData(res.data.sales);
      setSalesSummary(res.data.summary);
    } catch {
      toast.error("Error al cargar reporte de ventas");
    } finally {
      setSalesLoading(false);
    }
  }, [filterLocation, filterFrom, filterTo, filterNoInvoice]);

  const fetchDaily = useCallback(async () => {
    try {
      setDailyLoading(true);
      const params = new URLSearchParams({ limit: "1000" });
      if (filterFrom) params.set("startDate", filterFrom);
      if (filterTo) params.set("endDate", filterTo);
      const [salesRes, returnsRes] = await Promise.all([
        api.get(`/sales?${params.toString()}`),
        api.get("/returns?limit=100"),
      ]);
      groupDaily(salesRes.data.sales, returnsRes.data.returns || []);
    } catch {
      toast.error("Error al cargar reporte diario");
      setDailyData([]);
    } finally {
      setDailyLoading(false);
    }
  }, [filterFrom, filterTo, locations]);

  const groupDaily = (sales: any[], returns: any[]) => {
    const byDate: Record<string, DailyGroup> = {};
    for (const s of sales) {
      const day = s.saleDate ? new Date(s.saleDate).toDateString() : "Sin fecha";
      if (!byDate[day]) byDate[day] = { date: day, stores: [], total: 0, saleCount: 0 };
      const group = byDate[day];
      group.total += Number(s.total) || 0;
      group.saleCount += 1;
      const locName = s.location?.name || "Sin tienda";
      let store = group.stores.find((st) => st.locationName === locName);
      if (!store) {
        store = { locationName: locName, total: 0, saleCount: 0, returns: 0, products: [] };
        group.stores.push(store);
      }
      store.total += Number(s.total) || 0;
      store.saleCount += 1;
      for (const item of s.items || []) {
        const pName = item.product?.name || item.productId || "Producto";
        let p = store.products.find((pr) => pr.name === pName);
        if (!p) {
          p = { name: pName, quantity: 0, subtotal: 0 };
          store.products.push(p);
        }
        p.quantity += item.quantity || 0;
        p.subtotal += Number(item.subtotal) || 0;
      }
    }
    for (const item of returns) {
      const day = item.date ? new Date(item.date).toDateString() : "Sin fecha";
      if (!byDate[day]) byDate[day] = { date: day, stores: [], total: 0, saleCount: 0 };
      const group = byDate[day];
      const locName = locations.find((location) => location.id === item.sale?.locationId)?.name || "Sin tienda";
      let store = group.stores.find((st) => st.locationName === locName);
      if (!store) {
        store = { locationName: locName, total: 0, saleCount: 0, returns: 0, products: [] };
        group.stores.push(store);
      }
      store.returns += Number(item.amount) || 0;
    }
    const sorted = Object.values(byDate).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
    setDailyData(sorted);
  };

  const fetchInventory = useCallback(async () => {
    try {
      setInventoryLoading(true);
      const params = new URLSearchParams();
      if (filterLocation) params.set("locationId", filterLocation);
      if (filterSearch) params.set("brand", filterSearch);
      const res = await api.get(`/reports/inventory?${params.toString()}`);
      setInventoryData(res.data);
    } catch {
      toast.error("Error al cargar reporte de inventario");
    } finally {
      setInventoryLoading(false);
    }
  }, [filterLocation, filterSearch]);

  const fetchMonthly = useCallback(async () => {
    try {
      setMonthlyLoading(true);
      const params = new URLSearchParams();
      if (filterMonth) {
        const [year, month] = filterMonth.split("-");
        if (year) params.set("year", year);
        if (month) params.set("month", month);
      }
      const res = await api.get(`/reports/monthly?${params.toString()}`);
      setMonthlyData(res.data);
    } catch {
      toast.error("Error al cargar reporte mensual");
    } finally {
      setMonthlyLoading(false);
    }
  }, [filterMonth]);

  useEffect(() => {
    if (activeTab === "ventas") fetchSales();
    if (activeTab === "diario") fetchDaily();
    if (activeTab === "inventario") fetchInventory();
    if (activeTab === "mensual") fetchMonthly();
  }, [activeTab, fetchSales, fetchDaily, fetchInventory, fetchMonthly]);

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

  const formatDate = (d: string) => new Date(d).toLocaleDateString("es-BO", { day: "2-digit", month: "short", year: "numeric" });

  const filteredSales = salesData.filter((s) =>
    !filterSearch || (s.customer?.name || "").toLowerCase().includes(filterSearch.toLowerCase()) || String(s.id).includes(filterSearch)
  );

  const dailyTotal = dailyData.reduce((sum, g) => sum + g.total, 0);
  const dailyCount = dailyData.reduce((sum, g) => sum + g.saleCount, 0);

  const inventoryItems: InventoryItem[] = inventoryData?.locations?.flatMap((loc: any) => loc.items) || [];
  const filteredInventory = inventoryItems.filter((i) =>
    !filterSearch || i.product.name.toLowerCase().includes(filterSearch.toLowerCase()) || i.product.brand.toLowerCase().includes(filterSearch.toLowerCase())
  );

  const monthlyLocations: MonthlyReport[] = monthlyData?.locations || [];
  const filteredMonthly = monthlyLocations.filter((m) =>
    !filterLocation || String(m.location.id) === filterLocation
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Reportes</h1>
        <p className="text-gray-400 text-sm mt-1">Informes y estadísticas del sistema</p>
      </div>

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

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-1">Total Ventas</p>
          <p className="text-2xl font-bold text-amber-400">{formatBs(activeTab === "diario" ? dailyTotal : salesSummary.totalSales || inventoryData?.totalStock || monthlyData?.summary?.totalSales || 0)}</p>
          <p className="text-xs text-gray-500 mt-1">{activeTab === "ventas" ? `${salesSummary.count} registros` : activeTab === "diario" ? `${dailyCount} ventas` : activeTab === "inventario" ? `${inventoryData?.totalProducts || 0} productos` : `${monthlyData?.summary?.totalLocations || 0} ubicaciones`}</p>
        </div>
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-1">{activeTab === "inventario" ? "Stock Total" : activeTab === "mensual" ? "Ventas Netas" : "Promedio/Venta"}</p>
          <p className="text-2xl font-bold text-blue-400">{activeTab === "ventas" ? formatBs(salesSummary.average) : activeTab === "diario" ? formatBs(dailyCount > 0 ? dailyTotal / dailyCount : 0) : activeTab === "inventario" ? `${inventoryData?.totalStock || 0} uds` : formatBs(monthlyData?.summary?.netSales || 0)}</p>
          <p className="text-xs text-gray-500 mt-1">{activeTab === "inventario" ? `${inventoryData?.lowStockCount || 0} bajo stock` : activeTab === "mensual" ? `${monthlyData?.summary?.activeLocations || 0} activas` : ""}</p>
        </div>
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-xl p-4">
          <p className="text-gray-400 text-xs mb-1">Stock Crítico</p>
          <p className={`text-2xl font-bold ${(inventoryData?.lowStockCount || 0) > 0 ? "text-red-400" : "text-green-400"}`}>{inventoryData?.lowStockCount || 0}</p>
          <p className="text-xs text-gray-500 mt-1">{(inventoryData?.lowStockCount || 0) > 0 ? "Requiere atención" : "Todo en orden"}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input value={filterSearch} onChange={(e) => setFilterSearch(e.target.value)} placeholder="Buscar..."
            className="pl-9 pr-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500 w-48" />
        </div>
        <select value={filterLocation} onChange={(e) => setFilterLocation(e.target.value)}
          className="px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500">
          <option value="">Todas las ubicaciones</option>
          {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
        {activeTab !== "mensual" ? (
          <>
            <input type="date" value={filterFrom} onChange={(e) => setFilterFrom(e.target.value)}
              className="px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
            <span className="text-gray-500 text-sm">→</span>
            <input type="date" value={filterTo} onChange={(e) => setFilterTo(e.target.value)}
              className="px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
            {activeTab === "ventas" && (
              <label className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-300">
                <input type="checkbox" checked={filterNoInvoice} onChange={(e) => setFilterNoInvoice(e.target.checked)} className="accent-primary-600" />
                Sin factura
              </label>
            )}
          </>
        ) : (
          <input type="month" value={filterMonth} onChange={(e) => setFilterMonth(e.target.value)}
            className="px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
        )}
      </div>

      {activeTab === "ventas" && (
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-700/50 flex items-center justify-between">
            <h3 className="text-white font-medium">Reporte de Ventas</h3>
            <div className="flex items-center gap-2">
              <button onClick={fetchSales} className="p-1.5 text-gray-400 hover:text-white rounded-lg transition-all"><RefreshCw size={14} /></button>
              <button onClick={() => exportCSV(filteredSales.map((s) => ({
                ID: s.id, Fecha: formatDate(s.date), Tipo: s.type, Total: s.total,
                Ubicacion: s.location?.name || "N/A", Cliente: s.customer?.name || "N/A", Vendedor: s.user?.name || "N/A",
              })), "reporte_ventas")}
                className="flex items-center gap-1 px-3 py-1.5 bg-green-600/20 text-green-400 hover:bg-green-600/30 rounded-lg text-xs transition-all border border-green-600/30">
                <Download size={14} /> Exportar
              </button>
            </div>
          </div>
          {salesLoading ? (
            <div className="flex items-center justify-center h-32"><RefreshCw size={24} className="text-primary-400 animate-spin" /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-dark-700/50">
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">ID</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Fecha</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Tipo</th>
                    <th className="text-right px-4 py-3 text-gray-400 font-medium">Total</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Ubicación</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Cliente</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Vendedor</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSales.length === 0 ? (
                    <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">No hay ventas para los filtros seleccionados</td></tr>
                  ) : filteredSales.map((s) => (
                    <tr key={s.id} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                      <td className="px-4 py-3 text-gray-300 font-mono text-xs">#{s.id}</td>
                      <td className="px-4 py-3 text-gray-300">{formatDate(s.date)}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.type === "MAYOR" ? "bg-amber-500/10 text-amber-400" : "bg-blue-500/10 text-blue-400"}`}>
                          {s.type === "MAYOR" ? "Mayor" : "Normal"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-amber-400 font-medium text-right">{formatBs(s.total)}</td>
                      <td className="px-4 py-3 text-gray-300">{s.location?.name || "N/A"}</td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{s.customer?.name || "N/A"}</td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{s.user?.name || "N/A"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "diario" && (
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-700/50 flex items-center justify-between">
            <h3 className="text-white font-medium">Reporte Diario por Tienda</h3>
            <div className="flex items-center gap-2">
              <button onClick={fetchDaily} className="p-1.5 text-gray-400 hover:text-white rounded-lg transition-all"><RefreshCw size={14} /></button>
              <button onClick={() => exportCSV(dailyData.flatMap((g) => g.stores.map((st) => ({
                Fecha: formatDate(g.date), Tienda: st.locationName,
                "N° Ventas": st.saleCount, Total: st.total, Devoluciones: st.returns,
              }))), "reporte_diario")}
                className="flex items-center gap-1 px-3 py-1.5 bg-green-600/20 text-green-400 hover:bg-green-600/30 rounded-lg text-xs transition-all border border-green-600/30">
                <Download size={14} /> Exportar
              </button>
            </div>
          </div>
          {dailyLoading ? (
            <div className="flex items-center justify-center h-32"><RefreshCw size={24} className="text-primary-400 animate-spin" /></div>
          ) : dailyData.length === 0 ? (
            <div className="p-10 text-center text-gray-500">No hay ventas en el rango seleccionado</div>
          ) : (
            <div className="p-4 space-y-4">
              {dailyData.map((g) => (
                <div key={g.date} className="border border-dark-700/50 rounded-xl overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-2 bg-dark-900/40 border-b border-dark-700/50">
                    <span className="text-white font-medium text-sm">{formatDate(g.date)}</span>
                    <span className="text-xs text-gray-400">{g.saleCount} ventas · <span className="text-amber-400 font-medium">{formatBs(g.total)}</span></span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-dark-700/50">
                          <th className="text-left px-4 py-2 text-gray-400 font-medium">Tienda</th>
                          <th className="text-center px-4 py-2 text-gray-400 font-medium">N° Ventas</th>
                          <th className="text-right px-4 py-2 text-gray-400 font-medium">Total</th>
                          <th className="text-right px-4 py-2 text-gray-400 font-medium">Devoluciones</th>
                        </tr>
                      </thead>
                      <tbody>
                        {g.stores.map((st) => (
                          <tr key={st.locationName} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                            <td className="px-4 py-2 text-white font-medium">{st.locationName}</td>
                            <td className="px-4 py-2 text-gray-300 text-center">{st.saleCount}</td>
                            <td className="px-4 py-2 text-amber-400 font-medium text-right">{formatBs(st.total)}</td>
                            <td className="px-4 py-2 text-red-400 text-right">{formatBs(st.returns)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {g.stores.some((st) => st.products.length > 0) && (
                    <div className="p-3 border-t border-dark-700/50">
                      <p className="text-xs text-gray-400 mb-2">Productos vendidos del día</p>
                      <div className="flex flex-wrap gap-2">
                        {Array.from(new Set(g.stores.flatMap((st) => st.products.map((p) => p.name)))).slice(0, 10).map((name) => {
                          const totalQty = g.stores.reduce((sum, st) => sum + (st.products.find((p) => p.name === name)?.quantity || 0), 0);
                          const totalSub = g.stores.reduce((sum, st) => sum + (st.products.find((p) => p.name === name)?.subtotal || 0), 0);
                          return (
                            <span key={name} className="inline-flex items-center gap-2 px-3 py-1 bg-dark-900/30 border border-dark-700/30 rounded-lg text-xs">
                              <span className="text-gray-200">{name}</span>
                              <span className="text-gray-500">x{totalQty}</span>
                              <span className="text-amber-400 font-medium">{formatBs(totalSub)}</span>
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "inventario" && (
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-700/50 flex items-center justify-between">
            <h3 className="text-white font-medium">Reporte de Inventario</h3>
            <div className="flex items-center gap-2">
              <button onClick={fetchInventory} className="p-1.5 text-gray-400 hover:text-white rounded-lg transition-all"><RefreshCw size={14} /></button>
              <button onClick={() => exportCSV(filteredInventory.map((i) => ({
                Codigo: i.product.itemCode, Producto: i.product.name, Marca: i.product.brand, Modelo: i.product.model,
                Ubicacion: i.location.name, Stock: i.stock, Minimo: i.minStock, Estado: i.status,
              })), "reporte_inventario")}
                className="flex items-center gap-1 px-3 py-1.5 bg-green-600/20 text-green-400 hover:bg-green-600/30 rounded-lg text-xs transition-all border border-green-600/30">
                <Download size={14} /> Exportar
              </button>
            </div>
          </div>
          {inventoryLoading ? (
            <div className="flex items-center justify-center h-32"><RefreshCw size={24} className="text-primary-400 animate-spin" /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-dark-700/50">
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Código</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Producto</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Marca</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Ubicación</th>
                    <th className="text-center px-4 py-3 text-gray-400 font-medium">Stock</th>
                    <th className="text-center px-4 py-3 text-gray-400 font-medium">Mínimo</th>
                    <th className="text-center px-4 py-3 text-gray-400 font-medium">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredInventory.length === 0 ? (
                    <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">No hay datos para los filtros seleccionados</td></tr>
                  ) : filteredInventory.map((i) => (
                    <tr key={i.id} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                      <td className="px-4 py-3 text-gray-300 font-mono text-xs">{i.product.itemCode}</td>
                      <td className="px-4 py-3 text-white font-medium">{i.product.name}</td>
                      <td className="px-4 py-3 text-gray-300">{i.product.brand}</td>
                      <td className="px-4 py-3 text-gray-300">{i.location.name}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          i.stock === 0 ? "bg-red-500/20 text-red-400" :
                          i.stock <= i.minStock ? "bg-yellow-500/20 text-yellow-400" :
                          "bg-green-500/20 text-green-400"
                        }`}>{i.stock}</span>
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-center text-xs">{i.minStock}</td>
                      <td className="px-4 py-3 text-center">
                        {i.status === "AGOTADO" ? (
                          <span className="text-red-400 text-xs font-medium">SIN STOCK</span>
                        ) : i.status === "BAJO" ? (
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
          )}
        </div>
      )}

      {activeTab === "mensual" && (
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-700/50 flex items-center justify-between">
            <h3 className="text-white font-medium">Reporte Mensual por Tienda</h3>
            <div className="flex items-center gap-2">
              <button onClick={fetchMonthly} className="p-1.5 text-gray-400 hover:text-white rounded-lg transition-all"><RefreshCw size={14} /></button>
              <button onClick={() => exportCSV(filteredMonthly.map((m) => ({
                Tienda: m.location.name, Ventas: m.summary.totalSales, Devoluciones: m.summary.totalReturns,
                Netas: m.summary.netSales, "N° Ventas": m.summary.saleCount, Promedio: m.summary.averagePerSale,
              })), "reporte_mensual")}
                className="flex items-center gap-1 px-3 py-1.5 bg-green-600/20 text-green-400 hover:bg-green-600/30 rounded-lg text-xs transition-all border border-green-600/30">
                <Download size={14} /> Exportar
              </button>
            </div>
          </div>
          {monthlyLoading ? (
            <div className="flex items-center justify-center h-32"><RefreshCw size={24} className="text-primary-400 animate-spin" /></div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-dark-700/50">
                      <th className="text-left px-4 py-3 text-gray-400 font-medium">Tienda</th>
                      <th className="text-center px-4 py-3 text-gray-400 font-medium">N° Ventas</th>
                      <th className="text-right px-4 py-3 text-gray-400 font-medium">Total Ventas</th>
                      <th className="text-right px-4 py-3 text-gray-400 font-medium">Devoluciones</th>
                      <th className="text-right px-4 py-3 text-gray-400 font-medium">Neto</th>
                      <th className="text-right px-4 py-3 text-gray-400 font-medium">Promedio</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredMonthly.length === 0 ? (
                      <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No hay datos para los filtros seleccionados</td></tr>
                    ) : filteredMonthly.map((m, idx) => (
                      <tr key={idx} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                        <td className="px-4 py-3 text-white font-medium">{m.location.name}</td>
                        <td className="px-4 py-3 text-gray-300 text-center">{m.summary.saleCount}</td>
                        <td className="px-4 py-3 text-amber-400 font-medium text-right">{formatBs(m.summary.totalSales)}</td>
                        <td className="px-4 py-3 text-red-400 text-right">{formatBs(m.summary.totalReturns)}</td>
                        <td className="px-4 py-3 text-green-400 font-medium text-right">{formatBs(m.summary.netSales)}</td>
                        <td className="px-4 py-3 text-gray-300 text-right">{formatBs(m.summary.averagePerSale)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {filteredMonthly.length > 0 && filteredMonthly[0]?.topProducts?.length > 0 && (
                <div className="p-4 border-t border-dark-700/50">
                  <h4 className="text-white font-medium text-sm mb-3">Productos Más Vendidos</h4>
                  <div className="space-y-2">
                    {filteredMonthly[0].topProducts.slice(0, 5).map((tp, i) => (
                      <div key={i} className="flex items-center justify-between p-2 bg-dark-900/30 rounded-lg">
                        <div>
                          <span className="text-white text-sm">{tp.product.name}</span>
                          <span className="text-gray-500 text-xs ml-2">{tp.product.brand}</span>
                        </div>
                        <div className="text-right">
                          <span className="text-amber-400 text-sm font-medium">{formatBs(tp.totalRevenue)}</span>
                          <span className="text-gray-500 text-xs ml-2">{tp.quantitySold} uds</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
