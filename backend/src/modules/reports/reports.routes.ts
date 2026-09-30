import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate } from "../../shared/middlewares/auth";
import { parsePagination } from "../../shared/utils/pagination";
import { rangoFechasNegocio, rangoMesNegocio } from "../../shared/utils/rangoFechas";
import { AuthRequest } from "../../shared/types";
import { ROLES_CON_COSTOS as ROLES_CON_COSTOS_SHARED, alcanceDeFiltro, SIN_ALCANCE } from "../../shared/utils/scope";

const router = Router();
const prisma = new PrismaClient();

// Roles autorizados a ver información financiera (costos de mercadería, costos de
// tienda y utilidad). Allow-list explícita: el nombre del rol viene de RoleModel.name
// (tabla data-driven editable desde el panel de permisos), por lo que un deny-list
// ("cualquier cosa que no sea TIENDA") terminaría concediendo costos a roles futuros.
// La definición vive en shared/utils/scope.ts, junto con la de search-image y visión,
// para que las tres superficies no puedan divergir.
export const ROLES_CON_COSTOS = ROLES_CON_COSTOS_SHARED;

router.use(authenticate);

/**
 * DECISIÓN PENDIENTE — por qué NO hay `authorizeModule("reportes")` en este router.
 *
 * ACCESO ACTUAL (verificado): cualquiera con un JWT válido entra a /api/reports/*, y
 * la SEGURIDAD DE LOS DATOS se aplica dentro de cada endpoint, no en el router:
 *  - /sales, /inventory, /monthly → acotados a la ubicación del usuario; los costos,
 *    utilidad y margen solo a ADMIN/INVENTARIO (ROLES_CON_COSTOS).
 *  - /suppliers → 403 salvo ADMIN/INVENTARIO (agrega costos de compra por proveedor).
 *  - El PDF de /monthly heredea exactamente el mismo `puedeVerCostos`, así que un
 *    TIENDA no puede exportar costos por la vía del PDF.
 *
 * QUIÉN TIENE EL PERMISO `reportes` HOY: NADIE. Los permisos sembrados son
 *   ADMIN      -> ["*"]
 *   TIENDA     -> ["ventas", "inventario", "solicitudes", "devoluciones"]
 *   INVENTARIO -> ["movimientos", "inventario", "solicitudes"]
 * ADMIN pasa siempre (línea 96 y 110 del middleware,Atribución por nombre de rol), pero
 * TIENDA e INVENTARIO no tienen la cadena "reportes".
 *
 * QUÉ SE ROMPERÍA AL ACTIVARLO: añadir `router.use(authorizeModule("reportes"))` sin
 * tocar los permisos dejaría a TIENDA e INVENTARIO con 403 en TODO /api/reports,
 * incluidos los reportes operativos que hoy sí ven (sus propias ventas, su inventario y
 * su resumen mensual sin costos). Para activarlo hay que decidir antes qué roles lo
 * reciben y añadir "reportes" a `RoleModel.permissions` (seed y panel de permisos).
 *
 * Alternativa de menor riesgo, si se quiere endurecer sin cambiar permisos: exigir
 * `authorizeModule("inventario")` o `authorizeModule("ventas")` según el reporte, que sí
 * existen en los tres roles. Queda como decisión de arquitectura, no se aplica aquí.
 */

