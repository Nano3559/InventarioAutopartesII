import { test, before, after } from "node:test";
import assert from "node:assert/strict";
// IMPORTANTE: `helpers` debe ser el primer import del proyecto. Importarlo antes
// de `@prisma/client` hace que este último cargue el `.env` (Neon remoto) y el
// guardián de `assertLocalTestUrl` aborta la suite. Los imports reales van
// después a propósito.
import { startTestServer, TestServer, loginAndGetToken, fakeIa } from "../../../testing/helpers";
import { seed, cleanup, SeedContext } from "../../../testing/seed";
import type { EscenarioIa } from "../../../testing/fakeIaServer";
import bcrypt from "bcryptjs";
import { PrismaClient } from "@prisma/client";

/**
 * Búsqueda por visión (rotas /api/vision) contra un `ia-service` real:
 *  - Público: /api/vision/public/detectar sin token, respuestas seguras (sin
 *    price2/stockTotal/stockPorSucursal), 400/422/504 coherentes.
 *  - Interno: /api/vision/detectar exige token; TIENDA sin ubicación → 403;
 *    TIENDA con ubicación ve SOLO su sucursal; ADMIN ve stock global exacto.
 *  - El proveedor es SIEMPRE HTTP real: los escenarios (default con Frenos 0.94,
 *    ninguna, baja_confianza, categoria_desconocida, caida, timeout, clave
 *    incorrecta) se configuran en el doble `src/testing/fakeIaServer`, nunca con
 *    una detección inventada en el runtime.
 *  - Sin limiter propio de visión: 12 detecciones públicas consecutivas → todas
 *    200, ninguna 429 (queda solo el `generalLimiter` global de 300/15 min).
 */

let server: TestServer;
let ctx: SeedContext;
let categoriaFrenosId: number;
let categoryCreada = false;

let adminToken: string;
let tiendaToken: string;
let tiendaSinUbicacionToken: string;
let tiendaBToken: string;
let tiendaBId = 0;

const PASSWORD = "TestPassword123!";

const FRENO_HILUX = { itemCode: "VISION-FRENO-HILUX", brand: "Toyota", model: "Hilux", year: "2020-2024", price1: 250000, price2: 200000, stockTienda: 5, stockAlmacen: 100 };
const FRENO_COROLLA = { itemCode: "VISION-FRENO-COROLLA", brand: "Toyota", model: "Corolla", year: "2018", price1: 200000, price2: 160000, stockTienda: 12 };
const FRENO_AVEO = { itemCode: "VISION-FRENO-AVEO", brand: "Chevrolet", model: "Aveo", year: "2015", price1: 180000, price2: 140000, stockTienda: 5 };
const SIN_CATEGORIA = { itemCode: "VISION-SIN-CATEGORIA", brand: "Toyota", model: "Hilux", year: "2020-2024", price1: 300000, price2: 240000, stockTienda: 3, stockAlmacen: 7 };

let productIds: number[] = [];

function fdConImagen(vehiculo?: { marca?: string; modelo?: string; anio?: string }): { fd: FormData } {
  const fd = new FormData();
  fd.append("image", new Blob([Buffer.from("bytes de una foto de una pieza")], { type: "image/jpeg" }), "pieza.jpg");
  if (vehiculo) {
    if (vehiculo.marca) fd.append("vehiculoMarca", vehiculo.marca);
    if (vehiculo.modelo) fd.append("vehiculoModelo", vehiculo.modelo);
    if (vehiculo.anio) fd.append("vehiculoAnio", vehiculo.anio);
  }
return { fd };
}

/**
 * Fija el comportamiento del doble de `ia-service` para la siguiente petición y
 * vuelve al escenario por defecto al terminar.
 *
 * Antes esto viajaba en un header `x-vision-mock-scenario` que solo tenía efecto
 * con el proveedor simulado. Como el runtime ya no tiene proveedor simulado, el
 * escenario se decide aquí, en el test, modulando el servidor HTTP real.
 */
