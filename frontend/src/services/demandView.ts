export const DEMAND_ARTIFACT = "def5a93dcabf27916d1120af0160d2910dc7737f4036ec2507f60eb7d5670f35";
export const REPLAY_MONTHS = ["2026-04", "2026-05", "2026-06"];
const releases: Record<string, {hash:string;selection:string;build:string;policy:string}> = {
  "V2.2.0": {hash:DEMAND_ARTIFACT,selection:"accepted-absolute-2.2-20261115-01",build:"calibrated-20261115-01",policy:"NONNEGATIVE_CONTINUOUS_1"},
  "V2.1.0": {hash:"e53cdb53f296b38098639f7dd7d748d5ecd088ea6353993d8d3f911ba32b6dfc",selection:"accepted-absolute-2.1-20261115-01",build:"expanded-20261115-01",policy:"NONNEGATIVE_V1"},
};
export interface DemandCatalog {
  products: { id: number; name: string; itemCode: string }[];
  locations: { id: number; name: string }[];
  catalogObservedAt: string; defaultTargetMonth: string; availableTargetMonths: string[];
  version: string; artifactSha256: string; origin: string; mode: string;
}
export interface DemandSelection { productId: number; locationId: number; targetMonth: string }
export interface DemandResult extends DemandSelection {
  status: "OK"; prediction: number; baseline: number; model: string; version: string;
  history: { month: string; units: number }[];
  metrics: { mae: number; rmse: number; r2: number };
  evaluationContext: { origin: string; split: string; mae: number; rmse: number; r2: number };
  datasetVersion: string; buildId: string; selectionId: string; artifactSha256: string;
  policyVersion: string; historySnapshotId: string; featureSnapshotSha256: string;
  historyCutoff: string; issuedAt: string; warnings: string[]; origin: string; mode: string;
}
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const positiveId = (v: unknown) => Number.isInteger(v) && Number(v) > 0 && Number(v) <= 2147483647;
const dateTime = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}-\d{2}T.+(?:Z|[+-]\d{2}:\d{2})$/.test(v) && Number.isFinite(Date.parse(v));
function common(v: any, expectedVersion = "V2.2.0") {
  const release=Object.prototype.hasOwnProperty.call(releases,expectedVersion) ? releases[expectedVersion] : undefined;
  return release && v && v.version === expectedVersion && v.artifactSha256 === release.hash && v.origin === "SYNTHETIC" && v.mode === "ACADEMIC_REPLAY";
}
export function checkedCatalog(v: any): DemandCatalog {
  if (!common(v,v?.version) || !Array.isArray(v.products) || !v.products.length || !v.products.every((p: any) => positiveId(p.id) && typeof p.name === "string" && typeof p.itemCode === "string") ||
      !Array.isArray(v.locations) || !v.locations.length || !v.locations.every((p: any) => positiveId(p.id) && typeof p.name === "string") ||
      new Set(v.products.map((p: any) => p.id)).size !== v.products.length || new Set(v.locations.map((p: any) => p.id)).size !== v.locations.length ||
      JSON.stringify(v.availableTargetMonths) !== JSON.stringify(REPLAY_MONTHS) || !REPLAY_MONTHS.includes(v.defaultTargetMonth) || !dateTime(v.catalogObservedAt)) {
    throw new Error("INCOMPATIBLE_RESPONSE");
  }
  return v;
}
export function checkedResult(v: any, selected: DemandSelection, expectedVersion = "V2.2.0"): DemandResult {
  const release=Object.prototype.hasOwnProperty.call(releases,expectedVersion) ? releases[expectedVersion] : undefined;
  if (!REPLAY_MONTHS.includes(selected.targetMonth) || !positiveId(selected.productId) || !positiveId(selected.locationId) ||
      !release || !common(v,expectedVersion) || v.status !== "OK" || v.model !== "RandomForestRegressor" || v.policyVersion !== release.policy ||
      v.selectionId !== release.selection || v.datasetVersion !== expectedVersion.slice(1) || v.buildId !== release.build ||
      v.productId !== selected.productId || v.locationId !== selected.locationId || v.targetMonth !== selected.targetMonth ||
      !finite(v.prediction) || v.prediction < 0 || !finite(v.baseline) || v.baseline < 0 ||
      !v.metrics || ![v.metrics.mae, v.metrics.rmse, v.metrics.r2].every(finite) || v.metrics.mae < 0 || v.metrics.rmse < 0 ||
      v.evaluationContext?.origin !== "SYNTHETIC" || v.evaluationContext?.split !== "TEST" || !["mae", "rmse", "r2"].every(k => v.metrics[k] === v.evaluationContext[k]) ||
      !Array.isArray(v.warnings) || !v.warnings.every((w: unknown) => typeof w === "string") ||
      typeof v.historySnapshotId !== "string" || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(v.historySnapshotId) ||
      typeof v.featureSnapshotSha256 !== "string" || !/^[a-f0-9]{64}$/.test(v.featureSnapshotSha256) || !dateTime(v.issuedAt) || !dateTime(v.historyCutoff) ||
      Date.parse(v.historyCutoff) !== Date.parse(`${selected.targetMonth}-01T04:00:00Z`) || !Array.isArray(v.history) || v.history.length !== 3) throw new Error("INCOMPATIBLE_RESPONSE");
  const [year, month] = selected.targetMonth.split("-").map(Number);
  const expected = [3, 2, 1].map(n => new Date(Date.UTC(year, month - 1 - n, 1)).toISOString().slice(0, 7));
  if (!v.history.every((r: any, i: number) => r.month === expected[i] && Number.isInteger(r.units) && r.units >= 0) || v.history[2].units !== v.baseline) throw new Error("INCOMPATIBLE_RESPONSE");
  return v;
}
export function demandError(error: unknown): string {
  const e = error as { message?: string; response?: { status?: number; data?: { code?: string } } };
  if (e?.message === "INCOMPATIBLE_RESPONSE") return "La respuesta no coincide con la selección o con el modelo V2 fijado. No se mostrará una predicción incompatible.";
  const status = e?.response?.status;
  if (status === 401) return "La sesión no es válida. Inicia sesión nuevamente.";
  if (status === 403) return "Solo ADMIN puede consultar esta sección.";
  if (status === 409) return "El snapshot cambió o no corresponde a la selección. Actualiza las referencias antes de consultar.";
  if (status === 422) return "No hay un snapshot aprobado para ese mes. No se completarán datos faltantes automáticamente.";
  if (status === 400) return "La selección no es válida. Revisa producto, tienda y mes.";
  if (status === 503) return "El modelo V2 no está disponible o no superó la verificación de integridad. No se sustituirá por V1.";
  return "No se pudo obtener la predicción. Comprueba la conexión y vuelve a intentar.";
}
