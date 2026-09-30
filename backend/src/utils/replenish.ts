import type { RequestStatus } from "@prisma/client";

export function nextDayAt8(): Date {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(8, 0, 0, 0);
  return d;
}

/**
 * Estados en los que una solicitud sigue ABIERTA (fuera de PENDIENTE hay tres
 * más). Coincide con la tabla de transiciones de requests.routes.ts: RECIBIDO_POR_TIENDA
 * y CANCELADO son terminales (sin transiciones de salida), todo lo demás sigue vigente.
 *
 * ENTREGADO importa: la mercadería ya salió del almacén pero la tienda todavía no la
 * recibió, así que la reposición de ese producto sigue pendiente. Omitirlo permitía que
 * el job abriera una segunda solicitud para la misma tienda y producto.
 *
 * Es la lista que replica el índice único parcial `ProductRequest_solicitud_abierta_unica`
 * (ver prisma/migrations). Debe mantenerse sincronizada con ese WHERE.
 */
export const REQUEST_STATUS_ACTIVOS: RequestStatus[] = [
  "PENDIENTE",
  "RECIBIDO_POR_INVENTARIO",
  "PREPARANDO",
  "ENTREGADO",
];