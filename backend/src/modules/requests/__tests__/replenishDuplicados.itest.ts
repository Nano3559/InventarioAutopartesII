import { test, before, after, describe } from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { seed, cleanup, createProduct, SeedContext } from "../../../testing/seed";
import { REQUEST_STATUS_ACTIVOS } from "../../../utils/replenish";

/**
 * ETAPA 9 — Una sola solicitud de reposición ABIERTA por producto y ubicación.
 *
 * Regresión sobre dos defectos encadenados:
 *  1. El job hacía findFirst (¿existe solicitud abierta?) y luego create en otra
 *     sentencia: dos corridas simultáneas veían "no existe" a la vez y creaban dos
 *     solicitudes idénticas (TOCTOU).
 *  2. El chequeo solo miraba PENDIENTE / RECIBIDO_POR_INVENTARIO / PREPARANDO, y
 *     omitía ENTREGADO, que sigue abierta (la tienda aún no recibió la mercadería).
 *
 * La garantía final vive en el índice parcial
 * `ProductRequest_solicitud_abierta_unica` (ver prisma/migrations).
 */

const execFileAsync = promisify(execFile);

let ctx: SeedContext;

/** Producto con stock 0 en la tienda (0 < minStock 1) y 20 en almacén: dispara reposición. */
async function crearProductoBajoMinimo() {
  return createProduct(ctx, { stockTienda: 0, stockAlmacen: 20, unitPrice: 100 });
}

async function solicitudesDe(productId: number) {
  return ctx.prisma.productRequest.findMany({
    where: { productId },
    select: { id: true, status: true, locationId: true },
    orderBy: { id: "asc" },
  });
}

/** Corre el job real en un PROCESO NUEVO (conexión propia) para forzar la carrera. */
async function correrJobEnProcesoSeparado(archivo: string, startAt: number) {
  return execFileAsync(
    process.execPath,
    ["--import", "tsx", archivo, String(startAt)],
    {
      cwd: path.resolve(__dirname, "../../../.."),
      env: { ...process.env, DATABASE_URL: process.env.DATABASE_URL },
    }
  );
}

/** Script hijo temporal (fuera de src/ para que tsc no lo recoja como fuente del proyecto). */
function escribirScriptHijo() {
  const jobPath = path.resolve(__dirname, "../../../jobs/replenishJob").replace(/\\/g, "/");
  const archivo = path.join(os.tmpdir(), `correrJobHijo_${process.pid}.ts`);
  const contenido = [
    `import { generateLowStockRequests } from "${jobPath}";`,
    "",
    "const startAt = Number(process.argv[2]);",
    "",
    "async function main() {",
    "  // Barrera: esperar a la hora acordada para arrancar los dos procesos a la vez.",
    "  while (Date.now() < startAt) { /* spin */ }",
    "  await generateLowStockRequests();",
    "}",
    "",
    "main().then(() => process.exit(0), () => process.exit(1));",
    "",
  ].join("\n");
  return { archivo, contenido };
}

before(async () => {
  ctx = await seed("replenish-dup");
});

after(async () => {
  await cleanup(ctx);
});

