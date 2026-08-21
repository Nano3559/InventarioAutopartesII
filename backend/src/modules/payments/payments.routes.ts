import { Router, Request, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

// GET / — Listar pagos con filtros
router.get("/", async (req: Request, res: Response) => {
  try {
    const { saleId, method, page = "1", limit = "50" } = req.query;

    const where: any = {};
    if (saleId && typeof saleId === "string") where.saleId = Number(saleId);
    if (method && typeof method === "string") where.method = method;

    const skip = (Number(page) - 1) * Number(limit);
    const take = Number(limit);

    const [payments, total] = await Promise.all([
      prisma.payment.findMany({
        where,
        include: {
          sale: {
            include: {
              location: { select: { name: true } },
              user: { select: { name: true } },
            },
          },
        },
        orderBy: { date: "desc" },
        skip,
        take,
      }),
      prisma.payment.count({ where }),
    ]);

    res.json({
      payments,
      pagination: { total, page: Number(page), limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar pagos:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST / — Registrar pago adicional a una venta
router.post("/", async (req: Request, res: Response) => {
  try {
    const { saleId, method, amount } = req.body;

    if (!saleId || !method || amount == null) {
      return res.status(400).json({ message: "Campos obligatorios: saleId, method, amount" });
    }

    const sale = await prisma.sale.findUnique({ where: { id: saleId } });
    if (!sale) {
      return res.status(404).json({ message: "Venta no encontrada" });
    }

    const validMethods = ["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"];
    if (!validMethods.includes(method)) {
      return res.status(400).json({ message: `Método inválido. Use: ${validMethods.join(", ")}` });
    }

    const payment = await prisma.payment.create({
      data: { saleId, method, amount: Number(amount) },
    });

    res.status(201).json(payment);
  } catch (error) {
    console.error("Error al registrar pago:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /summary/:saleId — Resumen de pagos de una venta
router.get("/summary/:saleId", async (req: Request, res: Response) => {
  try {
    const saleId = Number(req.params.saleId);
    const sale = await prisma.sale.findUnique({ where: { id: saleId } });
    if (!sale) {
      return res.status(404).json({ message: "Venta no encontrada" });
    }

    const payments = await prisma.payment.findMany({
      where: { saleId },
      orderBy: { date: "asc" },
    });

    const totalPaid = payments.reduce((sum, p) => sum + Number(p.amount), 0);
    const totalSale = Number(sale.total);

    res.json({
      saleId,
      totalSale,
      totalPaid,
      pending: totalSale - totalPaid,
      payments: payments.map((p) => ({
        id: p.id,
        method: p.method,
        amount: Number(p.amount),
        date: p.date,
      })),
    });
  } catch (error) {
    console.error("Error al obtener resumen de pagos:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
