import { test } from "node:test";
import assert from "node:assert/strict";
import type { Response } from "express";
import type { AuthRequest } from "../../shared/types";
import { dashboardFailure } from "./dashboardFailure";

process.env.JWT_SECRET = "dashboard-unit-test-only-secret";

test("periodos inválidos o futuros se rechazan antes de consultar", async () => {
  const {createDashboardHandler}=await import("./dashboard.routes");
  for (const month of ["2026-13","2026-02-31","9999-01",["2026-10"]]) {
    let status=200; const response:any={status(n:number){status=n;return this;},json(){return this;}};
    await createDashboardHandler({} as any)({query:{month},user:{role:"ADMIN"}} as any,response);
    assert.equal(status,400);
  }
});

test("TIENDA no puede escoger otra ubicación mediante query", async () => {
  const {createDashboardHandler}=await import("./dashboard.routes"); let status=200;
  await createDashboardHandler({} as any)({query:{locationId:"6"},user:{role:"TIENDA",locationId:5}} as any,{status(n:number){status=n;return this;},json(){return this;}} as any);
  assert.equal(status,403);
});

test("periodo histórico respeta UTC-4, confirmadas y ubicación", async () => {
  const {createDashboardHandler}=await import("./dashboard.routes"); const db=partialDatabase(); const ranges:any[]=[];
  db.sale={aggregate:async (q:any)=>{ranges.push(q);return {_count:0,_sum:{total:null}};},groupBy:async()=>[],findMany:async()=>[]}; db.saleItem={findMany:async()=>[]};
  let result:any; await createDashboardHandler(db)({query:{month:"2026-09"},user:{role:"TIENDA",locationId:5}} as any,{json(v:any){result=v;}} as any);
  assert.equal(result.period.month,"2026-09"); assert.equal(result.period.inventory,"CURRENT_NOT_HISTORICAL");
  assert.equal(ranges[1].where.saleDate.gte.toISOString(),"2026-09-01T04:00:00.000Z");
  assert.equal(ranges[1].where.saleDate.lte.toISOString(),"2026-10-01T03:59:59.999Z");
  assert.equal(ranges[1].where.locationId,5); assert.equal(ranges[1].where.status,"CONFIRMED");
});

test("clasifica conexión y esquema sin exponer SQL o credenciales", () => {
  assert.equal(dashboardFailure({ code: "P2022", message: "SQL sensible" }).code, "DASHBOARD_SCHEMA_UNAVAILABLE");
  assert.equal(dashboardFailure({ code: "P1001" }).status, 503);
  assert.equal(dashboardFailure(new Error("contraseña sensible")).status, 500);
  assert.ok(!JSON.stringify(dashboardFailure(new Error("contraseña sensible"))).includes("contraseña"));
});

test("dashboard consulta solo campos necesarios, filtra confirmadas y conserva alcance TIENDA", async () => {
  const calls: Record<string, any[]> = {};
  const prisma: any = { product: {}, inventory: {}, location: {}, sale: {}, saleItem: {}, movement: {}, productRequest: {} };
  const stub = (model: any, method: string, key: string, value: any) => { model[method] = async (args: any) => {
    (calls[key] ||= []).push(args);
    return value;
  }; };
  stub(prisma.product, "count", "count", 2);
  stub(prisma.product, "findMany", "products", []);
  stub(prisma.inventory, "findMany", "inventory", []);
  stub(prisma.inventory, "groupBy", "stock", []);
  stub(prisma.location, "findMany", "locations", []);
  stub(prisma.sale, "aggregate", "totals", { _count: 0, _sum: { total: null } });
  stub(prisma.sale, "groupBy", "salesByLocation", []);
  stub(prisma.sale, "findMany", "sales", []);
  stub(prisma.saleItem, "findMany", "items", []);
  stub(prisma.movement, "findMany", "movements", []);
  stub(prisma.productRequest, "findMany", "requests", []);
  stub(prisma.productRequest, "count", "requestCount", 14);
  let status = 200;
  let result: any;
  const res = { status(n: number) { status = n; return this; }, json(value: any) { result = value; return this; } } as Response;
  {
    const { createDashboardHandler } = await import("./dashboard.routes");
    const dashboardHandler = createDashboardHandler(prisma);
    await dashboardHandler({ user: { role: "TIENDA", locationId: 5 } } as AuthRequest, res);
    assert.equal(status, 200);
    assert.equal(result.summary.salesTodayTotal, 0);
    assert.equal(result.summary.pendingRequests, 14);
    assert.deepEqual(calls.count[0].where, { inventories: { some: { locationId: 5 } } });
    assert.deepEqual(calls.products[0].where, { inventories: { some: { locationId: 5 } } });
    assert.equal(calls.sales[0].where.status, "CONFIRMED");
    assert.equal(calls.sales[0].where.locationId, 5);
    assert.deepEqual(calls.sales[0].select.items, { select: { id: true } });
    assert.equal(calls.movements[0].select.receivedQuantity, undefined);
    assert.equal(calls.movements[0].select.id, true);
    assert.equal(calls.totals[0].where.saleDate.gte.toISOString().slice(11), "04:00:00.000Z");
    assert.deepEqual(calls.movements[0].where.OR, [{ fromLocationId: 5 }, { toLocationId: 5 }]);
  }
});