describe("Job de reposición: no duplica solicitudes abiertas", () => {
  test("crea la solicitud cuando el stock está bajo el mínimo", async () => {
    const { generateLowStockRequests } = await import("../../../jobs/replenishJob");
    const p = await crearProductoBajoMinimo();

    await generateLowStockRequests();

    const abiertas = await solicitudesDe(p.id);
    assert.equal(abiertas.length, 1, "la primera corrida debe crear una solicitud");
    assert.equal(abiertas[0].status, "PENDIENTE");
    assert.equal(abiertas[0].locationId, ctx.locationIds.tienda);
  });

  test("una segunda corrida NO crea otra solicitud para el mismo producto y tienda", async () => {
    const { generateLowStockRequests } = await import("../../../jobs/replenishJob");
    const p = await crearProductoBajoMinimo();

    await generateLowStockRequests();
    await generateLowStockRequests();
    await generateLowStockRequests();

    const abiertas = await solicitudesDe(p.id);
    assert.equal(abiertas.length, 1, "tres corridas del job deben dejar una sola solicitud");
  });

  test("ENTREGADO también bloquea: la solicitud sigue abierta hasta que la tienda la recibe", async () => {
    const { generateLowStockRequests } = await import("../../../jobs/replenishJob");
    const p = await crearProductoBajoMinimo();

    await generateLowStockRequests();
    const [creada] = await solicitudesDe(p.id);
    await ctx.prisma.productRequest.update({
      where: { id: creada.id },
      data: { status: "ENTREGADO" },
    });

    // El estado anterior NO lo cubría el chequeo: el job abría una segunda solicitud
    // mientras la mercadería ya había salido del almacén pero nadie la había recibido.
    await generateLowStockRequests();

    const abiertas = await solicitudesDe(p.id);
    assert.equal(abiertas.length, 1, "ENTREGADO es una solicitud abierta: no debe duplicarse");
  });

  test("tras RECIBIDO_POR_TIENDA (cerrada) SÍ se permite una nueva solicitud", async () => {
    const { generateLowStockRequests } = await import("../../../jobs/replenishJob");
    const p = await crearProductoBajoMinimo();

    await generateLowStockRequests();
    const [primera] = await solicitudesDe(p.id);
    await ctx.prisma.productRequest.update({
      where: { id: primera.id },
      data: { status: "RECIBIDO_POR_TIENDA" },
    });

    await generateLowStockRequests();

    const todas = await solicitudesDe(p.id);
    assert.equal(todas.length, 2, "una solicitud cerrada libera el slot para la siguiente");
    assert.deepEqual(todas.map((s) => s.status), ["RECIBIDO_POR_TIENDA", "PENDIENTE"]);
  });

  test("tras CANCELAR SÍ se permite una nueva solicitud", async () => {
    const { generateLowStockRequests } = await import("../../../jobs/replenishJob");
    const p = await crearProductoBajoMinimo();

    await generateLowStockRequests();
    const [primera] = await solicitudesDe(p.id);
    await ctx.prisma.productRequest.update({
      where: { id: primera.id },
      data: { status: "CANCELADO" },
    });

    await generateLowStockRequests();

    const todas = await solicitudesDe(p.id);
    assert.equal(todas.length, 2);
    assert.deepEqual(todas.map((s) => s.status), ["CANCELADO", "PENDIENTE"]);
  });
});

