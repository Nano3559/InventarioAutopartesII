import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search, Plus, Filter, ChevronDown, Eye, Pencil, Trash2,
  Package, RefreshCw, X, ChevronLeft, ChevronRight, Upload, FileSpreadsheet,
} from "lucide-react";
import toast from "react-hot-toast";
import api from "../services/api";
import ProductImage from "../components/public/ProductImage";
import { validateYearRanges } from "../utils/yearRanges";
import Autocomplete from "../components/ui/Autocomplete";
import ColumnManager from "../components/ui/ColumnManager";
import { useAuthStore } from "../stores/authStore";

interface Product {
  id: number; itemCode: string; manufacturer: string; name: string;
  brand: string; model: string; year: string; detail: string | null;
  detalles: string | null; image: string | null; oemCode: string | null;
  factoryCode: string | null; price1: string; price2: string;
  wholesalePrice: string | null; cost: string | null;
  categoryId: number | null; category: string | null; stock: number;
}

interface Filters {
  brands: string[];
  manufacturers: string[];
  categories: { id: number; name: string }[];
  models?: string[];
  years?: string[];
}

interface Location {
  id: number;
  name: string;
  type: string;
}

interface FormData {
  itemCode: string; manufacturer: string; name: string; brand: string;
  model: string; year: string; detail: string; oemCode: string;
  factoryCode: string; price1: string; price2: string;
  wholesalePrice: string; cost: string; categoryId: string;
}

const emptyForm: FormData = {
  itemCode: "", manufacturer: "", name: "", brand: "", model: "", year: "",
  detail: "", oemCode: "", factoryCode: "", price1: "", price2: "",
  wholesalePrice: "", cost: "", categoryId: "",
};

const ALL_COLUMNS = [
  "ID", "Fabricante", "Producto", "Marca", "Modelo", "Año", "Detalles",
  "Cód. OEM", "Cód. Fábrica", "Imagen", "Precio 1", "Precio 2", "Stock", "Acciones",
];

