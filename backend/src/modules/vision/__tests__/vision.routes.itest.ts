import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import bcrypt from "bcryptjs";
import { PrismaClient } from "@prisma/client";
import { startTestServer, TestServer, loginAndGetToken } from "../../../testing/helpers";
import { seed, cleanup, SeedContext } from "../../../testing/seed";

/**
 * Búsqueda por visión (rotas /api/vision, modo mock):
 *  - Público: /api/vision/public/detectar sin token, respuestas seguras (sin
 *    price2/stockTotal/stockPorSucursal), 400/422/429/504 coherentes.
 *  - Interno: /api/vision/detectar exige token; TIENDA sin ubicación → 403;
 *    TIENDA con ubicación ve SOLO su sucursal; ADMIN ve stock global exacto.
 *  - Escenarios mock: default (Frenos 0.94), ninguna, baja_confianza,
 *    categoria_desconocida, error, timeout.
 *  - Límite de 5 detecciones públicas y 20 internas por usuario (limiter).
 */

let server: TestServer;
let ctx: SeedContext;
let categoriaFrenosId: number;
let categoryCreada = false;

let adminToken: string;
let tiendaToken: string;
let tiendaSinUbicacionToken: string;

const PASSWORD = "TestPassword123!";

const FRENO_HILUX = { itemCode: "VISION-FRENO-HILUX", brand: "Toyota", model: "Hilux", year: "2020-2024", price1: 250000, price2: 200000, stockTienda: 5, stockAlmacen: 100 };
const FRENO_COROLLA = { itemCode: "VISION-FRENO-COROLLA", brand: "Toyota", model: "Corolla", year: "2018", price1: 200000, price2: 160000, stockTienda: 12 };
const FRENO_AVEO = { itemCode: "VISION-FRENO-AVEO", brand: "Chevrolet", model: "Aveo", year: "2015", price1: 180000, price2: 140000, stockTienda: 5 };
const SIN_CATEGORIA = { itemCode: "VISION-SIN-CATEGORIA", brand: "Toyota", model: "Hilux", year: "2020-2024", price1: 300000, price2: 240000, stockTienda: 3, stockAlmacen: 7 };

let productIds: number[] = [];

function fdConImagen(scenario?: string, vehiculo?: { marca?: string; modelo?: string; anio?: string }): { fd: FormData; headers: Record<string, string> } {
  const fd = new FormData();
  fd.append("image", new Blob([Buffer.from("foto simulada de una pieza")], { type: "image/jpeg" }), "pieza.jpg");
  const headers: Record<string, string> = {};
  if (scenario) headers["x-vision-mock-scenario"] = scenario;
  if (vehiculo) {
    if (vehiculo.marca) fd.append("vehiculoMarca", vehiculo.marca);
    if (vehiculo.modelo) fd.append("vehiculoModelo", vehiculo.modelo);
    if (vehiculo.anio) fd.append("vehiculoAnio", vehiculo.anio);
  }
  return { fd, headers };
}