describe("Índice parcial: la base de datos sola impide el duplicado", () => {
  test("una segunda fila abierta para el mismo producto/ubicación es rechazada por el índice", async () => {
    const p = await crearProductoBajoMinimo();
    const usuario = ctx.users.tienda.userId;

    const base = {
      productId: p.id,
      locationId: ctx.locationIds.tienda,
      requestedById: usuario,
      quantity: 1,
      expectedDate: new Date(),
    };
    await ctx.prisma.productRequest.create({ data: { ...base, status: "PENDIENTE" } });

    await assert.rejects(
      () => ctx.prisma.productRequest.create({ data: { ...base, status: "PREPARANDO" } }),
      (err: any) => {
        assert.equal(err.code, "P2002", "debe fallar por violación de índice único");
        return true;
      },
      "el índice parcial debe rechazar la segunda solicitud abierta"
    );
  });

  test("cerrar la primera fila libera el slot (el índice es parcial, no total)", async () => {
    const p = await crearProductoBajoMinimo();
    const usuario = ctx.users.tienda.userId;

    const primera = await ctx.prisma.productRequest.create({
      data: {
        productId: p.id,
        locationId: ctx.locationIds.tienda,
        requestedById: usuario,
        quantity: 1,
        status: "PENDIENTE",
      },
    });

    await assert.rejects(
      () =>
        ctx.prisma.productRequest.create({
          data: {
            productId: p.id,
            locationId: ctx.locationIds.tienda,
            requestedById: usuario,
            quantity: 1,
            status: "RECIBIDO_POR_INVENTARIO",
          },
        }),
      (err: any) => err.code === "P2002"
    );

    await ctx.prisma.productRequest.update({ where: { id: primera.id }, data: { status: "CANCELADO" } });

    const segunda = await ctx.prisma.productRequest.create({
      data: {
        productId: p.id,
        locationId: ctx.locationIds.tienda,
        requestedById: usuario,
        quantity: 1,
        status: "PENDIENTE",
      },
    });
    assert.ok(segunda.id > primera.id, "tras cerrar, la siguiente solicitud debe poder crearse");
  });

  test("cada estado activo bloquea por separado (cobertura de REQUEST_STATUS_ACTIVOS)", async () => {
    assert.deepEqual(REQUEST_STATUS_ACTIVOS, [
      "PENDIENTE",
      "RECIBIDO_POR_INVENTARIO",
      "PREPARANDO",
      "ENTREGADO",
    ]);

    for (const estado of REQUEST_STATUS_ACTIVOS) {
      const p = await crearProductoBajoMinimo();
      const base = {
        productId: p.id,
        locationId: ctx.locationIds.tienda,
        requestedById: ctx.users.tienda.userId,
        quantity: 1,
      };
      await ctx.prisma.productRequest.create({ data: { ...base, status: estado } });
      await assert.rejects(
        () => ctx.prisma.productRequest.create({ data: { ...base, status: "PENDIENTE" } }),
        (err: any) => err.code === "P2002",
        `con una solicitud en ${estado} no debe poder abrirse otra`
      );
    }
  });
  test("el WHERE del índice parcial en SQL coincide con REQUEST_STATUS_ACTIVOS", async () => {
    // Si alguien agrega un estado al enum y actualiza la lista de TS pero no el
    // migration.sql, el índice queda obsoleto en silencio y vuelve el duplicado.
    const rutaMigration = path.resolve(
      __dirname,
      "../../../../prisma/migrations/20260928_request_abierta_unica/migration.sql"
    );
    const sql = await fs.readFile(rutaMigration, "utf8");

    const match = sql.match(/WHERE\s+"status"\s+IN\s*\(([^)]*)\)/i);
    assert.ok(match, "no se encontró el WHERE ... IN (...) del índice parcial en migration.sql");

    const estadosEnSql = (match![1].match(/'([^']+)'/g) ?? []).map((s) => s.replace(/'/g, ""));
    assert.deepEqual(
      estadosEnSql,
      REQUEST_STATUS_ACTIVOS,
      "la lista de estados activos del índice parcial debe coincidir con REQUEST_STATUS_ACTIVOS"
    );
  });

  test("VALID_STATUSES es exactamente los estados activos más los dos terminales", async () => {
    // El test anterior solo detecta que la lista de TS y el SQL se desincronicen entre
    // sí. Este cubre el otro hueco: que se agregue un estado nuevo al flujo y se
    // olvide la lista de activos (y por tanto el índice), que seguiría en verde.
    const { VALID_STATUSES } = await import("../requests.routes");
    assert.deepEqual(
      [...VALID_STATUSES].sort(),
      [...REQUEST_STATUS_ACTIVOS, "RECIBIDO_POR_TIENDA", "CANCELADO"].sort(),
      "todo estado no terminal debe estar en REQUEST_STATUS_ACTIVOS y viceversa"
    );
  });
});

describe("La venta nunca se cae por la reposición automática (regresión C-1)", () => {
  test("venta que agota el stock con una solicitud en ENTREGADO responde 201 y no duplica", async () => {
    const { startTestServer, postJson, loginAndGetToken } = await import("../../../testing/helpers");
    const server = await startTestServer();
    try {
      // Producto con 1 unidad en la tienda y 20 en almacén: al venderla el stock queda
      // en 0 y se intentaría abrir la reposición automática.
      const p = await createProduct(ctx, { unitPrice: 100, stockTienda: 1, stockAlmacen: 20 });
      const token = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, ctx.users.tienda.password);

      // Solicitud previa en ENTREGADO: la mercadería salió del almacén pero la tienda
      // todavía no la recibió, así que SIGUE ABIERTA. Con la lista de estados vieja
      // (sin ENTREGADO) la venta no la encontraba, intentaba crear otra y el índice
      // parcial rechazaba la inserción con P2002, abortando toda la venta con HTTP 500.
      const previa = await ctx.prisma.productRequest.create({
        data: {
          productId: p.id,
          locationId: ctx.locationIds.tienda,
          requestedById: ctx.users.tienda.userId,
          quantity: 5,
          status: "ENTREGADO",
        },
      });

      const venta = await postJson(
        server.baseUrl,
        "/api/sales",
        { items: [{ productId: p.id, quantity: 1, unitPrice: 100 }], payments: [{ method: "EFECTIVO", amount: 100 }] },
        token
      );
      assert.equal(venta.status, 201, `la venta NO debe fallar por la reposición: ${venta.status}`);

      const abiertas = await solicitudesDe(p.id);
      assert.equal(abiertas.length, 1, "no debe abrirse una segunda solicitud");
      assert.equal(abiertas[0].id, previa.id, "la solicitud existente debe seguir siendo la única");
    } finally {
      await server.close();
    }
  });
});

