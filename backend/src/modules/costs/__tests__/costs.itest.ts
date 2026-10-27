import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import * as XLSX from "xlsx";
import { seed, cleanup, createProduct, createSupplier, SeedContext } from "../../../testing/seed";
import { startTestServer, TestServer, loginAndGetToken, postJson } from "../../../testing/helpers";
let ctx: SeedContext;
let server: TestServer;
let token: string;
let supplierId: number;
before(async () => { ctx = await seed("costs"); server = await startTestServer(); token = await loginAndGetToken(server.baseUrl, ctx.users.admin.email, ctx.users.admin.password); supplierId = await createSupplier(ctx); });
after(async () => { await cleanup(ctx); await server.close(); });

test("costo calculado por servidor actualiza snapshot, ingreso y auditoría atómicos", async () => {
  const p = await createProduct(ctx, { stockAlmacen: 2 });
  const res = await postJson(server.baseUrl, "/api/costs", { productId: p.id, supplierId, costPrice: 1, unitCost: 5, exchangeRate: 7, percentage: 10, locationId: ctx.locationIds.almacen, quantity: 3 }, token);
  assert.equal(res.status, 201, await res.clone().text());
  assert.equal(Number((await res.json() as any).costPrice), 38.5);
  assert.equal(Number((await ctx.prisma.product.findUniqueOrThrow({ where: { id: p.id } })).cost), 38.5);
  const inv = await ctx.prisma.inventory.findUniqueOrThrow({ where: { productId_locationId: { productId: p.id, locationId: ctx.locationIds.almacen } } });
  assert.equal(inv.stock, 5);
  assert.equal(await ctx.prisma.auditLog.count({ where: { targetType: "INVENTORY", targetId: inv.id, action: "RECEIVE_PURCHASE" } }), 1);
});

test("costo contradictorio hace rollback sin cambiar inventario", async () => {
  const p = await createProduct(ctx, { stockAlmacen: 2 });
  const res = await postJson(server.baseUrl, "/api/costs", { productId: p.id, supplierId, costPrice: 200, locationId: ctx.locationIds.almacen, quantity: 3 }, token);
  assert.equal(res.status, 400);
  assert.equal(await ctx.prisma.cost.count({ where: { productId: p.id } }), 0);
  assert.equal(Number((await ctx.prisma.product.findUniqueOrThrow({ where: { id: p.id } })).cost), 50);
});

test("factura Excel almacenada en disco se lee, conserva historial y procesa cantidad", async () => {
  const p = await createProduct(ctx, { stockAlmacen: 1 });
  const book = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(book, XLSX.utils.json_to_sheet([{ Codigo: p.itemCode, Cantidad: 2, Precio: 5 }]), "Factura");
  const bytes = XLSX.write(book, { type: "buffer", bookType: "xlsx" });
  const form = new FormData();
  form.append("file", new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), "factura.xlsx");
  form.append("supplierId", String(supplierId)); form.append("exchangeRate", "7"); form.append("percentage", "10"); form.append("locationId", String(ctx.locationIds.almacen));
  const res = await fetch(`${server.baseUrl}/api/costs/import-invoice`, { method: "POST", headers: { authorization: `Bearer ${token}` }, body: form });
  assert.equal(res.status, 200, await res.clone().text());
  assert.equal((await res.json() as any).imported, 1);
  assert.equal((await ctx.prisma.inventory.findUniqueOrThrow({ where: { productId_locationId: { productId: p.id, locationId: ctx.locationIds.almacen } } })).stock, 3);
});
