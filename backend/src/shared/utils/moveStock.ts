import { incrementStock } from "./stock";
import { Prisma } from "@prisma/client";
import { errorDominio } from "./errorDominio";
import { MAX_QUANTITY } from "./pricing";

export async function moveStock(tx: Prisma.TransactionClient, data: { productId: number; fromLocationId: number; toLocationId: number; quantity: number; userId: number; requestId?: number | null; observation?: string | null }) {
  if (!Number.isInteger(data.quantity) || data.quantity < 1 || data.quantity > MAX_QUANTITY) throw errorDominio("Cantidad de traslado inválida");
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
  return tx.movement.create({ data: { ...data, status: "IN_TRANSIT" }, include: { product: { select: { name: true, itemCode: true } }, fromLocation: { select: { name: true } }, toLocation: { select: { name: true } }, user: { select: { name: true } }, request: { select: { id: true, status: true } } } });
}

export async function receiveMovement(tx: Prisma.TransactionClient, movementId: number, userId: number, quantity?: number) {
  await tx.$queryRaw`SELECT id FROM "Movement" WHERE id = ${movementId} FOR UPDATE`;
  const movement = await tx.movement.findUnique({ where: { id: movementId } });
  if (!movement) throw errorDominio("Traslado no encontrado");
  if (movement.status === "LEGACY") throw errorDominio("El traslado legacy requiere conciliación física. No se modifica su stock automáticamente");
  if (movement.status === "RECEIVED") return movement;
  const remaining = movement.quantity - movement.receivedQuantity;
  const received = quantity ?? remaining;
  if (!Number.isInteger(received) || received < 1 || received > remaining) throw errorDominio("La recepción supera la cantidad pendiente del traslado");
  await incrementStock(tx, movement.productId, movement.toLocationId, received);
  const receivedQuantity = movement.receivedQuantity + received;
  const result = await tx.movement.update({ where: { id: movement.id }, data: {
    receivedQuantity, status: receivedQuantity === movement.quantity ? "RECEIVED" : "IN_TRANSIT",
    receivedAt: receivedQuantity === movement.quantity ? new Date() : null,
  } });
  await tx.auditLog.create({ data: { userId, action: "RECEIVE_MOVEMENT", targetType: "MOVEMENT", targetId: movement.id,
    newValue: { quantity: received, receivedQuantity, locationId: movement.toLocationId } } });
  return result;
}
