import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import bcrypt from "bcryptjs";
import { startTestServer, TestServer, jsonHeaders, loginAndGetToken } from "../../../testing/helpers";
import { seed, cleanup, SeedContext } from "../../../testing/seed";
import { invalidateRoleCache } from "../auth";

/**
 * ETAPA 8 — Caché de permisos de authorizeModule.
 *
 * Usa un ROL DEDICADO por namespace (TEST-CACHE-<ns>) para no mutar los roles
 * compartidos (ADMIN/TIENDA/INVENTARIO) que otros itest leen.
 *
 * Secuencia:
 *  1. El rol entra a la caché con permiso "movimientos" → GET /api/movements = 200.
 *  2. Se retira el permiso por fuera del path de invalidación (write directo a BD).
 *     La caché aún sirve los permisos previos (TTL) → sigue siendo 200.
 *  3. invalidateRoleCache(roleId) → la siguiente petición recarga desde BD → 403.
 */
const NS = "permcache";
const ROLE_NAME = `TEST-CACHE-${NS}`;

let server: TestServer;
let ctx: SeedContext;
let roleId: number;
let userId: number;
let email: string;
const password = "CachePass123!";

before(async () => {
  ctx = await seed(NS);
  server = await startTestServer();

  const role = await ctx.prisma.roleModel.upsert({
    where: { name: ROLE_NAME },
    update: { permissions: ["movimientos"] },
    create: { name: ROLE_NAME, permissions: ["movimientos"] },
  });
  roleId = role.id;

  const user = await ctx.prisma.user.create({
    data: {
      name: `Cache ${NS}`,
      email: `cache.${NS.toLowerCase()}@itest.local`,
      password: await bcrypt.hash(password, 10),
      roleId,
    },
  });
  userId = user.id;
  email = user.email;
});

after(async () => {
  await ctx.prisma.user.delete({ where: { id: userId } }).catch(() => undefined);
  await ctx.prisma.roleModel
    .delete({ where: { id: roleId } })
    .catch(() => undefined);
  await cleanup(ctx);
  await server.close();
});

test("E8-cache — el permiso del rol dedicado entra a la caché y permite movimientos", async () => {
  const token = await loginAndGetToken(server.baseUrl, email, password);
  const res = await fetch(`${server.baseUrl}/api/movements`, { headers: jsonHeaders(token) });
  assert.equal(res.status, 200, "rol con movimientos en caché accede al módulo");
});

test("E8-cache — sin invalidación: el cambio de permisos se refleja con TTL (caché sirve el snapshot)", async () => {
  const token = await loginAndGetToken(server.baseUrl, email, password);

  // Cambio por fuera del flujo de invalidación (simula script/migración/otra instancia).
  await ctx.prisma.roleModel.update({ where: { id: roleId }, data: { permissions: [] } });

  // Dentro del TTL la caché sigue sirviendo los permisos que conoce → aún 200.
  const resCached = await fetch(`${server.baseUrl}/api/movements`, { headers: jsonHeaders(token) });
  assert.equal(resCached.status, 200, "caché mantiene el snapshot de permisos dentro del TTL");

  // Invalidación explícita → recarga desde BD y el acceso cae.
  invalidateRoleCache(roleId);
  const resAfterInvalidation = await fetch(`${server.baseUrl}/api/movements`, { headers: jsonHeaders(token) });
  assert.equal(resAfterInvalidation.status, 403, "tras invalidar, el rol sin movimiento es rechazado");
  const body: any = await resAfterInvalidation.json();
  assert.equal(body.message, "No tiene acceso al módulo: movimientos");

  // Restaura el permiso para no dejar el rol mutado si otro test vuelve a usarlo.
  await ctx.prisma.roleModel.update({
    where: { id: roleId },
    data: { permissions: ["movimientos"] },
  });
  invalidateRoleCache(roleId);
});