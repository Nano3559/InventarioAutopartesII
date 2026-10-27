import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { startTestServer, TestServer, postJson, loginAndGetToken, jsonHeaders } from "../../../testing/helpers";
import { seed, cleanup, createProduct, SeedContext } from "../../../testing/seed";

let ctx: SeedContext;
let server: TestServer;
let admin: string;
let tienda: string;
before(async () => {
  ctx = await seed("preh4");
  server = await startTestServer();
  admin = await loginAndGetToken(server.baseUrl, ctx.users.admin.email, ctx.users.admin.password);
  tienda = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, ctx.users.tienda.password);
});
after(async () => { await cleanup(ctx); await server.close(); });

test("POR MENOR y POR MAYOR usan catálogo, ubicación correcta y pagos combinados", async () => {
  const p = await createProduct(ctx, { price1: 100, price2: 150, stockTienda: 10, stockAlmacen: 20 });
  for (const [priceMode, expected] of [["POR_MENOR", 100], ["POR_MAYOR", 80]] as const) {
    const res = await postJson(server.baseUrl, "/api/sales", {
      items: [{ productId: p.id, quantity: 2, priceMode, unitPrice: 0.01 }],
      payments: [{ method: "EFECTIVO", amount: expected }, { method: "QR", amount: expected }],
    }, tienda);
    assert.equal(res.status, 201, await res.clone().text());
    const sale = await res.json() as any;
    assert.equal(Number(sale.total), expected * 2);
    assert.equal(Number(sale.items[0].unitPrice), expected);
  }
  const inventories = await ctx.prisma.inventory.findMany({ where: { productId: p.id } });
  assert.equal(inventories.find((i) => i.locationId === ctx.locationIds.tienda)?.stock, 6);
  assert.equal(inventories.find((i) => i.locationId === ctx.locationIds.almacen)?.stock, 20);
});

test("ADMIN elige origen explícito, normal no sale de almacén y TIENDA no cambia ubicación", async () => {
  const p = await createProduct(ctx, { stockTienda: 10, stockAlmacen: 10 });
  const payload = { items: [{ productId: p.id, quantity: 1, priceTier: "PRICE1" }], payments: [{ method: "QR", amount: 100 }] };
  assert.equal((await postJson(server.baseUrl, "/api/sales", payload, admin)).status, 400);
  assert.equal((await postJson(server.baseUrl, "/api/sales", { ...payload, locationId: ctx.locationIds.almacen }, admin)).status, 400);
  assert.equal((await postJson(server.baseUrl, "/api/sales", { ...payload, locationId: ctx.locationIds.almacen }, tienda)).status, 403);
  const before = await ctx.prisma.sale.count({ where: { userId: ctx.users.admin.userId } });
  assert.equal((await postJson(server.baseUrl, "/api/wholesale", { ...payload, locationId: ctx.locationIds.almacen, payments: [{ method: "QR", amount: 80 }] }, admin)).status, 201);
  assert.equal(await ctx.prisma.sale.count({ where: { userId: ctx.users.admin.userId } }), before + 1);
});

test("edición rechaza mayorista superior a niveles normales y precio inferior al costo", async () => {
  const p = await createProduct(ctx);
  for (const change of [{ wholesalePrice: 101 }, { price1: 49 }, { cost: 101 }]) {
    const res = await fetch(`${server.baseUrl}/api/products/${p.id}`, { method: "PUT", headers: jsonHeaders(admin), body: JSON.stringify(change) });
    assert.equal(res.status, 400, await res.clone().text());
  }
  const current = await ctx.prisma.product.findUniqueOrThrow({ where: { id: p.id } });
  assert.equal(Number(current.price1), 100);
  assert.equal(Number(current.wholesalePrice), 80);
});

test("crédito inicial no cuenta como cobro y admite cobrar el saldo después", async () => {
  const p = await createProduct(ctx, { stockTienda: 4 });
  const res = await postJson(server.baseUrl, "/api/sales", { items: [{ productId: p.id, quantity: 1, priceTier: "PRICE1" }], payments: [{ method: "EFECTIVO", amount: 30 }, { method: "CREDITO", amount: 70 }] }, tienda);
  assert.equal(res.status, 201);
  const sale = await res.json() as any;
  const summary = await (await fetch(`${server.baseUrl}/api/payments/summary/${sale.id}`, { headers: jsonHeaders(tienda) })).json() as any;
  assert.equal(summary.totalPaid, 30);
  assert.equal(summary.pending, 70);
  assert.equal((await postJson(server.baseUrl, "/api/payments", { saleId: sale.id, method: "QR", amount: 70 }, tienda)).status, 201);
  assert.equal((await postJson(server.baseUrl, "/api/payments", { saleId: sale.id, method: "QR", amount: 1 }, tienda)).status, 400);
});

