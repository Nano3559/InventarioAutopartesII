import { useState, useEffect, useCallback, useRef } from "react";
import {
  Send, Plus, X, RefreshCw, ChevronDown, ChevronLeft, ChevronRight,
  Search, Clock, Package, Truck, CheckCircle, Ban,
} from "lucide-react";
import toast from "react-hot-toast";
import api from "../services/api";
import { useAuthStore } from "../stores/authStore";

interface Product {
  id: number; itemCode: string; name: string; brand: string; model: string;
  stock: number; category: string | null; image: string | null;
}

interface RequestRecord {
  id: number; productId: number; quantity: number; locationId: number;
  status: string; date: string;
  product: { id: number; name: string; itemCode: string; brand: string; model: string };
  location: { id: number; name: string; type: string };
  requestedBy: { id: number; name: string; email: string };
}

interface Location {
  id: number; name: string; type: string;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof Clock }> = {
  PENDIENTE: { label: "Pendiente", color: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20", icon: Clock },
  EN_PREPARACION: { label: "En Preparación", color: "text-blue-400 bg-blue-500/10 border-blue-500/20", icon: Package },
  ENVIADO: { label: "Enviado", color: "text-purple-400 bg-purple-500/10 border-purple-500/20", icon: Truck },
  RECIBIDO: { label: "Recibido", color: "text-green-400 bg-green-500/10 border-green-500/20", icon: CheckCircle },
  CANCELADO: { label: "Cancelado", color: "text-red-400 bg-red-500/10 border-red-500/20", icon: Ban },
};

const STATUS_FLOW: Record<string, string[]> = {
  PENDIENTE: ["EN_PREPARACION", "CANCELADO"],
  EN_PREPARACION: ["ENVIADO", "CANCELADO"],
  ENVIADO: ["RECIBIDO"],
};

const PAGE_SIZE = 15;

export default function RequestsPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === "ADMIN";

  const [requests, setRequests] = useState<RequestRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [filterStatus, setFilterStatus] = useState("");

  const [showNew, setShowNew] = useState(false);
  const [searchProd, setSearchProd] = useState("");
  const [searchResults, setSearchResults] = useState<Product[]>([]);
  const [, setSearching] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [selectedLocation, setSelectedLocation] = useState("");
  const [quantity, setQuantity] = useState("");
  const [locations, setLocations] = useState<Location[]>([]);
  const [saving, setSaving] = useState(false);

  const fetchRequests = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterStatus) params.set("status", filterStatus);
      params.set("page", String(page));
      params.set("limit", String(PAGE_SIZE));
      const res = await api.get(`/requests?${params.toString()}`);
      setRequests(res.data.requests);
      setTotal(res.data.pagination.total);
      setPages(res.data.pagination.pages);
    } catch {
      toast.error("Error al cargar solicitudes");
    } finally {
      setLoading(false);
    }
  }, [filterStatus, page]);

  const fetchLocations = useCallback(async () => {
    try {
      const res = await api.get("/locations");
      setLocations(res.data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchRequests(); }, [fetchRequests]);
  useEffect(() => { fetchLocations(); }, [fetchLocations]);
  useEffect(() => { setPage(1); }, [filterStatus]);

  const doSearch = (q: string) => {
    setSearchProd(q);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!q || q.trim().length < 2) { setSearchResults([]); return; }
    searchTimer.current = setTimeout(async () => {
      try {
        setSearching(true);
        const res = await api.get(`/products?search=${encodeURIComponent(q.trim())}&limit=8`);
        setSearchResults(res.data.products);
      } catch { /* ignore */ }
      finally { setSearching(false); }
    }, 300);
  };

  const handleCreate = async () => {
    if (!selectedProduct || !selectedLocation || !quantity || !user) {
      toast.error("Completa todos los campos");
      return;
    }
    const qty = Number(quantity);
    if (qty <= 0) { toast.error("La cantidad debe ser mayor a 0"); return; }

    try {
      setSaving(true);
      await api.post("/requests", {
        productId: selectedProduct.id,
        quantity: qty,
        locationId: Number(selectedLocation),
        requestedById: user.id,
      });
      toast.success("Solicitud creada");
      setShowNew(false);
      setSelectedProduct(null);
      setSearchProd(""); setSearchResults([]);
      setSelectedLocation(""); setQuantity("");
      fetchRequests();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al crear solicitud");
    } finally {
      setSaving(false);
    }
  };

  const changeStatus = async (id: number, newStatus: string) => {
    try {
      await api.put(`/requests/${id}`, { status: newStatus });
      toast.success(`Estado cambiado a ${STATUS_CONFIG[newStatus]?.label || newStatus}`);
      fetchRequests();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al cambiar estado");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Solicitudes</h1>
          <p className="text-gray-400 text-sm mt-1">{total} solicitudes</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchRequests} className="p-2.5 bg-dark-800 border border-dark-700/50 rounded-xl text-gray-400 hover:text-white hover:border-primary-600/50 transition-all" title="Actualizar">
            <RefreshCw size={18} />
          </button>
          <button onClick={() => setShowNew(true)} className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2 shadow-lg shadow-primary-600/20">
            <Plus size={18} /> Nueva Solicitud
          </button>
        </div>
      </div>

      {/* Filtros de estado */}
      <div className="flex flex-wrap gap-2">
        <button onClick={() => setFilterStatus("")} className={`px-3 py-2 rounded-xl text-sm border transition-all ${!filterStatus ? "bg-primary-600/10 border-primary-600/20 text-primary-400" : "bg-dark-800/50 border-dark-700/50 text-gray-400 hover:text-white"}`}>
          Todas
        </button>
        {Object.entries(STATUS_CONFIG).map(([key, cfg]) => {
          const Icon = cfg.icon;
          return (
            <button key={key} onClick={() => setFilterStatus(key)}
              className={`px-3 py-2 rounded-xl text-sm border transition-all flex items-center gap-1.5 ${filterStatus === key ? cfg.color : "bg-dark-800/50 border-dark-700/50 text-gray-400 hover:text-white"}`}>
              <Icon size={14} /> {cfg.label}
            </button>
          );
        })}
      </div>

      {/* Tabla */}
      <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <RefreshCw size={24} className="text-primary-400 animate-spin" />
          </div>
        ) : requests.length === 0 ? (
          <div className="p-6 text-center">
            <Send size={40} className="text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400 text-sm">Sin solicitudes{filterStatus ? ` con estado "${STATUS_CONFIG[filterStatus]?.label}"` : ""}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 border-b border-dark-700/50">
                  <th className="text-left px-4 py-3 font-medium">ID</th>
                  <th className="text-left px-4 py-3 font-medium">Fecha</th>
                  <th className="text-left px-4 py-3 font-medium">Producto</th>
                  <th className="text-left px-4 py-3 font-medium">Ubicación</th>
                  <th className="text-center px-4 py-3 font-medium">Cantidad</th>
                  <th className="text-left px-4 py-3 font-medium">Solicitado por</th>
                  <th className="text-left px-4 py-3 font-medium">Estado</th>
                  <th className="text-center px-4 py-3 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((r) => {
                  const cfg = STATUS_CONFIG[r.status] || STATUS_CONFIG.PENDIENTE;
                  const Icon = cfg.icon;
                  const nextStatuses = STATUS_FLOW[r.status] || [];
                  return (
                    <tr key={r.id} className="border-b border-dark-700/30 last:border-0 hover:bg-dark-900/30 transition-colors">
                      <td className="px-4 py-3 text-gray-400">{r.id}</td>
                      <td className="px-4 py-3 text-gray-300">{new Date(r.date).toLocaleDateString("es-BO")}</td>
                      <td className="px-4 py-3">
                        <p className="text-white font-medium">{r.product.name}</p>
                        <p className="text-xs text-gray-500">{r.product.itemCode}</p>
                      </td>
                      <td className="px-4 py-3 text-gray-300">{r.location.name}</td>
                      <td className="px-4 py-3 text-center text-white font-medium">{r.quantity}</td>
                      <td className="px-4 py-3 text-gray-400">{r.requestedBy.name}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2.5 py-1 text-xs font-medium rounded-full border inline-flex items-center gap-1 ${cfg.color}`}>
                          <Icon size={12} /> {cfg.label}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          {isAdmin && nextStatuses.map((ns) => {
                            const nCfg = STATUS_CONFIG[ns];
                            return (
                              <button key={ns} onClick={() => changeStatus(r.id, ns)}
                                title={`Cambiar a ${nCfg.label}`}
                                className={`px-2 py-1 text-xs rounded-lg border transition-all ${nCfg.color} hover:opacity-80`}>
                                {nCfg.label}
                              </button>
                            );
                          })}
                          {r.status === "PENDIENTE" && (
                            <button onClick={() => changeStatus(r.id, "CANCELADO")} title="Cancelar"
                              className="px-2 py-1 text-xs rounded-lg border text-red-400 bg-red-500/10 border-red-500/20 hover:opacity-80">
                              Cancelar
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

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
                const p = start + i;
                if (p > pages) return null;
                return (
                  <button key={p} onClick={() => setPage(p)}
                    className={`w-8 h-8 rounded-lg text-sm font-medium transition-all ${p === page ? "bg-primary-600 text-white" : "bg-dark-900/50 border border-dark-600/50 text-gray-400 hover:text-white"}`}>
                    {p}
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
      </div>

      {/* Modal: Nueva Solicitud */}
      {showNew && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-dark-800 border border-dark-700/50 rounded-2xl w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b border-dark-700/50">
              <h2 className="text-lg font-bold text-white">Nueva Solicitud</h2>
              <button onClick={() => { setShowNew(false); setSelectedProduct(null); setSearchProd(""); setSearchResults([]); }}
                className="p-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-xl transition-all">
                <X size={18} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              {/* Buscar producto */}
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Producto *</label>
                <div className="relative">
                  <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                  <input type="text" value={searchProd} onChange={(e) => doSearch(e.target.value)}
                    placeholder="Buscar por código, nombre, marca..."
                    className="w-full pl-9 pr-4 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none placeholder-gray-500" />
                </div>
                {searchResults.length > 0 && !selectedProduct && (
                  <div className="mt-2 bg-dark-900 border border-dark-700/50 rounded-xl max-h-48 overflow-y-auto">
                    {searchResults.map((p) => (
                      <button key={p.id} onClick={() => { setSelectedProduct(p); setSearchProd(p.name); setSearchResults([]); }}
                        className="w-full text-left px-3 py-2.5 hover:bg-dark-800 transition-colors border-b border-dark-700/30 last:border-0">
                        <p className="text-sm text-white">{p.name}</p>
                        <p className="text-xs text-gray-500">{p.itemCode} · {p.brand} · Stock: {p.stock}</p>
                      </button>
                    ))}
                  </div>
                )}
                {selectedProduct && (
                  <div className="mt-2 p-3 bg-primary-600/10 border border-primary-600/20 rounded-xl">
                    <p className="text-sm text-white">{selectedProduct.name}</p>
                    <p className="text-xs text-gray-400">{selectedProduct.itemCode} · {selectedProduct.brand}</p>
                    <button onClick={() => { setSelectedProduct(null); setSearchProd(""); }} className="text-xs text-primary-400 hover:text-primary-300 mt-1">Cambiar</button>
                  </div>
                )}
              </div>

              {/* Ubicación */}
              <div className="relative">
                <label className="block text-xs text-gray-400 mb-1.5">Ubicación solicitante *</label>
                <select value={selectedLocation} onChange={(e) => setSelectedLocation(e.target.value)}
                  className="w-full appearance-none px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none pr-8">
                  <option value="">Seleccionar ubicación</option>
                  {locations.filter((l) => l.type === "TIENDA").map((l) => (
                    <option key={l.id} value={l.id}>{l.name}</option>
                  ))}
                </select>
                <ChevronDown size={14} className="absolute right-2.5 top-[38px] text-gray-500 pointer-events-none" />
              </div>

              {/* Cantidad */}
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Cantidad *</label>
                <input type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} min="1"
                  className="w-full px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none" />
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-5 border-t border-dark-700/50">
              <button onClick={() => { setShowNew(false); setSelectedProduct(null); }} className="px-4 py-2.5 text-sm text-gray-400 hover:text-white transition-colors">Cancelar</button>
              <button onClick={handleCreate} disabled={saving}
                className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-all disabled:opacity-50">
                {saving ? "Creando..." : "Crear Solicitud"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