test("TIENDA sin ubicación falla antes de consultar incluso al llamar el handler directamente", async () => {
  const {createDashboardHandler}=await import("./dashboard.routes");
  let status=200;
  const res:any={status(n:number){status=n;return this;},json(){return this;}};
  await createDashboardHandler({} as any)({user:{role:"TIENDA",locationId:null}} as AuthRequest,res);
  assert.equal(status,403);
});

test("esquema incompatible produce 503 explícito sin devolver cifras comerciales inventadas", async () => {
  const { createDashboardHandler } = await import("./dashboard.routes");
  const database = { product: { count: async () => { throw Object.assign(new Error("SQL privado"), { code: "P2022" }); } } } as any;
  let status = 200;
  let value: any;
  const response = { status(n: number) { status = n; return this; }, json(data: any) { value = data; return this; } } as Response;
  await createDashboardHandler(database)({ user: { role: "ADMIN" } } as AuthRequest, response);
  assert.equal(status, 503);
  assert.equal(value.code, "DASHBOARD_SCHEMA_UNAVAILABLE");
  assert.equal(value.summary, undefined);
  assert.ok(!JSON.stringify(value).includes("SQL privado"));
});

function partialDatabase() {
  return {
    product: { count: async () => 12, findMany: async () => [] },
    inventory: { findMany: async () => [], groupBy: async () => [] },
    location: { findMany: async () => [] },
    movement: { findMany: async () => [] },
    productRequest: { count: async () => 4, findMany: async () => [] },
    sale: { aggregate: async () => { throw Object.assign(new Error("missing column"), { code: "P2022" }); } },
  } as any;
}

test("ventas incompatibles no bloquean inventario ni se convierten en ventas cero", async () => {
  const { createDashboardHandler } = await import("./dashboard.routes");
  let status = 200; let value: any;
  const response: any = { status(n: number) { status = n; return this; }, json(data: any) { value = data; return this; } };
  await createDashboardHandler(partialDatabase())({ user: { role: "ADMIN" } } as AuthRequest, response);
  assert.equal(status, 200);
  assert.equal(value.summary.totalProducts, 12);
  assert.equal(value.summary.pendingRequests, 4);
  for (const key of ["salesToday", "salesMonth", "salesTodayTotal", "salesMonthTotal"]) assert.equal(value.summary[key], null);
  assert.equal(value.availability.sales, "SCHEMA_UNAVAILABLE");
  assert.deepEqual(value.recentSales, []);
});

test("preflight evita consultar una columna ausente incluso dentro de una transacción", async () => {
  const { createDashboardHandler } = await import("./dashboard.routes");
  const db = partialDatabase(); let queried = false;
  db.$queryRaw = async () => [{ ready: false }];
  db.sale.aggregate = async () => { queried = true; throw new Error("should not query"); };
  let value: any;
  await createDashboardHandler(db)({ user: { role: "TIENDA", locationId: 5 } } as AuthRequest, { json(v: any) { value = v; } } as any);
  assert.equal(queried, false);
  assert.equal(value.summary.salesToday, null);
  assert.equal(value.summary.totalProducts, 12);
});

test("un fallo de conexión no se oculta como compatibilidad de ventas", async () => {
  const { createDashboardHandler } = await import("./dashboard.routes");
  const db = partialDatabase();
  db.sale.aggregate = async () => { throw Object.assign(new Error("private details"), { code: "P1001" }); };
  let status = 200; let value: any;
  await createDashboardHandler(db)({ user: { role: "ADMIN" } } as AuthRequest, { status(n: number) { status = n; return this; }, json(v: any) { value = v; } } as any);
  assert.equal(status, 503);
  assert.equal(value.code, "DASHBOARD_DATABASE_UNAVAILABLE");
  assert.equal(value.summary, undefined);
});
