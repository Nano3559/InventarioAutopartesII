import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { startTestServer, TestServer } from "../../../testing/helpers";

/**
 * J3 — Flujo de búsqueda por imagen (punto a punto automatizable):
 *  - J3.1  El endpoint público POST /api/public/search-image funciona SIN token.
 *  - J3.2  El endpoint interno POST /api/products/search-image exige token (401 anónimo e inválido).
 *  - J3.3  Los errores de subida del endpoint público se responden 400 (no 401) y nunca ejecutan OCR.
 *  - J3.8  Los límites de MIME y tamaño aplican también en el flujo HTTP real (público anónimo).
 * (La validación OCR con foto real Exposición/cámara queda como validación manual requerida.)
 */

let server: TestServer;

before(async () => {
  server = await startTestServer();
});

after(async () => {
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