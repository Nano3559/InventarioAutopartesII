import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate, authorize } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import { parseId, parseString } from "../../shared/middlewares/validate";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);
router.use(authorize("ADMIN"));

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

    const pg = Math.max(1, Number(page) || 1);
    const take = Math.min(100, Math.max(1, Number(limit) || 50));
    const skip = (pg - 1) * take;

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
      pagination: { total, page: pg, limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar proveedores:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /:id — Detalle de proveedor
router.get("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const id = parseId(req.params.id);
    const supplier = await prisma.supplier.findUnique({
      where: { id },
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
  } catch (error: any) {
    if (error.message === "ID inválido") return res.status(400).json({ message: error.message });
    console.error("Error al obtener proveedor:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Crear proveedor
router.post("/", async (req: AuthRequest, res: Response) => {
  try {
    const name = parseString(req.body.name, "Nombre", { required: true, max: 255 });
    const nit = parseString(req.body.nit, "NIT", { max: 20 });
    const phone = parseString(req.body.phone, "Teléfono", { max: 20 });

    if (nit) {
      const existing = await prisma.supplier.findFirst({ where: { nit } });
      if (existing) return res.status(400).json({ message: "Ya existe un proveedor con ese NIT" });
    }

    const supplier = await prisma.supplier.create({
      data: { name: name!, nit, phone },
    });
    res.status(201).json(supplier);
  } catch (error: any) {
    if (error.message && !error.message.includes("Prisma")) {
      return res.status(400).json({ message: error.message });
    }
    console.error("Error al crear proveedor:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Editar proveedor
router.put("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const id = parseId(req.params.id);
    const existing = await prisma.supplier.findUnique({ where: { id } });
    if (!existing) return res.status(404).json({ message: "Proveedor no encontrado" });

    const name = parseString(req.body.name, "Nombre", { max: 255 });
    const nit = parseString(req.body.nit, "NIT", { max: 20 });
    const phone = parseString(req.body.phone, "Teléfono", { max: 20 });

    if (name !== null && name!.trim().length === 0) {
      return res.status(400).json({ message: "El nombre no puede estar vacío" });
    }

    if (nit !== null && nit !== existing.nit) {
      const dup = await prisma.supplier.findFirst({ where: { nit, id: { not: id } } });
      if (dup) return res.status(400).json({ message: "Ya existe otro proveedor con ese NIT" });
    }

    const supplier = await prisma.supplier.update({
      where: { id },
      data: {
        ...(name !== null && name !== undefined && { name: name! }),
        ...(req.body.nit !== undefined && { nit }),
        ...(req.body.phone !== undefined && { phone }),
      },
    });
    res.json(supplier);
  } catch (error: any) {
    if (error.message && !error.message.includes("Prisma")) {
      return res.status(400).json({ message: error.message });
    }
    console.error("Error al editar proveedor:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// DELETE /:id — Eliminar proveedor
router.delete("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const id = parseId(req.params.id);
    const existing = await prisma.supplier.findUnique({
      where: { id },
      include: { _count: { select: { costs: true } } },
    });
    if (!existing) return res.status(404).json({ message: "Proveedor no encontrado" });
    if (existing._count.costs > 0) {
      return res.status(400).json({ message: "No se puede eliminar: tiene costos asociados" });
    }
    await prisma.supplier.delete({ where: { id } });
    res.json({ message: "Proveedor eliminado" });
  } catch (error: any) {
    if (error.message === "ID inválido") return res.status(400).json({ message: error.message });
    console.error("Error al eliminar proveedor:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