async function conEscenarioIa<T>(escenario: EscenarioIa, fn: () => Promise<T>): Promise<T> {
  const ia = await fakeIa();
  ia.setEscenario(escenario);
  try {
    return await fn();
  } finally {
    ia.setEscenario("default");
  }
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

  // Segunda tienda, para comprobar el aislamiento entre ubicaciones: TIENDA A no debe
  // ver la disponibilidad de TIENDA B ni del almacén.
  const tiendaB = await ctx.prisma.location.create({
    data: { name: `TIENDA-B-${ctx.ns}`, type: "TIENDA" },
  });
  tiendaBId = tiendaB.id;

  // 77 unidades en TIENDA B: un valor que no coincide con ninguna otra ubicación, para
  // que cualquier contaminación en la respuesta sea evidente.
  await ctx.prisma.inventory.createMany({
    data: productIds.slice(0, 3).map((productId) => ({ productId, locationId: tiendaB.id, stock: 77, minStock: 1 })),
  });

  const usuarioTiendaB = await ctx.prisma.user.create({
    data: {
      name: "Vendedor tienda B",
      email: "tienda.b.vision@itest.local",
      password: hash,
      roleId: ctx.roleIds.tienda,
      locationId: tiendaB.id,
    },
  });
  tiendaBToken = await loginAndGetToken(server.baseUrl, usuarioTiendaB.email, PASSWORD);
});

after(async () => {
  await ctx.prisma.user.deleteMany({ where: { email: { in: ["tienda.noloc.vision@itest.local", "tienda.b.vision@itest.local"] } } });
  await cleanup(ctx);
  if (categoryCreada) {
    const p = new PrismaClient();
    await p.category.deleteMany({ where: { id: categoriaFrenosId } });
    await p.$disconnect();
  }
  await server.close();
});

// ===== Público =====

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

test("público: multipart real en el campo 'image' llega a multer (req.file presente)", async () => {
  // Regresión 400 "Debe subir una imagen": el cliente debe enviar el archivo
  // como multipart en la clave `image`. Aquí se valida el contrato completo,
  // incluidos los bytes reales del archivo (no solo el status).
  const jpeg = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0xff, 0xd9]);
  const fd = new FormData();
  fd.append("image", new Blob([jpeg], { type: "image/jpeg" }), "captura.jpg");

  const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", body: fd });

  // Si multer no vio el archivo, la respuesta sería 400 VISION_IMAGEN_REQUERIDA.
  assert.notEqual(res.status, 400, "el archivo en el campo 'image' no debe producir 400");
  const body: any = await res.json();
  assert.notEqual(body.codigo, "VISION_IMAGEN_REQUERIDA");
  // El proveedor real/fake recibió la imagen: la petición llegó más allá de multer.
  assert.equal(body.proveedor, "http");
  assert.ok(body.deteccion, "el proveedor devolvió una detección a partir de los bytes recibidos");
});

test("público: body JSON serializado no cuenta como imagen → 400 VISION_IMAGEN_REQUERIDA", async () => {
  // Documenta por qué el cliente NO debe enviar el FormData como
  // `Content-Type: application/json`: en ese caso los bytes se pierden.
  const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: {} }),
  });
  assert.equal(res.status, 400);
  const body: any = await res.json();
  assert.equal(body.codigo, "VISION_IMAGEN_REQUERIDA");
});

test("público: el campo multipart debe llamarse exactamente 'image'", async () => {
  // Contrato único: con otro nombre de campo multer rechaza la petición
  // (LIMIT_UNEXPECTED_FILE) y el handler nunca ve un archivo.
  const jpeg = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0xff, 0xd9]);
  const fd = new FormData();
  fd.append("archivo", new Blob([jpeg], { type: "image/jpeg" }), "captura.jpg");

  const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", body: fd });
  assert.equal(res.status, 400, "un campo distinto de 'image' no puede llegar al proveedor");
  const body: any = await res.json();
  assert.notEqual(body.codigo, "VISION_IMAGEN_REQUERIDA");
});

