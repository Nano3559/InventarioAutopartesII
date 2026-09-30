import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { startTestServer, TestServer, postJson, jsonHeaders, loginAndGetToken } from "../../../testing/helpers";
import { seed, cleanup, createProduct, createSupplier, SeedContext } from "../../../testing/seed";

/**
 * G7 / J4 / J6 — Reportes:
 *  - G7 el costo de mercadería de un producto SIN factura en el mes usa el último
 *    costo conocido (sin el fallback la utilidad del mes salía inflada).
 *  - J4 el listado de ventas del reporte diario acepta rango de fechas y topa el
 *    límite en 1000 (con el default de 100 los totales quedaban truncados).
 *  - J6 el listado de devoluciones acepta rango de fechas y topa el límite en 1000.
 */

let server: TestServer;
let ctx: SeedContext;
let token: string;
let tokenAdmin: string;
let supplierId: number;

const COSTO_MES_PASADO = 40;

before(async () => {
  ctx = await seed("reports");
  supplierId = await createSupplier(ctx);
  server = await startTestServer();
  token = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, ctx.users.tienda.password);
  tokenAdmin = await loginAndGetToken(server.baseUrl, ctx.users.admin.email, ctx.users.admin.password);
});

after(async () => {
  await cleanup(ctx);
  await server.close();
});

async function sell(productId: number, quantity: number): Promise<number> {
  const res = await postJson(
    server.baseUrl,
    "/api/sales",
    {
      items: [{ productId, quantity, unitPrice: 100 }],
      payments: [{ method: "EFECTIVO", amount: quantity * 100 }],
    },
    token
  );
  assert.equal(res.status, 201, `la venta previa falló: ${res.status}`);
  const body: any = await res.json();
  return body.id as number;
}

async function getJson(pathname: string, authToken = token): Promise<{ status: number; body: any }> {
  const res = await fetch(`${server.baseUrl}${pathname}`, { headers: jsonHeaders(authToken) });
  return { status: res.status, body: await res.json() };
}

/** Fecha ISO (YYYY-MM-DD) de hace `days` días, en hora local. */
function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

test("G7 — el costo mensual cae al último costo conocido si el producto no fue facturado en el mes", async () => {
  const p = await createProduct(ctx, { stockTienda: 10, unitPrice: 100 });
  const cantidad = 3;

  // Costo registrado el mes pasado: el reporte del mes en curso no lo encuentra
  // en su propio periodo, y sin fallback lo costo como 0.
  await ctx.prisma.cost.create({
    data: { productId: p.id, supplierId, costPrice: COSTO_MES_PASADO, date: new Date(new Date().getFullYear(), new Date().getMonth() - 1, 15) },
  });

  await sell(p.id, cantidad);

  const ahora = new Date();
  // Los costos son información financiera interna: esta aserción se hace como ADMIN.
  const { status, body } = await getJson(`/api/reports/monthly?year=${ahora.getFullYear()}&month=${ahora.getMonth() + 1}`, tokenAdmin);
  assert.equal(status, 200);

  const tienda = body.locations.find((l: any) => l.location.id === ctx.locationIds.tienda);
  assert.ok(tienda, "el reporte mensual debe incluir la tienda de prueba");
  assert.equal(tienda.summary.saleCount, 1);
  assert.equal(tienda.costs.productsCost, COSTO_MES_PASADO * cantidad);
  assert.ok(
    tienda.costs.productsCost > 0,
    "sin fallback el costo del mes sería 0 y la utilidad aparecería inflada"
  );
});

