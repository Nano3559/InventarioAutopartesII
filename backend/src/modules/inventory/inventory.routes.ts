import { Router, Request, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate, authorize } from "../../shared/middlewares/auth";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

// GET / — Listar todo el inventario con información de producto y ubicación
router.get("/", async (req: Request, res: Response) => {
  try {
    const { locationId, lowStock } = req.query;

    const where: any = {};
    if (locationId && typeof locationId === "string") where.locationId = Number(locationId);

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
router.get("/product/:productId", async (req: Request, res: Response) => {
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
router.put("/:id", authorize("ADMIN"), async (req: Request, res: Response) => {
  try {
    const id = Number(req.params.id);
    const { stock, minStock } = req.body;

    const existing = await prisma.inventory.findUnique({ where: { id } });
    if (!existing) {
      return res.status(404).json({ message: "Registro de inventario no encontrado" });
    }

    const updated = await prisma.inventory.update({
      where: { id },
      data: {
        ...(stock != null && { stock }),
        ...(minStock != null && { minStock }),
      },
      include: { product: true, location: true },
    });

    res.json(updated);
  } catch (error) {
    console.error("Error al actualizar inventario:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
