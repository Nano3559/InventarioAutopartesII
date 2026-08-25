import { Router, Request, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";
import { parseId, parseString } from "../../shared/middlewares/validate";

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

    const pg = Math.max(1, Number(page) || 1);
    const take = Math.min(100, Math.max(1, Number(limit) || 20));
    const skip = (pg - 1) * take;

    const [customers, total] = await Promise.all([
      prisma.customer.findMany({ where, skip, take, orderBy: { name: "asc" } }),
      prisma.customer.count({ where }),
    ]);

    res.json({
      customers,
      pagination: { total, page: pg, limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar clientes:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /:id — Detalle de cliente
router.get("/:id", async (req: Request, res: Response) => {
  try {
    const id = parseId(req.params.id);
    const customer = await prisma.customer.findUnique({
      where: { id },
      include: { sales: { orderBy: { saleDate: "desc" }, take: 10 } },
    });
    if (!customer) return res.status(404).json({ message: "Cliente no encontrado" });
    res.json(customer);
  } catch (error: any) {
    if (error.message === "ID inválido") return res.status(400).json({ message: error.message });
    console.error("Error al obtener cliente:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Crear cliente (o buscar existente por NIT)
router.post("/", async (req: Request, res: Response) => {
  try {
    const name = parseString(req.body.name, "Nombre", { required: true, max: 255 });
    const nit = parseString(req.body.nit, "NIT", { max: 20 });
    const phone = parseString(req.body.phone, "Teléfono", { max: 20 });

    if (nit) {
      const existing = await prisma.customer.findFirst({ where: { nit } });
      if (existing) return res.json(existing);
    }

    const customer = await prisma.customer.create({
      data: { name: name!, nit, phone },
    });

    res.status(201).json(customer);
  } catch (error: any) {
    if (error.message && !error.message.includes("Prisma")) {
      return res.status(400).json({ message: error.message });
    }
    console.error("Error al crear cliente:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Editar cliente
router.put("/:id", async (req: Request, res: Response) => {
  try {
    const id = parseId(req.params.id);
    const existing = await prisma.customer.findUnique({ where: { id } });
    if (!existing) return res.status(404).json({ message: "Cliente no encontrado" });

    const name = parseString(req.body.name, "Nombre", { max: 255 });
    const nit = parseString(req.body.nit, "NIT", { max: 20 });
    const phone = parseString(req.body.phone, "Teléfono", { max: 20 });

    if (name !== null && name!.trim().length === 0) {
      return res.status(400).json({ message: "El nombre no puede estar vacío" });
    }

    const customer = await prisma.customer.update({
      where: { id },
      data: {
        name: name !== null && name !== undefined ? name! : existing.name,
        nit: req.body.nit !== undefined ? nit : existing.nit,
        phone: req.body.phone !== undefined ? phone : existing.phone,
      },
    });

    res.json(customer);
  } catch (error: any) {
    if (error.message && !error.message.includes("Prisma")) {
      return res.status(400).json({ message: error.message });
    }
    console.error("Error al editar cliente:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
