import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, render as renderBase, screen, within, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import type { ReactElement } from "react";
import userEvent from "@testing-library/user-event";
import PredictionsPage from "../PredictionsPage";
import api from "../../services/api";
import { checkedCatalog, checkedResult, DEMAND_ARTIFACT, demandError } from "../../services/demandView";
import { capabilities as scenarioCapabilities, snapshot as scenarioSnapshot, baseFixture, resultFixture } from "../../test/fixtures/demandScenario";
function render(ui: ReactElement) {
  return renderBase(<MemoryRouter initialEntries={["/panel/prediccion?modo=historico"]}>{ui}</MemoryRouter>);
}
function LocationProbe() { const location = useLocation(); return <output data-testid="page-query">{location.search}</output>; }
vi.mock("../../services/api", () => ({ default: { get: vi.fn(), post: vi.fn() } }));
vi.mock("recharts", () => ({ ResponsiveContainer: ({ children }: any) => <div>{children}</div>, LineChart: ({ data }: any) => <div data-testid="chart" data-points={JSON.stringify(data)}>Gráfico</div>, Legend: () => null, Line: () => null, CartesianGrid: () => null, XAxis: () => null, YAxis: () => null, Tooltip: () => null }));
const catalog = { products: [{ id: 1, name: "Filtro", itemCode: "F-1" }, { id: 2, name: "Bujía", itemCode: "B-2" }], locations: [{ id: 5, name: "Tienda 1" }, {id:6,name:"Tienda 2"}], catalogObservedAt: "2026-10-28T01:08:41Z", defaultTargetMonth:"2026-06", availableTargetMonths:["2026-04","2026-05","2026-06"], version:"V2.2.0", artifactSha256:DEMAND_ARTIFACT, origin:"SYNTHETIC", mode:"ACADEMIC_REPLAY" };
function response(productId=1,locationId=5,targetMonth="2026-06",prediction=40.8725) {
  const [year,month]=targetMonth.split("-").map(Number);
  return {status:"OK",productId,locationId,targetMonth,prediction,baseline:21,model:"RandomForestRegressor",version:"V2.2.0",history:[3,2,1].map(n=>({month:new Date(Date.UTC(year,month-1-n,1)).toISOString().slice(0,7),units:n===1?21:25})),metrics:{mae:7.632738,rmse:15.42526,r2:.64287},evaluationContext:{origin:"SYNTHETIC",split:"TEST",mae:7.632738,rmse:15.42526,r2:.64287},datasetVersion:"2.2.0",buildId:"calibrated-20261115-01",selectionId:"accepted-absolute-2.2-20261115-01",artifactSha256:DEMAND_ARTIFACT,policyVersion:"NONNEGATIVE_CONTINUOUS_1",historySnapshotId:"fixture-approved",featureSnapshotSha256:"a".repeat(64),historyCutoff:`${targetMonth}-01T00:00:00-04:00`,issuedAt:"2026-11-15T06:00:00Z",warnings:["DATOS_SINTETICOS_NO_VALIDA_VENTAS_REALES"],origin:"SYNTHETIC",mode:"ACADEMIC_REPLAY"};
}
function deferred() { let resolve!:(value:any)=>void; let reject!:(error:any)=>void; const promise=new Promise((r,j)=>{resolve=r;reject=j;}); return {promise,resolve,reject}; }
async function ready() { await screen.findByRole("option", { name: "F-1 · Filtro" }); }
async function submit() { await userEvent.click(screen.getByRole("button", {name:"Consultar predicción"})); }
beforeEach(() => { vi.clearAllMocks(); vi.mocked(api.get).mockResolvedValue({data:catalog}); vi.mocked(api.post).mockImplementation(async (_url,p:any)=>({data:response(p.productId,p.locationId,p.targetMonth)})); });

