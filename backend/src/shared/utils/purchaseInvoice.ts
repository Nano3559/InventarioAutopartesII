import type { Prisma } from "@prisma/client";
import { createHash } from "crypto";
import { errorDominio } from "./errorDominio";
export function invoiceIdentity(value: unknown): string {
  if (typeof value !== "string" || value.trim().length < 3 || value.trim().length > 160) throw errorDominio("Registre el identificador completo de factura, con serie y autorización cuando existan (3 a 160 caracteres)");
  return value.normalize("NFKC").trim().replace(/\s+/g, " ").toUpperCase();
}
function stable(value: any): any {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map(k => [k, stable(value[k])]));
  return value;
}
export async function registerInvoice<T>(tx: Prisma.TransactionClient, supplierId: number, identity: unknown, payload: unknown, execute: (invoiceId: number) => Promise<T>): Promise<T> {
  const identityKey = invoiceIdentity(identity);
  const contentHash = createHash("sha256").update(JSON.stringify(stable(payload))).digest("hex");
  await tx.$queryRaw`SELECT pg_advisory_xact_lock(hashtextextended(${`invoice-identity:${supplierId}:${identityKey}`}, 0))::text`;
  const previous = await tx.purchaseInvoice.findUnique({ where: { supplierId_identityKey: { supplierId, identityKey } } });
  if (previous) {
    if (previous.contentHash !== contentHash) throw errorDominio("Esta factura ya está registrada con otro contenido o destino. Revise el comprobante, no vuelva a ingresar stock");
    return { ...(previous.result as object), replayed: true } as T;
  }
  const record = await tx.purchaseInvoice.create({ data: { supplierId, identityKey, documentIdentity: String(identity).trim(), contentHash, result: {} } });
  const result = await execute(record.id);
  await tx.purchaseInvoice.update({ where: { id: record.id }, data: { result: JSON.parse(JSON.stringify(result)) } });
  return result;
}
