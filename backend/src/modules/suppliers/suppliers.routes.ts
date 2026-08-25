import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

// GET / — Listar proveedores con búsqueda
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { search, page = "1", limit = "50" } = req.query;

    const where: any = {};
    if (search && typeof search === "string") {
      where.OR = [
        { name: { contains: search, mode: "insensitive" } },
        { nit: { contains: search, mode: "insensitive" } },
        { phone: { contains: search, mode: "insensitive" } },
      ];
    }

    const skip = (Number(page) - 1) * Number(limit);
    const take = Number(limit);

    const [suppliers, total] = await Promise.all([
      prisma.supplier.findMany({
        where,
        include: { _count: { select: { costs: true } } },
        orderBy: { name: "asc" },
        skip,
        take,
      }),
      prisma.supplier.count({ where }),
    ]);

    res.json({
      suppliers: suppliers.map((s) => ({
        id: s.id,
        name: s.name,
        nit: s.nit,
        phone: s.phone,
        costsCount: s._count.costs,
        createdAt: s.createdAt,
      })),
      pagination: { total, page: Number(page), limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar proveedores:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /:id — Detalle de proveedor
router.get("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const supplier = await prisma.supplier.findUnique({
      where: { id: Number(req.params.id) },
      include: {
        costs: {
          include: { product: { select: { name: true, itemCode: true } } },
          orderBy: { date: "desc" },
          take: 10,
        },
        _count: { select: { costs: true } },
      },
    });

    if (!supplier) return res.status(404).json({ message: "Proveedor no encontrado" });

    res.json({
      id: supplier.id,
      name: supplier.name,
      nit: supplier.nit,
      phone: supplier.phone,
      costsCount: supplier._count.costs,
      recentCosts: supplier.costs.map((c) => ({
        id: c.id,
        productName: c.product.name,
        itemCode: c.product.itemCode,
        costPrice: Number(c.costPrice),
        date: c.date,
      })),
    });
  } catch (error) {
    console.error("Error al obtener proveedor:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Crear proveedor
router.post("/", async (req: AuthRequest, res: Response) => {
  try {
    const { name, nit, phone } = req.body;

    if (!name) return res.status(400).json({ message: "El nombre es obligatorio" });

    if (nit) {
      const existing = await prisma.supplier.findFirst({ where: { nit } });
      if (existing) return res.status(400).json({ message: "Ya existe un proveedor con ese NIT" });
    }

    const supplier = await prisma.supplier.create({
      data: { name, nit: nit || null, phone: phone || null },
    });

    res.status(201).json(supplier);
  } catch (error) {
    console.error("Error al crear proveedor:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Editar proveedor
router.put("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const { name, nit, phone } = req.body;

    const existing = await prisma.supplier.findUnique({ where: { id: Number(id) } });
    if (!existing) return res.status(404).json({ message: "Proveedor no encontrado" });

    if (nit && nit !== existing.nit) {
      const dup = await prisma.supplier.findFirst({ where: { nit, id: { not: Number(id) } } });
      if (dup) return res.status(400).json({ message: "Ya existe otro proveedor con ese NIT" });
    }

    const supplier = await prisma.supplier.update({
      where: { id: Number(id) },
      data: {
        ...(name && { name }),
        ...(nit !== undefined && { nit: nit || null }),
        ...(phone !== undefined && { phone: phone || null }),
      },
    });

    res.json(supplier);
  } catch (error) {
    console.error("Error al editar proveedor:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// DELETE /:id — Eliminar proveedor
router.delete("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const existing = await prisma.supplier.findUnique({
      where: { id: Number(req.params.id) },
      include: { _count: { select: { costs: true } } },
    });
    if (!existing) return res.status(404).json({ message: "Proveedor no encontrado" });

    if (existing._count.costs > 0) {
      return res.status(400).json({ message: "No se puede eliminar: tiene costos asociados" });
    }

    await prisma.supplier.delete({ where: { id: Number(req.params.id) } });
    res.json({ message: "Proveedor eliminado" });
  } catch (error) {
    console.error("Error al eliminar proveedor:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
