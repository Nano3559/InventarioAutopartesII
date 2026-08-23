import { Router, Request, Response } from "express";
import { PrismaClient, RequestStatus } from "@prisma/client";

const router = Router();
const prisma = new PrismaClient();

// GET / — Listar solicitudes con filtros
router.get("/", async (req: Request, res: Response) => {
  try {
    const { status, locationId, page = "1", limit = "20" } = req.query;

    const where: any = {};
    if (status && typeof status === "string") where.status = status as RequestStatus;
    if (locationId && typeof locationId === "string") where.locationId = Number(locationId);

    const skip = (Number(page) - 1) * Number(limit);
    const take = Number(limit);

    const [requests, total] = await Promise.all([
      prisma.productRequest.findMany({
        where,
        include: {
          product: { select: { id: true, name: true, itemCode: true, brand: true, model: true } },
          location: { select: { id: true, name: true, type: true } },
          requestedBy: { select: { id: true, name: true, email: true } },
        },
        skip,
        take,
        orderBy: { date: "desc" },
      }),
      prisma.productRequest.count({ where }),
    ]);

    res.json({
      requests,
      pagination: { total, page: Number(page), limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar solicitudes:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Crear solicitud (tienda pide a almacén)
router.post("/", async (req: Request, res: Response) => {
  try {
    const { productId, quantity, locationId, requestedById } = req.body;

    if (!productId || !quantity || !locationId || !requestedById) {
      return res.status(400).json({ message: "Campos obligatorios: productId, quantity, locationId, requestedById" });
    }

    const product = await prisma.product.findUnique({ where: { id: productId } });
    if (!product) {
      return res.status(404).json({ message: "Producto no encontrado" });
    }

    const location = await prisma.location.findUnique({ where: { id: locationId } });
    if (!location) {
      return res.status(404).json({ message: "Ubicación no encontrada" });
    }

    const request = await prisma.productRequest.create({
      data: { productId, quantity, locationId, requestedById },
      include: {
        product: { select: { name: true, itemCode: true } },
        location: { select: { name: true } },
      },
    });

    res.status(201).json(request);
  } catch (error) {
    console.error("Error al crear solicitud:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Cambiar estado de solicitud
router.put("/:id", async (req: Request, res: Response) => {
  try {
    const id = Number(req.params.id);
    const { status } = req.body;

    if (!status) {
      return res.status(400).json({ message: "Campo obligatorio: status" });
    }

    const validStatuses: RequestStatus[] = ["PENDIENTE", "EN_PREPARACION", "ENVIADO", "RECIBIDO", "CANCELADO"];
    if (!validStatuses.includes(status)) {
      return res.status(400).json({ message: `Estado inválido. Valores válidos: ${validStatuses.join(", ")}` });
    }

    const existing = await prisma.productRequest.findUnique({ where: { id } });
    if (!existing) {
      return res.status(404).json({ message: "Solicitud no encontrada" });
    }

    const updated = await prisma.productRequest.update({
      where: { id },
      data: { status },
      include: {
        product: { select: { name: true, itemCode: true } },
        location: { select: { name: true } },
        requestedBy: { select: { name: true } },
      },
    });

    res.json(updated);
  } catch (error) {
    console.error("Error al actualizar solicitud:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// DELETE /:id — Cancelar solicitud
router.delete("/:id", async (req: Request, res: Response) => {
  try {
    const id = Number(req.params.id);
    const existing = await prisma.productRequest.findUnique({ where: { id } });

    if (!existing) {
      return res.status(404).json({ message: "Solicitud no encontrada" });
    }

    await prisma.productRequest.update({
      where: { id },
      data: { status: "CANCELADO" },
    });

    res.json({ message: "Solicitud cancelada" });
  } catch (error) {
    console.error("Error al cancelar solicitud:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
