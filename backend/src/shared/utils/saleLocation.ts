import { PrismaClient } from "@prisma/client";
import { errorDominio } from "./errorDominio";
import { MAX_QUANTITY } from "./pricing";
export async function saleLocation(prisma: PrismaClient, user: { role: string; locationId?: number | null }, selected: unknown, wholesale = false): Promise<number> {
  const id = user.role === "TIENDA" ? user.locationId : Number(selected);
  if (!id || typeof selected === "boolean" || !Number.isInteger(id) || id < 1 || id > MAX_QUANTITY) throw errorDominio("Seleccione explícitamente una ubicación válida para la venta");
  if (user.role === "TIENDA" && selected !== undefined && Number(selected) !== id) throw errorDominio("No puede vender productos de otra tienda");
  const location = await prisma.location.findUnique({ where: { id } });
  if (!location) throw errorDominio("Ubicación de venta no encontrada");
  if ((!wholesale || user.role === "TIENDA") && location.type !== "TIENDA") throw errorDominio("La venta normal y los usuarios TIENDA requieren una ubicación de tipo TIENDA");
  return id;
}
