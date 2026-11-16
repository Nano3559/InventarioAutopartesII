import { describe, expect, it } from "vitest";
import { productChoices, scenarioDate, scenarioMonth } from "./scenarioPresentation";
import { snapshot } from "../test/fixtures/demandScenario";

describe("presentación de escenarios", () => {
  const sources = [
    { ...snapshot, productName: "Árbol", previousMonthUnits: 0 },
    { ...snapshot, productId: 2, productName: "Bujía", previousMonthUnits: 12 },
    { ...snapshot, productId: 3, productName: "Filtro" },
    { ...snapshot, baseSnapshotId: "other-store", locationId: 6, productId: 2, productName: "Bujía", previousMonthUnits: 999 },
    { ...snapshot, baseSnapshotId: "other-month", targetMonth: "2028-05", productId: 1, productName: "Árbol", previousMonthUnits: 999 },
  ];
  it("busca sin depender de acentos y ordena por nombre", () => {
    expect(productChoices(sources,snapshot,"", "az").map(s => s.productId)).toEqual([1,2,3]);
    expect(productChoices(sources,snapshot,"", "za").map(s => s.productId)).toEqual([3,2,1]);
    expect(productChoices(sources,snapshot,"bujia", "az").map(s => s.productId)).toEqual([2]);
    expect(productChoices(sources,snapshot,"inexistente", "az")).toEqual([]);
  });
  it("ordena ventas del mismo corte y tienda sin convertir ausencia en cero", () => {
    expect(productChoices(sources,snapshot,"", "most").map(s => s.productId)).toEqual([2,1,3]);
    expect(productChoices(sources,snapshot,"", "least").map(s => s.productId)).toEqual([1,2,3]);
  });
  it("muestra meses con año y fechas de Bolivia sin hora", () => {
    expect(scenarioMonth("2028-06")).toBe("junio de 2028");
    expect(scenarioDate("2028-04-01T00:00:00-04:00")).toBe("2028-04-01");
    expect(scenarioDate("2028-04-01T02:00:00Z")).toBe("2028-03-31");
    expect(scenarioDate("pedido-1")).toBe("pedido-1");
  });
});
