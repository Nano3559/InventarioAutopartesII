import { useEffect, useState } from "react";
import api from "../services/api";
import { checkedCapabilities, type Snapshot } from "../services/scenarioView";
import { scenarioMonth, spanishOrder, type ProductOrder } from "../services/scenarioPresentation";
import { DemonstrationChart } from "./ScenarioHistoryChart";

const input = "w-full min-w-0 rounded-lg border border-slate-700 bg-dark-900 px-3 py-2.5 text-sm";
const normalize = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("es");
type Selection = {productId:number;locationId:number};
export default function DemonstrationSalesPanel({initialSelection,onSelection}: {initialSelection?:Selection|null;onSelection?:(selection:Selection)=>void} = {}) {
  const [references,setReferences]=useState<Snapshot[]>([]);
  const [selected,setSelected]=useState<Snapshot | null>(null);
  const [month,setMonth]=useState("2026-10");
  const [query,setQuery]=useState("");
  const [order,setOrder]=useState<ProductOrder>("az");
  const [error,setError]=useState(false);
  const [reload,setReload]=useState(0);
  useEffect(() => {
    const abort=new AbortController(); let alive=true;
    setError(false); setSelected(null); setReferences([]);
    api.get("/predictions/scenarios/capabilities",{signal:abort.signal}).then(res => {
      if (!alive) return;
      const snapshots=checkedCapabilities(res.data).snapshots;
      if(snapshots.some(s=>!s.historyMonthly?.length)) throw new Error("Missing approved history");
      const unique=[...new Map(snapshots.map(s => [`${s.productId}:${s.locationId}`,s])).values()];
      unique.sort((a,b) => spanishOrder.compare(a.productName,b.productName) || spanishOrder.compare(a.locationName,b.locationName) || a.productId-b.productId);
      setReferences(unique); setSelected(unique.find(s=>s.productId===initialSelection?.productId && s.locationId===initialSelection?.locationId) ?? unique.find(s=>s.productId===snapshots[0].productId && s.locationId===snapshots[0].locationId) ?? unique[0]);
    }).catch(() => {if(alive) setError(true);});
    return () => {alive=false;abort.abort();};
  },[reload]);
  useEffect(()=>{if(selected) onSelection?.({productId:selected.productId,locationId:selected.locationId});},[selected?.productId,selected?.locationId,onSelection]);
  if(error) return <div role="alert" className="rounded-xl border border-amber-500/30 p-4">No se pudieron cargar los productos y tiendas.<button className="ml-3 rounded-lg border border-slate-600 px-3 py-2" onClick={() => setReload(n=>n+1)}>Reintentar</button></div>;
  if(!selected) return <p role="status">Cargando productos y tiendas…</p>;
  const score=(s:Snapshot) => s.historyMonthly?.find(h=>h.month===month)?.units ?? 0;
  const orderedProducts=(nextOrder:ProductOrder)=>references.filter(s=>s.locationId===selected.locationId && normalize(`${s.productName} ${s.productId}`).includes(normalize(query.trim()))).sort((a,b)=>{
    const alpha=spanishOrder.compare(a.productName,b.productName)||a.productId-b.productId;
    return nextOrder==="az"?alpha:nextOrder==="za"?-alpha:(nextOrder==="most"?score(b)-score(a):score(a)-score(b))||alpha;
  });
  const products=orderedProducts(order);
  function changeOrder(nextOrder:ProductOrder) {
    setOrder(nextOrder);
    if(nextOrder==="most" || nextOrder==="least") { const first=orderedProducts(nextOrder)[0]; if(first) setSelected(first); }
  }
  const locations=references.filter(s=>s.productId===selected.productId).sort((a,b)=>spanishOrder.compare(a.locationName,b.locationName));
  const history=selected.historyMonthly!.filter(h=>h.month<=month);
  const recent=history.slice(-3);
  return <section aria-label="Explorar ventas de demostración" className="space-y-4 rounded-2xl border border-slate-700/60 bg-dark-800/50 p-4 md:p-5 min-w-0">
    <div className="flex flex-wrap justify-between gap-2"><h2 className="font-semibold">Ventas del dataset · 2026</h2><span className="text-xs text-gray-400">Historial hasta octubre · predicción en noviembre</span></div>
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <label className="space-y-1 text-sm">Buscar producto<input type="search" className={input} value={query} placeholder="Nombre o identificador" onChange={e=>setQuery(e.target.value)}/></label>
      <label className="space-y-1 text-sm">Ordenar productos<select className={input} value={order} onChange={e=>changeOrder(e.target.value as ProductOrder)}><option value="az">Nombre: A a Z</option><option value="za">Nombre: Z a A</option><option value="most">Más vendido</option><option value="least">Menos vendido</option></select></label>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <label className="space-y-1 text-sm">Producto<select className={input} value={products.some(s=>s.productId===selected.productId)?selected.productId:""} onChange={e=>{const next=products.find(s=>s.productId===Number(e.target.value));if(next)setSelected(next);}}><option value="" disabled>Selecciona un resultado</option>{products.map(s=><option key={s.productId} value={s.productId}>{s.productName}{references.some(o=>o.productId!==s.productId && o.productName===s.productName)?` · #${s.productId}`:""}</option>)}</select></label>
      <label className="space-y-1 text-sm">Tienda<select className={input} value={selected.locationId} onChange={e=>{const next=locations.find(s=>s.locationId===Number(e.target.value));if(next)setSelected(next);}}>{locations.map(s=><option key={s.locationId} value={s.locationId}>{s.locationName}</option>)}</select></label>
      <label className="space-y-1 text-sm">Mes del historial<select className={input} value={month} onChange={e=>setMonth(e.target.value)}>{selected.historyMonthly!.map(h=><option key={h.month} value={h.month}>{scenarioMonth(h.month)}</option>)}</select></label>
    </div>
    {!products.length && <p role="status" className="text-sm text-amber-200">Sin coincidencias. La gráfica conserva {selected.productName}.</p>}
    {(order==="most"||order==="least") && <p className="text-xs text-gray-400">Orden del dataset en {scenarioMonth(month)} · {selected.locationName}.</p>}
    <section aria-label="Resumen de ventas mensuales" className="space-y-3">
      <h3 className="text-sm font-semibold">{month === "2026-10" ? "Ventas de referencia para predecir noviembre de 2026" : "Últimos meses del historial seleccionado"}</h3>
      <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3">{recent.map(h=><div key={h.month} className="rounded-xl bg-dark-900 p-3"><dt className="text-xs text-gray-400 capitalize">{scenarioMonth(h.month)}</dt><dd className="mt-1 text-2xl font-semibold">{h.units.toLocaleString("es-BO")} <span className="text-xs font-normal text-gray-400">unidades</span></dd></div>)}</dl>
    </section>
    <DemonstrationChart reference={selected} throughMonth={month}/>
  </section>;
}
