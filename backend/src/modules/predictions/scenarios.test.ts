import { test } from "node:test";
import assert from "node:assert/strict";
import express from "express";
import path from "node:path";
import fs from "node:fs/promises";
import { createPredictionsRouter } from "./predictions.routes";
import { scenarioQuery, createScenarioPreview, assertUniqueJsonKeys, SCENARIO_ARTIFACT } from "./scenarios.service";

test("JSON duplicado, incluso con escapes o arrays, no sobrescribe campos", () => {
  for (const raw of ['{"a":1,"a":2}', '{"a":[{"b":1,"b":2}]}', '{"a":1,"\\u0061":2}']) assert.throws(() => assertUniqueJsonKeys(raw), /INVALID_INPUT/);
  for (const raw of ['{}','[]','{"a":[{"b":1},{"b":2}],"c":3}']) assert.doesNotThrow(() => assertUniqueJsonKeys(raw));
});

async function serve(role: string | null, work: (url: string) => Promise<void>, query: any = scenarioQuery) {
  const app = express(); app.use(express.json());
  const session: any = (req: any, _res: any, next: any) => { if (role) req.user = { role, userId: 1 }; next(); };
  const cache = await fs.mkdtemp(path.resolve(__dirname, "../../../../ml/demand/tmp/scenario-test-"));
  app.use("/api/predictions", createPredictionsRouter(session, undefined, query, createScenarioPreview(query, cache)));
  const server = app.listen(0, "127.0.0.1"); await new Promise<void>(r => server.on("listening", r));
  try { await work(`http://127.0.0.1:${(server.address() as any).port}/api/predictions`); }
  finally { server.closeAllConnections(); await new Promise<void>(r => server.close(() => r())); }
}

test("escenarios solo ADMIN, también desde API", async () => {
  for (const role of [null, "TIENDA", "INVENTARIO", "UNKNOWN"]) await serve(role, async url => {
    for (const route of ["scenarios/capabilities", "scenarios/snapshots/id", "scenarios/preview"]) {
      const res = await fetch(`${url}/${route}`, route.endsWith("preview") ? { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" } : {});
      assert.equal(res.status, role === null ? 401 : 403);
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
    const invalid = await send({...payload,clientRequestId:"reject-extra",target_ventas_mes:4}); assert.equal(invalid.status,400);
  });
});

test("idempotencia durable, simultánea y separada por actor", async () => {
  const directory = await fs.mkdtemp(path.resolve(__dirname, "../../../../ml/demand/tmp/scenario-idempotence-"));
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