test("público: detección válida 200 con serialización SEGURA (sin price2/stockTotal/stockPorSucursal)", async () => {
  const { fd } = fdConImagen({ marca: "Toyota", modelo: "Hilux", anio: "2020" });
  const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", body: fd });
  assert.equal(res.status, 200);
  const body: any = await res.json();

  assert.equal(body.version, "1.0");
  assert.equal(body.proveedor, "http");
  assert.equal(body.deteccion.categoria, "Frenos");
  assert.equal(body.deteccion.categoriaMapeada, "Frenos");
  assert.equal(body.categoriaCatalogo.nombre, "Frenos");
  assert.equal(body.deteccion.vehiculo === undefined, true); // vehiculo va a nivel raíz

  const raw = JSON.stringify(body);
  assert.ok(!raw.includes('"price2"'), "nunca expone price2");
  assert.ok(!raw.includes('"stockTotal"'), "nunca expone stockTotal");
  assert.ok(!raw.includes('"stockPorSucursal"'), "nunca expone stockPorSucursal");
  assert.ok(!raw.includes('"wholesalePrice"'), "nunca expone precio mayorista");
  assert.ok(!raw.includes('"cost"'), "nunca expone costo");
  assert.ok(!raw.includes('"minStock"'), "nunca expone stock mínimo");

  const hilux = body.candidatos.find((c: any) => c.itemCode === FRENO_HILUX.itemCode);
  assert.ok(hilux, "candidato Hilux presente");
  assert.equal(hilux.compatibilidad.verificada, true, "Hilux verifica contra Toyota/Hilux/2020");

  assert.deepEqual(body.vehiculo, { marca: "Toyota", modelo: "Hilux", anio: "2020" });
  assert.equal(body.compatibilidad.consultada, true);
  assert.equal(new Set(body.entrega.modalidades).size, 2);

  const sinCategoria = body.candidatos.find((c: any) => c.itemCode === SIN_CATEGORIA.itemCode);
  assert.equal(sinCategoria, undefined, "producto sin categoría queda excluido");

  // La disponibilidad agregada sigue siendo SOLO el bucket; el desglose interno
  // (`disponibilidadPorSucursal` con `locationId`/`tipo`/`etiqueta`) nunca viaja.
  assert.ok(typeof hilux.disponibilidad.nivel === "string", "el público sí recibe el bucket de disponibilidad");
  assert.deepEqual(hilux.disponibilidadPorSucursal, [], "el público nunca recibe el desglose interno por sede");

  // El desglose PÚBLICO usa el DTO mínimo (`disponibilidadPorSucursalPublica`):
  // solo sucursales TIENDA y solo sucursalId + nombre + nivel.
  assert.ok(Array.isArray(hilux.disponibilidadPorSucursalPublica), "el público recibe el desglose seguro por sede");
  assert.equal(hilux.disponibilidadPorSucursalPublica.length, 2, "dos sucursales TIENDA (A y B)");
  const idsPublicos = hilux.disponibilidadPorSucursalPublica.map((s: any) => s.sucursalId);
  assert.ok(idsPublicos.includes(ctx.locationIds.tienda), "incluye TIENDA A (stock 5)");
  assert.ok(idsPublicos.includes(tiendaBId), "incluye TIENDA B (stock 77)");
  assert.equal(idsPublicos.includes(ctx.locationIds.almacen), false, "el almacén nunca es punto de recogida público");

  const tiendaAPublica = hilux.disponibilidadPorSucursalPublica.find((s: any) => s.sucursalId === ctx.locationIds.tienda);
  assert.equal(tiendaAPublica.nivel, "POCAS_UNIDADES", "stock 5 → bucket 'Pocas unidades', jamás la cifra");
  const tiendaBPublica = hilux.disponibilidadPorSucursalPublica.find((s: any) => s.sucursalId === tiendaBId);
  assert.equal(tiendaBPublica.nivel, "DISPONIBLE", "stock 77 → bucket 'Disponible', jamás la cifra");

  for (const s of hilux.disponibilidadPorSucursalPublica) {
    assert.deepEqual(Object.keys(s).sort(), ["nivel", "nombre", "sucursalId"], "DTO público mínimo sin internals");
    assert.equal(s.stock, undefined, `${s.nombre}: sin stock`);
    assert.equal(s.locationId, undefined, `${s.nombre}: sin locationId`);
    assert.equal(s.tipo, undefined, `${s.nombre}: sin tipo`);
    assert.equal(s.minStock, undefined, `${s.nombre}: sin minStock`);
  }

  // Red de seguridad: ningún candidato público puede traer identificadores de sede.
  for (const cand of body.candidatos) {
    assert.equal(cand.locationId, undefined, `${cand.itemCode}: sin locationId`);
    assert.equal(cand.nombre, undefined, `${cand.itemCode}: sin nombre de sede a nivel raíz`);
    assert.equal(cand.tipo, undefined, `${cand.itemCode}: sin tipo de sede`);
    assert.ok(!JSON.stringify(cand).includes(`"locationId"`), `${cand.itemCode}: sin locationId en el JSON`);
  }
});

