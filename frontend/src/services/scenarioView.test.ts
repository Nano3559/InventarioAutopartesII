import { describe, expect, it } from "vitest";
import { changeNames, checkedCapabilities, checkedScenario, checkedScenarioBase, emptyDraft, lpInstant, priorMonths, scenarioRequest } from "./scenarioView";

import { snapshot, capabilities, resultFixture, baseFixture } from "../test/fixtures/demandScenario";
describe("contrato frontend de escenarios", () => {
  it("rechaza ventas de entrada distintas a la gráfica aunque coincidan los IDs del snapshot", () => {
    const selected={...snapshot,targetMonth:"2026-11"};
    const history=selected.historyMonthly!.slice(-3).map(({month,retailUnits,wholesaleUnits,unknownModeUnits})=>({month,retailUnits,wholesaleUnits,unknownModeUnits}));
    const base={...baseFixture(),...selected,history};
    expect(checkedScenarioBase(base,selected).history).toEqual(history);
    expect(()=>checkedScenarioBase({...base,history:history.map((h,i)=>i===2?{...h,retailUnits:h.retailUnits+1}:h)},selected)).toThrow(/no coinciden con la gráfica/);
    expect(()=>checkedScenarioBase({...base,history:history.map((h,i)=>i===2?{...h,retailUnits:h.retailUnits+1,wholesaleUnits:h.wholesaleUnits-1}:h)},selected)).toThrow(/no coinciden con la gráfica/);
  });
  it("unifica el historial 4.0.0 hasta octubre con noviembre sin permitir datos futuros", () => {
    const history=Array.from({length:10},(_,i)=>({month:`2026-${String(i+1).padStart(2,"0")}`,units:18,retailUnits:12,wholesaleUnits:6,unknownModeUnits:0}));
    const s={...snapshot,targetMonth:"2026-11",historyMonthly:history};
    const c={...capabilities,datasetVersion:"4.0.0",snapshots:[s]};
    expect(checkedCapabilities(c).snapshots[0].historyMonthly?.[9].month).toBe("2026-10");
    expect(()=>checkedCapabilities({...c,snapshots:[{...s,historyMonthly:[...history,{...history[0],month:"2026-11"}]}]})).toThrow();
    expect(()=>checkedCapabilities({...c,snapshots:[{...s,historyMonthly:history.map((h,i)=>i===9?{...h,units:99}:h)}]})).toThrow();
    expect(()=>checkedCapabilities({...c,snapshots:[{...s,targetMonth:"2028-04"}]})).toThrow();
  });
  it("no transforma KEEP en ceros o valores inventados", () => {
    const request = scenarioRequest(emptyDraft(), snapshot, [...changeNames], "test-1");
    expect(Object.values(request.changes)).toEqual(changeNames.map(() => ({ mode: "KEEP" })));
    expect(JSON.stringify(request)).not.toContain("6.96");
    expect(request).not.toHaveProperty("target_ventas_mes");
  });
  it("conserva decimales como strings y valida la regla económica", () => {
    const d = emptyDraft(); d.enabled.prices = true; d.retail = "150.00"; d.wholesale = "120.00"; d.priceAt = "2028-04-15T12:30";
    expect(scenarioRequest(d, snapshot, [...changeNames], "test-1").changes.prices).toEqual({ mode: "SET_PRICES", retailPriceBs: "150.00", wholesalePriceBs: "120.00", effectiveAt: "2028-04-15T12:30:00-04:00" });
    d.wholesale = "150.0001"; expect(() => scenarioRequest(d, snapshot, [...changeNames], "test-1")).toThrow(/no puede superar/);
  });
  it("rechaza un costo mayor al precio cuando ambos son explícitos", () => {
    const d = emptyDraft(); d.enabled.prices = d.enabled.cost = true; d.retail = "150"; d.wholesale = "100"; d.costBs = "110"; d.priceAt = d.costAt = "2028-04-01T00:00";
    expect(() => scenarioRequest(d, snapshot, [...changeNames], "test-1")).toThrow(/costo no puede/);
  });
  it("rechaza cantidades negativas, fraccionarias o vacías", () => {
    const d = emptyDraft(); d.enabled.stock = true;
    for (const value of ["", "-1", "1.5", "NaN", "1000000001"]) { d.stock = value; expect(() => scenarioRequest(d, snapshot, [...changeNames], "test-1")).toThrow(); }
    d.stock = "0"; expect(scenarioRequest(d, snapshot, [...changeNames], "test-1").changes.stock).toEqual({ mode: "SET_SELLABLE_STOCK", sellablePhysicalUnits: 0 });
  });
  it("valida fechas reales, cambios de mes y el corte UTC-4", () => {
    expect(priorMonths("2028-01")).toEqual(["2027-10", "2027-11", "2027-12"]);
    expect(lpInstant("2028-02-29T23:59")).toBe("2028-02-29T23:59:00-04:00");
    expect(() => lpInstant("2027-02-29T00:00")).toThrow();
    const d = emptyDraft(); d.enabled.quote = true; d.quote = "10.5"; d.quoteAt = "2028-04-01T00:01";
    expect(() => scenarioRequest(d, snapshot, [...changeNames], "test-1")).toThrow(/al corte/);
  });
  it("no permite editar variables que el backend no soporta", () => {
    const d = emptyDraft(); d.enabled.prices = true;
    expect(() => scenarioRequest(d, snapshot, [], "test-1")).toThrow(/no admite/);
  });
  it("separa costo USD y gastos Bs sin convertirlos en frontend", () => {
    const d = emptyDraft(); d.enabled.cost = true; d.costMode = "SIMULATE_IMPORT_USD"; d.costUsd = "10"; d.freight = "3"; d.other = "0"; d.costAt = "2028-04-01T00:00";
    expect(scenarioRequest(d, snapshot, [...changeNames], "test-1").changes.cost).toMatchObject({ unitCostUsd: "10", freightPerUnitBs: "3", otherPerUnitBs: "0" });
  });
  it("rechaza reservas imposibles y pedidos duplicados", () => {
    const d = emptyDraft(); d.enabled.orders = true; const order = { orderId: "o1", mode: "POR_MAYOR" as const, outstandingUnits: "100", reservedUnits: "101", dueAt: "2028-04-10T12:00" };
    d.orders = [order]; expect(() => scenarioRequest(d, snapshot, [...changeNames], "test-1")).toThrow(/reservas/);
    order.reservedUnits = "1"; d.orders = [order, order]; expect(() => scenarioRequest(d, snapshot, [...changeNames], "test-1")).toThrow(/duplicado/);
  });
  it("mantiene plazos largos como planes, sin prometer reposición dentro del mes", () => {
    const d = emptyDraft(); d.enabled.logistics = true; d.supplierDays = "60"; d.internalDays = "2"; d.orderAt = "2028-04-01T00:00";
    expect(scenarioRequest(d, snapshot, [...changeNames], "test-1").changes.logistics).toMatchObject({ supplierLeadTimeDays: 60, internalRestockDays: 2 });
  });
  it("acepta nulos de UNSUPPORTED y nunca los convierte en cero", () => {
    const result = checkedScenario(resultFixture(), snapshot, capabilities);
    expect(result.scenario.salesUnits).toBeNull(); expect(result.replenishment.suggestedUnits).toBeNull();
  });
  it("rechaza otra selección, artefacto, delta o estado inconsistentes", () => {
    for (const mutation of [{ productId: 2 }, { artifactSha256: "c".repeat(64) }, { deltaSalesUnits: 0 }, { scenario: { status: "OK", salesUnits: null, reason: null } }]) expect(() => checkedScenario({ ...resultFixture(), ...mutation }, snapshot, capabilities)).toThrow();
  });
  it("acepta capacidades válidas, rechaza referencias duplicadas y no disponibles", () => {
    expect(checkedCapabilities(capabilities).snapshots).toHaveLength(2);
    expect(() => checkedCapabilities({ ...capabilities, snapshots: [snapshot, snapshot] })).toThrow();
    expect(() => checkedCapabilities({ ...capabilities, status: "PENDING" })).toThrow();
  });
  it("valida una comparación completa y el redondeo comercial de reposición", () => {
    const response = resultFixture();
    const full = { ...response, status: "OK", scenario: { status: "OK", salesUnits: 14, reason: null }, deltaSalesUnits: -4,
      replenishment: { ...response.replenishment, status: "OK_MONTH_END_ESTIMATE", requiredUnits: 19, availablePositionUnits: 9, rawNeedUnits: 10, minimumOrderUnits: 20, orderMultipleUnits: 6, suggestedUnits: 24 } };
    expect(checkedScenario(full, snapshot, capabilities).replenishment.suggestedUnits).toBe(24);
    expect(() => checkedScenario({ ...full, replenishment: { ...full.replenishment, suggestedUnits: 20 } }, snapshot, capabilities)).toThrow(/Reposición inconsistente/);
  });
  it("rechaza un OK global con hipótesis no soportada o salida no finita", () => {
    expect(() => checkedScenario({ ...resultFixture(), status: "OK" }, snapshot, capabilities)).toThrow(/incompleto/);
    expect(() => checkedScenario({ ...resultFixture(), baseline: { status: "OK", salesUnits: Infinity, reason: null } }, snapshot, capabilities)).toThrow();
  });
  it("no permite que una llegada fuera del horizonte conserve una sugerencia", () => {
    const r = resultFixture(); r.replenishment.status = "OUTSIDE_FORECAST_HORIZON";
    expect(checkedScenario(r, snapshot, capabilities).replenishment.suggestedUnits).toBeNull();
    expect(() => checkedScenario({ ...r, replenishment: { ...r.replenishment, suggestedUnits: 0 } }, snapshot, capabilities)).toThrow();
  });
});
