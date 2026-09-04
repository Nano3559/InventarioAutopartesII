import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate, authorize, requireTiendaLocation } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);
router.use(requireTiendaLocation);
router.use(authorize("ADMIN", "TIENDA"));

// GET / — Listar pagos con filtros
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { saleId, method, page = "1", limit = "50" } = req.query;

    const where: any = {};
    if (saleId && typeof saleId === "string") where.saleId = Number(saleId);
    if (method && typeof method === "string") where.method = method;

    if (req.user?.role === "TIENDA") {
      where.sale = { locationId: req.user.locationId };
    }

    const pg = Math.max(1, Number(page) || 1);
    const take = Math.min(500, Math.max(1, Number(limit) || 50));
    const skip = (pg - 1) * take;

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
      pagination: { total, page: pg, limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar pagos:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST / — Registrar pago adicional a una venta
router.post("/", async (req: AuthRequest, res: Response) => {
  try {
    const { saleId, method, amount } = req.body;

    if (!saleId || !method || amount == null) {
      return res.status(400).json({ message: "Campos obligatorios: saleId, method, amount" });
    }

    const amountNum = Number(amount);
    if (isNaN(amountNum) || amountNum <= 0) {
      return res.status(400).json({ message: "El monto debe ser un número mayor a 0" });
    }

    const sale = await prisma.sale.findUnique({
      where: { id: Number(saleId) },
      include: { location: true },
    });
    if (!sale) {
      return res.status(404).json({ message: "Venta no encontrada" });
    }

    // Aislamiento por tienda: solo pueden pagar ventas de su propia ubicación
    const payUser = req.user!;
    if (payUser.role === "TIENDA" && payUser.locationId && sale.locationId !== payUser.locationId) {
      return res.status(403).json({ message: "No tiene acceso a esta venta" });
    }

    const validMethods = ["EFECTIVO", "QR", "TRANSFERENCIA", "CREDITO"];
    if (!validMethods.includes(method)) {
      return res.status(400).json({ message: `Método inválido. Use: ${validMethods.join(", ")}` });
    }

    // No permitir pagar de más: pendiente = total - pagado - devuelto
    const existingPayments = await prisma.payment.aggregate({ where: { saleId: Number(saleId) }, _sum: { amount: true } });
    const totalReturned = await prisma.return.aggregate({ where: { saleId: Number(saleId) }, _sum: { amount: true } });
    const paid = Number(existingPayments._sum.amount || 0);
    const returned = Number(totalReturned._sum.amount || 0);
    const pending = Number(sale.total) - paid - returned;

    if (amountNum - pending > 0.01) {
      return res.status(400).json({
        message: `El monto (Bs. ${amountNum.toFixed(2)}) supera el saldo pendiente de la venta (Bs. ${pending.toFixed(2)})`,
      });
    }

    const payment = await prisma.payment.create({
      data: { saleId: Number(saleId), method, amount: amountNum },
    });

    res.status(201).json(payment);
  } catch (error) {
    console.error("Error al registrar pago:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /summary/:saleId — Resumen de pagos de una venta
router.get("/summary/:saleId", async (req: AuthRequest, res: Response) => {
  try {
    const saleId = Number(req.params.saleId);
    const sale = await prisma.sale.findUnique({ where: { id: saleId } });
    if (!sale) {
      return res.status(404).json({ message: "Venta no encontrada" });
    }

    const summaryUser = req.user!;
    if (summaryUser.role === "TIENDA" && summaryUser.locationId && sale.locationId !== summaryUser.locationId) {
      return res.status(403).json({ message: "No tiene acceso a esta venta" });
    }

    const [payments, returns] = await Promise.all([
      prisma.payment.findMany({
        where: { saleId },
        orderBy: { date: "asc" },
      }),
      prisma.return.aggregate({ where: { saleId }, _sum: { amount: true } }),
    ]);

    const totalPaid = payments.reduce((sum, p) => sum + Number(p.amount), 0);
    const totalReturned = Number(returns._sum.amount || 0);
    const totalSale = Number(sale.total);

    res.json({
      saleId,
      totalSale,
      totalPaid,
      totalReturned,
      pending: totalSale - totalPaid - totalReturned,
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
