import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

const PERCENTAGES = [20, 30, 40, 50, 60, 70, 80];

// GET / — Calcular precios desde costo con porcentajes
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { search, page = "1", limit = "20" } = req.query;

    const where: any = {};
    if (search && typeof search === "string") {
      where.OR = [
        { name: { contains: search, mode: "insensitive" } },
        { itemCode: { contains: search, mode: "insensitive" } },
        { brand: { contains: search, mode: "insensitive" } },
        { model: { contains: search, mode: "insensitive" } },
      ];
    }

    const skip = (Number(page) - 1) * Number(limit);
    const take = Number(limit);

    const [products, total] = await Promise.all([
      prisma.product.findMany({
        where,
        include: {
          costs: { orderBy: { date: "desc" }, take: 1 },
        },
        orderBy: { name: "asc" },
        skip,
        take,
      }),
      prisma.product.count({ where }),
    ]);

    const prices = products.map((p) => {
      const cost = p.costs[0]?.costPrice ? Number(p.costs[0].costPrice) : p.cost ? Number(p.cost) : 0;
      const calculated: Record<string, number> = {};
      for (const pct of PERCENTAGES) {
        calculated[`p${pct}`] = Number((cost * (1 + pct / 100)).toFixed(2));
      }

      return {
        id: p.id,
        itemCode: p.itemCode,
        productName: p.name,
        brand: p.brand,
        model: p.model,
        years: p.year,
        detail: p.detail || "",
        cost,
        ...calculated,
        wholesalePrice: p.wholesalePrice ? Number(p.wholesalePrice) : 0,
      };
    });

    res.json({
      prices,
      percentages: PERCENTAGES,
      pagination: { total, page: Number(page), limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al calcular precios:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:productId — Actualizar precio por mayor
router.put("/:productId", async (req: AuthRequest, res: Response) => {
  try {
    const { productId } = req.params;
    const { wholesalePrice } = req.body;

    if (wholesalePrice === undefined || wholesalePrice === null) {
      return res.status(400).json({ message: "El campo wholesalePrice es obligatorio" });
    }

    const product = await prisma.product.findUnique({ where: { id: Number(productId) } });
    if (!product) return res.status(404).json({ message: "Producto no encontrado" });

    const updated = await prisma.product.update({
      where: { id: Number(productId) },
      data: { wholesalePrice: Number(wholesalePrice) },
      select: { id: true, name: true, itemCode: true, wholesalePrice: true },
    });

    res.json({
      id: updated.id,
      productName: updated.name,
      itemCode: updated.itemCode,
      wholesalePrice: Number(updated.wholesalePrice),
    });
  } catch (error) {
    console.error("Error al actualizar precio:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /export — Exportar precios a CSV
router.get("/export", async (req: AuthRequest, res: Response) => {
  try {
    const products = await prisma.product.findMany({
      where: { cost: { not: null } },
      include: { costs: { orderBy: { date: "desc" }, take: 1 } },
      orderBy: { name: "asc" },
    });

    const rows = products.map((p) => {
      const cost = p.costs[0]?.costPrice ? Number(p.costs[0].costPrice) : p.cost ? Number(p.cost) : 0;
      return {
        itemCode: p.itemCode,
        name: p.name,
        brand: p.brand,
        model: p.model,
        years: p.year,
        detail: p.detail || "",
        wholesalePrice: p.wholesalePrice ? Number(p.wholesalePrice) : 0,
      };
    });

    res.json({ data: rows, total: rows.length });
  } catch (error) {
    console.error("Error al exportar precios:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
