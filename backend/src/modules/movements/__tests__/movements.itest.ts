import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { startTestServer, TestServer, postJson, loginAndGetToken } from "../../../testing/helpers";
import { seed, cleanup, createProduct, SeedContext } from "../../../testing/seed";

/**
 * ETAPA 6 — Inventario / movimientos:
 *  - R6.11 Movimiento de stock (ALMACÉN → TIENDA, descuenta y acredita)
 *  - R6.12 Movimiento concurrente (invariante: el origen nunca queda negativo)
 */

let server: TestServer;
let ctx: SeedContext;
let token: string;

before(async () => {
  ctx = await seed("movements");
  server = await startTestServer();
  token = await loginAndGetToken(server.baseUrl, ctx.users.inventario.email, ctx.users.inventario.password);
});

after(async () => {
  await cleanup(ctx);
  await server.close();
});

async function stock(productId: number, locationId: number): Promise<number> {
  const inv = await ctx.prisma.inventory.findUnique({
    where: { productId_locationId: { productId, locationId } },
  });
  return inv?.stock ?? 0;
}

async function postMovement(productId: number, quantity: number): Promise<Response> {
  return postJson(
    server.baseUrl,
    "/api/movements",
    {
      productId,
      fromLocationId: ctx.locationIds.almacen,
      toLocationId: ctx.locationIds.tienda,
      quantity,
      observation: "Movimiento de prueba",
    },
    token
  );
}

test("R6.11 — movimiento válido ALMACÉN→TIENDA descuenta origen y acredita destino", async () => {
  const p = await createProduct(ctx, { stockAlmacen: 10, stockTienda: 0 });
  const res = await postMovement(p.id, 4);
  assert.equal(res.status, 201);
  const body: any = await res.json();
  assert.equal(body.quantity, 4);
  assert.equal(body.product.itemCode, p.itemCode);

  assert.equal(await stock(p.id, ctx.locationIds.almacen), 6);
  assert.equal(await stock(p.id, ctx.locationIds.tienda), 4);
});

test("R6.11 — validaciones de movimiento: origen==destino y stock insuficiente en origen", async () => {
  const p = await createProduct(ctx, { stockAlmacen: 2, stockTienda: 0 });

  const sameLocation = await postJson(
    server.baseUrl,
    "/api/movements",
    {
      productId: p.id,
      fromLocationId: ctx.locationIds.almacen,
      toLocationId: ctx.locationIds.almacen,
      quantity: 1,
    },
    token
  );
  assert.equal(sameLocation.status, 400);
  const sameBody: any = await sameLocation.json();
  assert.equal(sameBody.message, "La ubicación de origen y destino no pueden ser la misma");

  const tooMuch = await postMovement(p.id, 5);
  assert.equal(tooMuch.status, 400);
  const tooMuchBody: any = await tooMuch.json();
  assert.match(tooMuchBody.message, /Stock insuficiente en origen/);
  assert.equal(await stock(p.id, ctx.locationIds.almacen), 2, "el stock no cambia tras el movimiento fallido");
});

test("R6.12 — dos movimientos concurrentes que agotarían el origen: exactamente uno gana y el stock nunca es negativo", async () => {
  const p = await createProduct(ctx, { stockAlmacen: 5, stockTienda: 0 });
  const [a, b] = await Promise.all([postMovement(p.id, 4), postMovement(p.id, 4)]);

  const statuses = [a.status, b.status].sort();
  assert.deepEqual(statuses, [201, 400], "un movimiento debe ganar y el otro fallar por stock");
  const loser: any = a.status === 400 ? await a.json() : await b.json();
  assert.match(loser.message, /Stock insuficiente en origen/);

  assert.equal(await stock(p.id, ctx.locationIds.almacen), 1);
  assert.equal(await stock(p.id, ctx.locationIds.tienda), 4);

  const count = await ctx.prisma.movement.count({ where: { productId: p.id } });
  assert.equal(count, 1, "solo debe registrarse un movimiento");
});