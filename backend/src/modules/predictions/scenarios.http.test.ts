import { after, before, beforeEach, mock, test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import path from "node:path";
import fs from "node:fs/promises";
import type { PathLike } from "node:fs";
import { execFileSync } from "node:child_process";
import jwt from "jsonwebtoken";
import ts from "typescript";
import { runInNewContext } from "node:vm";
import { logger } from "../../shared/utils/logger";

// Run the real app/parser/router/authentication. Only external verification,
// session reads and technical-cache storage are replaced; never contact Neon.
const database = require("../../config/database");
const originalDatabase = database.default;
const cacheRoot = path.resolve(__dirname, "../../../../ml/demand/tmp/scenario-preview-cache-v1");
const cache = new Map<string, string>();
const originalRead = fs.readFile.bind(fs);
let session: "ADMIN" | "TIENDA" | "INVENTARIO" | "DOWN" | "REVOKED" = "ADMIN";
let server: http.Server;
let origin: string;
let caps: any, selected: any, base: any, keep: any;
const errors: any[] = [];
const routes = [
  "/api/predictions/scenarios/preview",
  "/api/predictions/scenarios/preview/",
  "/api/predictions/scenarios/PREVIEW",
  "/API/PREDICTIONS/SCENARIOS/PREVIEW/",
  "/Api/Predictions/Scenarios/PreView/?audit=1",
  "/api/predictions/scenarios/preview?audit=1",
  "/api/predictions//scenarios/preview",
  "/API/PREDICTIONS//SCENARIOS/PREVIEW/?audit=1",
];
type Reply = { status: number; body: any; headers: http.IncomingHttpHeaders };

function send(route: string, raw?: string, token: string | null = "audit-session", absolute = false): Promise<Reply> {
  const url = new URL(origin);
  return new Promise((resolve, reject) => {
    const request = http.request({ hostname: url.hostname, port: url.port,
      path: absolute ? origin + route : route, method: raw === undefined ? "GET" : "POST",
      headers: { Connection: "close", ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(raw === undefined ? {} : { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(raw) }) },
    }, response => {
      const chunks: Buffer[] = [];
      response.on("data", chunk => chunks.push(Buffer.from(chunk)));
      response.on("end", () => {
        try { resolve({ status: response.statusCode!, body: JSON.parse(Buffer.concat(chunks).toString("utf8")), headers: response.headers }); }
        catch (error) { reject(error); }
      });
    });
    request.on("error", reject); request.end(raw);
  });
}

function payload(id = "e07-http-variants") {
  return { contractVersion: caps.contractVersion, mode: "HYPOTHETICAL_SCENARIO", clientRequestId: id,
    productId: selected.productId, locationId: selected.locationId, targetMonth: selected.targetMonth,
    baseSnapshotId: selected.baseSnapshotId,
    changes: Object.fromEntries(caps.supportedChanges.map((name: string) => [name, { mode: "KEEP" }])),
    replenishment: { requested: false, policy: "MONTH_END_COMMITMENT_FLOOR_V1", safetyStockUnits: 5,
      minimumOrderUnits: 0, orderMultipleUnits: 1, reviewPeriodDays: 0 } };
}

function envelope(reply: Reply, status: number, code: string) {
  assert.equal(reply.status, status);
  assert.deepEqual(Object.keys(reply.body).sort(), ["code", "contractVersion", "issues", "message"]);
  assert.equal(reply.body.contractVersion, "demand-scenarios-1.0.0");
  assert.equal(reply.body.code, code);
  assert.equal(typeof reply.body.message, "string");
  assert.deepEqual(reply.body.issues, []);
  errors.push(reply.body);
}

before(async () => {
  database.default = {
    user: { findUnique: async () => {
      if (session === "DOWN") throw new Error("SESSION_STORE_INTERNAL_DETAIL");
      return { id: 1, email: "audit@example.invalid", locationId: 6, role: { name: session } };
    } },
    auditLog: { findFirst: async () => session === "REVOKED" ? { id: 1 } : null },
  };
  mock.method(jwt, "verify", ((token: string) => {
    if (token === "invalid") throw new jwt.JsonWebTokenError("invalid");
    return { userId: 1, iat: Math.floor(Date.now() / 1000) };
  }) as any);
  mock.method(logger, "info", () => {}); mock.method(logger, "error", () => {});
  const inCache = (p: unknown) => path.resolve(String(p)).startsWith(cacheRoot + path.sep);
  const missing = () => Object.assign(new Error("Virtual cache miss"), { code: "ENOENT" });
  mock.method(fs, "readFile", (async (p: any, ...args: any[]) => {
    if (!inCache(p)) return (originalRead as any)(p, ...args);
    if (!cache.has(String(p))) throw missing();
    return cache.get(String(p));
  }) as any);
  mock.method(fs, "mkdir", (async (p: any) => { assert.equal(path.resolve(String(p)), cacheRoot); }) as any);
  mock.method(fs, "writeFile", (async (p: any, value: string) => {
    assert.ok(inCache(p)); cache.set(String(p), value);
  }) as any);
  mock.method(fs, "link", async (a: PathLike, b: PathLike) => {
    assert.ok(inCache(a) && inCache(b));
    if (cache.has(String(b))) throw Object.assign(new Error("Exists"), { code: "EEXIST" });
    if (!cache.has(String(a))) throw missing();
    cache.set(String(b), cache.get(String(a))!);
  });
  mock.method(fs, "unlink", async (p: PathLike) => { assert.ok(inCache(p)); cache.delete(String(p)); });
  const app = (await import("../../app")).default;
  server = app.listen(0, "127.0.0.1");
  await new Promise<void>(resolve => server.on("listening", resolve));
  origin = `http://127.0.0.1:${(server.address() as any).port}`;
  const capabilities = await send("/api/predictions/scenarios/capabilities");
  assert.equal(capabilities.status, 200); caps = capabilities.body;
  assert.equal(caps.datasetVersion, "4.0.0");
  selected = caps.snapshots.find((s: any) => s.baseSnapshotId === "calendar-2026-53-6-november");
  assert.ok(selected);
  const snapshot = await send("/api/predictions/scenarios/snapshots/" + selected.baseSnapshotId);
  assert.equal(snapshot.status, 200); base = snapshot.body;
});

beforeEach(() => { session = "ADMIN"; });
after(async () => {
  try {
    if (server) { server.closeAllConnections(); await new Promise<void>(resolve => server.close(() => resolve())); }
  } finally { database.default = originalDatabase; mock.restoreAll(); }
});

test("E07: JSON válido en rutas canónicas, variantes y request-target absoluto", async () => {
  for (const route of routes) {
    const reply = await send(route, JSON.stringify(payload()));
    assert.equal(reply.status, 200, route);
    if (!keep) keep = reply.body;
    assert.deepEqual(reply.body, keep, route);
  }
  const absolute = await send(routes[0], JSON.stringify(payload()), "audit-session", true);
  assert.equal(absolute.status, 200); assert.deepEqual(absolute.body, keep);
});

test("E07-01: duplicados rechazados incluso si existe una respuesta en caché", async t => {
  const raw = '{"productId":999,' + JSON.stringify(payload()).slice(1);
  for (const route of routes) await t.test(route, async () => envelope(await send(route, raw), 400, "INVALID_INPUT"));
  await t.test("request-target absoluto", async () => envelope(await send(routes[0], raw, "audit-session", true), 400, "INVALID_INPUT"));
});

test("E07-01: duplicados anidados, escapados y dentro de arrays", async t => {
  const p = payload();
  const nested = JSON.stringify(p).replace('"stock":{"mode":"KEEP"}', '"stock":{"mode":"KEEP","mode":"KEEP"}');
  const escaped = JSON.stringify(p).slice(0, -1) + ',"\\u0070roductId":53}';
  p.changes.orders = { mode: "REPLACE_OPEN_ORDER_PLAN", orders: [{ orderId: "fixture", mode: "POR_MAYOR",
    outstandingUnits: 1, reservedUnits: 0, dueAt: "2026-11-10T00:00:00-04:00" }] } as any;
  const array = JSON.stringify(p).replace('"reservedUnits":0', '"reservedUnits":0,"reservedUnits":0');
  for (const [name, raw] of [["nested", nested], ["escaped", escaped], ["array", array]]) {
    await t.test(name, async () => envelope(await send(routes[3], raw), 400, "INVALID_INPUT"));
  }
});

test("E07-02: JSON mal formado conserva mensaje seguro y sobre en todas las variantes", async t => {
  for (const route of routes) await t.test(route, async () => {
    const reply = await send(route, "{"); envelope(reply, 400, "INVALID_INPUT");
    assert.equal(reply.body.message, "JSON inválido en el cuerpo de la petición");
  });
  for (const raw of ["null", '"text"']) envelope(await send(routes[0], raw), 400, "INVALID_INPUT");
  envelope(await send(routes[0], "{", "audit-session", true), 400, "INVALID_INPUT");
});

test("E07-01: separadores adicionales no permiten omitir el JSON original", async t => {
  const raw = '{"productId":999,' + JSON.stringify(payload()).slice(1);
  for (const route of ["/api/predictions///scenarios/preview",
    "/api/predictions/scenarios//preview", "/api/predictions/scenarios/preview//"]) {
    await t.test(route, async () => {
      const valid = await send(route, JSON.stringify(payload()));
      assert.equal(valid.status, 404);
      const duplicate = await send(route, raw);
      assert.equal(duplicate.status, 404);
    });
  }
});

test("E07: métodos y rutas no admitidos no ejecutan preview", async () => {
  for (const route of [routes[0], routes[0] + "//"]) {
    assert.equal((await send(route)).status, 404);
  }
  assert.equal((await send(routes[0] + "//", JSON.stringify(payload()))).status, 404);
});

test("E07: autenticación y autorización conservadas también con prefijo en mayúsculas", async () => {
  for (const route of ["/api/predictions/scenarios/capabilities", "/API/PREDICTIONS/SCENARIOS/CAPABILITIES",
    "/api/predictions//scenarios/capabilities"]) {
    envelope(await send(route, undefined, null), 401, "SESSION_INVALID");
    envelope(await send(route, undefined, "invalid"), 401, "SESSION_INVALID");
    for (const role of ["TIENDA", "INVENTARIO"] as const) {
      session = role; envelope(await send(route), 403, "ADMIN_REQUIRED");
    }
    session = "REVOKED"; envelope(await send(route), 401, "SESSION_INVALID");
  }
});

test("E07-02: verificación de sesión no disponible responde 503 contractual", async () => {
  session = "DOWN";
  for (const route of ["/api/predictions/scenarios/capabilities", "/api/predictions/scenarios/snapshots/" + selected.baseSnapshotId,
    "/API/PREDICTIONS/SCENARIOS/CAPABILITIES"]) {
    const reply = await send(route); envelope(reply, 503, "MODEL_UNAVAILABLE");
    assert.equal(reply.body.message, "No se pudo verificar la sesión. Intente nuevamente");
    assert.ok(!JSON.stringify(reply.body).includes("SESSION_STORE_INTERNAL_DETAIL"));
  }
  for (const route of routes) envelope(await send(route, JSON.stringify(payload())), 503, "MODEL_UNAVAILABLE");
});

test("E07: errores JSON de otros módulos conservan su estructura legada", async () => {
  for (const route of ["/api/auth/login", "/api/users", "/api/predictions/demand", "/api/predictions/scenarios-extra"]) {
    const reply = await send(route, "{");
    assert.equal(reply.status, 400); assert.deepEqual(reply.body, { message: "JSON inválido en el cuerpo de la petición" });
  }
});

test("E07: 401/403/503 de otros módulos no se adaptan al contrato de escenarios", async () => {
  for (const route of ["/api/users", "/api/predictions/catalog", "/api/predictions/demand"]) {
    const raw = route.endsWith("demand") ? "{}" : undefined;
    session = "ADMIN";
    const anonymous = await send(route, raw, null);
    assert.equal(anonymous.status, 401); assert.deepEqual(Object.keys(anonymous.body), ["message"]);
    session = "TIENDA";
    const forbidden = await send(route, raw);
    assert.equal(forbidden.status, 403); assert.deepEqual(Object.keys(forbidden.body), ["message"]);
    session = "DOWN";
    const unavailable = await send(route, raw);
    assert.equal(unavailable.status, 503); assert.deepEqual(Object.keys(unavailable.body), ["message"]);
  }
});

test("E07: idempotencia y concurrencia reales conservan timestamp y conflicto", async () => {
  const p = payload("e07-concurrent");
  const replies = await Promise.all([send(routes[0], JSON.stringify(p)), send(routes[1], JSON.stringify(p))]);
  assert.ok(replies.every(reply => reply.status === 200));
  assert.deepEqual(replies[0].body, replies[1].body);
  assert.deepEqual(replies.map(reply => reply.headers["x-scenario-delivery"]).sort(), ["computed", "replayed"]);
  const replay = await send(routes[2], JSON.stringify(Object.fromEntries(Object.entries(p).reverse())));
  assert.equal(replay.status, 200);
  assert.deepEqual(replay.body, replies[0].body);
  assert.equal(replay.headers["x-scenario-delivery"], "replayed");
  p.changes.stock = { mode: "SET_SELLABLE_STOCK", sellablePhysicalUnits: 20 } as any;
  const conflict = await send(routes[0], JSON.stringify(p));
  assert.equal(conflict.status, 409); assert.equal(conflict.body.code, "IDEMPOTENCY_CONFLICT");
  assert.deepEqual(conflict.body.issues, [{ field: "clientRequestId", ruleId: "SC18" }]);
  assert.equal(conflict.headers["x-scenario-delivery"], undefined);
});

test("M41-08: revisión publicada, recuperada y desconocida sin reescribir evidencia", async () => {
  const { createHash } = await import("node:crypto");
  const { createScenarioPreview } = await import("./scenarios.service");
  const hash = (value: string | Buffer) => createHash("sha256").update(value).digest("hex");
  const p = payload("m41-08-provenance");
  const key = path.join(cacheRoot, hash("1:" + p.clientRequestId) + ".json");
  const first = await send(routes[0], JSON.stringify(p));
  assert.equal(first.status, 200);
  assert.equal(first.headers["x-scenario-delivery"], "computed");
  const sourceNames = ["admin_scenarios.py", "v2/__init__.py", "v2/calendar2026.py",
    "v2/calendar2026_runtime.py", "v2/scenario_data.py", "v2/scenario_runtime.py"];
  const sources = await Promise.all(sourceNames.map(async name => [name,
    hash(await originalRead(path.resolve(cacheRoot, "../..", name)))]));
  const revision = "sha256:" + hash(JSON.stringify(sources));
  assert.equal(first.headers["x-scenario-runtime-revision"], revision);
  assert.equal(first.headers["access-control-expose-headers"], "X-Scenario-Delivery, X-Scenario-Runtime-Revision");
  assert.equal(first.body.scenario.salesUnits, 87.17);
  assert.equal(first.body.runtimeRevision, undefined);

  const bytes = cache.get(key)!;
  const saved = JSON.parse(bytes);
  assert.equal(saved.runtimeRevision, revision);
  const restarted = createScenarioPreview(async () => { assert.fail("Se recalculó el registro guardado"); }, cacheRoot);
  assert.deepEqual(await restarted(1, p, meta => {
    assert.deepEqual(meta, { delivery: "replayed", runtimeRevision: revision });
  }), first.body);
  assert.equal(cache.get(key), bytes);

  // Model an older entry in the in-memory cache, including its original timestamp.
  saved.response.recordedAt = "2026-11-16T10:00:00-04:00";
  delete saved.runtimeRevision;
  const legacy = JSON.stringify(saved);
  cache.set(key, legacy);
  const old = await send(routes[0], JSON.stringify(p));
  assert.equal(old.status, 200);
  assert.equal(old.headers["x-scenario-delivery"], "replayed");
  assert.equal(old.headers["x-scenario-runtime-revision"], "unknown");
  assert.deepEqual(old.body, saved.response);
  assert.equal(old.body.scenarioInputSha256, first.body.scenarioInputSha256);
  assert.equal(cache.get(key), legacy);
});

test("E07: identidad BASE y consumidor frontend permanecen compatibles", async () => {
  const snapshot = await send("/api/predictions/scenarios/snapshots/" + selected.baseSnapshotId);
  assert.deepEqual(snapshot.body, base);
  const source = await fs.readFile(path.resolve(__dirname, "../../../../frontend/src/services/scenarioView.ts"), "utf8");
  const adapter = { exports: {} as any };
  runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText, adapter);
  const checked = adapter.exports.checkedScenario(keep, selected, adapter.exports.checkedCapabilities(caps));
  assert.equal(checked.scenario.salesUnits, 87.17); assert.equal(checked.deltaSalesUnits, 0);
  for (const body of errors) assert.equal(typeof adapter.exports.scenarioFailureText({ response: { data: body } }), "string");
});

test("E07: errores reales cumplen error_schema congelado", () => {
  assert.ok(errors.length > 20);
  const python = path.resolve(__dirname, "../../../../ml/demand/.venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  const contract = path.resolve(__dirname, "../../../../ml/demand/v2/contracts/scenarios.v1.json");
  execFileSync(python, ["-B", "-c", "import json,sys,jsonschema; c=json.load(open(sys.argv[1],encoding='utf8')); v=jsonschema.Draft202012Validator(c['response_policy']['error_schema']); [v.validate(x) for x in json.load(sys.stdin)]", contract],
    { input: JSON.stringify(errors), encoding: "utf8", timeout: 30000 });
});