describe("Creación manual: misma regla de una sola solicitud abierta", () => {
  test("el segundo POST /requests para el mismo producto y tienda responde 409, no 500", async () => {
    const { startTestServer, postJson, loginAndGetToken } = await import("../../../testing/helpers");
    const server = await startTestServer();
    try {
      const p = await createProduct(ctx, { unitPrice: 100, stockTienda: 5, stockAlmacen: 5 });
      const token = await loginAndGetToken(server.baseUrl, ctx.users.tienda.email, ctx.users.tienda.password);

      const primero = await postJson(
        server.baseUrl,
        "/api/requests",
        { productId: p.id, quantity: 3 },
        token
      );
      assert.equal(primero.status, 201, `la primera solicitud debe crearse: ${primero.status}`);

      const segundo = await postJson(
        server.baseUrl,
        "/api/requests",
        { productId: p.id, quantity: 3 },
        token
      );
      assert.equal(segundo.status, 409, "la segunda debe rechazarse con conflicto explícito");
      const body: any = await segundo.json();
      assert.match(body.message, /Ya existe una solicitud abierta/i);

      const abiertas = await solicitudesDe(p.id);
      assert.equal(abiertas.length, 1);
    } finally {
      await server.close();
    }
  });

  test("tras cerrar la solicitud manual, se puede volver a pedir el mismo producto", async () => {
    const { startTestServer, postJson, jsonHeaders, loginAndGetToken } = await import("../../../testing/helpers");
    const server = await startTestServer();
    try {
      const p = await createProduct(ctx, { unitPrice: 100, stockTienda: 5, stockAlmacen: 5 });
      const tokenAdmin = await loginAndGetToken(server.baseUrl, ctx.users.admin.email, ctx.users.admin.password);

      const primero = await postJson(
        server.baseUrl,
        "/api/requests",
        { productId: p.id, quantity: 2, locationId: ctx.locationIds.tienda },
        tokenAdmin
      );
      assert.equal(primero.status, 201);
      const cuerpo: any = await primero.json();

      const cierreRes = await fetch(`${server.baseUrl}/api/requests/${cuerpo.id}`, {
        method: "PUT",
        headers: jsonHeaders(tokenAdmin),
        body: JSON.stringify({ status: "CANCELADO" }),
      });
      assert.equal(cierreRes.status, 200, `el cierre debe funcionar: ${cierreRes.status}`);

      const segundo = await postJson(
        server.baseUrl,
        "/api/requests",
        { productId: p.id, quantity: 2, locationId: ctx.locationIds.tienda },
        tokenAdmin
      );
      assert.equal(segundo.status, 201, "cerrada la anterior, debe permitirse una nueva");

      const todas = await solicitudesDe(p.id);
      assert.equal(todas.length, 2);
      assert.deepEqual(todas.map((s) => s.status), ["CANCELADO", "PENDIENTE"]);
    } finally {
      await server.close();
    }
  });
});

describe("Concurrencia real: varios procesos ejecutando el job a la vez", () => {
  test("dejan una sola solicitud abierta para el mismo producto y tienda", async () => {
    const p = await crearProductoBajoMinimo();

    const script = escribirScriptHijo();
    await fs.writeFile(script.archivo, script.contenido, "utf8");

    try {
      // 4 procesos reales, cada uno con su propia conexión, liberados a la vez por una
      // barrera temporal. NOTA: una carrera de findFirst+create es intermitente por
      // naturaleza (a veces los procesos se serializan y "no pasa nada"), así que este
      // test es la evidencia de que el camino concurrente no duplica. La garantía
      // DETERMINISTA de "una sola solicitud abierta" la da el índice parcial, y la
      // comprueban los tests del bloque anterior de forma reproducible.
      const startAt = Date.now() + 1500;
      const resultados = await Promise.all(
        [0, 1, 2, 3].map(() => correrJobEnProcesoSeparado(script.archivo, startAt))
      );
      assert.equal(resultados.length, 4);

      const abiertas = await solicitudesDe(p.id);
      assert.equal(
        abiertas.length,
        1,
        `varios procesos concurrentes deben dejar UNA sola solicitud abierta, se crearon ${abiertas.length}`
      );
      assert.equal(abiertas[0].status, "PENDIENTE");
    } finally {
      await fs.rm(script.archivo, { force: true });
    }
  });
});
