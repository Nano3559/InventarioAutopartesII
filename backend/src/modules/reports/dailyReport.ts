import { Prisma, PrismaClient } from "@prisma/client";
import { AuthRequest } from "../../shared/types";
import { rangoFechasNegocio } from "../../shared/utils/rangoFechas";
import { alcanceDeFiltro, SIN_ALCANCE, puedeVerCostos } from "../../shared/utils/scope";
import { errorDominio } from "../../shared/utils/errorDominio";

export async function dailyReport(prisma: PrismaClient, req: AuthRequest) {
  const scope = alcanceDeFiltro(req.user);
  if (scope === SIN_ALCANCE) throw errorDominio("Usuario sin ubicación asignada");
  const locationId = scope ?? (req.query.locationId ? Number(req.query.locationId) : null);
  if (locationId !== null && (!Number.isInteger(locationId) || locationId < 1)) throw errorDominio("Ubicación inválida");
  const range = rangoFechasNegocio(req.query.startDate, req.query.endDate);
  const loc = locationId === null ? Prisma.sql`TRUE` : Prisma.sql`s."locationId" = ${locationId}`;
  const salesDates = Prisma.sql`${range.gte ? Prisma.sql`s."saleDate" >= (${range.gte}::timestamptz AT TIME ZONE 'UTC')` : Prisma.sql`TRUE`} AND ${range.lte ? Prisma.sql`s."saleDate" <= (${range.lte}::timestamptz AT TIME ZONE 'UTC')` : Prisma.sql`TRUE`}`;
  const returnDates = Prisma.sql`${range.gte ? Prisma.sql`r.date >= (${range.gte}::timestamptz AT TIME ZONE 'UTC')` : Prisma.sql`TRUE`} AND ${range.lte ? Prisma.sql`r.date <= (${range.lte}::timestamptz AT TIME ZONE 'UTC')` : Prisma.sql`TRUE`}`;
  const conditions: Prisma.Sql[] = [Prisma.sql`TRUE`];
  for (const [key, column] of [["brand", Prisma.sql`p.brand`], ["model", Prisma.sql`p.model`], ["product", Prisma.sql`p.name`]] as const) {
    if (typeof req.query[key] === "string" && req.query[key]) conditions.push(Prisma.sql`${column} ILIKE ${`%${req.query[key]}%`}`);
  }
  if (req.query.supplierId && puedeVerCostos(req.user)) {
    const supplierId = Number(req.query.supplierId);
    if (!Number.isInteger(supplierId) || supplierId < 1) throw errorDominio("Proveedor inválido");
    conditions.push(Prisma.sql`EXISTS (SELECT 1 FROM "Cost" c WHERE c."productId" = p.id AND c."supplierId" = ${supplierId})`);
  }
  const products = Prisma.join(conditions, " AND ");
  type Total = { date: string; locationId: number; locationName: string; total: Prisma.Decimal; saleCount: number };
  type Item = { date: string; locationId: number; productId: number; name: string; quantity: bigint; subtotal: Prisma.Decimal };
  type Returned = { date: string; locationId: number; locationName: string; amount: Prisma.Decimal };
  // La base agrega todas las filas del intervalo. No depende de una página de listados.
  const [totals, items, returns] = await prisma.$transaction([
    prisma.$queryRaw<Total[]>`SELECT to_char(s."saleDate" - interval '4 hours', 'YYYY-MM-DD') AS date, s."locationId", l.name AS "locationName", SUM(i.subtotal) AS total, COUNT(DISTINCT s.id)::int AS "saleCount"
      FROM "Sale" s JOIN "Location" l ON l.id = s."locationId" JOIN "SaleItem" i ON i."saleId" = s.id JOIN "Product" p ON p.id = i."productId"
      WHERE ${loc} AND ${salesDates} AND ${products}
      GROUP BY 1, 2, 3`,
    prisma.$queryRaw<Item[]>`SELECT to_char(s."saleDate" - interval '4 hours', 'YYYY-MM-DD') AS date, s."locationId", i."productId", p.name, SUM(i.quantity)::bigint AS quantity, SUM(i.subtotal) AS subtotal
      FROM "Sale" s JOIN "SaleItem" i ON i."saleId" = s.id JOIN "Product" p ON p.id = i."productId"
      WHERE ${loc} AND ${salesDates} AND ${products} GROUP BY 1, 2, 3, 4`,
    prisma.$queryRaw<Returned[]>`SELECT to_char(r.date - interval '4 hours', 'YYYY-MM-DD') AS date, s."locationId", l.name AS "locationName", SUM(r.amount) AS amount
      FROM "Return" r JOIN "Sale" s ON s.id = r."saleId" JOIN "Location" l ON l.id = s."locationId" JOIN "Product" p ON p.id = r."productId"
      WHERE ${loc} AND ${returnDates} AND ${products} GROUP BY 1, 2, 3`,
  ], { isolationLevel: "RepeatableRead" });
  type Store = { locationId: number; locationName: string; total: number; saleCount: number; returns: number; netSales: number; products: { productId: number; name: string; quantity: number; subtotal: number }[] };
  const days = new Map<string, { date: string; total: number; saleCount: number; stores: Store[] }>();
  const storeFor = (date: string, id: number, name: string) => {
    if (!days.has(date)) days.set(date, { date, total: 0, saleCount: 0, stores: [] });
    const group = days.get(date)!;
    let store = group.stores.find((s) => s.locationId === id);
    if (!store) { store = { locationId: id, locationName: name, total: 0, saleCount: 0, returns: 0, netSales: 0, products: [] }; group.stores.push(store); }
    return { group, store };
  };
  for (const t of totals) {
    const { group, store } = storeFor(t.date, t.locationId, t.locationName);
    store.total = Number(t.total); store.saleCount = t.saleCount;
    group.total += store.total; group.saleCount += store.saleCount;
  }
  for (const r of returns) storeFor(r.date, r.locationId, r.locationName).store.returns = Number(r.amount);
  for (const i of items) {
    const store = days.get(i.date)?.stores.find((s) => s.locationId === i.locationId);
    store?.products.push({ productId: i.productId, name: i.name, quantity: Number(i.quantity), subtotal: Number(i.subtotal) });
  }
  for (const d of days.values()) for (const s of d.stores) s.netSales = s.total - s.returns;
  return [...days.values()].sort((a, b) => b.date.localeCompare(a.date));
}
