import { createHash } from "crypto";
import { errorDominio } from "../../shared/utils/errorDominio";
import { landedCost, syncProductCost, receivePurchase } from "../../shared/utils/costing";
import { money, validatePriceConfiguration } from "../../shared/utils/pricing";
import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authorizeModule, authenticate, authorize } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import { parseId, parsePositiveDecimal, parsePositiveInt } from "../../shared/middlewares/validate";
import { isPrismaClientError } from "../../shared/utils/errors";
import { parsePagination } from "../../shared/utils/pagination";
import multer from "multer";
import path from "path";
import fs from "fs";
import * as XLSX from "xlsx";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);
router.use(authorize("ADMIN"));
router.use(authorizeModule("costos"));

const uploadsDir = path.join(__dirname, "../../../uploads");
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, uploadsDir),
  filename: (_req, file, cb) => {
    const unique = `${Date.now()}-${Math.round(Math.random() * 1e9)}`;
    cb(null, `${unique}${path.extname(file.originalname)}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 10 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const allowed = [".pdf", ".jpg", ".jpeg", ".png", ".xlsx", ".xls"];
    const ext = path.extname(file.originalname).toLowerCase();
    const allowedMimes = ["application/pdf", "image/jpeg", "image/png", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"];
    const mimeOk = allowedMimes.includes(file.mimetype);
    if (allowed.includes(ext) && mimeOk) {
      cb(null, true);
    } else {
      cb(new Error("Solo se permiten archivos PDF, JPG, PNG o Excel"));
    }
  },
});

// GET /invoice/:filename — Visualizar/descargar factura subida
router.get("/invoice/:filename", (req: AuthRequest, res: Response) => {
  const filename = path.basename(String(req.params.filename));
  if (!filename || filename !== req.params.filename) {
    return res.status(400).json({ message: "Nombre de archivo inválido" });
  }
  const filePath = path.join(uploadsDir, filename);
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ message: "Factura no encontrada" });
  }
  res.sendFile(filePath);
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

    const { page: pg, limit: take, skip } = parsePagination(page, limit, 100);

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
      pagination: { total, page: pg, limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error al listar costos:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST — Registrar costo con factura
router.post("/", authorize("ADMIN"), upload.single("invoice"), async (req: AuthRequest, res: Response) => {
  try {
    const productId = parsePositiveInt(req.body.productId, "Producto");
    const supplierId = parsePositiveInt(req.body.supplierId, "Proveedor");
    let costPrice = money(req.body.costPrice, "Costo");
    if (costPrice <= 0) return res.status(400).json({ message: "El costo debe ser mayor a 0" });

    const exchangeRate = req.body.exchangeRate ? parsePositiveDecimal(req.body.exchangeRate, "Tipo de cambio") : null;
    if (exchangeRate !== null && exchangeRate <= 0) {
      return res.status(400).json({ message: "El tipo de cambio debe ser mayor a 0" });
    }
    const percentage = req.body.percentage !== undefined && req.body.percentage !== "" ? parsePositiveDecimal(req.body.percentage, "Porcentaje") : null;
    if (percentage !== null && (percentage < 0 || percentage > 100)) {
      return res.status(400).json({ message: "El porcentaje debe estar entre 0 y 100" });
    }

    if (req.body.unitCost !== undefined) costPrice = landedCost(parsePositiveDecimal(req.body.unitCost, "Costo unitario"), exchangeRate ?? 1, percentage ?? 0);
    const [product, supplier] = await Promise.all([
      prisma.product.findUnique({ where: { id: productId } }),
      prisma.supplier.findUnique({ where: { id: supplierId } }),
    ]);
    if (!product) return res.status(404).json({ message: "Producto no encontrado" });
    if (!supplier) return res.status(404).json({ message: "Proveedor no encontrado" });

    const cost = await prisma.$transaction(async (tx) => {
    await tx.$queryRaw`SELECT id FROM "Product" WHERE id = ${productId} FOR UPDATE`;
    const created = await tx.cost.create({
      data: { productId, supplierId, costPrice, exchangeRate, percentage, invoiceUrl: req.file?.filename || null },
      include: {
        product: { select: { name: true, itemCode: true } },
        supplier: { select: { name: true } },
      },
    });

    await tx.auditLog.create({
      data: {
        userId: req.user!.userId,
        action: "CREATE_COST",
        targetType: "COST",
        targetId: created.id,
        newValue: {
          productId,
          supplierId,
          costPrice,
          invoiceUrl: created.invoiceUrl,
        },
      },
    });

    await syncProductCost(tx, productId);
    if (req.body.locationId || req.body.quantity) {
      await receivePurchase(tx, productId, parsePositiveInt(req.body.locationId, "Ubicación"), parsePositiveInt(req.body.quantity, "Cantidad"), req.user!.userId, created.id);
    }
    return created;
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
  } catch (error: any) {
    if (typeof error?.message === "string" && !error.code && !isPrismaClientError(error)) {
      return res.status(400).json({ message: error.message });
    }
    if (error.code === "LIMIT_FILE_SIZE") {
      return res.status(400).json({ message: "El archivo excede el tamaño máximo de 10MB" });
    }
    console.error("Error al registrar costo:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Editar costo
router.put("/:id", authorize("ADMIN"), upload.single("invoice"), async (req: AuthRequest, res: Response) => {
  try {
    const id = parseId(req.params.id);
    const existing = await prisma.cost.findUnique({ where: { id } });
    if (!existing) return res.status(404).json({ message: "Costo no encontrado" });

    const data: any = {};
    if (req.body.productId !== undefined) {
      data.productId = parsePositiveInt(req.body.productId, "Producto");
      const p = await prisma.product.findUnique({ where: { id: data.productId } });
      if (!p) return res.status(404).json({ message: "Producto no encontrado" });
    }
    if (req.body.supplierId !== undefined) {
      data.supplierId = parsePositiveInt(req.body.supplierId, "Proveedor");
      const s = await prisma.supplier.findUnique({ where: { id: data.supplierId } });
      if (!s) return res.status(404).json({ message: "Proveedor no encontrado" });
    }
    if (req.body.costPrice !== undefined && req.body.costPrice !== "") {
      data.costPrice = parsePositiveDecimal(req.body.costPrice, "Costo");
      if (data.costPrice <= 0) return res.status(400).json({ message: "El costo debe ser mayor a 0" });
    }
    if (req.body.exchangeRate !== undefined) {
      data.exchangeRate = req.body.exchangeRate !== "" ? parsePositiveDecimal(req.body.exchangeRate, "Tipo de cambio") : null;
      if (data.exchangeRate !== null && data.exchangeRate <= 0) {
        return res.status(400).json({ message: "El tipo de cambio debe ser mayor a 0" });
      }
    }
    if (req.body.percentage !== undefined) {
      data.percentage = req.body.percentage !== "" ? parsePositiveDecimal(req.body.percentage, "Porcentaje") : null;
      if (data.percentage !== null && (data.percentage < 0 || data.percentage > 100)) {
        return res.status(400).json({ message: "El porcentaje debe estar entre 0 y 100" });
      }
    }
    if (req.body.unitCost !== undefined) data.costPrice = landedCost(parsePositiveDecimal(req.body.unitCost, "Costo unitario"), data.exchangeRate ?? Number(existing.exchangeRate ?? 1), data.percentage ?? Number(existing.percentage ?? 0));
    if (req.file) data.invoiceUrl = req.file.filename;

    const previous = {
      productId: existing.productId,
      supplierId: existing.supplierId,
      costPrice: Number(existing.costPrice),
      exchangeRate: existing.exchangeRate ? Number(existing.exchangeRate) : null,
      percentage: existing.percentage ? Number(existing.percentage) : null,
      invoiceUrl: existing.invoiceUrl,
    };

    const cost = await prisma.$transaction(async (tx) => {
    const productIds = [...new Set([existing.productId, data.productId ?? existing.productId])].sort((a: number, b: number) => a - b);
    for (const pid of productIds) await tx.$queryRaw`SELECT id FROM "Product" WHERE id = ${pid} FOR UPDATE`;
    const changed = await tx.cost.update({
      where: { id },
      data,
      include: {
        product: { select: { name: true, itemCode: true } },
        supplier: { select: { name: true } },
      },
    });

    await tx.auditLog.create({
      data: {
        userId: req.user!.userId,
        action: "UPDATE_COST",
        targetType: "COST",
        targetId: id,
        oldValue: previous,
        newValue: {
          productId: changed.productId,
          supplierId: changed.supplierId,
          costPrice: Number(changed.costPrice),
          exchangeRate: changed.exchangeRate ? Number(changed.exchangeRate) : null,
          percentage: changed.percentage ? Number(changed.percentage) : null,
          invoiceUrl: changed.invoiceUrl,
        },
      },
    });

    for (const pid of productIds) await syncProductCost(tx, pid);
    return changed;
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
  } catch (error: any) {
    if (error.code === "LIMIT_FILE_SIZE") {
      return res.status(400).json({ message: "El archivo excede el tamaño máximo de 10MB" });
    }
    if (typeof error?.message === "string" && !isPrismaClientError(error)) {
      return res.status(400).json({ message: error.message });
    }
    console.error("Error al editar costo:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// DELETE /:id — Eliminar costo
router.delete("/:id", authorize("ADMIN"), async (req: AuthRequest, res: Response) => {
  try {
    const id = parseId(req.params.id);
    const existing = await prisma.cost.findUnique({ where: { id } });
    if (!existing) return res.status(404).json({ message: "Costo no encontrado" });
    await prisma.$transaction(async (tx) => {
    await tx.$queryRaw`SELECT id FROM "Product" WHERE id = ${existing.productId} FOR UPDATE`;
    await tx.cost.delete({ where: { id } });
    await tx.auditLog.create({
      data: {
        userId: req.user!.userId,
        action: "DELETE_COST",
        targetType: "COST",
        targetId: id,
        oldValue: { costPrice: Number(existing.costPrice), invoiceUrl: existing.invoiceUrl },
      },
    });
    await syncProductCost(tx, existing.productId);
    });
    res.json({ message: "Costo eliminado" });
  } catch (error: any) {
    if (error.message === "ID inválido") return res.status(400).json({ message: error.message });
    console.error("Error al eliminar costo:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST /import-invoice — Importar costos masivamente desde factura Excel (ADMIN)
// Calcula el "Costo Puesto Aquí" (CIF nacionalizado):
//   CostoPuestoAqui = PrecioUnitario(USD) × TipoCambio × (1 + %Gastos/100)
router.post("/import-invoice", authorize("ADMIN"), upload.fields([{ name: "file", maxCount: 1 }, { name: "invoice", maxCount: 1 }]), async (req: AuthRequest, res: Response) => {
  const excelFile = (req.files as any)?.file?.[0];
  const invoiceFile = (req.files as any)?.invoice?.[0];
  let keepInvoice = false;
  try {
    if (!excelFile || ![".xlsx", ".xls"].includes(path.extname(excelFile.originalname).toLowerCase())) throw errorDominio("Debe subir el archivo Excel de la factura");
    const supplierId = parsePositiveInt(req.body.supplierId, "Proveedor");
    const exchangeRate = parsePositiveDecimal(req.body.exchangeRate, "Tipo de cambio");
    const percentage = req.body.percentage !== undefined && req.body.percentage !== "" ? parsePositiveDecimal(req.body.percentage, "Porcentaje de gastos") : 0;
    const defaultMargin = req.body.defaultMargin !== undefined && req.body.defaultMargin !== "" ? parsePositiveDecimal(req.body.defaultMargin, "Margen") : 0;
    const locationId = req.body.locationId ? parsePositiveInt(req.body.locationId, "Ubicación") : null;
    if (exchangeRate <= 0 || percentage > 100 || defaultMargin > 200) throw errorDominio("Tipo de cambio, porcentaje o margen inválidos");
    if (!await prisma.supplier.findUnique({ where: { id: supplierId } })) return res.status(404).json({ message: "Proveedor no encontrado" });
    const excelBytes = fs.readFileSync(excelFile.path);
    const fileHash = createHash("sha256").update(excelBytes).digest("hex");
    const workbook = XLSX.read(excelBytes, { type: "buffer" });
    const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(workbook.Sheets[workbook.SheetNames[0]]);
    if (!rows.length || rows.length > 5000) throw errorDominio("La factura debe contener entre 1 y 5000 filas");
    const configuration = { exchangeRate, percentage, defaultMargin, locationId };
    const result = await prisma.$transaction(async tx => {
      // Se comparte entre procesos y protege la comprobación y todos los efectos.
      await tx.$queryRaw`SELECT pg_advisory_xact_lock(hashtextextended(${`invoice:${supplierId}:${fileHash}`}, 0))::text`;
      const prior = await tx.auditLog.findFirst({ where: { action: "IMPORT_INVOICE", targetType: "SUPPLIER", targetId: supplierId, newValue: { path: ["fileHash"], equals: fileHash } }, orderBy: { id: "asc" } });
      if (prior) {
        const saved = prior.newValue as any;
        if (JSON.stringify(saved.configuration) !== JSON.stringify(configuration)) {
          // JSONB no conserva orden de claves. Se comparan sus valores.
          if (Object.entries(configuration).some(([k,v]) => saved.configuration[k] !== v)) return { conflict: true as const };
        }
        return { conflict: false as const, response: { ...saved.response, replayed: true } };
      }
      const prepared = [];
      for (let i=0; i<rows.length; i++) {
        const row = rows[i];
        const code = String(row["Código"] ?? row["Codigo"] ?? row["codigo"] ?? row.itemCode ?? row.ItemCode ?? row["Codigo Fabrica"] ?? row["Código Fábrica"] ?? row["Cod. Fabrica"] ?? row["Cód. Fabrica"] ?? row["Cód. Producto"] ?? row["Codigo Producto"] ?? "").trim();
        const quantity = parsePositiveInt(row.Cantidad ?? row.cantidad ?? row.Cant ?? row.Qty ?? row.Quantity ?? 1, `Cantidad fila ${i+2}`);
        const unit = parsePositiveDecimal(row["Precio Unitario"] ?? row["Precio unitario"] ?? row.Precio ?? row.PU ?? row.Pu ?? row["Unit Price"] ?? row["Precio USD"] ?? row["Precio US"] ?? row.precio, `Precio unitario fila ${i+2}`);
        if (!code || unit <= 0) throw errorDominio(`Fila ${i+2}: código o precio inválido`);
        const product = await tx.product.findUnique({ where: { itemCode: code } });
        if (!product) throw errorDominio(`Fila ${i+2}: producto no encontrado (${code})`);
        prepared.push({ product, quantity, costPrice: landedCost(unit, exchangeRate, percentage) });
      }
      for (const id of [...new Set(prepared.map(r=>r.product.id))].sort((a,b)=>a-b)) await tx.$queryRaw`SELECT id FROM "Product" WHERE id = ${id} FOR UPDATE`;
      const imported = [];
      for (const row of prepared) {
        const actual = await tx.product.findUniqueOrThrow({ where: { id: row.product.id } });
        const next = { ...actual, cost: row.costPrice, ...(defaultMargin > 0 ? { price1: money(row.costPrice * (1+defaultMargin/100), "Precio por menor") } : {}) };
        validatePriceConfiguration(next);
        const cost = await tx.cost.create({ data: { productId: actual.id, supplierId, costPrice: row.costPrice, exchangeRate, percentage, invoiceUrl: invoiceFile?.filename ?? null } });
        await tx.product.update({ where: { id: actual.id }, data: { cost: row.costPrice, ...(defaultMargin > 0 ? { price1: Number(next.price1) } : {}) } });
        await tx.auditLog.create({ data: { userId: req.user!.userId, action: "IMPORT_COST", targetType: "COST", targetId: cost.id, newValue: { productId: actual.id, supplierId, costPrice: row.costPrice, fileHash } } });
        if (locationId) await receivePurchase(tx, actual.id, locationId, row.quantity, req.user!.userId, cost.id);
        imported.push({ id: cost.id, itemCode: actual.itemCode, name: actual.name, costPrice: row.costPrice, cantidad: row.quantity });
      }
      const response = { total: rows.length, imported: imported.length, updated: 0, errors: 0, formula: `PrecioUnitario × TipoCambio(${exchangeRate}) × (1 + ${percentage}% / 100)`, details: { imported, updated: [], errors: [] }, replayed: false };
      await tx.auditLog.create({ data: { userId: req.user!.userId, action: "IMPORT_INVOICE", targetType: "SUPPLIER", targetId: supplierId, newValue: { fileHash, configuration, response } } });
      return { conflict: false as const, response };
    }, { timeout: 60000 });
    if (result.conflict) return res.status(409).json({ message: "Este archivo ya fue importado para el proveedor con otros parámetros. Revise la importación registrada" });
    keepInvoice = !result.response.replayed;
    res.json(result.response);
  } catch (error: any) {
    if (!isPrismaClientError(error)) return res.status(400).json({ message: error.message || "Factura inválida" });
    console.error("Error al importar factura:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  } finally {
    if (excelFile?.path && fs.existsSync(excelFile.path)) fs.unlinkSync(excelFile.path);
    if (!keepInvoice && invoiceFile?.path && fs.existsSync(invoiceFile.path)) fs.unlinkSync(invoiceFile.path);
  }
});

export default router;
