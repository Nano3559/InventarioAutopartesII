import { test } from "node:test";
import assert from "node:assert/strict";
import express, { RequestHandler } from "express";
import { authorize } from "../../shared/middlewares/auth";

// Los permisos usan el middleware real. La sesión y la consulta se sustituyen
// solo en la app de pruebas. Nunca se abre una conexión de base de datos.
async function exercise(role: string | null, path: string, payload?: unknown, fail?: string, realPython = false, realSession = false, authorization?: string) {
  const { createPredictionsRouter } = await import("./predictions.routes");
  const { demandQuery } = await import("./predictions.service");
  let calls = 0;
  const session: RequestHandler = (req, _res, next) => {
    if (role) (req as any).user = { role, userId: 1 };
    next();
  };
  const app = express();
  app.use(express.json());
  app.use("/api/predictions", createPredictionsRouter(realSession ? undefined : session as any, realPython ? demandQuery : async () => {
    calls++;
    if (fail) throw new Error(fail);
    return { origin: "SYNTHETIC", prediction: 40.8725 };
  }));
  const server = app.listen(0, "127.0.0.1");
  await new Promise<void>(resolve => server.on("listening", resolve));
  try {
    const port = (server.address() as any).port;
    const response = await fetch(`http://127.0.0.1:${port}/api/predictions/${path}`, {
      method: payload === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json", ...(authorization ? {Authorization: authorization} : {}) },
      ...(payload === undefined ? {} : {body: JSON.stringify(payload)}),
    });
    return { status: response.status, body: await response.json() as any, calls };
  } finally { server.closeAllConnections(); await new Promise<void>(resolve => server.close(() => resolve())); }
}

test("predicciones rechaza sesión ausente y roles no ADMIN antes de consultar", async () => {
  for (const role of [null, "TIENDA", "INVENTARIO", "UNKNOWN"]) {
    for (const endpoint of ["catalog", "demand"]) {
      const response = await exercise(role, endpoint, endpoint === "demand" ? {productId:1, locationId:5} : undefined);
      assert.equal(response.status, role === null ? 401 : 403);
      assert.equal(response.calls, 0);
    }
  }
  assert.equal(typeof authorize, "function");
});
test("ADMIN puede consultar catálogo y predicción", async () => {
  assert.equal((await exercise("ADMIN", "catalog")).status, 200);
  const response = await exercise("ADMIN", "demand", { productId: 1, locationId: 5 });
  assert.equal(response.status, 200);
  assert.equal(response.body.origin, "SYNTHETIC");
});
test("IDs inválidos no llegan a Python", async () => {
  for (const productId of [0, -1, 1.2, true, [1], "1", null]) {
    const response = await exercise("ADMIN", "demand", { productId, locationId: 5 });
    assert.equal(response.status, 400);
    assert.equal(response.calls, 0);
  }
});
test("selección inexistente es 400 y fallo de modelo es 503 sin filtrar detalles", async () => {
  assert.equal((await exercise("ADMIN", "demand", { productId: 999, locationId: 5 }, "UNKNOWN_ENTITY")).status, 400);
  const response = await exercise("ADMIN", "demand", { productId: 1, locationId: 5 }, "contraseña privada");
  assert.equal(response.status, 503);
  assert.ok(!JSON.stringify(response.body).includes("contraseña"));
});
test("HTTP → Node → Python → V2 fijado: catálogo, replay y snapshots reales sin BD", async () => {
  const catalog = await exercise("ADMIN", "catalog", undefined, undefined, true);
  assert.equal(catalog.status, 200);
  assert.equal(catalog.body.products.length, 56);
  assert.equal(catalog.body.version, "V2.2.0");
  assert.equal(catalog.body.defaultTargetMonth, "2026-06");
  const response = await exercise("ADMIN", "demand", { productId: 20, locationId: 5 }, undefined, true);
  assert.equal(response.status, 200);
  assert.equal(response.body.targetMonth, "2026-06");
  assert.equal(response.body.prediction, 0);
  assert.equal(response.body.version, "V2.2.0");
  assert.equal(response.body.policyVersion, "NONNEGATIVE_CONTINUOUS_1");
  assert.equal(response.body.artifactSha256, "def5a93dcabf27916d1120af0160d2910dc7737f4036ec2507f60eb7d5670f35");
  assert.equal(response.body.metrics.mae, 9.204618055555557);
  assert.deepEqual(response.body.history.map((r: any) => r.month), ["2026-03", "2026-04", "2026-05"]);
  const explicit = await exercise("ADMIN", "demand", {productId:20, locationId:5, targetMonth:response.body.targetMonth, historySnapshotId:response.body.historySnapshotId}, undefined, true);
  assert.equal(explicit.body.prediction, response.body.prediction);
  assert.equal((await exercise("ADMIN", "demand", {productId:20,locationId:5,targetMonth:"2026-06",historySnapshotId:"incorrect"}, undefined, true)).status, 409);
  assert.equal((await exercise("ADMIN", "demand", {productId:20,locationId:5,targetMonth:"2026-07"}, undefined, true)).status, 422);
  assert.equal((await exercise("ADMIN", "demand", { productId: 99999, locationId: 5 }, undefined, true)).status, 400);
});

