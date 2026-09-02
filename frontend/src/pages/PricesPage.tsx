import { useState, useEffect, useCallback } from "react";
import {
  Search, Pencil, Download, ChevronLeft, ChevronRight, X, Check, RefreshCw,
} from "lucide-react";
import toast from "react-hot-toast";
import api from "../services/api";
import * as XLSX from "xlsx";

interface PriceRow {
  id: number; itemCode: string; productName: string; brand: string;
  model: string; years: string; detail: string;
  cost: number; p20: number; p30: number; p40: number;
  p50: number; p60: number; p70: number; p80: number;
  wholesalePrice: number;
}

const PAGE_SIZE = 15;

export default function PricesPage() {
  const [prices, setPrices] = useState<PriceRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");

  const formatBs = (v: number) =>
    `Bs. ${v.toLocaleString("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const fetchPrices = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("limit", String(PAGE_SIZE));
      if (search) params.set("search", search);
      const res = await api.get(`/prices?${params.toString()}`);
      setPrices(res.data.prices);
      setTotal(res.data.pagination.total);
      setPages(res.data.pagination.pages);
    } catch { toast.error("Error al cargar precios"); }
    finally { setLoading(false); }
  }, [page, search]);

  useEffect(() => { fetchPrices(); }, [fetchPrices]);
  useEffect(() => { setPage(1); }, [search]);

  const startEdit = (p: PriceRow) => {
    setEditingId(p.id);
    setEditValue(String(p.wholesalePrice));
  };

  const saveEdit = async (id: number) => {
    const val = Number(editValue);
    if (isNaN(val) || val < 0) { toast.error("Precio inválido"); return; }
    try {
      await api.put(`/prices/${id}`, { wholesalePrice: val });
      setPrices((prev) => prev.map((p) => p.id === id ? { ...p, wholesalePrice: val } : p));
      setEditingId(null);
      toast.success("Precio por mayor actualizado");
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al actualizar");
    }
  };

  const exportExcel = async () => {
    try {
      const [pricesRes, productsRes, costsRes] = await Promise.all([
        api.get("/prices/export"),
        api.get("/products?limit=1000"),
        api.get("/costs?limit=100"),
      ]);
      const stockByCode = new Map((productsRes.data.products || []).map((p: any) => [p.itemCode, p.stock]));
      const supplierByCode = new Map((costsRes.data.costs || []).map((c: any) => [c.itemCode, c.supplierName]));
      const data = pricesRes.data.data.map((row: any) => ({ ...row, stock: stockByCode.get(row.itemCode) ?? 0, supplier: supplierByCode.get(row.itemCode) || "" }));
      if (!data.length) { toast.error("No hay datos para exportar"); return; }
      const rows = data.map((r: any) => ({ "Código Fábrica": r.itemCode, Producto: r.name, Marca: r.brand, Modelo: r.model, Años: r.years, Detalle: r.detail, Proveedor: r.supplier, Stock: r.stock, "Precio Mayor": r.wholesalePrice }));
      const sheet = XLSX.utils.json_to_sheet(rows);
      const book = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(book, sheet, "Precios");
      XLSX.writeFile(book, "precios_mayor.xlsx");
      toast.success("Precios exportados");
    } catch { toast.error("Error al exportar"); }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Precios</h1>
          <p className="text-gray-400 text-sm mt-1">Cálculo de precios por porcentaje desde costo</p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchPrices}
            className="flex items-center gap-2 px-4 py-2.5 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-xl text-sm transition-all border border-dark-600">
            <RefreshCw size={16} />
          </button>
          <button onClick={exportExcel}
            className="flex items-center gap-2 px-4 py-2.5 bg-green-600 hover:bg-green-500 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-green-600/20">
            <Download size={16} /> Exportar Excel
          </button>
        </div>
      </div>

      <div className="relative">
        <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500" />
        <input value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por producto, código, marca o modelo..."
          className="w-full pl-10 pr-4 py-2.5 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500 transition-all" />
      </div>

      <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <RefreshCw size={24} className="text-primary-400 animate-spin" />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-dark-700/50">
                    <th className="text-left px-3 py-3 text-gray-400 font-medium">Código</th>
                    <th className="text-left px-3 py-3 text-gray-400 font-medium">Producto</th>
                    <th className="text-left px-3 py-3 text-gray-400 font-medium">Marca</th>
                    <th className="text-left px-3 py-3 text-gray-400 font-medium">Modelo</th>
                    <th className="text-right px-3 py-3 text-gray-400 font-medium">Costo</th>
                    <th className="text-right px-3 py-3 text-amber-400/70 font-medium">+20%</th>
                    <th className="text-right px-3 py-3 text-amber-400/70 font-medium">+30%</th>
                    <th className="text-right px-3 py-3 text-amber-400/70 font-medium">+40%</th>
                    <th className="text-right px-3 py-3 text-amber-400/70 font-medium">+50%</th>
                    <th className="text-right px-3 py-3 text-amber-400/70 font-medium">+60%</th>
                    <th className="text-right px-3 py-3 text-amber-400/70 font-medium">+70%</th>
                    <th className="text-right px-3 py-3 text-amber-400/70 font-medium">+80%</th>
                    <th className="text-right px-3 py-3 text-primary-400 font-medium">P. Mayor</th>
                    <th className="text-center px-3 py-3 text-gray-400 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {prices.length === 0 ? (
                    <tr><td colSpan={14} className="px-3 py-8 text-center text-gray-500">No hay productos con costo registrado</td></tr>
                  ) : prices.map((p) => (
                    <tr key={p.id} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                      <td className="px-3 py-3 text-gray-300 font-mono text-xs">{p.itemCode}</td>
                      <td className="px-3 py-3 text-white font-medium">{p.productName}</td>
                      <td className="px-3 py-3 text-gray-300">{p.brand}</td>
                      <td className="px-3 py-3 text-gray-300">{p.model}</td>
                      <td className="px-3 py-3 text-amber-400 font-medium text-right">{formatBs(p.cost)}</td>
                      <td className="px-3 py-3 text-gray-300 text-right text-xs">{formatBs(p.p20)}</td>
                      <td className="px-3 py-3 text-gray-300 text-right text-xs">{formatBs(p.p30)}</td>
                      <td className="px-3 py-3 text-gray-300 text-right text-xs">{formatBs(p.p40)}</td>
                      <td className="px-3 py-3 text-gray-300 text-right text-xs">{formatBs(p.p50)}</td>
                      <td className="px-3 py-3 text-gray-300 text-right text-xs">{formatBs(p.p60)}</td>
                      <td className="px-3 py-3 text-gray-300 text-right text-xs">{formatBs(p.p70)}</td>
                      <td className="px-3 py-3 text-gray-300 text-right text-xs">{formatBs(p.p80)}</td>
                      <td className="px-3 py-3 text-right">
                        {editingId === p.id ? (
                          <div className="flex items-center gap-1 justify-end">
                            <input type="number" value={editValue} onChange={(e) => setEditValue(e.target.value)}
                              onKeyDown={(e) => e.key === "Enter" && saveEdit(p.id)}
                              className="w-24 px-2 py-1 bg-dark-800 border border-primary-500 rounded-lg text-white text-xs text-right focus:outline-none" autoFocus />
                            <button onClick={() => saveEdit(p.id)} className="p-1 text-green-400 hover:text-green-300"><Check size={12} /></button>
                            <button onClick={() => setEditingId(null)} className="p-1 text-gray-400 hover:text-white"><X size={12} /></button>
                          </div>
                        ) : (
                          <span className="text-primary-400 font-bold cursor-pointer hover:text-primary-300" onClick={() => startEdit(p)}>
                            {formatBs(p.wholesalePrice)}
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        <button onClick={() => startEdit(p)} className="p-1.5 text-gray-400 hover:text-primary-400 hover:bg-primary-500/10 rounded-lg transition-all" title="Editar precio mayor">
                          <Pencil size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {pages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-dark-700/50">
                <span className="text-xs text-gray-500">{total} productos</span>
                <div className="flex items-center gap-2">
                  <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1}
                    className="p-1.5 text-gray-400 hover:text-white disabled:opacity-30 rounded-lg transition-all">
                    <ChevronLeft size={16} />
                  </button>
                  <span className="text-xs text-gray-400">{page}/{pages}</span>
                  <button onClick={() => setPage(Math.min(pages, page + 1))} disabled={page === pages}
                    className="p-1.5 text-gray-400 hover:text-white disabled:opacity-30 rounded-lg transition-all">
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
