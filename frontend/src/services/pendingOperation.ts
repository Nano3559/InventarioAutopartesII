/** Conserva solo la identidad del intento, nunca cliente, importe ni carrito. */
export function pendingStorageKey(scope: string): string {
  let id = "session";
  try { id = String(JSON.parse(localStorage.getItem("user") || "null")?.id ?? id); } catch { /* sesión aún no recuperada */ }
  return `repuestopro:pending:${id}:${scope}`;
}
export function pendingOperationId(scope: string): string {
  const key = pendingStorageKey(scope);
  const saved = localStorage.getItem(key);
  if (saved) return saved;
  // randomUUID requiere contexto seguro. getRandomValues también funciona en
  // instalaciones de desarrollo por IP de la red local.
  const id = typeof crypto.randomUUID === "function" ? crypto.randomUUID() :
    Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, "0")).join("");
  localStorage.setItem(key, id);
  return id;
}
export function completeOperation(scope: string) { localStorage.removeItem(pendingStorageKey(scope)); }
