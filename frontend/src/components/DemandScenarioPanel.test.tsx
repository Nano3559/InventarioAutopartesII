import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DemandScenarioPanel from "./DemandScenarioPanel";
import api from "../services/api";
import { capabilities, resultFixture, baseFixture } from "../test/fixtures/demandScenario";
vi.mock("../services/api", () => ({ default: { get: vi.fn(), post: vi.fn() } }));
beforeEach(() => { vi.clearAllMocks(); vi.mocked(api.get).mockImplementation(async url => ({ data: String(url).includes("/snapshots/") ? baseFixture(String(url).split("/").pop()) : capabilities })); vi.mocked(api.post).mockResolvedValue({ data: resultFixture() }); });
async function ready() { await waitFor(() => expect(screen.getByRole("button", { name: "Comparar base e hipótesis" })).toBeEnabled()); }

function novemberSelections() {
  const snapshots = [1, 2].flatMap(productId => [5, 6].map(locationId => {
    const historyMonthly = Array.from({ length: 10 }, (_, i) => {
      const units = productId * 10 + locationId + i;
      return { month: `2026-${String(i + 1).padStart(2, "0")}`, units, retailUnits: units - 3, wholesaleUnits: 2, unknownModeUnits: 1 };
    });
    return { ...capabilities.snapshots[0], productId, locationId, productName: productId === 1 ? "Filtro" : "Bujía", locationName: `Tienda ${locationId - 4}`, baseSnapshotId: `nov-${productId}-${locationId}`, targetMonth: "2026-11", historyMonthly, previousMonthUnits: historyMonthly[9].units };
  }));
  const caps = { ...capabilities, datasetVersion: "4.0.0", snapshots };
  const base = (id: string) => {
    const s = snapshots.find(s => s.baseSnapshotId === id)!;
    return { ...baseFixture(), ...s, displayHistory: s.historyMonthly,
      quoteAt: "2026-10-31T00:00:00-04:00", orderAt: "2026-11-01T00:00:00-04:00",
      history: s.historyMonthly.slice(-3).map(({ month, retailUnits, wholesaleUnits, unknownModeUnits }) => ({ month, retailUnits, wholesaleUnits, unknownModeUnits })) };
  };
  const prediction = (id: string) => {
    const s = snapshots.find(s => s.baseSnapshotId === id)!;
    const units = s.productId * 10 + s.locationId;
    return { ...resultFixture(), ...s, datasetVersion: caps.datasetVersion, status: "OK", featureCutoffAt: "2026-11-01T00:00:00-04:00", assumedAsOf: "2026-11-01T00:00:00-04:00",
      baseline: { status: "OK", salesUnits: units, reason: null }, scenario: { status: "OK", salesUnits: units, reason: null }, deltaSalesUnits: 0, impacts: [] };
  };
  vi.mocked(api.get).mockImplementation(async url => ({ data: String(url).includes("/snapshots/") ? base(String(url).split("/").pop()!) : caps }));
  vi.mocked(api.post).mockImplementation(async (_url, payload) => ({ data: prediction((payload as {baseSnapshotId:string}).baseSnapshotId) }));
  return { snapshots, caps, base, prediction };
}
describe("interfaz ampliada de Ross", () => {
  it("selecciona el primero al pedir más o menos vendido en la tienda actual", async () => {
    novemberSelections(); render(<DemandScenarioPanel />); await ready();
    await userEvent.selectOptions(screen.getByLabelText("Ordenar productos"), "most"); await ready();
    expect(screen.getByLabelText("Producto")).toHaveValue("2");
    expect(screen.getByLabelText("Histórico mensual y pronósticos del escenario")).toHaveTextContent("Bujía · Tienda 1");
    await userEvent.selectOptions(screen.getByLabelText("Ordenar productos"), "least"); await ready();
    expect(screen.getByLabelText("Producto")).toHaveValue("1");
    expect(screen.getByRole("option", { name: "Filtro" })).toBeInTheDocument();
    expect(screen.getByText(/Orden según ventas de octubre de 2026 en Tienda 1/)).toBeInTheDocument();
  });
  it("envía precios, cantidades y cotización de noviembre y reemplaza la reposición con la respuesta nueva", async () => {
    const f = novemberSelections();
    vi.mocked(api.post).mockImplementation(async (_url, payload) => {
      const p = payload as any;
      const units = p.changes.history.mode !== "KEEP" ? 10 : p.changes.prices.mode !== "KEEP" ? 12 : 15;
      const result = f.prediction(p.baseSnapshotId);
      return { data: { ...result, scenario: { status: "OK", salesUnits: units, reason: null }, deltaSalesUnits: units - result.baseline.salesUnits,
        replenishment: { ...result.replenishment, status: "OK_MONTH_END_ESTIMATE", requiredUnits: units + 5, availablePositionUnits: 9, rawNeedUnits: units - 4, suggestedUnits: units - 4, minimumOrderUnits: 0, orderMultipleUnits: 1 } } };
    });
    render(<DemandScenarioPanel />); await ready();
    await userEvent.click(screen.getByRole("checkbox", { name: "Calcular reposición" }));
    await userEvent.clear(screen.getByLabelText("Seguridad (unidades)"));
    await userEvent.type(screen.getByLabelText("Seguridad (unidades)"), "5");
    const compare = screen.getByRole("button", { name: "Comparar base e hipótesis" });
    await userEvent.click(compare); await screen.findByRole("heading", { name: "Comparación" });
    expect(screen.getByText("11", { selector: "p.text-xl" })).toHaveTextContent("11 unidades sugeridas");
    await userEvent.click(screen.getByRole("checkbox", { name: "Modificar Precios" }));
    expect(screen.queryByRole("heading", { name: "Comparación" })).not.toBeInTheDocument();
    for (const [label, value] of [["Nuevo precio por menor (Bs/unidad)", "150"], ["Nuevo precio por mayor (Bs/unidad)", "127.5"]]) {
      await userEvent.clear(screen.getByLabelText(label)); await userEvent.type(screen.getByLabelText(label), value);
    }
    await userEvent.click(compare); await screen.findByRole("heading", { name: "Comparación" });
    expect(screen.getByText("8", { selector: "p.text-xl" })).toHaveTextContent("8 unidades sugeridas");
    expect((vi.mocked(api.post).mock.lastCall![1] as any).changes.prices).toMatchObject({ retailPriceBs: "150", wholesalePriceBs: "127.5", effectiveAt: "2026-11-01T00:00:00-04:00" });
    await userEvent.click(screen.getByRole("checkbox", { name: "Modificar Ventas previas" }));
    const quantity = screen.getAllByLabelText("Unidades por menor")[0];
    await userEvent.clear(quantity); await userEvent.type(quantity, "10");
    await userEvent.click(compare); await screen.findByRole("heading", { name: "Comparación" });
    expect(screen.getByText("6", { selector: "p.text-xl" })).toHaveTextContent("6 unidades sugeridas");
    const history = (vi.mocked(api.post).mock.lastCall![1] as any).changes.history.months;
    expect(history.map((h: any) => h.month)).toEqual(["2026-08", "2026-09", "2026-10"]);
    expect(history[0].retailUnits).toBe(10);
    await userEvent.click(screen.getByRole("checkbox", { name: "Modificar Tipo de cambio" }));
    expect(screen.getByText(/Por sí sola no cambia el pronóstico/)).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText("Cotización hipotética (Bs por USD)"));
    await userEvent.type(screen.getByLabelText("Cotización hipotética (Bs por USD)"), "9");
    await userEvent.click(compare); await screen.findByRole("heading", { name: "Comparación" });
    expect(screen.getByText("6", { selector: "p.text-xl" })).toHaveTextContent("6 unidades sugeridas");
    expect(vi.mocked(api.post).mock.lastCall![1]).toMatchObject({ targetMonth: "2026-11", replenishment: { requested: true, safetyStockUnits: 5 }, changes: { quote: { bsPerUsd: "9" } } });
  });
  it("actualiza meses, gráfica, orden y petición de noviembre para cada producto y tienda", async () => {
    const f = novemberSelections(); render(<DemandScenarioPanel />); await ready();
    for (const [product, store] of [[1, 5], [2, 5], [2, 6], [1, 6]]) {
      await userEvent.selectOptions(screen.getByLabelText("Producto"), String(product)); await ready();
      await userEvent.selectOptions(screen.getByLabelText("Tienda"), String(store)); await ready();
      expect(screen.queryByRole("heading", { name: "Comparación" })).not.toBeInTheDocument();
      const selected = f.snapshots.find(s => s.productId === product && s.locationId === store)!;
      const previous = within(screen.getByRole("region", { name: "Ventas anteriores para la predicción" }));
      expect(previous.getAllByRole("definition").map(n => n.textContent)).toEqual(selected.historyMonthly.slice(-3).map(h => `${h.units} unidades`));
      const chart = within(screen.getByLabelText("Histórico mensual y pronósticos del escenario"));
      expect(chart.getByText(`${selected.productName} · ${selected.locationName}`)).toBeInTheDocument();
      await userEvent.click(chart.getByText("Datos de la gráfica"));
      const rows = chart.getAllByRole("row");
      expect(rows).toHaveLength(11);
      for (let i = 0; i < 10; i++) expect(within(rows[i + 1]).getAllByRole("cell")[1]).toHaveTextContent(String(selected.historyMonthly[i].units));
      await userEvent.click(screen.getByRole("button", { name: "Comparar base e hipótesis" }));
      await screen.findByRole("heading", { name: "Comparación" });
      expect(vi.mocked(api.post).mock.lastCall![1]).toMatchObject({ productId: product, locationId: store, targetMonth: "2026-11", baseSnapshotId: selected.baseSnapshotId });
      expect(chart.getAllByRole("row")).toHaveLength(13);
      expect(chart.getByRole("row", { name: `Pronóstico base ${product * 10 + store}` })).toBeInTheDocument();
    }
  });
  it("ignora la referencia tardía de otra tienda mientras carga la selección nueva", async () => {
    const f = novemberSelections(); let resolve!: (value: unknown) => void;
    vi.mocked(api.get).mockImplementation(async url => {
      if (!String(url).includes("/snapshots/")) return { data: f.caps };
      const id = String(url).split("/").pop()!;
      if (id === "nov-1-6") return new Promise(r => { resolve = r; });
      return { data: f.base(id) };
    });
    render(<DemandScenarioPanel />); await ready();
    await userEvent.selectOptions(screen.getByLabelText("Tienda"), "6");
    expect(screen.queryByRole("region", { name: "Ventas anteriores para la predicción" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Histórico mensual y pronósticos del escenario")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Comparar base e hipótesis" })).toBeDisabled();
    await userEvent.selectOptions(screen.getByLabelText("Producto"), "2"); await ready();
    await act(async () => { resolve({ data: f.base("nov-1-6") }); });
    expect(screen.getByLabelText("Histórico mensual y pronósticos del escenario")).toHaveTextContent("Bujía · Tienda 2");
    expect(within(screen.getByRole("region", { name: "Ventas anteriores para la predicción" })).getAllByRole("definition").map(n => n.textContent)).toEqual(["33 unidades", "34 unidades", "35 unidades"]);
  });
  it.each(["Producto", "Tienda"])("descarta una predicción anterior al cambiar %s", async field => {
    const f = novemberSelections(); let resolve!: (value: unknown) => void;
    vi.mocked(api.post).mockImplementationOnce(() => new Promise(r => { resolve = r; }));
    render(<DemandScenarioPanel />); await ready();
    await userEvent.click(screen.getByRole("button", { name: "Comparar base e hipótesis" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledOnce());
    await userEvent.selectOptions(screen.getByLabelText(field), field === "Producto" ? "2" : "6"); await ready();
    await act(async () => { resolve({ data: f.prediction("nov-1-5") }); });
    expect(screen.queryByRole("heading", { name: "Comparación" })).not.toBeInTheDocument();
    expect(screen.queryByRole("row", { name: /Pronóstico base/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Comparar base e hipótesis" }));
    await screen.findByRole("heading", { name: "Comparación" });
    expect(vi.mocked(api.post).mock.lastCall![1]).toMatchObject({ baseSnapshotId: field === "Producto" ? "nov-2-5" : "nov-1-6", targetMonth: "2026-11" });
  });
  it("separa agosto, septiembre y octubre para noviembre y deja solo nombres al ordenar por ventas", async () => {
    const selected = { ...capabilities.snapshots[0], targetMonth: "2026-11", previousMonthUnits: 130 };
    const months = ["2026-08", "2026-09", "2026-10"];
    const totals = [50, 74, 130];
    const history = months.map((month, i) => ({ month, retailUnits: totals[i] - 10, wholesaleUnits: 7, unknownModeUnits: 3 }));
    const displayHistory = selected.historyMonthly!.map(h => {
      const index = months.indexOf(h.month);
      return index < 0 ? h : { ...h, units: totals[index], ...history[index] };
    });
    selected.historyMonthly = displayHistory;
    const base = { ...baseFixture(), targetMonth: "2026-11", history, displayHistory };
    vi.mocked(api.get).mockImplementation(async url => ({ data: String(url).includes("/snapshots/")
      ? base : { ...capabilities, snapshots: [selected] } }));
    render(<DemandScenarioPanel />); await ready();
    const previous = within(screen.getByRole("region", { name: "Ventas anteriores para la predicción" }));
    expect(previous.getByText("Referencia base para predecir noviembre de 2026.")).toBeInTheDocument();
    for (const month of ["agosto de 2026", "septiembre de 2026", "octubre de 2026"]) expect(previous.getByText(month)).toBeInTheDocument();
    for (const total of totals) expect(previous.getByText(String(total), { exact: false, selector: "dd" })).toHaveTextContent(`${total} unidades`);
    for (const order of ["most", "least"]) {
      await userEvent.selectOptions(screen.getByLabelText("Ordenar productos"), order);
      expect(screen.getByRole("option", { name: "Filtro" })).toBeInTheDocument();
      expect(screen.queryByRole("option", { name: /130 u\./ })).not.toBeInTheDocument();
      expect(screen.getByText(/Orden según ventas de octubre de 2026 en Tienda 1/)).toBeInTheDocument();
    }
    expect(api.post).not.toHaveBeenCalled();
  });
  it("avisa cuando el stock real del snapshot excede el rango aprendido sin recortarlo", async () => {
    vi.mocked(api.get).mockImplementation(async url => ({ data: String(url).includes("/snapshots/")
      ? { ...baseFixture(), stock: 220 }
      : { ...capabilities, stockTrainingMax: 150 } }));
    render(<DemandScenarioPanel />); await ready();
    expect(screen.getByRole("status")).toHaveTextContent("El stock base (220 unidades) supera el rango aprendido (150)");
    expect(screen.getByLabelText("Valores base del escenario")).toHaveTextContent("220 u.");
  });
  it("omite la tabla vacía cuando la comparación no tiene cambios", async () => {
    vi.mocked(api.post).mockResolvedValue({data:{...resultFixture(),impacts:[]}});
    render(<DemandScenarioPanel/>); await ready();
    await userEvent.click(screen.getByRole("button",{name:"Comparar base e hipótesis"}));
    await screen.findByText("Comparación");
    expect(screen.queryByText("Ver cambios aplicados")).not.toBeInTheDocument();
    expect(screen.queryByText("Entradas antes y después. No todas son variables del modelo.")).not.toBeInTheDocument();
  });
  it("busca y ordena productos sin cambiar silenciosamente la referencia activa", async () => {
    render(<DemandScenarioPanel />); await ready();
    const select = screen.getByLabelText("Producto");
    expect(Array.from((select as HTMLSelectElement).options).filter(o => o.value).map(o => o.text)).toEqual(["Bujía", "Filtro"]);
    await userEvent.type(screen.getByLabelText("Buscar producto"), "bujia");
    expect(screen.queryByRole("option", { name: "Filtro" })).not.toBeInTheDocument();
    expect(select).toHaveValue("");
    expect(screen.getByLabelText("Valores base del escenario")).toHaveTextContent("Bs 120.00");
    await userEvent.selectOptions(select,"2"); await ready();
    expect(select).toHaveValue("2");
    await userEvent.clear(screen.getByLabelText("Buscar producto"));
    await userEvent.selectOptions(screen.getByLabelText("Ordenar productos"),"za");
    expect(Array.from((select as HTMLSelectElement).options).filter(o => o.value).map(o => o.text)).toEqual(["Filtro", "Bujía"]);
  });
  it("muestra historia del servidor y fechas de solo día sin romper el contrato temporal", async () => {
    render(<DemandScenarioPanel />); await ready();
    expect(screen.getByRole("option", { name: "abril de 2028" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Historial hasta octubre de 2026/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: "Modificar Precios" }));
    const date = screen.getByLabelText("Vigencia del nuevo precio (America/La_Paz)");
    expect(date).toHaveAttribute("type","date"); expect(date).toHaveValue("2028-04-01");
    await userEvent.clear(date); await userEvent.type(date,"2028-04-15");
    await userEvent.click(screen.getByRole("button", { name: "Comparar base e hipótesis" }));
    await screen.findByText("Comparación");
    expect((vi.mocked(api.post).mock.calls[0][1] as any).changes.prices.effectiveAt).toBe("2028-04-15T00:00:00-04:00");
  });
  it("muestra carga inicial sin anunciar una indisponibilidad antes de recibir capacidades", async () => {
    let resolve!: (value: unknown) => void;
    vi.mocked(api.get).mockImplementationOnce(() => new Promise(r => { resolve = r; }));
    render(<DemandScenarioPanel />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText(/todavía no están habilitados/)).not.toBeInTheDocument();
    await act(async () => { resolve({ data: capabilities }); });
    await ready();
    expect(screen.getByLabelText("Valores base del escenario")).toBeInTheDocument();
  });
  it("conserva la clave de petición al recuperar una respuesta perdida y la cambia al editar", async () => {
    vi.mocked(api.post).mockRejectedValueOnce(Object.assign(new Error("network"), { isAxiosError: true }));
    render(<DemandScenarioPanel />); await ready();
    const compare = screen.getByRole("button", { name: "Comparar base e hipótesis" });
    await userEvent.click(compare); expect(await screen.findByRole("alert")).toHaveTextContent(/recuperar la misma petición/);
    const first = (vi.mocked(api.post).mock.calls[0][1] as any).clientRequestId;
    await userEvent.click(compare); await screen.findByText("Comparación");
    expect((vi.mocked(api.post).mock.calls[1][1] as any).clientRequestId).toBe(first);
    await userEvent.click(screen.getByRole("checkbox", { name: "Modificar Precios" }));
    await userEvent.click(compare); await screen.findByText("Comparación");
    expect((vi.mocked(api.post).mock.calls[2][1] as any).clientRequestId).not.toBe(first);
  });
  it("explica un rechazo económico del backend sin mostrar un resultado anterior", async () => {
    vi.mocked(api.post).mockRejectedValueOnce({ response: { status: 400, data: { code: "INCOHERENT_PRICES" } } });
    render(<DemandScenarioPanel />); await ready();
    await userEvent.click(screen.getByRole("button", { name: "Comparar base e hipótesis" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/costo no puede superar al precio por mayor/);
    expect(screen.queryByText("Comparación")).not.toBeInTheDocument();
  });
  it("distingue productos que comparten nombre sin inventar códigos de catálogo", async () => {
    const duplicate = { ...capabilities.snapshots[0], baseSnapshotId: "same-name", productId: 3 };
    vi.mocked(api.get).mockImplementation(async url => ({ data: String(url).includes("/snapshots/") ? baseFixture() : { ...capabilities, snapshots: [...capabilities.snapshots, duplicate] } }));
    render(<DemandScenarioPanel />); await ready();
    expect(screen.getByRole("option", { name: "Filtro · #1" })).toHaveValue("1");
    expect(screen.getByRole("option", { name: "Filtro · #3" })).toHaveValue("3");
  });
  it("carga los importes del servidor y los conserva como KEEP hasta editar", async () => {
    render(<DemandScenarioPanel />); await ready();
    expect(screen.getByLabelText("Valores base del escenario")).toHaveTextContent("Bs 120.00");
    await userEvent.click(screen.getByRole("button", { name: "Comparar base e hipótesis" }));
    const payload = vi.mocked(api.post).mock.calls[0][1] as any;
    expect(payload.changes.prices).toEqual({ mode: "KEEP" });
    expect(payload.targetMonth).toBe("2028-04");
    expect(payload).not.toHaveProperty("target_ventas_mes");
  });
  it("no habilita comparar si falta una referencia base válida", async () => {
    vi.mocked(api.get).mockImplementation(async url => ({ data: String(url).includes("/snapshots/") ? { ...baseFixture(), productId: 999 } : capabilities }));
    render(<DemandScenarioPanel />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/referencia base/);
    expect(screen.getByRole("button", { name: "Comparar base e hipótesis" })).toBeDisabled();
    expect(api.post).not.toHaveBeenCalled();
  });
  it("muestra que no hay predicción nueva si la API está pendiente", async () => {
    vi.mocked(api.get).mockRejectedValue(new Error("404")); render(<DemandScenarioPanel />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/todavía no están habilitados/);
    expect(screen.queryByRole("button", { name: "Comparar base e hipótesis" })).not.toBeInTheDocument(); expect(screen.queryByRole("checkbox")).not.toBeInTheDocument(); expect(api.post).not.toHaveBeenCalled();
  });
  it("muestra los siete grupos y el cálculo de reposición separado", async () => {
    render(<DemandScenarioPanel />); await ready();
    expect(screen.getAllByRole("checkbox")).toHaveLength(8);
    await userEvent.click(screen.getAllByRole("checkbox")[1]);
    expect(screen.getByLabelText("Nuevo precio por menor (Bs/unidad)")).toHaveValue("120.00");
    expect(screen.getByLabelText("Nuevo precio por mayor (Bs/unidad)")).toHaveValue("100.00");
    expect(screen.queryByText("Precio 1")).not.toBeInTheDocument();
  });
  it("expone resultado parcial, antes/después y reposición no disponible", async () => {
    render(<DemandScenarioPanel />); await ready(); await userEvent.click(screen.getByRole("button", { name: "Comparar base e hipótesis" }));
    expect(await screen.findByText("Comparación")).toBeInTheDocument();
    expect(screen.getByText("150.00")).toBeInTheDocument(); expect(screen.getByText("120.00")).toBeInTheDocument();
    expect(screen.getByText("Hipótesis: No disponible", { selector: "span" })).toBeInTheDocument(); expect(screen.getByText("Reposición: Datos insuficientes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Exportar evidencia JSON/ })).toBeEnabled();
  });
  it("limpia el resultado cuando se cambia de snapshot", async () => {
    render(<DemandScenarioPanel />); await ready(); await userEvent.click(screen.getByRole("button", { name: "Comparar base e hipótesis" })); await screen.findByText("Comparación");
    await userEvent.selectOptions(screen.getByLabelText("Producto"), "2"); expect(screen.queryByText("Comparación")).not.toBeInTheDocument();
  });
  it("descarta una respuesta tardía tras una edición", async () => {
    let resolve!: (v: unknown) => void; vi.mocked(api.post).mockImplementation(() => new Promise(r => { resolve = r; }));
    render(<DemandScenarioPanel />); await ready(); await userEvent.click(screen.getByRole("button", { name: "Comparar base e hipótesis" }));
    await waitFor(() => expect(api.post).toHaveBeenCalled()); await userEvent.click(screen.getAllByRole("checkbox")[1]);
    await act(async () => { resolve({ data: resultFixture() }); });
    expect(screen.queryByText("Comparación")).not.toBeInTheDocument();
  });
  it("exporta solo la comparación validada como JSON, no RAW", async () => {
    const fixture = resultFixture();
    const revision = "sha256:" + "c".repeat(64);
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: fixture, headers: { "x-scenario-delivery": "computed", "x-scenario-runtime-revision": revision } })
      .mockResolvedValueOnce({ data: fixture, headers: { "x-scenario-delivery": "replayed", "x-scenario-runtime-revision": "unknown" } });
    render(<DemandScenarioPanel />); await ready(); await userEvent.click(screen.getByRole("button", { name: "Comparar base e hipótesis" })); await screen.findByText("Comparación");
    expect(screen.getByText("Respuesta nueva")).toBeVisible();
    expect(screen.getByText(revision)).toBeVisible();
    expect(screen.getByText("Generación original (La Paz)").parentElement?.querySelector("time")).toHaveAttribute("datetime", fixture.recordedAt);
    await userEvent.click(screen.getByRole("button", { name: "Comparar base e hipótesis" }));
    expect(await screen.findByText("Respuesta recuperada")).toBeVisible();
    expect(screen.getByText("Revisión desconocida")).toBeVisible();
    const create = vi.fn((_value: Blob | MediaSource) => "blob:fixture"); const revoke = vi.fn();
    const oldCreate = URL.createObjectURL, oldRevoke = URL.revokeObjectURL;
    URL.createObjectURL = create; URL.revokeObjectURL = revoke;
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    try {
      await userEvent.click(screen.getByRole("button", { name: /Exportar evidencia JSON/ }));
      expect(create).toHaveBeenCalledOnce(); expect(create.mock.calls[0][0]).toBeInstanceOf(Blob);
      expect((create.mock.calls[0][0] as Blob).type).toBe("application/json");
      const exportText = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = () => reject(reader.error);
        reader.readAsText(create.mock.calls[0][0] as Blob);
      });
      const exported = JSON.parse(exportText);
      expect(exported.provenance).toEqual({
        scenarioId: fixture.scenarioId, modelVersion: fixture.modelVersion, recordedAt: fixture.recordedAt,
        scenarioInputSha256: fixture.scenarioInputSha256, delivery: "replayed", runtimeRevision: null,
      });
      expect(exported.result.baseline).toEqual(fixture.baseline);
      expect(exported.result.scenario).toEqual(fixture.scenario);
      expect(exported.result.replenishment).toMatchObject({ status: "INCOMPLETE", suggestedUnits: null, availablePositionUnits: 9 });
      expect(exported.result.impacts).toHaveLength(1);
      expect(exported.result.impacts[0]).toMatchObject({ before: "120.00", after: "150.00" });
      expect(click).toHaveBeenCalledOnce(); expect(revoke).toHaveBeenCalledWith("blob:fixture");
    } finally { click.mockRestore(); URL.createObjectURL = oldCreate; URL.revokeObjectURL = oldRevoke; }
  });
  it.each([undefined, { "x-scenario-delivery": "unexpected", "x-scenario-runtime-revision": "malformed" }])(
    "mantiene los resultados cuando falta procedencia válida (%j)", async headers => {
      vi.mocked(api.post).mockResolvedValueOnce({ data: resultFixture(), headers });
      render(<DemandScenarioPanel />); await ready();
      await userEvent.click(screen.getByRole("button", { name: "Comparar base e hipótesis" }));
      expect(await screen.findByText("Procedencia desconocida")).toBeVisible();
      expect(screen.getByText("Revisión desconocida")).toBeVisible();
      expect(screen.getByRole("img", { name: "Comparación visual base e hipótesis" })).toHaveTextContent("Base: 18");
    },
  );
});