test("público: confianza baja → 422 VISION_BAJA_CONFIANZA", async () => {
  await conEscenarioIa("baja_confianza", async () => {
    const { fd } = fdConImagen();
    const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", body: fd });
    assert.equal(res.status, 422);
    const body: any = await res.json();
    assert.equal(body.codigo, "VISION_BAJA_CONFIANZA");
    // Baja confianza es el caso donde más ayuda al usuario: explica cómo mejorar la foto.
    assert.ok(Array.isArray(body.recomendaciones) && body.recomendaciones.length > 0, "baja confianza debe recomendar cómo capturar");
  });
});

test("público: el contrato híbrido expone evidences de OCR sin romper nada previo", async () => {
  const { fd } = fdConImagen({ marca: "Toyota", modelo: "Hilux", anio: "2020" });
  const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", body: fd });
  assert.equal(res.status, 200);
  const body: any = await res.json();

  // Evidencia OCR a nivel de detección: siempre presente, puede venir vacía.
  assert.ok(Array.isArray(body.deteccion.textoDetectado), "textoDetectado siempre es un arreglo");
  assert.ok(Array.isArray(body.deteccion.codigosDetectados), "codigosDetectados siempre es un arreglo");

  // Evidencia por candidato: score + trazabilidad. 0 significa "sin evidencia".
  for (const cand of body.candidatos) {
    assert.equal(typeof cand.scoreEvidencia, "number", `${cand.itemCode}: scoreEvidencia numérico`);
    assert.ok(Array.isArray(cand.evidencias), `${cand.itemCode}: evidencias es un arreglo`);
    for (const ev of cand.evidencias) {
      assert.ok(["oemCode", "factoryCode", "itemCode"].includes(ev.campo), "campo de evidencia válido");
      assert.ok(["exacta", "parcial"].includes(ev.tipo), "tipo de evidencia válido");
      assert.equal(typeof ev.peso, "number");
      assert.ok(!("verificada" in ev), "la evidencia OCR nunca declara compatibilidad verificada");
    }
  }
});

test("público: la evidencia de código no puede cambiar una compatibilidad no verificada", async () => {
  const { fd } = fdConImagen({ marca: "Toyota", modelo: "Hilux", anio: "2020" });
  const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", body: fd });
  const body: any = await res.json();

  // Aunque un candidato acumule evidencia de código, `verificada` solo depende de
  // marca/modelo/año contra el catálogo. Es la garantía de que no se inventa
  // compatibilidad a partir de un texto leído con OCR.
  for (const cand of body.candidatos) {
    if (cand.scoreEvidencia > 0) {
      const marca = cand.brand?.toLowerCase() ?? "";
      const modelo = cand.model?.toLowerCase() ?? "";
      const coincide = marca.includes("toyota") && modelo.includes("hilux");
      if (!coincide) {
        assert.equal(cand.compatibilidad.verificada, false, `${cand.itemCode}: evidencia sin verificación de vehículo`);
      }
    }
  }
});

test("público: sin clasificación (ninguna) → 422 VISION_NO_CLASIFICADA", async () => {
  await conEscenarioIa("ninguna", async () => {
    const { fd } = fdConImagen();
    const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", body: fd });
    assert.equal(res.status, 422);
    const body: any = await res.json();
    assert.equal(body.codigo, "VISION_NO_CLASIFICADA");
    // Recomendaciones de captura: el 422 debe decir CÓMO tomar la foto, no solo
    // que falló. Sin esto el usuario no sabe qué corregir.
    assert.ok(Array.isArray(body.recomendaciones), "el 422 debe incluir recomendaciones");
    assert.ok(body.recomendaciones.length >= 3, "debe incluir varias recomendaciones accionables");
    assert.ok(body.recomendaciones.every((r: unknown) => typeof r === "string" && r.length > 0));
  });
});

