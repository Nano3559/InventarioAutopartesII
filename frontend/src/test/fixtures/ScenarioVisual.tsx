// Opt-in visual harness, never imported by the application entry point.
import React from "react";
import { createRoot } from "react-dom/client";
import api from "../../services/api";
import PredictionsPage from "../../pages/PredictionsPage";
import DashboardPage from "../../pages/DashboardPage";
import { Routes, Route, MemoryRouter } from "react-router-dom";
import { DEMAND_ARTIFACT } from "../../services/demandView";
import DemandScenarioPanel from "../../components/DemandScenarioPanel";
import MainLayout from "../../components/layout/MainLayout";
import { useAuthStore } from "../../stores/authStore";
import { capabilities, resultFixture, baseFixture } from "./demandScenario";
import "../../index.css";
const catalog = { products:[{id:1,name:"Pastillas de freno",itemCode:"FRN-001"}], locations:[{id:5,name:"Tienda 1"}], catalogObservedAt:"2026-10-28T01:08:41Z", defaultTargetMonth:"2026-06", availableTargetMonths:["2026-04","2026-05","2026-06"],version:"V2.2.0",artifactSha256:DEMAND_ARTIFACT,origin:"SYNTHETIC",mode:"ACADEMIC_REPLAY" };
function replay(payload: { productId:number;locationId:number;targetMonth:string }) {
  const [y,m]=payload.targetMonth.split("-").map(Number);
  return {...payload,status:"OK",prediction:18.42,baseline:21,model:"RandomForestRegressor",version:"V2.2.0",history:[3,2,1].map(n=>({month:new Date(Date.UTC(y,m-1-n,1)).toISOString().slice(0,7),units:n===1?21:25})),metrics:{mae:9.204618055555557,rmse:16.90851955066845,r2:.6465904325570372},evaluationContext:{origin:"SYNTHETIC",split:"TEST",mae:9.204618055555557,rmse:16.90851955066845,r2:.6465904325570372},datasetVersion:"2.2.0",buildId:"calibrated-20261115-01",selectionId:"accepted-absolute-2.2-20261115-01",artifactSha256:DEMAND_ARTIFACT,policyVersion:"NONNEGATIVE_CONTINUOUS_1",historySnapshotId:"fixture-approved",featureSnapshotSha256:"a".repeat(64),historyCutoff:`${payload.targetMonth}-01T00:00:00-04:00`,issuedAt:"2026-11-15T20:00:00Z",warnings:["DATOS_SINTETICOS_NO_VALIDA_VENTAS_REALES"],origin:"SYNTHETIC",mode:"ACADEMIC_REPLAY"};
}
api.defaults.adapter = async config => {
  let data: unknown;
  if(config.url==="/notifications") data={notifications:[],unreadCount:0};
  else if(config.url==="/dashboard") data={availability:{sales:"SCHEMA_UNAVAILABLE"},summary:{totalProducts:62,productsWithoutStock:2,productsWithLowStock:2,salesToday:null,salesTodayTotal:null,salesMonth:null,salesMonthTotal:null,pendingRequests:2,criticalStock:2},stockByLocation:[{locationId:5,name:"Tienda 1",type:"TIENDA",totalStock:250},{locationId:6,name:"Tienda 2",type:"TIENDA",totalStock:120},{locationId:1,name:"Almacén de prueba",type:"ALMACEN",totalStock:140}],salesByLocation:[],salesByBrand:[],salesByVehicle:[],recentSales:[],recentMovements:[],pendingRequests:[{id:1,product:"Filtro de prueba",itemCode:"F-TEST",quantity:10,location:"Tienda 1",requestedBy:"Usuario de prueba",date:"2026-11-15T14:00:00Z"},{id:2,product:"Pastillas de prueba",itemCode:"P-TEST",quantity:5,location:"Tienda 2",requestedBy:"Usuario de prueba",date:"2026-11-15T14:00:00Z"}],criticalStock:[{product:"Filtro de prueba",itemCode:"F-TEST",location:"Tienda 1",stock:1,minStock:3},{product:"Pastillas de prueba",itemCode:"P-TEST",location:"Tienda 2",stock:1,minStock:5}]};
  else if(config.url==="/predictions/catalog") data=catalog;
  else if(config.url==="/predictions/demand") data=replay(JSON.parse(String(config.data)));
  else {
    if(location.search.includes("unavailable")) throw new Error("Fixture: backend unavailable");
    data=config.url?.endsWith("capabilities")?capabilities:config.url?.includes("/snapshots/")?baseFixture(config.url.split("/").pop()):resultFixture();
  }
  return {data,config,status:200,statusText:"FIXTURE",headers:{}};
};
const view=new URLSearchParams(location.search).get("view");
if(view==="admin") useAuthStore.setState({user:{id:1,name:"ADMIN de prueba",email:"fixture@example.invalid",role:"ADMIN",locationId:null},isAuthenticated:true});
createRoot(document.getElementById("root")!).render(view==="admin" ? <MemoryRouter initialEntries={["/panel/prediccion"]}><div className="fixed bottom-1 right-2 z-[100] rounded bg-dark-950/90 px-2 text-[10px] text-gray-500 pointer-events-none">Revisión local con fixtures</div><Routes><Route element={<MainLayout/>}><Route path="/panel/prediccion" element={<PredictionsPage/>}/></Route></Routes></MemoryRouter> : <React.StrictMode><MemoryRouter><main className="max-w-7xl mx-auto p-4 space-y-4"><p className="text-xs text-gray-400">REVISIÓN VISUAL CON FIXTURES · No es API real ni una predicción comercial</p>{view==="history"?<PredictionsPage/>:view==="dashboard"?<DashboardPage/>:<DemandScenarioPanel/>}</main></MemoryRouter></React.StrictMode>);
