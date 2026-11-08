import { Prisma } from "@prisma/client";
import { errorDominio } from "../../shared/utils/errorDominio";
import { incrementStock } from "../../shared/utils/stock";
export async function voidSale(tx: Prisma.TransactionClient, id: number, actorId: number, reason: string, goodsVerified: boolean) {
  if (!goodsVerified) throw errorDominio("Confirme que toda la mercadería sigue en la ubicación original, fue contada y está vendible");
  if (typeof reason !== "string" || reason.trim().length < 10 || reason.length > 500) throw errorDominio("Explique el motivo de anulación entre 10 y 500 caracteres");
  await tx.$queryRaw`SELECT id FROM "Sale" WHERE id = ${id} FOR UPDATE`;
  const sale = await tx.sale.findUnique({ where: { id }, include: { payments: true, returns: true, items: true } });
  if (!sale) throw errorDominio("Venta no encontrada");
  if (sale.status === "VOIDED") return { id, status: sale.status, voidedAt: sale.voidedAt, voidReason: sale.voidReason };
  if (sale.returns.length || sale.payments.some(p => p.method !== "CREDITO" && Number(p.amount) > 0)) throw errorDominio("La venta tiene cobros o devoluciones. Requiere devolución y conciliación, no anulación directa");
  if (!sale.items.length || Math.abs(sale.items.reduce((sum, item) => sum + Number(item.subtotal), 0) - Number(sale.total)) > 0.01) throw errorDominio("La venta histórica tiene detalle o total inconsistente. Requiere conciliación");
  const quantities = new Map<number, number>();
  for (const item of sale.items) {
    if (item.quantity < 1) throw errorDominio("Detalle histórico inválido. Requiere revisión");
    quantities.set(item.productId, (quantities.get(item.productId) || 0) + item.quantity);
  }
  // Misma secuencia de bloqueo que ventas normales: Inventory.id, no productId.
  await tx.$queryRaw(Prisma.sql`SELECT id FROM "Inventory" WHERE "locationId" = ${sale.locationId}
    AND "productId" IN (${Prisma.join([...quantities.keys()])}) ORDER BY id FOR UPDATE`);
  for (const [productId, quantity] of [...quantities].sort(([a], [b]) => a - b)) await incrementStock(tx, productId, sale.locationId, quantity);
  const changed = await tx.sale.update({ where: { id }, data: { status: "VOIDED", voidedAt: new Date(), voidedById: actorId, voidReason: reason.trim() } });
  await tx.auditLog.create({ data: { userId: actorId, action: "VOID_SALE", targetType: "SALE", targetId: id,
    newValue: { reason: changed.voidReason, goodsNeverDeliveredAndVerified: true, locationId: sale.locationId, items: [...quantities].map(([productId, quantity]) => ({ productId, quantity })), totalPreserved: String(sale.total) } } });
  return { id, status: changed.status, voidedAt: changed.voidedAt, voidReason: changed.voidReason };
}
