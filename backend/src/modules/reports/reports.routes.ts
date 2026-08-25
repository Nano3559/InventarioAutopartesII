import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);

// GET /sales — Ventas filtradas
router.get("/sales", async (req: AuthRequest, res: Response) => {
  try {
    const { brand, model, month, locationId, supplierId, startDate, endDate, page = "1", limit = "50" } = req.query;

    const where: any = {};

    if (locationId && typeof locationId === "string") where.locationId = Number(locationId);

    if (startDate || endDate) {
      where.saleDate = {};
      if (startDate && typeof startDate === "string") where.saleDate.gte = new Date(startDate);
      if (endDate && typeof endDate === "string") {
        const end = new Date(endDate);
        end.setHours(23, 59, 59, 999);
        where.saleDate.lte = end;
      }
    }

    if (month && typeof month === "string") {
      const [year, mon] = month.split("-").map(Number);
      const start = new Date(year, mon - 1, 1);
      const end = new Date(year, mon, 0, 23, 59, 59, 999);
      where.saleDate = { gte: start, lte: end };
    }

    if (brand && typeof brand === "string") {
      where.items = { some: { product: { brand: { contains: brand, mode: "insensitive" } } } };
    }

    if (model && typeof model === "string") {
      where.items = { some: { product: { model: { contains: model, mode: "insensitive" } } } };
    }

    if (brand && model) {
      where.items = {
        some: {
          product: {
            brand: { contains: brand, mode: "insensitive" },
            model: { contains: model, mode: "insensitive" },
          },
        },
      };
    }

    const skip = (Number(page) - 1) * Number(limit);
    const take = Number(limit);

    const [sales, total, summary] = await Promise.all([
      prisma.sale.findMany({
        where,
        include: {
          user: { select: { id: true, name: true } },
          location: { select: { id: true, name: true } },
          customer: { select: { id: true, name: true } },
          items: { include: { product: { select: { id: true, name: true, brand: true, model: true, itemCode: true } } } },
          payments: true,
        },
        orderBy: { saleDate: "desc" },
        skip,
        take,
      }),
      prisma.sale.count({ where }),
      prisma.sale.aggregate({ where, _sum: { total: true }, _count: true }),
    ]);

    res.json({
      sales: sales.map((s) => ({
        id: s.id,
        date: s.saleDate,
        type: s.type,
        total: Number(s.total),
        location: s.location,
        customer: s.customer,
        user: s.user,
        itemCount: s.items.length,
        payments: s.payments.map((p) => ({ method: p.method, amount: Number(p.amount) })),
      })),
      summary: {
        totalSales: Number(summary._sum.total) || 0,
        count: summary._count,
        average: summary._count > 0 ? Number((Number(summary._sum.total) / summary._count).toFixed(2)) : 0,
      },
      pagination: { total, page: Number(page), limit: take, pages: Math.ceil(total / take) },
    });
  } catch (error) {
    console.error("Error en reporte de ventas:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /inventory — Stock por ubicación
router.get("/inventory", async (req: AuthRequest, res: Response) => {
  try {
    const { brand, model, locationId, lowStock } = req.query;

    const where: any = {};
    if (locationId && typeof locationId === "string") where.locationId = Number(locationId);

    if (brand && typeof brand === "string") {
      where.product = { ...where.product, brand: { contains: brand, mode: "insensitive" } };
    }
    if (model && typeof model === "string") {
      where.product = { ...where.product, model: { contains: model, mode: "insensitive" } };
    }

    const inventories = await prisma.inventory.findMany({
      where,
      include: {
        product: { select: { id: true, name: true, itemCode: true, brand: true, model: true, manufacturer: true } },
        location: { select: { id: true, name: true, type: true } },
      },
      orderBy: { product: { name: "asc" } },
    });

    let filtered = inventories;
    if (lowStock === "true") {
      filtered = inventories.filter((i) => i.stock <= i.minStock);
    }

    const byLocation = filtered.reduce((acc: any, inv) => {
      const locName = inv.location.name;
      if (!acc[locName]) acc[locName] = { location: inv.location, items: [], totalStock: 0 };
      acc[locName].items.push({
        ...inv,
        product: inv.product,
        stock: inv.stock,
        minStock: inv.minStock,
        status: inv.stock === 0 ? "AGOTADO" : inv.stock <= inv.minStock ? "BAJO" : "OK",
      });
      acc[locName].totalStock += inv.stock;
      return acc;
    }, {});

    res.json({
      locations: Object.values(byLocation),
      totalProducts: filtered.length,
      totalStock: filtered.reduce((sum, i) => sum + i.stock, 0),
      lowStockCount: filtered.filter((i) => i.stock <= i.minStock).length,
    });
  } catch (error) {
    console.error("Error en reporte de inventario:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /suppliers — Reporte por proveedor
router.get("/suppliers", async (req: AuthRequest, res: Response) => {
  try {
    const suppliers = await prisma.supplier.findMany({
      include: {
        costs: {
          include: {
            product: { select: { id: true, name: true, itemCode: true, brand: true } },
          },
          orderBy: { date: "desc" },
        },
      },
      orderBy: { name: "asc" },
    });

    const report = suppliers.map((s) => {
      const totalCost = s.costs.reduce((sum, c) => sum + Number(c.costPrice), 0);
      const productsCount = new Set(s.costs.map((c) => c.productId)).size;
      const lastPurchase = s.costs[0]?.date || null;

      return {
        id: s.id,
        name: s.name,
        nit: s.nit,
        phone: s.phone,
        totalPurchases: totalCost,
        productsCount,
        lastPurchase,
        recentCosts: s.costs.slice(0, 10).map((c) => ({
          id: c.id,
          product: c.product,
          costPrice: Number(c.costPrice),
          exchangeRate: c.exchangeRate ? Number(c.exchangeRate) : null,
          date: c.date,
        })),
      };
    });

    res.json({
      suppliers: report,
      summary: {
        totalSuppliers: report.length,
        totalPurchases: report.reduce((sum, s) => sum + s.totalPurchases, 0),
      },
    });
  } catch (error) {
    console.error("Error en reporte de proveedores:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /monthly — Reporte mensual por tienda con costos
router.get("/monthly", async (req: AuthRequest, res: Response) => {
  try {
    const { year, month } = req.query;

    const targetYear = year ? Number(year) : new Date().getFullYear();
    const targetMonth = month ? Number(month) : new Date().getMonth() + 1;

    const startDate = new Date(targetYear, targetMonth - 1, 1);
    const endDate = new Date(targetYear, targetMonth, 0, 23, 59, 59, 999);

    const [sales, returns, locations] = await Promise.all([
      prisma.sale.findMany({
        where: { saleDate: { gte: startDate, lte: endDate } },
        include: {
          location: { select: { id: true, name: true } },
          items: { include: { product: { select: { id: true, name: true, brand: true } } } },
        },
      }),
      prisma.return.findMany({
        where: { date: { gte: startDate, lte: endDate } },
        include: { sale: { select: { locationId: true, location: { select: { name: true } } } } },
      }),
      prisma.location.findMany({ select: { id: true, name: true, type: true } }),
    ]);

    const byLocation: any[] = locations.map((loc) => {
      const locSales = sales.filter((s) => s.locationId === loc.id);
      const locReturns = returns.filter((r) => r.sale.locationId === loc.id);
      const totalSales = locSales.reduce((sum, s) => sum + Number(s.total), 0);
      const totalReturns = locReturns.reduce((sum, r) => sum + Number(r.amount), 0);
      const saleCount = locSales.length;

      const productSales: any = {};
      for (const sale of locSales) {
        for (const item of sale.items) {
          const key = item.productId;
          if (!productSales[key]) {
            productSales[key] = { product: item.product, quantity: 0, total: 0 };
          }
          productSales[key].quantity += item.quantity;
          productSales[key].total += Number(item.subtotal);
        }
      }

      return {
        location: loc,
        summary: {
          totalSales,
          totalReturns,
          netSales: totalSales - totalReturns,
          saleCount,
          averagePerSale: saleCount > 0 ? Number((totalSales / saleCount).toFixed(2)) : 0,
        },
        topProducts: Object.values(productSales)
          .sort((a: any, b: any) => b.total - a.total)
          .slice(0, 10)
          .map((p: any) => ({
            product: p.product,
            quantitySold: p.quantity,
            totalRevenue: p.total,
          })),
      };
    });

    const totalGeneral = byLocation.reduce((sum, l) => sum + l.summary.totalSales, 0);
    const returnsGeneral = byLocation.reduce((sum, l) => sum + l.summary.totalReturns, 0);

    res.json({
      period: { year: targetYear, month: targetMonth, startDate, endDate },
      locations: byLocation,
      summary: {
        totalSales: totalGeneral,
        totalReturns: returnsGeneral,
        netSales: totalGeneral - returnsGeneral,
        totalLocations: locations.length,
        activeLocations: byLocation.filter((l) => l.summary.saleCount > 0).length,
      },
    });
  } catch (error) {
    console.error("Error en reporte mensual:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
