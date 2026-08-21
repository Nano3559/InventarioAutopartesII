import { Router, Request, Response } from "express";
import { PrismaClient } from "@prisma/client";

const router = Router();
const prisma = new PrismaClient();

// GET / — Listar productos con filtros, búsqueda y paginación
router.get("/", async (req: Request, res: Response) => {
  try {
    const {
      search, brand, manufacturer, model, year, oemCode, factoryCode,
      categoryId, page = "1", limit = "20",
    } = req.query;

    const where: any = {};
    const AND: any[] = [];

    if (search && typeof search === "string") {
      AND.push({
        OR: [
          { name: { contains: search, mode: "insensitive" } },
          { itemCode: { contains: search, mode: "insensitive" } },
          { oemCode: { contains: search, mode: "insensitive" } },
          { factoryCode: { contains: search, mode: "insensitive" } },
          { manufacturer: { contains: search, mode: "insensitive" } },
          { brand: { contains: search, mode: "insensitive" } },
          { model: { contains: search, mode: "insensitive" } },
        ],
      });
    }

    if (brand && typeof brand === "string") AND.push({ brand: { equals: brand, mode: "insensitive" } });
    if (manufacturer && typeof manufacturer === "string") AND.push({ manufacturer: { equals: manufacturer, mode: "insensitive" } });
    if (model && typeof model === "string") AND.push({ model: { equals: model, mode: "insensitive" } });
    if (year && typeof year === "string") AND.push({ year: { contains: year } });
    if (oemCode && typeof oemCode === "string") AND.push({ oemCode: { contains: oemCode, mode: "insensitive" } });
    if (factoryCode && typeof factoryCode === "string") AND.push({ factoryCode: { contains: factoryCode, mode: "insensitive" } });
    if (categoryId && typeof categoryId === "string") AND.push({ categoryId: Number(categoryId) });

    if (AND.length > 0) where.AND = AND;

    const skip = (Number(page) - 1) * Number(limit);
    const take = Number(limit);

    const [products, total] = await Promise.all([
      prisma.product.findMany({
        where,
        include: {
          category: true,
          inventories: { include: { location: true } },
        },
        skip,
        take,
        orderBy: { name: "asc" },
      }),
      prisma.product.count({ where }),
    ]);

    const result = products.map((p) => {
      const stockTotal = p.inventories.reduce((sum, inv) => sum + inv.stock, 0);
      return {
        id: p.id,
        itemCode: p.itemCode,
        manufacturer: p.manufacturer,
        name: p.name,
        brand: p.brand,
        model: p.model,
        year: p.year,
        detail: p.detail,
        quality: p.quality,
        image: p.image,
        oemCode: p.oemCode,
        factoryCode: p.factoryCode,
        price1: p.price1,
        price2: p.price2,
        wholesalePrice: p.wholesalePrice,
        cost: p.cost,
        categoryId: p.categoryId,
        category: p.category?.name || null,
        stock: stockTotal,
      };
    });

    res.json({
      products: result,
      pagination: { total, page: Number(page), limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar productos:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /filters — Marcas, fabricantes, categorías disponibles
router.get("/filters", async (_req: Request, res: Response) => {
  try {
    const [brands, manufacturers, categories] = await Promise.all([
      prisma.product.findMany({ select: { brand: true }, distinct: ["brand"], orderBy: { brand: "asc" } }),
      prisma.product.findMany({ select: { manufacturer: true }, distinct: ["manufacturer"], orderBy: { manufacturer: "asc" } }),
      prisma.category.findMany({ select: { id: true, name: true }, orderBy: { name: "asc" } }),
    ]);
    res.json({
      brands: brands.map((b) => b.brand),
      manufacturers: manufacturers.map((m) => m.manufacturer),
      categories,
    });
  } catch (error) {
    console.error("Error al obtener filtros:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /:id — Detalle de producto con stock por ubicación
router.get("/:id", async (req: Request, res: Response) => {
  try {
    const product = await prisma.product.findUnique({
      where: { id: Number(req.params.id) },
      include: {
        category: true,
        inventories: { include: { location: true } },
        importers: { include: { importer: true } },
      },
    });

    if (!product) {
      return res.status(404).json({ message: "Producto no encontrado" });
    }

    const stockTotal = product.inventories.reduce((sum, inv) => sum + inv.stock, 0);

    res.json({
      id: product.id,
      itemCode: product.itemCode,
      manufacturer: product.manufacturer,
      name: product.name,
      brand: product.brand,
      model: product.model,
      year: product.year,
      detail: product.detail,
      quality: product.quality,
      image: product.image,
      oemCode: product.oemCode,
      factoryCode: product.factoryCode,
      price1: product.price1,
      price2: product.price2,
      wholesalePrice: product.wholesalePrice,
      cost: product.cost,
      categoryId: product.categoryId,
      category: product.category?.name || null,
      stock: stockTotal,
      stockByLocation: product.inventories.map((inv) => ({
        locationId: inv.location.id,
        locationName: inv.location.name,
        locationType: inv.location.type,
        stock: inv.stock,
        minStock: inv.minStock,
      })),
      importers: product.importers.map((pi) => ({
        id: pi.importer.id,
        name: pi.importer.name,
        phone: pi.importer.phone,
        city: pi.importer.city,
      })),
    });
  } catch (error) {
    console.error("Error al obtener producto:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Crear producto
router.post("/", async (req: Request, res: Response) => {
  try {
    const { itemCode, manufacturer, name, brand, model, year, detail, oemCode, factoryCode, price1, price2, wholesalePrice, cost, categoryId, image } = req.body;

    if (!itemCode || !manufacturer || !name || !brand || !model || !year || price1 == null) {
      return res.status(400).json({ message: "Campos obligatorios: itemCode, manufacturer, name, brand, model, year, price1" });
    }

    const existing = await prisma.product.findUnique({ where: { itemCode } });
    if (existing) {
      return res.status(409).json({ message: `Ya existe un producto con código "${itemCode}"` });
    }

    const product = await prisma.product.create({
      data: {
        itemCode,
        manufacturer,
        name,
        brand,
        model,
        year,
        detail: detail || null,
        oemCode: oemCode || null,
        factoryCode: factoryCode || null,
        price1,
        price2: price2 ?? price1,
        wholesalePrice: wholesalePrice ?? null,
        cost: cost ?? null,
        categoryId: categoryId ?? null,
        image: image || null,
      },
    });

    res.status(201).json(product);
  } catch (error) {
    console.error("Error al crear producto:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Editar producto
router.put("/:id", async (req: Request, res: Response) => {
  try {
    const id = Number(req.params.id);
    const existing = await prisma.product.findUnique({ where: { id } });
    if (!existing) {
      return res.status(404).json({ message: "Producto no encontrado" });
    }

    const { itemCode, manufacturer, name, brand, model, year, detail, oemCode, factoryCode, price1, price2, wholesalePrice, cost, categoryId, image } = req.body;

    if (itemCode && itemCode !== existing.itemCode) {
      const dup = await prisma.product.findUnique({ where: { itemCode } });
      if (dup) {
        return res.status(409).json({ message: `Ya existe un producto con código "${itemCode}"` });
      }
    }

    const product = await prisma.product.update({
      where: { id },
      data: {
        ...(itemCode && { itemCode }),
        ...(manufacturer && { manufacturer }),
        ...(name && { name }),
        ...(brand && { brand }),
        ...(model && { model }),
        ...(year && { year }),
        detail: detail !== undefined ? detail : existing.detail,
        oemCode: oemCode !== undefined ? oemCode : existing.oemCode,
        factoryCode: factoryCode !== undefined ? factoryCode : existing.factoryCode,
        ...(price1 != null && { price1 }),
        ...(price2 != null && { price2 }),
        wholesalePrice: wholesalePrice !== undefined ? wholesalePrice : existing.wholesalePrice,
        cost: cost !== undefined ? cost : existing.cost,
        categoryId: categoryId !== undefined ? (categoryId ?? null) : existing.categoryId,
        image: image !== undefined ? (image || null) : existing.image,
      },
    });

    res.json(product);
  } catch (error) {
    console.error("Error al editar producto:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// DELETE /:id — Eliminar producto
router.delete("/:id", async (req: Request, res: Response) => {
  try {
    const id = Number(req.params.id);
    const existing = await prisma.product.findUnique({
      where: { id },
      include: { saleItems: { take: 1 } },
    });

    if (!existing) {
      return res.status(404).json({ message: "Producto no encontrado" });
    }

    if (existing.saleItems.length > 0) {
      return res.status(409).json({ message: "No se puede eliminar: el producto tiene ventas asociadas" });
    }

    await prisma.inventory.deleteMany({ where: { productId: id } });
    await prisma.productImporter.deleteMany({ where: { productId: id } });
    await prisma.product.delete({ where: { id } });

    res.json({ message: "Producto eliminado correctamente" });
  } catch (error) {
    console.error("Error al eliminar producto:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