test("pago distinto del total produce rollback de cabecera, detalles y stock", async () => {
  const p = await createProduct(ctx, { stockTienda: 4 });
  const res = await postJson(server.baseUrl, "/api/sales", { items: [{ productId: p.id, quantity: 1, priceMode: "POR_MAYOR" }], payments: [{ method: "QR", amount: 1 }] }, tienda);
  assert.equal(res.status, 400);
  assert.equal(await ctx.prisma.saleItem.count({ where: { productId: p.id } }), 0);
  assert.equal((await ctx.prisma.inventory.findUniqueOrThrow({ where: { productId_locationId: { productId: p.id, locationId: ctx.locationIds.tienda } } })).stock, 4);
});

test("ajuste y auditoría son atómicos, un stock leído antes de una venta queda obsoleto", async () => {
  const p = await createProduct(ctx, { stockTienda: 5 });
  const inv = await ctx.prisma.inventory.findUniqueOrThrow({ where: { productId_locationId: { productId: p.id, locationId: ctx.locationIds.tienda } } });
  await postJson(server.baseUrl, "/api/sales", { items: [{ productId: p.id, quantity: 1 }], payments: [{ method: "QR", amount: 100 }] }, tienda);
  const put = (expectedStock: number) => fetch(`${server.baseUrl}/api/inventory/${inv.id}`, { method: "PUT", headers: jsonHeaders(admin), body: JSON.stringify({ stock: 8, expectedStock, reasonType: "AJUSTE" }) });
  assert.equal((await put(5)).status, 409);
  assert.equal((await ctx.prisma.inventory.findUniqueOrThrow({ where: { id: inv.id } })).stock, 4);
  assert.equal((await put(4)).status, 200);
  const log = await ctx.prisma.auditLog.findFirstOrThrow({ where: { targetType: "INVENTORY", targetId: inv.id } });
  assert.equal((log.oldValue as any).stock, 4);
  assert.equal((log.newValue as any).stock, 8);
});

test("retirar el permiso ventas también bloquea la API con token todavía válido", async () => {
  const { invalidateRoleCache } = await import("../../../shared/middlewares/auth");
  const role = await ctx.prisma.roleModel.findUniqueOrThrow({ where: { id: ctx.roleIds.tienda } });
  try {
    await ctx.prisma.roleModel.update({ where: { id: role.id }, data: { permissions: role.permissions.filter((p) => p !== "ventas") } });
    invalidateRoleCache(role.id);
    const response = await fetch(`${server.baseUrl}/api/sales`, { headers: jsonHeaders(tienda) });
    assert.equal(response.status, 403);
  } finally {
    await ctx.prisma.roleModel.update({ where: { id: role.id }, data: { permissions: role.permissions } });
    invalidateRoleCache(role.id);
  }
});

test("dos ventas del mismo NIT reutilizan un solo cliente", async () => {
  const p = await createProduct(ctx, { stockTienda: 8 });
  const nit = `PREH4-${Date.now()}`;
  const payload = { items: [{ productId: p.id, quantity: 1, priceTier: "PRICE1" }], payments: [{ method: "QR", amount: 100 }], customerData: { name: "Cliente preh4 concurrente", nit } };
  const results = await Promise.all([postJson(server.baseUrl, "/api/sales", payload, tienda), postJson(server.baseUrl, "/api/sales", payload, tienda)]);
  assert.deepEqual(results.map((r) => r.status), [201, 201]);
  assert.equal(await ctx.prisma.customer.count({ where: { nit } }), 1);
  const ids = (await Promise.all(results.map((r) => r.json())) as any[]).map((s) => s.customerId);
  assert.equal(ids[0], ids[1]);
});
test("nota imprime texto escapado y saldo de crédito sin tratarlo como cobrado", async () => {
  const p = await createProduct(ctx, { stockTienda: 3 });
  const res = await postJson(server.baseUrl, "/api/sales", { items: [{ productId: p.id, quantity: 1 }], payments: [{ method: "CREDITO", amount: 100 }], paraQuien: '<script>alert("test")</script>' }, tienda);
  assert.equal(res.status, 201);
  const sale = await res.json() as any;
  const note = await fetch(`${server.baseUrl}/api/sales/${sale.id}/nota`, { headers: jsonHeaders(tienda) });
  const html = await note.text();
  // Delivery text is displayed for wholesale notes, so verify a displayed product too.
  await ctx.prisma.product.update({ where: { id: p.id }, data: { name: "<script>unsafe</script>" } });
  const refreshed = await (await fetch(`${server.baseUrl}/api/sales/${sale.id}/nota`, { headers: jsonHeaders(tienda) })).text();
  assert.ok(!refreshed.includes("<script>unsafe</script>"));
  assert.ok(refreshed.includes("&lt;script&gt;unsafe&lt;/script&gt;"));
  assert.ok(html.includes("Pendiente:"));
});