before(async () => {
  server = await startTestServer();
  ctx = await seed("vision");

  const categoria = await ctx.prisma.category.findFirst({ where: { name: "Frenos" } });
  if (categoria) {
    categoriaFrenosId = categoria.id;
  } else {
    const creada = await ctx.prisma.category.create({ data: { name: "Frenos" } });
    categoriaFrenosId = creada.id;
    categoryCreada = true;
  }

  const crear = async (p: { itemCode: string; brand: string; model: string; year: string; price1: number; price2: number; stockTienda?: number; stockAlmacen?: number }, categoryId: number | null) => {
    const product = await ctx.prisma.product.create({
      data: {
        itemCode: p.itemCode,
        manufacturer: "TEST-vision",
        name: `Producto visión ${p.itemCode}`,
        brand: p.brand,
        model: p.model,
        year: p.year,
        detail: "Producto para pruebas de visión",
        price1: p.price1,
        price2: p.price2,
        wholesalePrice: Math.round(p.price1 * 0.8 * 100) / 100,
        cost: Math.round(p.price1 * 0.5 * 100) / 100,
        categoryId,
      },
    });
    const rows: { productId: number; locationId: number; stock: number; minStock: number }[] = [];
    if ("stockTienda" in p) rows.push({ productId: product.id, locationId: ctx.locationIds.tienda, stock: (p as any).stockTienda, minStock: 1 });
    if ("stockAlmacen" in p) rows.push({ productId: product.id, locationId: ctx.locationIds.almacen, stock: (p as any).stockAlmacen, minStock: 1 });
    if (rows.length > 0) await ctx.prisma.inventory.createMany({ data: rows });
    return product.id;
  };

  productIds.push(await crear(FRENO_HILUX, categoriaFrenosId));
  productIds.push(await crear(FRENO_COROLLA, categoriaFrenosId));
  productIds.push(await crear(FRENO_AVEO, categoriaFrenosId));
  productIds.push(await crear(SIN_CATEGORIA, null));

  adminToken = await loginAndGetToken(server.baseUrl, ctx.users.admin.email, PASSWORD);
  tiendaToken = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, PASSWORD);

  const hash = await bcrypt.hash(PASSWORD, 10);
  const sinUbicacion = await ctx.prisma.user.create({
    data: {
      name: "Vendedor sin ubicación",
      email: "tienda.noloc.vision@itest.local",
      password: hash,
      roleId: ctx.roleIds.tienda,
      locationId: null,
    },
  });
  tiendaSinUbicacionToken = await loginAndGetToken(server.baseUrl, sinUbicacion.email, PASSWORD);
});

after(async () => {
  await ctx.prisma.user.deleteMany({ where: { email: "tienda.noloc.vision@itest.local" } });
  await cleanup(ctx);
  if (categoryCreada) {
    const p = new PrismaClient();
    await p.category.deleteMany({ where: { id: categoriaFrenosId } });
    await p.$disconnect();
  }
  await server.close();
});

// ===== Público (exactamente 5 llamadas para no tocar el límite de 5/15min) =====

test("público: sin imagen → 400 VISION_IMAGEN_REQUERIDA", async () => {
  const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST" });
  assert.equal(res.status, 400);
  const body: any = await res.json();
  assert.equal(body.codigo, "VISION_IMAGEN_REQUERIDA");
  assert.equal(body.message, "Debe subir una imagen");
});

test("público: MIME no permitido → 400 (multer)", async () => {
  const fd = new FormData();
  fd.append("image", new Blob([Buffer.from("no soy imagen")], { type: "text/plain" }), "pieza.jpg");
  const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", body: fd });
  assert.equal(res.status, 400);
  const body: any = await res.json();
  assert.equal(body.message, "Tipo de archivo no permitido");
});

test("público: detección válida 200 con serialización SEGURA (sin price2/stockTotal/stockPorSucursal)", async () => {
  const { fd, headers } = fdConImagen(undefined, { marca: "Toyota", modelo: "Hilux", anio: "2020" });
  const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", headers, body: fd });
  assert.equal(res.status, 200);
  const body: any = await res.json();

  assert.equal(body.version, "1.0");
  assert.equal(body.proveedor, "mock");
  assert.equal(body.deteccion.categoria, "Frenos");
  assert.equal(body.deteccion.categoriaMapeada, "Frenos");
  assert.equal(body.categoriaCatalogo.nombre, "Frenos");
  assert.equal(body.deteccion.vehiculo === undefined, true); // vehiculo va a nivel raíz

  const raw = JSON.stringify(body);
  assert.ok(!raw.includes('"price2"'), "nunca expone price2");
  assert.ok(!raw.includes('"stockTotal"'), "nunca expone stockTotal");
  assert.ok(!raw.includes('"stockPorSucursal"'), "nunca expone stockPorSucursal");

  const hilux = body.candidatos.find((c: any) => c.itemCode === FRENO_HILUX.itemCode);
  assert.ok(hilux, "candidato Hilux presente");
  assert.equal(hilux.compatibilidad.verificada, true, "Hilux verifica contra Toyota/Hilux/2020");

  assert.deepEqual(body.vehiculo, { marca: "Toyota", modelo: "Hilux", anio: "2020" });
  assert.equal(body.compatibilidad.consultada, true);
  assert.equal(new Set(body.entrega.modalidades).size, 2);

  const sinCategoria = body.candidatos.find((c: any) => c.itemCode === SIN_CATEGORIA.itemCode);
  assert.equal(sinCategoria, undefined, "producto sin categoría queda excluido");

  const hiluxDisponibilidad = hilux.disponibilidadPorSucursal;
  assert.ok(hiluxDisponibilidad.every((s: any) => typeof s.nivel === "string"), "nivel por sucursal público");
  assert.ok(hiluxDisponibilidad.every((s: any) => typeof s.stock === "undefined"), "nunca cantidad por sucursal");
});

