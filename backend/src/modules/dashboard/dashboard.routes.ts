import { safeError } from "../../shared/utils/safeError";
import { fechaNegocio, inicioDiaNegocio, rangoMesNegocio } from "../../shared/utils/rangoFechas";
import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate, authorize, requireTiendaLocation } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import { dashboardFailure } from "./dashboardFailure";

const router = Router();
import prisma from "../../config/database";

export function createDashboardHandler(database = prisma) {
return async function dashboardHandler(req: AuthRequest, res: Response) {
  const prisma = database;
  try {
    const now = new Date();
    const startOfDay = inicioDiaNegocio(fechaNegocio(now))!;
    const currentMonth = fechaNegocio(now).slice(0, 7);
    const selectedMonth = req.query?.month ?? currentMonth;
    const range = rangoMesNegocio(selectedMonth);
    if (!range || typeof selectedMonth !== "string" || selectedMonth > currentMonth) return res.status(400).json({ code: "INVALID_PERIOD", message: "Seleccione un mes válido hasta el mes actual." });
    const startOfMonth = range.gte;
    const endOfMonth = new Date(Math.min(now.getTime(), range.lte.getTime()));

    // Un usuario TIENDA solo ve los datos de su propia tienda.
    const userLoc = req.user?.locationId ?? null;
    const isTienda = req.user?.role === "TIENDA";
    if (isTienda && !userLoc) return res.status(403).json({ message: "Usuario TIENDA sin ubicación asignada" });
    const rawLocation = req.query?.locationId;
    if (rawLocation !== undefined && (typeof rawLocation !== "string" || !/^[1-9]\d{0,9}$/.test(rawLocation) || Number(rawLocation) > 2147483647)) return res.status(400).json({ code: "INVALID_LOCATION" });
    if (isTienda && rawLocation !== undefined && Number(rawLocation) !== userLoc) return res.status(403).json({ code: "LOCATION_FORBIDDEN" });
    const scopedLocation = isTienda ? userLoc : rawLocation === undefined ? null : Number(rawLocation);
    const locWhere: any = scopedLocation ? { locationId: scopedLocation } : {};
    const productScope = scopedLocation ? { inventories: { some: { locationId: scopedLocation } } } : {};

    const totalProducts = await prisma.product.count({ where: productScope });
    const [productsWithInventory, lowStockItems, locations, stockAgg] = await Promise.all([
      prisma.product.findMany({ where: productScope, select: { id: true, inventories: { ...(scopedLocation ? { where: { locationId: scopedLocation } } : {}), select: { stock: true } } } }),
      prisma.inventory.findMany({ where: { stock: { gt: 0 }, minStock: { gt: 0 }, ...locWhere }, select: { productId: true, locationId: true, stock: true, minStock: true } }),
      prisma.location.findMany({ select: { id: true, name: true, type: true } }),
      prisma.inventory.groupBy({ by: ["locationId"], ...(scopedLocation ? { where: { locationId: scopedLocation } } : {}), _sum: { stock: true } }),
    ]);
    if (rawLocation !== undefined && !locations.some(l => l.id === Number(rawLocation))) return res.status(400).json({ code: "UNKNOWN_LOCATION" });
    const productsWithoutStock = productsWithInventory.filter(p => p.inventories.every(inv => inv.stock === 0)).length;
    const criticalStockItems = lowStockItems.filter(item => item.stock <= item.minStock);
    const productsWithLowStock = criticalStockItems.length;
    const stockByLocation = stockAgg.map(agg => {
      const loc = locations.find(l => l.id === agg.locationId);
      return { locationId: agg.locationId, name: loc?.name || "Desconocido", type: loc?.type || "TIENDA", totalStock: Number(agg._sum.stock || 0) };
    });

    // A missing sales column must not hide independently available inventory.
    // Never relax the CONFIRMED filter or convert unknown financial totals to zero.
    const sales = await (async () => {
      try {
        // Avoid a failed statement inside read-only transactions on legacy DBs.
        if (typeof prisma.$queryRaw === "function") {
          const columns = await prisma.$queryRaw<{ ready: boolean }[]>`
            SELECT EXISTS (
              SELECT 1 FROM information_schema.columns
              WHERE table_schema = 'public' AND table_name = 'Sale' AND column_name = 'status'
            ) AS ready`;
          if (!columns[0]?.ready) return null;
        }
        const salesToday = await prisma.sale.aggregate({
          where: { status: "CONFIRMED", saleDate: { gte: startOfDay, lte: now }, ...locWhere },
          _count: true,
          _sum: { total: true },
        });
        const [salesMonth, salesByLocationAgg, saleItems, recentSales] = await Promise.all([

          prisma.sale.aggregate({
          where: { status: "CONFIRMED", saleDate: { gte: startOfMonth, lte: endOfMonth }, ...locWhere },
          _count: true,
          _sum: { total: true },
        }),
          prisma.sale.groupBy({
          by: ["locationId"],
          where: { status: "CONFIRMED", saleDate: { gte: startOfMonth, lte: endOfMonth }, ...locWhere },
          _count: true,
          _sum: { total: true },
        }),
          prisma.saleItem.findMany({
          where: { sale: { status: "CONFIRMED", saleDate: { gte: startOfMonth, lte: endOfMonth }, ...locWhere } },
          include: { product: { select: { brand: true, model: true, name: true, itemCode: true } } },
        }),
          prisma.sale.findMany({
          where: { status: "CONFIRMED", ...locWhere },
          take: 10,
          orderBy: { saleDate: "desc" },
          select: {
            id: true, saleDate: true, total: true, type: true,
            location: { select: { name: true } },
            user: { select: { name: true } },
            customer: { select: { name: true } },
            items: { select: { id: true } },
          },
        })
        ]);




        const salesByLocation = salesByLocationAgg.map((agg) => {
          const loc = locations.find((l) => l.id === agg.locationId);
          return {
            locationId: agg.locationId,
            name: loc?.name || "Desconocido",
            count: agg._count,
            total: Number(agg._sum.total || 0),
          };
        });



        const brandMap = new Map<string, { totalQuantity: number; totalAmount: number }>();
        const vehicleMap = new Map<string, { totalQuantity: number; totalAmount: number }>();
        for (const item of saleItems) {
          const brand = item.product.brand;
          const brandExisting = brandMap.get(brand) || { totalQuantity: 0, totalAmount: 0 };
          brandExisting.totalQuantity += item.quantity;
          brandExisting.totalAmount += Number(item.subtotal);
          brandMap.set(brand, brandExisting);

          const model = item.product.model;
          const vehicleExisting = vehicleMap.get(model) || { totalQuantity: 0, totalAmount: 0 };
          vehicleExisting.totalQuantity += item.quantity;
          vehicleExisting.totalAmount += Number(item.subtotal);
          vehicleMap.set(model, vehicleExisting);
        }
        const salesByBrand = Array.from(brandMap.entries())
          .map(([brand, v]) => ({ brand, ...v }))
          .sort((a, b) => b.totalAmount - a.totalAmount);
        const salesByVehicle = Array.from(vehicleMap.entries())
          .map(([model, v]) => ({ model, ...v }))
          .sort((a, b) => b.totalAmount - a.totalAmount);



        const productMap = new Map<number, { productId: number; name: string; itemCode: string; units: number; amount: number }>();
        for (const item of saleItems) {
          const row = productMap.get(item.productId) ?? { productId: item.productId, name: item.product.name, itemCode: item.product.itemCode, units: 0, amount: 0 };
          row.units += item.quantity; row.amount += Number(item.subtotal); productMap.set(item.productId, row);
        }
        return { salesToday, salesMonth, salesByLocation, salesByBrand, salesByVehicle, recentSales,
          soldUnits: saleItems.reduce((sum, item) => sum + item.quantity, 0),
          topProducts: [...productMap.values()].sort((a, b) => b.units - a.units || a.productId - b.productId).slice(0, 10) };
      } catch (error) {
        const code = error && typeof error === "object" && "code" in error ? String(error.code) : "";
        if (code === "P2021" || code === "P2022") return null;
        throw error;
      }
    })();

    const recentMovements = await prisma.movement.findMany({
      ...(scopedLocation ? { where: { OR: [{ fromLocationId: scopedLocation }, { toLocationId: scopedLocation }] } } : {}),
      take: 10,
      orderBy: { date: "desc" },
      select: {
        id: true, date: true, quantity: true,
        product: { select: { name: true, itemCode: true } },
        fromLocation: { select: { name: true } },
        toLocation: { select: { name: true } },
        user: { select: { name: true } },
      },
    });

    const pendingRequestCount = await prisma.productRequest.count({ where: { status: "PENDIENTE", ...locWhere } });
    const pendingRequests = await prisma.productRequest.findMany({
      where: { status: "PENDIENTE", ...locWhere },
      take: 10,
      orderBy: { createdAt: "desc" },
      select: {
        id: true, quantity: true, createdAt: true,
        product: { select: { name: true, itemCode: true } },
        location: { select: { name: true } },
        requestedBy: { select: { name: true } },
      },
    });

    const criticalStock = criticalStockItems.map((item) => ({
      product: "",
      itemCode: "",
      locationId: item.locationId,
      location: "",
      stock: item.stock,
      minStock: item.minStock,
      productId: item.productId,
    }));

    const productIds = [...new Set(criticalStock.map((c) => c.productId))];
    const locationIds = [...new Set(criticalStock.map((c) => c.locationId))];
    const [products, locs] = await Promise.all([
      prisma.product.findMany({
        where: { id: { in: productIds } },
        select: { id: true, name: true, itemCode: true },
      }),
      prisma.location.findMany({
        where: { id: { in: locationIds } },
        select: { id: true, name: true },
      }),
    ]);
    const criticalStockFormatted = criticalStock.map((c) => ({
      product: products.find((p) => p.id === c.productId)?.name || "",
      itemCode: products.find((p) => p.id === c.productId)?.itemCode || "",
      location: locs.find((l) => l.id === c.locationId)?.name || "",
      stock: c.stock,
      minStock: c.minStock,
    }));

    res.json({
      period: { month: selectedMonth, locationId: scopedLocation, timeZone: "America/La_Paz", generatedAt: now.toISOString(), inventory: "CURRENT_NOT_HISTORICAL" },
      availableLocations: locations.filter(l => !isTienda || l.id === userLoc),
      analytics: sales ? { soldUnits: sales.soldUnits, topProducts: sales.topProducts } : null,
      summary: {
        totalProducts,
        productsWithoutStock,
        productsWithLowStock,
        salesToday: sales ? sales.salesToday._count : null,
        salesTodayTotal: sales ? Number(sales.salesToday._sum.total || 0) : null,
        salesMonth: sales ? sales.salesMonth._count : null,
        salesMonthTotal: sales ? Number(sales.salesMonth._sum.total || 0) : null,
        pendingRequests: pendingRequestCount,
        criticalStock: criticalStockFormatted.length,
      },
      stockByLocation,
      availability: { sales: sales ? "AVAILABLE" : "SCHEMA_UNAVAILABLE" },
      salesByLocation: sales?.salesByLocation ?? [],
      salesByBrand: sales?.salesByBrand ?? [],
      salesByVehicle: sales?.salesByVehicle ?? [],
      recentSales: sales ? sales.recentSales.map((sale) => ({
        id: sale.id,
        date: sale.saleDate,
        total: Number(sale.total),
        type: sale.type,
        location: sale.location.name,
        user: sale.user.name,
        customer: sale.customer?.name || "Cliente general",
        itemCount: sale.items.length,
      })) : [],
      recentMovements: recentMovements.map((m) => ({
        id: m.id,
        date: m.date,
        product: m.product.name,
        itemCode: m.product.itemCode,
        from: m.fromLocation.name,
        to: m.toLocation.name,
        quantity: m.quantity,
        user: m.user.name,
      })),
      pendingRequests: pendingRequests.map((r) => ({
        id: r.id,
        product: r.product.name,
        itemCode: r.product.itemCode,
        quantity: r.quantity,
        location: r.location.name,
        requestedBy: r.requestedBy.name,
        date: r.createdAt,
      })),
      criticalStock: criticalStockFormatted,
    });
  } catch (error) {
    console.error("Error en dashboard:", safeError(error));
    const failure = dashboardFailure(error);
    res.status(failure.status).json({ message: failure.message, code: failure.code });
  }
}
}
export const dashboardHandler = createDashboardHandler();
router.get("/", authenticate, authorize("ADMIN", "TIENDA", "INVENTARIO"), requireTiendaLocation, dashboardHandler);

export default router;