test("Aislamiento de costos — ADMIN recibe costos de mercadería y de tienda en el reporte mensual", async () => {
  const p = await createProduct(ctx, { stockTienda: 10, unitPrice: 100 });
  await ctx.prisma.cost.create({
    data: { productId: p.id, supplierId, costPrice: 50, date: new Date() },
  });
  await sell(p.id, 2);

  const ahora = new Date();
  const { status, body } = await getJson(`/api/reports/monthly?year=${ahora.getFullYear()}&month=${ahora.getMonth() + 1}`, tokenAdmin);
  assert.equal(status, 200);

  const tienda = body.locations.find((l: any) => l.location.id === ctx.locationIds.tienda);
  assert.ok(tienda);
  assert.ok(tienda.costs, "ADMIN debe recibir el bloque costs por tienda");
  assert.ok(tienda.costs.productsCost > 0, "ADMIN debe ver el costo de mercadería");
  assert.ok(tienda.costs.storeCost > 0, "ADMIN debe ver el costo de tienda");
  assert.ok(body.summary.costs, "ADMIN debe recibir costs en el resumen general");
  assert.ok(body.summary.costs.totalStoreCost > 0);
  assert.ok(
    body.summary.costs.totalStoreCost >= body.summary.costs.totalProductsCost,
    "el costo de tienda incluye el 10% de sobreprecio sobre la mercadería"
  );
});

test("Aislamiento de costos — TIENDA NO recibe costs ni datos derivados de costo en el reporte mensual", async () => {
  const p = await createProduct(ctx, { stockTienda: 10, unitPrice: 100 });
  await ctx.prisma.cost.create({
    data: { productId: p.id, supplierId, costPrice: 50, date: new Date() },
  });
  await sell(p.id, 2);

  const ahora = new Date();
  const { status, body } = await getJson(`/api/reports/monthly?year=${ahora.getFullYear()}&month=${ahora.getMonth() + 1}`);
  assert.equal(status, 200);

  const tienda = body.locations.find((l: any) => l.location.id === ctx.locationIds.tienda);
  assert.ok(tienda, "TIENDA sigue viendo su propia tienda");
  assert.ok(tienda.summary.saleCount >= 1, "TIENDA conserva su información operativa de ventas");
  assert.equal(tienda.costs, undefined, "TIENDA no debe recibir el bloque costs por tienda");
  assert.equal(body.summary.costs, undefined, "TIENDA no debe recibir costs en el resumen general");

  // El payload completo no debe filtrar ningún costo/utilidad/margen por otro camino.
  const serializado = JSON.stringify(body);
  for (const prohibido of ["productsCost", "storeCost", "totalProductsCost", "totalStoreCost", "costo", "utilidad"]) {
    assert.equal(
      serializado.toLowerCase().includes(prohibido.toLowerCase()),
      false,
      `la respuesta de TIENDA no debe contener "${prohibido}"`
    );
  }
});

test("Aislamiento de costos — TIENDA mantiene su alcance de ubicación y no ve otras tiendas", async () => {
  const { body } = await getJson(
    `/api/reports/monthly?year=${new Date().getFullYear()}&month=${new Date().getMonth() + 1}`
  );
  assert.equal(body.locations.length, 1, "TIENDA solo debe recibir su propia ubicación");
  assert.equal(body.locations[0].location.id, ctx.locationIds.tienda);
});

test("J4 — el listado de ventas filtra por rango de fechas y topa el límite en 1000", async () => {
  const p = await createProduct(ctx, { stockTienda: 20, unitPrice: 100 });

  const reciente = await sell(p.id, 1);
  const antigua = await sell(p.id, 1);

  // Se retrodatea una venta fuera del periodo consultado.
  await ctx.prisma.sale.update({
    where: { id: antigua },
    data: { saleDate: new Date(`${isoDaysAgo(45)}T12:00:00`) },
  });

  const enRango = await getJson(`/api/sales?startDate=${isoDaysAgo(3)}&endDate=${isoDaysAgo(0)}&limit=1000`);
  assert.equal(enRango.status, 200);
  const ids = enRango.body.sales.map((s: any) => s.id);
  assert.ok(
    ids.includes(reciente),
    `la venta actual debe entrar en el rango (reciente=${reciente} antigua=${antigua} iso=${isoDaysAgo(3)}..${isoDaysAgo(
      0
    )} ids=${JSON.stringify(ids)})`
  );
  assert.ok(!ids.includes(antigua), "la venta de hace 45 días no debe entrar en un rango de 3 días");
  assert.equal(enRango.body.pagination.limit, 1000);

  // Tope de seguridad: un limit absurdo se acota (no se abre la paginación).
  const capado = await getJson(`/api/sales?limit=5000`);
  assert.equal(capado.status, 200);
  assert.equal(capado.body.pagination.limit, 1000);
});

