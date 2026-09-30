import { test, before, after, describe } from "node:test";
import assert from "node:assert/strict";
import { startTestServer, TestServer, postJson, loginAndGetToken } from "../../../testing/helpers";
import { seed, cleanup, createProduct, SeedContext } from "../../../testing/seed";

/**
 * P0-7 — El precio lo fija el SERVIDOR, nunca el cliente.
 *
 * Un cliente (carrito web, app móvil o cualquier cliente HTTP) puede enviar
 * `unitPrice` manipulado: la API debe IGNORARLO y cobrar el precio del catálogo
 * en la base de datos.
 *
 * Reglas verificadas aquí:
 *  - Venta NORMAL  -> Product.price2 (minorista), fallback a price1 si price2 <= 0
 *  - Venta MAYORISTA -> Product.wholesalePrice (fallback a price1 si es null)
 *  - Precio de BD <= 0 -> la venta se RECHAZA (nunca se cobra 0 ni negativo).
 *
 * Semántica de precios del catálogo (ver prices.routes e InventoryPage):
 *   price1 = mayorista, price2 = minorista.
 * La venta NORMAL es venta al público minorista; por eso cobra price2.
 */

let server: TestServer;
let ctx: SeedContext;
let tokenTienda: string;
let tokenAdmin: string;

before(async () => {
  ctx = await seed("preciosrv");
  server = await startTestServer();
  tokenTienda = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, ctx.users.tienda.password);
  tokenAdmin = await loginAndGetToken(server.baseUrl, ctx.users.admin.email, ctx.users.admin.password);
});

after(async () => {
  await cleanup(ctx);
  await server.close();
});

function ventaSimple(productId: number, unitPrice: number, quantity = 1) {
  return postJson(
    server.baseUrl,
    "/api/sales",
    {
      items: [{ productId, quantity, unitPrice }],
      payments: [{ method: "EFECTIVO", amount: 999999 }],
    },
    tokenTienda
  );
}

describe("P0-7 · venta NORMAL usa Product.price2 (minorista) e ignora el unitPrice del cliente", () => {
  test("con price1 != price2 se cobra el minorista (price2), no el mayorista", async () => {
    const p = await createProduct(ctx, { price1: 100, price2: 280, stockTienda: 10 });
    const res = await postJson(
      server.baseUrl,
      "/api/sales",
      {
        items: [{ productId: p.id, quantity: 2, unitPrice: 1 }],
        payments: [{ method: "EFECTIVO", amount: 560 }],
      },
      tokenTienda
    );

    assert.equal(res.status, 201, "el POS minorista debe poder cobrar el precio minorista");
    const body: any = await res.json();
    assert.equal(Number(body.items[0].unitPrice), 280, "venta al público cobra price2 (minorista)");
    assert.equal(Number(body.items[0].subtotal), 560);
    assert.equal(Number(body.total), 560);
  });

  test("si price2 no esta definido (0) cae a price1", async () => {
    const p = await createProduct(ctx, { price1: 100, price2: 0, stockTienda: 10 });
    const res = await postJson(
      server.baseUrl,
      "/api/sales",
      {
        items: [{ productId: p.id, quantity: 1, unitPrice: 999999 }],
        payments: [{ method: "EFECTIVO", amount: 100 }],
      },
      tokenTienda
    );

    assert.equal(res.status, 201);
    const body: any = await res.json();
    assert.equal(Number(body.items[0].unitPrice), 100, "fallback a price1 cuando no hay minorista");
  });

  test("unitPrice manipulado a 1 se descarta y se cobra el precio de catálogo", async () => {
    const p = await createProduct(ctx, { unitPrice: 100, stockTienda: 10 });
    const res = await postJson(
      server.baseUrl,
      "/api/sales",
      {
        items: [{ productId: p.id, quantity: 2, unitPrice: 1 }],
        payments: [{ method: "EFECTIVO", amount: 200 }],
      },
      tokenTienda
    );

    assert.equal(res.status, 201);
    const body: any = await res.json();
    assert.equal(Number(body.items[0].unitPrice), 100, "el item debe quedar al precio de catálogo");
    assert.equal(Number(body.items[0].subtotal), 200);
    assert.equal(Number(body.total), 200, "el total ignora el unitPrice del cliente");
  });

  test("unitPrice inflado a 999999 se descarta y se cobra el precio de catálogo", async () => {
    const p = await createProduct(ctx, { unitPrice: 50, stockTienda: 10 });
    const res = await postJson(
      server.baseUrl,
      "/api/sales",
      {
        items: [{ productId: p.id, quantity: 1, unitPrice: 999999 }],
        payments: [{ method: "EFECTIVO", amount: 50 }],
      },
      tokenTienda
    );

    assert.equal(res.status, 201);
    const body: any = await res.json();
    assert.equal(Number(body.items[0].unitPrice), 50);
    assert.equal(Number(body.total), 50, "nadie puede cobrar de más desde el cliente");
  });

  test("unitPrice a 0 o negativo se rechaza por validación (400)", async () => {
    const p = await createProduct(ctx, { unitPrice: 100, stockTienda: 10 });
    for (const manipulado of [0, -5]) {
      const res = await postJson(
        server.baseUrl,
        "/api/sales",
        {
          items: [{ productId: p.id, quantity: 1, unitPrice: manipulado }],
          payments: [{ method: "EFECTIVO", amount: 100 }],
        },
        tokenTienda
      );
      assert.equal(res.status, 400, `unitPrice=${manipulado} debe rechazarse`);
    }
  });

  test("precio de base de datos <= 0 -> la venta se rechaza, no se cobra 0", async () => {
    const p = await createProduct(ctx, { unitPrice: 0, stockTienda: 10 });
    const res = await postJson(
      server.baseUrl,
      "/api/sales",
      {
        items: [{ productId: p.id, quantity: 1, unitPrice: 100 }],
        payments: [{ method: "EFECTIVO", amount: 100 }],
      },
      tokenTienda
    );
    assert.equal(res.status, 400, "sin precio de catálogo válido no se puede vender");
    const body: any = await res.json();
    assert.match(String(body.message), /precio/i);
  });
});

