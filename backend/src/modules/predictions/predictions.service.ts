import { execFile } from "node:child_process";
import path from "node:path";
import fs from "node:fs";

const root = path.resolve(__dirname, "../../../..");
const releases: Record<string, {hash: string; selection: string; build: string; policy: string; contract: string}> = {
  "2.2.0": {hash:"def5a93dcabf27916d1120af0160d2910dc7737f4036ec2507f60eb7d5670f35",selection:"accepted-absolute-2.2-20261115-01",build:"calibrated-20261115-01",policy:"NONNEGATIVE_CONTINUOUS_1",contract:"v2-inference-2.2-1"},
  "2.1.0": {hash:"e53cdb53f296b38098639f7dd7d748d5ecd088ea6353993d8d3f911ba32b6dfc",selection:"accepted-absolute-2.1-20261115-01",build:"expanded-20261115-01",policy:"NONNEGATIVE_V1",contract:"v2-inference-2.1-1"},
};
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const id = (v: unknown) => Number.isInteger(v) && Number(v) > 0 && Number(v) <= 2147483647;

export function validateDemandResponse(value: any, payload: Record<string, unknown>) {
  const release = process.env.DEMAND_RELEASE ?? "2.2.0";
  const expected = Object.prototype.hasOwnProperty.call(releases, release) ? releases[release] : undefined;
  if (!expected || !value || value.version !== `V${release}` || value.origin !== "SYNTHETIC" || value.mode !== "ACADEMIC_REPLAY" ||
      value.artifactSha256 !== expected.hash || value.selectionId !== expected.selection ||
      value.model !== "RandomForestRegressor" || value.datasetVersion !== release || value.buildId !== expected.build || value.policyVersion !== expected.policy) throw new Error("INCOMPATIBLE_ARTIFACT");
  if (payload.action === "catalog") {
    if (!Array.isArray(value.products) || !value.products.length || !value.products.every((p: any) => id(p.id) && typeof p.name === "string" && typeof p.itemCode === "string") ||
        !Array.isArray(value.locations) || !value.locations.length || !value.locations.every((l: any) => id(l.id) && typeof l.name === "string") ||
        new Set(value.products.map((p: any) => p.id)).size !== value.products.length ||
        new Set(value.locations.map((l: any) => l.id)).size !== value.locations.length ||
        JSON.stringify(value.availableTargetMonths) !== JSON.stringify(["2026-04", "2026-05", "2026-06"]) || value.defaultTargetMonth !== "2026-06") throw new Error("DEMAND_UNAVAILABLE");
  } else {
    if (value.status !== "OK" || value.productId !== payload.productId || value.locationId !== payload.locationId ||
        value.targetMonth !== (payload.targetMonth ?? "2026-06") || !finite(value.prediction) || value.prediction < 0 ||
        value.contractVersion !== expected.contract || value.modelVersion !== value.selectionId || value.horizonMonths !== 1 ||
        !finite(value.baseline) || value.baseline < 0 || typeof value.historySnapshotId !== "string" || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(value.historySnapshotId) ||
        typeof value.featureSnapshotSha256 !== "string" || !/^[a-f0-9]{64}$/.test(value.featureSnapshotSha256) ||
        !Array.isArray(value.warnings) || !value.warnings.every((w: unknown) => typeof w === "string") ||
        typeof value.issuedAt !== "string" || !Number.isFinite(Date.parse(value.issuedAt)) ||
        (payload.historySnapshotId !== undefined && value.historySnapshotId !== payload.historySnapshotId) ||
        !Array.isArray(value.history) || value.history.length !== 3 || !value.history.every((r: any) => typeof r.month === "string" && Number.isInteger(r.units) && r.units >= 0) ||
        !value.metrics || ![value.metrics.mae, value.metrics.rmse, value.metrics.r2].every(finite) || value.metrics.mae < 0 || value.metrics.rmse < 0) throw new Error("DEMAND_UNAVAILABLE");
    const [year, month] = value.targetMonth.split("-").map(Number);
    const historyMonths = [3, 2, 1].map(n => new Date(Date.UTC(year, month - 1 - n, 1)).toISOString().slice(0, 7));
    if (!value.history.every((r: any, i: number) => r.month === historyMonths[i]) || value.baseline !== value.history[2].units ||
        Date.parse(value.historyCutoff) !== Date.parse(`${value.targetMonth}-01T04:00:00Z`) ||
        value.evaluationContext?.split !== "TEST" || value.evaluationContext?.origin !== "SYNTHETIC" ||
        !["mae", "rmse", "r2"].every(k => value.metrics[k] === value.evaluationContext[k])) throw new Error("DEMAND_UNAVAILABLE");
  }
  return value;
}
export function demandQuery(payload: Record<string, unknown>): Promise<any> {
  if (!Object.prototype.hasOwnProperty.call(releases, process.env.DEMAND_RELEASE ?? "2.2.0")) return Promise.reject(new Error("INCOMPATIBLE_ARTIFACT"));
  const python = process.env.DEMAND_PYTHON || path.join(root, "ml/demand/.venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  return new Promise((resolve, reject) => {
    if (!fs.existsSync(python)) return reject(new Error("DEMAND_UNAVAILABLE"));
    const child = execFile(python, ["-B", path.join(root, "ml/demand/admin_prediction_v2.py")],
      { cwd: root, timeout: 25000, maxBuffer: 1024 * 1024, windowsHide: true }, (error, stdout) => {
        if (error) {
          try {
            const code = JSON.parse(stdout).error?.code;
            if (["INVALID_INPUT", "UNKNOWN_ENTITY", "SNAPSHOT_MISMATCH", "UNAVAILABLE_REQUIRED_FEATURE", "INCOMPATIBLE_ARTIFACT", "MODEL_UNAVAILABLE"].includes(code)) return reject(new Error(code));
          } catch { /* No devolver stderr, credenciales o rutas del servidor. */ }
          return reject(new Error("DEMAND_UNAVAILABLE"));
        }
        try { resolve(validateDemandResponse(JSON.parse(stdout), payload)); } catch { reject(new Error("DEMAND_UNAVAILABLE")); }
      });
    child.stdin?.on("error", () => {});
    child.stdin?.end(JSON.stringify(payload));
  });
}
