import { Router, Response } from "express";
import prisma from "../../config/database";
import { authenticate, authorizeModule } from "../../shared/middlewares/auth";
import type { AuthRequest } from "../../shared/types";
const router = Router();
router.use(authenticate);
const modules: Record<string, string[]> = {
  VOID_SALE: ["ventas", "ventas-mayor"], SALE_NORMAL: ["ventas"], SALE_WHOLESALE: ["ventas-mayor"], PAYMENT: ["ventas", "ventas-mayor"],
  RETURN: ["devoluciones"], RETURN_INSPECTION: ["inventario", "devoluciones"], RECEIVE_MOVEMENT: ["movimientos", "solicitudes"],
};
router.get("/:scope/:key", (req: AuthRequest, res, next) => {
  const permissions = modules[req.params.scope];
  if (!permissions || !/^[\w-]{8,100}$/.test(req.params.key)) return res.status(400).json({ message: "Operación inválida" });
  const roles = req.params.scope === "VOID_SALE" ? ["ADMIN"] : req.params.scope === "RETURN_INSPECTION" ? ["ADMIN", "INVENTARIO"] :
    req.params.scope === "RECEIVE_MOVEMENT" ? ["ADMIN", "INVENTARIO", "TIENDA"] : ["ADMIN", "TIENDA"];
  if (!roles.includes(req.user!.role)) return res.status(403).json({ message: "No tiene permiso para consultar esta operación" });
  return authorizeModule(permissions)(req, res, next);
}, async (req: AuthRequest, res: Response) => {
  try {
    const record = await prisma.$transaction(async tx => {
      await tx.$queryRaw`SELECT pg_advisory_xact_lock(hashtextextended(${`${req.params.scope}:${req.user!.userId}:${req.params.key}`}, 0))::text`;
      return tx.auditLog.findFirst({ where: { action: "REPLAYABLE_OPERATION", targetType: req.params.scope,
        userId: req.user!.userId, newValue: { path: ["operationId"], equals: req.params.key } } });
    });
    if (!record) return res.status(404).json({ message: "No hay resultado confirmado. Reintente conservando la misma identidad" });
    const saved = record.newValue as any;
    if (req.user!.role === "TIENDA") {
      const sale = saved.result?.saleId ? await prisma.sale.findUnique({ where: { id: saved.result.saleId }, select: { locationId: true } }) : null;
      const locationId = saved.result?.locationId ?? saved.result?.toLocationId ?? sale?.locationId;
      if (!locationId || locationId !== req.user!.locationId) return res.status(403).json({ message: "La operación requiere revisión de un administrador por su ubicación" });
    }
    if (["SALE_NORMAL", "SALE_WHOLESALE", "VOID_SALE"].includes(req.params.scope)) {
      const current = await prisma.sale.findUnique({ where: { id: saved.result.id }, select: { status: true, voidedAt: true, voidReason: true } });
      if (current) saved.result = { ...saved.result, ...current };
    }
    res.json({ operationId: req.params.key, scope: req.params.scope, result: saved.result });
  } catch { res.status(503).json({ message: "No se pudo consultar el resultado de la operación" }); }
});
export default router;
