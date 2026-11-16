import type { Snapshot } from "./scenarioView";

export const spanishOrder = new Intl.Collator("es", { numeric: true, sensitivity: "base" });
export type ProductOrder = "az" | "za" | "most" | "least";
export function scenarioMonth(month: string): string {
  return new Intl.DateTimeFormat("es-BO", { month: "long", year: "numeric", timeZone: "UTC" })
    .format(new Date(`${month}-01T00:00:00Z`));
}
export function scenarioDate(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}T/.test(value) || !Number.isFinite(Date.parse(value))) return value;
  const parts = new Intl.DateTimeFormat("en", { timeZone: "America/La_Paz", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(value));
  const part = (type: string) => parts.find(p => p.type === type)?.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}
export function productChoices(snapshots: Snapshot[], selected: Snapshot, query: string, order: ProductOrder): Snapshot[] {
  const normalize = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es");
  // Rank only a single store and cutoff. Never sum overlapping snapshot histories.
  const candidates = snapshots.filter(s => s.locationId === selected.locationId && s.targetMonth === selected.targetMonth);
  return [...new Map(candidates.map(s => [s.productId, s])).values()]
    .filter(s => normalize(`${s.productName} ${s.productId}`).includes(normalize(query.trim())))
    .sort((a, b) => {
      const alpha = spanishOrder.compare(a.productName, b.productName) || a.productId - b.productId;
      if (order === "az") return alpha;
      if (order === "za") return -alpha;
      if (a.previousMonthUnits === undefined || b.previousMonthUnits === undefined) {
        if (a.previousMonthUnits === undefined && b.previousMonthUnits !== undefined) return 1;
        if (a.previousMonthUnits !== undefined && b.previousMonthUnits === undefined) return -1;
        return alpha;
      }
      return (order === "most" ? b.previousMonthUnits - a.previousMonthUnits : a.previousMonthUnits - b.previousMonthUnits) || alpha;
    });
}
