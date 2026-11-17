import { test } from "node:test";
import assert from "node:assert/strict";
import express from "express";
import path from "node:path";
import fs from "node:fs/promises";
import { runInNewContext } from "node:vm";
import ts from "typescript";
import { createPredictionsRouter } from "./predictions.routes";
import { scenarioQuery, createScenarioPreview, assertUniqueJsonKeys, SCENARIO_ARTIFACT, SCENARIO_CONTRACT } from "./scenarios.service";
import { authorize } from "../../shared/middlewares/auth";

test("JSON duplicado, incluso con escapes o arrays, no sobrescribe campos", () => {
  for (const raw of ['{"a":1,"a":2}', '{"a":[{"b":1,"b":2}]}', '{"a":1,"\\u0061":2}']) assert.throws(() => assertUniqueJsonKeys(raw), /INVALID_INPUT/);
  for (const raw of ['{}','[]','{"a":[{"b":1},{"b":2}],"c":3}']) assert.doesNotThrow(() => assertUniqueJsonKeys(raw));
});

const TMP_DIR = path.resolve(__dirname, "../../../../ml/demand/tmp");
async function ensureTmpDir() { await fs.mkdir(TMP_DIR, { recursive: true }); return TMP_DIR; }
async function mkdtempInTmp(prefix: string) { return fs.mkdtemp(path.join(await ensureTmpDir(), prefix)); }

async function serve(role: string | null, work: (url: string) => Promise<void>, query: any = scenarioQuery) {
  const app = express(); app.use(express.json());
  const session: any = (req: any, _res: any, next: any) => { if (role) req.user = { role, userId: 1 }; next(); };
  const cache = await mkdtempInTmp("scenario-test-");
  app.use("/api/predictions", createPredictionsRouter(session, undefined, query, createScenarioPreview(query, cache)));
  const server = app.listen(0, "127.0.0.1"); await new Promise<void>(r => server.on("listening", r));
  try { await work(`http://127.0.0.1:${(server.address() as any).port}/api/predictions`); }
  finally { server.closeAllConnections(); await new Promise<void>(r => server.close(() => r())); }
}

const captured: Array<{ route: string; status: number; body: any }> = [];
function record(route: string, status: number, body: any) { captured.push({ route, status, body }); return body; }
function assertEnvelope(body: any, status: number, code: string) {
  assert.ok(status >= 400 && status <= 599);
  assert.equal(body.contractVersion, SCENARIO_CONTRACT);
  assert.equal(body.code, code);
  assert.match(body.code, /^[A-Z][A-Z0-9_]{0,127}$/);
  assert.equal(typeof body.message, "string");
  assert.ok(body.message.length >= 1 && body.message.length <= 2000);
  assert.ok(Array.isArray(body.issues) && body.issues.length <= 100);
  assert.deepEqual(Object.keys(body).sort(), ["code", "contractVersion", "issues", "message"]);
  for (const issue of body.issues) {
    assert.deepEqual(Object.keys(issue).sort(), ["field", "ruleId"]);
    assert.equal(typeof issue.field, "string");
    assert.ok(issue.field.length <= 200);
    assert.match(issue.ruleId, /^SC[0-9]{2}$/);
  }
}

