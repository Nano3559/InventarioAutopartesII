import { execFile } from "node:child_process";
import path from "node:path";
import fs from "node:fs/promises";
import { createHash, randomUUID } from "node:crypto";

const root = path.resolve(__dirname, "../../../..");
export const SCENARIO_ARTIFACT = "8d73bbfb769e432461f2a202e37842b47820a76627e46be3e4ba412e64562e1e";
export const SCENARIO_CONTRACT = "demand-scenarios-1.0.0";
export const SCENARIO_DELIVERY_HEADER = "X-Scenario-Delivery";
export const SCENARIO_RUNTIME_REVISION_HEADER = "X-Scenario-Runtime-Revision";
type ScenarioProvenance = { delivery: "computed" | "replayed"; runtimeRevision: string | null };
const runtimeRevisionPattern = /^sha256:[a-f0-9]{64}$/;
const runtimeSources = [
  "admin_scenarios.py",
  "v2/__init__.py",
  "v2/calendar2026.py",
  "v2/calendar2026_runtime.py",
  "v2/scenario_data.py",
  "v2/scenario_runtime.py",
];

async function runtimeRevision() {
  const sources = await Promise.all(runtimeSources.map(async name => {
    const contents = await fs.readFile(path.join(root, "ml/demand", name));
    return [name, createHash("sha256").update(contents).digest("hex")];
  }));
  return "sha256:" + createHash("sha256").update(JSON.stringify(sources)).digest("hex");
}
const finite = (v: unknown) => typeof v === "number" && Number.isFinite(v);
export function assertUniqueJsonKeys(raw: string) {
  // Syntax is checked by express.json first. Walk tokens to catch duplicate keys,
  // including escaped spellings, which JSON.parse alone would silently replace.
  const tokens = raw.match(/"(?:\\.|[^"\\])*"|[{}\[\],:]|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g) ?? [];
  let i = 0;
  function value() {
    const t = tokens[i++];
    if (t === "{") {
      const keys = new Set<string>();
      while (tokens[i] !== "}") {
        const key = JSON.parse(tokens[i++]);
        if (keys.has(key)) throw new Error("INVALID_INPUT");
        keys.add(key); i++; value(); if (tokens[i] !== ",") break; i++;
      }
      i++;
    } else if (t === "[") {
      while (tokens[i] !== "]") { value(); if (tokens[i] !== ",") break; i++; }
      i++;
    }
  }
  value();
}
export function validateScenarioOutput(value: any, action: string, payload: any) {
  if (!value || typeof value !== "object") throw new Error("MODEL_UNAVAILABLE");
  if (action === "snapshot") {
    if (value.baseSnapshotId !== payload.baseSnapshotId || value.origin !== "SYNTHETIC_SCENARIO_NOT_REAL_SALES") throw new Error("INCOMPATIBLE_ARTIFACT");
    return value;
  }
  const releases: Record<string, { hash: string; model: string }> = {
    "4.0.0": { hash: SCENARIO_ARTIFACT, model: "calendar-model-20261116-01" },
    "3.0.0": { hash: "1ae61ad487d22c3fa8c8e8b5acd0c20d03e1f25d1151a5f680bbd8596d07bde3", model: "scenarios-model-20261115-01" },
  };
  const pinned = releases[value.datasetVersion];
  if (value.contractVersion !== SCENARIO_CONTRACT || !pinned || value.artifactSha256 !== pinned.hash || value.modelVersion !== pinned.model || value.policyVersion !== "SCENARIO_NONNEGATIVE_1") throw new Error("INCOMPATIBLE_ARTIFACT");
  if (action === "capabilities") {
    if (value.status !== "AVAILABLE" || !Array.isArray(value.snapshots) || !value.snapshots.length) throw new Error("MODEL_UNAVAILABLE");
  } else {
    if (value.origin !== "SYNTHETIC_SCENARIO_NOT_REAL_SALES" || value.mode !== "HYPOTHETICAL_SCENARIO" || value.timeZone !== "America/La_Paz" || value.horizonMonths !== 1) throw new Error("MODEL_UNAVAILABLE");
    for (const key of ["baseSnapshotId", "productId", "locationId", "targetMonth"]) if (value[key] !== payload[key]) throw new Error("SNAPSHOT_MISMATCH");
    for (const item of [value.baseline, value.scenario]) {
      if (!item || (item.status === "OK" ? !finite(item.salesUnits) || item.salesUnits < 0 || item.reason !== null : item.salesUnits !== null || typeof item.reason !== "string")) throw new Error("MODEL_UNAVAILABLE");
    }
    if (!value.replenishment || !Array.isArray(value.impacts) || !/^[a-f0-9]{64}$/.test(value.scenarioInputSha256)) throw new Error("MODEL_UNAVAILABLE");
    if (value.deltaSalesUnits !== null && (!finite(value.deltaSalesUnits) || value.baseline.salesUnits === null || value.scenario.salesUnits === null || Math.abs(value.deltaSalesUnits - (value.scenario.salesUnits - value.baseline.salesUnits)) > 1e-6)) throw new Error("MODEL_UNAVAILABLE");
  }
  return value;
}
export async function scenarioQuery(action: "capabilities" | "snapshot" | "preview", payload: Record<string, unknown> = {}, reportRevision?: (revision: string) => void): Promise<any> {
  const revision = action === "preview" && reportRevision ? await runtimeRevision() : null;
  const python = process.env.DEMAND_PYTHON || path.join(root, "ml/demand/.venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  const response = await new Promise((resolve, reject) => {
    const child = execFile(python, ["-B", path.join(root, "ml/demand/admin_scenarios.py")], { cwd: root, timeout: 25000, maxBuffer: 4 * 1024 * 1024, windowsHide: true }, (error, stdout) => {
      try {
        const value = JSON.parse(stdout);
        if (error) {
          const code = value.error?.code;
          return reject(new Error(typeof code === "string" && /^[A-Z_]{1,80}$/.test(code) ? code : "MODEL_UNAVAILABLE"));
        }
        resolve(validateScenarioOutput(value, action, payload));
      } catch { reject(new Error("MODEL_UNAVAILABLE")); }
    });
    child.stdin?.on("error", () => {});
    child.stdin?.end(JSON.stringify({ ...payload, action }));
  });
  if (revision !== null) {
    if (await runtimeRevision() !== revision) throw new Error("MODEL_UNAVAILABLE");
    reportRevision?.(revision);
  }
  return response;
}