// GET /sales — Ventas filtradas
router.get("/sales", async (req: AuthRequest, res: Response) => {
  try {
    const { brand, model, month, locationId, supplierId, startDate, endDate, noInvoice, product, page = "1", limit = "50" } = req.query;

    const where: any = {};

    let effectiveLocationId: number | null = null;
    if (locationId && typeof locationId === "string") effectiveLocationId = Number(locationId);
    if (effectiveLocationId) where.locationId = effectiveLocationId;

    const alcanceVentas = alcanceDeFiltro(req.user);
    if (alcanceVentas === SIN_ALCANCE) {
      return res.status(403).json({ message: "Usuario sin ubicación asignada" });
    }
    if (alcanceVentas !== null) where.locationId = alcanceVentas;

    if (noInvoice === "true") where.customerId = null;

    if (startDate || endDate) {
      // Mismo criterio de día de negocio que ventas y devoluciones.
      const rango = rangoFechasNegocio(startDate, endDate);
      if (rango.gte || rango.lte) where.saleDate = rango;
    }

    if (month && typeof month === "string") {
      // Un month inválido se rechaza con 400 en vez de construir new Date(NaN,...)
      // (que terminaba en un 500 al consultarse la base de datos).
      const rangoMes = rangoMesNegocio(month);
      if (!rangoMes) {
        return res.status(400).json({ message: "Parámetro month inválido. Use el formato YYYY-MM" });
      }
      // Si ya hay startDate/endDate se INTERSECTA con el mes (gana el rango más
      // estrecho) en lugar de sobrescribirlo, para que combinar ambos filtros
      // no amplíe el reporte sin avisar.
      const existente = where.saleDate as { gte?: Date; lte?: Date } | undefined;
      if (existente?.gte && existente.gte > rangoMes.gte) rangoMes.gte = existente.gte;
      if (existente?.lte && existente.lte < rangoMes.lte) rangoMes.lte = existente.lte;
      where.saleDate = rangoMes;
    }

    // Filtros por marca/modelo/proveedor/producto se aplican a los productos de las ventas
    const supplierIdEfectivo =
      supplierId && supplierId !== "all" && ROLES_CON_COSTOS.has(req.user?.role ?? "") ? supplierId : undefined;

    if (brand || model || supplierIdEfectivo || product) {
      const productFilter: any = {};
      if (brand && typeof brand === "string") productFilter.brand = { contains: brand, mode: "insensitive" };
      if (model && typeof model === "string") productFilter.model = { contains: model, mode: "insensitive" };
      if (product && typeof product === "string") productFilter.name = { contains: product, mode: "insensitive" };
      if (supplierIdEfectivo && typeof supplierIdEfectivo === "string") {
        const sid = Number(supplierIdEfectivo);
        // El filtro por proveedor no devuelve costos, pero sí permite a un TIENDA
        // sondear qué productos se compraron a qué proveedor variando el supplierId y
        // mirando si el conteo o los totales cambian. Es información comercial que el
        // reporte de proveedores ya le restringe (403 a TIENDA), así que aquí se
        // descarta el parámetro por rol ANTES de construir el filtro: si se dejara
        // entrar sin el predicado, `productFilter` quedaría `{}` y
        // `where.items = { some: { product: {} } }` seguiría aplicándose, cambiando el
        // resultado de la consulta sin filtrar por nada.
        if (!Number.isNaN(sid) && sid >= 1) productFilter.costs = { some: { supplierId: sid } };
      }
      where.items = { some: { product: productFilter } };
    }

    // `?limit=2.7` necesita un entero: sin Math.floor Prisma recibía 2.7 y
    // respondía 500.
    const { page: pg, limit: take, skip } = parsePagination(page, limit, 500);

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
      pagination: { total, page: pg, limit: take, pages: Math.ceil(total / take) },
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

    const alcanceInventario = alcanceDeFiltro(req.user);
    if (alcanceInventario === SIN_ALCANCE) {
      return res.status(403).json({ message: "Usuario sin ubicación asignada" });
    }
    if (alcanceInventario !== null) where.locationId = alcanceInventario;

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

// GET /suppliers — Reporte por proveedor (solo ADMIN/INVENTARIO)
router.get("/suppliers", async (req: AuthRequest, res: Response) => {
  try {
    // Este reporte agrega costos de compra por proveedor: es información financiera
    // interna, así que va por allow-list y no por "rechazar a TIENDA". Un rol futuro
    // o desconocido no debe obtener costos de proveedores por defecto.
    if (!ROLES_CON_COSTOS.has(req.user?.role ?? "")) {
      return res.status(403).json({ message: "Reporte de proveedores no disponible para este rol" });
    }
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

    // El reporte mensual se acota a un mes de negocio. Se construye con
    // rangoMesNegocio (America/La_Paz) en vez de new Date(year, month, ...) para
    // no depender de la zona horaria del servidor, y un mes/año inválido se
    // rechaza con 400 en vez de producir un rango inválido (500).
    //
    // Contrato que ya envía el frontend: ?year=YYYY&month=MM (mes suelto 1-12).
    // Se acepta además ?month=YYYY-MM.
    const mesActual = (() => {
      const ahora = new Date();
      return `${ahora.getFullYear()}-${String(ahora.getMonth() + 1).padStart(2, "0")}`;
    })();

    const anio = year === undefined || String(year).trim() === "" ? null : String(year).trim();
    if (anio !== null && (!/^\d{4}$/.test(anio) || Number(anio) < 1000)) {
      return res.status(400).json({ message: "Parámetro year inválido. Use un año de 4 dígitos" });
    }

    const mesBruto = month === undefined ? "" : String(month).trim();
    let claveMes: string;
    if (mesBruto.includes("-")) {
      claveMes = mesBruto;
    } else if (mesBruto !== "") {
      if (!/^(0?[1-9]|1[0-2])$/.test(mesBruto)) {
        return res.status(400).json({ message: "Parámetro month inválido. Use un mes entre 1 y 12" });
      }
      claveMes = `${anio ?? String(new Date().getFullYear())}-${mesBruto.padStart(2, "0")}`;
    } else {
      claveMes = anio !== null ? `${anio}-01` : mesActual;
    }

    const rangoMes = rangoMesNegocio(claveMes);
    if (!rangoMes) {
      return res.status(400).json({ message: "Parámetro month inválido. Use el formato YYYY-MM" });
    }
    const [targetYear, targetMonth] = claveMes.split("-").map(Number);
    const startDate = rangoMes.gte;
    const endDate = rangoMes.lte;

    // Los roles de la allow-list ven todas las tiendas; el resto queda acotado a la
    // suya, y sin ubicación asignada no ve el reporte.
    const locationScope = alcanceDeFiltro(req.user);
    if (locationScope === SIN_ALCANCE) {
      return res.status(403).json({ message: "Usuario sin ubicación asignada" });
    }

    // Los costos de mercadería y de tienda (y por tanto la utilidad) son
    // información financiera interna: en el resto del sistema los costos están
    // restringidos a ADMIN (ver /reports/suppliers, que además rechaza a TIENDA
    // con 403). Aquí TIENDA recibe únicamente su información operativa, así que
    // los costos se OMITEN del payload (no se envían en cero, que permitiría
    // inferirlos) y ni siquiera se consultan.
    // Allow-list, no deny-list: el rol viene de RoleModel.name, que es data-driven y
    // editable, así que "cualquier rol que no sea TIENDA" concedería costos a cualquier
    // rol futuro mal configurado. Solo ADMIN e INVENTARIOAcceden a información
    // financiera (los únicos tres roles que crea prisma/seed.ts).
    const puedeVerCostos = ROLES_CON_COSTOS.has(req.user?.role ?? "");

    const saleWhere: any = { saleDate: { gte: startDate, lte: endDate } };
    if (locationScope) saleWhere.locationId = locationScope;

    const returnWhere: any = { date: { gte: startDate, lte: endDate } };
    if (locationScope) returnWhere.sale = { locationId: locationScope };

    const [sales, returns, locations, costs] = await Promise.all([
      prisma.sale.findMany({
        where: saleWhere,
        include: {
          location: { select: { id: true, name: true } },
          items: { include: { product: { select: { id: true, name: true, brand: true } } } },
        },
      }),
      prisma.return.findMany({
        where: returnWhere,
        include: { sale: { select: { locationId: true, location: { select: { name: true } } } } },
      }),
      prisma.location.findMany({ select: { id: true, name: true, type: true }, ...(locationScope ? { where: { id: locationScope } } : {}) }),
      puedeVerCostos
        ? prisma.cost.findMany({
            where: { date: { gte: startDate, lte: endDate } },
            orderBy: { date: "desc" },
            select: { productId: true, costPrice: true },
          })
        : Promise.resolve([]),
    ]);

    // G7: para productos SIN factura en el mes se usa el último costo conocido
    // vigente al cierre del periodo. Sin este fallback, baseCost = 0 -> la
    // utilidad del mes aparecia inflada para todo producto no facturado en ese mes.
    // Se acota a los productos que realmente se vendieron en el periodo: sin este
    // filtro la consulta arrastraba TODO el historial de costos de la base.
    const productIdsVendidos = Array.from(new Set(sales.flatMap((s) => s.items.map((i) => i.productId))));
    const allCosts =
      puedeVerCostos && productIdsVendidos.length > 0
        ? await prisma.cost.findMany({
            where: { productId: { in: productIdsVendidos }, date: { lte: endDate } },
            orderBy: { date: "desc" },
            select: { productId: true, costPrice: true },
          })
        : [];

    // Costo más reciente por producto dentro del mes
    const costMap = new Map<number, number>();
    for (const c of costs) {
      if (!costMap.has(c.productId)) costMap.set(c.productId, Number(c.costPrice));
    }
    // Fallback: último costo conocido hasta el cierre del periodo.
    const lastKnownCost = new Map<number, number>();
    for (const c of allCosts) {
      if (!lastKnownCost.has(c.productId)) lastKnownCost.set(c.productId, Number(c.costPrice));
    }

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

      // G7: costo tienda = costo de la mercadería vendida + 10%
      let productsCost = 0;
      for (const key of Object.keys(productSales)) {
        const pid = Number(key);
        const baseCost = costMap.get(pid) ?? lastKnownCost.get(pid) ?? 0;
        productsCost += baseCost * productSales[key].quantity;
      }
      const storeCost = Number((productsCost * 1.1).toFixed(2));

      const reporte: any = {
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

      if (puedeVerCostos) {
        reporte.costs = {
          productsCost: Number(productsCost.toFixed(2)),
          storeCost,
        };
      }

      return reporte;
    });

    const totalGeneral = byLocation.reduce((sum, l) => sum + l.summary.totalSales, 0);
    const returnsGeneral = byLocation.reduce((sum, l) => sum + l.summary.totalReturns, 0);
    const totalProductsCost = byLocation.reduce((sum, l) => sum + (l.costs?.productsCost ?? 0), 0);
    const totalStoreCost = byLocation.reduce((sum, l) => sum + (l.costs?.storeCost ?? 0), 0);

    const resumen: any = {
      totalSales: totalGeneral,
      totalReturns: returnsGeneral,
      netSales: totalGeneral - returnsGeneral,
      totalLocations: locations.length,
      activeLocations: byLocation.filter((l) => l.summary.saleCount > 0).length,
    };

    if (puedeVerCostos) {
      resumen.costs = {
        totalProductsCost: Number(totalProductsCost.toFixed(2)),
        totalStoreCost: Number(totalStoreCost.toFixed(2)),
      };
    }

    res.json({
      period: { year: targetYear, month: targetMonth, startDate, endDate },
      locations: byLocation,
      summary: resumen,
    });
  } catch (error) {
    console.error("Error en reporte mensual:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