// El flujo público NO tiene limiter propio: 12 detecciones seguidas deben responder
// 200 con resultado normal, sin 429. Con el antiguo límite de 5/15 min esta prueba
// fallaba en la 6.ª llamada, que era exactamente el bloqueo que prolijó durante la demo.
//
// NOTA sobre `proveedor`: esta suite habla con un `ia-service` real (el doble de
// `src/testing/fakeIaServer`) por HTTP, igual que producción, así que cada respuesta
// debe declarar `proveedor: "http"`. Lo que se verifica aquí es que la cuota de visión
// ya no bloquea el flujo; que la respuesta nunca sea una detección simulada lo
// comprueban `vision.provider.test.ts` y `vision.config.test.ts`.
// NOTA: node:test ejecuta los tests en orden dentro del archivo; no reordenar.
test("público: 12 detecciones consecutivas sin 429 (solo el generalLimiter global)", async () => {
  const TOTAL = 12;
  for (let i = 1; i <= TOTAL; i++) {
    const { fd } = fdConImagen();
    const res = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", body: fd });
    assert.notEqual(res.status, 429, `la detección ${i} de ${TOTAL} no debe recibir 429`);
    assert.equal(res.status, 200, `la detección ${i} de ${TOTAL} debe responder 200`);
    const body: any = await res.json();
    assert.equal(body.proveedor, "http", `la detección ${i} declara proveedor http`);
    assert.ok(Array.isArray(body.candidatos), `la detección ${i} devuelve candidatos`);
    assert.equal(body.deteccion.categoria, "Frenos", `la detección ${i} devuelve un resultado real`);
  }
});

// El flujo interno tampoco lleva limiter por usuario: 12 detecciones seguidas con el
// mismo token deben responder 200 y seguir viendo price2/stockTotal (ámbito ADMIN).
test("interno: 12 detecciones consecutivas con el mismo token sin 429", async () => {
  const TOTAL = 12;
  for (let i = 1; i <= TOTAL; i++) {
    const { fd } = fdConImagen();
    const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
      method: "POST",
      headers: { authorization: `Bearer ${adminToken}` },
      body: fd,
    });
    assert.notEqual(res.status, 429, `la detección interna ${i} de ${TOTAL} no debe recibir 429`);
    assert.equal(res.status, 200, `la detección interna ${i} de ${TOTAL} debe responder 200`);
    const body: any = await res.json();
    const hilux = body.candidatos.find((c: any) => c.itemCode === FRENO_HILUX.itemCode);
    assert.ok(hilux, `la detección interna ${i} devuelve el candidato Hilux`);
    assert.equal(hilux.price2, FRENO_HILUX.price2, `la detección interna ${i} mantiene price2`);
  }
});

// El límite de tamaño y el MIME siguen aplicándose en el flujo público ahora que ya no
// hay quota que los de preceda: 5 MB + 1 y MIME text/plain deben seguir rechazados.
test("público: las validaciones de upload siguen activas tras quitar el limiter", async () => {
  const mimeInvalido = new FormData();
  mimeInvalido.append("image", new Blob([Buffer.from("no soy imagen")], { type: "text/plain" }), "pieza.jpg");
  const resMime = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", body: mimeInvalido });
  assert.equal(resMime.status, 400, "MIME inválido sigue rechazándose con 400");
  assert.equal((await resMime.json() as any).message, "Tipo de archivo no permitido");

  const grande = new FormData();
  grande.append("image", new Blob([Buffer.alloc(5 * 1024 * 1024 + 1)], { type: "image/jpeg" }), "grande.jpg");
  const resGrande = await fetch(`${server.baseUrl}/api/vision/public/detectar`, { method: "POST", body: grande });
  assert.equal(resGrande.status, 400, "el archivo > 5 MB sigue rechazándose con 400");
  assert.equal((await resGrande.json() as any).message, "El archivo excede el tamaño máximo permitido");
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
  const { fd } = fdConImagen();
  const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { authorization: `Bearer ${adminToken}` },
    body: fd,
  });
  assert.equal(res.status, 200);
  const body: any = await res.json();

  const hilux = body.candidatos.find((c: any) => c.itemCode === FRENO_HILUX.itemCode);
  assert.ok(hilux, "candidato Hilux presente");
  assert.equal(hilux.price2, 200000, "price2 visible en modo interno");
  // TIENDA A + almacén + TIENDA B (creada en el `before` para las pruebas de aislamiento).
  assert.equal(hilux.stockTotal, FRENO_HILUX.stockTienda + FRENO_HILUX.stockAlmacen + 77, "stock total exacto");
  assert.equal(hilux.stockPorSucursal.length, 3, "tres sucursales (tienda A + almacén + tienda B)");

  const hiluxSuc = hilux.stockPorSucursal.find((s: any) => s.locationId === ctx.locationIds.tienda);
  assert.equal(hiluxSuc.stock, FRENO_HILUX.stockTienda);

  const sinUbic = body.candidatos.find((c: any) => c.itemCode === SIN_CATEGORIA.itemCode);
  assert.equal(sinUbic, undefined, "producto sin categoría excluido en modo interno también");

  assert.equal(body.compatibilidad.consultada, true);
  assert.match(body.compatibilidad.nota, /Sin vehículo/);
});

