import { useState, useEffect, useCallback, useRef } from "react";
import {
  ArrowLeftRight, Search, Plus, X, ChevronDown, ChevronLeft, ChevronRight,
  RefreshCw, MapPin, Calendar,
} from "lucide-react";
import toast from "react-hot-toast";
import api from "../services/api";

interface Product {
  id: number; itemCode: string; name: string; brand: string; model: string; stock: number;
}

interface Location {
  id: number; name: string; type: "ALMACEN" | "TIENDA"; address?: string;
}

interface Movement {
  id: number; quantity: number; date: string; observation: string | null;
  product: { id: number; name: string; itemCode: string; brand: string };
  fromLocation: { id: number; name: string; type: string };
  toLocation: { id: number; name: string; type: string };
  user: { id: number; name: string };
}

export default function MovementsPage() {
  const [locations, setLocations] = useState<Location[]>([]);
  const [showForm, setShowForm] = useState(false);

  // Form state
  const [productSearch, setProductSearch] = useState("");
  const [productResults, setProductResults] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [fromLocationId, setFromLocationId] = useState("");
  const [toLocationId, setToLocationId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [observation, setObservation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // History state
  const [movements, setMovements] = useState<Movement[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);

  const [filterFrom, setFilterFrom] = useState("");
  const [filterTo, setFilterTo] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const fetchLocations = useCallback(async () => {
    try {
      const res = await api.get("/locations");
      setLocations(res.data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchLocations(); }, [fetchLocations]);

  // ==================== PRODUCT SEARCH ====================
  const searchProducts = useCallback(async (q: string) => {
    if (!q || q.length < 2) { setProductResults([]); return; }
    try {
      const res = await api.get(`/products?search=${encodeURIComponent(q)}&limit=8`);
      setProductResults(res.data.products);
    } catch { toast.error("Error al buscar productos"); }
  }, []);

  const handleProductSearch = (v: string) => {
    setProductSearch(v);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => searchProducts(v), 300);
  };

  const selectProduct = (p: Product) => {
    setSelectedProduct(p);
    setProductSearch(p.name);
    setProductResults([]);
  };

  // ==================== FETCH HISTORY ====================
  const fetchMovements = useCallback(async () => {
    try {
      setHistoryLoading(true);
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("limit", "15");
      if (filterFrom) params.set("fromLocationId", filterFrom);
      if (filterTo) params.set("toLocationId", filterTo);
      if (filterDateFrom) params.set("startDate", filterDateFrom);
      if (filterDateTo) params.set("endDate", filterDateTo);

      const res = await api.get(`/movements?${params.toString()}`);
      setMovements(res.data.movements);
      setTotal(res.data.pagination.total);
      setPages(res.data.pagination.pages);
    } catch { toast.error("Error al cargar movimientos"); }
    finally { setHistoryLoading(false); }
  }, [page, filterFrom, filterTo, filterDateFrom, filterDateTo]);

  useEffect(() => { fetchMovements(); }, [fetchMovements]);
  useEffect(() => { setPage(1); }, [filterFrom, filterTo, filterDateFrom, filterDateTo]);

  // ==================== SUBMIT ====================
  const handleSubmit = async () => {
    if (!selectedProduct) { toast.error("Selecciona un producto"); return; }
    if (!fromLocationId) { toast.error("Selecciona la ubicación de origen"); return; }
    if (!toLocationId) { toast.error("Selecciona la ubicación de destino"); return; }
    if (fromLocationId === toLocationId) { toast.error("Origen y destino deben ser diferentes"); return; }
    if (!quantity || Number(quantity) <= 0) { toast.error("Ingresa una cantidad válida"); return; }

    try {
      setSubmitting(true);
      await api.post("/movements", {
        productId: selectedProduct.id,
        fromLocationId: Number(fromLocationId),
        toLocationId: Number(toLocationId),
        quantity: Number(quantity),
        observation: observation.trim() || null,
      });
      toast.success("Movimiento registrado exitosamente");
      setShowForm(false);
      resetForm();
      fetchMovements();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al registrar movimiento");
    } finally { setSubmitting(false); }
  };

  const resetForm = () => {
    setSelectedProduct(null);
    setProductSearch("");
    setFromLocationId("");
    setToLocationId("");
    setQuantity("");
    setObservation("");
  };

  const fromLocations = locations.filter((l) => l.id !== Number(toLocationId));
  const toLocations = locations.filter((l) => l.id !== Number(fromLocationId));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Movimientos</h1>
          <p className="text-gray-400 text-sm mt-1">{total} movimientos registrados</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchMovements}
            className="p-2.5 bg-dark-800 border border-dark-700/50 rounded-xl text-gray-400 hover:text-white hover:border-primary-600/50 transition-all" title="Actualizar">
            <RefreshCw size={18} />
          </button>
          <button onClick={() => { resetForm(); setShowForm(true); }}
            className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2 shadow-lg shadow-primary-600/20">
            <Plus size={18} /> Nuevo Movimiento
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl p-4">
        <button onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm border transition-all ${
            showFilters ? "bg-primary-600/10 border-primary-600/20 text-primary-400" : "bg-dark-900/50 border-dark-600/50 text-gray-400 hover:text-white"
          }`}>
          <Calendar size={16} /> Filtros
          <ChevronDown size={14} className={`transition-transform ${showFilters ? "rotate-180" : ""}`} />
        </button>

        {showFilters && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4 pt-4 border-t border-dark-700/50">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Desde fecha</label>
              <input type="date" value={filterDateFrom} onChange={(e) => setFilterDateFrom(e.target.value)}
                className="w-full px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Hasta fecha</label>
              <input type="date" value={filterDateTo} onChange={(e) => setFilterDateTo(e.target.value)}
                className="w-full px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none" />
            </div>
            <div className="relative">
              <label className="block text-xs text-gray-500 mb-1">Ubicación origen</label>
              <select value={filterFrom} onChange={(e) => setFilterFrom(e.target.value)}
                className="w-full appearance-none px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none pr-8">
                <option value="">Todas</option>
                {locations.map((l) => <option key={l.id} value={l.id}>{l.name} ({l.type})</option>)}
              </select>
              <ChevronDown size={14} className="absolute right-2.5 top-[34px] text-gray-500 pointer-events-none" />
            </div>
            <div className="relative">
              <label className="block text-xs text-gray-500 mb-1">Ubicación destino</label>
              <select value={filterTo} onChange={(e) => setFilterTo(e.target.value)}
                className="w-full appearance-none px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none pr-8">
                <option value="">Todas</option>
                {locations.map((l) => <option key={l.id} value={l.id}>{l.name} ({l.type})</option>)}
              </select>
              <ChevronDown size={14} className="absolute right-2.5 top-[34px] text-gray-500 pointer-events-none" />
            </div>
            {(filterDateFrom || filterDateTo || filterFrom || filterTo) && (
              <div className="flex items-end">
                <button onClick={() => { setFilterDateFrom(""); setFilterDateTo(""); setFilterFrom(""); setFilterTo(""); }}
                  className="px-3 py-2.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm hover:bg-red-500/20 transition-colors">
                  Limpiar
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* History Table */}
      <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
        {historyLoading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw size={32} className="text-primary-400 animate-spin" />
          </div>
        ) : movements.length === 0 ? (
          <div className="p-10 text-center">
            <ArrowLeftRight size={48} className="text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No hay movimientos registrados</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 border-b border-dark-700/50">
                    <th className="text-left px-4 py-3 font-medium">#</th>
                    <th className="text-left px-4 py-3 font-medium">Fecha</th>
                    <th className="text-left px-4 py-3 font-medium">Producto</th>
                    <th className="text-left px-4 py-3 font-medium">Origen</th>
                    <th className="text-center px-4 py-3 font-medium"></th>
                    <th className="text-left px-4 py-3 font-medium">Destino</th>
                    <th className="text-center px-4 py-3 font-medium">Cantidad</th>
                    <th className="text-left px-4 py-3 font-medium">Usuario</th>
                    <th className="text-left px-4 py-3 font-medium">Observación</th>
                  </tr>
                </thead>
                <tbody>
                  {movements.map((m) => (
                    <tr key={m.id} className="border-b border-dark-700/30 last:border-0 hover:bg-dark-900/30">
                      <td className="px-4 py-3 text-gray-400">{m.id}</td>
                      <td className="px-4 py-3 text-gray-300 text-xs">
                        {new Date(m.date).toLocaleDateString("es-BO")}{" "}
                        <span className="text-gray-500">
                          {new Date(m.date).toLocaleTimeString("es-BO", { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-white text-sm font-medium">{m.product.name}</p>
                        <p className="text-xs text-gray-500">{m.product.itemCode} · {m.product.brand}</p>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-1 text-xs text-gray-300">
                          <MapPin size={12} className="text-gray-500" />
                          {m.fromLocation.name}
                        </span>
                        <p className="text-xs text-gray-600 ml-4">{m.fromLocation.type}</p>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <ArrowLeftRight size={16} className="text-primary-400 mx-auto" />
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center gap-1 text-xs text-gray-300">
                          <MapPin size={12} className="text-gray-500" />
                          {m.toLocation.name}
                        </span>
                        <p className="text-xs text-gray-600 ml-4">{m.toLocation.type}</p>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="px-2.5 py-0.5 bg-primary-600/10 text-primary-400 font-medium rounded-full text-sm">
                          {m.quantity}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{m.user.name}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs max-w-[150px] truncate">
                        {m.observation || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {pages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-dark-700/50">
                <p className="text-gray-400 text-sm">Página {page} de {pages}</p>
                <div className="flex items-center gap-2">
                  <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
                    className="p-2 rounded-lg bg-dark-900/50 border border-dark-600/50 text-gray-400 hover:text-white disabled:opacity-30 transition-all">
                    <ChevronLeft size={16} />
                  </button>
                  {Array.from({ length: Math.min(5, pages) }, (_, i) => {
                    const start = Math.max(1, Math.min(page - 2, pages - 4));
                    const pg = start + i;
                    if (pg > pages) return null;
                    return (
                      <button key={pg} onClick={() => setPage(pg)}
                        className={`w-8 h-8 rounded-lg text-sm font-medium transition-all ${
                          pg === page ? "bg-primary-600 text-white" : "bg-dark-900/50 border border-dark-600/50 text-gray-400 hover:text-white"
                        }`}>
                        {pg}
                      </button>
                    );
                  })}
                  <button onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page === pages}
                    className="p-2 rounded-lg bg-dark-900/50 border border-dark-600/50 text-gray-400 hover:text-white disabled:opacity-30 transition-all">
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* ============ MODAL: Nuevo Movimiento ============ */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-dark-800 border border-dark-700/50 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-dark-700/50">
              <h2 className="text-lg font-bold text-white">Nuevo Movimiento</h2>
              <button onClick={() => setShowForm(false)}
                className="p-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-xl transition-all">
                <X size={18} />
              </button>
            </div>

            <div className="p-5 space-y-4">
              {/* Producto */}
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Producto *</label>
                {selectedProduct ? (
                  <div className="flex items-center justify-between p-3 bg-dark-900/50 border border-primary-600/20 rounded-xl">
                    <div>
                      <p className="text-sm text-white font-medium">{selectedProduct.name}</p>
                      <p className="text-xs text-gray-500">{selectedProduct.brand} · {selectedProduct.itemCode}</p>
                    </div>
                    <button onClick={() => { setSelectedProduct(null); setProductSearch(""); }}
                      className="p-1.5 text-gray-400 hover:text-red-400 transition-all">
                      <X size={16} />
                    </button>
                  </div>
                ) : (
                  <div className="relative">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                    <input ref={searchInputRef} type="text" value={productSearch}
                      onChange={(e) => handleProductSearch(e.target.value)}
                      placeholder="Buscar producto..."
                      className="w-full pl-9 pr-4 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none placeholder-gray-600" />
                    {productResults.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-dark-800 border border-dark-700/50 rounded-xl max-h-48 overflow-y-auto shadow-xl">
                        {productResults.map((p) => (
                          <button key={p.id} onClick={() => selectProduct(p)}
                            className="w-full text-left px-3 py-2.5 hover:bg-dark-700/50 transition-colors border-b border-dark-700/30 last:border-0">
                            <p className="text-sm text-white">{p.name}</p>
                            <p className="text-xs text-gray-500">{p.brand} · {p.itemCode} · Stock: {p.stock}</p>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Origen y Destino */}
              <div className="grid grid-cols-[1fr_auto_1fr] gap-2 items-end">
                <div className="relative">
                  <label className="block text-xs text-gray-400 mb-1.5">Origen *</label>
                  <select value={fromLocationId} onChange={(e) => setFromLocationId(e.target.value)}
                    className="w-full appearance-none px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none pr-8">
                    <option value="">Seleccionar</option>
                    {fromLocations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                  </select>
                  <ChevronDown size={14} className="absolute right-2.5 top-[38px] text-gray-500 pointer-events-none" />
                </div>
                <div className="pb-1">
                  <ArrowLeftRight size={20} className="text-primary-400" />
                </div>
                <div className="relative">
                  <label className="block text-xs text-gray-400 mb-1.5">Destino *</label>
                  <select value={toLocationId} onChange={(e) => setToLocationId(e.target.value)}
                    className="w-full appearance-none px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none pr-8">
                    <option value="">Seleccionar</option>
                    {toLocations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                  </select>
                  <ChevronDown size={14} className="absolute right-2.5 top-[38px] text-gray-500 pointer-events-none" />
                </div>
              </div>

              {/* Cantidad */}
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Cantidad *</label>
                <input type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)}
                  placeholder="Cantidad a mover" min="1"
                  className="w-full px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none placeholder-gray-600" />
              </div>

              {/* Observación */}
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Observación</label>
                <textarea value={observation} onChange={(e) => setObservation(e.target.value)}
                  placeholder="Motivo del movimiento (opcional)" rows={2}
                  className="w-full px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none placeholder-gray-600 resize-none" />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 p-5 border-t border-dark-700/50">
              <button onClick={() => setShowForm(false)}
                className="px-4 py-2.5 text-sm text-gray-400 hover:text-white transition-colors">
                Cancelar
              </button>
              <button onClick={handleSubmit} disabled={submitting}
                className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2 disabled:opacity-50">
                {submitting ? <><RefreshCw size={16} className="animate-spin" /> Registrando...</> : <><Plus size={16} /> Registrar Movimiento</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
