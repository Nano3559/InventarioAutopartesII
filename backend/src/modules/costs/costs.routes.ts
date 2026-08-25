import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import multer from "multer";
import path from "path";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, path.join(__dirname, "../../../uploads")),
  filename: (_req, file, cb) => {
    const unique = `${Date.now()}-${Math.round(Math.random() * 1e9)}`;
    cb(null, `${unique}${path.extname(file.originalname)}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 10 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const allowed = [".pdf", ".jpg", ".jpeg", ".png"];
    const ext = path.extname(file.originalname).toLowerCase();
    cb(null, allowed.includes(ext));
  },
});

// GET / — Listar costos con filtros
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { productId, supplierId, search, page = "1", limit = "20" } = req.query;

    const where: any = {};
    if (productId && typeof productId === "string") where.productId = Number(productId);
    if (supplierId && typeof supplierId === "string") where.supplierId = Number(supplierId);
    if (search && typeof search === "string") {
      where.OR = [
        { product: { name: { contains: search, mode: "insensitive" } } },
        { product: { itemCode: { contains: search, mode: "insensitive" } } },
        { product: { brand: { contains: search, mode: "insensitive" } } },
        { supplier: { name: { contains: search, mode: "insensitive" } } },
      ];
    }

    const skip = (Number(page) - 1) * Number(limit);
    const take = Number(limit);

    const [costs, total] = await Promise.all([
      prisma.cost.findMany({
        where,
        include: {
          product: { select: { id: true, name: true, itemCode: true, brand: true, model: true } },
          supplier: { select: { id: true, name: true, nit: true, phone: true } },
        },
        orderBy: { date: "desc" },
        skip,
        take,
      }),
      prisma.cost.count({ where }),
    ]);

    res.json({
      costs: costs.map((c) => ({
        id: c.id,
        productId: c.productId,
        productName: c.product.name,
        itemCode: c.product.itemCode,
        brand: c.product.brand,
        model: c.product.model,
        supplierId: c.supplierId,
        supplierName: c.supplier.name,
        invoiceUrl: c.invoiceUrl,
        exchangeRate: c.exchangeRate ? Number(c.exchangeRate) : null,
        costPrice: Number(c.costPrice),
        percentage: c.percentage ? Number(c.percentage) : null,
        date: c.date,
      })),
      pagination: { total, page: Number(page), limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar costos:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Registrar costo con factura
router.post("/", upload.single("invoice"), async (req: AuthRequest, res: Response) => {
  try {
    const { productId, supplierId, exchangeRate, percentage, costPrice } = req.body;

    if (!productId || !supplierId || !costPrice) {
      return res.status(400).json({ message: "Campos obligatorios: productId, supplierId, costPrice" });
    }

    const product = await prisma.product.findUnique({ where: { id: Number(productId) } });
    if (!product) return res.status(404).json({ message: "Producto no encontrado" });

    const supplier = await prisma.supplier.findUnique({ where: { id: Number(supplierId) } });
    if (!supplier) return res.status(404).json({ message: "Proveedor no encontrado" });

    const cost = await prisma.cost.create({
      data: {
        productId: Number(productId),
        supplierId: Number(supplierId),
        costPrice: Number(costPrice),
        exchangeRate: exchangeRate ? Number(exchangeRate) : null,
        percentage: percentage ? Number(percentage) : null,
        invoiceUrl: req.file ? req.file.filename : null,
      },
      include: {
        product: { select: { name: true, itemCode: true } },
        supplier: { select: { name: true } },
      },
    });

    res.status(201).json({
      id: cost.id,
      productName: cost.product.name,
      itemCode: cost.product.itemCode,
      supplierName: cost.supplier.name,
      costPrice: Number(cost.costPrice),
      exchangeRate: cost.exchangeRate ? Number(cost.exchangeRate) : null,
      percentage: cost.percentage ? Number(cost.percentage) : null,
      invoiceUrl: cost.invoiceUrl,
      date: cost.date,
    });
  } catch (error) {
    console.error("Error al registrar costo:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Editar costo
router.put("/:id", upload.single("invoice"), async (req: AuthRequest, res: Response) => {
  try {
    const { id } = req.params;
    const { productId, supplierId, exchangeRate, percentage, costPrice } = req.body;

    const existing = await prisma.cost.findUnique({ where: { id: Number(id) } });
    if (!existing) return res.status(404).json({ message: "Costo no encontrado" });

    const cost = await prisma.cost.update({
      where: { id: Number(id) },
      data: {
        ...(productId && { productId: Number(productId) }),
        ...(supplierId && { supplierId: Number(supplierId) }),
        ...(costPrice && { costPrice: Number(costPrice) }),
        ...(exchangeRate !== undefined && { exchangeRate: exchangeRate ? Number(exchangeRate) : null }),
        ...(percentage !== undefined && { percentage: percentage ? Number(percentage) : null }),
        ...(req.file && { invoiceUrl: req.file.filename }),
      },
      include: {
        product: { select: { name: true, itemCode: true } },
        supplier: { select: { name: true } },
      },
    });

    res.json({
      id: cost.id,
      productName: cost.product.name,
      itemCode: cost.product.itemCode,
      supplierName: cost.supplier.name,
      costPrice: Number(cost.costPrice),
      exchangeRate: cost.exchangeRate ? Number(cost.exchangeRate) : null,
      percentage: cost.percentage ? Number(cost.percentage) : null,
      invoiceUrl: cost.invoiceUrl,
      date: cost.date,
    });
  } catch (error) {
    console.error("Error al editar costo:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// DELETE /:id — Eliminar costo
router.delete("/:id", async (req: AuthRequest, res: Response) => {
  try {
    const existing = await prisma.cost.findUnique({ where: { id: Number(req.params.id) } });
    if (!existing) return res.status(404).json({ message: "Costo no encontrado" });

    await prisma.cost.delete({ where: { id: Number(req.params.id) } });
    res.json({ message: "Costo eliminado" });
  } catch (error) {
    console.error("Error al eliminar costo:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
