// Frontend contract adapter. All calculations come from the scenario API.
export const SCENARIO_CONTRACT = "demand-scenarios-1.0.0";
export function scenarioFailureText(error: unknown): string {
  const e = error as { isAxiosError?: boolean; response?: { status?: number; data?: { code?: string } }; request?: unknown };
  const messages: Record<string, string> = {
    INCOHERENT_PRICES: "El costo no puede superar al precio por mayor, ni este al precio por menor. Revisa también las fechas de vigencia.",
    INVALID_QUOTE_TIME: "La fecha de la cotización debe ser anterior o igual al inicio del mes del escenario.",
    INVALID_RESERVATION: "Las reservas no pueden superar el stock vendible ni las unidades pendientes del pedido.",
    INVALID_HISTORY_WINDOW: "Se requieren exactamente los tres meses cerrados anteriores, en orden.",
    INVALID_ORDER_PLAN: "Revisa los identificadores, las cantidades y las reservas de los pedidos.",
    INVALID_SHIPMENT_PLAN: "Revisa las cantidades y fechas de llegada de los envíos pendientes.",
    INVALID_QUANTITY: "Las cantidades deben ser enteras, no negativas y estar dentro de los límites admitidos.",
    SNAPSHOT_MISMATCH: "La referencia base ya no coincide. Actualiza las opciones antes de comparar.",
    IDEMPOTENCY_CONFLICT: "La petición cambió desde su primer envío. Actualiza las opciones para iniciar otra comparación.",
  };
  const code = e?.response?.data?.code;
  if (code && messages[code]) return messages[code];
  if (e?.response?.status === 401) return "La sesión venció. Inicia sesión nuevamente.";
  if (e?.response?.status === 403) return "Solo ADMIN puede comparar escenarios.";
  if (e?.response?.status === 429) return "Hay varias comparaciones en curso. Espera un momento y reintenta.";
  if (e?.response?.status === 400) return "Revisa las cantidades, importes y fechas del escenario.";
  if (e?.isAxiosError || e?.response || e?.request) return "No se pudo completar la comparación. Reintenta sin cambiar los datos para recuperar la misma petición.";
  return error instanceof Error ? error.message : "No se pudo completar la comparación.";
}
export const changeNames = ["history", "prices", "quote", "cost", "stock", "orders", "logistics"] as const;
export type ChangeName = typeof changeNames[number];
export type MonthlyHistory = { month: string; units: number; retailUnits: number; wholesaleUnits: number; unknownModeUnits: number };
export type Snapshot = { baseSnapshotId: string; productId: number; locationId: number; targetMonth: string; productName: string; locationName: string; previousMonthUnits?: number; historyMonthly?: MonthlyHistory[] };
export type Capabilities = { contractVersion: string; status: "AVAILABLE"; supportedChanges: ChangeName[]; snapshots: Snapshot[]; artifactSha256: string; datasetVersion: string; modelVersion: string; policyVersion: string; stockTrainingMax?: number };
export type OrderDraft = { orderId: string; mode: "POR_MENOR" | "POR_MAYOR"; outstandingUnits: string; reservedUnits: string; dueAt: string };
export type ShipmentDraft = { shipmentId: string; pendingUnits: string; reservedAfterHorizonUnits: string; expectedArrivalAt: string };
export type Draft = {
  enabled: Record<ChangeName, boolean>;
  history: { retailUnits: string; wholesaleUnits: string; unknownModeUnits: string }[];
  retail: string; wholesale: string; priceAt: string; quote: string; quoteAt: string;
  costMode: "SET_LANDED_COST_BS" | "SIMULATE_IMPORT_USD"; costBs: string; costUsd: string; freight: string; other: string; costAt: string;
  stock: string; orders: OrderDraft[]; shipments: ShipmentDraft[];
  supplierDays: string; internalDays: string; orderAt: string;
  replenish: boolean; safety: string; minimum: string; multiple: string; review: string;
};
export function emptyDraft(): Draft {
  return { enabled: Object.fromEntries(changeNames.map(n => [n, false])) as Draft["enabled"],
    history: Array.from({ length: 3 }, () => ({ retailUnits: "", wholesaleUnits: "", unknownModeUnits: "" })),
    retail: "", wholesale: "", priceAt: "", quote: "", quoteAt: "", costMode: "SET_LANDED_COST_BS", costBs: "", costUsd: "", freight: "", other: "", costAt: "", stock: "", orders: [], shipments: [], supplierDays: "", internalDays: "", orderAt: "", replenish: false, safety: "0", minimum: "0", multiple: "1", review: "0" };
}
function fail(message: string): never { throw new Error(message); }
function obj(v: unknown): Record<string, unknown> { return v !== null && typeof v === "object" && !Array.isArray(v) ? v as Record<string, unknown> : fail("Respuesta de escenarios inválida."); }
function text(v: unknown): string { return typeof v === "string" && v.length > 0 && v.length <= 2000 ? v : fail("Texto inválido en respuesta."); }
function token(v: unknown): string { const s = text(v); return /^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(s) ? s : fail("Identificador inválido."); }
function integer(v: unknown): number { return typeof v === "number" && Number.isSafeInteger(v) && v >= 0 && v <= 1e9 ? v : fail("Cantidad inválida en respuesta."); }
function finite(v: unknown): number { return typeof v === "number" && Number.isFinite(v) ? v : fail("Número inválido en respuesta."); }
function strings(v: unknown): string[] { return Array.isArray(v) && v.length <= 100 ? v.map(text) : fail("Lista inválida."); }
function instant(v: unknown): string { const s = text(v); return /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(s) && Number.isFinite(Date.parse(s)) ? s : fail("Fecha inválida o sin zona."); }
function checkedMonthlyHistory(value: unknown, targetMonth: string): MonthlyHistory[] {
  if (!Array.isArray(value) || !value.length || value.length > 36) fail("Historial mensual incompleto.");
  let previous = "";
  return value.map(item => {
    const r=obj(item), month=text(r.month);
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(month) || month >= targetMonth || month <= previous) fail("Historial mensual fuera de orden o con información futura.");
    if (previous) { const d=new Date(`${previous}-01T00:00:00Z`); d.setUTCMonth(d.getUTCMonth()+1); if(d.toISOString().slice(0,7)!==month) fail("Faltan meses en el historial."); }
    previous=month;
    const retailUnits=integer(r.retailUnits),wholesaleUnits=integer(r.wholesaleUnits),unknownModeUnits=integer(r.unknownModeUnits),units=integer(r.units);
    if(units!==retailUnits+wholesaleUnits+unknownModeUnits) fail("Total mensual inconsistente.");
    return {month,units,retailUnits,wholesaleUnits,unknownModeUnits};
  });
}
export function checkedCapabilities(v: unknown): Capabilities {
  const d = obj(v);
  if (d.contractVersion !== SCENARIO_CONTRACT || d.status !== "AVAILABLE") fail("El backend de escenarios aún no está disponible o usa otro contrato.");
  if (!Array.isArray(d.supportedChanges) || !d.supportedChanges.every(n => changeNames.includes(n))) fail("Capacidades desconocidas.");
  if (new Set(d.supportedChanges).size !== d.supportedChanges.length) fail("Capacidades duplicadas.");
  if (!Array.isArray(d.snapshots) || !d.snapshots.length || d.snapshots.length > 20000) fail("No hay snapshots de escenarios autorizados.");
  const ids = new Set<string>();
  const snapshots = d.snapshots.map(v => {
    const s = obj(v); const id = token(s.baseSnapshotId);
    if (ids.has(id)) fail("Snapshot duplicado."); ids.add(id);
    const productId = integer(s.productId), locationId = integer(s.locationId);
    if (!productId || !locationId || typeof s.targetMonth !== "string" || !/^[1-9]\d{3}-(0[1-9]|1[0-2])$/.test(s.targetMonth)) fail("Referencia inválida.");
    const historyMonthly=s.historyMonthly === undefined ? undefined : checkedMonthlyHistory(s.historyMonthly,s.targetMonth);
    if(d.datasetVersion === "4.0.0" && (!historyMonthly || historyMonthly.length!==10 || historyMonthly[0].month!=="2026-01" || historyMonthly[9].month!=="2026-10" || s.targetMonth!=="2026-11")) fail("Calendario 4.0.0 incompatible.");
    return { baseSnapshotId: id, productId, locationId, targetMonth: s.targetMonth, productName: text(s.productName), locationName: text(s.locationName), ...(s.previousMonthUnits === undefined ? {} : { previousMonthUnits: integer(s.previousMonthUnits) }), ...(historyMonthly ? {historyMonthly} : {}) };
  });
  if (!/^[a-f0-9]{64}$/.test(String(d.artifactSha256))) fail("Falta integridad del modelo en capacidades.");
  return { contractVersion: SCENARIO_CONTRACT, status: "AVAILABLE", supportedChanges: [...new Set(d.supportedChanges)] as ChangeName[], snapshots, artifactSha256: String(d.artifactSha256), datasetVersion: token(d.datasetVersion), modelVersion: token(d.modelVersion), policyVersion: token(d.policyVersion), ...(d.stockTrainingMax===undefined?{}:{stockTrainingMax:integer(d.stockTrainingMax)}) };
}
export function priorMonths(month: string): string[] {
  const [y, m] = month.split("-").map(Number);
  return [3, 2, 1].map(n => new Date(Date.UTC(y, m - 1 - n, 1)).toISOString().slice(0, 7));
}
export function lpInstant(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) fail("Completa la fecha y hora en America/La_Paz.");
  const iso = value + ":00-04:00", ms = Date.parse(iso);
  if (!Number.isFinite(ms) || new Date(ms - 4 * 3600000).toISOString().slice(0, 16) !== value) fail("Fecha inexistente.");
  return iso;
}
function units(s: string, label: string, maximum = 1e9, minimum = 0): number {
  if (!/^(0|[1-9]\d*)$/.test(s) || Number(s) < minimum || Number(s) > maximum) fail(`${label}: usa un entero entre ${minimum} y ${maximum}.`);
  return Number(s);
}
function amount(s: string, label: string, rate = false, zero = false): string {
  const pattern = rate ? /^(0|[1-9]\d{0,5})(\.\d{1,6})?$/ : /^(0|[1-9]\d{0,8})(\.\d{1,4})?$/;
  if (!pattern.test(s) || (!zero && !/[1-9]/.test(s))) fail(`${label}: completa un decimal válido sin coma.`);
  return s;
}
function scaled(s: string): bigint { const [a, b = ""] = s.split("."); return BigInt(a) * 1000000n + BigInt(b.padEnd(6, "0")); }
export function scenarioRequest(d: Draft, s: Snapshot, supported: ChangeName[], requestId: string) {
  const cutoff = Date.parse(s.targetMonth + "-01T00:00:00-04:00");
  const [y, m] = s.targetMonth.split("-").map(Number);
  const end = Date.parse(`${new Date(Date.UTC(y, m, 1)).toISOString().slice(0, 7)}-01T00:00:00-04:00`);
  const changes: Record<string, unknown> = Object.fromEntries(changeNames.map(n => [n, { mode: "KEEP" }]));
  for (const n of changeNames) if (d.enabled[n] && !supported.includes(n)) fail(`El servidor no admite ${n}.`);
  function effective(value: string): string { const v = lpInstant(value); if (Date.parse(v) < cutoff || Date.parse(v) >= end) fail("La fecha de vigencia debe pertenecer al mes objetivo."); return v; }
  function planDate(value: string): string { const v = lpInstant(value); if (Date.parse(v) < cutoff) fail("El plan no puede comenzar antes del corte."); return v; }
  if (d.enabled.history) {
    if (d.history.length !== 3) fail("Se requieren tres meses cerrados completos.");
    changes.history = { mode: "REPLACE_SYNTHETIC_HISTORY", months: d.history.map((r, i) => ({ month: priorMonths(s.targetMonth)[i], retailUnits: units(r.retailUnits, "Por menor"), wholesaleUnits: units(r.wholesaleUnits, "Por mayor"), unknownModeUnits: units(r.unknownModeUnits, "Modalidad desconocida"), complete: true })) };
  }
  if (d.enabled.prices) {
    const retail = amount(d.retail, "Precio por menor"), wholesale = amount(d.wholesale, "Precio por mayor");
    if (scaled(wholesale) > scaled(retail)) fail("El precio por mayor no puede superar al precio por menor.");
    changes.prices = { mode: "SET_PRICES", retailPriceBs: retail, wholesalePriceBs: wholesale, effectiveAt: effective(d.priceAt) };
  }
  if (d.enabled.quote) {
    const observedAt = lpInstant(d.quoteAt);
    if (Date.parse(observedAt) > cutoff) fail("La cotización debe estar disponible al corte.");
    changes.quote = { mode: "SET_HYPOTHETICAL_QUOTE", bsPerUsd: amount(d.quote, "Cotización", true), observedAt };
  }
  if (d.enabled.cost) {
    const effectiveAt = effective(d.costAt);
    changes.cost = d.costMode === "SET_LANDED_COST_BS" ? { mode: d.costMode, unitCostBs: amount(d.costBs, "Costo Bs", false, true), effectiveAt } : { mode: d.costMode, unitCostUsd: amount(d.costUsd, "Costo USD", false, true), freightPerUnitBs: amount(d.freight, "Flete Bs", false, true), otherPerUnitBs: amount(d.other, "Otros Bs", false, true), effectiveAt };
    if (d.costMode === "SET_LANDED_COST_BS" && d.enabled.prices && scaled(d.costBs) > scaled(d.wholesale)) fail("El costo no puede superar al precio por mayor.");
  }
  if (d.enabled.stock) changes.stock = { mode: "SET_SELLABLE_STOCK", sellablePhysicalUnits: units(d.stock, "Stock físico vendible") };
  if (d.enabled.orders) {
    const ids = new Set<string>(); let reserved = 0;
    const orders = d.orders.map(o => {
      const id = token(o.orderId); if (ids.has(id)) fail("Identificador de pedido duplicado."); ids.add(id);
      const outstanding = units(o.outstandingUnits, "Pendientes", 1e9, 1), reservation = units(o.reservedUnits, "Reservadas"); reserved += reservation;
      if (reservation > outstanding) fail("Las reservas no pueden superar la cantidad pendiente.");
      return { orderId: id, mode: o.mode, outstandingUnits: outstanding, reservedUnits: reservation, dueAt: lpInstant(o.dueAt) };
    });
    if (d.enabled.stock && reserved > units(d.stock, "Stock")) fail("Las reservas superan el stock físico vendible.");
    changes.orders = { mode: "REPLACE_OPEN_ORDER_PLAN", orders };
  }
  if (d.enabled.logistics) {
    const ids = new Set<string>();
    changes.logistics = { mode: "SET_LOGISTICS_PLAN", supplierLeadTimeDays: units(d.supplierDays, "Plazo proveedor", 3650), internalRestockDays: units(d.internalDays, "Plazo interno", 3650), plannedOrderAt: planDate(d.orderAt), pendingShipments: d.shipments.map(o => {
      const id = token(o.shipmentId); if (ids.has(id)) fail("Identificador de envío duplicado."); ids.add(id);
      const pending = units(o.pendingUnits, "En tránsito", 1e9, 1), reserved = units(o.reservedAfterHorizonUnits, "Reservadas posteriores");
      if (reserved > pending) fail("La reserva de un envío supera sus unidades pendientes.");
      return { shipmentId: id, pendingUnits: pending, reservedAfterHorizonUnits: reserved, expectedArrivalAt: planDate(o.expectedArrivalAt) };
    }) };
  }
  if (d.orders.length > 100 || d.shipments.length > 100) fail("Máximo 100 pedidos o envíos.");
  return { contractVersion: SCENARIO_CONTRACT, mode: "HYPOTHETICAL_SCENARIO", clientRequestId: token(requestId), productId: s.productId, locationId: s.locationId, targetMonth: s.targetMonth, baseSnapshotId: s.baseSnapshotId, changes,
    replenishment: { requested: d.replenish, safetyStockUnits: units(d.safety, "Seguridad"), policy: "MONTH_END_COMMITMENT_FLOOR_V1", minimumOrderUnits: units(d.minimum, "Pedido mínimo"), orderMultipleUnits: units(d.multiple, "Múltiplo", 1e9, 1), reviewPeriodDays: units(d.review, "Revisión", 3650) } };
}
type Estimate = { status: string; salesUnits: number | null; reason: string | null };
export type ScenarioResult = { scenarioId: string; datasetVersion: string; modelVersion: string; artifactSha256: string; policyVersion: string; status: string; baseline: Estimate; scenario: Estimate; deltaSalesUnits: number | null; impacts: { field: string; role: string; effectStatus: string; explanation: string; before: string | number | boolean | null; after: string | number | boolean | null; unit: string }[]; assumptions: string[]; warnings: string[]; replenishment: Record<string, string | number | string[] | null>; metrics: { mae: number; rmse: number; r2: number | null; partition: string } | null };
export function checkedScenario(v: unknown, selected: Snapshot, capabilities: Capabilities): ScenarioResult {
  const d = obj(v);
  if (d.contractVersion !== SCENARIO_CONTRACT || d.mode !== "HYPOTHETICAL_SCENARIO" || d.origin !== "SYNTHETIC_SCENARIO_NOT_REAL_SALES" || d.timeZone !== "America/La_Paz" || d.horizonMonths !== 1) fail("La respuesta no corresponde al contrato académico.");
  for (const key of ["productId", "locationId", "targetMonth", "baseSnapshotId"] as const) if (d[key] !== selected[key]) fail("La respuesta pertenece a otra selección o snapshot.");
  if (!/^[a-f0-9]{64}$/.test(String(d.artifactSha256)) || !/^[a-f0-9]{64}$/.test(String(d.scenarioInputSha256))) fail("Falta integridad de artefacto o entradas.");
  const cutoff = Date.parse(selected.targetMonth + "-01T00:00:00-04:00");
  if (Date.parse(instant(d.featureCutoffAt)) !== cutoff || Date.parse(instant(d.assumedAsOf)) !== cutoff) fail("Corte de escenario inesperado.");
  instant(d.recordedAt);
  for (const key of ["artifactSha256", "datasetVersion", "modelVersion", "policyVersion"] as const) if (d[key] !== capabilities[key]) fail("El modelo cambió durante la consulta. Actualiza las capacidades.");
  function estimate(v: unknown): Estimate {
    const e = obj(v), status = text(e.status);
    if (!["OK", "UNSUPPORTED", "ABSTAINED", "OUT_OF_DOMAIN"].includes(status)) fail("Estado de estimación desconocido.");
    const salesUnits = e.salesUnits === null ? null : finite(e.salesUnits);
    if (salesUnits !== null && salesUnits < 0 || status === "OK" && salesUnits === null || status !== "OK" && salesUnits !== null) fail("Estimación inválida para su estado.");
    return { status, salesUnits, reason: e.reason === null ? null : token(e.reason) };
  }
  const baseline = estimate(d.baseline), scenario = estimate(d.scenario);
  const delta = d.deltaSalesUnits === null ? null : finite(d.deltaSalesUnits);
  if (baseline.salesUnits === null || scenario.salesUnits === null) { if (delta !== null) fail("No hay dos predicciones para calcular diferencia."); }
  else if (delta === null || Math.abs(delta - (scenario.salesUnits - baseline.salesUnits)) > 1e-6) fail("Diferencia inconsistente.");
  if (!Array.isArray(d.impacts) || d.impacts.length > 2000) fail("Impactos inválidos.");
  const scalar = (x: unknown): string | number | boolean | null => x === null || typeof x === "boolean" ? x : typeof x === "string" ? (x.length <= 2000 ? x : fail("Texto de impacto demasiado largo.")) : finite(x);
  const impacts = d.impacts.map(v => { const i = obj(v); const role = text(i.role), effectStatus = text(i.effectStatus);
    if (!["DIRECT_MODEL_FEATURE", "DERIVED_MODEL_FEATURE", "REPLENISHMENT_ONLY", "VALIDATION_ONLY", "UNSUPPORTED"].includes(role) || !["USED", "NOT_USED_BY_SELECTED_MODEL", "ASSUMPTION_ONLY", "UNKNOWN"].includes(effectStatus)) fail("Impacto desconocido.");
    return { field: text(i.field), role, effectStatus, explanation: text(i.explanation), before: scalar(i.before), after: scalar(i.after), unit: text(i.unit) };
  });
  const repos = obj(d.replenishment), status = text(repos.status);
  if (!["NOT_REQUESTED", "OK_MONTH_END_ESTIMATE", "INCOMPLETE", "OUTSIDE_FORECAST_HORIZON"].includes(status) || repos.policy !== "MONTH_END_COMMITMENT_FLOOR_V1" || repos.temporalFeasibility !== "MONTH_END_ONLY_NO_DAILY_STOCKOUT_GUARANTEE") fail("Política de reposición desconocida.");
  const replenishment: ScenarioResult["replenishment"] = { status, warnings: strings(repos.warnings) };
  for (const key of ["suggestedUnits", "requiredUnits", "availablePositionUnits", "committedUnitsWithinHorizon", "reservedUnitsWithinHorizon", "reservedUnitsAfterHorizon", "eligibleIncomingUnits", "rawNeedUnits", "minimumOrderUnits", "orderMultipleUnits"]) replenishment[key] = repos[key] === null ? null : integer(repos[key]);
  for (const key of ["expectedNewOrderArrivalAt", "protectionEndAt"]) replenishment[key] = repos[key] === null ? null : instant(repos[key]);
  if (status !== "OK_MONTH_END_ESTIMATE" && replenishment.suggestedUnits !== null) fail("Reposición no disponible debe permanecer nula.");
  if (status === "OK_MONTH_END_ESTIMATE" && replenishment.suggestedUnits === null) fail("Falta reposición calculada.");
  if (status === "OK_MONTH_END_ESTIMATE") {
    const required = replenishment.requiredUnits, position = replenishment.availablePositionUnits, raw = replenishment.rawNeedUnits, minimum = replenishment.minimumOrderUnits, multiple = replenishment.orderMultipleUnits;
    if ([required, position, raw, minimum, multiple].some(x => typeof x !== "number") || Number(multiple) <= 0) fail("Faltan componentes de la reposición.");
    const need = Math.max(0, Number(required) - Number(position));
    const suggestion = need === 0 ? 0 : Math.ceil(Math.max(need, Number(minimum)) / Number(multiple)) * Number(multiple);
    if (raw !== need || replenishment.suggestedUnits !== suggestion) fail("Reposición inconsistente con mínimo, múltiplo o posición.");
  }
  const metrics = d.metrics === null ? null : obj(d.metrics);
  const outputMetrics = metrics === null ? null : { mae: finite(metrics.mae), rmse: finite(metrics.rmse), r2: metrics.r2 === null ? null : finite(metrics.r2), partition: text(metrics.partition) };
  if (outputMetrics && (outputMetrics.mae < 0 || outputMetrics.rmse < 0 || !["TRAIN_CV", "VALIDATION", "FINAL_TEST_SAVED"].includes(outputMetrics.partition) || metrics?.origin !== "SYNTHETIC")) fail("Métricas sin contexto sintético válido.");
  const resultStatus = text(d.status);
  if (!["OK", "PARTIAL", "UNSUPPORTED", "ABSTAINED"].includes(resultStatus)) fail("Estado global desconocido.");
  if (resultStatus === "OK" && (baseline.status !== "OK" || scenario.status !== "OK")) fail("Resultado incompleto marcado como OK.");
  return { scenarioId: token(d.scenarioId), datasetVersion: token(d.datasetVersion), modelVersion: token(d.modelVersion), artifactSha256: String(d.artifactSha256), policyVersion: token(d.policyVersion), status: resultStatus, baseline, scenario, deltaSalesUnits: delta, impacts, assumptions: strings(d.assumptions), warnings: strings(d.warnings), replenishment, metrics: outputMetrics };
}

