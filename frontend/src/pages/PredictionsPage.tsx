import { spanishOrder } from "../services/scenarioPresentation";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import api from "../services/api";
import DemandScenarioPanel from "../components/DemandScenarioPanel";
import DemonstrationSalesPanel from "../components/DemonstrationSalesPanel";
import { checkedCatalog, checkedResult, demandError, DemandCatalog, DemandResult } from "../services/demandView";

function businessTime(value: string) {
  return new Intl.DateTimeFormat("es-BO", { timeZone: "America/La_Paz", dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
function monthLabel(value: string) {
  return new Intl.DateTimeFormat("es-BO", { timeZone: "UTC", month: "long", year: "numeric" }).format(new Date(`${value}-01T00:00:00Z`));
}
export default function PredictionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const productParam = searchParams.get("productId") ?? "";
  const locationParam = searchParams.get("locationId") ?? "";
  const selectedContext = /^[1-9]\d{0,9}$/.test(productParam) && /^[1-9]\d{0,9}$/.test(locationParam)
    ? { productId: Number(productParam), locationId: Number(locationParam) } : null;
  const setSelectedContext = useCallback((selection: {productId:number;locationId:number}) => {
    if (searchParams.get("productId") === String(selection.productId) && searchParams.get("locationId") === String(selection.locationId)) return;
    setSearchParams(previous => {
      const next = new URLSearchParams(previous);
      next.set("productId", String(selection.productId));
      next.set("locationId", String(selection.locationId));
      return next;
    }, { replace: true });
  }, [searchParams, setSearchParams]);
  const mode = ["historico", "escenarios"].includes(searchParams.get("modo") ?? "") ? searchParams.get("modo")! : "demo";
  const scenarioOpen = mode === "escenarios";
  function setScenarioOpen(open: boolean) {
    setSearchParams(previous => {
      const next = new URLSearchParams(previous);
      next.set("modo", open ? "escenarios" : "historico");
      return next;
    }, { replace: true });
  }
  const [catalog, setCatalog] = useState<DemandCatalog | null>(null);
  const [product, setProduct] = useState("");
  const [location, setLocation] = useState("");
  const [month, setMonth] = useState("");
  const [result, setResult] = useState<DemandResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [catalogBusy, setCatalogBusy] = useState(true);
  const [error, setError] = useState("");
  const mounted = useRef(false);
  const request = useRef(0);
  const catalogRequest = useRef(0);
  const pending = useRef<AbortController | null>(null);
  const pendingCatalog = useRef<AbortController | null>(null);
  function clearPrediction() {
    request.current++; pending.current?.abort(); setBusy(false); setResult(null); setError("");
  }
  async function load() {
    const id = ++catalogRequest.current;
    pendingCatalog.current?.abort();
    const controller = new AbortController(); pendingCatalog.current = controller;
    clearPrediction(); setCatalog(null); setCatalogBusy(true);
    try {
      const { data } = await api.get("/predictions/catalog", { signal: controller.signal });
      const checked = checkedCatalog(data);
      if (mounted.current && id === catalogRequest.current) {
        setCatalog(checked); setProduct(String(checked.products[0].id)); setLocation(String(checked.locations[0].id)); setMonth(checked.defaultTargetMonth);
      }
    } catch (e) {
      if (mounted.current && id === catalogRequest.current && !controller.signal.aborted) setError(`No se pudo cargar el catálogo predictivo. ${demandError(e)}`);
    } finally { if (mounted.current && id === catalogRequest.current) setCatalogBusy(false); }
  }
  useEffect(() => {
    mounted.current = true; if (mode === "historico") void load();
    return () => { mounted.current = false; request.current++; catalogRequest.current++; pending.current?.abort(); pendingCatalog.current?.abort(); };
  }, [mode]);
  async function predict() {
    if (!catalog || !catalog.availableTargetMonths.includes(month) || !catalog.products.some(p => String(p.id) === product) || !catalog.locations.some(l => String(l.id) === location)) return;
    clearPrediction(); const id = request.current;
    const controller = new AbortController(); pending.current = controller;
    const selected = { productId: Number(product), locationId: Number(location), targetMonth: month };
    setBusy(true);
    try {
      const { data } = await api.post("/predictions/demand", selected, { signal: controller.signal });
      if (mounted.current && id === request.current && !controller.signal.aborted) setResult(checkedResult(data, selected, catalog.version));
    } catch (e) {
      if (mounted.current && id === request.current && !controller.signal.aborted) setError(demandError(e));
    } finally { if (mounted.current && id === request.current) setBusy(false); }
  }
  function change(value: string, kind: "product" | "location" | "month") {
    clearPrediction();
    if (kind === "product") setProduct(value);
    else if (kind === "location") setLocation(value);
    else setMonth(value);
  }
  const points = result ? [...result.history.map(r => ({ month: r.month, observed: r.units as number | null, forecast: null as number | null, baseline: null as number | null })),
    { month: result.targetMonth, observed: null, forecast: result.prediction, baseline: result.baseline }] : [];
  if (result && points.length > 1) {
    points[points.length - 2].forecast = result.baseline;
    points[points.length - 2].baseline = result.baseline;
  }
  return <section className="mx-auto w-full max-w-6xl space-y-5 min-w-0 pb-6">
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div><p className="text-xs uppercase tracking-widest text-primary-400 mb-1">Planificación</p><h1 className="text-2xl font-semibold text-white">Predicción de ventas</h1><p className="mt-1 text-sm text-gray-400">Consulta el historial hasta octubre y estima las ventas de noviembre de 2026.</p></div>
    </header>
    <div className="flex flex-wrap gap-2" aria-label="Modo de consulta">
      <button className={`rounded-xl border px-4 py-3 text-sm font-medium ${mode === "demo" ? "border-primary-500 bg-primary-500/10 text-white" : "border-slate-700 text-gray-400"}`} aria-pressed={mode === "demo"} onClick={() => setSearchParams(previous => { const next=new URLSearchParams(previous);next.set("modo","demo");return next; },{replace:true})}>Explorar ventas<span className="ml-2 text-xs text-gray-400">2026</span></button>
      <button className={`rounded-xl border px-4 py-3 text-sm font-medium ${scenarioOpen ? "border-primary-500 bg-primary-500/10 text-white" : "border-slate-700 text-gray-400"}`} aria-pressed={scenarioOpen} onClick={() => setScenarioOpen(true)}>Predecir y comparar<span className="ml-2 text-xs text-gray-400">Noviembre 2026</span></button>
    </div>
    <details className="text-xs text-gray-400"><summary className="cursor-pointer">Versiones anteriores</summary><button className="mt-2 rounded-lg border border-slate-600 px-3 py-2" aria-pressed={mode === "historico"} onClick={() => setScenarioOpen(false)}>Consulta histórica</button></details>
    {mode === "demo" ? <DemonstrationSalesPanel initialSelection={selectedContext} onSelection={setSelectedContext} /> : scenarioOpen ? <DemandScenarioPanel initialSelection={selectedContext} onSelection={setSelectedContext} /> : <>
    {catalog?.version === "V2.1.0" && <p role="status" className="rounded-xl border border-amber-500 p-4 text-amber-200">Recuperación explícita: el servidor utiliza el modelo conservado 2.1.0. No es un reemplazo automático.</p>}
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-400"><span>Historial simulado: abril–junio de 2026</span><span>Horizonte: 1 mes</span><span>Sin cambios en inventario</span></div>
    {error && <div role="alert" className="rounded-xl border border-red-500 p-4 text-red-200 space-y-3"><p>{error}</p><div className="flex flex-wrap gap-3">{catalog && <button className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm hover:bg-slate-700" onClick={() => void predict()}>Reintentar consulta</button>}<button className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm hover:bg-slate-700" onClick={() => void load()}>{catalog ? "Actualizar referencias" : "Reintentar catálogo"}</button></div></div>}
    {catalogBusy && <p role="status">Cargando catálogo aprobado…</p>}
    {catalog && <div className="rounded-xl bg-slate-800 p-4 space-y-4">
      <div className="flex items-center justify-between gap-2"><h2 className="font-medium text-white">Selecciona la consulta</h2><span className="text-xs text-gray-400">{catalog.version}</span></div>
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <label className="flex flex-col min-w-0 gap-1">Producto<select className="bg-slate-900 p-3 rounded w-full min-w-0" value={product} onChange={e => change(e.target.value, "product")}>{[...catalog.products].sort((a,b) => spanishOrder.compare(a.name,b.name) || a.id-b.id).map(p => <option key={p.id} value={p.id}>{p.itemCode} · {p.name}</option>)}</select></label>
        <label className="flex flex-col min-w-0 gap-1">Tienda<select className="bg-slate-900 p-3 rounded w-full" value={location} onChange={e => change(e.target.value, "location")}>{[...catalog.locations].sort((a,b) => spanishOrder.compare(a.name,b.name) || a.id-b.id).map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
        <label className="flex flex-col min-w-0 gap-1">Mes de reproducción<select className="bg-slate-900 p-3 rounded w-full" value={month} onChange={e => change(e.target.value, "month")}>{catalog.availableTargetMonths.map(m => <option key={m} value={m}>{monthLabel(m)}</option>)}</select></label>
        <label className="flex flex-col min-w-0 gap-1">Horizonte<input className="bg-slate-900 p-3 rounded w-full text-gray-300" readOnly value="1 mes" /></label>
      </div>
      <div className="flex flex-wrap gap-3"><button className="bg-primary-600 rounded p-3 disabled:opacity-50" disabled={busy || !product || !location || !month} onClick={() => void predict()}>{busy ? "Calculando…" : "Consultar predicción"}</button><button className="border border-slate-500 rounded p-3" onClick={() => void load()}>Actualizar referencias</button></div>

    </div>}
    {busy && <p role="status" aria-live="polite">Consultando el modelo V2 fijado…</p>}
    {result && <div className="space-y-6" aria-live="polite">
      <div className="rounded-xl bg-slate-800 p-5 space-y-3"><h2 className="text-xl">Mes objetivo: {result.targetMonth}</h2><p>{catalog?.products.find(p => p.id === result.productId)?.name} · {catalog?.locations.find(l => l.id === result.locationId)?.name}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4"><p className="rounded-lg bg-slate-900 p-4">Ventas previstas<br/><strong className="text-3xl">{result.prediction.toFixed(2)} unidades</strong></p><p className="rounded-lg bg-slate-900 p-4">Referencia del mes anterior<br/><strong className="text-3xl">{result.baseline} unidades</strong></p></div>
        <p className="text-xs text-gray-400">{result.model} · {result.version} · No es una orden de compra</p>
      </div>
      <div className="rounded-xl bg-slate-800 p-4 min-w-0"><h2 className="text-xl mb-2">Histórico y predicción</h2><p className="text-sm text-gray-400 mb-3">Últimos tres meses y estimación del mes seleccionado.</p>
        <div className="h-80 w-full min-w-0" role="img" aria-label="Gráfico de tres meses simulados, predicción y baseline"><ResponsiveContainer width="100%" height="100%"><LineChart data={points} margin={{ top: 10, right: 12, bottom: 10, left: 0 }}><CartesianGrid stroke="#334155"/><XAxis dataKey="month"/><YAxis allowDecimals={false}/><Tooltip/><Legend/><Line name="Ventas simuladas" type="linear" dataKey="observed" stroke="#60a5fa" connectNulls={false}/><Line name="Predicción" type="linear" dataKey="forecast" stroke="#fbbf24" strokeDasharray="5 5" connectNulls={false}/><Line name="Baseline: mes anterior" type="linear" dataKey="baseline" stroke="#c084fc" strokeDasharray="2 3" connectNulls={false}/></LineChart></ResponsiveContainer></div>
        <details className="mt-4"><summary className="cursor-pointer">Datos del gráfico</summary><div className="overflow-x-auto"><table className="w-full text-left mt-2"><caption className="sr-only">Valores usados en el gráfico</caption><thead><tr><th className="p-2">Mes</th><th className="p-2">Tipo</th><th className="p-2">Unidades</th></tr></thead><tbody>{result.history.map(r => <tr key={r.month}><td className="p-2">{monthLabel(r.month)}</td><td className="p-2">Histórico simulado</td><td className="p-2">{r.units}</td></tr>)}<tr><td className="p-2">{monthLabel(result.targetMonth)}</td><td className="p-2">Predicción</td><td className="p-2">{result.prediction.toFixed(2)}</td></tr></tbody></table></div></details>
      </div>
      <div className="rounded-xl bg-slate-800 p-5 space-y-3"><h2 className="text-xl">Evaluación guardada del modelo</h2><div className="grid grid-cols-1 sm:grid-cols-3 gap-3"><p>MAE TEST sintético<br/><strong>{result.metrics.mae.toFixed(2)} unidades</strong></p><p>RMSE TEST<br/><strong>{result.metrics.rmse.toFixed(2)} unidades</strong></p><p>R² TEST<br/><strong>{result.metrics.r2.toFixed(3)}</strong></p></div><details className="text-xs text-gray-400"><summary className="cursor-pointer">Cómo interpretar las métricas</summary><p className="mt-2">Resultados guardados sobre datos sintéticos. No se recalcula TEST al consultar. MAE expresa error medio en unidades. R² no es un porcentaje de precisión.</p></details></div>
      <details className="rounded-xl border border-slate-700/60 p-4 text-sm text-gray-400 space-y-2" aria-label="Límites del pronóstico"><summary className="cursor-pointer font-medium text-gray-300">Limitaciones del pronóstico</summary><p>El modelo puede subestimar pedidos grandes o suavizar niveles estables. {result.datasetVersion === "2.2.0" ? "En VALIDATION, 13 productos y 36 combinaciones producto-tienda empeoraron frente al baseline." : "Esta versión recuperada conserva sus propios resultados y límites de evaluación."} Los compromisos mayoristas conocidos no son una variable explícita de este modelo.</p><p>Ventas observadas no equivalen a toda la demanda. Un mes sin ventas puede incluir falta de stock. Revisa el resultado antes de tomar decisiones.</p><p>No se calcula reposición ni se modifican existencias. Este experimento no acredita precisión comercial.</p>{result.warnings.includes("NEGATIVE_PREDICTION_CLIPPED") && <p>Una salida negativa se limitó a cero según la política fijada.</p>}</details>
      <details className="rounded-xl bg-slate-800 p-4"><summary className="cursor-pointer font-medium text-gray-300">Datos del modelo y trazabilidad</summary><dl className="mt-3 space-y-3 text-xs text-gray-400 break-words"><div><dt>Catálogo observado (America/La_Paz)</dt><dd>{catalog && businessTime(catalog.catalogObservedAt)}</dd></div><div><dt className="text-gray-400">Snapshot aprobado</dt><dd className="break-all">{result.historySnapshotId}</dd></div><div><dt className="text-gray-400">Corte de historia (America/La_Paz)</dt><dd>{businessTime(result.historyCutoff)}</dd></div><div><dt className="text-gray-400">Consulta emitida (America/La_Paz)</dt><dd>{businessTime(result.issuedAt)}</dd></div><div><dt className="text-gray-400">Selección y dataset</dt><dd className="break-all">{result.selectionId} · {result.datasetVersion} · {result.buildId}</dd></div><div><dt className="text-gray-400">SHA-256 del artefacto</dt><dd className="break-all">{result.artifactSha256}</dd></div><div><dt className="text-gray-400">Huella del snapshot de variables</dt><dd className="break-all">{result.featureSnapshotSha256}</dd></div><div><dt className="text-gray-400">Política</dt><dd>{result.policyVersion}: valores no finitos rechazados, negativos limitados a cero y salida sin redondeo en la API.</dd></div></dl></details>
    </div>}
    </>}
  </section>;
}
