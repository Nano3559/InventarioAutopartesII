import { createHash } from "crypto";
import type { Prisma } from "@prisma/client";
import type { Request } from "express";
import { errorDominio } from "./errorDominio";

export function operationKey(req: Request): string | undefined {
  const header = req.get("Idempotency-Key");
  const body = req.body?.operationId;
  if (header && body && header !== body) throw errorDominio("Las identidades de operación no coinciden");
  const key = header ?? body;
  if (key === undefined) return undefined; // Compatibilidad con clientes anteriores.
  if (typeof key !== "string" || !/^[\w-]{8,100}$/.test(key)) throw errorDominio("Identidad de operación inválida");
  return key;
}

function stable(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => [k, stable(v)]));
  return value;
}

/** El resultado y la huella se guardan atómicamente con el cambio comercial. */
export async function replayableOperation<T>(tx: Prisma.TransactionClient, userId: number, scope: string,
  key: string | undefined, payload: unknown, execute: () => Promise<T>): Promise<T> {
  if (!key) return execute();
  const hash = createHash("sha256").update(JSON.stringify(stable(payload))).digest("hex");
  await tx.$queryRaw`SELECT pg_advisory_xact_lock(hashtextextended(${`${scope}:${userId}:${key}`}, 0))::text`;
  const prior = await tx.auditLog.findFirst({ where: { action: "REPLAYABLE_OPERATION", targetType: scope, userId,
    newValue: { path: ["operationId"], equals: key } } });
  if (prior) {
    const saved = prior.newValue as { hash: string; result: T };
    if (saved.hash !== hash) throw errorDominio("La operación ya existe con otros datos. Revise su resultado antes de repetirla");
    return saved.result;
  }
  const result = await execute();
  await tx.auditLog.create({ data: { userId, action: "REPLAYABLE_OPERATION", targetType: scope,
    newValue: JSON.parse(JSON.stringify({ operationId: key, hash, result })) } });
  return result;
}
