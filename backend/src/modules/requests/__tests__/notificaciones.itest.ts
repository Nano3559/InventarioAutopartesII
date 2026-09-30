import { test, before, after, describe } from "node:test";
import assert from "node:assert/strict";
import { startTestServer, TestServer, postJson, loginAndGetToken } from "../../../testing/helpers";
import { seed, cleanup, createProduct, SeedContext } from "../../../testing/seed";

/**
 * E5/E7 — el flujo de solicitudes debe notificar a INVENTARIO al CREAR la
 * solicitud. Antes solo se notificaba cuando el job activaba la solicitud por
 * `expectedDate`, y `POST /requests` ni siquiera fijaba `expectedDate`: la
 * solicitud quedaba PENDIENTE e invisible salvo que alguien abriera el módulo.
 */

let server: TestServer;
let ctx: SeedContext;
let tokenTienda: string;
let tokenInventario: string;

before(async () => {
  ctx = await seed("notifinv");
  server = await startTestServer();
  tokenTienda = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, ctx.users.tienda.password);
  tokenInventario = await loginAndGetToken(server.baseUrl, ctx.users.inventario.email, ctx.users.inventario.password);
});

after(async () => {
  await cleanup(ctx);
  await server.close();
});

describe("E5/E7 · notificar a INVENTARIO al crear la solicitud", () => {
  test("POST /requests crea la notificación para el usuario INVENTARIO", async () => {
    const p = await createProduct(ctx, { unitPrice: 100 });

    const res = await postJson(
      server.baseUrl,
      "/api/requests",
      { productId: p.id, quantity: 7, locationId: ctx.locationIds.tienda, note: "Prueba E5" },
      tokenTienda
    );
    assert.equal(res.status, 201);
    const body: any = await res.json();

    // La solicitud debe tener expectedDate: sin él el job nunca la activaba.
    assert.ok(body.expectedDate, "la solicitud debe tener expectedDate para que el job la active");

    // La notificación va a TODOS los usuarios INVENTARIO (enfoque correcto en
    // producción), así que al parallelism otros namespaces también notifican a
    // este usuario. Se cuentan solo los avisos de ESTA solicitud.
    const nuevas = await ctx.prisma.notification.findMany({
      where: { userId: ctx.users.inventario.userId, message: { contains: `#${body.id}` } },
    });
    assert.equal(nuevas.length, 1, "INVENTARIO debe recibir una notificación por esta solicitud");
    const n = nuevas[0];
    assert.match(n.title, /Nueva solicitud/);
    assert.match(n.message, new RegExp(p.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
    assert.equal(n.linkUrl, "/panel/solicitudes");
  });

  test("la venta que agota el stock también notifica a INVENTARIO", async () => {
    const p = await createProduct(ctx, { unitPrice: 100, stockTienda: 1, stockAlmacen: 20 });

    const res = await postJson(
      server.baseUrl,
      "/api/sales",
      {
        items: [{ productId: p.id, quantity: 1, unitPrice: 100 }],
        payments: [{ method: "EFECTIVO", amount: 100 }],
      },
      tokenTienda
    );
    assert.equal(res.status, 201);

    const request = await ctx.prisma.productRequest.findFirst({ where: { productId: p.id } });
    assert.ok(request, "debe crearse la solicitud de reposición");

    const notifs = await ctx.prisma.notification.findMany({
      where: { userId: ctx.users.inventario.userId, message: { contains: `#${request!.id}` } },
    });
    assert.equal(notifs.length, 1, "INVENTARIO debe ser notificado de la reposición automática");
  });

  test("no se duplica la notificación si ya existe una solicitud abierta", async () => {
    const p = await createProduct(ctx, { unitPrice: 100, stockTienda: 1, stockAlmacen: 20 });

    // Primera venta: crea solicitud + notificación.
    const r1 = await postJson(
      server.baseUrl,
      "/api/sales",
      { items: [{ productId: p.id, quantity: 1, unitPrice: 100 }], payments: [{ method: "EFECTIVO", amount: 100 }] },
      tokenTienda
    );
    assert.equal(r1.status, 201);
    const request = await ctx.prisma.productRequest.findFirst({ where: { productId: p.id } });
    assert.ok(request);
    const avisos1 = await ctx.prisma.notification.count({
      where: { userId: ctx.users.inventario.userId, message: { contains: `#${request!.id}` } },
    });
    assert.equal(avisos1, 1);

    // Reponemos y vendemos de nuevo: ya hay solicitud abierta, no debe duplicar.
    await ctx.prisma.inventory.update({
      where: { productId_locationId: { productId: p.id, locationId: ctx.locationIds.tienda } },
      data: { stock: 1 },
    });
    const r2 = await postJson(
      server.baseUrl,
      "/api/sales",
      { items: [{ productId: p.id, quantity: 1, unitPrice: 100 }], payments: [{ method: "EFECTIVO", amount: 100 }] },
      tokenTienda
    );
    assert.equal(r2.status, 201);

    const requests = await ctx.prisma.productRequest.count({ where: { productId: p.id } });
    assert.equal(requests, 1, "no debe crearse una segunda solicitud para el mismo producto/tienda");
    const avisos2 = await ctx.prisma.notification.count({
      where: { userId: ctx.users.inventario.userId, message: { contains: `#${request!.id}` } },
    });
    assert.equal(avisos2, 1, "no debe notificarse dos veces la misma reposición");
  });
});
