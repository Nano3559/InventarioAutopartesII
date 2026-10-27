import { Prisma } from "@prisma/client";
import { createHash } from "crypto";
import { errorDominio } from "./errorDominio";

/** La misma operación conserva su respuesta. Una nueva operación requiere otra clave. */
export async function idempotentMovement<T>(tx: Prisma.TransactionClient, userId: number, key: string, payload: unknown, execute: () => Promise<T>): Promise<T> {
  if (!/^[\w-]{8,100}$/.test(key)) throw errorDominio("operationId debe tener entre 8 y 100 letras, números o guiones");
  const hash = createHash("sha256").update(JSON.stringify(payload)).digest("hex");
  await tx.$queryRaw`SELECT pg_advisory_xact_lock(hashtextextended(${`movement:${userId}:${key}`}, 0))::text`;
  const previous = await tx.auditLog.findFirst({ where: { action: "MOVEMENT_OPERATION", targetType: "MOVEMENT", userId, newValue: { path: ["operationId"], equals: key } } });
  if (previous) {
    const saved = previous.newValue as any;
    if (saved.hash !== hash) throw errorDominio("operationId ya se utilizó con otros datos. Inicie un nuevo movimiento");
    return saved.result as T;
  }
  const result = await execute();
  await tx.auditLog.create({ data: { userId, action: "MOVEMENT_OPERATION", targetType: "MOVEMENT", newValue: { operationId: key, hash, result: JSON.parse(JSON.stringify(result)) } } });
  return result;
}
