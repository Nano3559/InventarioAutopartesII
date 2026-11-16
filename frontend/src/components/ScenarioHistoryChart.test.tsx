import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import ScenarioHistoryChart, { DemonstrationChart } from "./ScenarioHistoryChart";
import { checkedScenarioBase, type ScenarioResult } from "../services/scenarioView";
import { baseFixture, snapshot } from "../test/fixtures/demandScenario";

describe("gráfica de demostración y gráfica del modelo", () => {
  it("presenta enero a octubre de 2026 sin trasladar pronósticos de 2028 a ese periodo", async () => {
    const base=checkedScenarioBase(baseFixture(),snapshot);
    const result={ baseline:{salesUnits:1234}, scenario:{salesUnits:2345} } as ScenarioResult;
    const view=render(<DemonstrationChart reference={snapshot} throughMonth="2026-10" />);
    expect(screen.getByRole("img",{name:/Ventas del dataset/})).toBeInTheDocument();
    const table=screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(11);
    expect(within(table).getByText("enero de 2026")).toBeInTheDocument();
    expect(within(table).getByText("octubre de 2026")).toBeInTheDocument();
    expect(screen.queryByText("1234")).not.toBeInTheDocument();
    expect(screen.queryByText("2345")).not.toBeInTheDocument();
    view.rerender(<ScenarioHistoryChart base={base} result={result} reference={snapshot} />);
    expect(screen.getByRole("img",{name:/Historial hasta octubre de 2026/})).toBeInTheDocument();
    expect(within(screen.getByRole("table")).getByText("enero de 2026")).toBeInTheDocument();
    expect(within(screen.getByRole("table")).getByText("1234")).toBeInTheDocument();
    expect(within(screen.getByRole("table")).getByText("octubre de 2026")).toBeInTheDocument();
  });
});
