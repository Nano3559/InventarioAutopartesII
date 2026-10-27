import { Prisma } from "@prisma/client";
import { errorDominio } from "./errorDominio";

export async function saleCustomer(tx: Prisma.TransactionClient, customerId: unknown, data: unknown): Promise<number | null> {
  if (customerId != null) {
    const customer = await tx.customer.findUnique({ where: { id: Number(customerId) } });
    if (!customer) throw errorDominio("Cliente no encontrado");
    return customer.id;
  }
  if (data == null) return null;
  if (typeof data !== "object" || !("name" in data) || typeof data.name !== "string" || !data.name.trim()) throw errorDominio("El nombre del cliente es obligatorio");
  const value = data as { name: string; nit?: string | null; phone?: string | null };
  const name = value.name.trim();
  const nit = value.nit?.trim() || null;
  const phone = value.phone?.trim() || null;
  const created = nit
    ? await tx.customer.upsert({ where: { nit }, update: { nit }, create: { name, nit, phone } })
    : await tx.customer.create({ data: { name, phone } });
  return created.id;
}
