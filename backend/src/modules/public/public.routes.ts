import { Router, Request, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { yearMatchesRanges } from "../../utils/yearRanges";

const router = Router();
const prisma = new PrismaClient();

// GET /api/public/products - Catálogo público con filtros
router.get("/products", async (req: Request, res: Response) => {
  try {
    const { search, brand, model, year, category, detalles, page = "1", limit = "12" } = req.query;

    const where: any = {};
    const AND: any[] = [];

    if (search && typeof search === "string") {
      AND.push({
        OR: [
          { name: { contains: search, mode: "insensitive" } },
          { oemCode: { contains: search, mode: "insensitive" } },
          { factoryCode: { contains: search, mode: "insensitive" } },
          { detail: { contains: search, mode: "insensitive" } },
        ],
      });
    }

    if (brand && typeof brand === "string") {
      AND.push({ brand: { contains: brand, mode: "insensitive" } });
    }

    if (model && typeof model === "string") {
      AND.push({ model: { contains: model, mode: "insensitive" } });
    }

    if (year && typeof year === "string") {
      const searchYear = parseInt(year, 10);
      if (!isNaN(searchYear)) {
        AND.push({ id: { gt: 0 } });
      }
    }

    if (category && typeof category === "string") {
      AND.push({ category: { name: { equals: category, mode: "insensitive" } } });
    }

    if (detalles && typeof detalles === "string") {
      AND.push({ detalles: { equals: detalles, mode: "insensitive" } });
    }

    if (AND.length > 0) where.AND = AND;

    const skip = (Number(page) - 1) * Number(limit);
    const hasYearFilter = year && typeof year === "string";

    let allProducts = await prisma.product.findMany({
      where,
      include: {
        category: true,
        inventories: true,
        importers: { include: { importer: true } },
      },
      orderBy: { name: "asc" },
    });

    if (hasYearFilter) {
      const searchYear = parseInt(year as string, 10);
      if (!isNaN(searchYear)) {
        allProducts = allProducts.filter((p) => yearMatchesRanges(searchYear, p.year));
      }
    }

    const total = allProducts.length;
    const products = allProducts.slice(skip, skip + Number(limit));

    const productsWithStock = products.map((p) => {
      const stockTotal = p.inventories.reduce((sum, inv) => sum + inv.stock, 0);
      let availability = "Consultar disponibilidad";
      if (stockTotal > 10) availability = "Disponible";
      else if (stockTotal > 0) availability = "Pocas unidades";

      return {
        id: p.id,
        itemCode: p.itemCode,
        name: p.name,
        brand: p.brand,
        model: p.model,
        year: p.year,
        detail: p.detail,
        detalles: p.detalles,
        image: p.image,
        oemCode: p.oemCode,
        factoryCode: p.factoryCode,
        price1: p.price1,
        price2: p.price2,
        category: p.category?.name || null,
        availability,
        importers: p.importers.map((pi) => ({
          id: pi.importer.id,
          name: pi.importer.name,
          phone: pi.importer.phone,
          city: pi.importer.city,
        })),
      };
    });

    res.json({
      products: productsWithStock,
      pagination: {
        total,
        page: Number(page),
        limit: Number(limit),
        pages: Math.ceil(total / Number(limit)),
      },
    });
  } catch (error) {
    console.error("Error en catálogo público:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /api/public/products/:id - Detalle público de producto
router.get("/products/:id", async (req: Request, res: Response) => {
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
    let availability = "Consultar disponibilidad";
    if (stockTotal > 10) availability = "Disponible";
    else if (stockTotal > 0) availability = "Pocas unidades";

    res.json({
      id: product.id,
      itemCode: product.itemCode,
      name: product.name,
      manufacturer: product.manufacturer,
      brand: product.brand,
      model: product.model,
      year: product.year,
      detail: product.detail,
      detalles: product.detalles,
      image: product.image,
      oemCode: product.oemCode,
      factoryCode: product.factoryCode,
      price1: product.price1,
      price2: product.price2,
      category: product.category?.name || null,
      availability,
      importers: product.importers.map((pi) => ({
        id: pi.importer.id,
        name: pi.importer.name,
        phone: pi.importer.phone,
        email: pi.importer.email,
        city: pi.importer.city,
        address: pi.importer.address,
        description: pi.importer.description,
      })),
    });
  } catch (error) {
    console.error("Error en detalle público:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /api/public/filters - Filtros progresivos
router.get("/filters", async (_req: Request, res: Response) => {
  try {
    const brandsRaw = await prisma.product.findMany({
      select: { brand: true },
      orderBy: { brand: "asc" },
    });

    const categories = await prisma.category.findMany({
      select: { name: true },
      orderBy: { name: "asc" },
    });

    const qualities = await prisma.product.findMany({
      where: { detalles: { not: null } },
      select: { detalles: true },
      distinct: ["detalles"],
      orderBy: { detalles: "asc" },
    });

    const brands = [...new Set(brandsRaw.flatMap((b) => b.brand.split("/").map((v) => v.trim())).filter(Boolean))].sort();

    res.json({
      brands,
      categories: categories.map((c) => c.name),
      qualities: qualities.map((q) => q.detalles).filter(Boolean),
    });
  } catch (error) {
    console.error("Error en filtros:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /api/public/filters/models - Modelos por marca
router.get("/filters/models", async (req: Request, res: Response) => {
  try {
    const { brand } = req.query;
    const where: any = {};
    if (brand && typeof brand === "string") {
      where.brand = { contains: brand, mode: "insensitive" };
    }

    const modelsRaw = await prisma.product.findMany({
      where,
      select: { model: true },
      orderBy: { model: "asc" },
    });

    const models = [...new Set(modelsRaw.flatMap((m) => m.model.split("/").map((v) => v.trim())).filter(Boolean))].sort();
    res.json(models);
  } catch (error) {
    console.error("Error en modelos:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /api/public/filters/years - Años por marca y modelo
router.get("/filters/years", async (req: Request, res: Response) => {
  try {
    const { brand, model } = req.query;
    const where: any = {};
    if (brand && typeof brand === "string") {
      where.brand = { contains: brand, mode: "insensitive" };
    }
    if (model && typeof model === "string") {
      where.model = { contains: model, mode: "insensitive" };
    }

    const yearsRaw = await prisma.product.findMany({
      where,
      select: { year: true },
      orderBy: { year: "asc" },
    });

    const years = [...new Set(yearsRaw.flatMap((y) => y.year.split("/").map((v) => v.trim())).filter(Boolean))].sort();
    res.json(years);
  } catch (error) {
    console.error("Error en años:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /api/public/importers - Todas las importadoras
router.get("/importers", async (_req: Request, res: Response) => {
  try {
    const importers = await prisma.importer.findMany({
      include: { products: { include: { product: true } } },
      orderBy: { name: "asc" },
    });

    res.json(
      importers.map((imp) => ({
        id: imp.id,
        name: imp.name,
        phone: imp.phone,
        email: imp.email,
        address: imp.address,
        city: imp.city,
        description: imp.description,
        productCount: imp.products.length,
      }))
    );
  } catch (error) {
    console.error("Error en importadoras:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
