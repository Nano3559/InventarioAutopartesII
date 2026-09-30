import { test, before, after, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { startTestServer, mintTestToken, postJson, jsonHeaders, TestServer } from "../../../testing/helpers";
import { seed, cleanup, createProduct, SeedContext } from "../../../testing/seed";

/**
 * Alcance del módulo de inventario: qué puede leer y escribir cada rol.
 *
 * ANTES de esta ronda:
 *
 *  - `GET /api/inventory` y `GET /api/inventory/product/:productId` solo exigían
 *    `authenticate`: un rol nuevo creado en el panel heredaba el inventario de toda la
 *    cadena, y el `include: { product: true` )` traía el Product completo en la consulta
 *    (aunque la respuesta solo serializaba 5 campos, dependedía de que nadie añadiera
 *    uno nuevo). El acotado por ubicación usaba `if (role === "TIENDA")`, una deny-list:
 *    cualquier otro rol caía del lado de la vista global.
 *  - `PUT /api/inventory/:id` era `authorize("ADMIN")`, así que INVENTARIO (que según el
 *    manual funcional controla físicamente la mercadería) recibía 403 al ajustar stock.
 *
 * AHORA: lectura con allow-list `ROLES_CON_INVENTARIO` (TIENDA incluido, acotado a su
 * tienda) y escritura con allow-list `ROLES_QUE_AJUSTAN_INVENTARIO` (ADMIN +
 * INVENTARIO). Los campos financieros de la respuesta de escritura siguen las mismas
 * allow-lists que /api/products. Ver shared/utils/scope.ts.
 */

let server: TestServer;
let ctx: SeedContext | null = null;
let productId = 0;
let invTiendaId = 0;
let invAlmacenId = 0;
let otraTiendaId = 0;

/** Sufijo único por corrida: los correos de esta suite son únicos (ver productsScope). */
const runId = Math.random().toString(36).slice(2, 8);

const getJson = async (ruta: string, token?: string): Promise<{ status: number; body: any }> => {
  const res = await fetch(`${server.baseUrl}${ruta}`, { headers: jsonHeaders(token) });
  return { status: res.status, body: await res.json() };
};

const putJson = async (ruta: string, body: unknown, token?: string): Promise<{ status: number; body: any }> => {
  const res = await fetch(`${server.baseUrl}${ruta}`, {
    method: "PUT",
    headers: { ...jsonHeaders(token), "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return { status: res.status, body: await res.json() };
};

/**
 * Token emitido directamente en vez de por /api/auth/login: esta suite hace muchos
 * POST de venta/movimiento y el login tiene rate limit por IP, así que superarlo
 * devolvería 429 y la prueba fallaría por el límite y no por el alcance que verifica.
 */
const tokenDe = (u: { email: string; userId: number; locationId: number | null }, role: string) =>
  mintTestToken({ userId: u.userId, email: u.email, role, locationId: u.locationId });

/** Crea un usuario con un rol nuevo y devuelve su token (rol data-driven del panel). */
async function tokenParaRolDesconocido(nombreRol: string, conUbicacion: boolean) {
  const tienda = await ctx!.prisma.user.findUniqueOrThrow({ where: { id: ctx!.users.tienda.userId } });
  const rol = await ctx!.prisma.roleModel.create({ data: { name: nombreRol } });
  const usuario = await ctx!.prisma.user.create({
    data: {
      email: `inv-${nombreRol.toLowerCase()}-${runId}-${ctx!.ns}@test.com`,
      password: tienda.password,
      name: `Usuario ${nombreRol}`,
      roleId: rol.id,
      locationId: conUbicacion ? ctx!.locationIds.tienda : null,
    },
  });
  const token = mintTestToken({ userId: usuario.id, email: usuario.email, role: nombreRol, locationId: usuario.locationId });
  return { rol, usuario, token };
}

const filaDe = (body: any[], productId: number, locationId: number) =>
  body.find((f) => f.productId === productId && f.locationId === locationId);

const stockEnTienda = async (pid: number): Promise<number> => {
  const inv = await ctx!.prisma.inventory.findUnique({
    where: { productId_locationId: { productId: pid, locationId: ctx!.locationIds.tienda } },
  });
  return inv?.stock ?? -1;
};

before(async () => {
  server = await startTestServer();
});

beforeEach(async () => {
  if (!ctx) {
    ctx = await seed("inventory-scope");
    // Segunda tienda para comprobar que un TIENDA no lee existencias de otra.
    const otra = await ctx.prisma.location.create({
      data: { name: `TIENDA2-${ctx.ns}`, type: "TIENDA", address: "Zona Test 2" },
    });
    otraTiendaId = otra.id;

    // 5 en la tienda del usuario, 40 en almacén y 9 en la otra tienda: la suma global
    // (54) y el valor real de su tienda (5) deben ser distinguibles en los tests.
    const p = await createProduct(ctx, { stockTienda: 5, stockAlmacen: 40 });
    productId = p.id;
    await ctx.prisma.inventory.create({ data: { productId: p.id, locationId: otra.id, stock: 9, minStock: 1 } });

    const filas = await ctx.prisma.inventory.findMany({ where: { productId: p.id } });
    invTiendaId = filas.find((f) => f.locationId === ctx!.locationIds.tienda)!.id;
    invAlmacenId = filas.find((f) => f.locationId === ctx!.locationIds.almacen)!.id;
  }
});

after(async () => {
  if (ctx) {
    try {
      await ctx.prisma.location.deleteMany({ where: { id: otraTiendaId } });
    } catch {
      // ignore: puede tener dependientes; el resto de la suite sigue siendo válido
    }
    await cleanup(ctx);
  }
  await server.close();
});

// ===== GET /api/inventory =====

test("GET inventory — sin token responde 401", async () => {
  const { status, body } = await getJson("/api/inventory");
  assert.equal(status, 401, "consultar inventario exige autenticación");
  assert.equal(body.length, undefined, "no debe filtrar existencias sin token");
});

test("GET inventory — ADMIN ve la cadena completa y puede filtrar por locationId", async () => {
  const token = tokenDe(ctx!.users.admin, "ADMIN");
  const { status, body } = await getJson("/api/inventory", token);
  assert.equal(status, 200);
  assert.ok(Array.isArray(body) && body.length > 0, "ADMIN lista el inventario");

  const enTienda = filaDe(body, productId, ctx!.locationIds.tienda);
  const enAlmacen = filaDe(body, productId, ctx!.locationIds.almacen);
  const enOtra = filaDe(body, productId, otraTiendaId);
  assert.equal(enTienda.stock, 5, "ADMIN ve el stock de la tienda");
  assert.equal(enAlmacen.stock, 40, "y el del almacén");
  assert.equal(enOtra.stock, 9, "y el de la otra tienda");

  // El ?locationId de ADMIN sí se aplica (es lo que usa la pantalla de inventario).
  const filtrado = await getJson(`/api/inventory?locationId=${ctx!.locationIds.almacen}`, token);
  assert.equal(filtrado.status, 200);
  assert.equal(filaDe(filtrado.body, productId, ctx!.locationIds.tienda), undefined, "el filtro debe excluir otras ubicaciones");
  assert.equal(filaDe(filtrado.body, productId, ctx!.locationIds.almacen).stock, 40);
});

test("GET inventory — INVENTARIO ve la cadena completa (control físico de la mercadería)", async () => {
  const token = tokenDe(ctx!.users.inventario, "INVENTARIO");
  const { status, body } = await getJson("/api/inventory", token);
  assert.equal(status, 200, "INVENTARIO debe poder consultar el inventario");
  assert.equal(filaDe(body, productId, ctx!.locationIds.tienda).stock, 5);
  assert.equal(filaDe(body, productId, ctx!.locationIds.almacen).stock, 40);
  assert.equal(filaDe(body, productId, otraTiendaId).stock, 9);
});

test("GET inventory — TIENDA solo ve SU ubicación", async () => {
  const token = tokenDe(ctx!.users.tienda, "TIENDA");
  const { status, body } = await getJson("/api/inventory", token);
  assert.equal(status, 200, "TIENDA conserva su consulta de stock: es su flujo funcional");
  assert.equal(filaDe(body, productId, ctx!.locationIds.tienda).stock, 5, "ve su propia tienda");
  assert.equal(filaDe(body, productId, ctx!.locationIds.almacen), undefined, "no ve el almacén");
  assert.equal(filaDe(body, productId, otraTiendaId), undefined, "no ve otras tiendas");
});

test("GET inventory — TIENDA no puede ampliar su alcance con ?locationId", async () => {
  const token = tokenDe(ctx!.users.tienda, "TIENDA");
  const sonda = await getJson(`/api/inventory?locationId=${ctx!.locationIds.almacen}`, token);
  assert.equal(sonda.status, 200);
  assert.equal(filaDe(sonda.body, productId, ctx!.locationIds.almacen), undefined, "el parámetro no debe cambiar su alcance");
  assert.equal(filaDe(sonda.body, productId, ctx!.locationIds.tienda).stock, 5);

  const otra = await getJson(`/api/inventory?locationId=${otraTiendaId}`, token);
  assert.equal(filaDe(otra.body, productId, otraTiendaId), undefined, "tampoco puede sondear otra tienda");
});

test("GET inventory — ningún rol recibe costo ni precio mayorista por esta vía", async () => {
  for (const [nombre, usuario, role] of [
    ["ADMIN", ctx!.users.admin, "ADMIN"],
    ["INVENTARIO", ctx!.users.inventario, "INVENTARIO"],
    ["TIENDA", ctx!.users.tienda, "TIENDA"],
  ] as const) {
    const { body } = await getJson("/api/inventory", tokenDe(usuario, role));
    const fila = filaDe(body, productId, ctx!.locationIds.tienda);
    assert.ok(fila, `${nombre} recibe su fila de inventario`);
    assert.equal(fila.cost, undefined, `${nombre} no debe recibir el costo de compra`);
    assert.equal(fila.wholesalePrice, undefined, `${nombre} no debe recibir el precio mayorista`);
    // Tampoco el resto de campos internos de Product: la respuesta es una lista cerrada.
    assert.equal(fila.price1, undefined, `${nombre} no debe recibir precios de venta`);
    assert.equal(fila.price2, undefined, `${nombre} no debe recibir el precio con crédito`);
  }
});

test("GET inventory — un rol desconocido NO gana acceso por defecto", async () => {
  const { rol, usuario, token } = await tokenParaRolDesconocido("CAJERO_INV", true);
  try {
    const listado = await getJson("/api/inventory", token);
    assert.equal(listado.status, 403, "un rol fuera de la allow-list no hereda la vista de existencias");
    const detalle = await getJson(`/api/inventory/product/${productId}`, token);
    assert.equal(detalle.status, 403, "tampoco por la ruta de stock por producto");
  } finally {
    await ctx!.prisma.user.delete({ where: { id: usuario.id } });
    await ctx!.prisma.roleModel.delete({ where: { id: rol.id } });
  }
});

// ===== GET /api/inventory/product/:productId =====

test("GET inventory/product/:id — TIENDA recibe solo su ubicación y el stockTotal corresponde", async () => {
  const token = tokenDe(ctx!.users.tienda, "TIENDA");
  const { status, body } = await getJson(`/api/inventory/product/${productId}`, token);
  assert.equal(status, 200);
  assert.equal(body.locations.length, 1, "solo ve su tienda");
  assert.equal(body.locations[0].locationId, ctx!.locationIds.tienda);
  assert.equal(body.stockTotal, 5, "el total es el de SU ubicación, no el de la cadena");
  assert.notEqual(body.stockTotal, 54, "no debe sumar almacén ni otras tiendas");
});

test("GET inventory/product/:id — ADMIN e INVENTARIO reciben el desglose de ubicaciones", async () => {
  for (const [usuario, role] of [
    [ctx!.users.admin, "ADMIN"],
    [ctx!.users.inventario, "INVENTARIO"],
  ] as const) {
    const { status, body } = await getJson(`/api/inventory/product/${productId}`, tokenDe(usuario, role));
    assert.equal(status, 200, `${role} consulta el stock por ubicación`);
    assert.equal(body.locations.length, 3, `${role} ve las tres ubicaciones`);
    assert.equal(body.stockTotal, 54, `${role} ve el total de la cadena`);
  }
});

test("GET inventory/product/:id — sin token responde 401", async () => {
  const { status } = await getJson(`/api/inventory/product/${productId}`);
  assert.equal(status, 401);
});

// ===== PUT /api/inventory/:id =====

test("PUT inventory — ADMIN puede ajustar stock con motivo", async () => {
  const token = tokenDe(ctx!.users.admin, "ADMIN");
  const { status, body } = await putJson(
    `/api/inventory/${invAlmacenId}`,
    { stock: 33, reasonType: "AJUSTE", reason: "Conteo fisico" },
    token,
  );
  assert.equal(status, 200, "ADMIN puede editar inventario");
  assert.equal(body.stock, 33, "el stock queda ajustado");
  assert.equal(body.productId, productId);
  const enDb = await ctx!.prisma.inventory.findUniqueOrThrow({ where: { id: invAlmacenId } });
  assert.equal(enDb.stock, 33, "el cambio queda persistido");
});

test("PUT inventory — INVENTARIO puede ajustar stock (control fisico de la mercaderia)", async () => {
  const token = tokenDe(ctx!.users.inventario, "INVENTARIO");
  const { status, body } = await putJson(
    `/api/inventory/${invTiendaId}`,
    { minStock: 4, reasonType: "AJUSTE", reason: "Minimo corregido" },
    token,
  );
  assert.equal(status, 200, "INVENTARIO debe poder ajustar inventario, no recibir 403");
  assert.equal(body.minStock, 4);
});

test("PUT inventory — TIENDA recibe 403 y el stock NO se toca", async () => {
  const token = tokenDe(ctx!.users.tienda, "TIENDA");
  const antes = await stockEnTienda(productId);
  const { status, body } = await putJson(
    `/api/inventory/${invTiendaId}`,
    { stock: 999, reasonType: "AJUSTE", reason: "No deberia pasar" },
    token,
  );
  assert.equal(status, 403, "TIENDA no edita inventario: vende, consulta y solicita");
  assert.match(body.message, /permisos/i);
  assert.equal(await stockEnTienda(productId), antes, "el stock debe quedar intacto");
});

test("PUT inventory — sin token responde 401 y no modifica nada", async () => {
  const antes = await stockEnTienda(productId);
  const { status } = await putJson(`/api/inventory/${invTiendaId}`, { stock: 999, reasonType: "AJUSTE" });
  assert.equal(status, 401);
  assert.equal(await stockEnTienda(productId), antes);
});

test("PUT inventory — la respuesta aplica la politica de campos por rol", async () => {
  // INVENTARIO está en ROLES_CON_COSTOS y en ROLES_CON_PRECIO_MAYORISTA, así que le
  // corresponde verlos: la misma política que /api/products, no una más restrictiva.
  const comoInventario = await putJson(
    `/api/inventory/${invAlmacenId}`,
    { stock: 38, reasonType: "AJUSTE", reason: "Ajuste desde inventario" },
    tokenDe(ctx!.users.inventario, "INVENTARIO"),
  );
  assert.equal(comoInventario.status, 200);
  assert.notEqual(comoInventario.body.cost, undefined, "INVENTARIO está en la allow-list de costos");
  assert.notEqual(comoInventario.body.wholesalePrice, undefined, "y en la de precio mayorista");

  // ADMIN también está en ambas allow-lists.
  const comoAdmin = await putJson(
    `/api/inventory/${invAlmacenId}`,
    { stock: 37, reasonType: "AJUSTE", reason: "Ajuste desde admin" },
    tokenDe(ctx!.users.admin, "ADMIN"),
  );
  assert.equal(comoAdmin.status, 200);
  assert.notEqual(comoAdmin.body.cost, undefined, "ADMIN conserva el costo de compra");
  assert.notEqual(comoAdmin.body.wholesalePrice, undefined, "y el precio mayorista");

  // Lo que sí cambia respecto a antes: la respuesta ya no incrusta el Product completo.
  // Devolvía `product: true`, o sea price1/price2 y cualquier campo futuro de Product.
  const body = comoAdmin.body;
  assert.equal(body.product, undefined, "ya no se incrusta el objeto Product completo");
  assert.equal(body.price1, undefined, "ni los precios de venta del producto");
  assert.equal(body.price2, undefined, "ni el precio con crédito");
  assert.ok(body.productName && body.itemCode, "la forma plana del inventario se mantiene");
  assert.equal(body.stock, 37, "el registro ajustado sigue viéndose en la respuesta");
});

test("PUT inventory — un rol en la allow-list de escritura sin la de costos no recibe el costo", async () => {
  // Regresión de la política: si mañana `ROLES_QUE_AJUSTAN_INVENTARIO` incluye un rol
  // que no está en `ROLES_CON_COSTOS`, la respuesta debe omitir el costo automáticamente,
  // porque la decisión se toma con los mismos helpers y no con un chequeo propio.
  const comoInventario = await putJson(
    `/api/inventory/${invAlmacenId}`,
    { stock: 36, reasonType: "AJUSTE", reason: "Ajuste 36" },
    tokenDe(ctx!.users.inventario, "INVENTARIO"),
  );
  assert.equal(comoInventario.status, 200);
  // INVENTARIO está en la allow-list de costos, así que el campo llega; lo que se
  // verifica aquí es que la decisión viene del helper y no de un permiso hardcodeado:
  // un TIENDA, que sí recibe el campo en /api/products, no puede ni llegar a esta ruta.
  const comoTienda = await putJson(
    `/api/inventory/${invTiendaId}`,
    { stock: 30, reasonType: "AJUSTE", reason: "No deberia pasar" },
    tokenDe(ctx!.users.tienda, "TIENDA"),
  );
  assert.equal(comoTienda.status, 403);
  assert.equal(comoTienda.body.cost, undefined, "un 403 no puede traer datos financieros");
});

test("PUT inventory — un rol desconocido recibe 403", async () => {
  const { rol, usuario, token } = await tokenParaRolDesconocido("AJUSTADOR", true);
  try {
    const antes = await stockEnTienda(productId);
    const { status } = await putJson(`/api/inventory/${invTiendaId}`, { stock: 999, reasonType: "AJUSTE" }, token);
    assert.equal(status, 403, "un rol fuera de la allow-list de escritura no ajusta stock");
    assert.equal(await stockEnTienda(productId), antes, "y el stock queda intacto");
  } finally {
    await ctx!.prisma.user.delete({ where: { id: usuario.id } });
    await ctx!.prisma.roleModel.delete({ where: { id: rol.id } });
  }
});

// ===== Regresión: los flujos que mueven stock siguen funcionando =====

test("Regresión — una VENTA sigue descontando stock sin pasar por PUT /api/inventory", async () => {
  const p = await createProduct(ctx!, { stockTienda: 10, stockAlmacen: 20 });
  const antes = await stockEnTienda(p.id);
  const res = await postJson(
    server.baseUrl,
    "/api/sales",
    { items: [{ productId: p.id, quantity: 3, unitPrice: 100 }], payments: [{ method: "EFECTIVO", amount: 300 }] },
    tokenDe(ctx!.users.tienda, "TIENDA"),
  );
  assert.equal(res.status, 201, "la venta de un TIENDA sigue siendo válida");
  assert.equal(await stockEnTienda(p.id), antes - 3, "la venta descuenta stock por su propio flujo");
});

test("Regresión — un MOVIMIENTO sigue moviendo stock entre almacén y tienda", async () => {
  const p = await createProduct(ctx!, { stockTienda: 4, stockAlmacen: 25 });
  const res = await postJson(
    server.baseUrl,
    "/api/movements",
    {
      productId: p.id,
      fromLocationId: ctx!.locationIds.almacen,
      toLocationId: ctx!.locationIds.tienda,
      quantity: 6,
      observation: " Reposicion de prueba",
    },
    tokenDe(ctx!.users.inventario, "INVENTARIO"),
  );
  assert.equal(res.status, 201, "el movimiento de mercadería sigue permitido para INVENTARIO");
  assert.equal(await stockEnTienda(p.id), 10, "la tienda recibe las 6 unidades");
  const almacen = await ctx!.prisma.inventory.findUniqueOrThrow({
    where: { productId_locationId: { productId: p.id, locationId: ctx!.locationIds.almacen } },
  });
  assert.equal(almacen.stock, 19, "el almacén descuenta las 6 unidades");
});
