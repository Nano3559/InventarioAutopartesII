import { useState, useEffect, useRef, useCallback } from "react";
import {
  TrendingUp, Plus, Minus, Trash2, X, Search, FileText,
  Check, Upload, RefreshCw, FileSpreadsheet,
} from "lucide-react";
import toast from "react-hot-toast";
import api from "../services/api";

interface WholesaleItem {
  productId: number; itemCode: string; name: string; brand: string;
  model: string; year: string; detail: string | null; quantity: number;
  unitPrice: number; subtotal: number;
}

interface WholesaleSale {
  id: number; saleDate: string; total: number; type: string;
  customer: { name: string; nit: string | null } | null;
  location: { name: string } | null;
  user: { name: string } | null;
  payments: { method: string; amount: number }[];
  items: { productId: number; quantity: number; unitPrice: number; subtotal: number; product: { id: number; name: string; itemCode: string; brand: string; model: string } }[];
}

interface ProductResult {
  id: number; itemCode: string; name: string; brand: string;
  model: string; year: string; detail: string | null;
  wholesalePrice: number | null; price1: number;
}

export default function WholesalePage() {
  const [sales, setSales] = useState<WholesaleSale[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);

  const [items, setItems] = useState<WholesaleItem[]>([]);
  const [searchProd, setSearchProd] = useState("");
  const [searchResults, setSearchResults] = useState<ProductResult[]>([]);
  const [searchingProducts, setSearchingProducts] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [clientName, setClientName] = useState("");
  const [pedido, setPedido] = useState("");
  const [deliveryPlace, setDeliveryPlace] = useState("Cochabamba");
  const [paymentMethod, setPaymentMethod] = useState("TRANSFERENCIA");
  const [facturaNIT, setFacturaNIT] = useState("");

  const formatBs = (v: number) =>
    `Bs. ${v.toLocaleString("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const total = items.reduce((sum, i) => sum + i.subtotal, 0);

  const fetchSales = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get("/wholesale?limit=50");
      setSales(res.data.sales);
    } catch {
      toast.error("Error al cargar ventas mayoristas");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSales(); }, [fetchSales]);

  const handleSearch = (v: string) => {
    setSearchProd(v);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(async () => {
      if (!v || v.length < 2) { setSearchResults([]); return; }
      try {
        setSearchingProducts(true);
        const res = await api.get(`/products?search=${encodeURIComponent(v)}&limit=10`);
        setSearchResults(res.data.products.map((p: any) => ({
          id: p.id, itemCode: p.itemCode, name: p.name, brand: p.brand,
          model: p.model, year: p.year, detail: p.detail,
          wholesalePrice: p.wholesalePrice ? Number(p.wholesalePrice) : null,
          price1: Number(p.price1),
        })));
      } catch {
        setSearchResults([]);
      } finally {
        setSearchingProducts(false);
      }
    }, 300);
  };

  const addItem = (p: ProductResult) => {
    if (items.find((i) => i.productId === p.id)) { toast.error("Producto ya agregado"); return; }
    const price = p.wholesalePrice || p.price1;
    setItems((prev) => [...prev, {
      productId: p.id, itemCode: p.itemCode, name: p.name, brand: p.brand,
      model: p.model, year: p.year, detail: p.detail,
      quantity: 1, unitPrice: price, subtotal: price,
    }]);
    setSearchProd(""); setSearchResults([]);
  };

  const updateQuantity = (productId: number, qty: number) => {
    if (qty < 1) return;
    setItems((prev) => prev.map((i) => i.productId === productId ? { ...i, quantity: qty, subtotal: qty * i.unitPrice } : i));
  };

  const updatePrice = (productId: number, price: number) => {
    setItems((prev) => prev.map((i) => i.productId === productId ? { ...i, unitPrice: price, subtotal: i.quantity * price } : i));
  };

  const removeItem = (productId: number) => setItems((prev) => prev.filter((i) => i.productId !== productId));

  const openConfirm = () => {
    if (!items.length) { toast.error("Agrega al menos un producto"); return; }
    if (!clientName.trim()) { toast.error("Ingresa el nombre del cliente"); return; }
    setShowConfirm(true);
  };

  const confirmSale = async () => {
    try {
      const payload = {
        customerData: { name: clientName, nit: facturaNIT || null },
        paraQuien: pedido,
        lugarEntrega: deliveryPlace,
        items: items.map((i) => ({
          productId: i.productId,
          quantity: i.quantity,
          unitPrice: i.unitPrice,
        })),
        payments: [{ method: paymentMethod, amount: total }],
      };
      await api.post("/wholesale", payload);
      toast.success("Venta por mayor registrada");
      setShowConfirm(false);
      setShowForm(false);
      resetForm();
      fetchSales();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al registrar venta");
    }
  };

  const resetForm = () => {
    setItems([]); setClientName(""); setPedido(""); setDeliveryPlace("Cochabamba");
    setPaymentMethod("TRANSFERENCIA"); setFacturaNIT("");
  };

  const handleImportExcel = async () => {
    if (!importFile) return;
    try {
      setImporting(true);
      setImportResult(null);
      const formData = new FormData();
      formData.append("file", importFile);
      const res = await api.post("/wholesale/import", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setImportResult(res.data);
      toast.success(`Importación completada: ${res.data.imported} productos importados`);
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al importar archivo");
    } finally {
      setImporting(false);
    }
  };

  const printNota = (sale: WholesaleSale) => {
    const win = window.open("", "_blank");
    if (!win) return;
    win.document.write(`<html><head><title>Nota de Venta #${sale.id}</title>
      <style>body{font-family:Arial,sans-serif;padding:20px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #ccc;padding:6px 8px;text-align:left}th{background:#f0f0f0}h1{font-size:18px}.total{font-size:16px;font-weight:bold;text-align:right;margin-top:10px}</style></head><body>
      <h1>RepuestoPro - Nota de Venta Mayorista</h1>
      <p><b>Fecha:</b> ${new Date(sale.saleDate).toLocaleDateString("es-BO")} | <b>ID:</b> #${sale.id}</p>
      <p><b>Cliente:</b> ${sale.customer?.name || "N/A"} | <b>Lugar:</b> ${sale.location?.name || "N/A"}</p>
      <p><b>Vendedor:</b> ${sale.user?.name || "N/A"}</p>
      <table><thead><tr><th>Código</th><th>Producto</th><th>Marca</th><th>Modelo</th><th>Cant.</th><th>Precio</th><th>Subtotal</th></tr></thead><tbody>
      ${sale.items.map((i) => `<tr><td>${i.product.itemCode}</td><td>${i.product.name}</td><td>${i.product.brand}</td><td>${i.product.model}</td><td>${i.quantity}</td><td>${formatBs(Number(i.unitPrice))}</td><td>${formatBs(Number(i.subtotal))}</td></tr>`).join("")}
      </tbody></table>
      <p class="total">TOTAL: ${formatBs(Number(sale.total))}</p>
      <p><b>Pagos:</b> ${sale.payments.map((p) => `${p.method}: ${formatBs(Number(p.amount))}`).join(", ")}</p>
      </body></html>`);
    win.document.close(); win.print();
  };

  const formatDate = (d: string) => new Date(d).toLocaleDateString("es-BO", { day: "2-digit", month: "short", year: "numeric" });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Ventas por Mayor</h1>
          <p className="text-gray-400 text-sm mt-1">Gestión de ventas al por mayor</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={() => { setShowImportModal(true); setImportFile(null); setImportResult(null); }}
            className="flex items-center gap-2 px-4 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-green-600/20">
            <Upload size={16} /> Importar Excel
          </button>
          <button onClick={() => { setShowHistory(!showHistory); if (!showHistory) fetchSales(); }}
            className="flex items-center gap-2 px-4 py-2.5 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-xl text-sm transition-all border border-dark-600">
            <FileText size={16} /> Historial
          </button>
          <button onClick={() => { resetForm(); setShowForm(true); }}
            className="flex items-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-primary-600/20">
            <Plus size={16} /> Nueva Venta Mayor
          </button>
        </div>
      </div>

      {/* History */}
      {showHistory && (
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-700/50 flex items-center justify-between">
            <h3 className="text-white font-medium">Historial de Ventas Mayoristas</h3>
            <button onClick={fetchSales} className="p-1.5 text-gray-400 hover:text-white rounded-lg transition-all">
              <RefreshCw size={14} />
            </button>
          </div>
          {loading ? (
            <div className="flex items-center justify-center h-32"><RefreshCw size={24} className="text-primary-400 animate-spin" /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-dark-700/50">
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">ID</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Fecha</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Cliente</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Lugar</th>
                    <th className="text-left px-4 py-3 text-gray-400 font-medium">Pago</th>
                    <th className="text-right px-4 py-3 text-gray-400 font-medium">Total</th>
                    <th className="text-center px-4 py-3 text-gray-400 font-medium">Nota</th>
                  </tr>
                </thead>
                <tbody>
                  {sales.length === 0 ? (
                    <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">No hay ventas mayoristas registradas</td></tr>
                  ) : sales.map((s) => (
                    <tr key={s.id} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                      <td className="px-4 py-3 text-gray-300 font-mono text-xs">#{s.id}</td>
                      <td className="px-4 py-3 text-gray-300">{formatDate(s.saleDate)}</td>
                      <td className="px-4 py-3 text-white font-medium">{s.customer?.name || "N/A"}</td>
                      <td className="px-4 py-3 text-gray-300">{s.location?.name || "N/A"}</td>
                      <td className="px-4 py-3 text-gray-300">{s.payments.map((p) => p.method).join(", ")}</td>
                      <td className="px-4 py-3 text-amber-400 font-medium text-right">{formatBs(Number(s.total))}</td>
                      <td className="px-4 py-3 text-center">
                        <button onClick={() => printNota(s)} className="p-1.5 text-gray-400 hover:text-primary-400 hover:bg-primary-500/10 rounded-lg transition-all" title="Imprimir nota">
                          <FileText size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* New sale form */}
      {showForm && (
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-700/50 flex items-center justify-between">
            <h3 className="text-white font-medium">Nueva Venta Mayorista</h3>
            <button onClick={() => setShowForm(false)} className="p-1.5 text-gray-400 hover:text-white hover:bg-dark-700 rounded-lg transition-all">
              <X size={18} />
            </button>
          </div>

          <div className="p-4 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Nombre del cliente *</label>
                <input value={clientName} onChange={(e) => setClientName(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Para quién es el pedido</label>
                <input value={pedido} onChange={(e) => setPedido(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Lugar de entrega *</label>
                <select value={deliveryPlace} onChange={(e) => setDeliveryPlace(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500">
                  <option value="Cochabamba">Cochabamba</option>
                  <option value="Santa Cruz">Santa Cruz</option>
                  <option value="La Paz">La Paz</option>
                  <option value="Otra">Otra ubicación</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Forma de pago *</label>
                <select value={paymentMethod} onChange={(e) => setPaymentMethod(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500">
                  <option value="EFECTIVO">Efectivo</option>
                  <option value="TRANSFERENCIA">Transferencia</option>
                  <option value="QR">QR</option>
                  <option value="CREDITO">Crédito</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Datos factura (NIT)</label>
                <input value={facturaNIT} onChange={(e) => setFacturaNIT(e.target.value)} placeholder="NIT"
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
              </div>
            </div>

            <div className="relative">
              <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500" />
              <input value={searchProd} onChange={(e) => handleSearch(e.target.value)}
                placeholder="Buscar producto por código, nombre o marca..."
                className="w-full pl-10 pr-4 py-2.5 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500 transition-all" />
              {searchResults.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-dark-900 border border-dark-700 rounded-xl shadow-xl z-10 max-h-48 overflow-y-auto">
                  {searchResults.map((p) => (
                    <button key={p.id} onClick={() => addItem(p)}
                      className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-dark-800 transition-colors text-left">
                      <div>
                        <p className="text-white text-sm">{p.name}</p>
                        <p className="text-gray-400 text-xs">{p.brand} | {p.itemCode} | {p.model}</p>
                      </div>
                      <span className="text-amber-400 text-sm font-medium">{formatBs(p.wholesalePrice || p.price1)}</span>
                    </button>
                  ))}
                </div>
              )}
              {searchingProducts && searchProd.length >= 2 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-dark-900 border border-dark-700 rounded-xl p-3 text-center">
                  <RefreshCw size={16} className="text-gray-500 animate-spin mx-auto" />
                </div>
              )}
            </div>

            {items.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-dark-700/50">
                      <th className="text-left px-3 py-2 text-gray-400 font-medium">Código</th>
                      <th className="text-left px-3 py-2 text-gray-400 font-medium">Producto</th>
                      <th className="text-left px-3 py-2 text-gray-400 font-medium">Marca</th>
                      <th className="text-left px-3 py-2 text-gray-400 font-medium">Modelo</th>
                      <th className="text-center px-3 py-2 text-gray-400 font-medium">Cant.</th>
                      <th className="text-right px-3 py-2 text-gray-400 font-medium">P. Unit.</th>
                      <th className="text-right px-3 py-2 text-gray-400 font-medium">Subtotal</th>
                      <th className="text-center px-3 py-2 text-gray-400 font-medium"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => (
                      <tr key={item.productId} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                        <td className="px-3 py-2 text-gray-300 font-mono text-xs">{item.itemCode}</td>
                        <td className="px-3 py-2 text-white font-medium">{item.name}</td>
                        <td className="px-3 py-2 text-gray-300">{item.brand}</td>
                        <td className="px-3 py-2 text-gray-300">{item.model}</td>
                        <td className="px-3 py-2">
                          <div className="flex items-center justify-center gap-1">
                            <button onClick={() => updateQuantity(item.productId, item.quantity - 1)}
                              className="p-1 text-gray-400 hover:text-white hover:bg-dark-700 rounded transition-all"><Minus size={12} /></button>
                            <span className="w-8 text-center text-white text-sm">{item.quantity}</span>
                            <button onClick={() => updateQuantity(item.productId, item.quantity + 1)}
                              className="p-1 text-gray-400 hover:text-white hover:bg-dark-700 rounded transition-all"><Plus size={12} /></button>
                          </div>
                        </td>
                        <td className="px-3 py-2 text-right">
                          <input type="number" value={item.unitPrice} onChange={(e) => updatePrice(item.productId, Number(e.target.value))}
                            className="w-20 px-2 py-1 bg-dark-800 border border-dark-700 rounded-lg text-white text-xs text-right focus:outline-none focus:border-primary-500" />
                        </td>
                        <td className="px-3 py-2 text-amber-400 font-medium text-right">{formatBs(item.subtotal)}</td>
                        <td className="px-3 py-2 text-center">
                          <button onClick={() => removeItem(item.productId)}
                            className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all">
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="flex items-center justify-between pt-3 border-t border-dark-700/50">
              <span className="text-lg font-bold text-white">Total: <span className="text-amber-400">{formatBs(total)}</span></span>
              <button onClick={openConfirm}
                className="flex items-center gap-2 px-6 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-primary-600/20">
                <Check size={16} /> Confirmar Venta
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirm modal */}
      {showConfirm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-900 border border-dark-700/50 rounded-2xl w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700/50">
              <h3 className="text-lg font-bold text-white">Confirmar Venta Mayorista</h3>
              <button onClick={() => setShowConfirm(false)} className="p-1.5 text-gray-400 hover:text-white hover:bg-dark-700 rounded-lg transition-all">
                <X size={18} />
              </button>
            </div>
            <div className="p-6 space-y-3">
              <div className="flex justify-between text-sm"><span className="text-gray-400">Cliente:</span><span className="text-white">{clientName}</span></div>
              <div className="flex justify-between text-sm"><span className="text-gray-400">Entrega:</span><span className="text-white">{deliveryPlace}</span></div>
              <div className="flex justify-between text-sm"><span className="text-gray-400">Pago:</span><span className="text-white">{paymentMethod}</span></div>
              <div className="flex justify-between text-sm"><span className="text-gray-400">Productos:</span><span className="text-white">{items.length}</span></div>
              <div className="border-t border-dark-700/50 pt-3 flex justify-between">
                <span className="text-white font-medium">Total:</span>
                <span className="text-amber-400 text-lg font-bold">{formatBs(total)}</span>
              </div>
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-dark-700/50">
              <button onClick={() => setShowConfirm(false)}
                className="px-4 py-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-xl text-sm transition-all">
                Cancelar
              </button>
              <button onClick={confirmSale}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-primary-600/20">
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!showForm && !showHistory && (
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl p-8 text-center">
          <TrendingUp size={48} className="text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 mb-4">Registro de ventas al por mayor</p>
          <button onClick={() => { resetForm(); setShowForm(true); }}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-sm font-medium transition-all">
            Crear nueva venta mayorista
          </button>
        </div>
      )}

      {/* Modal: Importar Excel */}
      {showImportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-dark-800 border border-dark-700/50 rounded-2xl w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b border-dark-700/50">
              <h2 className="text-lg font-bold text-white">Importar Productos Mayoristas</h2>
              <button onClick={() => { setShowImportModal(false); setImportResult(null); }} className="p-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-xl transition-all">
                <X size={18} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-3">
                <p className="text-blue-400 text-xs font-medium mb-1">El Excel debe contener columnas con: código, producto, marca, modelo, año, detalle, precio mayorista</p>
              </div>
              {!importResult ? (
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
              ) : (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3 text-center">
                    <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-3">
                      <p className="text-2xl font-bold text-green-400">{importResult.imported || 0}</p>
                      <p className="text-xs text-gray-400">Importados</p>
                    </div>
                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                      <p className="text-2xl font-bold text-red-400">{importResult.errors?.length || 0}</p>
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
