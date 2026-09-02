import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate, authorize } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

// GET / — Listar todo el inventario con información de producto y ubicación
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { locationId, lowStock } = req.query;

    const where: any = {};

    if (req.user?.role === "TIENDA" && req.user.locationId) {
      where.locationId = req.user.locationId;
    } else if (locationId && typeof locationId === "string") {
      where.locationId = Number(locationId);
    }

    const inventories = await prisma.inventory.findMany({
      where,
      include: {
        product: true,
        location: true,
      },
      orderBy: { product: { name: "asc" } },
    });

    let result = inventories.map((inv) => ({
      id: inv.id,
      productId: inv.productId,
      locationId: inv.locationId,
      stock: inv.stock,
      minStock: inv.minStock,
      productName: inv.product.name,
      itemCode: inv.product.itemCode,
      brand: inv.product.brand,
      model: inv.product.model,
      locationName: inv.location.name,
      locationType: inv.location.type,
    }));

    if (lowStock === "true") {
      result = result.filter((r) => r.stock <= r.minStock);
    }

    res.json(result);
  } catch (error) {
    console.error("Error al listar inventario:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /product/:productId — Stock por ubicación de un producto
router.get("/product/:productId", async (req: AuthRequest, res: Response) => {
  try {
    const productId = Number(req.params.productId);
    const inventories = await prisma.inventory.findMany({
      where: { productId },
      include: { location: true },
      orderBy: { location: { name: "asc" } },
    });

    const stockTotal = inventories.reduce((sum, inv) => sum + inv.stock, 0);

    res.json({
      productId,
      stockTotal,
      locations: inventories.map((inv) => ({
        locationId: inv.location.id,
        locationName: inv.location.name,
        locationType: inv.location.type,
        stock: inv.stock,
        minStock: inv.minStock,
      })),
    });
  } catch (error) {
    console.error("Error al obtener stock:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Actualizar stock manualmente (solo ADMIN)
router.put("/:id", authorize("ADMIN"), async (req: AuthRequest, res: Response) => {
  try {
    const id = Number(req.params.id);
    const { stock, minStock } = req.body;

    const existing = await prisma.inventory.findUnique({ where: { id } });
    if (!existing) {
      return res.status(404).json({ message: "Registro de inventario no encontrado" });
    }

    const data: any = {};
    if (stock != null) {
      const s = Number(stock);
      if (!Number.isInteger(s) || s < 0) {
        return res.status(400).json({ message: "El stock debe ser un entero mayor o igual a 0" });
      }
      data.stock = s;
    }
    if (minStock != null) {
      const m = Number(minStock);
      if (!Number.isInteger(m) || m < 0) {
        return res.status(400).json({ message: "El stock mínimo debe ser un entero mayor o igual a 0" });
      }
      data.minStock = m;
    }

    const updated = await prisma.inventory.update({
      where: { id },
      data,
      include: { product: true, location: true },
    });

    await prisma.auditLog.create({
      data: {
        userId: req.user!.userId,
        action: "UPDATE_INVENTORY",
        targetType: "INVENTORY",
        targetId: id,
        oldValue: { stock: existing.stock, minStock: existing.minStock },
        newValue: { stock: updated.stock, minStock: updated.minStock },
      },
    });

    res.json(updated);
  } catch (error) {
    console.error("Error al actualizar inventario:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