describe("P0-7 · venta MAYORISTA usa wholesalePrice y ignora el unitPrice del cliente", () => {
  test("unitPrice manipulado se descarta y se cobra wholesalePrice", async () => {
    const p = await createProduct(ctx, { unitPrice: 100, wholesalePrice: 80, stockTienda: 10 });
    const res = await postJson(
      server.baseUrl,
      "/api/wholesale",
      {
        items: [{ productId: p.id, quantity: 2, unitPrice: 1 }],
        payments: [{ method: "EFECTIVO", amount: 160 }],
        locationId: ctx.locationIds.tienda,
      },
      tokenAdmin
    );

    assert.equal(res.status, 201);
    const body: any = await res.json();
    assert.equal(Number(body.items[0].unitPrice), 80, "debe cobrarse el precio mayorista del catálogo");
    assert.equal(Number(body.total), 160);
  });

  test("sin wholesalePrice (null) cae a price1", async () => {
    const p = await createProduct(ctx, { unitPrice: 120, wholesalePrice: null, stockTienda: 10 });
    const res = await postJson(
      server.baseUrl,
      "/api/wholesale",
      {
        items: [{ productId: p.id, quantity: 1, unitPrice: 5 }],
        payments: [{ method: "EFECTIVO", amount: 120 }],
        locationId: ctx.locationIds.tienda,
      },
      tokenAdmin
    );

    assert.equal(res.status, 201);
    const body: any = await res.json();
    assert.equal(Number(body.items[0].unitPrice), 120, "fallback a price1 cuando no hay precio mayorista");
    assert.equal(Number(body.total), 120);
  });

  test("precio de base de datos <= 0 -> la venta mayorista se rechaza", async () => {
    const p = await createProduct(ctx, { unitPrice: 0, wholesalePrice: 0, stockTienda: 10 });
    const res = await postJson(
      server.baseUrl,
      "/api/wholesale",
      {
        items: [{ productId: p.id, quantity: 1, unitPrice: 10 }],
        payments: [{ method: "EFECTIVO", amount: 10 }],
        locationId: ctx.locationIds.tienda,
      },
      tokenAdmin
    );
    assert.equal(res.status, 400);
  });
});

/**
 * Clasificación de errores en POST /sales y POST /wholesale.
 *
 * Antes respondían 400 con `error.message` para CUALQUIER fallo, así que un TypeError o
 * un error interno devolvía 400 y filtraba el mensaje real al cliente. Ahora solo los
 * rechazos de negocio (ErrorDominio) son 400 con su mensaje propio; el resto va al 500
 * genérico del errorHandler.
 */
