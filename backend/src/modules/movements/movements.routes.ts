import { safeError } from "../../shared/utils/safeError";
import { idempotentMovement } from "../../shared/utils/idempotentMovement";
import { rangoFechasNegocio } from "../../shared/utils/rangoFechas";
import { moveStock, receiveMovement } from "../../shared/utils/moveStock";
import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate, authorizeModule, authorize, requireTiendaLocation } from "../../shared/middlewares/auth";
import { operationKey, replayableOperation } from "../../shared/utils/replayableOperation";
import { AuthRequest } from "../../shared/types";
import { parsePositiveInt, parseString } from "../../shared/middlewares/validate";
import { isPrismaClientError } from "../../shared/utils/errors";
import { parsePagination } from "../../shared/utils/pagination";

const router = Router();
import prisma from "../../config/database";

router.use(authenticate);
router.use(requireTiendaLocation);

router.get("/incoming", authorize("ADMIN", "INVENTARIO", "TIENDA"), authorizeModule(["movimientos", "solicitudes"]), async (req: AuthRequest, res: Response) => {
  try {
    const movements = await prisma.movement.findMany({ where: { status: "IN_TRANSIT",
      ...(req.user!.role === "TIENDA" ? { toLocationId: req.user!.locationId! } : {}) },
      include: { product: { select: { id: true, itemCode: true, name: true } }, fromLocation: { select: { name: true } }, toLocation: { select: { name: true } } },
      orderBy: { date: "asc" }, take: 200 });
    res.json({ movements });
  } catch { res.status(503).json({ message: "No se pudieron consultar los traslados pendientes" }); }
});

router.post("/:id/receive", authorizeModule(["movimientos", "solicitudes"]), async (req: AuthRequest, res: Response) => {
  try {
    if (!["ADMIN", "INVENTARIO", "TIENDA"].includes(req.user!.role)) return res.status(403).json({ message: "Rol no autorizado para recibir" });
    const id = parsePositiveInt(req.params.id, "Traslado");
    const key = operationKey(req);
    if (req.body.quantity !== undefined && !key) return res.status(400).json({ message: "La recepción parcial requiere identidad de operación" });
    const movement = await prisma.movement.findUnique({ where: { id } });
    if (!movement) return res.status(404).json({ message: "Traslado no encontrado" });
    if (req.user!.role === "TIENDA" && movement.toLocationId !== req.user!.locationId) return res.status(403).json({ message: "Solo puede recibir en su tienda" });
    if (movement.requestId) return res.status(400).json({ message: "Confirme la recepción desde la solicitud vinculada" });
    const quantity = req.body.quantity === undefined ? undefined : parsePositiveInt(req.body.quantity, "Cantidad recibida");
    const result = await prisma.$transaction(tx => replayableOperation(tx, req.user!.userId, "RECEIVE_MOVEMENT", key, { id, quantity }, () => receiveMovement(tx, id, req.user!.userId, quantity)));
    res.json(result);
  } catch (error) { res.status(isPrismaClientError(error) ? 500 : 400).json({ message: isPrismaClientError(error) ? "No se pudo registrar la recepción" : (error as Error).message }); }
});

