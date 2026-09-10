import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { startTestServer, TestServer, postJson, jsonHeaders, loginAndGetToken } from "../../../testing/helpers";
import { seed, cleanup, SeedContext } from "../../../testing/seed";

/**
 * ETAPA 6 — Autenticación y permisos:
 *  - R6.1 Login válido
 *  - R6.2 Login inválido
 *  - R6.3 Permisos ADMIN
 *  - R6.4 Permisos TIENDA
 *  - R6.5 Permisos INVENTARIO
 */

let server: TestServer;
let ctx: SeedContext;
let tiendaToken: string;
let inventarioToken: string;

before(async () => {
  ctx = await seed("auth");
  server = await startTestServer();
  tiendaToken = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, ctx.users.tienda.password);
  inventarioToken = await loginAndGetToken(server.baseUrl, ctx.users.inventario.email, ctx.users.inventario.password);
});

after(async () => {
  await cleanup(ctx);
  await server.close();
});

test("R6.1 — login válido responde 200 con token y perfil del usuario", async () => {
  const res = await postJson(server.baseUrl, "/api/auth/login", {
    email: ctx.users.tienda.email,
    password: ctx.users.tienda.password,
  });
  assert.equal(res.status, 200);
  const body: any = await res.json();
  assert.ok(body.token && typeof body.token === "string");
  assert.equal(body.user.email, ctx.users.tienda.email);
  assert.equal(body.user.role, "TIENDA");
  assert.equal(body.user.locationId, ctx.locationIds.tienda);
});

test("R6.2 — login inválido responde 401 (password incorrecta) y 400 (datos faltantes)", async () => {
  const wrongPassword = await postJson(server.baseUrl, "/api/auth/login", {
    email: ctx.users.admin.email,
    password: "password-incorrecta",
  });
  assert.equal(wrongPassword.status, 401);
  const wrongBody: any = await wrongPassword.json();
  assert.equal(wrongBody.message, "Credenciales inválidas");

  const unknownUser = await postJson(server.baseUrl, "/api/auth/login", {
    email: "nadie.auth@itest.local",
    password: "cualquiera",
  });
  assert.equal(unknownUser.status, 401);

  const missingFields = await postJson(server.baseUrl, "/api/auth/login", { email: ctx.users.admin.email });
  assert.equal(missingFields.status, 400);
});

test("R6.3 — permisos ADMIN: acceso a movimientos y a ventas", async () => {
  const token = await loginAndGetToken(server.baseUrl, ctx.users.admin.email, ctx.users.admin.password);

  const movements = await fetch(`${server.baseUrl}/api/movements`, { headers: jsonHeaders(token) });
  assert.equal(movements.status, 200, "ADMIN tiene acceso al módulo movimientos");
  const movBody: any = await movements.json();
  assert.ok(Array.isArray(movBody.movements));

  // La lista de ventas es 200 para ADMIN (no 403/401).
  const sales = await fetch(`${server.baseUrl}/api/sales`, { headers: jsonHeaders(token) });
  assert.equal(sales.status, 200, "ADMIN tiene acceso a ventas");
});

test("R6.4 — permisos TIENDA: sin acceso a movimientos, sí a ventas", async () => {
  const movements = await fetch(`${server.baseUrl}/api/movements`, { headers: jsonHeaders(tiendaToken) });
  assert.equal(movements.status, 403, "TIENDA no tiene permiso del módulo movimientos");
  const movBody: any = await movements.json();
  assert.equal(movBody.message, "No tiene acceso al módulo: movimientos");

  const sales = await fetch(`${server.baseUrl}/api/sales`, { headers: jsonHeaders(tiendaToken) });
  assert.equal(sales.status, 200, "TIENDA sí accede a ventas");
});

test("R6.5 — permisos INVENTARIO: acceso a movimientos, bloqueado en ventas", async () => {
  const movements = await fetch(`${server.baseUrl}/api/movements`, { headers: jsonHeaders(inventarioToken) });
  assert.equal(movements.status, 200, "INVENTARIO tiene permiso del módulo movimientos");

  const sales = await fetch(`${server.baseUrl}/api/sales`, { headers: jsonHeaders(inventarioToken) });
  assert.equal(sales.status, 403, "INVENTARIO no está autorizado en ventas");
  const salesBody: any = await sales.json();
  assert.equal(salesBody.message, "No tiene permisos para esta acción");
});