describe("pantalla administrativa V2", () => {
  it("conserva producto, tienda y los tres meses al ir de Explorar a Predecir y de vuelta, consultando noviembre", async () => {
    const snapshots=[1,2].flatMap(productId=>[5,6].map(locationId=>({ ...scenarioSnapshot,
      productId,locationId,productName:productId===1?"Filtro":"Bujía",locationName:`Tienda ${locationId-4}`,targetMonth:"2026-11",baseSnapshotId:`tabs-${productId}-${locationId}`,
      historyMonthly:scenarioSnapshot.historyMonthly!.map((h,i)=>({...h,units:productId*10+locationId+i,retailUnits:productId*10+locationId+i-3,wholesaleUnits:2,unknownModeUnits:1}))
    })));
    const caps={...scenarioCapabilities,datasetVersion:"4.0.0",snapshots};
    vi.mocked(api.get).mockImplementation(async url=>{
      if(!String(url).includes("/snapshots/")) return {data:caps};
      const s=snapshots.find(s=>String(url).endsWith(s.baseSnapshotId))!;
      return {data:{...baseFixture(),...s,quoteAt:"2026-10-31T00:00:00-04:00",orderAt:"2026-11-01T00:00:00-04:00",displayHistory:s.historyMonthly,history:s.historyMonthly.slice(-3)}};
    });
    vi.mocked(api.post).mockImplementation(async (_url,p:any)=>{
      const s=snapshots.find(s=>s.baseSnapshotId===p.baseSnapshotId)!;
      const units=s.productId*10+s.locationId;
      return {data:{...resultFixture(),...s,datasetVersion:"4.0.0",status:"OK",featureCutoffAt:"2026-11-01T00:00:00-04:00",assumedAsOf:"2026-11-01T00:00:00-04:00",baseline:{status:"OK",salesUnits:units,reason:null},scenario:{status:"OK",salesUnits:units,reason:null},deltaSalesUnits:0,impacts:[]}};
    });
    renderBase(<MemoryRouter initialEntries={["/panel/prediccion?modo=demo"]}><PredictionsPage/><LocationProbe/></MemoryRouter>);
    for(const [i,[product,store]] of [[1,5],[2,6],[2,5],[1,6]].entries()) {
      await screen.findByLabelText("Mes del historial");
      await userEvent.selectOptions(screen.getByLabelText("Producto"),String(product));
      await userEvent.selectOptions(screen.getByLabelText("Tienda"),String(store));
      const previous=within(screen.getByRole("region",{name:"Resumen de ventas mensuales"})).getAllByRole("definition").map(n=>n.textContent);
      expect(api.post).toHaveBeenCalledTimes(i);
      await userEvent.click(screen.getByRole("button",{name:/^Predecir y comparar/}));
      await waitFor(()=>expect(screen.getByRole("button",{name:"Comparar base e hipótesis"})).toBeEnabled());
      expect(screen.getByLabelText("Producto")).toHaveValue(String(product));
      expect(screen.getByLabelText("Tienda")).toHaveValue(String(store));
      expect(screen.getByLabelText("Mes de predicción")).toHaveValue("2026-11");
      expect(within(screen.getByRole("region",{name:"Ventas anteriores para la predicción"})).getAllByRole("definition").map(n=>n.textContent)).toEqual(previous);
      expect(within(screen.getByRole("region",{name:"Ventas anteriores para la predicción"})).getAllByRole("term").map(n=>n.textContent)).toEqual(["agosto de 2026","septiembre de 2026","octubre de 2026"]);
      expect(screen.getByTestId("page-query")).toHaveTextContent(`productId=${product}&locationId=${store}`);
      await userEvent.click(screen.getByRole("button",{name:"Comparar base e hipótesis"}));
      await screen.findByRole("heading",{name:"Comparación"});
      expect(vi.mocked(api.post).mock.lastCall![1]).toMatchObject({productId:product,locationId:store,targetMonth:"2026-11",baseSnapshotId:`tabs-${product}-${store}`,changes:{history:{mode:"KEEP"}}});
      await userEvent.click(screen.getByRole("button",{name:/^Explorar ventas/}));
      await screen.findByLabelText("Mes del historial");
      expect(screen.getByLabelText("Producto")).toHaveValue(String(product));
      expect(screen.getByLabelText("Tienda")).toHaveValue(String(store));
      expect(within(screen.getByRole("region",{name:"Resumen de ventas mensuales"})).getAllByRole("definition").map(n=>n.textContent)).toEqual(previous);
      expect(api.post).toHaveBeenCalledTimes(i+1);
    }
  });
  it.each(["productId=999&locationId=999","productId=NaN&locationId=-1"])("recupera una selección aprobada si la URL contiene IDs inválidos: %s", async query => {
    vi.mocked(api.get).mockResolvedValue({data:scenarioCapabilities});
    renderBase(<MemoryRouter initialEntries={[`/panel/prediccion?modo=demo&${query}`]}><PredictionsPage/><LocationProbe/></MemoryRouter>);
    await screen.findByLabelText("Mes del historial");
    expect(screen.getByLabelText("Producto")).toHaveValue("1");
    expect(screen.getByLabelText("Tienda")).toHaveValue("5");
    await waitFor(()=>expect(screen.getByTestId("page-query")).toHaveTextContent("productId=1&locationId=5"));
    expect(api.post).not.toHaveBeenCalled();
  });
  it("recupera producto y tienda al recargar su URL y vuelve a leer tarjetas y gráfica del servidor", async () => {
    const snapshots=[1,2].flatMap(productId=>[5,6].map(locationId=>({ ...scenarioSnapshot,
      productId,locationId,productName:productId===1?"Filtro":"Bujía",locationName:`Tienda ${locationId-4}`,targetMonth:"2026-11",baseSnapshotId:`reload-${productId}-${locationId}`,
      historyMonthly:scenarioSnapshot.historyMonthly!.map((h,i)=>({ ...h, units:productId*10+locationId+i,retailUnits:productId*10+locationId+i-3,wholesaleUnits:2,unknownModeUnits:1 }))
    })));
    vi.mocked(api.get).mockResolvedValue({data:{...scenarioCapabilities,datasetVersion:"4.0.0",snapshots}});
    const page=renderBase(<MemoryRouter initialEntries={["/panel/prediccion?modo=demo&origen=panel"]}><PredictionsPage/><LocationProbe/></MemoryRouter>);
    await screen.findByLabelText("Mes del historial");
    await userEvent.selectOptions(screen.getByLabelText("Producto"),"2");
    await userEvent.selectOptions(screen.getByLabelText("Tienda"),"6");
    expect(screen.getByTestId("page-query")).toHaveTextContent("productId=2&locationId=6");
    const previous=within(screen.getByRole("region",{name:"Resumen de ventas mensuales"}));
    expect(previous.getAllByRole("definition").map(n=>n.textContent)).toEqual(["33 unidades","34 unidades","35 unidades"]);
    const url="/panel/prediccion"+screen.getByTestId("page-query").textContent;
    page.unmount();
    // A new page lifecycle must fetch fresh observations, not persist sales values.
    const fresh=snapshots.map(s=>({...s,historyMonthly:s.historyMonthly.map(h=>({...h,units:h.units+10,retailUnits:h.retailUnits+10}))}));
    vi.mocked(api.get).mockResolvedValue({data:{...scenarioCapabilities,datasetVersion:"4.0.0",snapshots:fresh}});
    renderBase(<MemoryRouter initialEntries={[url]}><PredictionsPage/><LocationProbe/></MemoryRouter>);
    await screen.findByLabelText("Mes del historial");
    expect(screen.getByLabelText("Producto")).toHaveValue("2");
    expect(screen.getByLabelText("Tienda")).toHaveValue("6");
    const summary=within(screen.getByRole("region",{name:"Resumen de ventas mensuales"}));
    expect(summary.getAllByRole("definition").map(n=>n.textContent)).toEqual(["43 unidades","44 unidades","45 unidades"]);
    const chart=within(screen.getByLabelText("Histórico mensual y pronósticos del escenario"));
    expect(chart.getByText("agosto de 2026: 43 unidades",{selector:"title"})).toBeInTheDocument();
    expect(chart.getByText("septiembre de 2026: 44 unidades",{selector:"title"})).toBeInTheDocument();
    expect(chart.getByText("octubre de 2026: 45 unidades",{selector:"title"})).toBeInTheDocument();
    expect(api.get).toHaveBeenCalledTimes(2);
    expect(api.post).not.toHaveBeenCalled();
  });
  it("abre la exploración 2026 por defecto y conserva el modo en la URL al alternar", async () => {
    renderBase(<MemoryRouter initialEntries={["/panel/prediccion?origen=panel"]}><PredictionsPage /><LocationProbe /></MemoryRouter>);
    expect(screen.getByRole("button", { name: /^Explorar ventas/ })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByText("Versiones anteriores"));
    await userEvent.click(screen.getByRole("button", { name: "Consulta histórica" }));
    await ready();
    expect(screen.getByTestId("page-query")).toHaveTextContent("origen=panel&modo=historico");
    await userEvent.click(screen.getByRole("button", { name: /^Predecir y comparar/ }));
    expect(screen.getByTestId("page-query")).toHaveTextContent("modo=escenarios");
  });
  it("restaura Escenarios al abrir nuevamente su URL sin ejecutar predicciones", async () => {
    renderBase(<MemoryRouter initialEntries={["/panel/prediccion?modo=escenarios"]}><PredictionsPage /></MemoryRouter>);
    expect(screen.getByRole("button", { name: /^Predecir y comparar/ })).toHaveAttribute("aria-pressed", "true");
    await screen.findByText(/Los escenarios todavía no están habilitados/);
    expect(api.post).not.toHaveBeenCalled();
  });
  it("muestra recuperación explícita y valida la versión del catálogo", async () => {
    const hash="e53cdb53f296b38098639f7dd7d748d5ecd088ea6353993d8d3f911ba32b6dfc";
    const recovered={...response(),version:"V2.1.0",artifactSha256:hash,datasetVersion:"2.1.0",buildId:"expanded-20261115-01",selectionId:"accepted-absolute-2.1-20261115-01",policyVersion:"NONNEGATIVE_V1"};
    vi.mocked(api.get).mockResolvedValue({data:{...catalog,version:"V2.1.0",artifactSha256:hash}});
    vi.mocked(api.post).mockResolvedValue({data:recovered});
    render(<PredictionsPage/>);await ready();await submit();
    await screen.findByText("40.87 unidades");expect(screen.getByText(/Recuperación explícita/)).toBeInTheDocument();
    expect(()=>checkedResult(recovered,{productId:1,locationId:5,targetMonth:"2026-06"},"V2.2.0")).toThrow();
  });
  it("ofrece solo meses aprobados y horizonte fijo sin enviar features", async () => {
    render(<PredictionsPage />); await ready();
    expect(screen.getByLabelText("Horizonte")).toHaveValue("1 mes");
    expect(screen.getByLabelText("Horizonte")).toHaveAttribute("readonly");
    const select=screen.getByLabelText("Mes de reproducción");
    expect(within(select).getAllByRole("option").map((x:any)=>x.value)).toEqual(catalog.availableTargetMonths);
    await userEvent.selectOptions(select,"2026-04"); await submit();
    await screen.findByText("Mes objetivo: 2026-04");
    expect(api.post).toHaveBeenCalledWith("/predictions/demand",{productId:1,locationId:5,targetMonth:"2026-04"},{signal:expect.any(AbortSignal)});
  });
  it("presenta resultado, gráfico sin target observado, tabla, métricas y trazabilidad", async () => {
    render(<PredictionsPage />); await ready(); await submit(); await screen.findByText("40.87 unidades");
    expect(screen.queryByText("Datos simulados")).not.toBeInTheDocument();
    expect(screen.getByText(/RandomForestRegressor · V2.2.0/)).toBeInTheDocument();
    const points=JSON.parse(screen.getByTestId("chart").getAttribute("data-points")!);
    expect(points).toHaveLength(4); expect(points[3]).toEqual({month:"2026-06",observed:null,forecast:40.8725,baseline:21});
    expect(screen.getByText("Datos del gráfico")).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText(/No se recalcula TEST/)).toBeInTheDocument();
    expect(screen.getByText(/El modelo puede subestimar pedidos grandes/)).toBeInTheDocument();
    expect(screen.getByText(DEMAND_ARTIFACT)).toHaveClass("break-all");
    expect(screen.getByText("fixture-approved")).toBeInTheDocument();
    expect(screen.getByText(/NONNEGATIVE_CONTINUOUS_1/)).toBeInTheDocument();
    expect(screen.getAllByText(/America\/La_Paz/).length).toBeGreaterThan(0);
  });
  it("limpia resultados al cambiar producto, tienda o mes", async () => {
    render(<PredictionsPage />); await ready();
    for (const [label,value] of [["Producto","2"],["Tienda","6"],["Mes de reproducción","2026-05"]]) {
      await submit(); await screen.findByText("40.87 unidades");
      await userEvent.selectOptions(screen.getByLabelText(label),value);
      expect(screen.queryByText("40.87 unidades")).not.toBeInTheDocument();
    }
  });
  it("muestra cero como predicción válida sin inventar reposición", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({data:response(1,5,"2026-06",0)});
    render(<PredictionsPage />); await ready(); await submit();
    await screen.findByText("0.00 unidades"); expect(screen.getByText(/No se calcula reposición/)).toBeInTheDocument();
  });
  it("permite recuperar un fallo de catálogo", async () => {
    vi.mocked(api.get).mockRejectedValueOnce(new Error("offline"));
    render(<PredictionsPage />);
    await userEvent.click(await screen.findByRole("button",{name:"Reintentar catálogo"})); await ready();
    expect(api.get).toHaveBeenCalledTimes(2);
  });
  it("rechaza catálogo vacío, V1 o meses TEST antes de habilitar consulta", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({data:{...catalog,availableTargetMonths:["2026-07"]}});
    render(<PredictionsPage />); await screen.findByRole("alert");
    expect(screen.queryByRole("button",{name:"Consultar predicción"})).not.toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();
    for (const bad of [{...catalog,products:[]},{...catalog,version:"V1"}]) expect(()=>checkedCatalog(bad)).toThrow();
  });
  it("no muestra respuestas de otro producto, snapshot incompleto o métricas inválidas", async () => {
    for (const bad of [{...response(),productId:2},{...response(),prediction:NaN},{...response(),prediction:-1},{...response(),artifactSha256:"other"},{...response(),history:[]},{...response(),featureSnapshotSha256:"bad"},{...response(),metrics:{mae:1,rmse:2,r2:.1}}]) {
      expect(()=>checkedResult(bad,{productId:1,locationId:5,targetMonth:"2026-06"})).toThrow();
    }
    vi.mocked(api.post).mockResolvedValueOnce({data:response(2)});
    render(<PredictionsPage />); await ready(); await submit();
    await screen.findByRole("alert"); expect(screen.queryByText("40.87 unidades")).not.toBeInTheDocument();
  });
  it("explica errores de API y permite reintentar sin resultados ficticios", async () => {
    vi.mocked(api.post).mockRejectedValueOnce({response:{status:409,data:{code:"SNAPSHOT_MISMATCH"}}});
    render(<PredictionsPage />); await ready(); await submit();
    await screen.findByText(/El snapshot cambió/);
    expect(screen.queryByText("40.87 unidades")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button",{name:"Reintentar consulta"})); await screen.findByText("40.87 unidades");
    for (const status of [401,403,400,422,503]) expect(demandError({response:{status}})).not.toContain("undefined");
    expect(demandError({response:{status:503}})).toContain("No se sustituirá por V1");
  });
  it("ignora una respuesta anterior aunque la petición no respete la cancelación", async () => {
    const old=deferred(); vi.mocked(api.post).mockReturnValueOnce(old.promise as any);
    render(<PredictionsPage />); await ready(); await submit();
    await userEvent.selectOptions(screen.getByLabelText("Producto"),"2");
    await submit(); await screen.findByText("40.87 unidades");
    await act(async()=>old.resolve({data:response(1,5,"2026-06",999)}));
    expect(screen.queryByText("999.00 unidades")).not.toBeInTheDocument();
    expect(screen.getByText("Bujía · Tienda 1")).toBeInTheDocument();
    expect((vi.mocked(api.post).mock.calls[0][2] as any).signal.aborted).toBe(true);
  });
  it("ignora un error tardío después de una consulta nueva correcta", async () => {
    const old=deferred(); vi.mocked(api.post).mockReturnValueOnce(old.promise as any);
    render(<PredictionsPage />); await ready(); await submit();
    await userEvent.selectOptions(screen.getByLabelText("Mes de reproducción"),"2026-05");
    await submit(); await screen.findByText("Mes objetivo: 2026-05");
    await act(async()=>old.reject(new Error("old failure")));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
  it("actualizar referencias invalida resultados y consultas pendientes", async () => {
    render(<PredictionsPage />); await ready(); await submit(); await screen.findByText("40.87 unidades");
    await userEvent.click(screen.getByRole("button",{name:"Actualizar referencias"})); await ready();
    expect(screen.queryByText("40.87 unidades")).not.toBeInTheDocument(); expect(api.get).toHaveBeenCalledTimes(2);
  });
  it("desmontar cancela la consulta y no aplica su respuesta", async () => {
    const old=deferred(); vi.mocked(api.post).mockReturnValueOnce(old.promise as any);
    const view=render(<PredictionsPage />); await ready(); await submit(); view.unmount();
    expect((vi.mocked(api.post).mock.calls[0][2] as any).signal.aborted).toBe(true);
    await act(async()=>old.resolve({data:response()}));
  });
  it("separa escenarios e historial y oculta controles sin servicio", async () => {
    render(<PredictionsPage />); await ready();
    await userEvent.click(screen.getByRole("button", { name: /^Predecir y comparar/ }));
    await screen.findByText(/Los escenarios todavía no están habilitados/);
    expect(screen.queryByLabelText("Producto")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Consultar predicción" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("Versiones anteriores"));
    await userEvent.click(screen.getByRole("button", { name: "Consulta histórica" }));
    expect(screen.getByLabelText("Producto")).toBeInTheDocument();
    expect(screen.queryByText(/Los escenarios todavía no están habilitados/)).not.toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();
  });
});
