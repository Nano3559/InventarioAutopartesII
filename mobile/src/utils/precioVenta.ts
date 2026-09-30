/**
 * Regla de precio de venta minorista.
 *
 * El backend es la autoridad: `backend/src/modules/sales/sales.routes.ts` calcula
 * `price2 > 0 ? price2 : price1` y DESPUÉS valida que el importe pagado por el
 * cliente coincida con ese total (tolerancia Bs. 0.01). Si el móvil manda un
 * total calculado con otra regla, el backend responde 400 y la venta no se registra.
 *
 * `price1` es el precio mayorista y `price2` el minorista, por eso una venta al
 * público debe cobrar `price2`. Se replica aquí la misma regla que usa
 * `frontend/src/pages/SalesPage.tsx` para que móvil y web no diverjan.
 *
 * La venta MAYORISTA usa otra regla (`wholesalePrice ?? price1`) y se registra en
 * `/wholesale`, no aquí: esta pantalla solo crea ventas normales.
 */

export interface ProductoConPrecios {
  price1: number | string;
  price2?: number | string | null;
}

/** Precio minorista autoritativo. `price2` si está definido y es mayor que cero; si no, `price1`. */
export function precioVentaNormal(producto: ProductoConPrecios): number {
  const price2 = Number(producto.price2);
  if (Number.isFinite(price2) && price2 > 0) return price2;
  return Number(producto.price1);
}

/** Subtotal de una línea del carrito, con el precio minorista autoritativo. */
export function subtotalLinea(producto: ProductoConPrecios, cantidad: number): number {
  return precioVentaNormal(producto) * cantidad;
}

/** Total del carrito, redondeado a 2 decimales como espera la validación del backend. */
export function totalCarrito(lineas: Array<{ producto: ProductoConPrecios; cantidad: number }>): number {
  const total = lineas.reduce((sum, linea) => sum + subtotalLinea(linea.producto, linea.cantidad), 0);
  return Number(total.toFixed(2));
}
