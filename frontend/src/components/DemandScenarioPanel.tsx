import { useEffect, useRef, useState, type ReactNode } from "react";
import api from "../services/api";
import ScenarioHistoryChart from "./ScenarioHistoryChart";
import { productChoices, scenarioDate, scenarioMonth, spanishOrder, type ProductOrder } from "../services/scenarioPresentation";
import { changeNames, checkedCapabilities, checkedScenario, checkedScenarioBase, draftFromBase, emptyDraft, priorMonths, scenarioRequest, scenarioFailureText, type ScenarioBase, type Capabilities, type ChangeName, type Draft, type ScenarioResult } from "../services/scenarioView";

const titles: Record<ChangeName, string> = { history: "Cantidades de los tres meses cerrados", prices: "Precios por menor y por mayor", quote: "Cotización Bs/USD", cost: "Costo por unidad", stock: "Stock físico vendible", orders: "Compromisos y reservas", logistics: "Proveedor, tránsito y reposición interna" };
const shortTitles: Record<ChangeName, string> = { history: "Ventas previas", prices: "Precios", quote: "Tipo de cambio", cost: "Costo unitario", stock: "Stock", orders: "Pedidos y reservas", logistics: "Entregas" };
function Help({ children }: { children: ReactNode }) { return <details className="text-xs text-gray-400"><summary className="cursor-pointer">Ayuda</summary><p className="mt-2 leading-relaxed">{children}</p></details>; }
const inputClass = "w-full min-w-0 rounded-lg bg-dark-900 px-3 py-2.5 border border-slate-700/70 focus:border-primary-500 focus:outline-none";
const secondaryButton = "inline-flex items-center justify-center rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm font-medium text-gray-100 hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary-400 disabled:opacity-50";
function Field({ label, value, onChange, date = false }: { label: string; value: string; onChange: (v: string) => void; date?: boolean }) {
  return <label className="flex flex-col gap-1 min-w-0 text-sm">{label}<input className={inputClass} type={date ? "date" : "text"} inputMode={date ? undefined : "decimal"} value={date ? value.slice(0, 10) : value} onChange={e => onChange(date && e.target.value ? `${e.target.value}T00:00` : e.target.value)} /></label>;
}
const effectLabels: Record<string,string> = { USED:"Aplicado", NOT_USED_BY_SELECTED_MODEL:"No utilizado", ASSUMPTION_ONLY:"Supuesto", UNKNOWN:"Por revisar" };
const roleLabels: Record<string,string> = { DIRECT_MODEL_FEATURE:"Variable del modelo", DERIVED_MODEL_FEATURE:"Variable calculada", REPLENISHMENT_ONLY:"Solo reposición", VALIDATION_ONLY:"Validación", UNSUPPORTED:"No soportado" };
const replenishmentLabels: Record<string,string> = { NOT_REQUESTED:"No solicitada", OK_MONTH_END_ESTIMATE:"Estimación mensual", INCOMPLETE:"Datos insuficientes", OUTSIDE_FORECAST_HORIZON:"Fuera del horizonte" };
const fieldLabels: Record<string,string> = { retailPriceBs:"Precio por menor", wholesalePriceBs:"Precio por mayor", bsPerUsd:"Tipo de cambio", unitCostBs:"Costo final", unitCostUsd:"Costo proveedor", freightPerUnitBs:"Flete por unidad", otherPerUnitBs:"Otros costos por unidad", sellablePhysicalUnits:"Stock vendible", supplierLeadTimeDays:"Plazo proveedor", supplierDays:"Plazo proveedor", internalDays:"Reposición interna", internalRestockDays:"Reposición interna", effectiveAt:"Fecha de vigencia", observedAt:"Fecha de cotización", orderAt:"Fecha de compra", dueAt:"Entrega comprometida", expectedArrivalAt:"Llegada prevista", outstandingUnits:"Unidades pendientes", reservedUnits:"Unidades reservadas", pendingUnits:"Unidades en tránsito", reservedAfterHorizonUnits:"Reservadas para después", retailUnits:"Ventas por menor", wholesaleUnits:"Ventas por mayor", unknownModeUnits:"Ventas sin modalidad", orderId:"Pedido", shipmentId:"Envío",mode:"Modalidad" };
const warningLabels: Record<string,string> = { FORECAST_EXCEEDS_PLANNED_SUPPLY:"La estimación supera las unidades disponibles en el plan. Revisa las entradas y la reposición antes de tomar una decisión.", UNKNOWN_CHANNEL_MIX:"Falta identificar la modalidad de algunas ventas.", QUOTE_OLDER_THAN_30_DAYS_ASSUMPTION:"La cotización tiene más de 30 días. Se utiliza como supuesto, no como cotización vigente certificada.", COMMITMENT_OVERLAP_UNCERTAIN:"Los pedidos se tratan como un mínimo para evitar sumarlos dos veces al pronóstico.", EXPECTED_RECEIPTS_NOT_CONFIRMED_STOCK:"Las llegadas previstas todavía no son stock recibido.", OUTSIDE_TRAINING_RANGE:"Hay valores fuera del rango de entrenamiento. No se entrega una estimación numérica.", NO_DAILY_STOCKOUT_GUARANTEE:"El cálculo mensual no garantiza evitar faltantes antes de recibir la mercadería.", FORECAST_UNAVAILABLE:"Se necesita una predicción válida para calcular reposición." };
const display = (v: unknown) => v === null || v === undefined ? "No disponible" : typeof v === "number" ? v.toLocaleString("es-BO", { maximumFractionDigits: 4 }) : scenarioDate(String(v));