test("interno: TIENDA con ubicación ve SOLO su sucursal (stock total propio)", async () => {
  const { fd } = fdConImagen();
  const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { authorization: `Bearer ${tiendaToken}` },
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

// El leaks original: `disponibilidad` y `disponibilidadPorSucursal` se arrastraban
// calculadas sobre el stock GLOBAL (el spread de `serializarPublico`), así que acotar
// solo `stockTotal` seguía dejando ver que había existencias en otras tiendas.
test("Aislamiento visión — TIENDA A no recibe disponibilidad de TIENDA B ni del almacén", async () => {
  const { fd } = fdConImagen();
  const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { authorization: `Bearer ${tiendaToken}` },
    body: fd,
  });
  assert.equal(res.status, 200);
  const body: any = await res.json();

  for (const codigo of [FRENO_HILUX.itemCode, FRENO_COROLLA.itemCode, FRENO_AVEO.itemCode]) {
    const cand = body.candidatos.find((c: any) => c.itemCode === codigo);
    assert.ok(cand, `candidato ${codigo} presente`);

    // No puede aparecer la ubicación de la otra tienda.
    assert.equal(
      cand.disponibilidadPorSucursal.some((s: any) => s.locationId === tiendaBId),
      false,
      `${codigo}: no debe filtrar la disponibilidad de TIENDA B`,
    );
    // El almacén se excluye de `disponibilidadPorSucursal` por diseño (solo TIENDA), así
    // que su ausencia aquí no distingue un bug; lo que sí lo distingue es que la lista
    // contenga únicamente la tienda propia.
    assert.equal(
      cand.disponibilidadPorSucursal.length,
      1,
      `${codigo}: una sola sucursal, la propia`,
    );
    assert.equal(cand.disponibilidadPorSucursal[0].locationId, ctx.locationIds.tienda);

    // La disponibilidad agregada debe derivarse del stock VISIBLE, no del global.
    // Umbrales: >10 DISPONIBLE, >0 POCAS_UNIDADES, 0 NO_DISPONIBLE.
    // Si se calculara sobre el inventario global, el nivel sería DISPONIBLE (el global
    // supera 10 por el almacén y TIENDA B), delator de que hay stock en terceros.
    const nivelEsperado = cand.stockTotal > 10 ? "DISPONIBLE" : cand.stockTotal > 0 ? "POCAS_UNIDADES" : "NO_DISPONIBLE";
    assert.equal(
      cand.disponibilidad.nivel,
      nivelEsperado,
      `${codigo}: la disponibilidad debe derivarse del stock visible, no del global`,
    );
    assert.equal(cand.stockPorSucursal.length, 1);
  }
});

test("Aislamiento visión — dos tiendas ven inventarios distintos y ninguno el del otro", async () => {
  const { fd: fdA } = fdConImagen();
  const resA = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { authorization: `Bearer ${tiendaToken}` },
    body: fdA,
  });
  assert.equal(resA.status, 200);
  const bodyA: any = await resA.json();

  const { fd: fdB } = fdConImagen();
  const resB = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { authorization: `Bearer ${tiendaBToken}` },
    body: fdB,
  });
  assert.equal(resB.status, 200);
  const bodyB: any = await resB.json();

  const hiluxA = bodyA.candidatos.find((c: any) => c.itemCode === FRENO_HILUX.itemCode);
  const hiluxB = bodyB.candidatos.find((c: any) => c.itemCode === FRENO_HILUX.itemCode);
  assert.ok(hiluxA && hiluxB);

  assert.equal(hiluxA.stockTotal, FRENO_HILUX.stockTienda, "TIENDA A ve su stock");
  assert.equal(hiluxB.stockTotal, 77, "TIENDA B ve su stock");
  assert.notEqual(hiluxA.stockTotal, hiluxB.stockTotal, "cada tienda ve un valor distinto");

  assert.equal(hiluxA.stockPorSucursal[0].locationId, ctx.locationIds.tienda);
  assert.equal(hiluxB.stockPorSucursal[0].locationId, tiendaBId);
});