describe("Manejo de errores · los rechazos de negocio siguen siendo 400 con su mensaje", () => {
  test("venta normal: stock insuficiente -> 400 con mensaje explicativo", async () => {
    const p = await createProduct(ctx, { price1: 100, price2: 100, stockTienda: 1 });
    const res = await postJson(
      server.baseUrl,
      "/api/sales",
      {
        items: [{ productId: p.id, quantity: 50, unitPrice: 100 }],
        payments: [{ method: "EFECTIVO", amount: 5000 }],
      },
      tokenTienda
    );
    assert.equal(res.status, 400);
    const body: any = await res.json();
    assert.match(body.message, /Stock insuficiente/i);
    assert.ok(body.message.includes(p.id) || body.message.length > 0, "el mensaje de negocio es útil");
  });

  test("venta normal: total pagado que no coincide -> 400 con el detalle del importe", async () => {
    const p = await createProduct(ctx, { price1: 100, price2: 200, stockTienda: 10 });
    const res = await postJson(
      server.baseUrl,
      "/api/sales",
      {
        items: [{ productId: p.id, quantity: 1, unitPrice: 200 }],
        payments: [{ method: "EFECTIVO", amount: 999 }],
      },
      tokenTienda
    );
    assert.equal(res.status, 400);
    const body: any = await res.json();
    assert.match(body.message, /no coincide con el total/i);
  });

  test("venta normal: producto inexistente -> 400 (no 404, no 500)", async () => {
    const res = await postJson(
      server.baseUrl,
      "/api/sales",
      {
        items: [{ productId: 99999999, quantity: 1, unitPrice: 100 }],
        payments: [{ method: "EFECTIVO", amount: 100 }],
      },
      tokenTienda
    );
    assert.equal(res.status, 400);
    const body: any = await res.json();
    assert.match(body.message, /no encontrado/i);
  });

  test("venta normal: payload sin items -> 400 con mensaje de validación", async () => {
    const res = await postJson(server.baseUrl, "/api/sales", { items: [], payments: [{ method: "EFECTIVO", amount: 0 }] }, tokenTienda);
    assert.equal(res.status, 400);
    const body: any = await res.json();
    assert.match(body.message, /al menos un producto|ítem|item/i);
  });

  test("venta normal: método de pago inválido -> 400 controlado", async () => {
    const p = await createProduct(ctx, { price1: 100, price2: 100, stockTienda: 10 });
    const res = await postJson(
      server.baseUrl,
      "/api/sales",
      {
        items: [{ productId: p.id, quantity: 1, unitPrice: 100 }],
        payments: [{ method: "EFECTIVO", amount: 100 }],
        formaPago: "BITCOIN",
      },
      tokenTienda
    );
    assert.equal(res.status, 400);
    const body: any = await res.json();
    assert.match(body.message, /Método de pago inválido/i);
  });

  test("venta mayorista: stock insuficiente -> 400 con mensaje explicativo", async () => {
    const p = await createProduct(ctx, { price1: 100, wholesalePrice: 80, stockTienda: 1 });
    const res = await postJson(
      server.baseUrl,
      "/api/wholesale",
      {
        items: [{ productId: p.id, quantity: 99, unitPrice: 80 }],
        payments: [{ method: "EFECTIVO", amount: 7920 }],
        locationId: ctx.locationIds.tienda,
      },
      tokenAdmin
    );
    assert.equal(res.status, 400);
    const body: any = await res.json();
    assert.match(body.message, /Stock insuficiente/i);
  });

  test("venta mayorista: total que no coincide -> 400", async () => {
    const p = await createProduct(ctx, { price1: 100, wholesalePrice: 80, stockTienda: 10 });
    const res = await postJson(
      server.baseUrl,
      "/api/wholesale",
      {
        items: [{ productId: p.id, quantity: 1, unitPrice: 80 }],
        payments: [{ method: "EFECTIVO", amount: 12345 }],
        locationId: ctx.locationIds.tienda,
      },
      tokenAdmin
    );
    assert.equal(res.status, 400);
    const body: any = await res.json();
    assert.match(body.message, /no coincide con el total/i);
  });

  test("ningún error de negocio filtra una traza, un stack ni rutas del servidor", async () => {
    const p = await createProduct(ctx, { price1: 100, price2: 100, stockTienda: 1 });
    const res = await postJson(
      server.baseUrl,
      "/api/sales",
      {
        items: [{ productId: p.id, quantity: 50, unitPrice: 100 }],
        payments: [{ method: "EFECTIVO", amount: 5000 }],
      },
      tokenTienda
    );
    const body: any = await res.json();
    const texto = JSON.stringify(body);
    assert.equal(/at\s+\w+\s+\(/.test(texto), false, "no debe incluir un stack trace");
    assert.equal(texto.includes("E:\\"), false, "no debe incluir rutas del sistema de archivos");
    assert.equal(texto.toLowerCase().includes("prisma"), false, "no debe mencionar Prisma");
  });
});
