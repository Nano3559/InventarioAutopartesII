import { incrementStock } from "./stock";
import { Prisma } from "@prisma/client";
import { money, validatePriceConfiguration, MAX_QUANTITY } from "./pricing";
import { errorDominio } from "./errorDominio";

export function landedCost(unitCost: number, exchangeRate: number, percentage: number): number {
  if (!Number.isFinite(unitCost) || unitCost <= 0 || !Number.isFinite(exchangeRate) || exchangeRate <= 0 || !Number.isFinite(percentage) || percentage < 0 || percentage > 100) throw errorDominio("Tipo de cambio o porcentaje inválido");
  return money(unitCost * exchangeRate * (1 + percentage / 100), "Costo puesto aquí");
}

export async function syncProductCost(tx: Prisma.TransactionClient, productId: number) {
  await tx.$queryRaw`SELECT id FROM "Product" WHERE id = ${productId} FOR UPDATE`;
  const product = await tx.product.findUniqueOrThrow({ where: { id: productId } });
  const latest = await tx.cost.findFirst({ where: { productId }, orderBy: [{ date: "desc" }, { id: "desc" }] });
  const cost = latest?.costPrice ?? null;
  validatePriceConfiguration({ ...product, cost });
  return tx.product.update({ where: { id: productId }, data: { cost } });
}

export async function receivePurchase(tx: Prisma.TransactionClient, productId: number, locationId: number, quantity: number, userId: number, costId: number) {
  if (!Number.isInteger(quantity) || quantity < 1 || quantity > MAX_QUANTITY) throw errorDominio("Cantidad de compra inválida");
  if (!await tx.location.findUnique({ where: { id: locationId } })) throw errorDominio("Ubicación de ingreso no encontrada");
  const { previous: current, updated } = await incrementStock(tx, productId, locationId, quantity);
  await tx.auditLog.create({ data: { userId, action: "RECEIVE_PURCHASE", targetType: "INVENTORY", targetId: updated.id, oldValue: { stock: current.stock }, newValue: { stock: current.stock + quantity, quantity, costId } } });
}
