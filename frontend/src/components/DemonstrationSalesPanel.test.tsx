import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DemonstrationSalesPanel from "./DemonstrationSalesPanel";
import api from "../services/api";
import { capabilities, snapshot } from "../test/fixtures/demandScenario";
vi.mock("../services/api",()=>({default:{get:vi.fn(),post:vi.fn()}}));
beforeEach(()=>{vi.clearAllMocks();vi.mocked(api.get).mockResolvedValue({data:{...capabilities,snapshots:[...capabilities.snapshots,{...snapshot,baseSnapshotId:"store-2",locationId:6,locationName:"Tienda 2"}]}});});
describe("exploración independiente de ventas 2026",()=>{
  it("mantiene las tarjetas y los puntos de la gráfica iguales al cambiar producto o tienda",async()=>{
    const snapshots=[1,2].flatMap(productId=>[5,6].map(locationId=>({
      ...snapshot,productId,locationId,productName:productId===1?"Filtro":"Bujía",locationName:`Tienda ${locationId-4}`,baseSnapshotId:`pair-${productId}-${locationId}`,
      historyMonthly:snapshot.historyMonthly!.map((h,i)=>({...h,units:productId*10+locationId+i,retailUnits:productId*10+locationId+i,wholesaleUnits:0,unknownModeUnits:0}))
    })));
    vi.mocked(api.get).mockResolvedValue({data:{...capabilities,snapshots}});
    render(<DemonstrationSalesPanel/>); await screen.findByLabelText("Mes del historial");
    for(const [product,store] of [[1,5],[2,5],[2,6],[1,6]]) {
      await userEvent.selectOptions(screen.getByLabelText("Producto"),String(product));
      await userEvent.selectOptions(screen.getByLabelText("Tienda"),String(store));
      const expected=snapshots.find(s=>s.productId===product && s.locationId===store)!.historyMonthly.slice(-3);
      const summary=within(screen.getByRole("region",{name:"Resumen de ventas mensuales"}));
      expect(summary.getAllByRole("definition").map(n=>n.textContent)).toEqual(expected.map(h=>`${h.units} unidades`));
      const chart=within(screen.getByLabelText("Histórico mensual y pronósticos del escenario"));
      const rows=chart.getAllByRole("row").slice(-3);
      for(let i=0;i<3;i++) {
        expect(within(rows[i]).getAllByRole("cell")[1]).toHaveTextContent(String(expected[i].units));
        expect(chart.getByText(`${["agosto","septiembre","octubre"][i]} de 2026: ${expected[i].units} unidades`,{selector:"title"})).toBeInTheDocument();
      }
    }
    expect(api.post).not.toHaveBeenCalled();
  });
  it("muestra agosto, septiembre y octubre por separado, sin el acumulado confuso",async()=>{
    const snapshots=[{...snapshot,historyMonthly:snapshot.historyMonthly!.map((h,i)=>({ ...h,units:i===7?50:i===8?74:i===9?130:0,retailUnits:i===7?50:i===8?74:i===9?130:0,wholesaleUnits:0,unknownModeUnits:0 }))}];
    vi.mocked(api.get).mockResolvedValue({data:{...capabilities,snapshots}});
    render(<DemonstrationSalesPanel/>);
    const summary=within(await screen.findByRole("region",{name:"Resumen de ventas mensuales"}));
    expect(summary.getByRole("heading")).toHaveTextContent("Ventas de referencia para predecir noviembre de 2026");
    expect(summary.getAllByRole("term").map(n=>n.textContent)).toEqual(["agosto de 2026","septiembre de 2026","octubre de 2026"]);
    expect(summary.getAllByRole("definition").map(n=>n.textContent)).toEqual(["50 unidades","74 unidades","130 unidades"]);
    expect(screen.queryByText("Acumulado del periodo")).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Mes del historial"),"2026-01");
    expect(summary.getAllByRole("term").map(n=>n.textContent)).toEqual(["enero de 2026"]);
    expect(summary.queryByText(/predecir noviembre/)).not.toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();
  });
  it("distingue el mes histórico y selecciona el producto más o menos vendido sin cantidades en el nombre",async()=>{
    const snapshots=capabilities.snapshots.map(s=>({...s,historyMonthly:s.historyMonthly!.map(h=>({...h,units:s.productId*10,retailUnits:s.productId*10-3,wholesaleUnits:2,unknownModeUnits:1}))}));
    vi.mocked(api.get).mockResolvedValue({data:{...capabilities,snapshots}});
    render(<DemonstrationSalesPanel/>); await screen.findByLabelText("Mes del historial");
    expect(screen.queryByLabelText("Mes del escenario")).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Ordenar productos"),"most");
    expect(screen.getByLabelText("Producto")).toHaveValue("2");
    expect(screen.getByRole("option",{name:"Bujía"})).toBeInTheDocument();
    expect(within(screen.getByRole("region",{name:"Resumen de ventas mensuales"})).getByText("octubre de 2026").nextElementSibling).toHaveTextContent("20");
    await userEvent.selectOptions(screen.getByLabelText("Ordenar productos"),"least");
    expect(screen.getByLabelText("Producto")).toHaveValue("1");
    expect(within(screen.getByRole("region",{name:"Resumen de ventas mensuales"})).getByText("octubre de 2026").nextElementSibling).toHaveTextContent("10");
    expect(api.post).not.toHaveBeenCalled();
  });
  it("ofrece todos los meses hasta octubre y cambia la gráfica sin llamar a inferencia",async()=>{
    render(<DemonstrationSalesPanel/>);
    const month=await screen.findByLabelText("Mes del historial");
    expect(month).toHaveValue("2026-10");
    expect(within(month).getAllByRole("option")).toHaveLength(10);
    expect(within(month).getByRole("option",{name:"octubre de 2026"})).toBeInTheDocument();
    expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(11);
    await userEvent.selectOptions(month,"2026-01");
    expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(2);
    expect(screen.queryByText("Con cambios")).not.toBeInTheDocument();
    expect(api.get).toHaveBeenCalledTimes(1);
    expect(api.post).not.toHaveBeenCalled();
  });
  it("permite cambiar producto y tienda, buscar y ordenar usando el mismo mes de la gráfica",async()=>{
    render(<DemonstrationSalesPanel/>); await screen.findByLabelText("Mes del historial");
    await userEvent.selectOptions(screen.getByLabelText("Producto"),"1");
    await userEvent.selectOptions(screen.getByLabelText("Tienda"),"6");
    expect(screen.getByLabelText("Tienda")).toHaveValue("6");
    expect(screen.getByLabelText("Mes del historial")).toHaveValue("2026-10");
    await userEvent.selectOptions(screen.getByLabelText("Ordenar productos"),"most");
    expect(screen.getByText(/Orden del dataset en octubre de 2026/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Buscar producto"),"inexistente");
    expect(screen.getByRole("status")).toHaveTextContent("Sin coincidencias");
    expect(api.post).not.toHaveBeenCalled();
  });
});
