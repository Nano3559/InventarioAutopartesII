/** Dos modos comerciales. El backend confirma el precio del catálogo. */
export interface ProductoConPrecios { price1: number | string; price2?: number | string | null; wholesalePrice?: number | string | null; }
export type PriceTier = "POR_MENOR" | "POR_MAYOR";
export function precioVentaNormal(producto: ProductoConPrecios, tier: PriceTier = "POR_MENOR"): number {
  const price = Number(tier === "POR_MENOR" ? producto.price1 : producto.wholesalePrice);
  if (!Number.isFinite(price) || price <= 0) throw new Error("Precio de venta no configurado");
  if (tier === "POR_MAYOR" && price > Number(producto.price1)) throw new Error("POR MAYOR supera POR MENOR");
  return Math.round((price + Number.EPSILON) * 100) / 100;
}
export function subtotalLinea(producto: ProductoConPrecios, cantidad: number, tier: PriceTier = "POR_MENOR"): number {
  return Math.round(precioVentaNormal(producto, tier) * cantidad * 100) / 100;
}
export function totalCarrito(lineas: Array<{ producto: ProductoConPrecios; cantidad: number; priceMode?: PriceTier }>): number {
  return Number(lineas.reduce((sum, l) => sum + subtotalLinea(l.producto, l.cantidad, l.priceMode), 0).toFixed(2));
}
