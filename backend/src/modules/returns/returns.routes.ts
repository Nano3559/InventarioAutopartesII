import { Router, Request, Response } from "express";
import { PrismaClient } from "@prisma/client";

const router = Router();
const prisma = new PrismaClient();

// GET / — Listar devoluciones con filtros
router.get("/", async (req: Request, res: Response) => {
  try {
    const { saleId, productId, page = "1", limit = "20" } = req.query;

    const where: any = {};
    if (saleId && typeof saleId === "string") where.saleId = Number(saleId);
    if (productId && typeof productId === "string") where.productId = Number(productId);

    const skip = (Number(page) - 1) * Number(limit);
    const take = Number(limit);

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
      pagination: { total, page: Number(page), limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar devoluciones:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /sale/:saleId — Buscar venta por ID para ver sus items
router.get("/sale/:saleId", async (req: Request, res: Response) => {
  try {
    const saleId = Number(req.params.saleId);
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

    if (!sale) {
      return res.status(404).json({ message: "Venta no encontrada" });
    }

    res.json(sale);
  } catch (error) {
    console.error("Error al buscar venta:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Registrar devolución
router.post("/", async (req: Request, res: Response) => {
  try {
    const { saleId, productId, reason, quantity, amount, method } = req.body;

    if (!saleId || !productId || !reason || !quantity || !amount || !method) {
      return res.status(400).json({ message: "Campos obligatorios: saleId, productId, reason, quantity, amount, method" });
    }

    const sale = await prisma.sale.findUnique({
      where: { id: saleId },
      include: { items: true, location: true },
    });

    if (!sale) {
      return res.status(404).json({ message: "Venta no encontrada" });
    }

    const saleItem = sale.items.find((i) => i.productId === productId);
    if (!saleItem) {
      return res.status(400).json({ message: "El producto no pertenece a esta venta" });
    }

    if (quantity > saleItem.quantity) {
      return res.status(400).json({ message: `La cantidad a devolver (${quantity}) excede la vendida (${saleItem.quantity})` });
    }

    const returned = await prisma.$transaction(async (tx) => {
      const ret = await tx.return.create({
        data: { saleId, productId, reason, quantity, amount, method },
      });

      // Devolver stock a la ubicación de la venta
      await tx.inventory.upsert({
        where: { productId_locationId: { productId, locationId: sale.locationId } },
        update: { stock: { increment: quantity } },
        create: { productId, locationId: sale.locationId, stock: quantity, minStock: 1 },
      });

      return ret;
    });

    res.status(201).json(returned);
  } catch (error) {
    console.error("Error al registrar devolución:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