function canonical(value: any): string {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (value !== null && typeof value === "object") return "{" + Object.keys(value).sort().map(k => JSON.stringify(k) + ":" + canonical(value[k])).join(",") + "}";
  return JSON.stringify(value);
}
/** Durable synthetic-response cache, scoped to actor + key. Never writes to Neon. */
export function createScenarioPreview(query = scenarioQuery, directory = path.join(root, "ml/demand/tmp/scenario-preview-cache-v1")) {
  const pending = new Map<string, Promise<any>>();
  return async (actor: number, payload: Record<string, any>, reportProvenance?: (provenance: ScenarioProvenance) => void) => {
    if (!Number.isInteger(actor) || actor < 1 || typeof payload?.clientRequestId !== "string" || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(payload.clientRequestId)) throw new Error("INVALID_INPUT");
    const hash = (s: string) => createHash("sha256").update(s).digest("hex");
    const key = hash(`${actor}:${payload.clientRequestId}`), input = hash(canonical(payload));
    const file = path.join(directory, key + ".json");
    async function lookup() {
      try {
        const saved = JSON.parse(await fs.readFile(file, "utf8"));
        if (saved.input !== input) throw new Error("IDEMPOTENCY_CONFLICT");
        const response = validateScenarioOutput(saved.response, "preview", payload);
        const revision = saved.runtimeRevision;
        reportProvenance?.({ delivery: "replayed", runtimeRevision: typeof revision === "string" && runtimeRevisionPattern.test(revision) ? revision : null });
        return response;
      }
      catch (e: any) { if (e.code === "ENOENT") return undefined; throw e; }
    }
    const existing = await lookup(); if (existing !== undefined) return existing;
    const inFlight = pending.get(key);
    if (inFlight) { await inFlight; return lookup(); }
    if (pending.size >= 8) throw new Error("SCENARIO_BUSY");
    const operation = (async () => {
      let revision: string | null = null;
      const response = await query("preview", payload, value => { revision = value; });
      await fs.mkdir(directory, { recursive: true });
      // Exclusive publication handles a second process without overwriting evidence.
      const temporary = path.join(directory, key + "-" + randomUUID() + ".tmp");
      await fs.writeFile(temporary, JSON.stringify({ input, response, runtimeRevision: revision }), { flag: "wx" });
      try { await fs.link(temporary, file); }
      catch (e: any) { if (e.code === "EEXIST") return lookup(); throw e; }
      finally { await fs.unlink(temporary); }
      reportProvenance?.({ delivery: "computed", runtimeRevision: revision });
      return response;
    })();
    pending.set(key, operation);
    try { return await operation; } finally { pending.delete(key); }
  };
}
