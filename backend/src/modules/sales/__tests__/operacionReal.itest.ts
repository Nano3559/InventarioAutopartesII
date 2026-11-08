import { before, after, test } from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "crypto";
import { seed, cleanup, createProduct, type SeedContext } from "../../../testing/seed";
import { startTestServer, postJson, loginAndGetToken, jsonHeaders, type TestServer } from "../../../testing/helpers";

let ctx: SeedContext, server: TestServer, admin: string, tienda: string;
before(async () => {
  ctx = await seed("operacion-real"); server = await startTestServer();
  admin = await loginAndGetToken(server.baseUrl, ctx.users.admin.email, ctx.users.admin.password);
  tienda = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, ctx.users.tienda.password);
});
after(async () => { await cleanup(ctx); await server.close(); });
const stock = async (productId: number, locationId: number) => (await ctx.prisma.inventory.findUniqueOrThrow({ where: { productId_locationId: { productId, locationId } } })).stock;
const put = (path: string, body: unknown, token = admin) => fetch(server.baseUrl + path, { method: "PUT", headers: jsonHeaders(token), body: JSON.stringify(body) });

test("venta con identidad conserva resultado y stock al reintentar simultáneamente", async () => {
  const p = await createProduct(ctx, { stockTienda: 20 });
  const body = { operationId: randomUUID(), items: [{ productId: p.id, quantity: 2 }], payments: [{ method: "EFECTIVO", amount: p.unitPrice * 2 }] };
  const responses = await Promise.all([postJson(server.baseUrl, "/api/sales", body, tienda), postJson(server.baseUrl, "/api/sales", body, tienda)]);
  assert.deepEqual(responses.map(r => r.status), [201, 201]);
  const [a, b]: any[] = await Promise.all(responses.map(r => r.json()));
  assert.equal(a.id, b.id); assert.equal(await stock(p.id, ctx.locationIds.tienda), 18);
  const conflict = await postJson(server.baseUrl, "/api/sales", { ...body, items: [{ productId: p.id, quantity: 1 }] }, tienda);
  assert.equal(conflict.status, 400); assert.equal(await stock(p.id, ctx.locationIds.tienda), 18);
});

test("abono repetido no cobra dos veces aunque quede saldo", async () => {
  const p = await createProduct(ctx, { unitPrice: 100, stockTienda: 10 });
  const sale: any = await (await postJson(server.baseUrl, "/api/sales", { items: [{ productId: p.id, quantity: 1 }], payments: [{ method: "CREDITO", amount: 100 }], customerData: { name: "Cliente identificado de prueba" } }, tienda)).json();
  const body = { operationId: randomUUID(), saleId: sale.id, method: "EFECTIVO", amount: 20 };
  const [a, b] = await Promise.all([postJson(server.baseUrl, "/api/payments", body, tienda), postJson(server.baseUrl, "/api/payments", body, tienda)]);
  assert.equal(a.status, 201); assert.equal(b.status, 201);
  assert.equal((await a.json() as { id: number }).id, (await b.json() as { id: number }).id);
  const summary: any = await (await fetch(`${server.baseUrl}/api/payments/summary/${sale.id}`, { headers: jsonHeaders(tienda) })).json();
  assert.equal(summary.totalPaid, 20); assert.equal(summary.pending, 80);
});

test("traslado descuenta origen y solo ingresa al confirmar recepción", async () => {
  const p = await createProduct(ctx, { stockAlmacen: 20, stockTienda: 1 });
  const response = await postJson(server.baseUrl, "/api/movements", { operationId: randomUUID(), productId: p.id, fromLocationId: ctx.locationIds.almacen, toLocationId: ctx.locationIds.tienda, quantity: 4 }, admin);
  assert.equal(response.status, 201); const movement: any = await response.json();
  assert.equal(movement.status, "IN_TRANSIT");
  assert.equal(await stock(p.id, ctx.locationIds.almacen), 16);
  assert.equal(await stock(p.id, ctx.locationIds.tienda), 1);
  const body = { operationId: randomUUID(), quantity: 2 };
  for (let i = 0; i < 2; i++) assert.equal((await postJson(server.baseUrl, `/api/movements/${movement.id}/receive`, body, tienda)).status, 200);
  assert.equal(await stock(p.id, ctx.locationIds.tienda), 3);
  assert.equal((await postJson(server.baseUrl, `/api/movements/${movement.id}/receive`, {}, tienda)).status, 200);
  assert.equal(await stock(p.id, ctx.locationIds.tienda), 5);
  assert.equal((await postJson(server.baseUrl, `/api/movements/${movement.id}/receive`, {}, tienda)).status, 200);
  assert.equal(await stock(p.id, ctx.locationIds.tienda), 5);
});

