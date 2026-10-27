import { Prisma } from "@prisma/client";
import { MAX_QUANTITY } from "./pricing";
import { errorDominio } from "./errorDominio";

export async function incrementStock(tx: Prisma.TransactionClient, productId: number, locationId: number, quantity: number) {
  if (!Number.isInteger(quantity) || quantity < 1 || quantity > MAX_QUANTITY) throw errorDominio("Cantidad de ingreso inválida");
  const row = await tx.inventory.upsert({ where: { productId_locationId: { productId, locationId } }, create: { productId, locationId, stock: 0, minStock: 1 }, update: {} });
  await tx.$queryRaw`SELECT id FROM "Inventory" WHERE id = ${row.id} FOR UPDATE`;
  const previous = await tx.inventory.findUniqueOrThrow({ where: { id: row.id } });
  if (previous.stock + quantity > MAX_QUANTITY) throw errorDominio("El stock de destino supera el límite permitido");
  const updated = await tx.inventory.update({ where: { id: row.id }, data: { stock: { increment: quantity } } });
  return { previous, updated };
}
