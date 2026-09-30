import { Router, Response } from "express";
import { PrismaClient, PaymentMethod } from "@prisma/client";
import { isPrismaClientError } from "../../shared/utils/errors";
import { parsePagination } from "../../shared/utils/pagination";
import { rangoFechasNegocio } from "../../shared/utils/rangoFechas";
import { authenticate, authorize, requireTiendaLocation } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import { parseId, parsePositiveInt, parsePositiveDecimal, parseString } from "../../shared/middlewares/validate";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);
router.use(requireTiendaLocation);
router.use(authorize("ADMIN", "TIENDA"));

const VALID_METHODS: PaymentMethod[] = ["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"];

// GET / — Listar devoluciones con filtros
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { saleId, productId, locationId, seller, startDate, endDate, page = "1", limit = "20" } = req.query;

    const where: any = {};
    if (saleId && typeof saleId === "string") where.saleId = Number(saleId);
    if (productId && typeof productId === "string") where.productId = Number(productId);
    // J6: rango por fecha de la devolución. Sin esto el reporte diario sumaba
    // devoluciones de cualquier fecha (incluso fuera del periodo elegido).
    // El endDate incluye TODO ese día de negocio (antes cortaba a la medianoche).
    const rango = rangoFechasNegocio(startDate, endDate);
    if (rango.gte || rango.lte) where.date = rango;

    const user = req.user!;
    const saleFilters: any = {};
    if (user.role === "TIENDA") {
      saleFilters.locationId = user.locationId;
    } else if (locationId && typeof locationId === "string") {
      saleFilters.locationId = Number(locationId);
    }
    if (seller && typeof seller === "string") {
      saleFilters.seller = seller;
    }
    if (Object.keys(saleFilters).length > 0) {
      where.sale = saleFilters;
    }

    // Tope 1000: el reporte diario necesita el periodo completo, no 20 filas.
    // parsePagination entero-trunca page/limit: sin Math.floor, `?limit=2.7`
    // llegaba a Prisma como 2.7 y terminaba en 500.
    const { page: pg, limit: take, skip } = parsePagination(page, limit, 1000);

    const [returns, total] = await Promise.all([
      prisma.return.findMany({
        where,
        include: {
          product: { select: { id: true, name: true, itemCode: true, brand: true } },
          sale: { select: { id: true, saleDate: true, total: true, type: true, locationId: true, seller: true } },
        },
        skip,
        take,
        orderBy: { date: "desc" },
      }),
      prisma.return.count({ where }),
    ]);

    res.json({
      returns,
      pagination: { total, page: pg, limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar devoluciones:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /recent-sales — Ventas recientes filtradas por ubicación/rol
router.get("/recent-sales", async (req: AuthRequest, res: Response) => {
  try {
    const user = req.user!;
    const where: any = {};
    if (user.role === "TIENDA" && user.locationId) {
      where.locationId = user.locationId;
    }

    const sales = await prisma.sale.findMany({
      where,
      include: {
        location: { select: { id: true, name: true } },
        customer: { select: { id: true, name: true, nit: true } },
        items: { include: { product: { select: { id: true, name: true, itemCode: true } } } },
        returns: true,
      },
      orderBy: { saleDate: "desc" },
      take: 20,
    });

    res.json({ sales });
  } catch (error) {
    console.error("Error al obtener ventas recientes:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /sale/:saleId — Buscar venta por ID para ver sus items
router.get("/sale/:saleId", async (req: AuthRequest, res: Response) => {
  try {
    const saleId = parseId(req.params.saleId);
    const sale = await prisma.sale.findUnique({
      where: { id: saleId },
      include: {
        items: { include: { product: true } },
        customer: true,
        payments: true,
        returns: true,
        location: true,
      },
    });
    if (!sale) return res.status(404).json({ message: "Venta no encontrada" });

    const lookupUser = req.user!;
    if (lookupUser.role === "TIENDA" && lookupUser.locationId && sale.locationId !== lookupUser.locationId) {
      return res.status(403).json({ message: "No tiene acceso a esta venta" });
    }

    res.json(sale);
  } catch (error: any) {
    if (error.message === "ID inválido") return res.status(400).json({ message: error.message });
    console.error("Error al buscar venta:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Registrar devolución
router.post("/", async (req: AuthRequest, res: Response) => {
  try {
    const saleId = parsePositiveInt(req.body.saleId, "Venta");
    const productId = parsePositiveInt(req.body.productId, "Producto");
    const reason = parseString(req.body.reason, "Motivo", { required: true, max: 500 });
    const quantity = parsePositiveInt(req.body.quantity, "Cantidad");
    const amount = parsePositiveDecimal(req.body.amount, "Monto");
    const method = req.body.method as PaymentMethod;

    if (!VALID_METHODS.includes(method)) {
      return res.status(400).json({ message: `Método inválido. Valores válidos: ${VALID_METHODS.join(", ")}` });
    }
    if (amount <= 0) return res.status(400).json({ message: "El monto debe ser mayor a 0" });

    const sale = await prisma.sale.findUnique({
      where: { id: saleId },
      include: { items: true, location: true },
    });
    if (!sale) return res.status(404).json({ message: "Venta no encontrada" });

    const returnUser = req.user!;
    if (returnUser.role === "TIENDA" && returnUser.locationId && sale.locationId !== returnUser.locationId) {
      return res.status(403).json({ message: "No puede devolver productos de una venta de otra tienda" });
    }

    const saleItem = sale.items.find((i) => i.productId === productId);
    if (!saleItem) return res.status(400).json({ message: "El producto no pertenece a esta venta" });
    if (quantity > saleItem.quantity) {
      return res.status(400).json({ message: `La cantidad a devolver (${quantity}) excede la vendida (${saleItem.quantity})` });
    }

    // Impedir devolver la misma cantidad dos veces (suma devoluciones previas)
    const previousReturns = await prisma.return.findMany({
      where: { saleId, productId },
      select: { quantity: true },
    });
    const alreadyReturned = previousReturns.reduce((sum, r) => sum + r.quantity, 0);
    if (alreadyReturned + quantity > saleItem.quantity) {
      const remaining = saleItem.quantity - alreadyReturned;
      return res.status(400).json({
        message: `Ya se devolvieron ${alreadyReturned} de ${saleItem.quantity} unidades. Máximo adicional: ${Math.max(remaining, 0)}.`,
      });
    }

    // El monto debe coincidir con el precio vendido × cantidad
    const expectedAmount = Number(saleItem.unitPrice) * quantity;
    if (Math.abs(amount - expectedAmount) > 0.01) {
      return res.status(400).json({
        message: `El monto devuelto (Bs. ${amount}) no coincide con el precio vendido de la cantidad a devolver (Bs. ${expectedAmount.toFixed(2)})`,
      });
    }

    const returned = await prisma.$transaction(async (tx) => {
      // R4: serializar devoluciones del mismo producto dentro de la misma venta bloqueando
      // la(s) fila(s) del SaleItem (FOR UPDATE). Sin este lock, dos devoluciones concurrentes
      // de un mismo producto podrían leer la misma suma previa y devolver más de lo vendido.
      // La cantidad vendida se relee dentro de la transacción a partir de las filas bloqueadas.
      const lockedItems = await tx.$queryRaw<{ id: number; quantity: number }[]>`
        SELECT id, quantity FROM "SaleItem"
        WHERE "saleId" = ${saleId} AND "productId" = ${productId}
        FOR UPDATE`;

      if (!lockedItems.length) {
        throw new Error("El producto no pertenece a esta venta");
      }
      const soldQuantity = lockedItems.reduce((sum, i) => sum + i.quantity, 0);

      // Re-chequeo de la suma de devoluciones previas dentro de la transacción (atómico).
      const previousReturns = await tx.return.findMany({
        where: { saleId, productId },
        select: { quantity: true },
      });
      const alreadyReturned = previousReturns.reduce((sum, r) => sum + r.quantity, 0);
      if (alreadyReturned + quantity > soldQuantity) {
        const remaining = soldQuantity - alreadyReturned;
        throw new Error(`Ya se devolvieron ${alreadyReturned} de ${soldQuantity} unidades. Máximo adicional: ${Math.max(remaining, 0)}.`);
      }

      const ret = await tx.return.create({
        data: { saleId, productId, reason: reason!, quantity, amount, method },
      });
      // El increment es atómico en PostgreSQL: devoluciones concurrentes nunca pierden stock.
      // Se usa upsert (INSERT ... ON CONFLICT DO UPDATE) que resuelve concurrentemente la
      // creación o el incremento de la fila sin riesgo de conflicto de unicidad (P2002).
      await tx.inventory.upsert({
        where: { productId_locationId: { productId, locationId: sale.locationId } },
        update: { stock: { increment: quantity } },
        create: { productId, locationId: sale.locationId, stock: quantity, minStock: 1 },
      });
      return ret;
    }, { timeout: 20000 });

    res.status(201).json(returned);
  } catch (error: any) {
    // Los errores internos de Prisma (timeout, contención, conexión) se ocultan como 500.
    // Los errores de dominio (doble devolución, producto no perteneciente) son mensajes
    // planos y se responden como 400.
    if (error && isPrismaClientError(error)) {
      console.error("Error al registrar devolución:", error);
      return res.status(500).json({ message: "Error interno del servidor" });
    }
    res.status(400).json({ message: error.message || "Error interno del servidor" });
  }
});

export default router;
