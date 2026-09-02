import { Router, Request, Response } from "express";
import { PrismaClient } from "@prisma/client";
import multer from "multer";
import * as XLSX from "xlsx";
import { createWorker } from "tesseract.js";
import path from "path";
import { yearMatchesRanges } from "../../utils/yearRanges";
import { authenticate, authorize } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";

const router = Router();
const prisma = new PrismaClient();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024 } });

// Datos de idioma locales para OCR (evita descargas en cada request)
const OCR_LANG_PATH = path.join(process.cwd(), "node_modules", "@tesseract.js-data", "eng", "4.0.0");

const IMAGE_STOPWORDS = new Set(["img", "imagen", "image", "photo", "foto", "producto", "product", "part", "ref", "cod", "code", "dsc", "dscn", "captura", "nuevo", "venta", "jpeg", "jpg", "png", "webp", "2024", "2023", "2022", "the", "and", "for", "con", "numero", "number", "original", "oem", "referencia", "repuesto", "accesorio", "universal", "calidad", "estandar"]);

// GET / — Listar productos con filtros, búsqueda y paginación
router.get("/", async (req: Request, res: Response) => {
  try {
    const {
      search, brand, manufacturer, model, year, oemCode, factoryCode,
      categoryId, locationId: queryLocationId, page = "1", limit = "20",
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

    if (brand && typeof brand === "string") AND.push({ brand: { contains: brand, mode: "insensitive" } });
    if (manufacturer && typeof manufacturer === "string") AND.push({ manufacturer: { contains: manufacturer, mode: "insensitive" } });
    if (model && typeof model === "string") AND.push({ model: { contains: model, mode: "insensitive" } });
    if (oemCode && typeof oemCode === "string") AND.push({ oemCode: { contains: oemCode, mode: "insensitive" } });
    if (factoryCode && typeof factoryCode === "string") AND.push({ factoryCode: { contains: factoryCode, mode: "insensitive" } });
    if (categoryId && typeof categoryId === "string") AND.push({ categoryId: Number(categoryId) });

    if (queryLocationId && typeof queryLocationId === "string") {
      AND.push({ inventories: { some: { locationId: Number(queryLocationId), stock: { gt: 0 } } } });
    }

    if (AND.length > 0) where.AND = AND;

    const skip = (Number(page) - 1) * Number(limit);
    const take = Number(limit);

    const hasYearFilter = year && typeof year === "string";
    const filterLocationId = queryLocationId && typeof queryLocationId === "string" ? Number(queryLocationId) : null;

    let allProducts = await prisma.product.findMany({
      where,
      include: {
        category: true,
        inventories: { include: { location: true } },
      },
      orderBy: { name: "asc" },
    });

    if (hasYearFilter) {
      const searchYear = parseInt(year as string, 10);
      allProducts = allProducts.filter((p) => yearMatchesRanges(searchYear, p.year));
    }

    const total = allProducts.length;
    const products = allProducts.slice(skip, skip + take);

    const result = products.map((p) => {
      const stock = filterLocationId
        ? (p.inventories.find((inv) => inv.locationId === filterLocationId)?.stock || 0)
        : p.inventories.reduce((sum, inv) => sum + inv.stock, 0);
      return {
        id: p.id,
        itemCode: p.itemCode,
        manufacturer: p.manufacturer,
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
        wholesalePrice: p.wholesalePrice,
        cost: p.cost,
        categoryId: p.categoryId,
        category: p.category?.name || null,
        stock,
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

// GET /filters — Marcas, fabricantes, modelos, años, categorías disponibles
router.get("/filters", async (_req: Request, res: Response) => {
  try {
    const [brandsRaw, manufacturersRaw, modelsRaw, yearsRaw, categories] = await Promise.all([
      prisma.product.findMany({ select: { brand: true }, orderBy: { brand: "asc" } }),
      prisma.product.findMany({ select: { manufacturer: true }, orderBy: { manufacturer: "asc" } }),
      prisma.product.findMany({ select: { model: true }, orderBy: { model: "asc" } }),
      prisma.product.findMany({ select: { year: true }, orderBy: { year: "asc" } }),
      prisma.category.findMany({ select: { id: true, name: true }, orderBy: { name: "asc" } }),
    ]);

    const brands = [...new Set(brandsRaw.flatMap((b) => b.brand.split("/").map((v) => v.trim())).filter(Boolean))].sort();
    const manufacturers = [...new Set(manufacturersRaw.map((m) => m.manufacturer).filter(Boolean))].sort();
    const models = [...new Set(modelsRaw.flatMap((m) => m.model.split("/").map((v) => v.trim())).filter(Boolean))].sort();
    const years = [...new Set(yearsRaw.flatMap((y) => y.year.split("/").map((v) => v.trim())).filter(Boolean))].sort();

    res.json({ brands, manufacturers, models, categories, years });
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
      detalles: product.detalles,
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

// POST — Crear producto (solo ADMIN)
router.post("/", authenticate, authorize("ADMIN"), async (req: AuthRequest, res: Response) => {
  try {
    const { itemCode, manufacturer, name, brand, model, year, detail, oemCode, factoryCode, price1, price2, wholesalePrice, cost, categoryId, image, locationId, stock = 0, minStock = 1 } = req.body;

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

    if (locationId) {
      await prisma.inventory.create({ data: { productId: product.id, locationId: Number(locationId), stock: Number(stock) || 0, minStock: Number(minStock) || 1 } });
    }

    res.status(201).json(product);
  } catch (error) {
    console.error("Error al crear producto:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Editar producto (solo ADMIN)
router.put("/:id", authenticate, authorize("ADMIN"), async (req: AuthRequest, res: Response) => {
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

// DELETE /:id — Eliminar producto (solo ADMIN)
router.delete("/:id", authenticate, authorize("ADMIN"), async (req: AuthRequest, res: Response) => {
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

// POST /search-image — Buscar productos por imagen
router.post("/search-image", upload.single("image"), async (req: Request, res: Response) => {
  try {
    if (!req.file) {
      return res.status(400).json({ message: "Debe subir una imagen" });
    }

    // Normalizar el nombre del archivo: quitar extensión, guiones/guiones bajos y tokens genéricos/códigos
    const raw = req.file.originalname.toLowerCase().replace(/\.[^.]+$/, "");

    const tokenPool = new Set<string>();
    const pushToken = (w: string) => {
      if (w.length > 2 && !/^\d+$/.test(w) && !IMAGE_STOPWORDS.has(w)) tokenPool.add(w);
    };

    raw
      .replace(/[_\-\.\+\(\)\[\]]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .split(" ")
      .forEach(pushToken);

    // R25/C5: extraer el contenido real de la imagen (OCR) además del nombre del archivo
    let ocrText = "";
    try {
      const worker = await createWorker("eng", 1, { langPath: OCR_LANG_PATH, gzip: true });
      try {
        const ctx = await worker.recognize(req.file.buffer);
        ocrText = ctx.data.text || "";
      } finally {
        await worker.terminate();
      }
    } catch (ocrErr) {
      console.error("OCR no disponible:", ocrErr);
    }

    ocrText
      .toLowerCase()
      .split(/[\s,;/|]+/)
      .map((t) => t.replace(/[^\w.-]/g, "").replace(/-/g, ""))
      .forEach(pushToken);

    const keywords = Array.from(tokenPool);

    if (keywords.length === 0) {
      return res.json({ products: [], message: "No se pudieron extraer palabras clave del nombre o la imagen" });
    }

    // Buscar por múltiples campos y rankear por cantidad de coincidencias
    const products = await prisma.product.findMany({
      where: {
        AND: [
          {
            OR: keywords.flatMap((kw) => [
              { name: { contains: kw, mode: "insensitive" as const } },
              { brand: { contains: kw, mode: "insensitive" as const } },
              { model: { contains: kw, mode: "insensitive" as const } },
              { itemCode: { contains: kw, mode: "insensitive" as const } },
              { oemCode: { contains: kw, mode: "insensitive" as const } },
              { factoryCode: { contains: kw, mode: "insensitive" as const } },
              { detail: { contains: kw, mode: "insensitive" as const } },
              { manufacturer: { contains: kw, mode: "insensitive" as const } },
            ]),
          },
        ],
      },
      include: {
        inventories: {
          include: { location: { select: { id: true, name: true, type: true } } },
        },
      },
      take: 50,
    });

    // Rankear: cuantas más keywords coincidan con el nombre/marca/modelo/códigos, mejor
    const scored = products
      .map((p) => {
        const haystack = `${p.name} ${p.brand} ${p.model} ${p.itemCode} ${p.oemCode || ""} ${p.factoryCode || ""} ${p.detail || ""}`.toLowerCase();
        const matches = keywords.filter((kw) => haystack.includes(kw)).length;
        return { p, score: matches };
      })
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 20);

    const results = scored.map(({ p }) => ({
      id: p.id,
      itemCode: p.itemCode,
      name: p.name,
      brand: p.brand,
      model: p.model,
      year: p.year,
      price1: Number(p.price1),
      price2: Number(p.price2),
      image: p.image,
      score: 1,
      totalStock: p.inventories.reduce((sum, i) => sum + i.stock, 0),
      locations: p.inventories.map((i) => ({
        name: i.location.name,
        type: i.location.type,
        stock: i.stock,
      })),
    }));

    res.json({
      query: keywords.join(" "),
      count: results.length,
      products: results,
    });
  } catch (error) {
    console.error("Error en búsqueda por imagen:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST /import — Importar productos masivamente desde Excel (solo ADMIN)
router.post("/import", authenticate, authorize("ADMIN"), upload.single("file"), async (req: AuthRequest, res: Response) => {
  try {
    if (!req.file) {
      return res.status(400).json({ message: "Debe subir un archivo Excel (.xlsx o .xls)" });
    }

    const workbook = XLSX.read(req.file.buffer, { type: "buffer" });
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    const rows = XLSX.utils.sheet_to_json(sheet);

    if (rows.length === 0) {
      return res.status(400).json({ message: "El archivo está vacío" });
    }

    const categories = await prisma.category.findMany();
    const catMap: Record<string, number> = {};
    categories.forEach((c) => { catMap[c.name.toLowerCase()] = c.id; });

    const imported: any[] = [];
    const updated: any[] = [];
    const errors: string[] = [];

    for (let i = 0; i < rows.length; i++) {
      const row = rows[i] as any;

      const itemCode = (row["Codigo fabrica"] || row["codigo fabrica"] || row["Código Fábrica"] || row["itemCode"] || row["Código"] || "").toString().trim();
      const name = (row["Descripcion"] || row["descripcion"] || row["Producto"] || row["producto"] || row["Nombre"] || "").toString().trim();
      const manufacturer = (row["Fabricante"] || row["fabricante"] || row["Manufacturer"] || "Sin especificar").toString().trim();
      const brand = (row["Marca"] || row["marca"] || row["Brand"] || "").toString().trim();
      const model = (row["Modelo"] || row["modelo"] || row["Model"] || "").toString().trim();
      const year = (row["Anos"] || row["anos"] || row["Años"] || row["años"] || row["Año"] || "").toString().trim();
      const detail = (row["Detalle"] || row["detalle"] || row["Detail"] || "").toString().trim();
      const oemCode = (row["Código OEM"] || row["codigo oem"] || row["oemCode"] || row["Cód. OEM"] || "").toString().trim();
      const factoryCode = (row["Código fábrica"] || row["codigo fabrica"] || row["factoryCode"] || row["Cód. Fábrica"] || "").toString().trim();
      const category = (row["Categoría"] || row["categoría"] || row["Categoria"] || row["categoria"] || row["Category"] || "").toString().trim();
      const price1 = parseFloat(row["Precio 1"] || row["precio1"] || row["Precio minorista"] || row["price1"] || "0") || 0;
      const price2 = parseFloat(row["Precio 2"] || row["precio2"] || row["Precio mayoreo"] || row["price2"] || "0") || 0;
      const wholesalePrice = parseFloat(row["Precio mayor"] || row["precio mayor"] || row["wholesalePrice"] || "0") || 0;
      const cost = parseFloat(row["Costo"] || row["costo"] || row["cost"] || "0") || 0;
      const calidad = (row["Calidad"] || row["calidad"] || row["quality"] || row["Detalles"] || row["detalles"] || "").toString().trim();
      const rowStock = parseInt(row["Stock"] || row["stock"] || "0", 10) || 0;
      const requestedLocationId = Number(req.body.locationId) || 0;
      const rowLocation = (row["Ubicación"] || row["Ubicacion"] || row["Tienda"] || row["Almacén"] || row["Almacen"] || "").toString().trim();

      if (!itemCode || !name) {
        errors.push(`Fila ${i + 2}: Código y nombre son obligatorios`);
        continue;
      }

      try {
        let categoryId: number | null = null;
        if (category && catMap[category.toLowerCase()]) {
          categoryId = catMap[category.toLowerCase()];
        }

        let rowLocationId = requestedLocationId;
        if (rowLocation) {
          const location = await prisma.location.findFirst({ where: { OR: [{ name: { equals: rowLocation, mode: "insensitive" } }, { id: Number(rowLocation) || -1 }] } });
          if (!location) throw new Error(`Ubicación no encontrada: ${rowLocation}`);
          rowLocationId = location.id;
        }

        const existing = await prisma.product.findUnique({ where: { itemCode } });

        if (existing) {
          const updateData: any = {};
          if (name) updateData.name = name;
          if (brand) updateData.brand = brand;
          if (model) updateData.model = model;
          if (year) updateData.year = year;
          if (detail) updateData.detail = detail;
          if (manufacturer && manufacturer !== "Sin especificar") updateData.manufacturer = manufacturer;
          if (oemCode) updateData.oemCode = oemCode;
          if (factoryCode) updateData.factoryCode = factoryCode;
          if (price1 > 0) updateData.price1 = price1;
          if (price2 > 0) updateData.price2 = price2;
          if (wholesalePrice > 0) updateData.wholesalePrice = wholesalePrice;
          if (cost > 0) updateData.cost = cost;
          if (categoryId) updateData.categoryId = categoryId;
          if (calidad) updateData.detalles = calidad;

          if (Object.keys(updateData).length > 0) {
            await prisma.product.update({ where: { id: existing.id }, data: updateData });
          }
          if (rowLocationId) {
            await prisma.inventory.upsert({ where: { productId_locationId: { productId: existing.id, locationId: rowLocationId } }, update: { stock: rowStock }, create: { productId: existing.id, locationId: rowLocationId, stock: rowStock, minStock: 1 } });
          }
          updated.push({ id: existing.id, itemCode, name, action: "actualizado" });
        } else {
          const product = await prisma.product.create({
            data: {
              itemCode,
              name,
              manufacturer,
              brand: brand || "Sin marca",
              model: model || "Sin modelo",
              year,
              detail,
              oemCode: oemCode || null,
              factoryCode: factoryCode || null,
              price1: price1 || 0,
              price2: price2 || 0,
              wholesalePrice: wholesalePrice || null,
              cost: cost || null,
              categoryId,
              detalles: calidad || null,
            },
          });

          const locations = rowLocationId
            ? await prisma.location.findMany({ where: { id: rowLocationId } })
            : await prisma.location.findMany();
          for (const loc of locations) await prisma.inventory.create({ data: { productId: product.id, locationId: loc.id, stock: rowLocationId ? rowStock : 0, minStock: 1 } });

          imported.push({ id: product.id, itemCode, name, action: "creado" });
        }
      } catch (err: any) {
        errors.push(`Fila ${i + 2}: ${err.message}`);
      }
    }

    res.json({
      total: rows.length,
      imported: imported.length,
      updated: updated.length,
      errors: errors.length,
      details: { imported, updated, errors },
    });
  } catch (error: any) {
    console.error("Error al importar productos:", error);
    if (error.code === "LIMIT_FILE_SIZE") {
      return res.status(400).json({ message: "El archivo excede el tamaño máximo de 10MB" });
    }
    res.status(500).json({ message: error.message || "Error al procesar el archivo" });
  }
});

export default router;
