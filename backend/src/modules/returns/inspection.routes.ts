import { Router, Response } from "express";
import prisma from "../../config/database";
import { authorize, authorizeModule } from "../../shared/middlewares/auth";
import { parsePositiveInt, parseString } from "../../shared/middlewares/validate";
import { incrementStock } from "../../shared/utils/stock";
import { operationKey, replayableOperation } from "../../shared/utils/replayableOperation";
import { errorDominio } from "../../shared/utils/errorDominio";
import { isPrismaClientError } from "../../shared/utils/errors";
import { AuthRequest } from "../../shared/types";

const router = Router();
router.use(authorize("ADMIN", "INVENTARIO"));
router.use(authorizeModule(["inventario", "devoluciones"]));

router.get("/pending", async (_req: AuthRequest, res: Response) => {
  try {
    const returns = await prisma.return.findMany({ where: { disposition: "PENDING_INSPECTION" },
      select: { id: true, quantity: true, restockedQuantity: true, discardedQuantity: true, reason: true, date: true,
        product: { select: { id: true, name: true, itemCode: true } },
        sale: { select: { locationId: true, location: { select: { name: true } } } } },
      orderBy: { date: "asc" }, take: 200 });
    res.json({ returns });
  } catch { res.status(503).json({ message: "No se pudo consultar la inspección pendiente" }); }
});

router.post("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const id = parsePositiveInt(req.params.id, "Devolución");
    const quantity = parsePositiveInt(req.body.quantity, "Cantidad inspeccionada");
    const reason = parseString(req.body.reason, "Motivo de inspección", { required: true, max: 500 });
    const outcome = req.body.outcome;
    if (outcome !== "SELLABLE" && outcome !== "NOT_SELLABLE") throw errorDominio("Resultado de inspección inválido");
    const key = operationKey(req);
    if (!key) throw errorDominio("La inspección requiere identidad de operación");
    const result = await prisma.$transaction(tx => replayableOperation(tx, req.user!.userId, "RETURN_INSPECTION", key, { id, quantity, reason, outcome }, async () => {
      await tx.$queryRaw`SELECT id FROM "Return" WHERE id = ${id} FOR UPDATE`;
      const ret = await tx.return.findUnique({ where: { id }, include: { sale: { select: { locationId: true } } } });
      if (!ret) throw errorDominio("Devolución no encontrada");
      if (ret.disposition === "LEGACY") throw errorDominio("La devolución legacy requiere conciliación física previa");
      if (quantity > ret.quantity - ret.restockedQuantity - ret.discardedQuantity) throw errorDominio("La cantidad supera la inspección pendiente");
      const restockedQuantity = ret.restockedQuantity + (outcome === "SELLABLE" ? quantity : 0);
      const discardedQuantity = ret.discardedQuantity + (outcome === "NOT_SELLABLE" ? quantity : 0);
      if (outcome === "SELLABLE") await incrementStock(tx, ret.productId, ret.sale.locationId, quantity);
      const disposition = restockedQuantity + discardedQuantity < ret.quantity ? "PENDING_INSPECTION" :
        restockedQuantity === ret.quantity ? "SELLABLE" : discardedQuantity === ret.quantity ? "NOT_SELLABLE" : "MIXED";
      const updated = await tx.return.update({ where: { id }, data: { restockedQuantity, discardedQuantity, disposition, inspectedAt: new Date() } });
      await tx.auditLog.create({ data: { userId: req.user!.userId, action: "INSPECT_RETURN", targetType: "RETURN", targetId: id,
        newValue: { quantity, outcome, reason, restockedQuantity, discardedQuantity } } });
      return { id: updated.id, disposition: updated.disposition, restockedQuantity, discardedQuantity };
    }));
    res.json(result);
  } catch (error) { res.status(isPrismaClientError(error) ? 500 : 400).json({ message: isPrismaClientError(error) ? "No se pudo registrar la inspección" : (error as Error).message }); }
});
export default router;
