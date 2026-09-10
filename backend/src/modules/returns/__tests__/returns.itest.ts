import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { startTestServer, TestServer, postJson, loginAndGetToken } from "../../../testing/helpers";
import { seed, cleanup, createProduct, SeedContext } from "../../../testing/seed";

/**
 * ETAPA 6 — Devoluciones:
 *  - R6.13 Devolución válida
 *  - R6.14 Devolución superior a la cantidad vendida
 *  - R6.15 Incremento de stock por devolución (+ guarda contra doble devolución)
 */

let server: TestServer;
let ctx: SeedContext;
let token: string;

before(async () => {
  ctx = await seed("returns");
  server = await startTestServer();
  token = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, ctx.users.tienda.password);
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

async function postReturn(saleId: number, productId: number, quantity: number, amount: number, method = "EFECTIVO"): Promise<Response> {
  return postJson(
    server.baseUrl,
    "/api/returns",
    { saleId, productId, reason: "Garantía", quantity, amount, method },
    token
  );
}

async function stockInTienda(productId: number): Promise<number> {
  const inv = await ctx.prisma.inventory.findUnique({
    where: { productId_locationId: { productId, locationId: ctx.locationIds.tienda } },
  });
  return inv?.stock ?? 0;
}

test("R6.13 — devolución válida responde 201 con cantidad y datos", async () => {
  const p = await createProduct(ctx, { stockTienda: 5 });
  const saleId = await sell(p.id, 5);
  const res = await postReturn(saleId, p.id, 2, 200);
  assert.equal(res.status, 201);
  const body: any = await res.json();
  assert.equal(body.quantity, 2);
  assert.equal(body.saleId, saleId);
  assert.equal(body.productId, p.id);
  assert.equal(body.reason, "Garantía");
});

test("R6.14 — devoluciones inválidas responden 400", async () => {
  const p = await createProduct(ctx, { stockTienda: 5 });
  const saleId = await sell(p.id, 2);

  const excess = await postReturn(saleId, p.id, 3, 300);
  assert.equal(excess.status, 400);
  const excessBody: any = await excess.json();
  assert.equal(excessBody.message, "La cantidad a devolver (3) excede la vendida (2)");

  const badMethod = await postReturn(saleId, p.id, 1, 100, "BITCOIN");
  assert.equal(badMethod.status, 400);
  const badMethodBody: any = await badMethod.json();
  assert.match(badMethodBody.message, /Método inválido/);

  const badAmount = await postReturn(saleId, p.id, 1, 999);
  assert.equal(badAmount.status, 400);
  const badAmountBody: any = await badAmount.json();
  assert.match(badAmountBody.message, /El monto devuelto/);

  const notOwned = await postReturn(999999, p.id, 1, 100);
  assert.equal(notOwned.status, 404);
});

test("R6.15 — la devolución incrementa el stock y bloquea devolver más de lo vendido", async () => {
  const p = await createProduct(ctx, { stockTienda: 5 });
  const saleId = await sell(p.id, 3);
  assert.equal(await stockInTienda(p.id), 2);

  const first = await postReturn(saleId, p.id, 2, 200);
  assert.equal(first.status, 201);
  assert.equal(await stockInTienda(p.id), 4, "el stock debe aumentar con la cantidad devuelta");

  const second = await postReturn(saleId, p.id, 2, 200);
  assert.equal(second.status, 400);
  const secondBody: any = await second.json();
  assert.match(secondBody.message, /Ya se devolvieron/);
  assert.match(secondBody.message, /Máximo adicional: 1\./);

  const returnsCount = await ctx.prisma.return.count({ where: { saleId, productId: p.id } });
  assert.equal(returnsCount, 1, "solo debe registrarse una devolución");
});