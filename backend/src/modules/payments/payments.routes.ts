import { safeError } from "../../shared/utils/safeError";
import { bankReferenceConflict, paymentEvidence } from "../../shared/utils/paymentEvidence";
import { parsePositiveInt, parseString } from "../../shared/middlewares/validate";
import { money } from "../../shared/utils/pricing";
import { operationKey, replayableOperation } from "../../shared/utils/replayableOperation";
import { saleBalance } from "../../shared/utils/saleBalance";
import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authorizeModule, authenticate, authorize, requireTiendaLocation } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import { isPrismaClientError } from "../../shared/utils/errors";
import { parsePagination } from "../../shared/utils/pagination";

const router = Router();
import prisma from "../../config/database";

router.use(authenticate);
router.use(requireTiendaLocation);
router.use(authorize("ADMIN", "TIENDA"));
router.use(authorizeModule(["ventas", "ventas-mayor"]));

router.get("/receiving-accounts", async (_req, res) => {
  try { res.json({ accounts: await prisma.receivingAccount.findMany({ where: { active: true }, orderBy: { code: "asc" } }) }); }
  catch { res.status(503).json({ message: "No se pudieron consultar cuentas receptoras" }); }
});
router.post("/receiving-accounts", authorize("ADMIN"), async (req: AuthRequest, res) => {
  try {
    const code = parseString(req.body.code, "Código de cuenta", { required: true, max: 40 })!.toUpperCase();
    const name = parseString(req.body.name, "Nombre de cuenta", { required: true, max: 100 })!;
    if (!/^[A-Z0-9_-]{3,40}$/.test(code)) return res.status(400).json({ message: "Use un código de cuenta de 3 a 40 letras, números o guiones" });
    const account = await prisma.$transaction(async tx => {
      const created = await tx.receivingAccount.create({ data: { code, name } });
      await tx.auditLog.create({ data: { userId: req.user!.userId, action: "CREATE_RECEIVING_ACCOUNT", targetType: "RECEIVING_ACCOUNT", targetId: created.id, newValue: { code, name } } });
      return created;
    });
    res.status(201).json(account);
  } catch { res.status(400).json({ message: "Cuenta inválida o código ya registrado" }); }
});

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

    const { page: pg, limit: take, skip } = parsePagination(page, limit, 500);

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
    console.error("Error al listar pagos:", safeError(error));
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

    const amountNum = money(amount, "Monto de pago");
    if (method === "CREDITO") return res.status(400).json({ message: "El crédito se asigna al crear la venta. Registre aquí un cobro efectivo, QR o transferencia" });

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

    // M5 (ETAPA 8): la validación de "no pagar de más" es lectura+validación+escritura.
    // Dos pagos concurrentes sobre el mismo saldo pendiente podían pasar ambos el filtro.
    // Se protege dentro de una transacción con bloqueo pesimista de la fila de la venta.
    const key = operationKey(req);
    const payment = await prisma.$transaction(async (tx) => replayableOperation(tx, payUser.userId, "PAYMENT", key, req.body, async () => {
      await tx.$queryRaw`SELECT id FROM "Sale" WHERE "id" = ${Number(saleId)} FOR UPDATE`;
      if ((await tx.sale.findUniqueOrThrow({ where: { id: parsePositiveInt(saleId, "Venta") } })).status === "VOIDED") throw new Error("No se puede cobrar una venta anulada");

      const { pending } = await saleBalance(tx, Number(saleId), Number(sale.total));

      if (amountNum - pending > 0.01) {
        throw new Error(`El monto (Bs. ${amountNum.toFixed(2)}) supera el saldo pendiente de la venta (Bs. ${pending.toFixed(2)})`);
      }

      const [verified] = await paymentEvidence(tx, [{ method, amount: amountNum, bankVerification: req.body.bankVerification }], payUser.userId);
      return tx.payment.create({ data: { saleId: Number(saleId), ...verified } });
    }));

    res.status(201).json(payment);
  } catch (error: any) {
    if (bankReferenceConflict(error)) return res.status(409).json({ message: "La referencia bancaria ya está registrada. Revise el cobro original" });
    if (typeof error?.message === "string" && !isPrismaClientError(error)) {
      return res.status(400).json({ message: error.message });
    }
    console.error("Error al registrar pago:", safeError(error));
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
      prisma.return.aggregate({ where: { saleId }, _sum: { amount: true, refundAmount: true, debtReduction: true } }),
    ]);

    const totalPaid = payments.filter((p) => p.method !== "CREDITO").reduce((sum, p) => sum + Number(p.amount), 0);
    const totalReturned = Number(returns._sum.amount || 0);
    const totalRefunded = Number(returns._sum.refundAmount || 0);
    const totalSale = Number(sale.total);

    res.json({
      saleId,
      totalSale,
      totalPaid,
      totalReturned,
      totalRefunded,
      debtReduced: Number(returns._sum.debtReduction || 0),
      netCollected: totalPaid - totalRefunded,
      status: sale.status,
      pending: sale.status === "VOIDED" ? 0 : Math.max(0, totalSale - totalPaid - totalReturned + totalRefunded),
      creditAssigned: payments.filter((p) => p.method === "CREDITO").reduce((sum, p) => sum + Number(p.amount), 0),
      payments: payments.map((p) => ({
        id: p.id,
        method: p.method,
        amount: Number(p.amount),
        date: p.date,
      })),
    });
  } catch (error) {
    console.error("Error al obtener resumen de pagos:", safeError(error));
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
