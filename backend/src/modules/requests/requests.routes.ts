import { Router, Response } from "express";
import { PrismaClient, RequestStatus } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import { parseId, parsePositiveInt } from "../../shared/middlewares/validate";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

const VALID_STATUSES: RequestStatus[] = ["PENDIENTE", "EN_PREPARACION", "ENVIADO", "RECIBIDO", "CANCELADO"];

// GET / — Listar solicitudes con filtros
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { status, locationId, page = "1", limit = "20" } = req.query;

    const where: any = {};
    if (status && typeof status === "string") where.status = status as RequestStatus;
    if (locationId && typeof locationId === "string") where.locationId = Number(locationId);

    const pg = Math.max(1, Number(page) || 1);
    const take = Math.min(100, Math.max(1, Number(limit) || 20));
    const skip = (pg - 1) * take;

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
      pagination: { total, page: pg, limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar solicitudes:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Crear solicitud (tienda pide a almacén)
router.post("/", async (req: AuthRequest, res: Response) => {
  try {
    const productId = parsePositiveInt(req.body.productId, "Producto");
    const quantity = parsePositiveInt(req.body.quantity, "Cantidad");
    const locationId = parsePositiveInt(req.body.locationId, "Ubicación");
    const requestedById = parsePositiveInt(req.body.requestedById, "Usuario solicitante");

    if (quantity <= 0) return res.status(400).json({ message: "La cantidad debe ser mayor a 0" });

    const [product, location, user] = await Promise.all([
      prisma.product.findUnique({ where: { id: productId } }),
      prisma.location.findUnique({ where: { id: locationId } }),
      prisma.user.findUnique({ where: { id: requestedById } }),
    ]);

    if (!product) return res.status(404).json({ message: "Producto no encontrado" });
    if (!location) return res.status(404).json({ message: "Ubicación no encontrada" });
    if (!user) return res.status(404).json({ message: "Usuario no encontrado" });

    const request = await prisma.productRequest.create({
      data: { productId, quantity, locationId, requestedById },
      include: {
        product: { select: { name: true, itemCode: true } },
        location: { select: { name: true } },
      },
    });

    res.status(201).json(request);
  } catch (error: any) {
    if (error.message && !error.message.includes("Prisma")) {
      return res.status(400).json({ message: error.message });
    }
    console.error("Error al crear solicitud:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Cambiar estado de solicitud
router.put("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const id = parseId(req.params.id);
    const { status } = req.body;

    if (!status) return res.status(400).json({ message: "Campo obligatorio: status" });
    if (!VALID_STATUSES.includes(status)) {
      return res.status(400).json({ message: `Estado inválido. Valores válidos: ${VALID_STATUSES.join(", ")}` });
    }

    const existing = await prisma.productRequest.findUnique({ where: { id } });
    if (!existing) return res.status(404).json({ message: "Solicitud no encontrada" });

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
  } catch (error: any) {
    if (error.message === "ID inválido") return res.status(400).json({ message: error.message });
    console.error("Error al actualizar solicitud:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// DELETE /:id — Cancelar solicitud
router.delete("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const id = parseId(req.params.id);
    const existing = await prisma.productRequest.findUnique({ where: { id } });
    if (!existing) return res.status(404).json({ message: "Solicitud no encontrada" });

    if (existing.status === "RECIBIDO" || existing.status === "CANCELADO") {
      return res.status(400).json({ message: "No se puede cancelar una solicitud ya recibida o cancelada" });
    }

    await prisma.productRequest.update({ where: { id }, data: { status: "CANCELADO" } });
    res.json({ message: "Solicitud cancelada" });
  } catch (error: any) {
    if (error.message === "ID inválido") return res.status(400).json({ message: error.message });
    console.error("Error al cancelar solicitud:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
