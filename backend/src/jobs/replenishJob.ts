import cron from "node-cron";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

// Job diario a las 08:05: activa las solicitudes de reposición cuyo expectedDate ya llegó.
// Marca la solicitud como "PREPARANDO" (el almacén ya puede preparar el pedido) y crea
// una notificación para el encargado de inventario.
async function runReplenishCheck() {
  try {
    const now = new Date();
    const due = await prisma.productRequest.findMany({
      where: {
        expectedDate: { lte: now },
        status: "PENDIENTE",
      },
      include: { product: true, location: true, requestedBy: true },
    });

    for (const req of due) {
      await prisma.$transaction(async (tx) => {
        const updated = await tx.productRequest.update({
          where: { id: req.id },
          data: { status: "PREPARANDO" },
        });

        await tx.requestHistory.create({
          data: {
            requestId: req.id,
            previousStatus: "PENDIENTE",
            newStatus: "PREPARANDO",
            userId: req.requestedById,
            userRole: "AUTOMATICO",
          },
        });

        // Notificar a todos los usuarios del rol INVENTARIO
        const inventarioUsers = await tx.user.findMany({ where: { role: { name: "INVENTARIO" } } });
        for (const u of inventarioUsers) {
          await tx.notification.create({
            data: {
              userId: u.id,
              title: "Reposición disponible",
              message: `El producto "${req.product.name}" ya está disponible para preparar (solicitud #${req.id} a ${req.location.name}).`,
              type: "INFO",
              linkUrl: `/requests/${req.id}`,
            },
          });
        }
      });

      console.log(`[replenish] Solicitud #${req.id} activada (${req.product.name})`);
    }

    if (due.length > 0) console.log(`[replenish] ${due.length} solicitudes activadas a las ${now.toISOString()}`);
  } catch (err) {
    console.error("[replenish] Error ejecutando job de reposición:", err);
  }
}

export function startReplenishJob() {
  cron.schedule("5 8 * * *", runReplenishCheck, { timezone: "America/La_Paz" });
  console.log("[replenish] Job de reposición programado (diario 08:05 America/La_Paz)");
}