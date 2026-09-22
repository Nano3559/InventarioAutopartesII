export type BorradorEntregaVision =
  | { modalidad: "recoger"; sucursalId: number; sucursalNombre: string }
  | { modalidad: "delivery"; sucursalId: number | null; sucursalNombre: string; lugarEntrega: string; paraQuien: string };

export interface BorradorVentaVision {
  origen: "vision";
  creadoEn: string;
  producto: {
    itemCode: string;
    nombre: string;
    cantidad: number;
  };
  entrega: BorradorEntregaVision;
}

const CLAVE = "borrador_venta_vision";

export function guardarBorradorVision(borrador: BorradorVentaVision): void {
  localStorage.setItem(CLAVE, JSON.stringify(borrador));
}

export function leerBorradorVision(): BorradorVentaVision | null {
  try {
    const raw = localStorage.getItem(CLAVE);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      (parsed as Record<string, unknown>).origen !== "vision"
    ) {
      return null;
    }
    return parsed as BorradorVentaVision;
  } catch {
    return null;
  }
}

export function limpiarBorradorVision(): void {
  localStorage.removeItem(CLAVE);
}