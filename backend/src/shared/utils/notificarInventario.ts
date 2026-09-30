import { Prisma, PrismaClient } from "@prisma/client";

/**
 * E5/E7 — el flujo de solicitudes debe notificar a INVENTARIO en el MOMENTO en
 * que se crea la solicitud, no solo cuando el job la activa por `expectedDate`.
 * Sin esto, "Solicitar a almacén" desde la tienda quedaba invisible salvo que
 * alguien abriera el módulo de solicitudes.
 *
 * REGLA CRÍTICA: esta función NUNCA propaga un error. Una notificación es un
 * efecto secundario: si falla (FK, red, permiso) no debe tumbar ni la venta ni
 * la solicitud ya creada. Por eso traga la excepción, la registra y devuelve 0.
 */
export async function notificarInventarioSolicitud(
  tx: Prisma.TransactionClient | PrismaClient,
  args: { requestId: number; productName: string; locationName: string; quantity: number; origen: string }
): Promise<number> {
  const { requestId, productName, locationName, quantity, origen } = args;

  try {
    const inventarioUsers = await tx.user.findMany({ where: { role: { name: "INVENTARIO" } }, select: { id: true } });
    if (inventarioUsers.length === 0) return 0;

    await tx.notification.createMany({
      data: inventarioUsers.map((u) => ({
        userId: u.id,
        title: `Nueva solicitud #${requestId}`,
        message: `${origen}: "${productName}" (${quantity} unidades) para ${locationName}. Solicitud #${requestId} pendiente de preparación.`,
        type: "INFO" as const,
        linkUrl: "/panel/solicitudes",
      })),
    });

    return inventarioUsers.length;
  } catch (err) {
    console.error(
      `[notificaciones] No se pudo avisar a INVENTARIO de la solicitud #${requestId}:`,
      err instanceof Error ? err.message : err
    );
    return 0;
  }
}