test("público: confianza baja → 422 VISION_BAJA_CONFIANZA", async () => {
  const { fd, headers } = fdConImagen("baja_confianza");
  const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", headers, body: fd });
  assert.equal(res.status, 422);
  const body: any = await res.json();
  assert.equal(body.codigo, "VISION_BAJA_CONFIANZA");
});

test("público: sin clasificación (ninguna) → 422 VISION_NO_CLASIFICADA", async () => {
  const { fd, headers } = fdConImagen("ninguna");
  const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", headers, body: fd });
  assert.equal(res.status, 422);
  const body: any = await res.json();
  assert.equal(body.codigo, "VISION_NO_CLASIFICADA");
});

// El límite público es 5/15 min por IP: arriba ya se hicieron exactamente 5 peticiones
// públicas (400, 400, 200, 422, 422), así que la 6.ª debe responder 429.
// NOTA: node:test ejecuta los tests en orden dentro del archivo; no reordenar.
test("público: alcanzado el límite de 5/15 min por IP → 429", async () => {
  const { fd, headers } = fdConImagen();
  const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", headers, body: fd });
  assert.equal(res.status, 429);
  const body: any = await res.json();
  assert.equal(body.status, 429);
  assert.ok(body.message, "mensaje de límite presente");
});

// ===== Interno =====

test("interno: exige token (401 anónimo e inválido)", async () => {
  const anon = await fetch(`${server.baseUrl}/api/vision/detectar`, { method: "POST" });
  assert.equal(anon.status, 401);
  const anonBody: any = await anon.json();
  assert.equal(anonBody.message, "Token no proporcionado");

  const invalido = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { authorization: "Bearer token-invalido" },
  });
  assert.equal(invalido.status, 401);
  const invalidoBody: any = await invalido.json();
  assert.equal(invalidoBody.message, "Token inválido o expirado");
});

test("interno: TIENDA sin ubicación asignada → 403", async () => {
  const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { authorization: `Bearer ${tiendaSinUbicacionToken}` },
  });
  assert.equal(res.status, 403);
  const body: any = await res.json();
  assert.equal(body.message, "Usuario TIENDA sin ubicación asignada");
});

test("interno: detección válida 200 con stock exacto y price2 (ADMIN ve global)", async () => {
  const { fd, headers } = fdConImagen();
  const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { ...headers, authorization: `Bearer ${adminToken}` },
    body: fd,
  });
  assert.equal(res.status, 200);
  const body: any = await res.json();

  const hilux = body.candidatos.find((c: any) => c.itemCode === FRENO_HILUX.itemCode);
  assert.ok(hilux, "candidato Hilux presente");
  assert.equal(hilux.price2, 200000, "price2 visible en modo interno");
  assert.equal(hilux.stockTotal, FRENO_HILUX.stockTienda + FRENO_HILUX.stockAlmacen, "stock total exacto");
  assert.equal(hilux.stockPorSucursal.length, 2, "dos sucursales (tienda + almacén)");

  const hiluxSuc = hilux.stockPorSucursal.find((s: any) => s.locationId === ctx.locationIds.tienda);
  assert.equal(hiluxSuc.stock, FRENO_HILUX.stockTienda);

  const sinUbic = body.candidatos.find((c: any) => c.itemCode === SIN_CATEGORIA.itemCode);
  assert.equal(sinUbic, undefined, "producto sin categoría excluido en modo interno también");

  assert.equal(body.compatibilidad.consultada, true);
  assert.match(body.compatibilidad.nota, /Sin vehículo/);
});