test("J6 — el listado de devoluciones filtra por rango de fechas y topa el límite en 1000", async () => {
  const p = await createProduct(ctx, { stockTienda: 10, unitPrice: 100 });
  const saleId = await sell(p.id, 4);

  const res = await postJson(
    server.baseUrl,
    "/api/returns",
    { saleId, productId: p.id, reason: "Garantía", quantity: 1, amount: 100, method: "EFECTIVO" },
    token
  );
  assert.equal(res.status, 201);
  const creada: any = await res.json();

  // Se fecha la devolución fuera del periodo consultado.
  await ctx.prisma.return.update({
    where: { id: creada.id },
    data: { date: new Date(`${isoDaysAgo(30)}T12:00:00`) },
  });

  const enRango = await getJson(`/api/returns?startDate=${isoDaysAgo(2)}&endDate=${isoDaysAgo(0)}&limit=1000`);
  assert.equal(enRango.status, 200);
  const ids = enRango.body.returns.map((r: any) => r.id);
  assert.ok(!ids.includes(creada.id), "una devolución de hace 30 días no debe entrar en un rango de 2 días");

  const historico = await getJson(`/api/returns?startDate=${isoDaysAgo(60)}&endDate=${isoDaysAgo(0)}&limit=1000`);
  assert.ok(
    historico.body.returns.some((r: any) => r.id === creada.id),
    "con un rango amplio la devolución sí debe aparecer"
  );
  assert.equal(historico.body.pagination.limit, 1000);

  const capado = await getJson(`/api/returns?limit=5000`);
  assert.equal(capado.body.pagination.limit, 1000);
});

test("un limit decimal no rompe el reporte con 500", async () => {
  // `?limit=2.7` solía llegarle 2.7 a Prisma, que exige enteros -> 500.
  for (const path of ["/api/reports/sales?limit=2.7", "/api/sales?limit=2.7", "/api/returns?limit=2.7"]) {
    const res = await getJson(path);
    assert.equal(res.status, 200, `${path} debe responder 200`);
    assert.equal(res.body.pagination.limit, 2, `${path} debe truncar a entero`);
  }
});

test("el reporte mensual valida year/month en vez de construir una fecha inválida", async () => {
  const year = new Date().getFullYear();
  const invalidos = [
    `/api/reports/monthly?year=abc`,
    `/api/reports/monthly?year=2026&month=13`,
    `/api/reports/monthly?year=2026&month=0`,
    `/api/reports/monthly?year=2026&month=abc`,
  ];
  for (const path of invalidos) {
    const res = await getJson(path);
    assert.equal(res.status, 400, `${path} debe rechazarse con 400`);
  }

  // El contrato real del frontend (year + month suelto) debe seguir funcionando.
  const ok = await getJson(`/api/reports/monthly?year=${year}&month=${new Date().getMonth() + 1}`);
  assert.equal(ok.status, 200);
  assert.equal(ok.body.period.year, year);
  assert.equal(ok.body.period.month, new Date().getMonth() + 1);
});

test("el listado de ventas combina month con startDate/endDate sin ampliar el rango", async () => {
  const p = await createProduct(ctx, { stockTienda: 20, unitPrice: 100 });
  const venta = await sell(p.id, 1);

  // La venta es de HOY; un month antiguo + un rango que empieza mañana no debe verla.
  const futuro = new Date();
  futuro.setDate(futuro.getDate() + 1);
  const mesAntiguo = `${futuro.getFullYear()}-${String(futuro.getMonth() + 1).padStart(2, "0")}`;
  const manana = `${futuro.getFullYear()}-${String(futuro.getMonth() + 1).padStart(2, "0")}-${String(
    futuro.getDate()
  ).padStart(2, "0")}`;

  const res = await getJson(`/api/reports/sales?month=${mesAntiguo}&startDate=${manana}&endDate=${manana}`);
  assert.equal(res.status, 200);
  const ids = res.body.sales.map((s: any) => s.id);
  assert.ok(!ids.includes(venta), "combinar month con un rango posterior no debe ampliar el reporte");
});
