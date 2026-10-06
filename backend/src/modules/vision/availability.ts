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

/**
 * Disponibilidad POR SUCURSAL del contrato PÚBLICO (recogida). Es el equivalente
 * mínimo y seguro del desglose interno: nombre de la sucursal + bucket de
 * disponibilidad. JAMÁS lleva stock, `locationId`, `tipo` ni `etiqueta`.
 */
export interface SucursalDisponiblePublica {
  sucursalId: number;
  nombre: string;
  nivel: AvailabilityLevel;
}

/** Convierte un inventario a su bucket público de recogida (sin stock). */
export function sucursalDisponiblePublica(sucursalId: number, nombre: string, stock: number): SucursalDisponiblePublica {
  const { nivel } = availabilityView(stock);
  return { sucursalId, nombre, nivel };
}

export interface StockPorSucursal {
  locationId: number;
  nombre: string;
  tipo: string;
  stock: number;
}