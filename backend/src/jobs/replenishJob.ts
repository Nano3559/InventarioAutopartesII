import cron from "node-cron";
import { PrismaClient } from "@prisma/client";
import { nextDayAt8 } from "../utils/replenish";

const prisma = new PrismaClient();

// Job diario a las 08:05:
//  1) Activa solicitudes de reposición cuyo expectedDate ya llegó.
//  2) Genera solicitudes automáticas para tiendas cuyo stock quedó por debajo del mínimo.
async function runReplenishCheck() {
  try {
    const now = new Date();

    // 1) Activar solicitudes programadas: PENDIENTE -> RECIBIDO_POR_INVENTARIO
    const due = await prisma.productRequest.findMany({
      where: {
        expectedDate: { lte: now },
        status: "PENDIENTE",
      },
      include: { product: true, location: true, requestedBy: true },
    });

    for (const req of due) {
      await prisma.$transaction(async (tx) => {
        await tx.productRequest.update({
          where: { id: req.id },
          data: { status: "RECIBIDO_POR_INVENTARIO" },
        });

        await tx.requestHistory.create({
          data: {
            requestId: req.id,
            previousStatus: "PENDIENTE",
            newStatus: "RECIBIDO_POR_INVENTARIO",
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
              message: `El producto "${req.product.name}" fue recibido por inventario (solicitud #${req.id} a ${req.location.name}).`,
              type: "INFO",
              linkUrl: "/panel/solicitudes",
            },
          });
        }
      });

      console.log(`[replenish] Solicitud #${req.id} recibida por inventario (${req.product.name})`);
    }

    if (due.length > 0) console.log(`[replenish] ${due.length} solicitudes activadas a las ${now.toISOString()}`);

    // 2) Reposición automática por stock < mínimo en tiendas
    await generateLowStockRequests();
  } catch (err) {
    console.error("[replenish] Error ejecutando job de reposición:", err);
  }
}

// REPO_PRODUCTOS: crea solicitud de reposición cuando una tienda tiene stock < minStock
// y no existe ya una solicitud abierta para el mismo producto/tienda.
async function generateLowStockRequests() {
  const tiendas = await prisma.location.findMany({ where: { type: "TIENDA" } });

  for (const tienda of tiendas) {
    const inventories = await prisma.inventory.findMany({
      where: { locationId: tienda.id },
      include: { product: true },
    });

    for (const inv of inventories) {
      if (inv.minStock > 0 && inv.stock < inv.minStock) {
        const openRequest = await prisma.productRequest.findFirst({
          where: {
            productId: inv.productId,
            locationId: tienda.id,
            status: { in: ["PENDIENTE", "RECIBIDO_POR_INVENTARIO", "PREPARANDO"] },
          },
        });
        if (openRequest) continue;

        const delta = Math.max(1, inv.minStock - inv.stock);

        // Disponibilidad en almacén
        const almacen = await prisma.location.findFirst({ where: { type: "ALMACEN" } });
        if (almacen) {
          const almacenInv = await prisma.inventory.findUnique({
            where: { productId_locationId: { productId: inv.productId, locationId: almacen.id } },
          });
          if (!almacenInv || almacenInv.stock < delta) continue;
        }

        // Quién solicita: un usuario TIENDA de esa ubicación (fallback: admin)
        const tiendaUser = await prisma.user.findFirst({ where: { locationId: tienda.id, role: { name: "TIENDA" } } });
        const requestedBy = tiendaUser ?? (await prisma.user.findFirst({ where: { role: { name: "ADMIN" } } }));
        if (!requestedBy) continue;

        const created = await prisma.productRequest.create({
          data: {
            productId: inv.productId,
            quantity: delta,
            locationId: tienda.id,
            requestedById: requestedBy.id,
            note: "Reposición automática por stock mínimo",
            expectedDate: nextDayAt8(),
            history: {
              create: {
                newStatus: "PENDIENTE",
                userId: requestedBy.id,
                userRole: "AUTOMATICO",
              },
            },
          },
        });

        const inventarioUsers = await prisma.user.findMany({ where: { role: { name: "INVENTARIO" } } });
        for (const u of inventarioUsers) {
          await prisma.notification.create({
            data: {
              userId: u.id,
              title: "Reposición automática por stock mínimo",
              message: `"${inv.product.name}" en ${tienda.name} quedó con stock ${inv.stock} (mínimo ${inv.minStock}). Solicitud #${created.id} generada por ${delta} unidades.`,
              type: "WARNING",
              linkUrl: "/panel/solicitudes",
            },
          });
        }

        if (inventarioUsers.length === 0) {
          await prisma.notification.create({
            data: {
              userId: requestedBy.id,
              title: "Reposición automática por stock mínimo",
              message: `Se generó la solicitud #${created.id} para "${inv.product.name}" en ${tienda.name}.`,
              type: "INFO",
              linkUrl: "/panel/solicitudes",
            },
          });
        }

        console.log(`[replenish] Reposición automática #${created.id} (${inv.product.name} -> ${tienda.name})`);
      }
    }
  }
}

export function startReplenishJob() {
  cron.schedule("5 8 * * *", runReplenishCheck, { timezone: "America/La_Paz" });
  console.log("[replenish] Job de reposición programado (diario 08:05 America/La_Paz)");
}