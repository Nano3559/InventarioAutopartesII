import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate, authorize } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import { parseId, parsePositiveDecimal, parsePositiveInt } from "../../shared/middlewares/validate";
import multer from "multer";
import path from "path";
import fs from "fs";
import * as XLSX from "xlsx";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);
router.use(authorize("ADMIN"));

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

    const pg = Math.max(1, Number(page) || 1);
    const take = Math.min(100, Math.max(1, Number(limit) || 20));
    const skip = (pg - 1) * take;

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
    const costPrice = parsePositiveDecimal(req.body.costPrice, "Costo");
    if (costPrice <= 0) return res.status(400).json({ message: "El costo debe ser mayor a 0" });

    const exchangeRate = req.body.exchangeRate ? parsePositiveDecimal(req.body.exchangeRate, "Tipo de cambio") : null;
    if (exchangeRate !== null && exchangeRate <= 0) {
      return res.status(400).json({ message: "El tipo de cambio debe ser mayor a 0" });
    }
    const percentage = req.body.percentage !== undefined && req.body.percentage !== "" ? parsePositiveDecimal(req.body.percentage, "Porcentaje") : null;
    if (percentage !== null && (percentage < 0 || percentage > 100)) {
      return res.status(400).json({ message: "El porcentaje debe estar entre 0 y 100" });
    }

    const [product, supplier] = await Promise.all([
      prisma.product.findUnique({ where: { id: productId } }),
      prisma.supplier.findUnique({ where: { id: supplierId } }),
    ]);
    if (!product) return res.status(404).json({ message: "Producto no encontrado" });
    if (!supplier) return res.status(404).json({ message: "Proveedor no encontrado" });

    const cost = await prisma.cost.create({
      data: { productId, supplierId, costPrice, exchangeRate, percentage, invoiceUrl: req.file?.filename || null },
      include: {
        product: { select: { name: true, itemCode: true } },
        supplier: { select: { name: true } },
      },
    });

    await prisma.auditLog.create({
      data: {
        userId: req.user!.userId,
        action: "CREATE_COST",
        targetType: "COST",
        targetId: cost.id,
        newValue: {
          productId,
          supplierId,
          costPrice,
          invoiceUrl: cost.invoiceUrl,
        },
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
  } catch (error: any) {
    if (error.message && !error.message.includes("Prisma") && !error.code) {
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
    if (req.file) data.invoiceUrl = req.file.filename;

    const previous = {
      productId: existing.productId,
      supplierId: existing.supplierId,
      costPrice: Number(existing.costPrice),
      exchangeRate: existing.exchangeRate ? Number(existing.exchangeRate) : null,
      percentage: existing.percentage ? Number(existing.percentage) : null,
      invoiceUrl: existing.invoiceUrl,
    };

    const cost = await prisma.cost.update({
      where: { id },
      data,
      include: {
        product: { select: { name: true, itemCode: true } },
        supplier: { select: { name: true } },
      },
    });

    await prisma.auditLog.create({
      data: {
        userId: req.user!.userId,
        action: "UPDATE_COST",
        targetType: "COST",
        targetId: id,
        oldValue: previous,
        newValue: {
          productId: cost.productId,
          supplierId: cost.supplierId,
          costPrice: Number(cost.costPrice),
          exchangeRate: cost.exchangeRate ? Number(cost.exchangeRate) : null,
          percentage: cost.percentage ? Number(cost.percentage) : null,
          invoiceUrl: cost.invoiceUrl,
        },
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
  } catch (error: any) {
    if (error.code === "LIMIT_FILE_SIZE") {
      return res.status(400).json({ message: "El archivo excede el tamaño máximo de 10MB" });
    }
    if (error.message && !error.message.includes("Prisma")) {
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
    await prisma.cost.delete({ where: { id } });
    await prisma.auditLog.create({
      data: {
        userId: req.user!.userId,
        action: "DELETE_COST",
        targetType: "COST",
        targetId: id,
        oldValue: { costPrice: Number(existing.costPrice), invoiceUrl: existing.invoiceUrl },
      },
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
  try {
    const excelFile = (req.files as any)?.["file"]?.[0];
    const invoiceFile = (req.files as any)?.["invoice"]?.[0];
    if (!excelFile) {
      return res.status(400).json({ message: "Debe subir el archivo Excel de la factura (columna 'file')" });
    }

    const supplierId = parsePositiveInt(req.body.supplierId, "Proveedor");
    const exchangeRate = parsePositiveDecimal(req.body.exchangeRate, "Tipo de cambio");
    if (exchangeRate <= 0) return res.status(400).json({ message: "El tipo de cambio debe ser mayor a 0" });
    const percentage = req.body.percentage !== undefined && req.body.percentage !== "" ? parsePositiveDecimal(req.body.percentage, "Porcentaje de gastos") : 0;
    if (percentage < 0 || percentage > 100) return res.status(400).json({ message: "El porcentaje debe estar entre 0 y 100" });
    const defaultMargin = req.body.defaultMargin !== undefined && req.body.defaultMargin !== "" ? parsePositiveDecimal(req.body.defaultMargin, "Margen de ganancia") : 0;
    if (defaultMargin < 0 || defaultMargin > 200) return res.status(400).json({ message: "El margen debe estar entre 0 y 200" });

    const supplier = await prisma.supplier.findUnique({ where: { id: supplierId } });
    if (!supplier) return res.status(404).json({ message: "Proveedor no encontrado" });

    const workbook = XLSX.read(excelFile.buffer, { type: "buffer" });
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    const rows = XLSX.utils.sheet_to_json(sheet);
    if (rows.length === 0) return res.status(400).json({ message: "El archivo Excel está vacío" });

    const imported: any[] = [];
    const updated: any[] = [];
    const errors: string[] = [];
    const invoiceUrl = invoiceFile?.filename || null;

    for (let i = 0; i < rows.length; i++) {
      const row = rows[i] as any;
      const code = (row["Código"] || row["Codigo"] || row["codigo"] || row["itemCode"] || row["ItemCode"] || row["Codigo Fabrica"] || row["Código Fábrica"] || row["Cod. Fabrica"] || row["Cód. Fabrica"] || row["Cód. Producto"] || row["Codigo Producto"] || "").toString().trim();
      const qtyRaw = parseFloat(row["Cantidad"] || row["cantidad"] || row["Cant"] || row["Qty"] || row["Quantity"] || "1") || 1;
      const unitRaw = parseFloat(row["Precio Unitario"] || row["Precio unitario"] || row["Precio"] || row["PU"] || row["Pu"] || row["Unit Price"] || row["Precio USD"] || row["Precio US"] || row["precio"] || "0") || 0;

      if (!code) {
        errors.push(`Fila ${i + 2}: Falta el código del producto`);
        continue;
      }
      if (unitRaw <= 0) {
        errors.push(`Fila ${i + 2}: Precio unitario inválido para "${code}"`);
        continue;
      }

      const product = await prisma.product.findUnique({ where: { itemCode: code } });
      if (!product) {
        errors.push(`Fila ${i + 2}: Producto no encontrado (código "${code}")`);
        continue;
      }

      const costPuestoAqui = unitRaw * exchangeRate * (1 + percentage / 100);

      const existing = await prisma.cost.findFirst({ where: { productId: product.id, supplierId } });
      if (existing) {
        await prisma.cost.update({
          where: { id: existing.id },
          data: { costPrice: costPuestoAqui, exchangeRate, percentage: percentage > 0 ? percentage : null, invoiceUrl: invoiceUrl || existing.invoiceUrl },
        });
        updated.push({ id: existing.id, itemCode: code, name: product.name, costPrice: costPuestoAqui, cantidad: qtyRaw });
      } else {
        const cost = await prisma.cost.create({
          data: { productId: product.id, supplierId, costPrice: costPuestoAqui, exchangeRate, percentage: percentage > 0 ? percentage : null, invoiceUrl },
        });
        imported.push({ id: cost.id, itemCode: code, name: product.name, costPrice: costPuestoAqui, cantidad: qtyRaw });
      }

      await prisma.product.update({
        where: { id: product.id },
        data: {
          cost: costPuestoAqui,
          ...(defaultMargin > 0 ? { price1: costPuestoAqui * (1 + defaultMargin / 100) } : {}),
        },
      });
    }

    res.json({
      total: rows.length,
      imported: imported.length,
      updated: updated.length,
      errors: errors.length,
      formula: `PrecioUnitario × TipoCambio(${exchangeRate}) × (1 + ${percentage}% / 100)`,
      details: { imported, updated, errors },
    });
  } catch (error: any) {
    if (error.message && !error.message.includes("Prisma") && !error.code) {
      return res.status(400).json({ message: error.message });
    }
    if (error.code === "LIMIT_FILE_SIZE") {
      return res.status(400).json({ message: "El archivo excede el tamaño máximo de 10MB" });
    }
    console.error("Error al importar factura:", error);
    res.status(500).json({ message: error.message || "Error interno del servidor" });
  }
});

export default router;
