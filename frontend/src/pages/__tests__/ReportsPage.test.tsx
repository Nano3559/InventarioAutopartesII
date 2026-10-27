import { it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ReportsPage from "../ReportsPage";
const roleState=vi.hoisted(()=>({user:{role:"ADMIN"} as {role:string}|null}));
vi.mock("../../stores/authStore",()=>({useAuthStore:()=>roleState}));
vi.mock("../../services/api",()=>({default:{get:vi.fn(async(url:string)=>({data:url.startsWith("/reports/sales")?{sales:[],summary:{totalSales:80,count:1,average:80},pagination:{pages:1}}:url.startsWith("/reports/inventory")?{locations:[],totalProducts:3,totalStock:7,lowStockCount:0}:url.startsWith("/reports/monthly")?{period:{year:2026,month:10},locations:[],summary:{totalSales:0,totalReturns:0,netSales:0,totalLocations:0}}:url==="/locations"?[]:{suppliers:[]}}))}}));
beforeEach(()=>{roleState.user={role:"ADMIN"};});
for(const role of ["ADMIN","INVENTARIO"]){
 it(`${role} conserva las columnas de costo en el reporte mensual`,async()=>{
  roleState.user={role};render(<ReportsPage/>);await userEvent.click(screen.getByRole("button",{name:"Mensual por Tienda"}));
  await waitFor(()=>expect(screen.getByRole("columnheader",{name:"Costo Mercadería"})).toBeInTheDocument());
  expect(screen.getByRole("columnheader",{name:"Costo Tienda (+10%)"})).toBeInTheDocument();expect(screen.getByRole("columnheader",{name:"Utilidad"})).toBeInTheDocument();
 });
}
for(const role of ["TIENDA",null]){
 it(`${role??"sesión sin recuperar"} no muestra costos ni utilidad`,async()=>{
  roleState.user=role?{role}:null;render(<ReportsPage/>);await userEvent.click(screen.getByRole("button",{name:"Mensual por Tienda"}));
  await waitFor(()=>expect(screen.getByText("No hay datos para los filtros seleccionados")).toBeInTheDocument());
  expect(screen.queryByRole("columnheader",{name:"Costo Mercadería"})).not.toBeInTheDocument();expect(screen.queryByRole("columnheader",{name:"Utilidad"})).not.toBeInTheDocument();
 });
}
it("cambiar a inventario no reutiliza ventas anteriores ni muestra unidades como dinero",async()=>{
 render(<ReportsPage/>);await waitFor(()=>expect(screen.getAllByText(/80,00/).length).toBeGreaterThan(0));
 await userEvent.click(screen.getByRole("button",{name:"Inventario"}));
 await waitFor(()=>expect(screen.getByText("7 uds")).toBeInTheDocument());
 expect(screen.queryByText(/80,00/)).not.toBeInTheDocument();expect(screen.getByText("3 productos")).toBeInTheDocument();
});