test("variables, targets y snapshots inválidos se rechazan antes de Python", async () => {
  for (const extra of [{features:{}}, {target_ventas_mes:12}, {model:"V1"}, {role:"ADMIN"}, {targetMonth:null}, {targetMonth:"2026-13"}, {historySnapshotId:"x"}, {targetMonth:"2026-06",historySnapshotId:"../secret"}]) {
    const r = await exercise("ADMIN", "demand", {productId:1,locationId:5,...extra});
    assert.equal(r.status, 400); assert.equal(r.calls, 0);
  }
});

test("errores de snapshot, falta de historia e integridad tienen estados explícitos", async () => {
  for (const [code,status] of [["SNAPSHOT_MISMATCH",409],["UNAVAILABLE_REQUIRED_FEATURE",422],["INCOMPATIBLE_ARTIFACT",503],["MODEL_UNAVAILABLE",503]] as const) {
    const r = await exercise("ADMIN", "demand", {productId:1,locationId:5}, code);
    assert.equal(r.status,status); assert.ok(!JSON.stringify(r.body).includes(".env"));
  }
});

test("authenticate real rechaza ausencia o token inválido antes de cualquier consulta", async () => {
  for (const token of [undefined, "Bearer invalid-token"]) {
    const r = await exercise(null,"demand",{productId:1,locationId:5},undefined,false,true,token);
    assert.equal(r.status,401); assert.equal(r.calls,0);
  }
});

test("authenticate y authorize reales usan el rol vigente y rechazan sesiones revocadas con Prisma simulado", async () => {
  const jwt = (await import("jsonwebtoken")).default;
  const prisma = (await import("../../config/database")).default;
  const originalVerify = jwt.verify;
  const originalUser = prisma.user.findUnique;
  const originalAudit = prisma.auditLog.findFirst;
  let currentRole = "ADMIN";
  let revoked = false;
  try {
    // Solo se simulan claims y lecturas. No se firma con secretos ni se accede a BD.
    (jwt as any).verify = () => ({userId:1,iat:Math.floor(Date.now()/1000),role:"ADMIN"});
    (prisma.user as any).findUnique = async () => ({id:1,email:"fixture@example.invalid",locationId:5,role:{name:currentRole}});
    (prisma.auditLog as any).findFirst = async () => revoked ? {id:1} : null;
    assert.equal((await exercise(null,"catalog",undefined,undefined,false,true,"Bearer fixture-only")).status,200);
    for (const role of ["TIENDA","INVENTARIO"]) {
      currentRole=role;
      const r=await exercise(null,"demand",{productId:1,locationId:5},undefined,false,true,"Bearer fixture-only");
      assert.equal(r.status,403); assert.equal(r.calls,0);
    }
    currentRole="ADMIN"; revoked=true;
    const r=await exercise(null,"catalog",undefined,undefined,false,true,"Bearer fixture-only");
    assert.equal(r.status,401); assert.equal(r.calls,0);
  } finally {
    jwt.verify=originalVerify;
    prisma.user.findUnique=originalUser;
    prisma.auditLog.findFirst=originalAudit;
  }
});

test("puente Node rechaza V1, hashes ajenos y datos no finitos", async () => {
  const {validateDemandResponse} = await import("./predictions.service");
  const good = {version:"V2.2.0",origin:"SYNTHETIC",mode:"ACADEMIC_REPLAY",model:"RandomForestRegressor",artifactSha256:"def5a93dcabf27916d1120af0160d2910dc7737f4036ec2507f60eb7d5670f35",
    selectionId:"accepted-absolute-2.2-20261115-01",modelVersion:"accepted-absolute-2.2-20261115-01",datasetVersion:"2.2.0",buildId:"calibrated-20261115-01",policyVersion:"NONNEGATIVE_CONTINUOUS_1",contractVersion:"v2-inference-2.2-1",
    status:"OK",productId:1,locationId:5,targetMonth:"2026-06",horizonMonths:1,featureSnapshotSha256:"a".repeat(64),warnings:[],issuedAt:"2026-11-15T10:00:00Z",historySnapshotId:"fixture-approved",historyCutoff:"2026-06-01T00:00:00-04:00",prediction:1.25,baseline:1,
    history:[{month:"2026-03",units:1},{month:"2026-04",units:1},{month:"2026-05",units:1}],metrics:{mae:7,rmse:15,r2:.6},evaluationContext:{origin:"SYNTHETIC",split:"TEST",mae:7,rmse:15,r2:.6}};
  assert.equal(validateDemandResponse(good,{productId:1,locationId:5}),good);
  for (const value of [null, {...good,version:"V1"},{...good,artifactSha256:"different"},{...good,prediction:NaN},{...good,prediction:-1},{...good,prediction:Infinity},{...good,productId:2},{...good,history:[]},{...good,historyCutoff:"2026-06-01T00:00:00Z"},{...good,metrics:{mae:1,rmse:2,r2:.9}}]) {
    assert.throws(() => validateDemandResponse(value,{productId:1,locationId:5}));
  }
});
