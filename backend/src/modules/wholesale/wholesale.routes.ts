import { Router, Response } from "express";
import { Prisma, PrismaClient } from "@prisma/client";
import { isPrismaClientError } from "../../shared/utils/errors";
import { parsePagination } from "../../shared/utils/pagination";
import { rangoFechasNegocio } from "../../shared/utils/rangoFechas";
import * as XLSX from "xlsx";
import { authenticate, authorize, requireTiendaLocation } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import { nextDayAt8, REQUEST_STATUS_ACTIVOS } from "../../utils/replenish";
import { validateAndMergeItems } from "../../utils/saleItems";
import { excelUpload } from "../../shared/utils/upload";
import { notificarInventarioSolicitud } from "../../shared/utils/notificarInventario";
import { esErrorDominio, errorDominio } from "../../shared/utils/errorDominio";

const router = Router();
const prisma = new PrismaClient();
const upload = excelUpload;

router.use(authenticate);
router.use(requireTiendaLocation);
router.use(authorize("ADMIN", "TIENDA"));

// POST — Crear venta mayorista
router.post("/", async (req: AuthRequest, res: Response) => {
  try {
    const { items, payments, customerId, customerData, locationId, clienteName, paraQuien, lugarEntrega, datosFactura, formaPago } = req.body;

    if (!items || !Array.isArray(items) || items.length === 0) {
      return res.status(400).json({ message: "Debe agregar al menos un producto" });
    }

    if (!payments || !Array.isArray(payments) || payments.length === 0) {
      return res.status(400).json({ message: "Debe registrar al menos un pago" });
    }

    const user = req.user!;
    let userLocationId: number | null = null;

    if (user.role === "TIENDA") {
      userLocationId = user.locationId ?? null;
      if (!userLocationId) {
        return res.status(400).json({ message: "Usuario TIENDA sin ubicación asignada" });
      }
      if (locationId && Number(locationId) !== userLocationId) {
        return res.status(403).json({ message: "No puede vender productos de otra tienda" });
      }
    } else {
      userLocationId = locationId ? Number(locationId) : user.locationId || null;
    }

    if (!userLocationId) {
      const tienda = await prisma.location.findFirst({ where: { type: "TIENDA" } });
      if (!tienda) {
        return res.status(400).json({ message: "No hay tiendas configuradas en el sistema" });
      }
      userLocationId = tienda.id;
    }

    const validMethods = ["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"];
    for (const p of payments) {
      if (!validMethods.includes(p.method)) {
        return res.status(400).json({ message: `Método de pago inválido: ${p.method}` });
      }
      const amount = Number(p.amount);
      if (!Number.isFinite(amount) || amount < 0) {
        return res.status(400).json({ message: "El monto de pago debe ser un número mayor o igual a 0" });
      }
    }

    // Validar, deduplicar y resolver precio unitario de los ítems
    const validItems = validateAndMergeItems(items);

    // Datos de entrega: usar los enviados explícitamente o inferir del payload
    const entregaParaQuien = paraQuien || clienteName || null;
    const entregaLugar = lugarEntrega || null;
    const entregaFactura = datosFactura || (customerData?.nit ? `NIT/CI: ${customerData.nit}` : null);
    const entregaFormaPago = formaPago || (payments.length > 0 ? payments[0].method : null);

    // Se acumulan aquí y se notifica DESPUÉS del commit (ver más abajo): una
    // notificación es un efecto secundario y no puede abortar una venta válida.
    const notificaciones: {
      requestId: number;
      productName: string;
      locationName: string;
      quantity: number;
      origen: string;
    }[] = [];

    // Reposición automática "la venta agotó el stock": se registra dentro de la
    // transacción y se CREA tras el commit. Así una carrera con otra creación (P2002 del
    // índice parcial ProductRequest_solicitud_abierta_unica) no aborta la venta con 500.
    const reposicionesPendientes: {
      productId: number;
      quantity: number;
      locationId: number;
      requestedById: number;
    }[] = [];

    const result = await prisma.$transaction(async (tx) => {
      let finalCustomerId = customerId || null;

      if (customerData && !finalCustomerId) {
        const { name, nit, phone } = customerData;
        if (name) {
          let customer;
          if (nit) {
            customer = await tx.customer.findFirst({ where: { nit } });
          }
          if (!customer) {
            customer = await tx.customer.create({
              data: { name, nit: nit || null, phone: phone || null },
            });
          }
          finalCustomerId = customer.id;
        }
      }
      // R4: bloqueo de fila pesimista (FOR UPDATE) sobre el inventario antes de validar y
      // descontar (misma mecánica que movements). Todas las filas se bloquean en un único
      // query con ORDER BY id: locks en orden determinista y sin ventana entre bloqueos, por
      // lo que dos ventas mayoristas concurrentes no pueden deadlock. Validación y descuento
      // dentro de la misma transacción.
      const orderedItems = [...validItems].sort((a, b) => a.productId - b.productId);
      const productIds = orderedItems.map((i) => i.productId);
      const products = await tx.product.findMany({ where: { id: { in: productIds } } });
      const productById = new Map(products.map((p) => [p.id, p]));

      const tuples = orderedItems.map((item) => Prisma.sql`(${item.productId}, ${userLocationId})`);
      const lockedRows = await tx.$queryRaw<{ id: number; stock: number; productId: number }[]>`
        SELECT id, stock, "productId" FROM "Inventory"
        WHERE ("productId", "locationId") IN (${Prisma.join(tuples)})
        ORDER BY id FOR UPDATE`;
      const lockedStock = new Map(lockedRows.map((r) => [r.productId, { id: r.id, stock: r.stock }]));

      for (const item of orderedItems) {
        const product = productById.get(item.productId);
        if (!product) {
          throw errorDominio(`Producto con ID ${item.productId} no encontrado`);
        }

        const locked = lockedStock.get(item.productId);
        const currentStock = locked ? locked.stock : 0;
        if (currentStock < item.quantity) {
          throw errorDominio(`Stock insuficiente para "${product.name}". Disponible: ${currentStock}, solicitado: ${item.quantity}`);
        }
      }

      let totalSale = 0;
      const saleItemsData = orderedItems.map((item) => {
        const product = productById.get(item.productId)!;
        const unitPrice = Number(product.wholesalePrice ?? product.price1);
        if (!Number.isFinite(unitPrice) || unitPrice <= 0) {
          throw errorDominio(`El producto "${product.name}" no tiene un precio de venta por mayor definido`);
        }
        const subtotal = item.quantity * unitPrice;
        totalSale += subtotal;
        return {
          productId: item.productId,
          quantity: item.quantity,
          unitPrice,
          subtotal,
        };
      });

      const totalPaid = payments.reduce((sum: number, p: any) => sum + Number(p.amount), 0);
      if (Math.abs(totalPaid - totalSale) > 0.01) {
        throw errorDominio(`El total pagado (Bs. ${totalPaid}) no coincide con el total de la venta (Bs. ${totalSale})`);
      }

      const sale = await tx.sale.create({
        data: {
          total: totalSale,
          type: "MAYOR",
          userId: user.userId,
          locationId: userLocationId,
          customerId: finalCustomerId,
          paraQuien: entregaParaQuien,
          lugarEntrega: entregaLugar,
          datosFactura: entregaFactura,
          formaPago: entregaFormaPago,
          items: { create: saleItemsData },
          payments: {
            create: payments.map((p: any) => ({
              method: p.method,
              amount: Number(p.amount),
            })),
          },
        },
        include: { items: true, payments: true },
      });

      for (const item of validItems) {
        const locked = lockedStock.get(item.productId);
        if (locked) {
          const newStock = locked.stock - item.quantity;
          await tx.inventory.update({
            where: { id: locked.id },
            data: { stock: { decrement: item.quantity } },
          });

          if (newStock === 0) {
            const existing = await tx.productRequest.findFirst({
              where: {
                productId: item.productId,
                locationId: userLocationId,
                // REQUEST_STATUS_ACTIVOS incluye ENTREGADO (mercadería ya entregada pero
                // aún no recibida por la tienda). Con la lista sin ENTREGADO, el
                // findFirst no la encontraba y la venta intentaba abrir una segunda
                // solicitud, que el índice parcial ProductRequest_solicitud_abierta_unica
                // rechaza y abortaba toda la venta con 500.
                status: { in: REQUEST_STATUS_ACTIVOS },
              },
            });
            if (!existing) {
              // Mismo criterio que en venta NORMAL: se suma el stock de TODOS los
              // almacenes. Con findFirst la reposición dependía de un almacén
              // arbitrario y se perdía si el stock estaba repartido.
              const inventariosAlmacen = await tx.inventory.findMany({
                where: { productId: item.productId, location: { type: "ALMACEN" } },
                select: { stock: true },
              });
              const stockEnAlmacenes = inventariosAlmacen.reduce((sum, a) => sum + a.stock, 0);
              const requestQty = Math.max(item.quantity, 5);
              if (inventariosAlmacen.length > 0 && stockEnAlmacenes >= requestQty) {
                // Se registra aquí pero se crea tras el commit (ver reposicionesPendientes).
                reposicionesPendientes.push({
                  productId: item.productId,
                  quantity: requestQty,
                  locationId: userLocationId,
                  requestedById: user.userId,
                });
              }
            }
          }
        }
      }

      return {
        ...sale,
        total: Number(sale.total),
        items: sale.items.map((i) => ({ ...i, unitPrice: Number(i.unitPrice), subtotal: Number(i.subtotal) })),
        payments: sale.payments.map((p) => ({ ...p, amount: Number(p.amount) })),
      };
    }, { timeout: 20000 });

    // Reposición automática DESPUÉS del commit: la venta ya está confirmada, así que un
    // P2002 (carrera con otra creación simultánea) solo significa "ya había una solicitud
    // abierta" y se ignora con un log. Nunca responde 500 por la reposición.
    for (const reposicion of reposicionesPendientes) {
      try {
        const created = await prisma.productRequest.create({
          data: {
            productId: reposicion.productId,
            quantity: reposicion.quantity,
            requestedById: reposicion.requestedById,
            locationId: reposicion.locationId,
            status: "PENDIENTE",
            expectedDate: nextDayAt8(),
            // Trazabilidad: el job y la ruta manual también registran origen e historial,
            // así que sin esto esta vía era indistinguible de una solicitud manual y
            // llegaba con history: [].
            note: "Reposición automática (la venta mayorista agotó el stock)",
            history: {
              create: {
                newStatus: "PENDIENTE",
                userId: reposicion.requestedById,
                userRole: user.role,
              },
            },
          },
        });
        notificaciones.push({
          requestId: created.id,
          productName:
            (await prisma.product.findUnique({ where: { id: reposicion.productId }, select: { name: true } }))?.name ??
            `Producto #${reposicion.productId}`,
          locationName:
            (await prisma.location.findUnique({ where: { id: reposicion.locationId }, select: { name: true } }))?.name ??
            `Ubicación #${reposicion.locationId}`,
          quantity: reposicion.quantity,
          origen: "Reposición automática (venta mayorista agotó el stock)",
        });
      } catch (err: any) {
        if (err?.code === "P2002") {
          console.log(
            `[wholesale] Ya existe una solicitud abierta para el producto ${reposicion.productId} en la ubicación ${reposicion.locationId}: no se duplica`
          );
          continue;
        }
        console.error(`[wholesale] No se pudo crear la reposición del producto ${reposicion.productId}:`, err);
      }
    }

    // Notificar fuera de la transacción: si la notificación falla, la venta ya está
    // confirmada y se responde 201 (el helper tampoco propaga errores).
    for (const notificacion of notificaciones) {
      await notificarInventarioSolicitud(prisma, notificacion);
    }

    res.status(201).json(result);
  } catch (error: any) {
    // Solo los rechazos de negocio conocidos (ErrorDominio) responden 400 con su
    // mensaje. Cualquier otro fallo (Prisma, fs, TypeError) se registra y responde
    // 500 genérico, en vez de filtrar error.message con un 400 engañoso.
    if (esErrorDominio(error)) {
      return res.status(400).json({ message: error.message });
    }
    console.error("Error al crear venta mayorista:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST /import — Importar productos desde Excel
router.post("/import", authorize("ADMIN"), upload.single("file"), async (req: AuthRequest, res: Response) => {
  try {
    if (!req.file) {
      return res.status(400).json({ message: "Debe subir un archivo Excel" });
    }

    const workbook = XLSX.read(req.file.buffer, { type: "buffer" });
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    const rows = XLSX.utils.sheet_to_json(sheet);

    if (rows.length === 0) {
      return res.status(400).json({ message: "El archivo está vacío" });
    }

    const imported: any[] = [];
    const errors: string[] = [];

    for (let i = 0; i < rows.length; i++) {
      const row = rows[i] as any;
      const itemCode = row["Codigo fabrica"] || row["codigo fabrica"] || row["itemCode"] || "";
      const name = row["Descripcion"] || row["descripcion"] || row["Producto"] || row["producto"] || "";
      const brand = row["Marca"] || row["marca"] || "";
      const model = row["Modelo"] || row["modelo"] || "";
      const year = row["Anos"] || row["anos"] || row["Años"] || row["años"] || "";
      const detail = row["Detalle"] || row["detalle"] || "";
      const wholesalePrice = parseFloat(row["Precio mayor"] || row["precio mayor"] || row["wholesalePrice"] || "0");

      if (!itemCode || !name) {
        errors.push(`Fila ${i + 1}: Código y nombre son obligatorios`);
        continue;
      }

      try {
        let product = await prisma.product.findUnique({ where: { itemCode } });

        if (!product) {
          product = await prisma.product.create({
            data: {
              itemCode,
              name,
              brand: brand || "Sin marca",
              model: model || "Sin modelo",
              year: year || "",
              detail,
              manufacturer: "Importado",
              price1: wholesalePrice || 0,
              price2: wholesalePrice || 0,
              wholesalePrice: wholesalePrice || undefined,
            },
          });
        } else if (wholesalePrice > 0) {
          product = await prisma.product.update({
            where: { id: product.id },
            data: { wholesalePrice },
          });
        }

        imported.push({ id: product.id, itemCode: product.itemCode, name: product.name });
      } catch {
        errors.push(`Fila ${i + 1}: no se pudo guardar (verifique código, nombre y precio)`);
      }
    }

    res.json({
      imported: imported.length,
      errors: errors.length,
      details: { imported, errors },
    });
  } catch (error: any) {
    console.error("Error al importar Excel:", error);
    res.status(500).json({ message: "Error al procesar el archivo" });
  }
});

// GET / — Listar ventas mayoristas
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { startDate, endDate, locationId, page = "1", limit = "20" } = req.query;

    const where: any = { type: "MAYOR" };
    if (req.user?.role === "TIENDA") {
      where.locationId = req.user.locationId;
    } else if (locationId && typeof locationId === "string") {
      where.locationId = Number(locationId);
    }
    if (startDate || endDate) {
      // Mismo criterio de día de negocio que ventas, devoluciones y reportes
      // (endDate inclusivo hasta las 23:59:59.999 de America/La_Paz).
      const rango = rangoFechasNegocio(startDate, endDate);
      if (rango.gte || rango.lte) where.saleDate = rango;
    }

    const { page: pg, limit: take, skip } = parsePagination(page, limit, 500);

    const [sales, total] = await Promise.all([
      prisma.sale.findMany({
        where,
        include: {
          user: { select: { id: true, name: true } },
          location: { select: { id: true, name: true } },
          customer: true,
          items: { include: { product: { select: { id: true, name: true, itemCode: true } } } },
          payments: true,
        },
        orderBy: { saleDate: "desc" },
        skip,
        take,
      }),
      prisma.sale.count({ where }),
    ]);

    res.json({
      sales: sales.map((s) => ({
        ...s,
        total: Number(s.total),
        items: s.items.map((i) => ({ ...i, unitPrice: Number(i.unitPrice), subtotal: Number(i.subtotal) })),
        payments: s.payments.map((p) => ({ ...p, amount: Number(p.amount) })),
      })),
      pagination: { total, page: pg, limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar ventas mayoristas:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