test("interno: TIENDA con ubicación ve SOLO su sucursal (stock total propio)", async () => {
  const { fd, headers } = fdConImagen();
  const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { ...headers, authorization: `Bearer ${tiendaToken}` },
    body: fd,
  });
  assert.equal(res.status, 200);
  const body: any = await res.json();

  const hilux = body.candidatos.find((c: any) => c.itemCode === FRENO_HILUX.itemCode);
  assert.ok(hilux, "candidato Hilux presente");
  assert.equal(hilux.stockTotal, FRENO_HILUX.stockTienda, "TIENDA solo suma su propia ubicación");
  assert.equal(hilux.stockPorSucursal.length, 1);
  assert.equal(hilux.stockPorSucursal[0].locationId, ctx.locationIds.tienda);
});

test("interno: caso mapa de categoria inexistente → 200 con candidatos vacíos y nota", async () => {
  const { fd, headers } = fdConImagen("categoria_desconocida");
  const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { ...headers, authorization: `Bearer ${adminToken}` },
    body: fd,
  });
  assert.equal(res.status, 200);
  const body: any = await res.json();
  assert.equal(body.deteccion.categoriaMapeada, null);
  assert.equal(body.candidatos.length, 0);
  assert.equal(body.nota, "La clase detectada no tiene categoría equivalente en el catálogo.");
  assert.ok(body.entrega.sucursales.length > 0, "lista de sucursales disponible");
});

test("interno: IA no disponible → 503 VISION_NO_DISPONIBLE", async () => {
  const { fd, headers } = fdConImagen("error");
  const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { ...headers, authorization: `Bearer ${adminToken}` },
    body: fd,
  });
  assert.equal(res.status, 503);
  const body: any = await res.json();
  assert.equal(body.codigo, "VISION_NO_DISPONIBLE");
});

test("interno: timeout → 504 VISION_TIMEOUT", async () => {
  const { fd, headers } = fdConImagen("timeout");
  const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { ...headers, authorization: `Bearer ${adminToken}` },
    body: fd,
  });
  assert.equal(res.status, 504);
  const body: any = await res.json();
  assert.equal(body.codigo, "VISION_TIMEOUT");
});

test("interno: archivo > 5 MB → 400 antes de consultar al proveedor", async () => {
  const fd = new FormData();
  fd.append("image", new Blob([Buffer.alloc(5 * 1024 * 1024 + 1)], { type: "image/jpeg" }), "grande.jpg");
  const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { authorization: `Bearer ${adminToken}` },
    body: fd,
  });
  assert.equal(res.status, 400);
  const body: any = await res.json();
  assert.equal(body.message, "El archivo excede el tamaño máximo permitido");
});

test("interno: campo de vehículo con longitud excesiva → 400 VISION_REQUEST_INVALIDO", async () => {
  const fd = new FormData();
  fd.append("image", new Blob([Buffer.from("foto")], { type: "image/jpeg" }), "pieza.jpg");
  fd.append("vehiculoMarca", "T".repeat(200));
  const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { authorization: `Bearer ${adminToken}` },
    body: fd,
  });
  assert.equal(res.status, 400);
  const body: any = await res.json();
  assert.equal(body.codigo, "VISION_REQUEST_INVALIDO");
});