// GET / — Historial de movimientos con filtros (requiere permiso del módulo "movimientos")
router.get("/", authorizeModule("movimientos"), async (req: AuthRequest, res: Response) => {
  try {
    const { productId, fromLocationId, toLocationId, startDate, endDate, page = "1", limit = "20" } = req.query;

    const where: any = {};
    if (req.user!.role === "TIENDA") where.OR = [{ fromLocationId: req.user!.locationId }, { toLocationId: req.user!.locationId }];
    if (productId && typeof productId === "string") where.productId = Number(productId);
    if (fromLocationId && typeof fromLocationId === "string") where.fromLocationId = Number(fromLocationId);
    if (toLocationId && typeof toLocationId === "string") where.toLocationId = Number(toLocationId);
    const range = rangoFechasNegocio(startDate, endDate);
    if (range.gte || range.lte) where.date = range;

    const { page: pg, limit: take, skip } = parsePagination(page, limit, 100);

    const [movements, total] = await Promise.all([
      prisma.movement.findMany({
        where,
        include: {
          product: { select: { id: true, name: true, itemCode: true, brand: true } },
          fromLocation: { select: { id: true, name: true, type: true } },
          toLocation: { select: { id: true, name: true, type: true } },
          user: { select: { id: true, name: true } },
          request: { select: { id: true, status: true } },
        },
        orderBy: { date: "desc" },
        skip,
        take,
      }),
      prisma.movement.count({ where }),
    ]);

    res.json({
      movements,
      pagination: { total, page: pg, limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar movimientos:", safeError(error));
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST / — Registrar movimiento (requiere permiso del módulo "movimientos")
router.post("/", authorize("ADMIN", "INVENTARIO"), authorizeModule("movimientos"), async (req: AuthRequest, res: Response) => {
  try {
    const productId = parsePositiveInt(req.body.productId, "Producto");
    const fromLocationId = parsePositiveInt(req.body.fromLocationId, "Ubicación origen");
    const toLocationId = parsePositiveInt(req.body.toLocationId, "Ubicación destino");
    const quantity = parsePositiveInt(req.body.quantity, "Cantidad");
    const observation = parseString(req.body.observation, "Observación", { max: 500 });
    const requestId = req.body.requestId ? parsePositiveInt(req.body.requestId, "Solicitud") : null;

    if (fromLocationId === toLocationId) {
      return res.status(400).json({ message: "La ubicación de origen y destino no pueden ser la misma" });
    }

    const user = req.user!;

    const [product, fromLocation, toLocation] = await Promise.all([
      prisma.product.findUnique({ where: { id: productId } }),
      prisma.location.findUnique({ where: { id: fromLocationId } }),
      prisma.location.findUnique({ where: { id: toLocationId } }),
    ]);

    if (!product) return res.status(404).json({ message: "Producto no encontrado" });
    if (!fromLocation) return res.status(404).json({ message: "Ubicación de origen no encontrada" });
    if (!toLocation) return res.status(404).json({ message: "Ubicación de destino no encontrada" });

    const operationId = req.body.operationId;
    if (!requestId && typeof operationId !== "string") return res.status(400).json({ message: "Envíe operationId para evitar movimientos duplicados al reintentar" });

    const movement = await prisma.$transaction(async (tx) => {
      const execute = async () => {
      if (requestId) {
        await tx.$queryRaw`SELECT id FROM "ProductRequest" WHERE id = ${requestId} FOR UPDATE`;
        const request = await tx.productRequest.findUnique({ where: { id: requestId } });
        if (!request || request.status !== "PREPARANDO" || request.productId !== productId || request.locationId !== toLocationId || request.quantity !== quantity || fromLocation.type !== "ALMACEN") throw new Error("El movimiento no coincide con una solicitud en preparación");
        await tx.productRequest.update({ where: { id: requestId }, data: { status: "ENTREGADO" } });
        await tx.requestHistory.create({ data: { requestId, previousStatus: "PREPARANDO", newStatus: "ENTREGADO", userId: user.userId, userRole: user.role } });
      }
      return moveStock(tx, { productId, fromLocationId, toLocationId, quantity, userId: user.userId, observation, requestId });
      };
      return operationId ? idempotentMovement(tx, user.userId, operationId, { productId, fromLocationId, toLocationId, quantity, observation, requestId }, execute) : execute();
    });

    res.status(201).json(movement);
  } catch (error: any) {
    if (typeof error?.message === "string" && !isPrismaClientError(error)) {
      return res.status(400).json({ message: error.message });
    }
    console.error("Error al registrar movimiento:", safeError(error));
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
