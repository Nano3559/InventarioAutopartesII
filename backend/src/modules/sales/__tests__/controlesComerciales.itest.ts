import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { randomUUID } from "crypto";
import * as XLSX from "xlsx";
import { seed, cleanup, createProduct, createSupplier, type SeedContext } from "../../../testing/seed";
import { startTestServer, loginAndGetToken, postJson, jsonHeaders, type TestServer } from "../../../testing/helpers";
import { fechaNegocio } from "../../../shared/utils/rangoFechas";
let ctx: SeedContext, server: TestServer, admin: string, tienda: string, accountId: number, supplierId: number;
before(async () => {
  ctx = await seed("comercial"); server = await startTestServer();
  admin = await loginAndGetToken(server.baseUrl, ctx.users.admin.email, ctx.users.admin.password);
  tienda = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, ctx.users.tienda.password);
  supplierId = await createSupplier(ctx);
  const response = await postJson(server.baseUrl, "/api/payments/receiving-accounts", { code: "TEST_COMERCIAL_BANK", name: "Banco ficticio" }, admin);
  assert.equal(response.status, 201); accountId = (await response.json() as any).id;
});
after(async () => { if (ctx) await cleanup(ctx); if (server) await server.close(); });
const stock = async (id: number, loc = ctx.locationIds.tienda) => (await ctx.prisma.inventory.findUniqueOrThrow({ where: { productId_locationId: { productId: id, locationId: loc } } })).stock;
const evidence = () => ({ receivingAccountId: accountId, reference: randomUUID(), operationDate: fechaNegocio(), confirmed: true });
const saleBody = (id: number, payment: any) => ({ operationId: randomUUID(), items: [{ productId: id, quantity: 1 }], payments: [payment] });

test("QR y transferencia sin verificación no registran venta ni descuentan stock", async () => {
  const p = await createProduct(ctx, { stockTienda: 4 });
  for (const method of ["QR", "TRANSFERENCIA"]) {
    const response = await postJson(server.baseUrl, "/api/sales", saleBody(p.id, { method, amount: 100 }), tienda);
    assert.equal(response.status, 400); assert.equal(await stock(p.id), 4);
  }
  assert.equal((await postJson(server.baseUrl, "/api/payments/receiving-accounts", { code: "TEST_COMERCIAL_NO", name: "No autorizada" }, tienda)).status, 403);
});

test("verificación manual conserva responsable y el mismo intento no registra otro cobro", async () => {
  const p = await createProduct(ctx, { stockTienda: 4 });
  const proof = evidence();
  const body = saleBody(p.id, { method: "QR", amount: 100, bankVerification: proof });
  const a = await postJson(server.baseUrl, "/api/sales", body, tienda);
  const b = await postJson(server.baseUrl, "/api/sales", body, tienda);
  assert.equal(a.status, 201); assert.equal(b.status, 201);
  const first: any = await a.json(), second: any = await b.json();
  assert.equal(first.id, second.id); assert.equal(await stock(p.id), 3);
  assert.equal(first.payments[0].verifiedById, ctx.users.tienda.userId);
  assert.ok(first.payments[0].verifiedAt);
  assert.equal(await ctx.prisma.auditLog.count({ where: { action: "CONFIRM_BANK_RECEIPT", userId: ctx.users.tienda.userId,
    newValue: { path: ["reference"], equals: proof.reference.toUpperCase() } } }), 1);
  const duplicate = await postJson(server.baseUrl, "/api/sales", saleBody(p.id, { method: "TRANSFERENCIA", amount: 100, bankVerification: proof }), tienda);
  assert.ok([400, 409].includes(duplicate.status)); assert.equal(await stock(p.id), 3);
});

test("dos ventas simultáneas no pueden usar el mismo abono bancario", async () => {
  const a = await createProduct(ctx, { stockTienda: 2 }), b = await createProduct(ctx, { stockTienda: 2 });
  const proof = evidence();
  const responses = await Promise.all([a, b].map(p => postJson(server.baseUrl, "/api/sales", saleBody(p.id, { method: "TRANSFERENCIA", amount: 100, bankVerification: proof }), tienda)));
  assert.equal(responses.filter(r => r.status === 201).length, 1);
  assert.ok(responses.every(r => [201, 400, 409].includes(r.status)));
  assert.equal(await stock(a.id) + await stock(b.id), 3);
  assert.equal(await ctx.prisma.payment.count({ where: { receivingAccountId: accountId, bankReference: proof.reference.toUpperCase() } }), 1);
});

