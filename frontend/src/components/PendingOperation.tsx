import { useState } from "react";
import api from "../services/api";
import { pendingStorageKey, completeOperation } from "../services/pendingOperation";

export default function PendingOperation({ scope }: { scope: string }) {
  const [message, setMessage] = useState("");
  const [checking, setChecking] = useState(false);
  const operationId = localStorage.getItem(pendingStorageKey(scope));
  if (!operationId) return null;
  const check = async () => {
    try {
      setChecking(true);
      const response = await api.get(`/operations/${scope}/${operationId}`);
      const id = response.data.result?.id;
      const state = response.data.result?.status === "VOIDED" ? " Actualmente ANULADA." : "";
      setMessage(`Operación confirmada${id ? ` #${id}` : ""}.${state} Revise el comprobante antes de iniciar otra.`);
      if (window.confirm(`La operación${id ? ` #${id}` : ""} ya está registrada.${state} ¿Confirma que revisó su resultado y desea cerrar este intento?`)) {
        completeOperation(scope); setMessage("Intento cerrado. La operación registrada se conserva.");
      }
    } catch (error: any) { setMessage(error.response?.data?.message || "Resultado no confirmado. Reintente con los mismos datos."); }
    finally { setChecking(false); }
  };
  return <div role="status" className="my-3 rounded-lg border border-amber-500/40 p-3 text-sm text-amber-200">
    <p>Hay un intento pendiente. Evite registrar otra operación sin comprobar su resultado.</p>
    <button type="button" disabled={checking} onClick={check} className="mt-2 underline disabled:opacity-50">Consultar resultado del intento</button>
    {message && <p className="mt-2">{message}</p>}
  </div>;
}
