import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import RoleRoute from "./RoleRoute";
import Sidebar from "./layout/Sidebar";
const state=vi.hoisted(()=>({user:{role:"ADMIN"},isAuthenticated:true,permissions:["prediccion","inventario","ventas","reportes","movimientos"],permissionsLoading:false,logout:vi.fn()}));
vi.mock("../stores/authStore",()=>({useAuthStore:()=>state}));
beforeEach(()=>{state.user={role:"ADMIN"};state.isAuthenticated=true;state.permissionsLoading=false;});
describe("acceso predictivo por rol",()=>{
  for(const role of ["ADMIN","TIENDA","INVENTARIO","UNKNOWN"]){
    it(`ruta y menú respetan ${role} incluso con permiso prediccion`,()=>{
      state.user={role};
      render(<MemoryRouter initialEntries={["/panel/prediccion"]}><Sidebar open onClose={()=>{}}/><Routes><Route path="/panel/prediccion" element={<RoleRoute allowedRoles={["ADMIN"]}><div>Modelo protegido</div></RoleRoute>}/><Route path="/panel" element={<div>Inicio permitido</div>}/></Routes></MemoryRouter>);
      expect(!!screen.queryByText("Modelo protegido")).toBe(role==="ADMIN");
      expect(!!screen.queryByRole("link",{name:"Predicción de ventas"})).toBe(role==="ADMIN");
    });
  }
  it("sin sesión redirige al login",()=>{
    state.isAuthenticated=false;
    render(<MemoryRouter initialEntries={["/panel/prediccion"]}><Routes><Route path="/panel/prediccion" element={<RoleRoute allowedRoles={["ADMIN"]}><div>Modelo protegido</div></RoleRoute>}/><Route path="/login" element={<div>Ingresar al sistema</div>}/></Routes></MemoryRouter>);
    expect(screen.getByText("Ingresar al sistema")).toBeInTheDocument();expect(screen.queryByText("Modelo protegido")).toBeNull();
  });
});
