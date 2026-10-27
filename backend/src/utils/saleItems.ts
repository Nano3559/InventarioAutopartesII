import { errorDominio } from "../shared/utils/errorDominio";
import { MAX_QUANTITY, SaleMode } from "../shared/utils/pricing";
export interface RawSaleItem { productId?: unknown; quantity?: unknown; priceMode?: unknown; priceTier?: unknown; unitPrice?: unknown; wholesalePrice?: unknown; }
export interface ValidatedSaleItem { productId: number; quantity: number; priceMode: SaleMode; }
/** Importes del cliente ignorados. PRICE1 se admite solo como alias legacy por menor. */
export function validateAndMergeItems(items: RawSaleItem[], forcedMode?: SaleMode): ValidatedSaleItem[] {
  if (!Array.isArray(items) || !items.length) throw errorDominio("Debe enviar al menos un ítem (items)");
  const totals = new Map<number, ValidatedSaleItem>();
  for (const it of items) {
    if (!it || typeof it !== "object") throw errorDominio("Ítem inválido");
    const productId = Number(it.productId), quantity = Number(it.quantity);
    if (typeof it.productId === "boolean" || !Number.isInteger(productId) || productId < 1 || productId > MAX_QUANTITY) throw errorDominio("Cada ítem debe tener un productId válido");
    if (typeof it.quantity === "boolean" || !Number.isInteger(quantity) || quantity < 1 || quantity > MAX_QUANTITY) throw errorDominio(`La cantidad del producto ${productId} debe ser un entero mayor a 0 dentro del límite permitido`);
    if (it.priceTier !== undefined && it.priceTier !== "PRICE1") throw errorDominio("El segundo nivel es legacy. Seleccione POR MENOR o POR MAYOR");
    const priceMode = it.priceMode ?? forcedMode ?? "POR_MENOR";
    if (priceMode !== "POR_MENOR" && priceMode !== "POR_MAYOR") throw errorDominio("Seleccione POR MENOR o POR MAYOR");
    if (forcedMode && priceMode !== forcedMode) throw errorDominio("Este módulo solo admite POR MAYOR");
    if (it.priceTier === "PRICE1" && priceMode !== "POR_MENOR" && !forcedMode) throw errorDominio("El modo y el alias legacy no coinciden");
    const prev = totals.get(productId);
    if (prev) {
      if (prev.priceMode !== priceMode) throw errorDominio("Un producto repetido debe utilizar el mismo modo de venta");
      if (prev.quantity + quantity > MAX_QUANTITY) throw errorDominio("La cantidad acumulada supera el límite permitido");
      prev.quantity += quantity;
    } else totals.set(productId, { productId, quantity, priceMode });
  }
  return [...totals.values()];
}