test("escenarios solo ADMIN, también desde API", async () => {
  for (const role of [null, "TIENDA", "INVENTARIO", "UNKNOWN"]) await serve(role, async url => {
    for (const route of ["scenarios/capabilities", "scenarios/snapshots/id", "scenarios/preview"]) {
      const res = await fetch(`${url}/${route}`, route.endsWith("preview") ? { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" } : {});
      const status = role === null ? 401 : 403;
      assert.equal(res.status, status);
      const body = record(route, res.status, await res.json());
      assertEnvelope(body, res.status, status === 401 ? "SESSION_INVALID" : "ADMIN_REQUIRED");
      assert.equal(body.message, status === 401 ? "No autenticado" : "No tiene permisos para esta acción");
    }
  }, () => { throw Error("Must not reach model"); });
});

test("API real → snapshot 4.0.0 → modelo → comparación sin Neon", async () => {
  await serve("ADMIN", async url => {
    const capsResponse = await fetch(url + "/scenarios/capabilities"); assert.equal(capsResponse.status, 200);
    const caps: any = await capsResponse.json(); assert.equal(caps.datasetVersion, "4.0.0"); assert.equal(caps.artifactSha256, SCENARIO_ARTIFACT);
    const s = caps.snapshots[0]; const snapshot: any = await (await fetch(url + "/scenarios/snapshots/" + s.baseSnapshotId)).json();
    assert.equal(s.targetMonth,"2026-11"); assert.equal(snapshot.displayHistory.length,10); assert.equal(snapshot.displayHistory[9].month,"2026-10"); assert.equal(snapshot.history.length, 3); assert.ok(snapshot.retail); assert.equal(snapshot.origin, "SYNTHETIC_SCENARIO_NOT_REAL_SALES");
    const payload = { contractVersion: caps.contractVersion, mode: "HYPOTHETICAL_SCENARIO", clientRequestId: "real-preview", productId: s.productId, locationId: s.locationId, targetMonth: s.targetMonth, baseSnapshotId: s.baseSnapshotId, changes: Object.fromEntries(caps.supportedChanges.map((k: string) => [k, {mode:"KEEP"}])), replenishment: {requested:false,policy:"MONTH_END_COMMITMENT_FLOOR_V1",safetyStockUnits:5,minimumOrderUnits:0,orderMultipleUnits:1,reviewPeriodDays:0} };
    async function send(p: any) { return fetch(url + "/scenarios/preview", { method:"POST", headers:{"Content-Type":"application/json"},body:JSON.stringify(p) }); }
    const res = await send(payload); assert.equal(res.status, 200); const first: any = await res.json();
    assert.equal(first.deltaSalesUnits, 0); assert.equal(first.scenario.status, "OK");
    assert.deepEqual(await (await send(payload)).json(), first);
    const conflict = await send({...payload, replenishment: {...payload.replenishment,safetyStockUnits:6}}); assert.equal(conflict.status,409);
    const conflictBody = record("/scenarios/preview", 409, await conflict.json());
    assertEnvelope(conflictBody, 409, "IDEMPOTENCY_CONFLICT");
    assert.deepEqual(conflictBody.issues, [{ field: "clientRequestId", ruleId: "SC18" }]);
    const invalid = await send({...payload,clientRequestId:"reject-extra",target_ventas_mes:4}); assert.equal(invalid.status,400);
    const invalidBody = record("/scenarios/preview", 400, await invalid.json());
    assertEnvelope(invalidBody, 400, "INVALID_INPUT");
    assert.deepEqual(invalidBody.issues, []);
  });
});

test("E05-01: eliminar entrega explica el cambio y conserva el contrato del frontend", async () => {
  await serve("ADMIN", async url => {
    const caps: any = await (await fetch(url + "/scenarios/capabilities")).json();
    const selected = caps.snapshots.find((s: any) => s.baseSnapshotId === "calendar-2026-53-6-november");
    assert.ok(selected);
    const base: any = await (await fetch(url + "/scenarios/snapshots/" + selected.baseSnapshotId)).json();
    const payload = {
      contractVersion: caps.contractVersion, mode: "HYPOTHETICAL_SCENARIO", clientRequestId: "e05-delete-shipment",
      productId: selected.productId, locationId: selected.locationId, targetMonth: selected.targetMonth, baseSnapshotId: selected.baseSnapshotId,
      changes: { ...Object.fromEntries(caps.supportedChanges.map((k: string) => [k, { mode: "KEEP" }])), logistics: {
        mode: "SET_LOGISTICS_PLAN", supplierLeadTimeDays: base.supplierDays, internalRestockDays: base.internalDays,
        plannedOrderAt: base.orderAt, pendingShipments: [],
      } },
      replenishment: { requested: false, policy: "MONTH_END_COMMITMENT_FLOOR_V1", safetyStockUnits: 5, minimumOrderUnits: 0, orderMultipleUnits: 1, reviewPeriodDays: 0 },
    };
    const send = () => fetch(url + "/scenarios/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const response = await send(); assert.equal(response.status, 200);
    const result: any = await response.json();
    assert.ok(Math.abs(result.baseline.salesUnits - 87.17) < 1e-6);
    assert.ok(Math.abs(result.scenario.salesUnits - 86.57) < 1e-6);
    assert.ok(Math.abs(result.deltaSalesUnits + 0.60) < 1e-6);
    const removed = result.impacts.find((i: any) => i.field.endsWith(".pendingUnits"));
    assert.equal(removed.before, 50); assert.equal(removed.after, null);
    assert.equal(removed.role, "DERIVED_MODEL_FEATURE"); assert.equal(removed.effectStatus, "USED");
    assert.match(removed.explanation, /eliminado/);
    assert.match(removed.explanation, /entradas_plan_horizonte_unidades/);
    assert.ok(result.impacts.every((i: any) => i.before !== i.after));
    assert.deepEqual(await (await send()).json(), result);
    const unchanged: any = await (await fetch(url + "/scenarios/snapshots/" + selected.baseSnapshotId)).json();
    assert.deepEqual(unchanged, base);

    // Exercise Ross's actual standalone adapter without changing frontend files
    // or importing them into the backend TypeScript compilation root.
    const source = await fs.readFile(path.resolve(__dirname, "../../../../frontend/src/services/scenarioView.ts"), "utf8");
    const adapter = { exports: {} as any };
    runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText, adapter);
    const checkedCaps = adapter.exports.checkedCapabilities(caps);
    const checked = adapter.exports.checkedScenario(result, selected, checkedCaps);
    const checkedRemoval = checked.impacts.find((i: any) => i.field === removed.field);
    assert.equal(checkedRemoval.before, 50); assert.equal(checkedRemoval.after, null);
    assert.equal(checkedRemoval.effectStatus, "USED");
  });
});

test("E06-01: exceso de reposición responde 400 dentro y fuera del horizonte", async () => {
  await serve("ADMIN", async url => {
    const caps: any = await (await fetch(url + "/scenarios/capabilities")).json();
    const selected = caps.snapshots.find((s: any) => s.baseSnapshotId === "calendar-2026-53-6-november");
    assert.ok(selected);
    const base: any = await (await fetch(url + "/scenarios/snapshots/" + selected.baseSnapshotId)).json();
    const source = await fs.readFile(path.resolve(__dirname, "../../../../frontend/src/services/scenarioView.ts"), "utf8");
    const adapter = { exports: {} as any };
    runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText, adapter);
    const checkedCaps = adapter.exports.checkedCapabilities(caps);
    const payload = (days: number, safety: number, minimum = 0, multiple = 1) => ({
      contractVersion: caps.contractVersion, mode: "HYPOTHETICAL_SCENARIO",
      clientRequestId: `e06-${days}-${safety}-${minimum}-${multiple}`,
      productId: selected.productId, locationId: selected.locationId,
      targetMonth: selected.targetMonth, baseSnapshotId: selected.baseSnapshotId,
      changes: { ...Object.fromEntries(caps.supportedChanges.map((k: string) => [k, { mode: "KEEP" }])), logistics: {
        mode: "SET_LOGISTICS_PLAN", supplierLeadTimeDays: days, internalRestockDays: 0,
        plannedOrderAt: base.orderAt, pendingShipments: base.shipments,
      } },
      replenishment: { requested: true, policy: "MONTH_END_COMMITMENT_FLOOR_V1", safetyStockUnits: safety,
        minimumOrderUnits: minimum, orderMultipleUnits: multiple, reviewPeriodDays: 0 },
    });
    const send = (p: any) => fetch(url + "/scenarios/preview", {
      method: "POST", headers: { "Content-Type": "application/json", Connection: "close" }, body: JSON.stringify(p),
    });
    // Removing incoming supply leaves a positive need, so packing is actually applied.
    const packedOverflow = payload(7, 5, 1e9, 3);
    packedOverflow.changes.logistics.pendingShipments = [];
    for (const p of [payload(7, 1e9), payload(31, 1e9), packedOverflow]) {
      const response = await send(p);
      assert.equal(response.status, 400);
      const body: any = await response.json();
      assertEnvelope(body, response.status, "INVALID_QUANTITY");
      assert.deepEqual(body.issues, []);
      assert.equal(body.message, "Revisa cantidades, precios y fechas del escenario.");
      assert.match(adapter.exports.scenarioFailureText({ response: { status: response.status, data: body } }), /límites admitidos/);
    }
    // Exactly the maximum is valid, including the response with no late-order suggestion.
    const response = await send(payload(31, 1e9 - 88));
    assert.equal(response.status, 200);
    const result: any = await response.json();
    assert.equal(result.replenishment.requiredUnits, 1e9);
    assert.equal(result.replenishment.status, "OUTSIDE_FORECAST_HORIZON");
    assert.equal(result.replenishment.suggestedUnits, null);
    const checked = adapter.exports.checkedScenario(result, selected, checkedCaps);
    assert.equal(checked.replenishment.requiredUnits, 1e9);
    assert.equal(checked.replenishment.suggestedUnits, null);
    assert.deepEqual(await (await fetch(url + "/scenarios/snapshots/" + selected.baseSnapshotId)).json(), base);
  });
});

test("idempotencia durable, simultánea y separada por actor", async () => {
  const directory = await mkdtempInTmp("scenario-idempotence-");
  let calls = 0;
  const response: any = { contractVersion:"demand-scenarios-1.0.0",datasetVersion:"4.0.0",artifactSha256:SCENARIO_ARTIFACT,modelVersion:"calendar-model-20261116-01",policyVersion:"SCENARIO_NONNEGATIVE_1",origin:"SYNTHETIC_SCENARIO_NOT_REAL_SALES",mode:"HYPOTHETICAL_SCENARIO",timeZone:"America/La_Paz",horizonMonths:1,baseline:{status:"OK",salesUnits:2,reason:null},scenario:{status:"OK",salesUnits:2,reason:null},deltaSalesUnits:0,replenishment:{},impacts:[],scenarioInputSha256:"a".repeat(64)};
  const query: any = async (_a: string,p: any) => { calls++; return {...response,baseSnapshotId:p.baseSnapshotId,productId:p.productId,locationId:p.locationId,targetMonth:p.targetMonth}; };
  const p = {clientRequestId:"same",baseSnapshotId:"snapshot",productId:1,locationId:5,targetMonth:"2028-04"};
  const preview=createScenarioPreview(query,directory);
  await Promise.all([preview(1,p),preview(1,p)]); assert.equal(calls,1);
  await createScenarioPreview(query,directory)(1,p); assert.equal(calls,1);
  await assert.rejects(preview(1,{...p,productId:2}),/IDEMPOTENCY_CONFLICT/);
  await preview(2,p); assert.equal(calls,2);
});

test("códigos de escenario: envelope contractual y 503 restringido a la allowlist", async () => {
  const cases: Array<{ thrown: string; status: number; code: string; issue: { field: string; ruleId: string } | null }> = [
    { thrown: "MODEL_UNAVAILABLE", status: 503, code: "MODEL_UNAVAILABLE", issue: null },
    { thrown: "INCOMPATIBLE_ARTIFACT", status: 503, code: "INCOMPATIBLE_ARTIFACT", issue: null },
    { thrown: "DB_PASSWORD_LEAK", status: 503, code: "MODEL_UNAVAILABLE", issue: null },
    { thrown: "contraseña interna", status: 503, code: "MODEL_UNAVAILABLE", issue: null },
    { thrown: "INCOHERENT_PRICES", status: 400, code: "INCOHERENT_PRICES", issue: { field: "changes.prices", ruleId: "SC04" } },
    { thrown: "INVALID_HISTORY_WINDOW", status: 400, code: "INVALID_HISTORY_WINDOW", issue: { field: "changes.history", ruleId: "SC02" } },
    { thrown: "INVALID_QUOTE_TIME", status: 400, code: "INVALID_QUOTE_TIME", issue: { field: "changes.quote", ruleId: "SC05" } },
    { thrown: "INVALID_ORDER_PLAN", status: 400, code: "INVALID_ORDER_PLAN", issue: { field: "changes.orders", ruleId: "SC10" } },
    { thrown: "INVALID_SHIPMENT_PLAN", status: 400, code: "INVALID_SHIPMENT_PLAN", issue: { field: "changes.logistics", ruleId: "SC11" } },
    { thrown: "INVALID_QUANTITY", status: 400, code: "INVALID_QUANTITY", issue: null },
    { thrown: "INVALID_RESERVATION", status: 400, code: "INVALID_RESERVATION", issue: null },
    { thrown: "INVALID_INPUT", status: 400, code: "INVALID_INPUT", issue: null },
    { thrown: "SNAPSHOT_MISMATCH", status: 409, code: "SNAPSHOT_MISMATCH", issue: { field: "baseSnapshotId", ruleId: "SC01" } },
    { thrown: "IDEMPOTENCY_CONFLICT", status: 409, code: "IDEMPOTENCY_CONFLICT", issue: { field: "clientRequestId", ruleId: "SC18" } },
    { thrown: "SCENARIO_BUSY", status: 429, code: "SCENARIO_BUSY", issue: null },
  ];
  for (const c of cases) await serve("ADMIN", async url => {
    const res = await fetch(url + "/scenarios/capabilities");
    assert.equal(res.status, c.status);
    const body = record("/scenarios/capabilities", res.status, await res.json());
    assertEnvelope(body, res.status, c.code);
    if (c.issue) { assert.equal(body.issues.length, 1); assert.deepEqual(body.issues[0], c.issue); }
    else assert.deepEqual(body.issues, []);
    if (c.status === 503) {
      assert.equal(body.message, "No se pudo cargar el modelo de escenarios. Intenta nuevamente.");
      assert.ok(!JSON.stringify(body).includes(c.thrown) || c.thrown === "MODEL_UNAVAILABLE" || c.thrown === "INCOMPATIBLE_ARTIFACT");
    }
  }, async () => { throw new Error(c.thrown); });
});

test("validación de entrada y snapshot inválido responden 400 conforme al contrato", async () => {
  await serve("ADMIN", async url => {
    const previewResponse = await fetch(url + "/scenarios/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: '{"action":"x"}' });
    assert.equal(previewResponse.status, 400);
    const body = record("/scenarios/preview", 400, await previewResponse.json());
    assertEnvelope(body, 400, "INVALID_INPUT");
    assert.equal(body.message, "Escenario inválido");
    assert.deepEqual(body.issues, []);
    const snapshot = await fetch(url + "/scenarios/snapshots/bad%20id");
    assert.equal(snapshot.status, 400);
    const snapshotBody = record("/scenarios/snapshots/:id", 400, await snapshot.json());
    assertEnvelope(snapshotBody, 400, "INVALID_INPUT");
    assert.deepEqual(snapshotBody.issues, []);
  }, () => { throw Error("Must not reach model"); });
});

test("el envelope de escenarios no altera /catalog, /demand ni la autenticación compartida", async () => {
  await serve(null, async url => {
    const catalog = await fetch(url + "/catalog");
    assert.equal(catalog.status, 401);
    const catalogBody: any = await catalog.json();
    assert.deepEqual(Object.keys(catalogBody), ["message"]);
    assert.equal("contractVersion" in catalogBody, false);
    const demand = await fetch(url + "/demand", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ productId: 1, locationId: 5 }) });
    assert.equal(demand.status, 401);
    const demandBody: any = await demand.json();
    assert.deepEqual(Object.keys(demandBody), ["message"]);
    assert.equal("contractVersion" in demandBody, false);
  }, () => { throw Error("Must not reach model"); });
  const app = express(); app.use(express.json());
  const session: any = (req: any, _res: any, next: any) => { req.user = { role: "TIENDA", userId: 1 }; next(); };
  app.get("/other-module/resource", session, authorize("ADMIN"), (_req, res) => res.json({ ok: true }));
  const server = app.listen(0, "127.0.0.1"); await new Promise<void>(r => server.on("listening", r));
  try {
    const res = await fetch(`http://127.0.0.1:${(server.address() as any).port}/other-module/resource`);
    assert.equal(res.status, 403);
    const body: any = await res.json();
    assert.deepEqual(Object.keys(body), ["message"]);
    assert.equal("contractVersion" in body, false);
  } finally { server.closeAllConnections(); await new Promise<void>(r => server.close(() => r())); }
});

test("dump de respuestas de error reales para validarlas contra error_schema", async () => {
  assert.ok(captured.length >= 20, `esperaba >=20 respuestas capturadas, hubo ${captured.length}`);
  for (const entry of captured) assertEnvelope(entry.body, entry.status, entry.body.code);
  await fs.writeFile(path.join(await ensureTmpDir(), "scenario-error-bodies.json"), JSON.stringify(captured, null, 2), "utf8");
});
