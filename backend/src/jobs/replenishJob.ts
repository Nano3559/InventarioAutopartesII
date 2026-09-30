import cron from "node-cron";
import { PrismaClient } from "@prisma/client";
import { nextDayAt8, REQUEST_STATUS_ACTIVOS } from "../utils/replenish";

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
      // La activación es condicional (status = PENDIENTE) DENTRO de la
      // transacción: cierra la ventana TOCTOU entre el findMany de arriba y el
      // update. Si un usuario canceló la solicitud mientras tanto, count = 0 y no
      // se toca nada (antes el job la resucitaba y escribía un historial con
      // previousStatus=PENDIENTE falso).
      const activado = await prisma.$transaction(async (tx) => {
        const { count } = await tx.productRequest.updateMany({
          where: { id: req.id, status: "PENDIENTE" },
          data: { status: "RECIBIDO_POR_INVENTARIO" },
        });
        if (count === 0) return false;

        await tx.requestHistory.create({
          data: {
            requestId: req.id,
            previousStatus: "PENDIENTE",
            newStatus: "RECIBIDO_POR_INVENTARIO",
            userId: req.requestedById,
            userRole: "AUTOMATICO",
          },
        });
        return true;
      });

      if (!activado) {
        console.log(`[replenish] Solicitud #${req.id} ya no estaba PENDIENTE: se omite la activación`);
        continue;
      }

      // Notificar a INVENTARIO FUERA de la transacción: la notificación es un
      // efecto secundario y un fallo suyo no debe hacer rollback de la
      // activación (dejaba la solicitud en PENDIENTE para siempre).
      try {
        const inventarioUsers = await prisma.user.findMany({
          where: { role: { name: "INVENTARIO" } },
          select: { id: true },
        });
        if (inventarioUsers.length > 0) {
          await prisma.notification.createMany({
            data: inventarioUsers.map((u) => ({
              userId: u.id,
              title: "Reposición disponible",
              message: `El producto "${req.product.name}" fue recibido por inventario (solicitud #${req.id} a ${req.location.name}).`,
              type: "INFO" as const,
              linkUrl: "/panel/solicitudes",
            })),
          });
        } else {
          await prisma.notification.create({
            data: {
              userId: req.requestedById,
              title: "Reposición disponible",
              message: `El producto "${req.product.name}" fue recibido por inventario (solicitud #${req.id} a ${req.location.name}).`,
              type: "INFO",
              linkUrl: "/panel/solicitudes",
            },
          });
        }
      } catch (notifErr) {
        console.error(`[replenish] No se pudo avisar a INVENTARIO de la solicitud #${req.id}:`, notifErr);
      }

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
// Se exporta para poder ejercitar el job real desde los tests de concurrencia.
export async function generateLowStockRequests() {
  const tiendas = await prisma.location.findMany({ where: { type: "TIENDA" } });

  for (const tienda of tiendas) {
    const inventories = await prisma.inventory.findMany({
      where: { locationId: tienda.id },
      include: { product: true },
    });

    for (const inv of inventories) {
      if (inv.minStock > 0 && inv.stock < inv.minStock) {
        //(delta aproximado, solo para decidir si hay stock en almacén; la cantidad
        // definitiva se recalcula sobre la fila bloqueada dentro de la transacción)

        // Disponibilidad en almacén: se suma el stock de TODOS los almacenes.
        // Con findFirst la reposición se descartaba (continue) si el almacén
        // arbitrario no tenía stock aunque otro sí lo tuviera.
        const inventariosAlmacen = await prisma.inventory.findMany({
          where: { productId: inv.productId, location: { type: "ALMACEN" } },
          select: { stock: true },
        });
        if (inventariosAlmacen.length === 0) continue;
        const stockEnAlmacenes = inventariosAlmacen.reduce((sum, a) => sum + a.stock, 0);
        if (stockEnAlmacenes < 1) continue;

        // Quién solicita: un usuario TIENDA de esa ubicación (fallback: admin)
        const tiendaUser = await prisma.user.findFirst({ where: { locationId: tienda.id, role: { name: "TIENDA" } } });
        const requestedBy = tiendaUser ?? (await prisma.user.findFirst({ where: { role: { name: "ADMIN" } } }));
        if (!requestedBy) continue;

        // Chequeo de duplicado + creación, todo dentro de UNA transacción y con
        // bloqueo de fila (FOR UPDATE) sobre el inventario de esa tienda. El
        // findFirst y el create sueltos eran un TOCTOU: dos corridas del job
        // (o dos procesos) podían ver "sin solicitud abierta" a la vez y crear dos
        // solicitudes idénticas. El lock serializa a los que compiten por la misma
        // fila de inventario; el índice único parcial es la red de seguridad final.
        let created: { id: number; quantity: number; stock: number; minStock: number } | null = null;
        try {
          created = await prisma.$transaction(
            async (tx) => {
              const locked = await tx.$queryRaw<{ id: number; stock: number; minStock: number }[]>`
                SELECT id, stock, "minStock" FROM "Inventory"
                WHERE "productId" = ${inv.productId} AND "locationId" = ${tienda.id}
                ORDER BY id FOR UPDATE`;
              const fila = locked[0];

              // El stock pudo cambiar mientras esperábamos el lock (una venta concurrente):
              // si ya no está bajo el mínimo, no hay nada que reponer.
              if (!fila || fila.minStock <= 0 || fila.stock >= fila.minStock) return null;

              const openRequest = await tx.productRequest.findFirst({
                where: {
                  productId: inv.productId,
                  locationId: tienda.id,
                  status: { in: REQUEST_STATUS_ACTIVOS },
                },
              });
              if (openRequest) return null;

              // La cantidad se calcula SOBRE LA FILA BLOQUEADA, no con la lectura previa
              // al lock: si una venta concurrente bajó el stock, pedir la cantidad vieja
              // dejaría la reposición corta.
              const cantidad = Math.max(1, fila.minStock - fila.stock);

              return tx.productRequest.create({
                data: {
                  productId: inv.productId,
                  quantity: cantidad,
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
                select: { id: true, quantity: true },
              }).then((r) => ({
                id: r.id,
                quantity: r.quantity,
                stock: fila.stock,
                minStock: fila.minStock,
              }));
            },
            // La venta toma los mismos locks de Inventory con timeout 20000: si el job
            // usa el default de 5 s expiraría con P2028 mientras espera. Se alinean los
            // dos timeouts para que la contención se resuelva esperando, no por timeout.
            { timeout: 20000, maxWait: 10000 }
          );
        } catch (err: any) {
          const code = err?.code;
          // P2002: otra corrida ganó la carrera. El índice único parcial es la garantía
          // final y este es el resultado correcto, no un fallo del job.
          if (code === "P2002") {
            console.log(
              `[replenish] Ya existe una solicitud abierta para ${inv.productId} en ${tienda.name} (carrera resuelta por índice único)`
            );
            continue;
          }
          // P2028 (timeout) / P2034 (write conflict) / P2024 (pool de conexiones
          // agotado): contención puntual con una venta o con el resto del sistema. Se
          // salta SOLO este producto; abortar la corrida entera dejaría sin revisar
          // todas las tiendas y productos restantes.
          if (code === "P2028" || code === "P2034" || code === "P2024") {
            console.warn(
              `[replenish] Contención al bloquear el inventario de ${inv.productId} en ${tienda.name} (${code}): se reintenta en la próxima corrida`
            );
            continue;
          }
          throw err;
        }

        if (!created) continue;

        // Aviso a INVENTARIO: efecto secundario. Un fallo aquí no debe abortar el
        // resto del job ni las solicitudes ya creadas.
        try {
          const inventarioUsers = await prisma.user.findMany({ where: { role: { name: "INVENTARIO" } }, select: { id: true } });
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
          } else {
            await prisma.notification.createMany({
              data: inventarioUsers.map((u) => ({
                userId: u.id,
                title: "Reposición automática por stock mínimo",
                message: `"${inv.product.name}" en ${tienda.name} quedó con stock ${created.stock} (mínimo ${created.minStock}). Solicitud #${created.id} generada por ${created.quantity} unidades.`,
                type: "WARNING" as const,
                linkUrl: "/panel/solicitudes",
              })),
            });
          }
        } catch (notifErr) {
          console.error(`[replenish] No se pudo avisar a INVENTARIO de la solicitud #${created.id}:`, notifErr);
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