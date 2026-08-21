import { Router, Request, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

// GET / — Listar clientes con búsqueda
router.get("/", async (req: Request, res: Response) => {
  try {
    const { search, page = "1", limit = "20" } = req.query;

    const where: any = {};
    if (search && typeof search === "string") {
      where.OR = [
        { name: { contains: search, mode: "insensitive" } },
        { nit: { contains: search, mode: "insensitive" } },
        { phone: { contains: search } },
      ];
    }

    const skip = (Number(page) - 1) * Number(limit);
    const take = Number(limit);

    const [customers, total] = await Promise.all([
      prisma.customer.findMany({
        where,
        skip,
        take,
        orderBy: { name: "asc" },
      }),
      prisma.customer.count({ where }),
    ]);

    res.json({
      customers,
      pagination: { total, page: Number(page), limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar clientes:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /:id — Detalle de cliente
router.get("/:id", async (req: Request, res: Response) => {
  try {
    const customer = await prisma.customer.findUnique({
      where: { id: Number(req.params.id) },
      include: { sales: { orderBy: { saleDate: "desc" }, take: 10 } },
    });

    if (!customer) {
      return res.status(404).json({ message: "Cliente no encontrado" });
    }

    res.json(customer);
  } catch (error) {
    console.error("Error al obtener cliente:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Crear cliente (o buscar existente por NIT)
router.post("/", async (req: Request, res: Response) => {
  try {
    const { name, nit, phone } = req.body;

    if (!name) {
      return res.status(400).json({ message: "El nombre es obligatorio" });
    }

    if (nit) {
      const existing = await prisma.customer.findFirst({ where: { nit } });
      if (existing) {
        return res.json(existing);
      }
    }

    const customer = await prisma.customer.create({
      data: { name, nit: nit || null, phone: phone || null },
    });

    res.status(201).json(customer);
  } catch (error) {
    console.error("Error al crear cliente:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Editar cliente
router.put("/:id", async (req: Request, res: Response) => {
  try {
    const id = Number(req.params.id);
    const existing = await prisma.customer.findUnique({ where: { id } });
    if (!existing) {
      return res.status(404).json({ message: "Cliente no encontrado" });
    }

    const { name, nit, phone } = req.body;
    const customer = await prisma.customer.update({
      where: { id },
      data: {
        name: name !== undefined ? name : existing.name,
        nit: nit !== undefined ? (nit || null) : existing.nit,
        phone: phone !== undefined ? (phone || null) : existing.phone,
      },
    });

    res.json(customer);
  } catch (error) {
    console.error("Error al editar cliente:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
