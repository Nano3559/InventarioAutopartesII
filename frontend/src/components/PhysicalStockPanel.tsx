import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../services/api";
import { useAuthStore } from "../stores/authStore";
import { pendingOperationId, completeOperation } from "../services/pendingOperation";
import PendingOperation from "./PendingOperation";

type Row = { id: number; quantity: number; receivedQuantity?: number; restockedQuantity?: number; discardedQuantity?: number;
  requestId?: number | null; product: { name: string; itemCode: string }; toLocation?: { name: string };
  sale?: { location: { name: string } }; reason?: string };

export default function PhysicalStockPanel({ mode, onStockChanged }: { mode: "receive" | "inspect"; onStockChanged?: () => void }) {
  const { user, permissions } = useAuthStore();
  const allowed = user?.role === "ADMIN" || (mode === "inspect" ? user?.role === "INVENTARIO" : ["INVENTARIO", "TIENDA"].includes(user?.role || "")) &&
    (permissions || []).some(p => (mode === "inspect" ? ["inventario", "devoluciones"] : ["movimientos", "solicitudes"]).includes(p));
  const [rows, setRows] = useState<Row[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const scope = mode === "inspect" ? "RETURN_INSPECTION" : "RECEIVE_MOVEMENT";
  const load = useCallback(async () => {
    if (!allowed) return;
    try {
      const response = await api.get(mode === "inspect" ? "/returns/inspection/pending" : "/movements/incoming");
      setRows(response.data[mode === "inspect" ? "returns" : "movements"] || []); setError("");
    } catch (e: any) { setError(e.response?.data?.message || "No se pudieron consultar los pendientes"); }
  }, [allowed, mode]);
  useEffect(() => { void load(); }, [load]);
  if (!allowed) return null;
  const act = async (row: Row, outcome?: string) => {
    if (busy) return;
    const remaining = row.quantity - (mode === "inspect" ? (row.restockedQuantity || 0) + (row.discardedQuantity || 0) : row.receivedQuantity || 0);
    const input = window.prompt(mode === "inspect" ? "Cantidad inspeccionada físicamente" : "Cantidad recibida físicamente", String(remaining));
    if (input === null) return;
    const quantity = Number(input);
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > remaining) { toast.error("Cantidad fuera de lo pendiente"); return; }
    const reason = mode === "inspect" ? window.prompt("Motivo y resultado de la inspección") : undefined;
    if (mode === "inspect" && !reason?.trim()) return;
    try {
      setBusy(true);
      await api.post(mode === "inspect" ? `/returns/inspection/${row.id}` : `/movements/${row.id}/receive`,
        { operationId: pendingOperationId(scope), quantity, ...(mode === "inspect" ? { outcome, reason } : {}) });
      completeOperation(scope); toast.success(mode === "inspect" ? "Inspección registrada" : "Recepción registrada");
      await load();
      onStockChanged?.();
    } catch (e: any) { toast.error(e.response?.data?.message || "Resultado pendiente. Consulte el intento antes de repetir"); }
    finally { setBusy(false); }
  };
  return <section className="rounded-xl border border-dark-700 p-4 space-y-3">
    <div className="flex flex-wrap justify-between gap-2"><h2 className="font-semibold text-white">{mode === "inspect" ? "Devoluciones pendientes de inspección" : "Mercadería en tránsito"}</h2>
      <button type="button" onClick={load} className="text-sm text-primary-400">Actualizar pendientes</button></div>
    <p className="text-sm text-gray-400">{mode === "inspect" ? "Solo la cantidad aprobada como vendible ingresará al stock disponible." : "El traslado no está disponible para venta hasta confirmar la recepción física."}</p>
    <PendingOperation scope={scope} />
    {error && <p role="alert" className="text-red-400">{error}</p>}
    {!error && !rows.length && <p className="text-gray-500 text-sm">Sin pendientes.</p>}
    {rows.map(row => <div key={row.id} className="border-t border-dark-700 pt-3 flex flex-wrap items-center justify-between gap-3 text-sm">
      <div><p className="text-white">#{row.id} · {row.product.itemCode} · {row.product.name}</p><p className="text-gray-400">{row.toLocation?.name || row.sale?.location.name} · Pendiente: {row.quantity - (mode === "inspect" ? (row.restockedQuantity || 0) + (row.discardedQuantity || 0) : row.receivedQuantity || 0)}</p></div>
      {row.requestId ? <a className="text-primary-400 underline" href="/panel/solicitudes">Recibir desde solicitud #{row.requestId}</a> : <div className="flex flex-wrap gap-3">
        <button type="button" disabled={busy} onClick={() => act(row, "SELLABLE")} className="text-green-400 disabled:opacity-50">{mode === "inspect" ? "Aprobar vendible" : "Confirmar recepción"}</button>
        {mode === "inspect" && <button type="button" disabled={busy} onClick={() => act(row, "NOT_SELLABLE")} className="text-amber-400 disabled:opacity-50">Separar no vendible</button>}
      </div>}
    </div>)}
    {rows.length >= 200 && <p className="text-amber-300 text-sm">Se muestran 200 pendientes. Al resolverlos aparecerán los siguientes.</p>}
  </section>;
}
