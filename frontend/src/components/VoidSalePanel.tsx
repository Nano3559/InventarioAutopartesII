import { useState } from "react";
import toast from "react-hot-toast";
import api from "../services/api";
import { useAuthStore } from "../stores/authStore";
import { completeOperation, pendingOperationId } from "../services/pendingOperation";
import PendingOperation from "./PendingOperation";
export default function VoidSalePanel({ onChanged }: { onChanged?: () => void }) {
  const user = useAuthStore(s => s.user);
  const [id, setId] = useState("");
  const [sale, setSale] = useState<any>(null);
  const [reason, setReason] = useState("");
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  if (user?.role !== "ADMIN") return null;
  const load = async () => {
    try { const response = await api.get(`/sales/${Number(id)}`); setSale(response.data); setChecked(false); }
    catch (e: any) { setSale(null); toast.error(e.response?.data?.message || "No se encontró la venta"); }
  };
  const submit = async () => {
    if (busy || !sale || !checked) return;
    setBusy(true);
    try {
      await api.post(`/sales/${sale.id}/void`, { operationId: pendingOperationId("VOID_SALE"), reason, goodsNeverDeliveredAndVerified: checked });
      completeOperation("VOID_SALE"); toast.success("Venta anulada. Se conserva su historial"); await load(); onChanged?.();
    } catch (e: any) { toast.error(e.response?.data?.message || "Resultado desconocido. Consulte el intento antes de repetir"); }
    finally { setBusy(false); }
  };
  const blocked = sale?.status === "VOIDED" || sale?.returns?.length > 0 || sale?.payments?.some((p: any) => p.method !== "CREDITO" && Number(p.amount) > 0);
  return <details className="rounded-xl border border-dark-700 p-4 text-gray-300 space-y-3"><summary>Anulación administrativa de venta sin cobros</summary>
    <p className="text-sm">Solo antes de entregar la mercadería y sin cobros o devoluciones. Las ventas cobradas requieren devolución y conciliación.</p>
    <div className="flex flex-wrap gap-2"><input aria-label="Número de venta a revisar" className="bg-dark-800 p-2" type="number" min={1} value={id} onChange={e => { setId(e.target.value); setSale(null); }} /><button type="button" onClick={load}>Revisar venta</button></div>
    {sale && <div className="space-y-2"><p>Venta #{sale.id} · Total original Bs. {Number(sale.total).toFixed(2)} · {sale.status === "VOIDED" ? "ANULADA" : "Confirmada"}</p>
      {blocked ? <p>Esta venta no admite anulación directa. {sale.voidReason || "Revise cobros y devoluciones."}</p> : <>
        <textarea aria-label="Motivo de anulación" className="block w-full bg-dark-800 p-2" minLength={10} maxLength={500} placeholder="Motivo detallado" value={reason} onChange={e => setReason(e.target.value)} />
        <label className="flex gap-2"><input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} />La mercadería nunca se entregó. Conté todas las unidades y confirmé que siguen vendibles en la ubicación original.</label>
        <button type="button" disabled={busy || !checked || reason.trim().length < 10} onClick={submit} className="text-red-400 disabled:opacity-40">Anular y restituir stock verificado</button></>}
    </div>}<PendingOperation scope="VOID_SALE" />
  </details>;
}
