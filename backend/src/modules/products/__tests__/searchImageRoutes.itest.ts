import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { startTestServer, loginAndGetToken, TestServer } from "../../../testing/helpers";
import { seed, cleanup, SeedContext } from "../../../testing/seed";

/**
 * J3 — Flujo de búsqueda por imagen (punto a punto automatizable):
 *  - J3.1  El endpoint público POST /api/public/search-image funciona SIN token.
 *  - J3.2  El endpoint interno POST /api/products/search-image exige token (401 anónimo e inválido).
 *  - J3.3  Los errores de subida del endpoint público se responden 400 (no 401) y nunca ejecutan OCR.
 *  - J3.8  Los límites de MIME y tamaño aplican también en el flujo HTTP real (público anónimo).
 * (La validación OCR con foto real Exposición/cámara queda como validación manual requerida.)
 */

let server: TestServer;
let ctx: SeedContext | null = null;
let ctx2: SeedContext | null = null;

before(async () => {
  server = await startTestServer();
});

after(async () => {
  if (ctx) await cleanup(ctx);
  if (ctx2) await cleanup(ctx2);
  await server.close();
});

test("J3.1 — POST /api/public/search-image responde sin token (400 'Debe subir una imagen', nunca 401)", async () => {
  const res = await fetch(`${server.baseUrl}/api/public/search-image`, { method: "POST" });
  assert.equal(res.status, 400, "El endpoint público debe ser alcanzable sin token");
  const body: any = await res.json();
  assert.equal(body.message, "Debe subir una imagen");
});

test("J3.2 — POST /api/products/search-image exige token: 401 anónimo e inválido", async () => {
  const anon = await fetch(`${server.baseUrl}/api/products/search-image`, { method: "POST" });
  assert.equal(anon.status, 401);
  const anonBody: any = await anon.json();
  assert.equal(anonBody.message, "Token no proporcionado");

  const invalid = await fetch(`${server.baseUrl}/api/products/search-image`, {
    method: "POST",
    headers: { authorization: "Bearer token-invalido-abc123" },
  });
  assert.equal(invalid.status, 401);
  const invalidBody: any = await invalid.json();
  assert.equal(invalidBody.message, "Token inválido o expirado");
});

test("J3.3 — archivo inválido en la ruta pública anónima responde 400 (multer antes de OCR)", async () => {
  const fd = new FormData();
  fd.append("image", new Blob([Buffer.from("no soy una imagen")], { type: "text/plain" }), "noticia.jpg");
  const res = await fetch(`${server.baseUrl}/api/public/search-image`, { method: "POST", body: fd });
  assert.equal(res.status, 400);
  const body: any = await res.json();
  assert.equal(body.message, "Tipo de archivo no permitido");
});

test("J3.8 — límite de 5 MB aplica en el endpoint público anónimo (400 antes de OCR)", async () => {
  const fd = new FormData();
  fd.append("image", new Blob([Buffer.alloc(5 * 1024 * 1024 + 1)], { type: "image/jpeg" }), "grande.jpg");
  const res = await fetch(`${server.baseUrl}/api/public/search-image`, { method: "POST", body: fd });
  assert.equal(res.status, 400);
  const body: any = await res.json();
  assert.equal(body.message, "El archivo excede el tamaño máximo permitido");
});

test("Aislamiento OCR — un TIENDA sin ubicación asignada recibe 403 antes de multer/OCR", async () => {
  // requireTiendaLocation va tras authenticate y antes del limiter, del upload y del
  // handler: sin ubicación no se puede acotar el stock, así que se rechaza. Al ir
  // antes de multer, la respuesta es 403 y no el 400 de "Debe subir una imagen".
  ctx = await seed("search-image-scope");
  await ctx.prisma.user.update({ where: { id: ctx.users.tienda.userId }, data: { locationId: null } });
  const token = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, ctx.users.tienda.password);

  const res = await fetch(`${server.baseUrl}/api/products/search-image`, {
    method: "POST",
    headers: { authorization: `Bearer ${token}` },
  });
  assert.equal(res.status, 403, "un TIENDA sin ubicación no debe poder usar la búsqueda por imagen");
  const body: any = await res.json();
  assert.match(body.message, /ubicación/i);
});

test("Aislamiento OCR — un TIENDA con ubicación no recibe 403 (el scope se aplica en la serialización)", async () => {
  ctx2 = await seed("search-image-scope-ok");
  const token = await loginAndGetToken(server.baseUrl, ctx2.users.tienda.email, ctx2.users.tienda.password);

  // Sin archivo la ruta responde 400 (llegó al handler), no 403: la autorización
  // por ubicación dejó pasar al usuario con tienda asignada.
  const res = await fetch(`${server.baseUrl}/api/products/search-image`, {
    method: "POST",
    headers: { authorization: `Bearer ${token}` },
  });
  assert.equal(res.status, 400);
  const body: any = await res.json();
  assert.equal(body.message, "Debe subir una imagen");
});