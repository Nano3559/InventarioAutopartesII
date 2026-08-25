import { useState, useEffect, useCallback, useRef } from "react";
import {
  Plus, X, Upload, Search, Pencil, Trash2,
  ChevronLeft, ChevronRight, Building2, RefreshCw,
} from "lucide-react";
import toast from "react-hot-toast";
import api from "../services/api";

interface Supplier { id: number; name: string; nit: string; phone: string; costsCount?: number; }
interface Product { id: number; itemCode: string; name: string; brand: string; model: string; }
interface CostRecord {
  id: number; productId: number; productName: string; itemCode: string;
  brand: string; model: string; supplierId: number; supplierName: string;
  invoiceUrl: string | null; exchangeRate: number | null; percentage: number | null;
  costPrice: number; date: string;
}

const PAGE_SIZE = 15;

export default function CostsPage() {
  const [costs, setCosts] = useState<CostRecord[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [supplierSearch, setSupplierSearch] = useState("");

  // Cost form
  const [showCostModal, setShowCostModal] = useState(false);
  const [editingCost, setEditingCost] = useState<number | null>(null);
  const [productSearch, setProductSearch] = useState("");
  const [productResults, setProductResults] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [costSupplierId, setCostSupplierId] = useState("");
  const [exchangeRate, setExchangeRate] = useState("6.96");
  const [percentage, setPercentage] = useState("");
  const [costPrice, setCostPrice] = useState("");
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Supplier form
  const [showSupplierModal, setShowSupplierModal] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<number | null>(null);
  const [supplierForm, setSupplierForm] = useState({ name: "", nit: "", phone: "" });

  const formatBs = (v: number) =>
    `Bs. ${v.toLocaleString("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const fetchCosts = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("limit", String(PAGE_SIZE));
      if (search) params.set("search", search);
      const res = await api.get(`/costs?${params.toString()}`);
      setCosts(res.data.costs);
      setTotal(res.data.pagination.total);
      setPages(res.data.pagination.pages);
    } catch { toast.error("Error al cargar costos"); }
    finally { setLoading(false); }
  }, [page, search]);

  const fetchSuppliers = useCallback(async () => {
    try {
      const res = await api.get(`/suppliers?limit=100`);
      setSuppliers(res.data.suppliers);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchCosts(); }, [fetchCosts]);
  useEffect(() => { fetchSuppliers(); }, [fetchSuppliers]);
  useEffect(() => { setPage(1); }, [search]);

  // Product search
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

  // ========== COST CRUD ==========
  const openCreateCost = () => {
    setEditingCost(null);
    setSelectedProduct(null); setProductSearch(""); setCostSupplierId("");
    setExchangeRate("6.96"); setPercentage(""); setCostPrice(""); setInvoiceFile(null);
    setShowCostModal(true);
  };

  const openEditCost = (c: CostRecord) => {
    setEditingCost(c.id);
    setSelectedProduct({ id: c.productId, itemCode: c.itemCode, name: c.productName, brand: c.brand, model: c.model });
    setProductSearch(c.productName);
    setCostSupplierId(String(c.supplierId));
    setExchangeRate(c.exchangeRate ? String(c.exchangeRate) : "6.96");
    setPercentage(c.percentage ? String(c.percentage) : "");
    setCostPrice(String(c.costPrice));
    setInvoiceFile(null);
    setShowCostModal(true);
  };

  const saveCost = async () => {
    if (!selectedProduct || !costSupplierId || !costPrice) {
      toast.error("Producto, proveedor y costo son obligatorios"); return;
    }
    try {
      setSaving(true);
      const formData = new FormData();
      formData.append("productId", String(selectedProduct.id));
      formData.append("supplierId", costSupplierId);
      formData.append("costPrice", costPrice);
      if (exchangeRate) formData.append("exchangeRate", exchangeRate);
      if (percentage) formData.append("percentage", percentage);
      if (invoiceFile) formData.append("invoice", invoiceFile);

      if (editingCost) {
        await api.put(`/costs/${editingCost}`, formData, { headers: { "Content-Type": "multipart/form-data" } });
        toast.success("Costo actualizado");
      } else {
        await api.post("/costs", formData, { headers: { "Content-Type": "multipart/form-data" } });
        toast.success("Costo registrado");
      }
      setShowCostModal(false);
      fetchCosts();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al guardar costo");
    } finally { setSaving(false); }
  };

  const deleteCost = async (id: number) => {
    try {
      await api.delete(`/costs/${id}`);
      toast.success("Costo eliminado");
      fetchCosts();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al eliminar");
    }
  };

  // ========== SUPPLIER CRUD ==========
  const openCreateSupplier = () => {
    setEditingSupplier(null);
    setSupplierForm({ name: "", nit: "", phone: "" });
    setShowSupplierModal(true);
  };

  const openEditSupplier = (s: Supplier) => {
    setEditingSupplier(s.id);
    setSupplierForm({ name: s.name, nit: s.nit || "", phone: s.phone || "" });
    setShowSupplierModal(true);
  };

  const saveSupplier = async () => {
    if (!supplierForm.name) { toast.error("El nombre es obligatorio"); return; }
    try {
      if (editingSupplier) {
        await api.put(`/suppliers/${editingSupplier}`, supplierForm);
        toast.success("Proveedor actualizado");
      } else {
        await api.post("/suppliers", supplierForm);
        toast.success("Proveedor creado");
      }
      setShowSupplierModal(false);
      fetchSuppliers();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al guardar proveedor");
    }
  };

  const deleteSupplier = async (id: number) => {
    try {
      await api.delete(`/suppliers/${id}`);
      toast.success("Proveedor eliminado");
      fetchSuppliers();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al eliminar proveedor");
    }
  };

  const filteredSuppliers = suppliers.filter((s) =>
    !supplierSearch || s.name.toLowerCase().includes(supplierSearch.toLowerCase()) ||
    (s.nit && s.nit.includes(supplierSearch)) ||
    (s.phone && s.phone.includes(supplierSearch))
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Costos</h1>
          <p className="text-gray-400 text-sm mt-1">Gestión de costos, facturas y proveedores</p>
        </div>
        <div className="flex gap-2">
          <button onClick={openCreateSupplier}
            className="flex items-center gap-2 px-4 py-2.5 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-xl text-sm transition-all border border-dark-600">
            <Building2 size={16} /> Proveedor
          </button>
          <button onClick={openCreateCost}
            className="flex items-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-primary-600/20">
            <Plus size={16} /> Nuevo Costo
          </button>
        </div>
      </div>

      <div className="relative">
        <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500" />
        <input value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por producto, código, marca o proveedor..."
          className="w-full pl-10 pr-4 py-2.5 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500 transition-all" />
      </div>

      {/* Costs table */}
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
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Fecha</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Código</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Producto</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Marca</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Proveedor</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Factura</th>
                    <th className="text-right px-4 py-3 text-gray-400 font-medium">T. Cambio</th>
                    <th className="text-right px-4 py-3 text-gray-400 font-medium">%</th>
                    <th className="text-right px-4 py-3 text-gray-400 font-medium">Costo</th>
                    <th className="text-center px-4 py-3 text-gray-400 font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {costs.length === 0 ? (
                    <tr><td colSpan={10} className="px-4 py-8 text-center text-gray-500">No hay costos registrados</td></tr>
                  ) : costs.map((c) => (
                    <tr key={c.id} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                      <td className="px-4 py-3 text-gray-300">{new Date(c.date).toLocaleDateString("es-BO")}</td>
                      <td className="px-4 py-3 text-gray-300 font-mono text-xs">{c.itemCode}</td>
                      <td className="px-4 py-3 text-white font-medium">{c.productName}</td>
                      <td className="px-4 py-3 text-gray-300">{c.brand}</td>
                      <td className="px-4 py-3 text-gray-300">{c.supplierName}</td>
                      <td className="px-4 py-3">
                        {c.invoiceUrl ? (
                          <span className="text-green-400 text-xs flex items-center gap-1"><Upload size={12} /> {c.invoiceUrl}</span>
                        ) : (
                          <span className="text-gray-600 text-xs">Sin archivo</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-300 text-right">{c.exchangeRate || "—"}</td>
                      <td className="px-4 py-3 text-gray-300 text-right">{c.percentage ? `${c.percentage}%` : "—"}</td>
                      <td className="px-4 py-3 text-amber-400 font-medium text-right">{formatBs(c.costPrice)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          <button onClick={() => openEditCost(c)} className="p-1.5 text-gray-400 hover:text-primary-400 hover:bg-primary-500/10 rounded-lg transition-all" title="Editar">
                            <Pencil size={14} />
                          </button>
                          <button onClick={() => deleteCost(c.id)} className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all" title="Eliminar">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {pages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-dark-700/50">
                <span className="text-xs text-gray-500">{total} registros</span>
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

      {/* Suppliers */}
      <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
        <div className="px-4 py-3 border-b border-dark-700/50">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-white font-medium">Proveedores ({filteredSuppliers.length})</h3>
            <button onClick={openCreateSupplier} className="text-xs text-primary-400 hover:text-primary-300 flex items-center gap-1 transition-all">
              <Plus size={14} /> Agregar
            </button>
          </div>
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input value={supplierSearch} onChange={(e) => setSupplierSearch(e.target.value)}
              placeholder="Buscar por nombre, NIT o teléfono..."
              className="w-full pl-9 pr-3 py-2 bg-dark-900/50 border border-dark-700/50 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500 transition-all" />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-700/50">
                <th className="text-left px-4 py-3 text-gray-400 font-medium">Nombre</th>
                <th className="text-left px-4 py-3 text-gray-400 font-medium">NIT</th>
                <th className="text-left px-4 py-3 text-gray-400 font-medium">Teléfono</th>
                <th className="text-center px-4 py-3 text-gray-400 font-medium">Costos</th>
                <th className="text-center px-4 py-3 text-gray-400 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredSuppliers.map((s) => (
                <tr key={s.id} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{s.name}</td>
                  <td className="px-4 py-3 text-gray-300 font-mono text-xs">{s.nit || "—"}</td>
                  <td className="px-4 py-3 text-gray-300">{s.phone || "—"}</td>
                  <td className="px-4 py-3 text-gray-400 text-center text-xs">{s.costsCount || 0}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-1">
                      <button onClick={() => openEditSupplier(s)} className="p-1.5 text-gray-400 hover:text-primary-400 hover:bg-primary-500/10 rounded-lg transition-all" title="Editar">
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => deleteSupplier(s.id)} className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all" title="Eliminar">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cost Modal */}
      {showCostModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-900 border border-dark-700/50 rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700/50">
              <h3 className="text-lg font-bold text-white">{editingCost ? "Editar Costo" : "Nuevo Costo"}</h3>
              <button onClick={() => setShowCostModal(false)} className="p-1.5 text-gray-400 hover:text-white hover:bg-dark-700 rounded-lg transition-all">
                <X size={18} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              {/* Product search */}
              <div className="relative">
                <label className="block text-xs text-gray-400 mb-1">Producto *</label>
                {selectedProduct ? (
                  <div className="flex items-center justify-between p-3 bg-dark-800 border border-primary-600/20 rounded-xl">
                    <div>
                      <p className="text-sm text-white font-medium">{selectedProduct.name}</p>
                      <p className="text-xs text-gray-500">{selectedProduct.brand} · {selectedProduct.itemCode}</p>
                    </div>
                    <button onClick={() => { setSelectedProduct(null); setProductSearch(""); }} className="p-1 text-gray-400 hover:text-red-400">
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <>
                    <Search size={16} className="absolute left-3 top-[34px] text-gray-500" />
                    <input value={productSearch} onChange={(e) => handleProductSearch(e.target.value)} placeholder="Buscar producto..."
                      className="w-full pl-9 pr-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
                    {productResults.length > 0 && (
                      <div className="absolute top-full left-0 right-0 mt-1 bg-dark-800 border border-dark-700 rounded-xl shadow-xl z-10 max-h-48 overflow-y-auto">
                        {productResults.map((p) => (
                          <button key={p.id} onClick={() => { setSelectedProduct(p); setProductSearch(p.name); setProductResults([]); }}
                            className="w-full text-left px-4 py-2.5 hover:bg-dark-700 transition-colors border-b border-dark-700/30 last:border-0">
                            <p className="text-sm text-white">{p.name}</p>
                            <p className="text-xs text-gray-500">{p.brand} · {p.itemCode}</p>
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Proveedor *</label>
                <select value={costSupplierId} onChange={(e) => setCostSupplierId(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500">
                  <option value="">Seleccionar...</option>
                  {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Tipo Cambio</label>
                  <input type="number" step="0.01" value={exchangeRate} onChange={(e) => setExchangeRate(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Porcentaje (%)</label>
                  <input type="number" value={percentage} onChange={(e) => setPercentage(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Costo (Bs.) *</label>
                  <input type="number" step="0.01" value={costPrice} onChange={(e) => setCostPrice(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
                </div>
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Factura (archivo)</label>
                <label className="flex items-center gap-2 px-4 py-2 bg-dark-800 border border-dark-700 rounded-xl text-gray-400 text-sm cursor-pointer hover:border-primary-500 transition-all">
                  <Upload size={16} />
                  <span>{invoiceFile ? invoiceFile.name : "Subir factura"}</span>
                  <input type="file" className="hidden" accept=".pdf,.jpg,.png" onChange={(e) => setInvoiceFile(e.target.files?.[0] || null)} />
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-dark-700/50">
              <button onClick={() => setShowCostModal(false)}
                className="px-4 py-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-xl text-sm transition-all">
                Cancelar
              </button>
              <button onClick={saveCost} disabled={saving}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-primary-600/20 disabled:opacity-50">
                {saving ? "Guardando..." : editingCost ? "Guardar Cambios" : "Registrar Costo"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Supplier Modal */}
      {showSupplierModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-900 border border-dark-700/50 rounded-2xl w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700/50">
              <h3 className="text-lg font-bold text-white">{editingSupplier ? "Editar Proveedor" : "Nuevo Proveedor"}</h3>
              <button onClick={() => setShowSupplierModal(false)} className="p-1.5 text-gray-400 hover:text-white hover:bg-dark-700 rounded-lg transition-all">
                <X size={18} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Nombre *</label>
                <input value={supplierForm.name} onChange={(e) => setSupplierForm({ ...supplierForm, name: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">NIT</label>
                <input value={supplierForm.nit} onChange={(e) => setSupplierForm({ ...supplierForm, nit: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Teléfono</label>
                <input value={supplierForm.phone} onChange={(e) => setSupplierForm({ ...supplierForm, phone: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
              </div>
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-dark-700/50">
              <button onClick={() => setShowSupplierModal(false)}
                className="px-4 py-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-xl text-sm transition-all">
                Cancelar
              </button>
              <button onClick={saveSupplier}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-primary-600/20">
                {editingSupplier ? "Guardar Cambios" : "Crear Proveedor"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