test("devolución reduce deuda primero y requiere inspección para reintegrar stock", async () => {
  const p = await createProduct(ctx, { unitPrice: 10, stockTienda: 20 });
  await ctx.prisma.product.update({ where: { id: p.id }, data: { cost: 5 } });
  const saleResponse = await postJson(server.baseUrl, "/api/sales", { items: [{ productId: p.id, quantity: 10 }], payments: [{ method: "EFECTIVO", amount: 40 }, { method: "CREDITO", amount: 60 }], customerData: { name: "Cliente parcial" } }, tienda);
  assert.equal(saleResponse.status, 201); const sale: any = await saleResponse.json();
  const first = await postJson(server.baseUrl, "/api/returns", { operationId: randomUUID(), saleId: sale.id, productId: p.id, quantity: 2, amount: 20, method: "EFECTIVO", reason: "Inspección pendiente" }, tienda);
  assert.equal(first.status, 201); const ret: any = await first.json();
  assert.equal(Number(ret.debtReduction), 20); assert.equal(Number(ret.refundAmount), 0);
  assert.equal(await stock(p.id, ctx.locationIds.tienda), 10);
  const inspect = { operationId: randomUUID(), quantity: 1, outcome: "SELLABLE", reason: "Revisada físicamente" };
  assert.equal((await postJson(server.baseUrl, `/api/returns/inspection/${ret.id}`, inspect, tienda)).status, 403);
  for (let i = 0; i < 2; i++) assert.equal((await postJson(server.baseUrl, `/api/returns/inspection/${ret.id}`, inspect, admin)).status, 200);
  assert.equal(await stock(p.id, ctx.locationIds.tienda), 11);
  assert.equal((await postJson(server.baseUrl, `/api/returns/inspection/${ret.id}`, { ...inspect, operationId: randomUUID(), outcome: "NOT_SELLABLE" }, admin)).status, 200);
  assert.equal(await stock(p.id, ctx.locationIds.tienda), 11);
  const second = await postJson(server.baseUrl, "/api/returns", { saleId: sale.id, productId: p.id, quantity: 5, amount: 50, method: "EFECTIVO", reason: "Más piezas devueltas" }, tienda);
  assert.equal(second.status, 201); const secondRet: any = await second.json();
  assert.equal(Number(secondRet.debtReduction), 40); assert.equal(Number(secondRet.refundAmount), 10);
  const summary: any = await (await fetch(`${server.baseUrl}/api/payments/summary/${sale.id}`, { headers: jsonHeaders(tienda) })).json();
  assert.equal(summary.pending, 0); assert.equal(summary.netCollected, 30);
});

test("el rol actual prevalece sobre un token ADMIN anterior", async () => {
  const user = ctx.users.inventario;
  await ctx.prisma.user.update({ where: { id: user.userId }, data: { roleId: ctx.roleIds.admin } });
  const token = await loginAndGetToken(server.baseUrl, user.email, user.password);
  await ctx.prisma.user.update({ where: { id: user.userId }, data: { roleId: ctx.roleIds.inventario } });
  assert.equal((await fetch(`${server.baseUrl}/api/users`, { headers: jsonHeaders(token) })).status, 403);
});

test("cambio de contraseña revoca tokens previos y logout revoca un token", async () => {
  const user = ctx.users.inventario;
  const token = await loginAndGetToken(server.baseUrl, user.email, user.password);
  assert.equal((await put(`/api/users/${user.userId}`, { password: "OtraClaveLocal123!" })).status, 200);
  assert.equal((await fetch(`${server.baseUrl}/api/auth/me`, { headers: jsonHeaders(token) })).status, 401);
  const fresh = await loginAndGetToken(server.baseUrl, user.email, "OtraClaveLocal123!");
  assert.equal((await postJson(server.baseUrl, "/api/auth/logout", {}, fresh)).status, 204);
  assert.equal((await fetch(`${server.baseUrl}/api/auth/me`, { headers: jsonHeaders(fresh) })).status, 401);
});

test("dos inspecciones simultáneas no habilitan más unidades que las devueltas", async () => {
  const p = await createProduct(ctx, { stockTienda: 2 });
  const sale: any = await (await postJson(server.baseUrl, "/api/sales", { items: [{ productId: p.id, quantity: 1 }], payments: [{ method: "EFECTIVO", amount: 100 }] }, tienda)).json();
  const ret: any = await (await postJson(server.baseUrl, "/api/returns", { saleId: sale.id, productId: p.id, quantity: 1, amount: 100, method: "EFECTIVO", reason: "Pieza revisada" }, tienda)).json();
  const responses = await Promise.all([1, 2].map(() => postJson(server.baseUrl, `/api/returns/inspection/${ret.id}`, { operationId: randomUUID(), quantity: 1, outcome: "SELLABLE", reason: "Inspección concurrente" }, admin)));
  assert.deepEqual(responses.map(r => r.status).sort(), [200, 400]);
  assert.equal(await stock(p.id, ctx.locationIds.tienda), 2);
});

test("una tienda recupera su recepción confirmada con la misma identidad", async () => {
  const p = await createProduct(ctx, { stockAlmacen: 3, stockTienda: 0 });
  const movement: any = await (await postJson(server.baseUrl, "/api/movements", { operationId: randomUUID(), productId: p.id, fromLocationId: ctx.locationIds.almacen, toLocationId: ctx.locationIds.tienda, quantity: 2 }, admin)).json();
  const operationId = randomUUID();
  assert.equal((await postJson(server.baseUrl, `/api/movements/${movement.id}/receive`, { operationId, quantity: 1 }, tienda)).status, 200);
  const recovered = await fetch(`${server.baseUrl}/api/operations/RECEIVE_MOVEMENT/${operationId}`, { headers: jsonHeaders(tienda) });
  assert.equal(recovered.status, 200);
  assert.equal((await recovered.json() as any).result.receivedQuantity, 1);
  assert.equal(await stock(p.id, ctx.locationIds.tienda), 1);
});

test("cambio de tienda mediante API invalida la sesión anterior", async () => {
  assert.equal((await put(`/api/users/${ctx.users.tienda.userId}`, { locationId: ctx.locationIds.almacen })).status, 200);
  assert.equal((await fetch(`${server.baseUrl}/api/auth/me`, { headers: jsonHeaders(tienda) })).status, 401);
});
