import type { ScenarioBase, ScenarioResult, Snapshot } from "../services/scenarioView";
import { scenarioMonth } from "../services/scenarioPresentation";

type Reference = Pick<Snapshot, "productId" | "locationId" | "productName" | "locationName" | "targetMonth" | "historyMonthly">;
export default function ScenarioHistoryChart({ base, result, reference }: { base: ScenarioBase; result: ScenarioResult | null; reference: Reference }) {
  return <MonthlyChart reference={reference} history={base.displayHistory ?? base.history.map(h => ({ month: h.month, units: h.retailUnits + h.wholesaleUnits + h.unknownModeUnits }))} prediction={result} />;
}
export function DemonstrationChart({ reference, throughMonth }: { reference: Reference; throughMonth: string }) {
  const history = (reference.historyMonthly ?? []).filter(h => h.month <= throughMonth);
  return <MonthlyChart reference={reference} history={history} prediction={null} demo />;
}
function MonthlyChart({ reference, history, prediction, demo=false }: { reference: Reference; history: {month:string;units:number}[]; prediction: ScenarioResult | null; demo?:boolean }) {
  const months = demo ? history.map(h => h.month) : [...history.map(h => h.month), reference.targetMonth];
  const yMax = Math.max(1, ...history.map(h => h.units), prediction?.baseline.salesUnits ?? 0, prediction?.scenario.salesUnits ?? 0) * 1.15;
  const x = (i: number) => months.length === 1 ? 548 : 68 + i * 960 / (months.length - 1);
  const y = (units: number) => 238 - units / yMax * 190;
  const points = history.map((h, i) => `${x(i)},${y(h.units)}`).join(" ");
  const last = history.length - 1;
  return <figure className="rounded-xl border border-slate-700/60 bg-dark-900/40 p-4 min-w-0" aria-label="Histórico mensual y pronósticos del escenario">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <figcaption className="font-semibold">{demo ? "Evolución de ventas · 2026" : "Ventas anteriores y proyección"}</figcaption>
    </div>
    <p className="mt-2 text-xs text-gray-400">{demo ? "Historial sintético del dataset. La predicción de noviembre se consulta en «Predecir y comparar»." : "Historial hasta octubre. Noviembre muestra el pronóstico, sin una venta futura conocida."}</p>
    <p className="mt-1 text-xs text-gray-400">{reference.productName} · {reference.locationName}</p>
    <div className="overflow-x-auto">
      <svg viewBox="0 0 1100 310" className="mt-4 w-full min-w-[620px]" role="img" aria-label={demo ? "Ventas del dataset del periodo seleccionado de 2026" : history.length===3 ? "Tres meses de ventas simuladas y pronósticos base y con cambios" : "Historial hasta octubre de 2026 y pronóstico de noviembre"}>
        {[0, 1, 2, 3, 4].map(i => { const units = yMax * i / 4; return <g key={i}><line x1="68" x2="1028" y1={y(units)} y2={y(units)} stroke="#334155" strokeDasharray="3 4" /><text x="55" y={y(units) + 4} textAnchor="end" fill="#94a3b8" fontSize="12">{Math.round(units)}</text></g>; })}
        <polygon points={`${x(0)},238 ${points} ${x(last)},238`} fill="#3b82f6" fillOpacity="0.1" />
        <polyline points={points} fill="none" stroke="#60a5fa" strokeWidth="3" />
        {history.map((h, i) => <g key={h.month}><circle cx={x(i)} cy={y(h.units)} r="5" fill="#60a5fa" /><text x={x(i)} y={y(h.units) - 12} textAnchor="middle" fill="#bfdbfe" fontSize="13">{h.units}</text><title>{scenarioMonth(h.month)}: {h.units} unidades</title></g>)}
        {prediction && [{ value: prediction.baseline.salesUnits, color: "#fbbf24", offset: -12, label: "Base" }, { value: prediction.scenario.salesUnits, color: "#c084fc", offset: 18, label: "Con cambios" }].map(p => p.value === null ? null : <g key={p.label}><line x1={x(last)} y1={y(history[last].units)} x2={x(last + 1)} y2={y(p.value)} stroke={p.color} strokeWidth="2.5" strokeDasharray="6 5" /><circle cx={x(last + 1)} cy={y(p.value)} r="5" fill={p.color} /><text x={x(last + 1)} y={y(p.value) + p.offset} textAnchor="middle" fill={p.color} fontSize="13">{p.value.toLocaleString("es-BO", { maximumFractionDigits: 2 })}</text></g>)}
        {months.map((m, i) => <text key={m} x={x(i)} y="273" textAnchor="middle" fill="#94a3b8" fontSize="13"><tspan x={x(i)}>{scenarioMonth(m).split(" de ")[0]}</tspan><tspan x={x(i)} dy="17">{m.slice(0,4)}</tspan></text>)}
      </svg>
    </div>
    <div className="flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs"><span className="text-blue-300">● {demo ? "Unidades del dataset" : "Ventas simuladas"}</span>{!demo && <><span className="text-amber-300">● Pronóstico base</span><span className="text-purple-300">● Con cambios</span></>}</div>
    <details className="mt-3 text-xs text-gray-400"><summary className="cursor-pointer">Datos de la gráfica</summary><table className="mt-2 w-full text-left"><caption className="sr-only">{demo ? "Historial del dataset 2026" : "Serie del snapshot aprobado"}</caption><thead><tr><th className="py-1">Mes</th><th className="py-1">Unidades</th></tr></thead><tbody>{history.map(h => <tr key={h.month}><td className="py-1">{scenarioMonth(h.month)}</td><td>{h.units}</td></tr>)}{prediction && <><tr><td>Pronóstico base</td><td>{prediction.baseline.salesUnits ?? "No disponible"}</td></tr><tr><td>Con cambios</td><td>{prediction.scenario.salesUnits ?? "No disponible"}</td></tr></>}</tbody></table></details>
  </figure>;
}
