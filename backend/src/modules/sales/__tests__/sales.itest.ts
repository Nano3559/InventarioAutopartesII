import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { startTestServer, TestServer, postJson, loginAndGetToken } from "../../../testing/helpers";
import { seed, cleanup, createProduct, SeedContext } from "../../../testing/seed";

/**
 * ETAPA 6 — Ventas:
 *  - R6.6  Crear venta
 *  - R6.7  Descuento de stock
 *  - R6.8  Múltiples pagos
 *  - R6.9  Stock insuficiente
 *  - R6.10 Ventas concurrentes (invariante: nunca sobrevende)
 *  - R6.16 Reposición automática (al llegar a stock 0 se crea solicitud PENDIENTE)
 */

let server: TestServer;
let ctx: SeedContext;
let token: string;

before(async () => {
  ctx = await seed("sales");
  server = await startTestServer();
  token = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, ctx.users.tienda.password);
});

after(async () => {
  await cleanup(ctx);
  await server.close();
});

async function stockInTienda(productId: number): Promise<number> {
  const inv = await ctx.prisma.inventory.findUnique({
    where: { productId_locationId: { productId, locationId: ctx.locationIds.tienda } },
  });
  return inv?.stock ?? 0;
}

async function postSale(productId: number, quantity: number, paid: number, methods?: { method: string; amount: number }[]): Promise<Response> {
  return postJson(
    server.baseUrl,
    "/api/sales",
    {
      items: [{ productId, quantity, unitPrice: 100 }],
      payments: methods ?? [{ method: "EFECTIVO", amount: paid }],
    },
    token
  );
}

test("R6.6 — crear venta responde 201 con total, items y pagos calculados", async () => {
  const p = await createProduct(ctx, { stockTienda: 10 });
  const res = await postSale(p.id, 2, 200);
  assert.equal(res.status, 201);
  const body: any = await res.json();
  assert.ok(typeof body.id === "number");
  assert.equal(body.type, "NORMAL");
  assert.equal(Number(body.total), 200);
  assert.equal(body.items.length, 1);
  assert.equal(body.items[0].quantity, 2);
  assert.equal(Number(body.items[0].subtotal), 200);
  assert.equal(body.payments.length, 1);
  assert.equal(Number(body.payments[0].amount), 200);
});

test("R6.7 — al vender se descuenta el stock de la tienda", async () => {
  const p = await createProduct(ctx, { stockTienda: 8 });
  const res = await postSale(p.id, 3, 300);
  assert.equal(res.status, 201);
  assert.equal(await stockInTienda(p.id), 5);
});

test("R6.8 — venta con múltiples pagos suma correcta y valida métodos/montos", async () => {
  const p = await createProduct(ctx, { stockTienda: 10 });
  const res = await postSale(p.id, 3, 300, [
    { method: "EFECTIVO", amount: 120 },
    { method: "QR", amount: 180 },
  ]);
  assert.equal(res.status, 201);
  const body: any = await res.json();
  assert.equal(body.payments.length, 2);
  const sum = body.payments.reduce((acc: number, pay: any) => acc + Number(pay.amount), 0);
  assert.equal(sum, 300);

  const badMethod = await postSale(p.id, 1, 100, [{ method: "BITCOIN", amount: 100 }]);
  assert.equal(badMethod.status, 400);
  const badMethodBody: any = await badMethod.json();
  assert.equal(badMethodBody.message, "Método de pago inválido: BITCOIN");

  const negative = await postSale(p.id, 1, 100, [{ method: "EFECTIVO", amount: -5 }]);
  assert.equal(negative.status, 400);
});

test("R6.9 — venta sin stock suficiente responde 400 y no descuenta", async () => {
  const p = await createProduct(ctx, { stockTienda: 2 });
  const res = await postSale(p.id, 5, 500);
  assert.equal(res.status, 400);
  const body: any = await res.json();
  assert.match(body.message, /Stock insuficiente/);
  assert.equal(await stockInTienda(p.id), 2, "el stock no debe cambiar tras la venta fallida");
});

test("R6.10 — dos ventas concurrentes que agotarían el stock: exactamente una gana y el stock nunca es negativo", async () => {
  const p = await createProduct(ctx, { stockTienda: 5 });
  const [a, b] = await Promise.all([postSale(p.id, 3, 300), postSale(p.id, 3, 300)]);

  const statuses = [a.status, b.status].sort();
  assert.deepEqual(statuses, [201, 400], "una venta debe ganar y la otra fallar por stock");
  const loser: any = a.status === 400 ? await a.json() : await b.json();
  assert.match(loser.message, /Stock insuficiente/);
  assert.equal(await stockInTienda(p.id), 2);

  const soldCount = await ctx.prisma.saleItem.count({ where: { productId: p.id } });
  assert.equal(soldCount, 1, "solo debe existir un ítem vendido para el producto");
});

test("R6.16 — al llegar a stock 0 se crea solicitud de reposición automática (PENDIENTE, 5 unidades)", async () => {
  // El replenish usa findFirst({type:"ALMACEN"}), por lo tanto el producto debe tener
  // stock en el almacén "escogido" aunque ese no sea el del namespace (evita acoplamiento
  // con namespaces paralelos en la misma BD de prueba).
  const almacenIds = (await ctx.prisma.location.findMany({ where: { type: "ALMACEN" } })).map((a) => a.id);

  const p = await createProduct(ctx, { stockTienda: 1 });
  await ctx.prisma.inventory.createMany({
    data: almacenIds.map((locationId) => ({ productId: p.id, locationId, stock: 10, minStock: 1 })),
    skipDuplicates: true,
  });

  const res = await postSale(p.id, 1, 100);
  assert.equal(res.status, 201);

  const request = await ctx.prisma.productRequest.findFirst({
    where: { productId: p.id, locationId: ctx.locationIds.tienda, status: "PENDIENTE" },
  });
  assert.ok(request, "debe crearse una solicitud PENDIENTE al agotar el stock");
  assert.equal(request!.quantity, 5, "cantidad = max(vendida, 5)");
  assert.equal(request!.requestedById, ctx.users.tienda.userId);

  // Sin stock suficiente en el almacén no se crea la solicitud.
  const pSinAlmacen = await createProduct(ctx, { stockTienda: 1 });
  const res2 = await postSale(pSinAlmacen.id, 1, 100);
  assert.equal(res2.status, 201);
  const count = await ctx.prisma.productRequest.count({ where: { productId: pSinAlmacen.id } });
  assert.equal(count, 0, "no debe solicitarse reposición si el almacén no tiene stock");
});