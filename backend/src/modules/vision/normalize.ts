export function normalizarTexto(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim()
    .replace(/\s+/g, " ");
}

export function tokensDe(value: string): Set<string> {
  return new Set(normalizarTexto(value).split(/[\s/\\\-_,.]+/).filter((t) => t.length >= 2));
}

export function coincidenTextos(a: string, b: string): boolean {
  const na = normalizarTexto(a);
  const nb = normalizarTexto(b);
  if (!na || !nb) return false;
  if (na === nb) return true;
  if (na.includes(nb) || nb.includes(na)) return true;
  const ta = tokensDe(na);
  const tb = tokensDe(nb);
  for (const t of ta) if (tb.has(t)) return true;
  return false;
}

export function contienePalabra(contenedor: string, palabra: string): boolean {
  const esc = palabra.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|\\s)${esc}($|\\s)`).test(normalizarTexto(contenedor));
}