type Selection = {productId:number;locationId:number};
export default function DemandScenarioPanel({initialSelection,onSelection}: {initialSelection?:Selection|null;onSelection?:(selection:Selection)=>void} = {}) {
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [selection, setSelection] = useState("");
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  const [base, setBase] = useState<ScenarioBase | null>(null);
  const [baseLoading, setBaseLoading] = useState(false);
  const [productQuery, setProductQuery] = useState("");
  const [productOrder, setProductOrder] = useState<ProductOrder>("az");
  const request = useRef<AbortController | null>(null);
  const intentId = useRef<string | null>(null);
  const generation = useRef(0);
  const snapshot = caps?.snapshots.find(s => s.baseSnapshotId === selection);
  useEffect(()=>{if(snapshot) onSelection?.({productId:snapshot.productId,locationId:snapshot.locationId});},[snapshot?.productId,snapshot?.locationId,onSelection]);
  function invalidate(resetIntent = true) { if (resetIntent) intentId.current = null; generation.current++; request.current?.abort(); setBusy(false); setResult(null); setError(""); }
  function edit<K extends keyof Draft>(key: K, value: Draft[K]) { invalidate(); setDraft(d => ({ ...d, [key]: value })); }
  useEffect(() => {
    const abort = new AbortController(); let alive = true;
    setLoading(true); setCaps(null); setResult(null); setSelection(""); setDraft(emptyDraft());
    api.get("/predictions/scenarios/capabilities", { signal: abort.signal }).then(res => {
      if (!alive) return;
      const verified = checkedCapabilities(res.data); setCaps(verified); setSelection((verified.snapshots.find(s=>s.productId===initialSelection?.productId && s.locationId===initialSelection?.locationId) ?? verified.snapshots[0]).baseSnapshotId); setError("");
    }).catch(() => { if (alive) setError("Los escenarios todavía no están habilitados. La consulta histórica sigue disponible."); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; abort.abort(); generation.current++; request.current?.abort(); };
  }, [reload]);
  useEffect(() => {
    if (!snapshot) { setBase(null); return; }
    const abort = new AbortController(); let alive = true;
    setBaseLoading(true); setBase(null); invalidate(); setDraft(emptyDraft());
    api.get(`/predictions/scenarios/snapshots/${encodeURIComponent(snapshot.baseSnapshotId)}`, { signal: abort.signal }).then(res => {
      if (!alive) return;
      const verified = checkedScenarioBase(res.data, snapshot); setBase(verified); setDraft(draftFromBase(verified, snapshot.targetMonth)); setError("");
    }).catch(() => { if (alive) setError("No se pudo cargar la referencia base. Actualiza las opciones."); }).finally(() => { if (alive) setBaseLoading(false); });
    return () => { alive = false; abort.abort(); };
  }, [snapshot]);
  async function compare() {
    if (!caps || !snapshot || !base || baseLoading) return;
    const selected = snapshot;
    invalidate(false); const seq = generation.current;
    try {
      const payload = scenarioRequest(draft, selected, caps.supportedChanges, intentId.current ??= crypto.randomUUID());
      const abort = new AbortController(); request.current = abort; setBusy(true);
      const res = await api.post("/predictions/scenarios/preview", payload, { signal: abort.signal });
      if (seq !== generation.current || abort.signal.aborted) return;
      setResult(checkedScenario(res.data, selected, caps));
    } catch (e) {
      if (seq === generation.current) setError(scenarioFailureText(e));
    } finally { if (seq === generation.current) setBusy(false); }
  }
  function exportEvidence() {
    if (!result || !snapshot) return;
    const blob = new Blob([JSON.stringify({ origin: "SYNTHETIC_SCENARIO_NOT_REAL_SALES", selection: snapshot, result }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob), a = document.createElement("a"); a.href = url; a.download = `escenario-${result.scenarioId}.json`; a.click(); URL.revokeObjectURL(url);
  }
  if (!caps) return <section className="rounded-2xl border border-slate-700/60 bg-dark-800/50 p-6" aria-label="Escenarios ampliados">
    <div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-lg font-medium text-white">Escenarios</h2><p role={loading ? "status" : "alert"} className="mt-2 max-w-xl text-sm text-gray-400">{loading ? "Cargando opciones…" : "Los escenarios todavía no están habilitados. La consulta histórica sigue disponible."}</p></div><button className="rounded-lg border border-slate-600 px-4 py-2 text-sm disabled:opacity-50" disabled={loading} onClick={() => setReload(n => n + 1)}>Reintentar</button></div>
  </section>;
  const months = snapshot ? priorMonths(snapshot.targetMonth) : ["Mes -3", "Mes -2", "Mes -1"];
  const quantitative = result && [{ label: "Base", units: result.baseline.salesUnits }, { label: "Hipótesis", units: result.scenario.salesUnits }];
  const ceiling = Math.max(1, ...quantitative?.map(x => x.units ?? 0) ?? [1]);
  const products = snapshot ? productChoices(caps.snapshots, snapshot, productQuery, productOrder) : [];
  const locations = snapshot ? [...new Map(caps.snapshots.filter(s => s.productId === snapshot.productId).map(s => [s.locationId, s])).values()].sort((a,b) => spanishOrder.compare(a.locationName, b.locationName) || a.locationId - b.locationId) : [];
  const availableMonths = snapshot ? caps.snapshots.filter(s => s.productId === snapshot.productId && s.locationId === snapshot.locationId).sort((a,b) => a.targetMonth.localeCompare(b.targetMonth)) : [];
  function choose(value: string, key: "productId" | "locationId" | "targetMonth") {
    if (!snapshot) return;
    const candidates = caps!.snapshots.filter(s => key === "productId" ? s.productId === Number(value) : key === "locationId" ? s.productId === snapshot.productId && s.locationId === Number(value) : s.productId === snapshot.productId && s.locationId === snapshot.locationId && s.targetMonth === value);
    const next = candidates.find(s => s.locationId === snapshot.locationId && s.targetMonth === snapshot.targetMonth) ?? candidates.find(s => s.targetMonth === snapshot.targetMonth) ?? candidates[0];
    if (next && next.baseSnapshotId !== selection) {
      invalidate(); setBase(null); setBaseLoading(true); setDraft(emptyDraft());
      setSelection(next.baseSnapshotId);
    }
  }
  function changeOrder(order: ProductOrder) {
    setProductOrder(order);
    if (snapshot && (order === "most" || order === "least")) {
      const first = productChoices(caps!.snapshots, snapshot, productQuery, order)[0];
      if (first) choose(String(first.productId), "productId");
    }
  }
  return <section className="rounded-2xl border border-slate-700/60 bg-dark-800/50 p-5 space-y-4 min-w-0" aria-label="Escenarios ampliados">
    <div className="flex items-start justify-between gap-3"><div><h2 className="text-lg font-semibold">Predecir y comparar</h2><p className="mt-1 text-sm text-gray-400">Historial hasta octubre de 2026. Pronóstico de noviembre: modifica una condición y compara.</p></div><span className="rounded-full bg-slate-700/60 px-3 py-1 text-xs text-gray-300">V{caps.datasetVersion} · 1 mes</span></div>
    <details className="text-xs text-gray-400"><summary className="cursor-pointer">Alcance de la simulación</summary><p className="mt-2">Datos sintéticos. Las ediciones no cambian ventas, precios o inventario reales. Cada resultado indica si el modelo utiliza el cambio. Las ventas observadas no incluyen toda la demanda perdida.</p></details>
    {loading && <p role="status">Consultando capacidades del backend…</p>}
    {error && <p role="alert" className="rounded border border-amber-500 p-3 text-amber-200">{error}</p>}
    <button className={secondaryButton} disabled={loading || busy} onClick={() => { invalidate(); setReload(n => n + 1); }}>Actualizar opciones</button>
    {snapshot && <div className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label className="flex flex-col gap-1 text-sm">Buscar producto<input type="search" className={inputClass} value={productQuery} onChange={e => setProductQuery(e.target.value)} placeholder="Nombre o identificador" /></label>
        <label className="flex flex-col gap-1 text-sm">Ordenar productos<select className={inputClass} value={productOrder} onChange={e => changeOrder(e.target.value as ProductOrder)}><option value="az">Nombre: A a Z</option><option value="za">Nombre: Z a A</option><option value="most">Más vendido</option><option value="least">Menos vendido</option></select></label>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label className="flex flex-col gap-1 text-sm">Producto<select className={inputClass} value={products.some(s => s.productId === snapshot.productId) ? snapshot.productId : ""} onChange={e => choose(e.target.value,"productId")}><option value="" disabled>Selecciona un resultado</option>{products.map(s => <option key={s.productId} value={s.productId}>{s.productName}{caps.snapshots.some(other => other.productId !== s.productId && other.productName === s.productName) ? ` · #${s.productId}` : ""}</option>)}</select></label>
        <label className="flex flex-col gap-1 text-sm">Tienda<select className={inputClass} value={snapshot.locationId} onChange={e => choose(e.target.value,"locationId")}>{locations.map(s => <option key={s.locationId} value={s.locationId}>{s.locationName}</option>)}</select></label>
        <label className="flex flex-col gap-1 text-sm">Mes de predicción<select className={inputClass} value={snapshot.targetMonth} onChange={e => choose(e.target.value,"targetMonth")}>{availableMonths.map(s => <option key={s.targetMonth} value={s.targetMonth}>{scenarioMonth(s.targetMonth)}</option>)}</select></label>
      </div>
      {!products.length && <p role="status" className="text-sm text-amber-200">No hay productos que coincidan. La consulta actual sigue siendo {snapshot.productName}.</p>}
      {(productOrder === "most" || productOrder === "least") && <p className="text-xs text-gray-400">Orden según ventas de {scenarioMonth(priorMonths(snapshot.targetMonth)[2])} en {snapshot.locationName}. Los productos sin dato quedan al final.</p>}
    </div>}
    {baseLoading && <p role="status" className="text-sm text-gray-400">Cargando valores base…</p>}
    {base && snapshot && <section aria-label="Ventas anteriores para la predicción" className="rounded-xl border border-slate-700/60 p-4 space-y-3">
      <div><h3 className="text-sm font-semibold">Ventas anteriores</h3><p className="mt-1 text-xs text-gray-400">Referencia base para predecir {scenarioMonth(snapshot.targetMonth)}.</p></div>
      <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3">{base.history.map(h => <div key={h.month} className="rounded-lg bg-dark-900/60 p-3"><dt className="text-xs text-gray-400 capitalize">{scenarioMonth(h.month)}</dt><dd className="mt-1 text-lg font-semibold">{(h.retailUnits + h.wholesaleUnits + h.unknownModeUnits).toLocaleString("es-BO")} <span className="text-xs font-normal text-gray-400">unidades</span></dd></div>)}</dl>
    </section>}
    {base && <div className="grid grid-cols-2 md:grid-cols-6 gap-2" aria-label="Valores base del escenario">{[{label:"Por menor",value:`Bs ${base.retail}`},{label:"Por mayor",value:`Bs ${base.wholesale}`},{label:"Costo",value:`Bs ${base.costBs}`},{label:"Bs por USD",value:base.quote},{label:"Stock vendible",value:`${base.stock} u.`},{label:"Proveedor",value:`${base.supplierDays} días`}].map(v => <div className="rounded-lg bg-dark-900/60 p-3" key={v.label}><p className="text-xs text-gray-400">{v.label}</p><p className="mt-1 text-sm font-semibold">{v.value}</p></div>)}</div>}
    {base && caps.stockTrainingMax !== undefined && base.stock > caps.stockTrainingMax && <p role="status" className="rounded-lg border border-amber-500/30 p-3 text-sm text-amber-200">El stock base ({base.stock} unidades) supera el rango aprendido ({caps.stockTrainingMax}). El modelo se abstendrá con estos valores. Una hipótesis de stock debe representar una condición válida.</p>}
    {snapshot && <details className="text-xs text-gray-400 break-all"><summary className="cursor-pointer">Referencia del escenario</summary><p className="mt-2">Snapshot: {snapshot.baseSnapshotId}. Corte: {snapshot.targetMonth}-01 (America/La_Paz).</p></details>}
    {base && snapshot && <ScenarioHistoryChart key={snapshot.baseSnapshotId} base={base} result={result} reference={snapshot} />}
    <fieldset disabled={!base || baseLoading} className="grid grid-cols-1 lg:grid-cols-2 gap-3 items-start disabled:opacity-60">
      {changeNames.map(name => <fieldset key={name} className={`border rounded-xl p-4 min-w-0 space-y-3 ${draft.enabled[name] ? "border-primary-500/40 bg-primary-500/5" : "border-slate-700/60 bg-dark-900/30"}`}><legend className="sr-only">{titles[name]}</legend>
        <label className="flex cursor-pointer items-center justify-between gap-3"><span className="text-sm font-medium">{shortTitles[name]}</span><span className="flex items-center gap-2 text-xs text-gray-400">{draft.enabled[name] ? "Modificar" : "Sin cambios"}<input className="h-4 w-4 accent-red-500" type="checkbox" aria-label={`Modificar ${shortTitles[name]}`} checked={draft.enabled[name]} disabled={!caps.supportedChanges.includes(name)} onChange={e => edit("enabled", { ...draft.enabled, [name]: e.target.checked })} /></span></label>
        {!!caps && !caps.supportedChanges.includes(name) && <p className="text-amber-200 text-sm">No soportado por el servidor seleccionado.</p>}
        {draft.enabled[name] && <div className="space-y-3">
          {name === "history" && <><Help>Solo meses sintéticos completos. Cero significa una cantidad conocida, no un dato faltante.</Help>{draft.history.map((h, i) => <div key={i} className="space-y-2 border-t border-slate-600 pt-2"><p className="capitalize">{scenarioMonth(months[i])}</p><div className="grid grid-cols-1 sm:grid-cols-3 gap-2">{(["retailUnits", "wholesaleUnits", "unknownModeUnits"] as const).map((k, n) => <Field key={k} label={["Unidades por menor", "Unidades por mayor", "Modalidad desconocida"][n]} value={h[k]} onChange={v => edit("history", draft.history.map((r, j) => i === j ? { ...r, [k]: v } : r))} />)}</div></div>)}</>}
          {name === "prices" && <><div className="grid grid-cols-1 sm:grid-cols-2 gap-2"><Field label="Nuevo precio por menor (Bs/unidad)" value={draft.retail} onChange={v => edit("retail", v)} /><Field label="Nuevo precio por mayor (Bs/unidad)" value={draft.wholesale} onChange={v => edit("wholesale", v)} /></div><Field label="Vigencia del nuevo precio (America/La_Paz)" date value={draft.priceAt} onChange={v => edit("priceAt", v)} /><Help>El precio base proviene del servidor. Mayor ≤ menor, ambos ≥ costo. Un cambio a mitad del mes exige soporte temporal.</Help></>}
          {name === "quote" && <><p className="text-xs text-gray-400">La cotización convierte costos de importación. Por sí sola no cambia el pronóstico ni la reposición en unidades.</p><Field label="Cotización hipotética (Bs por USD)" value={draft.quote} onChange={v => edit("quote", v)} /><Field label="Observada al corte o antes (America/La_Paz)" date value={draft.quoteAt} onChange={v => edit("quoteAt", v)} /><Help>No se ofrece una cotización real ni un valor automático. La cotización por sí sola no cambia las ventas previstas. Se usa al calcular una importación en USD.</Help></>}
          {name === "cost" && <><label className="flex flex-col gap-1">Origen del costo<select className={inputClass} value={draft.costMode} onChange={e => edit("costMode", e.target.value as Draft["costMode"])}><option value="SET_LANDED_COST_BS">Costo final puesto en tienda, Bs</option><option value="SIMULATE_IMPORT_USD">Importación hipotética, USD + gastos Bs</option></select></label>{draft.costMode === "SET_LANDED_COST_BS" ? <Field label="Costo final (Bs/unidad)" value={draft.costBs} onChange={v => edit("costBs", v)} /> : <><Field label="Costo proveedor (USD/unidad)" value={draft.costUsd} onChange={v => edit("costUsd", v)} /><Field label="Flete (Bs/unidad)" value={draft.freight} onChange={v => edit("freight", v)} /><Field label="Otros gastos (Bs/unidad)" value={draft.other} onChange={v => edit("other", v)} /><Help>USD × cotización Bs/USD + flete Bs + otros Bs. El backend resuelve la cotización, sin reconvertir un costo ya puesto en tienda.</Help></>}<Field date label="Vigencia del costo (America/La_Paz)" value={draft.costAt} onChange={v => edit("costAt", v)} /></>}
          {name === "stock" && <><Field label="Unidades físicas vendibles al corte" value={draft.stock} onChange={v => edit("stock", v)} /><Help>Incluye reservas físicas. Excluye tránsito, cuarentena y devoluciones sin inspección. No equivale al stock histórico real.</Help></>}
          {name === "orders" && <><Help>Activar con una lista vacía elimina el plan hipotético, sin cancelar pedidos reales.</Help>{draft.orders.map((o, i) => <div key={i} className="border border-slate-600 p-2 rounded space-y-2"><Field label={`Pedido ${i + 1}: identificador`} value={o.orderId} onChange={v => edit("orders", draft.orders.map((r, j) => i === j ? { ...r, orderId: v } : r))} /><label className="flex flex-col">Modalidad<select className={inputClass} value={o.mode} onChange={e => edit("orders", draft.orders.map((r, j) => i === j ? { ...r, mode: e.target.value as typeof o.mode } : r))}><option value="POR_MENOR">POR MENOR</option><option value="POR_MAYOR">POR MAYOR</option></select></label>{(["outstandingUnits", "reservedUnits", "dueAt"] as const).map((k, n) => <Field key={k} label={["Unidades pendientes", "Unidades reservadas", "Entrega comprometida (America/La_Paz)"][n]} date={k === "dueAt"} value={o[k]} onChange={v => edit("orders", draft.orders.map((r, j) => i === j ? { ...r, [k]: v } : r))} />)}<button className={secondaryButton} onClick={() => edit("orders", draft.orders.filter((_, j) => i !== j))}>Quitar pedido {i + 1}</button></div>)}<button className={secondaryButton} disabled={draft.orders.length >= 100} onClick={() => edit("orders", [...draft.orders, { orderId: `pedido-${draft.orders.length + 1}`, mode: "POR_MAYOR", outstandingUnits: "", reservedUnits: "0", dueAt: "" }])}>Añadir compromiso hipotético</button></>}
          {name === "logistics" && <><Field label="Plazo proveedor (días calendario)" value={draft.supplierDays} onChange={v => edit("supplierDays", v)} /><Field label="Reposición interna (días calendario)" value={draft.internalDays} onChange={v => edit("internalDays", v)} /><Field date label="Fecha prevista de compra (America/La_Paz)" value={draft.orderAt} onChange={v => edit("orderAt", v)} />{draft.shipments.map((o, i) => <div key={i} className="border border-slate-600 p-2 rounded space-y-2">{(["shipmentId", "pendingUnits", "reservedAfterHorizonUnits", "expectedArrivalAt"] as const).map((k, n) => <Field key={k} label={["Identificador del envío", "Unidades pendientes en tránsito", "Reservadas para después del horizonte", "Llegada esperada (America/La_Paz)"][n]} date={k === "expectedArrivalAt"} value={o[k]} onChange={v => edit("shipments", draft.shipments.map((r, j) => i === j ? { ...r, [k]: v } : r))} />)}<button className={secondaryButton} onClick={() => edit("shipments", draft.shipments.filter((_, j) => i !== j))}>Quitar envío {i + 1}</button></div>)}<button className={secondaryButton} disabled={draft.shipments.length >= 100} onClick={() => edit("shipments", [...draft.shipments, { shipmentId: `envio-${draft.shipments.length + 1}`, pendingUnits: "", reservedAfterHorizonUnits: "0", expectedArrivalAt: "" }])}>Añadir envío hipotético</button><Help>Una llegada prevista no es una recepción confirmada. El plazo puede superar el horizonte de un mes e impedir una sugerencia válida.</Help></>}
        </div>}
      </fieldset>)}
      <fieldset className="border border-slate-700/60 bg-dark-900/30 p-4 rounded-xl min-w-0 space-y-3"><legend className="sr-only">Política de reposición</legend><label className="flex gap-2"><input type="checkbox" checked={draft.replenish} onChange={e => edit("replenish", e.target.checked)} /><span className="text-sm font-medium">Calcular reposición</span></label>{draft.replenish && <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">{(["safety", "minimum", "multiple", "review"] as const).map((k, i) => <Field key={k} label={["Seguridad (unidades)", "Pedido mínimo (unidades)", "Múltiplo de compra (unidades)", "Periodo de revisión (días)"][i]} value={draft[k]} onChange={v => edit(k, v)} />)}</div>}<Help>Se usa el mayor valor entre pronóstico y compromisos, luego seguridad. No se descuentan las mismas reservas dos veces. No garantiza disponibilidad diaria ni crea una compra.</Help></fieldset>
    </fieldset>
    <button className="rounded bg-primary-600 p-3 disabled:opacity-50" disabled={!snapshot || !caps || !base || baseLoading || busy || loading} onClick={() => void compare()}>{busy ? "Comparando…" : "Comparar base e hipótesis"}</button>
    {!caps && <p className="text-sm text-amber-200">Selecciona una referencia disponible para comparar.</p>}
    {result && <div className="space-y-4" aria-live="polite"><div className="flex items-center justify-between gap-3"><h3 className="text-lg font-semibold">Comparación</h3><button className={secondaryButton} aria-label="Exportar evidencia JSON de esta comparación" onClick={exportEvidence}>Exportar</button></div><div className="grid grid-cols-1 sm:grid-cols-3 gap-3">{[{label:"Base",value:result.baseline.salesUnits},{label:"Con cambios",value:result.scenario.salesUnits},{label:"Diferencia",value:result.deltaSalesUnits}].map(item => <div key={item.label} className="rounded-xl bg-dark-900 border border-slate-700/50 p-4"><p className="text-xs text-gray-400">{item.label}</p><p className="mt-2 text-2xl font-semibold">{display(item.value)}<span className="ml-1 text-xs font-normal text-gray-400">unidades</span></p></div>)}</div>{result.deltaSalesUnits === 0 && result.impacts.some(i => i.effectStatus === "USED" && i.before !== i.after) && <p className="text-sm text-gray-400">El cambio fue aplicado, pero el modelo mantiene la misma estimación para estas entradas.</p>}{result.warnings.includes("FORECAST_EXCEEDS_PLANNED_SUPPLY") && <p role="status" className="rounded-lg border border-amber-500/30 p-3 text-sm text-amber-200">{warningLabels.FORECAST_EXCEEDS_PLANNED_SUPPLY}</p>}{result.scenario.salesUnits === null && <p className="text-sm text-amber-200">El modelo no puede estimar este escenario.</p>}<div role="img" aria-label="Comparación visual base e hipótesis" className="space-y-2">{quantitative && quantitative.map(p => <div key={p.label}><span>{p.label}: {display(p.units)}</span><div className="h-4 bg-slate-900 rounded"><div className="h-4 bg-red-500 rounded" style={{ width: `${p.units === null ? 0 : 100 * p.units / ceiling}%` }} /></div></div>)}</div>
      {result.impacts.length > 0 && <details className="rounded-xl border border-slate-700/60 p-3"><summary className="cursor-pointer text-sm">Ver cambios aplicados</summary><div className="overflow-x-auto mt-3"><table className="w-full min-w-[760px] text-left text-sm"><caption className="text-left">Entradas antes y después. No todas son variables del modelo.</caption><thead><tr>{["Campo", "Base", "Hipótesis", "Unidad", "Uso real", "Explicación"].map(t => <th className="p-2" key={t}>{t}</th>)}</tr></thead><tbody>{result.impacts.map((i, n) => <tr key={n}><td className="p-2">{fieldLabels[i.field.split(".").pop() ?? i.field] ?? i.field.replace(/_/g," ")}</td><td className="p-2">{display(i.before)}</td><td className="p-2">{display(i.after)}</td><td className="p-2">{i.unit}</td><td className="p-2">{effectLabels[i.effectStatus] ?? "Por revisar"}<details className="mt-1 text-xs text-gray-400"><summary className="cursor-pointer">Detalle</summary>{roleLabels[i.role] ?? i.role}</details></td><td className="p-2">{i.explanation}</td></tr>)}</tbody></table></div></details>}
      {result.replenishment.status !== "NOT_REQUESTED" && <div className="border border-slate-600 rounded p-3 space-y-2"><h3>Reposición: {replenishmentLabels[String(result.replenishment.status)] ?? "Por revisar"}</h3><p className="text-xl font-semibold">{display(result.replenishment.suggestedUnits)}{" "}<span className="ml-1 text-xs font-normal text-gray-400">unidades sugeridas</span></p><details className="text-sm text-gray-400"><summary className="cursor-pointer">Ver cálculo</summary><dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">{Object.entries(result.replenishment).filter(([k]) => k !== "warnings").map(([k, v]) => <div key={k} className="break-words"><dt>{({ suggestedUnits: "Reposición sugerida (unidades)", requiredUnits: "Unidades requeridas", availablePositionUnits: "Posición disponible", committedUnitsWithinHorizon: "Compromisos del mes", reservedUnitsWithinHorizon: "Reservas del mes", reservedUnitsAfterHorizon: "Reservas posteriores", eligibleIncomingUnits: "Entradas elegibles", rawNeedUnits: "Necesidad antes del mínimo y múltiplo", minimumOrderUnits: "Pedido mínimo", orderMultipleUnits: "Múltiplo de compra", expectedNewOrderArrivalAt: "Llegada del nuevo pedido", protectionEndAt: "Fin de protección", status: "Estado" } as Record<string, string>)[k] ?? k}</dt><dd>{k === "status" ? replenishmentLabels[String(v)] : display(v)}</dd></div>)}</dl></details>{(result.replenishment.warnings as string[]).map(w => <p key={w}>{warningLabels[w] ?? w}</p>)}</div>}
      <details className="rounded-xl border border-slate-700/60 p-3 text-xs text-gray-400"><summary className="cursor-pointer">Supuestos, métricas y versión</summary><div className="mt-3 space-y-2">      {result.metrics && <p>Métricas guardadas ({result.metrics.partition === "FINAL_TEST_SAVED" ? "evaluación final" : "validación"}): MAE {display(result.metrics.mae)} unidades, RMSE {display(result.metrics.rmse)}, R² {display(result.metrics.r2)}. No se reevalúa TEST en esta consulta.</p>}
      {result.assumptions.map((a, i) => <p className="text-amber-200" key={i}>Supuesto: {a}</p>)}{result.warnings.map((w, i) => <p className="text-amber-200" key={i}>Advertencia: {warningLabels[w] ?? w}</p>)}<p className="break-all text-sm">Dataset {result.datasetVersion} · Modelo {result.modelVersion} · Política {result.policyVersion} · SHA-256 {result.artifactSha256}</p></div></details>
    </div>}
  </section>;
}