test("fecha, confirmación y cuenta bancaria inválidas se rechazan sin cobro", async () => {
  const p = await createProduct(ctx, { stockTienda: 5 });
  for (const patch of [{ confirmed: false }, { operationDate: "" }, { operationDate: "2026-02-30" }, { operationDate: "2999-01-01" }, { receivingAccountId: -1 }]) {
    assert.equal((await postJson(server.baseUrl, "/api/sales", saleBody(p.id, { method: "QR", amount: 100, bankVerification: { ...evidence(), ...patch } }), tienda)).status, 400);
  }
  assert.equal(await stock(p.id), 5);
});

test("abonos exigen verificación y la referencia tampoco puede reutilizarse en mayorista", async () => {
  const p = await createProduct(ctx, { stockTienda: 4 });
  const sale: any = await (await postJson(server.baseUrl, "/api/sales", { ...saleBody(p.id, { method: "CREDITO", amount: 100 }), customerData: { name: "Cliente comercial de abono" } }, tienda)).json();
  const body = { operationId: randomUUID(), saleId: sale.id, method: "QR", amount: 20 };
  assert.equal((await postJson(server.baseUrl, "/api/payments", body, tienda)).status, 400);
  const proof = evidence();
  const first = await postJson(server.baseUrl, "/api/payments", { ...body, bankVerification: proof }, tienda);
  const retry = await postJson(server.baseUrl, "/api/payments", { ...body, bankVerification: proof }, tienda);
  assert.equal(first.status, 201); assert.equal(retry.status, 201);
  assert.equal((await first.json() as any).id, (await retry.json() as any).id);
  const duplicate = await postJson(server.baseUrl, "/api/wholesale", { ...saleBody(p.id, { method: "TRANSFERENCIA", amount: 80, bankVerification: proof }), clienteName: "Cliente comercial" }, tienda);
  assert.ok([400, 409].includes(duplicate.status));
  const summary: any = await (await fetch(server.baseUrl + `/api/payments/summary/${sale.id}`, { headers: jsonHeaders(tienda) })).json();
  assert.equal(summary.totalPaid, 20); assert.equal(summary.pending, 80);
  assert.equal(await stock(p.id), 3);
});

async function upload(p: { itemCode: string }, identity: string, quantity: number, compression = false) {
  const book = XLSX.utils.book_new(); XLSX.utils.book_append_sheet(book, XLSX.utils.json_to_sheet([{ Codigo: p.itemCode, Cantidad: quantity, Precio: 5 }]), "Factura");
  const form = new FormData();
  form.append("file", new Blob([XLSX.write(book, { type: "buffer", bookType: "xlsx", compression })], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), "factura.xlsx");
  form.append("supplierId", String(supplierId)); form.append("exchangeRate", "7"); form.append("locationId", String(ctx.locationIds.almacen)); form.append("documentIdentity", identity);
  return fetch(server.baseUrl + "/api/costs/import-invoice", { method: "POST", headers: { authorization: `Bearer ${admin}` }, body: form });
}
test("misma factura en otro archivo no repite recepción y otro contenido se bloquea", async () => {
  const p = await createProduct(ctx, { stockAlmacen: 1 });
  const first = await upload(p, "AUT-001 / SERIE A / 000123", 2);
  assert.equal(first.status, 200, await first.clone().text());
  const again = await upload(p, " aut-001 / serie a / 000123 ", 2, true);
  assert.equal(again.status, 200, await again.clone().text());
  assert.equal((await again.json() as any).replayed, true);
  assert.equal(await stock(p.id, ctx.locationIds.almacen), 3);
  assert.equal((await upload(p, "AUT-001 / SERIE A / 000123", 3)).status, 400);
  assert.equal(await ctx.prisma.cost.count({ where: { productId: p.id } }), 1);
  const cost = await ctx.prisma.cost.findFirstOrThrow({ where: { productId: p.id } });
  assert.equal((await fetch(server.baseUrl + `/api/costs/${cost.id}`, { method: "DELETE", headers: jsonHeaders(admin) })).status, 409);
});

test("recepción manual también exige identidad y no se repite", async () => {
  const p = await createProduct(ctx, { stockAlmacen: 1 });
  const body = { productId: p.id, supplierId, costPrice: 40, locationId: ctx.locationIds.almacen, quantity: 2 };
  assert.equal((await postJson(server.baseUrl, "/api/costs", body, admin)).status, 400);
  for (let i = 0; i < 2; i++) assert.equal((await postJson(server.baseUrl, "/api/costs", { ...body, documentIdentity: "MANUAL-000001" }, admin)).status, 201);
  assert.equal(await stock(p.id, ctx.locationIds.almacen), 3);
  assert.equal(await ctx.prisma.cost.count({ where: { productId: p.id } }), 1);
});

