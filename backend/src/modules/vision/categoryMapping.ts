import { coincidenTextos, contienePalabra, normalizarTexto } from "./normalize";

/**
 * Mapeo de clases detectadas por visión (piezas) → categorías del catálogo.
 * Las claves están normalizadas (sin acentos, minúsculas). La clase detectada
 * puede coincidir directamente con una Category.name existente (identidad) o
 * resolverse vía estos sinónimos. No inventa categorías: si no hay equivalente,
 * devuelve null.
 */
export const CATEGORY_MAP: Record<string, string> = {
  "faro": "Carrocería",
  "faro delantero": "Carrocería",
  "faro trasero": "Carrocería",
  "retrovisor": "Carrocería",
  "retrovisores": "Carrocería",
  "parachoques": "Carrocería",
  "parachoque": "Carrocería",
  "paragolpes": "Carrocería",
  "guardabarros": "Carrocería",
  "guardabarros delantero": "Carrocería",
  "capot": "Carrocería",
  "capo": "Carrocería",
  "puerta": "Carrocería",
  "espejo": "Carrocería",
  "parrilla": "Carrocería",
  "radiador": "Motor",
  "radiadores": "Motor",
  "bomba de agua": "Motor",
  "bujia": "Motor",
  "bujias": "Motor",
  "correa de distribucion": "Motor",
  "junta de tapa": "Motor",
  "alternador": "Eléctrico",
  "bateria": "Eléctrico",
  "baterias": "Eléctrico",
  "motor de arranque": "Eléctrico",
  "sensor": "Eléctrico",
  "filtro de aceite": "Filtros",
  "filtro de aire": "Filtros",
  "filtro de combustible": "Filtros",
  "filtro": "Filtros",
  "frenos": "Frenos",
  "freno": "Frenos",
  "pastilla de freno": "Frenos",
  "pastillas de freno": "Frenos",
  "disco de freno": "Frenos",
  "discos de freno": "Frenos",
  "caliper": "Frenos",
  "manguera de freno": "Frenos",
  "amortiguador": "Suspensión",
  "amortiguadores": "Suspensión",
  "brazo de suspension": "Suspensión",
  "embrague": "Transmisión",
  "kit de embrague": "Transmisión",
  "transmision": "Transmisión",
  "reten de transmision": "Transmisión",
};

/**
 * Resuelve una clase detectada por la IA a una categoría EXISTENTE del catálogo.
 * @param categoriasCatálogo nombres reales (Category.name)
 * @param deteccion clase detectada (p. ej. "Faro", "Frenos")
 */
export function mapearCategoria(categoriasCatalogo: string[], deteccion: string): string | null {
  const norm = normalizarTexto(deteccion);
  if (!norm) return null;

  const identica = categoriasCatalogo.find((c) => normalizarTexto(c) === norm);
  if (identica) return identica;

  const claveExacta = Object.keys(CATEGORY_MAP).find((key) => key === norm);
  if (claveExacta) {
    const destino = CATEGORY_MAP[claveExacta];
    const categoria = categoriasCatalogo.find((c) => normalizarTexto(c) === normalizarTexto(destino));
    return categoria ?? null;
  }

  for (const key of Object.keys(CATEGORY_MAP)) {
    if (contienePalabra(norm, key)) {
      const destino = CATEGORY_MAP[key];
      const categoria = categoriasCatalogo.find((c) => normalizarTexto(c) === normalizarTexto(destino));
      if (categoria) return categoria;
    }
  }

  return null;
}

export { coincidenTextos };