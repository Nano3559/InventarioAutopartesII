import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import * as XLSX from "xlsx";
import { seed, cleanup, createProduct, SeedContext } from "../../../testing/seed";
import { startTestServer, TestServer, loginAndGetToken } from "../../../testing/helpers";
let ctx: SeedContext;
let server: TestServer;
let token: string;
before(async () => { ctx = await seed("importproducts"); server = await startTestServer(); token = await loginAndGetToken(server.baseUrl, ctx.users.admin.email, ctx.users.admin.password); });
after(async () => { await cleanup(ctx); await server.close(); });
async function importRow(row: Record<string, unknown>) {
  const book = XLSX.utils.book_new(); XLSX.utils.book_append_sheet(book, XLSX.utils.json_to_sheet([row]), "Productos");
  const form = new FormData();
  form.append("file", new Blob([XLSX.write(book, { type: "buffer", bookType: "xlsx" })], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), "productos.xlsx");
  form.append("locationId", String(ctx.locationIds.tienda));
  return fetch(`${server.baseUrl}/api/products/import`, { method: "POST", headers: { authorization: `Bearer ${token}` }, body: form });
}
test("importar metadatos sin columna Stock no vacía el inventario", async () => {
  const p = await createProduct(ctx, { stockTienda: 7 });
  const response = await importRow({ Codigo: p.itemCode, Nombre: p.name });
  assert.equal(response.status, 200);
  assert.equal((await response.json() as any).errors, 0);
  assert.equal((await ctx.prisma.inventory.findUniqueOrThrow({ where: { productId_locationId: { productId: p.id, locationId: ctx.locationIds.tienda } } })).stock, 7);
});
test("importación exige stock esperado y revierte precios contradictorios", async () => {
  const p = await createProduct(ctx, { stockTienda: 7 });
  for (const change of [{ Stock: 0 }, { "Precio 1": 10 }, { "Precio mayor": 120 }]) {
    const response = await importRow({ Codigo: p.itemCode, Nombre: p.name, ...change });
    assert.equal((await response.json() as any).errors, 1);
  }
  assert.equal(Number((await ctx.prisma.product.findUniqueOrThrow({ where: { id: p.id } })).price1), 100);
  const response = await importRow({ Codigo: p.itemCode, Nombre: p.name, Stock: 5, "Stock esperado": 7 });
  assert.equal((await response.json() as any).errors, 0);
  assert.equal((await ctx.prisma.inventory.findUniqueOrThrow({ where: { productId_locationId: { productId: p.id, locationId: ctx.locationIds.tienda } } })).stock, 5);
});
