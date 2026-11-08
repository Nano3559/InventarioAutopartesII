import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import api from "../services/api";
import { useAuthStore } from "../stores/authStore";
export interface BankVerification { receivingAccountId: number; reference: string; operationDate: string; confirmed: boolean }
export function bankDay() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/La_Paz", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
}
export const emptyBankVerification = (): BankVerification => ({ receivingAccountId: 0, reference: "", operationDate: bankDay(), confirmed: false });
export default function BankVerificationFields({ value, onChange }: { value?: BankVerification; onChange: (value: BankVerification) => void }) {
  const [accounts, setAccounts] = useState<{ id: number; code: string; name: string }[]>([]);
  const [error, setError] = useState("");
  const user = useAuthStore(s => s.user);
  const current = value || emptyBankVerification();
  const load = () => api.get("/payments/receiving-accounts").then(r => { setAccounts(r.data.accounts); setError(""); }).catch(() => setError("No se pudieron cargar cuentas receptoras"));
  useEffect(() => { void load(); }, []);
  const create = async () => {
    const code = window.prompt("Código único de cuenta receptora. Ejemplo: BANCO_CAJA_01. No escriba claves bancarias");
    if (!code) return;
    const name = window.prompt("Nombre visible de la cuenta receptora");
    if (!name) return;
    try { await api.post("/payments/receiving-accounts", { code, name }); await load(); toast.success("Cuenta receptora registrada"); }
    catch (e: any) { toast.error(e.response?.data?.message || "No se pudo registrar la cuenta"); }
  };
  return <fieldset className="w-full rounded-lg border border-amber-500/40 p-3 text-sm space-y-2">
    <legend className="text-amber-300">Verificación bancaria manual</legend>
    <p className="text-gray-400">Compruebe el abono en la cuenta de la empresa. Una captura del cliente no basta. La aplicación no consulta al banco.</p>
    <p className="text-xs text-gray-400">Administración debe mantener una sola ficha por cuenta bancaria real, sin duplicar alias.</p>
    {error && <p role="alert" className="text-red-400">{error}</p>}
    <label className="block">Cuenta receptora<select aria-label="Cuenta receptora" className="block w-full bg-dark-800 p-2" value={current.receivingAccountId} onChange={e => onChange({ ...current, receivingAccountId: Number(e.target.value), confirmed: false })}><option value={0}>Seleccione cuenta</option>{accounts.map(a => <option key={a.id} value={a.id}>{a.code} · {a.name}</option>)}</select></label>
    <label className="block">Referencia del abono<input aria-label="Referencia del abono" maxLength={120} className="block w-full bg-dark-800 p-2" value={current.reference} onChange={e => onChange({ ...current, reference: e.target.value, confirmed: false })} /></label>
    <label className="block">Fecha bancaria<input aria-label="Fecha bancaria" type="date" max={bankDay()} className="block bg-dark-800 p-2" value={current.operationDate} onChange={e => onChange({ ...current, operationDate: e.target.value, confirmed: false })} /></label>
    <label className="flex gap-2"><input type="checkbox" checked={current.confirmed} onChange={e => onChange({ ...current, confirmed: e.target.checked })} />Comprobé el abono, importe y cuenta de destino</label>
    {user?.role === "ADMIN" && <button type="button" className="underline" onClick={create}>Registrar cuenta receptora</button>}
  </fieldset>;
}
