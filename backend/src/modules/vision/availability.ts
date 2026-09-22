export type AvailabilityLevel = "DISPONIBLE" | "POCAS_UNIDADES" | "NO_DISPONIBLE";

export interface DisponibilidadView {
  nivel: AvailabilityLevel;
  etiqueta: string;
}

const ETIQUETAS: Record<AvailabilityLevel, string> = {
  DISPONIBLE: "Disponible",
  POCAS_UNIDADES: "Pocas unidades",
  NO_DISPONIBLE: "Consultar disponibilidad",
};

/**
 * Disponibilidad pública segura por umbral (mismo criterio que el catálogo:
 * >10 → Disponible, >0 → Pocas unidades, 0 → Consultar disponibilidad).
 * Nunca expone la cantidad exacta de stock.
 */
export function computeSafeAvailability(stock: number): AvailabilityLevel {
  if (stock > 10) return "DISPONIBLE";
  if (stock > 0) return "POCAS_UNIDADES";
  return "NO_DISPONIBLE";
}

export function availabilityView(stock: number): DisponibilidadView {
  const nivel = computeSafeAvailability(stock);
  return { nivel, etiqueta: ETIQUETAS[nivel] };
}

export interface SucursalDisponibilidad {
  locationId: number;
  nombre: string;
  tipo: string;
  nivel: AvailabilityLevel;
  etiqueta: string;
}

export interface StockPorSucursal {
  locationId: number;
  nombre: string;
  tipo: string;
  stock: number;
}