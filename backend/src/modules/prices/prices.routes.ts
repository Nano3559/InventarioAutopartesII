import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate, authorize, authorizeModule } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);
router.use(authorize("ADMIN"));

// Márgenes por defecto para los precios:
//   Precio 1 = mayorista (margen menor), Precio 2 = minorista (margen mayor)
const DEFAULT_MARGIN1 = 25; // % margen mayorista
const DEFAULT_MARGIN2 = 45; // % margen minorista

// GET / — Calcular precios desde costo con márgenes configurables y filtro por factura
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { search, costId, page = "1", limit = "20" } = req.query;
    const margin1 = req.query.margin1 !== undefined ? Number(req.query.margin1) : DEFAULT_MARGIN1;
    const margin2 = req.query.margin2 !== undefined ? Number(req.query.margin2) : DEFAULT_MARGIN2;
    const m1 = Number.isFinite(margin1) ? margin1 : DEFAULT_MARGIN1;
    const m2 = Number.isFinite(margin2) ? margin2 : DEFAULT_MARGIN2;

    const where: any = {};
    if (search && typeof search === "string") {
      where.OR = [
        { name: { contains: search, mode: "insensitive" } },
        { itemCode: { contains: search, mode: "insensitive" } },
        { brand: { contains: search, mode: "insensitive" } },
        { model: { contains: search, mode: "insensitive" } },
      ];
    }

    // H5: permitir seleccionar un costo/factura específico
    if (costId && typeof costId === "string") {
      const cid = Number(costId);
      if (!Number.isNaN(cid) && cid >= 1) {
        const c = await prisma.cost.findUnique({ where: { id: cid } });
        if (c) {
          // Acotar al producto de esa factura
          where.id = c.productId;
        }
      }
    }

    const [products, total] = await Promise.all([
      prisma.product.findMany({
        where,
        include: {
          costs: { orderBy: { date: "desc" }, include: { supplier: { select: { id: true, name: true } } } },
        },
        orderBy: { name: "asc" },
        skip: (Math.max(1, Number(page) || 1) - 1) * Math.min(200, Math.max(1, Number(limit) || 20)),
        take: Math.min(200, Math.max(1, Number(limit) || 20)),
      }),
      prisma.product.count({ where }),
    ]);

    const prices = products.map((p) => {
      const latestCost = p.costs[0]?.costPrice ? Number(p.costs[0].costPrice) : p.cost ? Number(p.cost) : 0;
      const precioMayorista = Number((latestCost * (1 + m1 / 100)).toFixed(2)); // Precio 1
      const precioMinorista = Number((latestCost * (1 + m2 / 100)).toFixed(2)); // Precio 2

      return {
        id: p.id,
        itemCode: p.itemCode,
        productName: p.name,
        brand: p.brand,
        model: p.model,
        years: p.year,
        detail: p.detail || "",
        cost: latestCost,
        costs: p.costs.map((c) => ({
          id: c.id,
          costPrice: Number(c.costPrice),
          supplierName: c.supplier?.name || null,
          invoiceUrl: c.invoiceUrl || null,
          date: c.date,
        })),
        precioMayorista,
        precioMinorista,
        currentPrice1: p.price1 ? Number(p.price1) : 0,
        currentPrice2: p.price2 ? Number(p.price2) : 0,
        wholesalePrice: p.wholesalePrice ? Number(p.wholesalePrice) : 0,
        costId: p.costs[0]?.id ?? null,
        costDate: p.costs[0]?.date ?? null,
        invoiceUrl: p.costs[0]?.invoiceUrl ?? null,
      };
    });

    // Lista de facturas/costos disponibles para el filtro
    const invoices = await prisma.cost.findMany({
      orderBy: { date: "desc" },
      distinct: ["invoiceUrl"],
      take: 50,
      include: { product: { select: { itemCode: true, name: true } }, supplier: { select: { name: true } } },
    });

    res.json({
      prices,
      defaultMargin1: m1,
      defaultMargin2: m2,
      invoices: invoices.filter((i) => i.invoiceUrl).map((i) => ({
        id: i.id,
        invoiceUrl: i.invoiceUrl,
        productName: i.product.name,
        itemCode: i.product.itemCode,
        supplierName: i.supplier?.name || null,
        date: i.date,
      })),
      pagination: { total, page: Math.max(1, Number(page) || 1), limit: Math.min(200, Math.max(1, Number(limit) || 20)), pages: Math.ceil(total / Math.min(200, Math.max(1, Number(limit) || 20))) },
    });
  } catch (error) {
    console.error("Error al calcular precios:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:productId — Actualizar precio por mayor (requiere permiso del módulo "precios")
router.put("/:productId", authorizeModule("precios"), async (req: AuthRequest, res: Response) => {
  try {
    const { productId } = req.params;
    const { wholesalePrice } = req.body;

    if (wholesalePrice === undefined || wholesalePrice === null) {
      return res.status(400).json({ message: "El campo wholesalePrice es obligatorio" });
    }

    const price = Number(wholesalePrice);
    if (isNaN(price) || price <= 0) {
      return res.status(400).json({ message: "El precio por mayor debe ser un número mayor a 0" });
    }

    const product = await prisma.product.findUnique({ where: { id: Number(productId) } });
    if (!product) return res.status(404).json({ message: "Producto no encontrado" });

    const updated = await prisma.product.update({
      where: { id: Number(productId) },
      data: { wholesalePrice: price },
      select: { id: true, name: true, itemCode: true, wholesalePrice: true },
    });

    res.json({
      id: updated.id,
      productName: updated.name,
      itemCode: updated.itemCode,
      wholesalePrice: Number(updated.wholesalePrice),
    });
  } catch (error) {
    console.error("Error al actualizar precio:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST /apply — Aplicar Precio 1 (mayorista) y Precio 2 (minorista) calculados desde el costo con márgenes
// Opcional: filtrar por factura (costId) para aplicar solo a los productos de esa factura
router.post("/apply", authorizeModule("precios"), async (req: AuthRequest, res: Response) => {
  try {
    const { margin1, margin2, costId } = req.body;
    const m1 = Number.isFinite(Number(margin1)) ? Number(margin1) : DEFAULT_MARGIN1;
    const m2 = Number.isFinite(Number(margin2)) ? Number(margin2) : DEFAULT_MARGIN2;
    if (m1 < 0 || m2 < 0) return res.status(400).json({ message: "Los márgenes deben ser mayores o iguales a 0" });

    const where: any = {};
    if (costId) {
      const c = await prisma.cost.findUnique({ where: { id: Number(costId) }, include: { product: true } });
      if (!c) return res.status(404).json({ message: "Factura/costo no encontrado" });
      where.id = c.productId;
    } else {
      where.cost = { not: null };
    }

    const products = await prisma.product.findMany({
      where,
      include: { costs: { orderBy: { date: "desc" }, take: 1 } },
    });

    let updated = 0;
    for (const p of products) {
      const cost = p.costs[0]?.costPrice ? Number(p.costs[0].costPrice) : p.cost ? Number(p.cost) : 0;
      if (cost <= 0) continue;
      const price1 = Number((cost * (1 + m1 / 100)).toFixed(2));
      const price2 = Number((cost * (1 + m2 / 100)).toFixed(2));
      await prisma.product.update({ where: { id: p.id }, data: { price1, price2 } });
      updated++;
    }

    res.json({ updated, margin1: m1, margin2: m2, costId: costId ? Number(costId) : null });
  } catch (error: any) {
    console.error("Error al aplicar precios:", error);
    res.status(500).json({ message: error.message || "Error interno del servidor" });
  }
});

// GET /export — Exportar precios a CSV
router.get("/export", async (req: AuthRequest, res: Response) => {
  try {
    const margin1 = Number.isFinite(Number(req.query.margin1)) ? Number(req.query.margin1) : DEFAULT_MARGIN1;
    const margin2 = Number.isFinite(Number(req.query.margin2)) ? Number(req.query.margin2) : DEFAULT_MARGIN2;

    const products = await prisma.product.findMany({
      where: { cost: { not: null } },
      include: { costs: { orderBy: { date: "desc" }, take: 1 } },
      orderBy: { name: "asc" },
    });

    const rows = products.map((p) => {
      const cost = p.costs[0]?.costPrice ? Number(p.costs[0].costPrice) : p.cost ? Number(p.cost) : 0;
      return {
        itemCode: p.itemCode,
        name: p.name,
        brand: p.brand,
        model: p.model,
        years: p.year,
        detail: p.detail || "",
        cost: Number(cost.toFixed(2)),
        precioMayorista: Number((cost * (1 + margin1 / 100)).toFixed(2)),
        precioMinorista: Number((cost * (1 + margin2 / 100)).toFixed(2)),
        wholesalePrice: p.wholesalePrice ? Number(p.wholesalePrice) : 0,
      };
    });

    const esc = (v: any) => {
      const s = v == null ? "" : String(v);
      if (/[",\n\r]/.test(s)) {
        return `"${s.replace(/"/g, '""')}"`;
      }
      return s;
    };

    const header = ["Codigo Fabrica", "Nombre", "Marca", "Modelo", "Año", "Detalle", "Costo", "Precio 1 (Mayorista)", "Precio 2 (Minorista)", "Precio Mayor"];
    const csvLines = [header, ...rows.map((r) => [r.itemCode, r.name, r.brand, r.model, r.years, r.detail, r.cost, r.precioMayorista, r.precioMinorista, r.wholesalePrice].map(esc))];
    const csv = "\uFEFF" + csvLines.map((l) => l.join(",")).join("\r\n");

    res.json({ data: rows, total: rows.length, csv });
  } catch (error) {
    console.error("Error al exportar precios:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
