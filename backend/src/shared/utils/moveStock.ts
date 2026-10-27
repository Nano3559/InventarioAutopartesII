import { incrementStock } from "./stock";
import { Prisma } from "@prisma/client";
import { errorDominio } from "./errorDominio";
import { MAX_QUANTITY } from "./pricing";

export async function moveStock(tx: Prisma.TransactionClient, data: { productId: number; fromLocationId: number; toLocationId: number; quantity: number; userId: number; requestId?: number | null; observation?: string | null }) {
  if (data.fromLocationId === data.toLocationId) throw errorDominio("La ubicación de origen y destino no pueden ser la misma");
  const rows = await tx.$queryRaw<{ id: number; locationId: number; stock: number }[]>`
    SELECT id, "locationId", stock FROM "Inventory"
    WHERE "productId" = ${data.productId} AND "locationId" IN (${data.fromLocationId}, ${data.toLocationId})
    ORDER BY id FOR UPDATE`;
  const origin = rows.find((r) => r.locationId === data.fromLocationId);
  const destination = rows.find((r) => r.locationId === data.toLocationId);
  if (!origin || origin.stock < data.quantity) throw errorDominio(`Stock insuficiente en origen. Disponible: ${origin?.stock || 0}, solicitado: ${data.quantity}`);
  if ((destination?.stock || 0) + data.quantity > MAX_QUANTITY) throw errorDominio("El stock de destino supera el límite permitido");
  await tx.inventory.update({ where: { id: origin.id }, data: { stock: { decrement: data.quantity } } });
  await incrementStock(tx, data.productId, data.toLocationId, data.quantity);
  return tx.movement.create({ data, include: { product: { select: { name: true, itemCode: true } }, fromLocation: { select: { name: true } }, toLocation: { select: { name: true } }, user: { select: { name: true } }, request: { select: { id: true, status: true } } } });
}
