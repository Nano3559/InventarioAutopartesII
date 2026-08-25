import { Router, Response } from "express";
import { PrismaClient, PaymentMethod } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import { parseId, parsePositiveInt, parsePositiveDecimal, parseString } from "../../shared/middlewares/validate";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

const VALID_METHODS: PaymentMethod[] = ["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"];

// GET / — Listar devoluciones con filtros
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { saleId, productId, page = "1", limit = "20" } = req.query;

    const where: any = {};
    if (saleId && typeof saleId === "string") where.saleId = Number(saleId);
    if (productId && typeof productId === "string") where.productId = Number(productId);

    const pg = Math.max(1, Number(page) || 1);
    const take = Math.min(100, Math.max(1, Number(limit) || 20));
    const skip = (pg - 1) * take;

    const [returns, total] = await Promise.all([
      prisma.return.findMany({
        where,
        include: {
          product: { select: { id: true, name: true, itemCode: true, brand: true } },
          sale: { select: { id: true, saleDate: true, total: true, type: true } },
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

    const saleItem = sale.items.find((i) => i.productId === productId);
    if (!saleItem) return res.status(400).json({ message: "El producto no pertenece a esta venta" });
    if (quantity > saleItem.quantity) {
      return res.status(400).json({ message: `La cantidad a devolver (${quantity}) excede la vendida (${saleItem.quantity})` });
    }

    const returned = await prisma.$transaction(async (tx) => {
      const ret = await tx.return.create({
        data: { saleId, productId, reason: reason!, quantity, amount, method },
      });
      await tx.inventory.upsert({
        where: { productId_locationId: { productId, locationId: sale.locationId } },
        update: { stock: { increment: quantity } },
        create: { productId, locationId: sale.locationId, stock: quantity, minStock: 1 },
      });
      return ret;
    });

    res.status(201).json(returned);
  } catch (error: any) {
    if (error.message && !error.message.includes("Prisma")) {
      return res.status(400).json({ message: error.message });
    }
    console.error("Error al registrar devolución:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
