import { errorDominio } from "../../shared/utils/errorDominio";
import { money, validatePriceConfiguration } from "../../shared/utils/pricing";
import { esErrorDominio } from "../../shared/utils/errorDominio";
import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate, authorize, authorizeModule } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import { parsePagination } from "../../shared/utils/pagination";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);
router.use(authorize("ADMIN"));
router.use(authorizeModule("precios"));

// Márgenes por defecto para los precios:
//   margin1 calcula POR MAYOR y margin2 calcula POR MENOR. price2 queda legacy.
const DEFAULT_MARGIN1 = 25; // % sobre costo para POR MAYOR
const DEFAULT_MARGIN2 = 45; // % sobre costo para POR MENOR
const margin = (value: unknown, fallback: number) => {
  if (value === undefined) return fallback;
  const n = Number(value);
  if (typeof value === "boolean" || value === null || value === "" || !Number.isFinite(n) || n < 0 || n > 200) throw errorDominio("El margen debe estar entre 0 y 200");
  return n;
};

// GET / — Calcular precios desde costo con márgenes configurables y filtro por factura
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { search, costId, page = "1", limit = "20" } = req.query;
    const margin1 = margin(req.query.margin1, DEFAULT_MARGIN1);
    const margin2 = margin(req.query.margin2, DEFAULT_MARGIN2);
    const m1 = Number.isFinite(margin1) ? margin1 : DEFAULT_MARGIN1;
    const m2 = Number.isFinite(margin2) ? margin2 : DEFAULT_MARGIN2;
    const pg = parsePagination(page, limit, 200);

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
          costs: { orderBy: [{ date: "desc" }, { id: "desc" }], include: { supplier: { select: { id: true, name: true } } } },
        },
        orderBy: { name: "asc" },
        skip: pg.skip,
        take: pg.take,
      }),
      prisma.product.count({ where }),
    ]);

    const prices = products.map((p) => {
      const latestCost = p.costs[0]?.costPrice ? Number(p.costs[0].costPrice) : p.cost ? Number(p.cost) : 0;
      const suggestedWholesale = Number((latestCost * (1 + m1 / 100)).toFixed(2)); // POR MAYOR
      const suggestedRetail = Number((latestCost * (1 + m2 / 100)).toFixed(2)); // POR MENOR

      return {
        id: p.id,
        itemCode: p.itemCode,
        productName: p.name,
        brand: p.brand,
        model: p.model,
        years: p.year,
        detail: p.detail || "",
        cost: latestCost,
        suggestions: [20, 30, 40, 50, 60, 70, 80].map((percentage) => ({ percentage, price: Number((latestCost * (1 + percentage / 100)).toFixed(2)) })),
        costs: p.costs.map((c) => ({
          id: c.id,
          costPrice: Number(c.costPrice),
          supplierName: c.supplier?.name || null,
          invoiceUrl: c.invoiceUrl || null,
          date: c.date,
        })),
        suggestedWholesale,
        suggestedRetail,
        retailPrice: p.price1 ? Number(p.price1) : 0,
        
        wholesalePrice: p.wholesalePrice ? Number(p.wholesalePrice) : null,
        costId: p.costs[0]?.id ?? null,
        costDate: p.costs[0]?.date ?? null,
        invoiceUrl: p.costs[0]?.invoiceUrl ?? null,
      };
    });

    // Lista de facturas/costos disponibles para el filtro
    const invoices = await prisma.cost.findMany({
      orderBy: [{ date: "desc" }, { id: "desc" }],
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
      pagination: { total, page: pg.page, limit: pg.take, pages: Math.ceil(total / pg.take) },
    });
  } catch (error) {
    if (esErrorDominio(error)) return res.status(400).json({ message: error.message });
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

    const price = money(wholesalePrice, "Precio por mayor");
    const updated = await prisma.$transaction(async (tx) => {
      const id = Number(productId);
      await tx.$queryRaw`SELECT id FROM "Product" WHERE id = ${id} FOR UPDATE`;
      const product = await tx.product.findUnique({ where: { id } });
      if (!product) return null;
      validatePriceConfiguration({ ...product, wholesalePrice: price });
      return tx.product.update({ where: { id }, data: { wholesalePrice: price }, select: { id: true, name: true, itemCode: true, wholesalePrice: true } });
    });
    if (!updated) return res.status(404).json({ message: "Producto no encontrado" });

    res.json({
      id: updated.id,
      productName: updated.name,
      itemCode: updated.itemCode,
      wholesalePrice: Number(updated.wholesalePrice),
    });
  } catch (error) {
    if (esErrorDominio(error)) return res.status(400).json({ message: error.message });
    console.error("Error al actualizar precio:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// POST /apply — Aplicar POR MENOR y POR MAYOR calculados desde el costo con márgenes
// Opcional: filtrar por factura (costId) para aplicar solo a los productos de esa factura
router.post("/apply", authorizeModule("precios"), async (req: AuthRequest, res: Response) => {
  try {
    const { margin1, margin2, costId } = req.body;
    const m1 = margin(margin1, DEFAULT_MARGIN1);
    const m2 = margin(margin2, DEFAULT_MARGIN2);
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
      include: { costs: { orderBy: [{ date: "desc" }, { id: "desc" }], take: 1 } },
    });

    const updated = await prisma.$transaction(async (tx) => {
      let count = 0;
      for (const ref of [...products].sort((a, b) => a.id - b.id)) {
        await tx.$queryRaw`SELECT id FROM "Product" WHERE id = ${ref.id} FOR UPDATE`;
        const p = await tx.product.findUniqueOrThrow({ where: { id: ref.id }, include: { costs: { orderBy: [{ date: "desc" }, { id: "desc" }], take: 1 } } });
        const cost = Number(p.costs[0]?.costPrice ?? p.cost ?? 0);
        if (cost <= 0) continue;
        const wholesalePrice = money(cost * (1 + m1 / 100), "Precio por mayor");
        const price1 = money(cost * (1 + m2 / 100), "Precio por menor");
        validatePriceConfiguration({ ...p, cost, price1, wholesalePrice });
        await tx.product.update({ where: { id: p.id }, data: { price1, wholesalePrice } });
        count++;
      }
      return count;
    }, { timeout: 20000 });

    res.json({ updated, margin1: m1, margin2: m2, costId: costId ? Number(costId) : null });
  } catch (error: any) {
    if (esErrorDominio(error)) return res.status(400).json({ message: error.message });
    console.error("Error al aplicar precios:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /export — Exportar precios a CSV
router.get("/export", async (req: AuthRequest, res: Response) => {
  try {
    const margin1 = margin(req.query.margin1, DEFAULT_MARGIN1);
    const margin2 = margin(req.query.margin2, DEFAULT_MARGIN2);

    const products = await prisma.product.findMany({
      where: { cost: { not: null } },
      include: { costs: { orderBy: [{ date: "desc" }, { id: "desc" }], take: 1 } },
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
        retailPrice: Number(p.price1),
        suggestedWholesale: Number((cost * (1 + margin1 / 100)).toFixed(2)),
        suggestedRetail: Number((cost * (1 + margin2 / 100)).toFixed(2)),
        wholesalePrice: p.wholesalePrice ? Number(p.wholesalePrice) : null,
      };
    });

    const esc = (v: any) => {
      const s = v == null ? "" : String(v);
      if (/[",\n\r]/.test(s)) {
        return `"${s.replace(/"/g, '""')}"`;
      }
      return s;
    };

    const header = ["Codigo Fabrica", "Nombre", "Marca", "Modelo", "Año", "Detalle", "Costo", "Por mayor sugerido", "Por menor sugerido", "Por menor", "Por mayor"];
    const csvLines = [header, ...rows.map((r) => [r.itemCode, r.name, r.brand, r.model, r.years, r.detail, r.cost, r.suggestedWholesale, r.suggestedRetail, r.retailPrice, r.wholesalePrice].map(esc))];
    const csv = "\uFEFF" + csvLines.map((l) => l.join(",")).join("\r\n");

    res.json({ data: rows, total: rows.length, csv });
  } catch (error) {
    if (esErrorDominio(error)) return res.status(400).json({ message: error.message });
    console.error("Error al exportar precios:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
