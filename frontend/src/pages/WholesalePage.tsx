import { useState, useRef } from "react";
import {
  TrendingUp, Plus, Minus, Trash2, X, Search, FileText,
  Check, Upload, RefreshCw, FileSpreadsheet,
} from "lucide-react";
import toast from "react-hot-toast";
import api from "../services/api";

interface WholesaleItem {
  id: number; itemCode: string; productName: string; brand: string;
  model: string; years: string; detail: string; quantity: number;
  unitPrice: number; subtotal: number;
}

interface WholesaleSale {
  id: number; date: string; clientName: string; pedido: string;
  deliveryPlace: string; paymentMethod: string; total: number;
  items: WholesaleItem[];
}

const MOCK_SALES: WholesaleSale[] = [
  { id: 1, date: "2026-08-20", clientName: "Taller Mecánico Los Andes", pedido: "Pedido #1234", deliveryPlace: "Cochabamba", paymentMethod: "Transferencia", total: 4250.00,
    items: [{ id: 1, itemCode: "FA-001", productName: "Filtro de Aceite", brand: "Bosch", model: "FIL-200", years: "2018-2024", detail: "Motor 1.6", quantity: 50, unitPrice: 40.00, subtotal: 2000.00 },
            { id: 2, itemCode: "PF-023", productName: "Pastillas de Freno", brand: "TRW", model: "DB-1200", years: "2015-2023", detail: "Delanteras", quantity: 20, unitPrice: 112.50, subtotal: 2250.00 }] },
  { id: 2, date: "2026-08-18", clientName: "Distribuidora AutoParts SRL", pedido: "Pedido #1230", deliveryPlace: "Santa Cruz", paymentMethod: "Efectivo", total: 7800.00,
    items: [{ id: 3, itemCode: "AD-105", productName: "Amortiguador Delantero", brand: "Monroe", model: "Matic-60", years: "2016-2022", detail: "Izquierdo", quantity: 30, unitPrice: 260.00, subtotal: 7800.00 }] },
];

const MOCK_CATALOG = [
  { id: 1, itemCode: "FA-001", productName: "Filtro de Aceite", brand: "Bosch", model: "FIL-200", years: "2018-2024", detail: "Motor 1.6", wholesalePrice: 40.00 },
  { id: 2, itemCode: "PF-023", productName: "Pastillas de Freno", brand: "TRW", model: "DB-1200", years: "2015-2023", detail: "Delanteras", wholesalePrice: 112.50 },
  { id: 3, itemCode: "AD-105", productName: "Amortiguador Delantero", brand: "Monroe", model: "Matic-60", years: "2016-2022", detail: "Izquierdo", wholesalePrice: 260.00 },
  { id: 4, itemCode: "CD-078", productName: "Correa de Distribución", brand: "Gates", model: "T-890", years: "2017-2025", detail: "Completa", wholesalePrice: 80.00 },
  { id: 5, itemCode: "BI-044", productName: "Bujía Iridium", brand: "NGK", model: "IR-7", years: "2019-2026", detail: "Set 4 unidades", wholesalePrice: 30.00 },
  { id: 6, itemCode: "RA-012", productName: "Radiador", brand: "Nissens", model: "RD-500", years: "2014-2020", detail: "Aluminio completo", wholesalePrice: 530.00 },
];

