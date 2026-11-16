import { describe, expect, it } from "vitest";
import { DEMONSTRATION_HISTORY, demonstrationHistory2026 } from "./demonstrationHistory";
import rawSnapshots from "../../../ml/demand/reports/v2/3.0.0/scenarios-model-20261115-01/snapshots.json?raw";

describe("historia de demostración independiente", () => {
  it("comprueba todos los productos y tiendas de las referencias aprobadas sin leer targets", () => {
    const snapshots=JSON.parse(rawSnapshots) as Record<string,{productId:number;locationId:number}>;
    const pairs=new Map(Object.values(snapshots).map(s=>[`${s.productId}:${s.locationId}`,s]));
    expect(new Set([...pairs.values()].map(s=>s.productId)).size).toBe(56);
    expect(new Set([...pairs.values()].map(s=>s.locationId)).size).toBe(3);
    expect(pairs.size).toBe(168);
    for(const s of pairs.values()) {
      const rows=demonstrationHistory2026(s.productId,s.locationId);
      expect(rows).toHaveLength(10);
      expect(rows).toEqual(demonstrationHistory2026(s.productId,s.locationId));
      for(const r of rows) {
        expect(Number.isSafeInteger(r.units)).toBe(true);
        expect(r.units).toBeGreaterThanOrEqual(0);
        expect(r.units).toBe(r.retailUnits+r.wholesaleUnits);
        expect(r.month).toMatch(/^2026-(0[1-9]|10)$/);
      }
    }
  });
  it("cubre diez meses consecutivos hasta octubre de 2026 con cantidades coherentes", () => {
    const rows = demonstrationHistory2026(39,5);
    expect(rows.map(r => r.month)).toEqual(Array.from({ length:10 },(_,i) => `2026-${String(i+1).padStart(2,"0")}`));
    for (const r of rows) {
      expect(Number.isSafeInteger(r.units)).toBe(true);
      expect(r.units).toBeGreaterThanOrEqual(0);
      expect(r.units).toBe(r.retailUnits+r.wholesaleUnits);
    }
    expect(DEMONSTRATION_HISTORY.origin).toBe("SYNTHETIC_ILLUSTRATION_NOT_DATASET_OR_FORECAST");
  });
  it("es reproducible por producto y tienda y no depende del reloj o del modelo", () => {
    expect(demonstrationHistory2026(39,5)).toEqual(demonstrationHistory2026(39,5));
    expect(demonstrationHistory2026(39,5)).not.toEqual(demonstrationHistory2026(39,6));
    expect(demonstrationHistory2026(39,5)).not.toEqual(demonstrationHistory2026(40,5));
    expect(() => demonstrationHistory2026(0,5)).toThrow();
  });
});