function getStoredColumns(): string[] | null {
  try {
    const raw = localStorage.getItem("columns_inventario");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function InventoryPage() {
  const navigate = useNavigate();
  const { user, columnConfig, allowedCategories } = useAuthStore();
  const canEdit = user?.role === "ADMIN";
  const hasCategoryRestriction = user?.role === "TIENDA" && allowedCategories.length > 0;
  const [products, setProducts] = useState<Product[]>([]);
  const [filters, setFilters] = useState<Filters>({ brands: [], manufacturers: [], categories: [] });
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);

  const [search, setSearch] = useState("");
  const [brand, setBrand] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const [visibleColumns, setVisibleColumns] = useState<string[]>(() => {
    const stored = getStoredColumns();
    const roleCols = columnConfig?.inventario;
    const base = stored && stored.length ? stored : roleCols && roleCols.length ? roleCols : ALL_COLUMNS;
    const merged = ALL_COLUMNS.filter((c) => base.includes(c));
    return merged.length ? merged : ALL_COLUMNS;
  });

  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormData>(emptyForm);
  const [saving, setSaving] = useState(false);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);

  const [showStockModal, setShowStockModal] = useState<number | null>(null);
  const [stockData, setStockData] = useState<any>(null);
  const [stockLoading, setStockLoading] = useState(false);

  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  const [importLocationId, setImportLocationId] = useState("");

  const fetchProducts = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (brand) params.set("brand", brand);
      if (manufacturer) params.set("manufacturer", manufacturer);
      params.set("page", String(page));
      params.set("limit", "15");

      const res = await api.get(`/products?${params.toString()}`);
      setProducts(res.data.products);
      setTotal(res.data.pagination.total);
      setPages(res.data.pagination.pages);
    } catch {
      toast.error("Error al cargar productos");
    } finally {
      setLoading(false);
    }
  }, [search, brand, manufacturer, page]);

  const fetchFilters = useCallback(async () => {
    try {
      const res = await api.get("/products/filters");
      setFilters(res.data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchProducts(); }, [fetchProducts]);
  useEffect(() => { fetchFilters(); }, [fetchFilters]);
  useEffect(() => { api.get("/locations").then((res) => setLocations(res.data.locations || res.data)).catch(() => {}); }, []);

  useEffect(() => { setPage(1); }, [search, brand, manufacturer]);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm);
    setShowModal(true);
  };

  const openEdit = (p: Product) => {
    setEditingId(p.id);
    setForm({
      itemCode: p.itemCode, manufacturer: p.manufacturer, name: p.name,
      brand: p.brand, model: p.model, year: p.year, detail: p.detail || "",
      oemCode: p.oemCode || "", factoryCode: p.factoryCode || "",
      price1: String(p.price1), price2: String(p.price2),
      wholesalePrice: p.wholesalePrice ? String(p.wholesalePrice) : "",
      cost: p.cost ? String(p.cost) : "",
      categoryId: p.categoryId ? String(p.categoryId) : "",
    });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.itemCode || !form.manufacturer || !form.name || !form.brand || !form.model || !form.year || !form.price1) {
      toast.error("Completa los campos obligatorios");
      return;
    }

    const yearError = validateYearRanges(form.year);
    if (yearError) {
      toast.error(yearError);
      return;
    }
    try {
      setSaving(true);
      const payload = {
        ...form,
        price1: Number(form.price1),
        price2: form.price2 ? Number(form.price2) : Number(form.price1),
        wholesalePrice: form.wholesalePrice ? Number(form.wholesalePrice) : null,
        cost: form.cost ? Number(form.cost) : null,
        categoryId: form.categoryId ? Number(form.categoryId) : null,
      };

      if (editingId) {
        await api.put(`/products/${editingId}`, payload);
        toast.success("Producto actualizado");
      } else {
        await api.post("/products", payload);
        toast.success("Producto creado");
      }
      setShowModal(false);
      fetchProducts();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/products/${id}`);
      toast.success("Producto eliminado");
      setShowDeleteConfirm(null);
      fetchProducts();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al eliminar");
    }
  };

  const openStock = async (productId: number) => {
    try {
      setShowStockModal(productId);
      setStockLoading(true);
      const res = await api.get(`/inventory/product/${productId}`);
      setStockData(res.data);
    } catch {
      toast.error("Error al cargar stock");
      setShowStockModal(null);
    } finally {
      setStockLoading(false);
    }
  };

  const formatCurrency = (v: string) => `Bs. ${Number(v).toLocaleString("es-BO", { minimumFractionDigits: 2 })}`;

  const handleImportExcel = async () => {
    if (!importFile) return;
    try {
      setImporting(true);
      setImportResult(null);
      const formData = new FormData();
      formData.append("file", importFile);
      if (importLocationId) formData.append("locationId", importLocationId);
      const res = await api.post("/products/import", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setImportResult(res.data);
      toast.success(`Importación completada: ${res.data.imported} creados, ${res.data.updated} actualizados`);
      fetchProducts();
      fetchFilters();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al importar archivo");
    } finally {
      setImporting(false);
    }
  };

  const setField = (field: keyof FormData, value: string) => setForm((prev) => ({ ...prev, [field]: value }));

  const visibleProducts = hasCategoryRestriction
    ? products.filter((p) => allowedCategories.includes(p.category || "") || !p.category)
    : products;

  const allVisibleCount = hasCategoryRestriction ? visibleProducts.length : total;

  const renderInventoryCell = (p: Product, column: string) => {
    switch (column) {
      case "ID": return <td key={column} className="px-4 py-3 text-gray-400">{p.id}</td>;
      case "Fabricante": return <td key={column} className="px-4 py-3 text-gray-300">{p.manufacturer}</td>;
      case "Producto": return <td key={column} className="px-4 py-3 text-white font-medium max-w-[200px] truncate">{p.name}</td>;
      case "Marca": return <td key={column} className="px-4 py-3 text-gray-300">{p.brand}</td>;
      case "Modelo": return <td key={column} className="px-4 py-3 text-gray-300">{p.model}</td>;
      case "Año": return <td key={column} className="px-4 py-3 text-gray-400">{p.year}</td>;
      case "Detalles": return <td key={column} className="px-4 py-3 text-gray-400 text-xs">{p.detalles || p.detail || "—"}</td>;
      case "Cód. OEM": return <td key={column} className="px-4 py-3 text-gray-400 text-xs">{p.oemCode || "—"}</td>;
      case "Cód. Fábrica": return <td key={column} className="px-4 py-3 text-gray-400 text-xs">{p.factoryCode || "—"}</td>;
      case "Imagen": return <td key={column} className="px-4 py-3"><div className="w-10 h-10 mx-auto bg-dark-900/50 rounded-lg flex items-center justify-center overflow-hidden"><ProductImage image={p.image} category={p.category} name={p.name} /></div></td>;
      case "Precio 1": return <td key={column} className="px-4 py-3 text-right text-green-400 font-medium">{formatCurrency(p.price1)}</td>;
      case "Precio 2": return <td key={column} className="px-4 py-3 text-right text-blue-400">{formatCurrency(p.price2)}</td>;
      case "Stock": return <td key={column} className="px-4 py-3 text-center"><span className={`px-2 py-0.5 text-xs font-medium rounded-full ${p.stock === 0 ? "bg-red-500/10 text-red-400" : p.stock <= 5 ? "bg-yellow-500/10 text-yellow-400" : "bg-green-500/10 text-green-400"}`}>{p.stock}</span></td>;
      case "Acciones": return <td key={column} className="px-4 py-3"><div className="flex items-center justify-center gap-1"><button onClick={() => navigate(`/panel/inventario/${p.id}`)} className="p-1.5 rounded-lg text-gray-400 hover:text-blue-400 hover:bg-blue-500/10 transition-all" title="Ver detalle"><Eye size={16} /></button>{canEdit && <><button onClick={() => openEdit(p)} className="p-1.5 rounded-lg text-gray-400 hover:text-amber-400 hover:bg-amber-500/10 transition-all" title="Editar"><Pencil size={16} /></button><button onClick={() => setShowDeleteConfirm(p.id)} className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition-all" title="Eliminar"><Trash2 size={16} /></button></>}<button onClick={() => openStock(p.id)} className="p-1.5 rounded-lg text-gray-400 hover:text-purple-400 hover:bg-purple-500/10 transition-all" title="Ver stock por ubicación"><Package size={16} /></button></div></td>;
      default: return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Inventario</h1>
          <p className="text-gray-400 text-sm mt-1">{allVisibleCount} productos registrados</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchProducts} className="p-2.5 bg-dark-800 border border-dark-700/50 rounded-xl text-gray-400 hover:text-white hover:border-primary-600/50 transition-all" title="Actualizar">
            <RefreshCw size={18} />
          </button>
          <ColumnManager module="inventario" columns={ALL_COLUMNS} onVisibleChange={setVisibleColumns} />
          {canEdit && (
            <>
              <button onClick={() => { setShowImportModal(true); setImportFile(null); setImportResult(null); }} className="flex items-center gap-2 px-4 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-green-600/20">
                <Upload size={18} />
                <span className="hidden sm:inline">Importar Excel</span>
              </button>
              <button onClick={openCreate} className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2 shadow-lg shadow-primary-600/20">
                <Plus size={18} />
                Nuevo Producto
              </button>
            </>
          )}
        </div>
      </div>

      {/* Search & Filters */}
      <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl p-4">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por código, nombre, marca, modelo, OEM..."
              className="w-full pl-10 pr-4 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-sm"
            />
            {search && (
              <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white">
                <X size={16} />
              </button>
            )}
          </div>
          <button onClick={() => setShowFilters(!showFilters)} className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm border transition-all ${showFilters ? "bg-primary-600/10 border-primary-600/20 text-primary-400" : "bg-dark-900/50 border-dark-600/50 text-gray-400 hover:text-white"}`}>
            <Filter size={16} />
            Filtros
            <ChevronDown size={14} className={`transition-transform ${showFilters ? "rotate-180" : ""}`} />
          </button>
        </div>

        {showFilters && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4 pt-4 border-t border-dark-700/50">
            <Autocomplete
              value={brand}
              onChange={setBrand}
              suggestions={filters.brands}
              placeholder="Todas las marcas"
              label="Marca"
            />
            <Autocomplete
              value={manufacturer}
              onChange={setManufacturer}
              suggestions={filters.manufacturers}
              placeholder="Todos los fabricantes"
              label="Fabricante"
            />
            {(brand || manufacturer) && (
              <div className="flex items-end">
                <button onClick={() => { setBrand(""); setManufacturer(""); }} className="px-3 py-2.5 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm hover:bg-red-500/20 transition-colors">
                  Limpiar filtros
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Table */}
      <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw size={32} className="text-primary-400 animate-spin" />
          </div>
        ) : visibleProducts.length === 0 ? (
          <div className="p-6 text-center">
            <Package size={48} className="text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">Sin productos registrados</p>
          </div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 border-b border-dark-700/50">
                    {visibleColumns.map((col) => {
                      const align = ["Precio 1", "Precio 2"].includes(col) ? "text-right" : ["Imagen", "Stock", "Acciones"].includes(col) ? "text-center" : "text-left";
                      return (
                        <th key={col} className={`${align} px-4 py-3 font-medium`}>{col}</th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {visibleProducts.map((p) => (
                    <tr key={p.id} className="border-b border-dark-700/30 last:border-0 hover:bg-dark-900/30 transition-colors">
                      {visibleColumns.map((column) => renderInventoryCell(p, column))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden divide-y divide-dark-700/30">
              {visibleProducts.map((p) => (
                <div key={p.id} className="p-4 space-y-2">
                  <div className="flex items-start gap-3">
                    <div className="w-12 h-12 bg-dark-900/50 rounded-xl flex items-center justify-center overflow-hidden shrink-0">
                      <ProductImage image={p.image} category={p.category} name={p.name} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-white font-medium text-sm truncate">{p.name}</p>
                      <p className="text-xs text-gray-500">{p.brand} · {p.model} · {p.year}</p>
                      <p className="text-xs text-gray-600">{p.manufacturer}</p>
                    </div>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full shrink-0 ${p.stock === 0 ? "bg-red-500/10 text-red-400" : p.stock <= 5 ? "bg-yellow-500/10 text-yellow-400" : "bg-green-500/10 text-green-400"}`}>
                      {p.stock}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-green-400 font-medium">{formatCurrency(p.price1)}</span>
                    <div className="flex items-center gap-1">
                      <button onClick={() => navigate(`/panel/inventario/${p.id}`)} className="p-1.5 rounded-lg text-gray-400 hover:text-blue-400 active:bg-blue-500/10 transition-all">
                        <Eye size={16} />
                      </button>
                      {canEdit && (
                        <>
                          <button onClick={() => openEdit(p)} className="p-1.5 rounded-lg text-gray-400 hover:text-amber-400 active:bg-amber-500/10 transition-all">
                            <Pencil size={16} />
                          </button>
                          <button onClick={() => setShowDeleteConfirm(p.id)} className="p-1.5 rounded-lg text-gray-400 hover:text-red-400 active:bg-red-500/10 transition-all">
                            <Trash2 size={16} />
                          </button>
                        </>
                      )}
                      <button onClick={() => openStock(p.id)} className="p-1.5 rounded-lg text-gray-400 hover:text-purple-400 active:bg-purple-500/10 transition-all">
                        <Package size={16} />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-dark-700/50">
            <p className="text-gray-400 text-sm">Página {page} de {pages}</p>
            <div className="flex items-center gap-2">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="p-2 rounded-lg bg-dark-900/50 border border-dark-600/50 text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all">
                <ChevronLeft size={16} />
              </button>
              {Array.from({ length: Math.min(5, pages) }, (_, i) => {
                const start = Math.max(1, Math.min(page - 2, pages - 4));
                const p = start + i;
                if (p > pages) return null;
                return (
                  <button key={p} onClick={() => setPage(p)} className={`w-8 h-8 rounded-lg text-sm font-medium transition-all ${p === page ? "bg-primary-600 text-white" : "bg-dark-900/50 border border-dark-600/50 text-gray-400 hover:text-white"}`}>
                    {p}
                  </button>
                );
              })}
              <button onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page === pages} className="p-2 rounded-lg bg-dark-900/50 border border-dark-600/50 text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all">
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal: Crear / Editar Producto */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-dark-800 border border-dark-700/50 rounded-2xl w-full max-w-full sm:max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-dark-700/50">
              <h2 className="text-lg font-bold text-white">{editingId ? "Editar Producto" : "Nuevo Producto"}</h2>
              <button onClick={() => setShowModal(false)} className="p-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-xl transition-all">
                <X size={18} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Field label="Código Item *" value={form.itemCode} onChange={(v) => setField("itemCode", v)} disabled={!!editingId} />
                <Field label="Fabricante *" value={form.manufacturer} onChange={(v) => setField("manufacturer", v)} />
                <Field label="Nombre *" value={form.name} onChange={(v) => setField("name", v)} className="col-span-2" />
                <Field label="Marca *" value={form.brand} onChange={(v) => setField("brand", v)} />
                <Field label="Modelo *" value={form.model} onChange={(v) => setField("model", v)} />
                <Field label="Año *" value={form.year} onChange={(v) => setField("year", v)} placeholder="ej: 2020-2024" />
                <Field label="Detalles" value={form.detail} onChange={(v) => setField("detail", v)} placeholder="Detalle opcional" />
                <Field label="Código OEM" value={form.oemCode} onChange={(v) => setField("oemCode", v)} />
                <Field label="Código Fábrica" value={form.factoryCode} onChange={(v) => setField("factoryCode", v)} />
              </div>
              <div className="border-t border-dark-700/50 pt-4">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-3">Precios (Bs.)</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Field label="Precio 1 *" value={form.price1} onChange={(v) => setField("price1", v)} type="number" />
                  <Field label="Precio 2" value={form.price2} onChange={(v) => setField("price2", v)} type="number" />
                  <Field label="Precio Mayor" value={form.wholesalePrice} onChange={(v) => setField("wholesalePrice", v)} type="number" />
                  <Field label="Costo" value={form.cost} onChange={(v) => setField("cost", v)} type="number" />
                </div>
              </div>
              <div className="relative">
                <label className="block text-xs text-gray-400 mb-1.5">Categoría</label>
                <select value={form.categoryId} onChange={(e) => setField("categoryId", e.target.value)} className="w-full appearance-none px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none pr-8">
                  <option value="">Sin categoría</option>
                  {filters.categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <ChevronDown size={14} className="absolute right-2.5 top-[38px] text-gray-500 pointer-events-none" />
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-5 border-t border-dark-700/50">
              <button onClick={() => setShowModal(false)} className="px-4 py-2.5 text-sm text-gray-400 hover:text-white transition-colors">Cancelar</button>
              <button onClick={handleSave} disabled={saving} className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-all disabled:opacity-50">
                {saving ? "Guardando..." : editingId ? "Actualizar" : "Crear Producto"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Confirmar Eliminación */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-dark-800 border border-dark-700/50 rounded-2xl p-6 w-full max-w-sm text-center">
            <Trash2 size={40} className="text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-white mb-2">¿Eliminar producto?</h3>
            <p className="text-gray-400 text-sm mb-6">Esta acción no se puede deshacer.</p>
            <div className="flex items-center justify-center gap-3">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2.5 text-sm text-gray-400 hover:text-white transition-colors">Cancelar</button>
              <button onClick={() => handleDelete(showDeleteConfirm)} className="bg-red-600 hover:bg-red-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-all">Eliminar</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Stock por Ubicación */}
      {showStockModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-dark-800 border border-dark-700/50 rounded-2xl w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b border-dark-700/50">
              <h2 className="text-lg font-bold text-white">Stock por Ubicación</h2>
              <button onClick={() => { setShowStockModal(null); setStockData(null); }} className="p-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-xl transition-all">
                <X size={18} />
              </button>
            </div>
            <div className="p-5">
              {stockLoading ? (
                <div className="flex items-center justify-center h-32">
                  <RefreshCw size={24} className="text-primary-400 animate-spin" />
                </div>
              ) : stockData ? (
                <>
                  <div className="mb-4 p-3 bg-dark-900/50 rounded-xl border border-dark-700/30">
                    <p className="text-white font-medium">{stockData.stockTotal} unidades totales</p>
                  </div>
                  <div className="space-y-2">
                    {stockData.locations.map((loc: any) => (
                      <div key={loc.locationId} className="flex items-center justify-between p-3 bg-dark-900/50 rounded-xl border border-dark-700/30">
                        <div>
                          <p className="text-sm text-gray-200">{loc.locationName}</p>
                          <p className="text-xs text-gray-500">{loc.locationType === "ALMACEN" ? "Almacén" : "Tienda"}</p>
                        </div>
                        <div className="text-right">
                          <p className={`text-lg font-bold ${loc.stock === 0 ? "text-red-400" : loc.stock <= loc.minStock ? "text-yellow-400" : "text-green-400"}`}>{loc.stock}</p>
                          <p className="text-xs text-gray-500">mín: {loc.minStock}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* Modal: Importar Excel */}
      {showImportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-dark-800 border border-dark-700/50 rounded-2xl w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b border-dark-700/50">
              <h2 className="text-lg font-bold text-white">Importar Productos desde Excel</h2>
              <button onClick={() => { setShowImportModal(false); setImportResult(null); }} className="p-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-xl transition-all">
                <X size={18} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-3">
                <p className="text-blue-400 text-xs font-medium mb-1">Columnas aceptadas:</p>
       <p className="text-gray-400 text-xs">Codigo fabrica, Descripcion, Fabricante, Marca, Modelo, Años, Detalle, Codigo OEM, Codigo fabrica, Categoría, Precio 1, Precio 2, Precio mayor, Costo, Stock, Detalles</p>
              </div>
                {!importResult ? (
                  <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Ubicación de los productos</label>
                    <select value={importLocationId} onChange={(e) => setImportLocationId(e.target.value)}
                      className="w-full px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none">
                      <option value="">Todas las ubicaciones (stock 0)</option>
                      {locations.map((location) => <option key={location.id} value={location.id}>{location.name} ({location.type})</option>)}
                    </select>
                    <p className="text-[11px] text-gray-600 mt-1">Si eliges una ubicación, la columna Stock se asigna allí.</p>
                  </div>
                  <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-dark-600/50 rounded-xl cursor-pointer hover:border-primary-500/50 transition-colors bg-dark-900/30">
                    <div className="flex flex-col items-center gap-2">
                      {importFile ? (
                        <>
                          <FileSpreadsheet size={32} className="text-green-400" />
                          <span className="text-sm text-white">{importFile.name}</span>
                          <span className="text-xs text-gray-500">{(importFile.size / 1024).toFixed(1)} KB</span>
                        </>
                      ) : (
                        <>
                          <Upload size={32} className="text-gray-500" />
                          <span className="text-sm text-gray-400">Seleccionar archivo .xlsx o .xls</span>
                        </>
                      )}
                    </div>
                    <input type="file" className="hidden" accept=".xlsx,.xls" onChange={(e) => setImportFile(e.target.files?.[0] || null)} />
                  </label>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-3">
                      <p className="text-2xl font-bold text-green-400">{importResult.imported}</p>
                      <p className="text-xs text-gray-400">Creados</p>
                    </div>
                    <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-3">
                      <p className="text-2xl font-bold text-blue-400">{importResult.updated}</p>
                      <p className="text-xs text-gray-400">Actualizados</p>
                    </div>
                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                      <p className="text-2xl font-bold text-red-400">{importResult.errors}</p>
                      <p className="text-xs text-gray-400">Errores</p>
                    </div>
                  </div>
                  {importResult.details?.errors?.length > 0 && (
                    <div className="bg-red-500/5 border border-red-500/10 rounded-xl p-3 max-h-32 overflow-y-auto">
                      {importResult.details.errors.map((e: string, i: number) => (
                        <p key={i} className="text-xs text-red-400">{e}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="flex items-center justify-end gap-3 p-5 border-t border-dark-700/50">
              <button onClick={() => { setShowImportModal(false); setImportResult(null); }} className="px-4 py-2.5 text-sm text-gray-400 hover:text-white transition-colors">
                {importResult ? "Cerrar" : "Cancelar"}
              </button>
              {!importResult && (
                <button onClick={handleImportExcel} disabled={!importFile || importing} className="bg-green-600 hover:bg-green-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-all disabled:opacity-50 flex items-center gap-2">
                  {importing ? <><RefreshCw size={16} className="animate-spin" /> Importando...</> : <><Upload size={16} /> Importar</>}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, value, onChange, type = "text", placeholder, disabled, className = "" }: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; placeholder?: string; disabled?: boolean; className?: string;
}) {
  return (
    <div className={className}>
      <label className="block text-xs text-gray-400 mb-1.5">{label}</label>
      <input
        type={type} value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder} disabled={disabled}
        className="w-full px-3 py-2.5 bg-dark-900/50 border border-dark-600/50 rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none placeholder-gray-600 disabled:opacity-50"
      />
    </div>
  );
}