test("Aislamiento visión — ADMIN conserva el alcance global", async () => {
  const { fd } = fdConImagen();
  const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
    method: "POST",
    headers: { authorization: `Bearer ${adminToken}` },
    body: fd,
  });
  assert.equal(res.status, 200);
  const body: any = await res.json();

  const hilux = body.candidatos.find((c: any) => c.itemCode === FRENO_HILUX.itemCode);
  assert.ok(hilux, "candidato Hilux presente");

  // Global = tienda A + almacén + tienda B.
  const stockGlobal = FRENO_HILUX.stockTienda + FRENO_HILUX.stockAlmacen + 77;
  assert.equal(hilux.stockTotal, stockGlobal, "ADMIN suma todas las ubicaciones");
  assert.equal(hilux.stockPorSucursal.length, 3, "ADMIN ve las tres ubicaciones");

  const idsVistos = hilux.stockPorSucursal.map((s: any) => s.locationId);
  assert.ok(idsVistos.includes(ctx.locationIds.tienda));
  assert.ok(idsVistos.includes(ctx.locationIds.almacen));
  assert.ok(idsVistos.includes(tiendaBId));

  // La disponibilidad global debe seguir reflejando TODO el inventario.
  assert.equal(hilux.disponibilidad.nivel, "DISPONIBLE");
  // `disponibilidadPorSucursal` solo incluye ubicaciones TIENDA (el almacén se excluye
  // por diseño), así que ADMIN debe ver las dos tiendas.
  assert.equal(hilux.disponibilidadPorSucursal.length, 2, "ADMIN ve la disponibilidad de ambas tiendas");
  const idsDisponibilidad = hilux.disponibilidadPorSucursal.map((s: any) => s.locationId);
  assert.ok(idsDisponibilidad.includes(ctx.locationIds.tienda));
  assert.ok(idsDisponibilidad.includes(tiendaBId));
  assert.equal(idsDisponibilidad.includes(ctx.locationIds.almacen), false, "el almacén no se publica como sucursal");
});

test("interno: caso mapa de categoria inexistente → 200 con candidatos vacíos y nota", async () => {
  await conEscenarioIa("categoria_desconocida", async () => {
    const { fd } = fdConImagen();
    const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
      method: "POST",
      headers: { authorization: `Bearer ${adminToken}` },
      body: fd,
    });
    assert.equal(res.status, 200);
    const body: any = await res.json();
    assert.equal(body.deteccion.categoriaMapeada, null);
    assert.equal(body.candidatos.length, 0);
    assert.equal(body.nota, "La clase detectada no tiene categoría equivalente en el catálogo.");
    assert.ok(body.entrega.sucursales.length > 0, "lista de sucursales disponible");
  });
});

test("interno: IA caída → 503 VISION_NO_DISPONIBLE (nunca una detección simulada)", async () => {
  await conEscenarioIa("caida", async () => {
    const { fd } = fdConImagen();
    const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
      method: "POST",
      headers: { authorization: `Bearer ${adminToken}` },
      body: fd,
    });
    assert.equal(res.status, 503);
    const body: any = await res.json();
    assert.equal(body.codigo, "VISION_NO_DISPONIBLE");
    assert.equal(body.deteccion, undefined, "una IA caída no debe devolver detecciones");
  });
});

test("interno: la IA rechaza X-Vision-Key → 503 controlado", async () => {
  const ia = await fakeIa();
  ia.setClaveEsperada("una-clave-que-el-backend-no-usa");
  try {
    const { fd } = fdConImagen();
    const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
      method: "POST",
      headers: { authorization: `Bearer ${adminToken}` },
      body: fd,
    });
    assert.equal(res.status, 503);
    const body: any = await res.json();
    assert.equal(body.codigo, "VISION_NO_DISPONIBLE");
  } finally {
    ia.setClaveEsperada(null);
  }
});

test("interno: timeout → 504 VISION_TIMEOUT", async () => {
  await conEscenarioIa("timeout", async () => {
    const { fd } = fdConImagen();
    const res = await fetch(`${server.baseUrl}/api/vision/detectar`, {
      method: "POST",
      headers: { authorization: `Bearer ${adminToken}` },
      body: fd,
    });
    assert.equal(res.status, 504);
    const body: any = await res.json();
    assert.equal(body.codigo, "VISION_TIMEOUT");
  });
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