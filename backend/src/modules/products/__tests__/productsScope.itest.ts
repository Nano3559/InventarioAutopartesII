import { test, before, after, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { startTestServer, mintTestToken, TestServer } from "../../../testing/helpers";
import { seed, cleanup, createProduct, SeedContext } from "../../../testing/seed";

/**
 * A1/A2 — Aislamiento de información financiera y de stock en /api/products.
 *
 * Antes de este cambio, `GET /api/products` y `GET /api/products/:id` devolvían el
 * costo de compra a cualquier usuario autenticado (incluido TIENDA) y el listado
 * calculaba `stock` sumando TODAS las ubicaciones, de modo que un TIENDA obtenía la
 * disponibilidad de la cadena y podía sondear otra tienda con ?locationId.
 *
 * Además estas rutas eran ANÓNIMAS (`optionalAuth`): sin token devolvían el stock global
 * y permitían enumerar cualquier sede. Se cerraron porque no hay consumidor anónimo
 * legítimo (el catálogo público es /api/public/*), así que ahora exigen token.
 *
 * `wholesalePrice` pasó de "cualquier usuario autenticado" a una allow-list por rol
 * (`ROLES_CON_PRECIO_MAYORISTA`), ver shared/utils/scope.ts.
 */

let server: TestServer;
let ctx: SeedContext | null = null;
let productId = 0;
let otraTiendaId = 0;

/**
 * Sufijo único por corrida. Los correos de los usuarios que crea esta suite son únicos
 * (varias de estas pruebas generan el mismo prefijo): si una corrida anterior falló antes
 * de borrar su usuario, reutilizar el correo haría fallar el `create` por la restricción
 * de unicidad y el error escondería lo que la prueba realmente verifica.
 */
const runId = Math.random().toString(36).slice(2, 8);

const getJson = async (ruta: string, token?: string): Promise<{ status: number; body: any }> => {
  const res = await fetch(`${server.baseUrl}${ruta}`, {
    headers: token ? { authorization: `Bearer ${token}` } : {},
  });
  return { status: res.status, body: await res.json() };
};

/**
 * Token de un usuario del seed, emitido directamente en vez de por /api/auth/login.
 * Esta suite hace muchos POST de login y el endpoint tiene rate limit por IP: al superarlo
 * devolvería 429 y la prueba fallaría por el límite, no por el alcance que verifica.
 */
const tokenDe = (u: { email: string; userId: number; locationId: number | null }, role: string) =>
  mintTestToken({ userId: u.userId, email: u.email, role, locationId: u.locationId });

before(async () => {
  server = await startTestServer();
});

beforeEach(async () => {
  if (!ctx) {
    ctx = await seed("products-scope");
    // El seed de test solo crea un almacén y una tienda, así que se agrega una segunda
    // tienda para poder comprobar que un TIENDA no sondea el stock de otra.
    const otra = await ctx.prisma.location.create({
      data: { name: `TIENDA2-${ctx.ns}`, type: "TIENDA", address: "Zona Test 2" },
    });
    otraTiendaId = otra.id;

    // 3 en la tienda del usuario, 40 en almacén y 7 en la otra tienda: la suma global
    // (50) y el valor real de su tienda (3) deben ser distinguibles en el test.
    const p = await createProduct(ctx, { stockTienda: 3, stockAlmacen: 40 });
    productId = p.id;
    await ctx.prisma.inventory.create({
      data: { productId: p.id, locationId: otra.id, stock: 7, minStock: 1 },
    });
  }
});

after(async () => {
  if (ctx) {
    // Borramos la tienda adicional solo si no hay inventarios que la referencian.
    // Si hay error, la corrida continúa y no affecta al resto.
    try {
      await ctx.prisma.location.deleteMany({ where: { id: otraTiendaId } });
    } catch {
      // ignore - location may have dependents; test still valid
    }
    await cleanup(ctx);
  }
  await server.close();
});

test("A1 — un TIENDA NO recibe el costo de compra en el listado", async () => {
  const token = tokenDe(ctx!.users.tienda, "TIENDA");
  const { body } = await getJson("/api/products?limit=100", token);
  const item = body.products.find((p: any) => p.id === productId);
  assert.ok(item, "el producto sembrado debe aparecer en el listado");
  assert.equal(item.cost, undefined, "TIENDA no debe recibir el costo de compra");
  assert.ok(item.price1 !== undefined, "TIENDA sí necesita el precio de venta");
});

test("A1 — un TIENDA NO recibe el costo de compra en el detalle", async () => {
  const token = tokenDe(ctx!.users.tienda, "TIENDA");
  const { body } = await getJson(`/api/products/${productId}`, token);
  assert.equal(body.cost, undefined, "TIENDA no debe recibir el costo de compra en el detalle");
});

test("A1 — ADMIN e INVENTARIO siguen recibiendo el costo (no se rompe el panel)", async () => {
  const admin = tokenDe(ctx!.users.admin, "ADMIN");
  const comoAdmin = await getJson(`/api/products/${productId}`, admin);
  assert.equal(comoAdmin.body.cost !== undefined, true, "ADMIN debe seguir viendo el costo");

  const inv = tokenDe(ctx!.users.inventario, "INVENTARIO");
  const comoInv = await getJson(`/api/products/${productId}`, inv);
  assert.equal(comoInv.body.cost !== undefined, true, "INVENTARIO debe seguir viendo el costo");
});

test("A2 — un TIENDA recibe solo el stock de SU tienda, no la suma de la cadena", async () => {
  const token = tokenDe(ctx!.users.tienda, "TIENDA");
  const { body } = await getJson("/api/products?limit=100", token);
  const item = body.products.find((p: any) => p.id === productId);
  assert.equal(item.stock, 3, "el stock debe ser el de su tienda (3), no la suma global (50)");
});

test("A2 — ?locationId de otra tienda no se aplica a un TIENDA (no hay oráculo de stock)", async () => {
  const token = tokenDe(ctx!.users.tienda, "TIENDA");
  const conParametro = await getJson(`/api/products?locationId=${otraTiendaId}&limit=100`, token);
  const sinParametro = await getJson("/api/products?limit=100", token);
  const conFiltro: any = conParametro.body.products.find((p: any) => p.id === productId);
  const sinFiltro: any = sinParametro.body.products.find((p: any) => p.id === productId);
  assert.equal(conFiltro.stock, sinFiltro.stock, "el parámetro de otra tienda no debe cambiar el stock devuelto");
  assert.equal(conFiltro.stock, 3);
});

test("A2 — ADMIN sigue viendo el stock global y puede filtrar por ubicación", async () => {
  const token = tokenDe(ctx!.users.admin, "ADMIN");
  const { body } = await getJson("/api/products?limit=100", token);
  const item = body.products.find((p: any) => p.id === productId);
  assert.equal(item.stock, 50, "ADMIN sigue viendo la suma de todas las ubicaciones");

  const filtrado = await getJson(`/api/products?locationId=${ctx!.locationIds.almacen}&limit=100`, token);
  const soloAlmacen: any = filtrado.body.products.find((p: any) => p.id === productId);
  assert.equal(soloAlmacen.stock, 40, "ADMIN puede seguir filtrando por una ubicación concreta");
});

test("A2 — un TIENDA sin ubicación asignada recibe 403 en lugar de la vista global", async () => {
  const tienda = await ctx!.prisma.user.findUniqueOrThrow({ where: { id: ctx!.users.tienda.userId } });
  const usuario = await ctx!.prisma.user.create({
    data: {
      email: `sin-tienda-${runId}-${ctx!.ns}@test.com`,
      // La contraseña se hashea en el seed con el mismo PASSWORD de los demás usuarios.
      password: tienda.password,
      name: "Vendedor Sin Tienda",
      roleId: tienda.roleId,
      locationId: null,
    },
  });
  const token = mintTestToken({ userId: usuario.id, email: usuario.email, role: "TIENDA", locationId: null });
  const { status, body } = await getJson("/api/products?limit=100", token);
  assert.equal(status, 403, "sin tienda asignada no puede caer en la vista global de stock");
  assert.match(body.message, /tienda asignada/i);
  await ctx!.prisma.user.delete({ where: { id: usuario.id } });
});

test("El catálogo INTERNO /api/products ya NO es anónimo: sin token responde 401", async () => {
  // Se comprobó que no existe consumidor anónimo legítimo: los 9 llamadores del panel web
  // y del móvil están protegidos, y el catálogo público usa /api/public/products.
  const listado = await getJson("/api/products?limit=100");
  assert.equal(listado.status, 401, "el listado interno exige autenticación");
  assert.equal(listado.body.products, undefined, "no debe filtrar catálogo sin token");

  const detalle = await getJson(`/api/products/${productId}`);
  assert.equal(detalle.status, 401, "el detalle interno exige autenticación");
  assert.equal(detalle.body.stock, undefined, "no debe filtrar existencias sin token");

  const filtros = await getJson("/api/products/filters");
  assert.equal(filtros.status, 401, "el enumerado de filtros interno exige autenticación");
  assert.equal(filtros.body.brands, undefined, "no debe filtrar el catálogo interno sin token");
});

test("El catálogo PÚBLICO /api/public/products sigue funcionando SIN token", async () => {
  const { status, body } = await getJson("/api/public/products?limit=100");
  assert.equal(status, 200, "el catálogo público no puede romperse: es el flujo anónimo del sitio");
  assert.ok(Array.isArray(body.products), "el catálogo público sigue devolviendo productos");
  // Y mantiene su contrato seguro: sin costos, sin stock exacto y sin ubicaciones.
  const raw = JSON.stringify(body);
  assert.ok(!raw.includes('"cost"'), "el público nunca recibe el costo de compra");
  assert.ok(!raw.includes('"stockTotal"'), "el público nunca recibe el stock total");
  assert.ok(!raw.includes('"stockByLocation"'), "el público nunca recibe el stock por ubicación");
});

test("El detalle público /api/public/products/:id sigue funcionando SIN token", async () => {
  const { status, body } = await getJson(`/api/public/products/${productId}`);
  assert.equal(status, 200, "el detalle público no puede romperse");
  assert.ok(body.id, "devuelve el producto");
  assert.equal(body.cost, undefined, "nunca incluye el costo de compra");
});

// ===== wholesalePrice: allow-list por rol, no "cualquier autenticado" =====

test("wholesalePrice — ADMIN recibe el precio mayorista", async () => {
  const token = tokenDe(ctx!.users.admin, "ADMIN");
  const listado = await getJson("/api/products?limit=100", token);
  const detalle = await getJson(`/api/products/${productId}`, token);
  const item = listado.body.products.find((p: any) => p.id === productId);
  assert.notEqual(item.wholesalePrice, undefined, "ADMIN gestiona la venta mayorista y lo necesita");
  assert.notEqual(detalle.body.wholesalePrice, undefined, "y también en el detalle");
});

test("wholesalePrice — TIENDA lo recibe porque la venta mayorista lo consume", async () => {
  // WholesalePage.tsx:113 usa `p.wholesalePrice || p.price1` para el carrito y el servidor
  // cobra `wholesalePrice ?? price1`; sin el campo el total del carrito no coincidiría.
  const token = tokenDe(ctx!.users.tienda, "TIENDA");
  const listado = await getJson("/api/products?limit=100", token);
  const detalle = await getJson(`/api/products/${productId}`, token);
  const item = listado.body.products.find((p: any) => p.id === productId);
  assert.notEqual(item.wholesalePrice, undefined, "TIENDA alcanza /panel/ventas-mayor y necesita el precio");
  assert.notEqual(detalle.body.wholesalePrice, undefined, "y también en el detalle");
});

test("wholesalePrice — INVENTARIO lo recibe porque edita el precio en el formulario", async () => {
  // InventoryPage.tsx:592 y ProductDetailPage.tsx:245 son inputs editables sin gate de rol.
  const token = tokenDe(ctx!.users.inventario, "INVENTARIO");
  const detalle = await getJson(`/api/products/${productId}`, token);
  assert.notEqual(detalle.body.wholesalePrice, undefined, "el formulario de producto necesita leerlo para no borrarlo");
});

test("Allow-list — un rol desconocido NO recibe wholesalePrice (listado ni detalle)", async () => {
  const { rol, usuario, token } = await tokenParaRolDesconocido("CAJERO_MAYOR", true);
  try {
    const listado = await getJson("/api/products?limit=100", token);
    const detalle = await getJson(`/api/products/${productId}`, token);
    const item = listado.body.products.find((p: any) => p.id === productId);
    assert.equal(item.wholesalePrice, undefined, "un rol no autorizado no recibe el precio mayorista");
    assert.equal(detalle.body.wholesalePrice, undefined, "tampoco en el detalle");
  } finally {
    await ctx!.prisma.user.delete({ where: { id: usuario.id } });
    await ctx!.prisma.roleModel.delete({ where: { id: rol.id } });
  }
});

// ===== Allow-list: un rol futuro/desconocido no recibe datos financieros por defecto =====
//
// El nombre del rol viene de RoleModel.name, una tabla data-driven editable desde el
// panel. Con el patrón anterior (`!esTienda`) cualquier rol que no se llamara TIENDA
// caía del lado permitido y recibía el costo de compra de toda la cadena.

/**
 * Crea un usuario con un rol nuevo y devuelve su token.
 *
 * El token se emite directamente (no con /api/auth/login) porque el login tiene rate
 * limit por IP y esta suite ya crea varios usuarios: al superarlo devolvería 429 y la
 * prueba fallaría por el límite, no por el alcance que verifica.
 */
async function tokenParaRolDesconocido(nombreRol: string, conUbicacion: boolean) {
  const tienda = await ctx!.prisma.user.findUniqueOrThrow({ where: { id: ctx!.users.tienda.userId } });
  const rol = await ctx!.prisma.roleModel.create({ data: { name: nombreRol } });
  const usuario = await ctx!.prisma.user.create({
    data: {
      email: `rol-${nombreRol.toLowerCase()}-${runId}-${ctx!.ns}@test.com`,
      password: tienda.password,
      name: `Usuario ${nombreRol}`,
      roleId: rol.id,
      locationId: conUbicacion ? ctx!.locationIds.tienda : null,
    },
  });
  const token = mintTestToken({
    userId: usuario.id,
    email: usuario.email,
    role: nombreRol,
    locationId: usuario.locationId,
  });
  return { rol, usuario, token };
}

test("Allow-list — un rol desconocido NO recibe el costo de compra en el listado", async () => {
  const { rol, usuario, token } = await tokenParaRolDesconocido("CAJERO", true);
  try {
    const { body } = await getJson("/api/products?limit=100", token);
    const item = body.products.find((p: any) => p.id === productId);
    assert.ok(item, "el usuario con rol nuevo debe poder listar productos");
    assert.equal(item.cost, undefined, "un rol no autorizado no debe recibir el costo de compra");
  } finally {
    await ctx!.prisma.user.delete({ where: { id: usuario.id } });
    await ctx!.prisma.roleModel.delete({ where: { id: rol.id } });
  }
});

test("Allow-list — un rol desconocido NO recibe el costo de compra en el detalle", async () => {
  const { rol, usuario, token } = await tokenParaRolDesconocido("VENDEDOR", true);
  try {
    const { body } = await getJson(`/api/products/${productId}`, token);
    assert.equal(body.cost, undefined, "el detalle tampoco debe filtrar el costo a un rol desconocido");
  } finally {
    await ctx!.prisma.user.delete({ where: { id: usuario.id } });
    await ctx!.prisma.roleModel.delete({ where: { id: rol.id } });
  }
});

test("Allow-list — un rol desconocido con ubicación ve el stock de SU ubicación, no el global", async () => {
  const { rol, usuario, token } = await tokenParaRolDesconocido("REPORTERO", true);
  try {
    const { body } = await getJson("/api/products?limit=100", token);
    const item = body.products.find((p: any) => p.id === productId);
    assert.equal(item.stock, 3, "queda acotado a su ubicación, no a la suma global (50)");
    // Y no puede usarla para sondear otra ubicación.
    const sondeadora = await getJson(`/api/products?locationId=${otraTiendaId}&limit=100`, token);
    const filtrado = sondeadora.body.products.find((p: any) => p.id === productId);
    assert.equal(filtrado.stock, 3, "no debe poder ampliar su alcance con ?locationId");
  } finally {
    await ctx!.prisma.user.delete({ where: { id: usuario.id } });
    await ctx!.prisma.roleModel.delete({ where: { id: rol.id } });
  }
});

test("Allow-list — un rol desconocido SIN ubicación no cae en la vista global de stock", async () => {
  const { rol, usuario, token } = await tokenParaRolDesconocido("MOSTRADOR", false);
  try {
    const { status, body } = await getJson("/api/products?limit=100", token);
    assert.equal(status, 403, "sin ubicación no debe ver el stock de ninguna tienda");
    assert.equal(body.products, undefined, "no debe devolver catálogo con stock global");
  } finally {
    await ctx!.prisma.user.delete({ where: { id: usuario.id } });
    await ctx!.prisma.roleModel.delete({ where: { id: rol.id } });
  }
});