test("anulación de ADMIN conserva evidencia, deja deuda cero y repone una sola vez", async () => {
  const p = await createProduct(ctx, { stockTienda: 3 });
  const creation = { ...saleBody(p.id, { method: "CREDITO", amount: 100 }), customerData: { name: "Cliente comercial" } };
  const response = await postJson(server.baseUrl, "/api/sales", creation, tienda);
  assert.equal(response.status, 201); const sale: any = await response.json();
  const body = { operationId: randomUUID(), reason: "Error de producto <script> sin entrega", goodsNeverDeliveredAndVerified: true };
  assert.equal((await postJson(server.baseUrl, `/api/sales/${sale.id}/void`, body, tienda)).status, 403);
  assert.equal((await postJson(server.baseUrl, `/api/sales/${sale.id}/void`, { ...body, goodsNeverDeliveredAndVerified: false }, admin)).status, 400);
  const responses = await Promise.all([body, { ...body, operationId: randomUUID() }].map(payload => postJson(server.baseUrl, `/api/sales/${sale.id}/void`, payload, admin)));
  assert.deepEqual(responses.map(r => r.status), [200, 200]); assert.equal(await stock(p.id), 3);
  const preserved = await ctx.prisma.sale.findUniqueOrThrow({ where: { id: sale.id }, include: { items: true } });
  assert.equal(preserved.status, "VOIDED"); assert.equal(Number(preserved.total), 100); assert.equal(preserved.items.length, 1);
  assert.equal(await ctx.prisma.auditLog.count({ where: { action: "VOID_SALE", targetId: sale.id } }), 1);
  const oldAttempt: any = await (await postJson(server.baseUrl, "/api/sales", creation, tienda)).json();
  assert.equal(oldAttempt.id, sale.id); assert.equal(oldAttempt.status, "VOIDED"); assert.equal(await stock(p.id), 3);
  const recovered: any = await (await fetch(`${server.baseUrl}/api/operations/SALE_NORMAL/${creation.operationId}`, { headers: jsonHeaders(tienda) })).json();
  assert.equal(recovered.result.status, "VOIDED");
  const summary: any = await (await fetch(server.baseUrl + `/api/payments/summary/${sale.id}`, { headers: jsonHeaders(tienda) })).json();
  assert.equal(summary.pending, 0);
  assert.equal((await postJson(server.baseUrl, "/api/payments", { saleId: sale.id, method: "EFECTIVO", amount: 10 }, tienda)).status, 400);
  assert.equal((await postJson(server.baseUrl, "/api/returns", { saleId: sale.id, productId: p.id, quantity: 1, amount: 100, method: "EFECTIVO", reason: "No corresponde" }, tienda)).status, 409);
  const note = await (await fetch(server.baseUrl + `/api/sales/${sale.id}/nota`, { headers: jsonHeaders(admin) })).text();
  assert.ok(note.includes("VENTA ANULADA")); assert.ok(note.includes("&lt;script&gt;"));
  const report: any = await (await fetch(server.baseUrl + "/api/reports/sales", { headers: jsonHeaders(admin) })).json();
  assert.ok(report.sales.every((s: any) => s.id !== sale.id));
});

test("venta con cobros o devoluciones no admite anulación ni reposición directa", async () => {
  const p = await createProduct(ctx, { stockTienda: 2 });
  const sale: any = await (await postJson(server.baseUrl, "/api/sales", saleBody(p.id, { method: "EFECTIVO", amount: 100 }), tienda)).json();
  assert.equal((await postJson(server.baseUrl, `/api/sales/${sale.id}/void`, { operationId: randomUUID(), reason: "Intento que requiere devolución", goodsNeverDeliveredAndVerified: true }, admin)).status, 400);
  assert.equal(await stock(p.id), 1);
  const credit: any = await (await postJson(server.baseUrl, "/api/sales", { ...saleBody(p.id, { method: "CREDITO", amount: 100 }), customerData: { name: "Cliente comercial con devolución" } }, tienda)).json();
  assert.equal((await postJson(server.baseUrl, "/api/returns", { saleId: credit.id, productId: p.id, quantity: 1, amount: 100, method: "CREDITO", reason: "No se habilita stock sin inspección" }, tienda)).status, 201);
  assert.equal((await postJson(server.baseUrl, `/api/sales/${credit.id}/void`, { operationId: randomUUID(), reason: "Ya tiene devolución registrada", goodsNeverDeliveredAndVerified: true }, admin)).status, 400);
  assert.equal(await stock(p.id), 0);
});
