import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

// GET / — Historial de movimientos con filtros
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { productId, fromLocationId, toLocationId, startDate, endDate, page = "1", limit = "20" } = req.query;

    const where: any = {};
    if (productId && typeof productId === "string") where.productId = Number(productId);
    if (fromLocationId && typeof fromLocationId === "string") where.fromLocationId = Number(fromLocationId);
    if (toLocationId && typeof toLocationId === "string") where.toLocationId = Number(toLocationId);
    if (startDate || endDate) {
      where.date = {};
      if (startDate && typeof startDate === "string") where.date.gte = new Date(startDate);
      if (endDate && typeof endDate === "string") {
        const end = new Date(endDate);
        end.setHours(23, 59, 59, 999);
        where.date.lte = end;
      }
    }

    const skip = (Number(page) - 1) * Number(limit);
    const take = Number(limit);

    const [movements, total] = await Promise.all([
      prisma.movement.findMany({
        where,
        include: {
          product: { select: { id: true, name: true, itemCode: true, brand: true } },
          fromLocation: { select: { id: true, name: true, type: true } },
          toLocation: { select: { id: true, name: true, type: true } },
          user: { select: { id: true, name: true } },
        },
        orderBy: { date: "desc" },
        skip,
        take,
      }),
      prisma.movement.count({ where }),
    ]);

    res.json({
      movements,
      pagination: { total, page: Number(page), limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar movimientos:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST / — Registrar movimiento
router.post("/", async (req: AuthRequest, res: Response) => {
  try {
    const { productId, fromLocationId, toLocationId, quantity, observation } = req.body;

    if (!productId || !fromLocationId || !toLocationId || !quantity) {
      return res.status(400).json({ message: "Campos obligatorios: productId, fromLocationId, toLocationId, quantity" });
    }

    if (fromLocationId === toLocationId) {
      return res.status(400).json({ message: "La ubicación de origen y destino no pueden ser la misma" });
    }

    if (Number(quantity) <= 0) {
      return res.status(400).json({ message: "La cantidad debe ser mayor a 0" });
    }

    const user = req.user!;

    const product = await prisma.product.findUnique({ where: { id: Number(productId) } });
    if (!product) {
      return res.status(404).json({ message: "Producto no encontrado" });
    }

    const fromLocation = await prisma.location.findUnique({ where: { id: Number(fromLocationId) } });
    if (!fromLocation) {
      return res.status(404).json({ message: "Ubicación de origen no encontrada" });
    }

    const toLocation = await prisma.location.findUnique({ where: { id: Number(toLocationId) } });
    if (!toLocation) {
      return res.status(404).json({ message: "Ubicación de destino no encontrada" });
    }

    const inventoryOrigin = await prisma.inventory.findUnique({
      where: {
        productId_locationId: { productId: Number(productId), locationId: Number(fromLocationId) },
      },
    });

    if (!inventoryOrigin || inventoryOrigin.stock < Number(quantity)) {
      const available = inventoryOrigin?.stock || 0;
      return res.status(400).json({
        message: `Stock insuficiente en origen. Disponible: ${available}, solicitado: ${quantity}`,
      });
    }

    const movement = await prisma.$transaction(async (tx) => {
      await tx.inventory.update({
        where: { id: inventoryOrigin.id },
        data: { stock: { decrement: Number(quantity) } },
      });

      const inventoryDest = await tx.inventory.findUnique({
        where: {
          productId_locationId: { productId: Number(productId), locationId: Number(toLocationId) },
        },
      });

      if (inventoryDest) {
        await tx.inventory.update({
          where: { id: inventoryDest.id },
          data: { stock: { increment: Number(quantity) } },
        });
      } else {
        await tx.inventory.create({
          data: {
            productId: Number(productId),
            locationId: Number(toLocationId),
            stock: Number(quantity),
            minStock: 0,
          },
        });
      }

      const newMovement = await tx.movement.create({
        data: {
          productId: Number(productId),
          fromLocationId: Number(fromLocationId),
          toLocationId: Number(toLocationId),
          quantity: Number(quantity),
          userId: user.userId,
          observation: observation || null,
        },
        include: {
          product: { select: { name: true, itemCode: true } },
          fromLocation: { select: { name: true } },
          toLocation: { select: { name: true } },
          user: { select: { name: true } },
        },
      });

      return newMovement;
    });

    res.status(201).json(movement);
  } catch (error: any) {
    console.error("Error al registrar movimiento:", error);
    res.status(400).json({ message: error.message || "Error interno del servidor" });
  }
});

export default router;
