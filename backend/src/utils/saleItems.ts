export interface RawSaleItem {
  productId?: unknown;
  quantity?: unknown;
  unitPrice?: unknown;
  wholesalePrice?: unknown;
}

export interface ValidatedSaleItem {
  productId: number;
  quantity: number;
  unitPrice: number;
}

/**
 * Valida y deduplica los ítems de una venta.
 * Combina cantidades del mismo producto (evita sobreventa con ítems repetidos)
 * y rechaza cantidades/precios no positivos. Lanza Error con mensajes claros
 * (los handlers lo convierten en respuesta 400).
 */
export function validateAndMergeItems(items: RawSaleItem[]): ValidatedSaleItem[] {
  if (!Array.isArray(items) || items.length === 0) {
    throw new Error("Debe enviar al menos un ítem (items)");
  }

  const totals = new Map<number, { quantity: number; unitPrice: number }>();
  for (const it of items) {
    const productId = Number(it.productId);
    const quantity = Number(it.quantity);
    const unitPrice = Number(it.unitPrice || it.wholesalePrice || 0);

    if (!Number.isInteger(productId) || productId < 1) {
      throw new Error("Cada ítem debe tener un productId válido");
    }
    if (!Number.isInteger(quantity) || quantity < 1) {
      throw new Error(`La cantidad del producto ${productId} debe ser un entero mayor a 0`);
    }
    if (isNaN(unitPrice) || unitPrice <= 0) {
      throw new Error(`El precio unitario del producto ${productId} debe ser mayor a 0`);
    }

    const prev = totals.get(productId);
    if (prev) {
      prev.quantity += quantity;
    } else {
      totals.set(productId, { quantity, unitPrice });
    }
  }

  return Array.from(totals.entries()).map(([productId, v]) => ({
    productId,
    quantity: v.quantity,
    unitPrice: v.unitPrice,
  }));
}