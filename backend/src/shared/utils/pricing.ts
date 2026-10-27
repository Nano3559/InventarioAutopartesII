import { errorDominio } from "./errorDominio";
export type PriceTier = "PRICE1" | "PRICE2";
export type SaleMode = "POR_MENOR" | "POR_MAYOR";
export const MAX_QUANTITY = 2_147_483_647;
export const MAX_MONEY = 1_000_000_000;
export function money(value: unknown, name: string, allowZero = false): number {
  if ((typeof value !== "number" && typeof value !== "string") || String(value).trim() === "") throw errorDominio(`${name} debe ser un número válido`);
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0 || (!allowZero && n === 0) || n > MAX_MONEY) throw errorDominio(`${name} debe ser ${allowZero ? "mayor o igual a" : "mayor que"} 0 y no superar ${MAX_MONEY}`);
  const rounded = Math.round((n + Number.EPSILON) * 100) / 100;
  if (!allowZero && rounded === 0) throw errorDominio(`${name} debe ser al menos 0.01`);
  return rounded;
}
export interface ProductPrices { price1: unknown; price2: unknown; wholesalePrice?: unknown; cost?: unknown; }
function priceValue(value: unknown): unknown { return value !== null && typeof value === "object" ? String(value) : value; }
export function validatePriceConfiguration(p: ProductPrices): void {
  const p1 = money(priceValue(p.price1), "Precio por menor");
  const cost = p.cost == null ? 0 : money(priceValue(p.cost), "Costo", true);
  if (p1 < cost) throw errorDominio("El precio por menor no puede ser inferior al costo");
  if (p.wholesalePrice != null) {
    const wholesale = money(priceValue(p.wholesalePrice), "Precio por mayor");
    if (wholesale < cost) throw errorDominio("El precio por mayor no puede ser inferior al costo");
    if (wholesale > p1) throw errorDominio("El precio por mayor no puede superar el precio por menor");
  }
}
export function salePrice(p: ProductPrices, tier: SaleMode | PriceTier | "WHOLESALE"): number {
  if (tier === "PRICE2") throw errorDominio("El segundo nivel es legacy. Seleccione POR MENOR o POR MAYOR");
  if (tier === "WHOLESALE" || tier === "POR_MAYOR") {
    if (p.wholesalePrice == null) throw errorDominio("Configure el precio por mayor antes de registrar esta venta");
    validatePriceConfiguration(p);
  }
  const price = money(priceValue(tier === "WHOLESALE" || tier === "POR_MAYOR" ? p.wholesalePrice : p.price1), "Precio de venta");
  if (p.cost != null && price < money(priceValue(p.cost), "Costo", true)) throw errorDominio("El precio de venta no puede ser inferior al costo");
  return price;
}
export function lineSubtotal(quantity: number, price: number): number { return money(quantity * price, "Subtotal"); }
export function validatePayments(payments: unknown): Array<{ method: "EFECTIVO" | "QR" | "TRANSFERENCIA" | "CREDITO"; amount: number }> {
  if (!Array.isArray(payments) || !payments.length) throw errorDominio("Debe registrar al menos un pago");
  const methods = ["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"] as const;
  return payments.map((p) => {
    if (!p || !methods.includes(p.method)) throw errorDominio("Método de pago inválido");
    return { method: p.method, amount: money(p.amount, "Monto de pago", true) };
  });
}