export default function WholesalePage() {
  const [sales, setSales] = useState<WholesaleSale[]>(MOCK_SALES);
  const [showForm, setShowForm] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);

  // Form state
  const [items, setItems] = useState<WholesaleItem[]>([]);
  const [searchProd, setSearchProd] = useState("");
  const [searchResults, setSearchResults] = useState<typeof MOCK_CATALOG>([]);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [clientName, setClientName] = useState("");
  const [pedido, setPedido] = useState("");
  const [deliveryPlace, setDeliveryPlace] = useState("Cochabamba");
  const [paymentMethod, setPaymentMethod] = useState("Transferencia");
  const [facturaNIT, setFacturaNIT] = useState("");

  const formatBs = (v: number) =>
    `Bs. ${v.toLocaleString("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  const total = items.reduce((sum, i) => sum + i.subtotal, 0);

  const handleSearch = (v: string) => {
    setSearchProd(v);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      if (!v || v.length < 2) { setSearchResults([]); return; }
      setSearchResults(MOCK_CATALOG.filter((p) =>
        p.productName.toLowerCase().includes(v.toLowerCase()) ||
        p.itemCode.toLowerCase().includes(v.toLowerCase()) ||
        p.brand.toLowerCase().includes(v.toLowerCase())
      ));
    }, 300);
  };

  const addItem = (p: typeof MOCK_CATALOG[0]) => {
    if (items.find((i) => i.id === p.id)) { toast.error("Producto ya agregado"); return; }
    setItems((prev) => [...prev, {
      id: p.id, itemCode: p.itemCode, productName: p.productName, brand: p.brand,
      model: p.model, years: p.years, detail: p.detail,
      quantity: 1, unitPrice: p.wholesalePrice, subtotal: p.wholesalePrice,
    }]);
    setSearchProd(""); setSearchResults([]);
  };

  const updateQuantity = (id: number, qty: number) => {
    if (qty < 1) return;
    setItems((prev) => prev.map((i) => i.id === id ? { ...i, quantity: qty, subtotal: qty * i.unitPrice } : i));
  };

  const updatePrice = (id: number, price: number) => {
    setItems((prev) => prev.map((i) => i.id === id ? { ...i, unitPrice: price, subtotal: i.quantity * price } : i));
  };

  const removeItem = (id: number) => setItems((prev) => prev.filter((i) => i.id !== id));

  const openConfirm = () => {
    if (!items.length) { toast.error("Agrega al menos un producto"); return; }
    if (!clientName.trim()) { toast.error("Ingresa el nombre del cliente"); return; }
    setShowConfirm(true);
  };

  const confirmSale = () => {
    const newSale: WholesaleSale = {
      id: Date.now(), date: new Date().toISOString().split("T")[0],
      clientName, pedido, deliveryPlace, paymentMethod, total, items: [...items],
    };
    setSales((prev) => [newSale, ...prev]);
    setShowConfirm(false);
    setShowForm(false);
    resetForm();
    toast.success("Venta por mayor registrada");
  };

  const resetForm = () => {
    setItems([]); setClientName(""); setPedido(""); setDeliveryPlace("Cochabamba");
    setPaymentMethod("Transferencia"); setFacturaNIT("");
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
      toast.success(`Importación completada: ${res.data.created} ventas creadas`);
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
      <style>body{font-family:Arial,sans-serif;padding:20px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #ccc;padding:6px 8px;text-align:left}th{background:#f0f0f0}h1{font-size:18px}h2{font-size:14px}.total{font-size:16px;font-weight:bold;text-align:right;margin-top:10px}</style></head><body>
      <h1>RepuestoPro - Nota de Venta Mayorista</h1>
      <p><b>Fecha:</b> ${sale.date} | <b>ID:</b> ${sale.id}</p>
      <p><b>Cliente:</b> ${sale.clientName} | <b>Pedido:</b> ${sale.pedido}</p>
      <p><b>Entrega:</b> ${sale.deliveryPlace} | <b>Pago:</b> ${sale.paymentMethod}</p>
      <table><thead><tr><th>Código</th><th>Producto</th><th>Marca</th><th>Modelo</th><th>Cant.</th><th>Precio</th><th>Subtotal</th></tr></thead><tbody>
      ${sale.items.map((i) => `<tr><td>${i.itemCode}</td><td>${i.productName}</td><td>${i.brand}</td><td>${i.model}</td><td>${i.quantity}</td><td>${formatBs(i.unitPrice)}</td><td>${formatBs(i.subtotal)}</td></tr>`).join("")}
      </tbody></table>
      <p class="total">TOTAL: ${formatBs(sale.total)}</p>
      </body></html>`);
    win.document.close(); win.print();
  };

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
          <button onClick={() => setShowHistory(!showHistory)}
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
          <div className="px-4 py-3 border-b border-dark-700/50">
            <h3 className="text-white font-medium">Historial de Ventas Mayoristas</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-700/50">
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">ID</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Fecha</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Cliente</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Entrega</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Pago</th>
                  <th className="text-right px-4 py-3 text-gray-400 font-medium">Total</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium">Nota</th>
                </tr>
              </thead>
              <tbody>
                {sales.map((s) => (
                  <tr key={s.id} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                    <td className="px-4 py-3 text-gray-300 font-mono text-xs">#{s.id}</td>
                    <td className="px-4 py-3 text-gray-300">{s.date}</td>
                    <td className="px-4 py-3 text-white font-medium">{s.clientName}</td>
                    <td className="px-4 py-3 text-gray-300">{s.deliveryPlace}</td>
                    <td className="px-4 py-3 text-gray-300">{s.paymentMethod}</td>
                    <td className="px-4 py-3 text-amber-400 font-medium text-right">{formatBs(s.total)}</td>
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
            {/* Client info */}
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
                  <option value="Efectivo">Efectivo</option>
                  <option value="Transferencia">Transferencia</option>
                  <option value="QR">QR</option>
                  <option value="Crédito">Crédito</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Datos factura (NIT)</label>
                <input value={facturaNIT} onChange={(e) => setFacturaNIT(e.target.value)} placeholder="NIT"
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
              </div>
            </div>

            {/* Product search */}
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
                        <p className="text-white text-sm">{p.productName}</p>
                        <p className="text-gray-400 text-xs">{p.brand} | {p.itemCode} | {p.model}</p>
                      </div>
                      <span className="text-amber-400 text-sm font-medium">{formatBs(p.wholesalePrice)}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Items table */}
            {items.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-dark-700/50">
                      <th className="text-left px-3 py-2 text-gray-400 font-medium">Código</th>
                      <th className="text-left px-3 py-2 text-gray-400 font-medium">Producto</th>
                      <th className="text-left px-3 py-2 text-gray-400 font-medium">Marca</th>
                      <th className="text-left px-3 py-2 text-gray-400 font-medium">Modelo</th>
                      <th className="text-left px-3 py-2 text-gray-400 font-medium">Años</th>
                      <th className="text-center px-3 py-2 text-gray-400 font-medium">Cant.</th>
                      <th className="text-right px-3 py-2 text-gray-400 font-medium">P. Unit.</th>
                      <th className="text-right px-3 py-2 text-gray-400 font-medium">Subtotal</th>
                      <th className="text-center px-3 py-2 text-gray-400 font-medium"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item) => (
                      <tr key={item.id} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                        <td className="px-3 py-2 text-gray-300 font-mono text-xs">{item.itemCode}</td>
                        <td className="px-3 py-2 text-white font-medium">{item.productName}</td>
                        <td className="px-3 py-2 text-gray-300">{item.brand}</td>
                        <td className="px-3 py-2 text-gray-300">{item.model}</td>
                        <td className="px-3 py-2 text-gray-400 text-xs">{item.years}</td>
                        <td className="px-3 py-2">
                          <div className="flex items-center justify-center gap-1">
                            <button onClick={() => updateQuantity(item.id, item.quantity - 1)}
                              className="p-1 text-gray-400 hover:text-white hover:bg-dark-700 rounded transition-all"><Minus size={12} /></button>
                            <span className="w-8 text-center text-white text-sm">{item.quantity}</span>
                            <button onClick={() => updateQuantity(item.id, item.quantity + 1)}
                              className="p-1 text-gray-400 hover:text-white hover:bg-dark-700 rounded transition-all"><Plus size={12} /></button>
                          </div>
                        </td>
                        <td className="px-3 py-2 text-right">
                          <input type="number" value={item.unitPrice} onChange={(e) => updatePrice(item.id, Number(e.target.value))}
                            className="w-20 px-2 py-1 bg-dark-800 border border-dark-700 rounded-lg text-white text-xs text-right focus:outline-none focus:border-primary-500" />
                        </td>
                        <td className="px-3 py-2 text-amber-400 font-medium text-right">{formatBs(item.subtotal)}</td>
                        <td className="px-3 py-2 text-center">
                          <button onClick={() => removeItem(item.id)}
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

            {/* Total + confirm */}
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
                <p className="text-blue-400 text-xs font-medium mb-1">El Excel debe contener columnas con: código, producto, marca, modelo, año, detalle, precio mayorista, cantidad</p>
              </div>
              {!importResult ? (
                <div className="space-y-3">
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
                      <p className="text-2xl font-bold text-green-400">{importResult.created || importResult.imported || 0}</p>
                      <p className="text-xs text-gray-400">Creados</p>
                    </div>
                    <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-3">
                      <p className="text-2xl font-bold text-blue-400">{importResult.updated || 0}</p>
                      <p className="text-xs text-gray-400">Actualizados</p>
                    </div>
                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                      <p className="text-2xl font-bold text-red-400">{importResult.errors?.length || 0}</p>
                      <p className="text-xs text-gray-400">Errores</p>
                    </div>
                  </div>
                  {importResult.errors?.length > 0 && (
                    <div className="bg-red-500/5 border border-red-500/10 rounded-xl p-3 max-h-32 overflow-y-auto">
                      {importResult.errors.map((e: string, i: number) => (
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