export type ScenarioBase = ReturnType<typeof checkedScenarioBase>;
export function checkedScenarioBase(value: unknown, selected: Snapshot) {
  const v = obj(value);
  for (const k of ["baseSnapshotId", "productId", "locationId", "targetMonth"] as const) if (v[k] !== selected[k]) fail("La referencia base no coincide.");
  if (v.origin !== "SYNTHETIC_SCENARIO_NOT_REAL_SALES") fail("Origen del escenario inválido.");
  if (!Array.isArray(v.history) || v.history.length !== 3) fail("Falta historia cerrada.");
  const history = v.history.map((h, i) => { const r = obj(h); if (r.month !== priorMonths(selected.targetMonth)[i]) fail("Historia fuera de periodo."); return { month: String(r.month), retailUnits: integer(r.retailUnits), wholesaleUnits: integer(r.wholesaleUnits), unknownModeUnits: integer(r.unknownModeUnits) }; });
  if (!Array.isArray(v.orders) || !Array.isArray(v.shipments)) fail("Planes incompletos.");
  const orders = v.orders.map(x => { const o = obj(x); if (!["POR_MENOR", "POR_MAYOR"].includes(String(o.mode))) fail("Modalidad inválida."); return { orderId: token(o.orderId), mode: o.mode as "POR_MENOR" | "POR_MAYOR", outstandingUnits: String(integer(o.outstandingUnits)), reservedUnits: String(integer(o.reservedUnits)), dueAt: localDate(instant(o.dueAt)) }; });
  const shipments = v.shipments.map(x => { const o = obj(x); return { shipmentId: token(o.shipmentId), pendingUnits: String(integer(o.pendingUnits)), reservedAfterHorizonUnits: String(integer(o.reservedAfterHorizonUnits)), expectedArrivalAt: localDate(instant(o.expectedArrivalAt)) }; });
  const displayHistory=v.displayHistory === undefined ? undefined : checkedMonthlyHistory(v.displayHistory,selected.targetMonth);
  if(selected.historyMonthly && JSON.stringify(displayHistory)!==JSON.stringify(selected.historyMonthly)) fail("El historial no coincide con el catálogo aprobado.");
  for (const row of history) {
    const plotted = displayHistory?.find(h => h.month === row.month);
    if (plotted && (plotted.retailUnits !== row.retailUnits || plotted.wholesaleUnits !== row.wholesaleUnits || plotted.unknownModeUnits !== row.unknownModeUnits))
      fail("Las ventas utilizadas para predecir no coinciden con la gráfica.");
  }
  return { retail: amount(text(v.retail), "Precio por menor"), wholesale: amount(text(v.wholesale), "Precio por mayor"), costBs: amount(text(v.costBs), "Costo", false, true), quote: amount(text(v.quote), "Cotización", true), quoteAt: instant(v.quoteAt), stock: integer(v.stock), supplierDays: integer(v.supplierDays), internalDays: integer(v.internalDays), orderAt: instant(v.orderAt), history, orders, shipments, displayHistory };
}
function localDate(value: string) { return new Date(Date.parse(value) - 4 * 3600000).toISOString().slice(0, 16); }
export function draftFromBase(base: ScenarioBase, month: string): Draft {
  return { ...emptyDraft(), retail: base.retail, wholesale: base.wholesale, priceAt: month + "-01T00:00", costBs: base.costBs, costAt: month + "-01T00:00", quote: base.quote, quoteAt: localDate(base.quoteAt), stock: String(base.stock), supplierDays: String(base.supplierDays), internalDays: String(base.internalDays), orderAt: localDate(base.orderAt), history: base.history.map(h => ({ retailUnits: String(h.retailUnits), wholesaleUnits: String(h.wholesaleUnits), unknownModeUnits: String(h.unknownModeUnits) })), orders: base.orders, shipments: base.shipments };
}
