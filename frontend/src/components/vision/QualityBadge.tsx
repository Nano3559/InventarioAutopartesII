import { useState } from "react";
import { Camera, AlertTriangle } from "lucide-react";
import type { ReporteCalidad } from "../../services/imageQuality";

const ESTILO_ESTADO: Record<ReporteCalidad["estado"], { chip: string; texto: string; expande: boolean }> = {
  buena: { chip: "border-emerald-500/30 bg-emerald-500/10", texto: "Calidad buena", expande: false },
  regular: { chip: "border-amber-500/30 bg-amber-500/10", texto: "Calidad regular", expande: true },
  mala: { chip: "border-red-500/30 bg-red-500/10", texto: "La imagen puede reducir la precisión", expande: true },
};

interface Props {
  calidad: ReporteCalidad | null;
  /** Permite ofrecer "Tomar otra foto" cuando la foto es claramente mala. */
  onRepetirFoto?: () => void;
  /** Re-lanza la búsqueda con la misma foto ("Buscar igualmente"). Solo aplica a mala. */
  onBuscarIgualmente?: () => void;
}

/**
 * Veredicto de calidad compacto del MODO ESCANEO INTELIGENTE:
 *   - buena:   "🟢 Calidad buena" (una sola línea, sin botones).
 *   - regular: "🟡 Calidad regular" + [Ver recomendaciones].
 *   - mala:    "🔴 La imagen puede reducir la precisión" + [Tomar otra foto]
 *              y [Buscar igualmente].
 *
 * Las métricas (brillo, nitidez, resolución) solo se muestran al expandir el
 * detalle: son para la defensa, no para la UX primaria. Sin medición real no se
 * dibuja nada: jamás "n/d".
 */
export default function QualityBadge({ calidad, onRepetirFoto, onBuscarIgualmente }: Props) {
  const [abierto, setAbierto] = useState(false);
  if (!calidad) return null;

  const estilo = ESTILO_ESTADO[calidad.estado];
  const mala = calidad.estado === "mala";

  if (calidad.estado === "buena") {
    return (
      <section
        className={`flex items-center gap-2 rounded-xl border px-3 py-2.5 ${estilo.chip}`}
        aria-label="Calidad de la imagen"
        data-testid="vision-calidad-badge"
      >
        <span aria-hidden="true">🟢</span>
        <p className="text-xs font-semibold text-emerald-300">Calidad buena</p>
      </section>
    );
  }

  return (
    <section
      className={`rounded-xl border p-3.5 ${estilo.chip}`}
      aria-label="Calidad de la imagen"
      data-testid="vision-calidad-badge"
    >
      <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
        <span aria-hidden="true">{mala ? "🔴" : "🟡"}</span>
        <p className={`text-xs font-semibold ${mala ? "text-red-300" : "text-amber-300"}`}>{estilo.texto}</p>
        {estilo.expande && (
          <button
            type="button"
            onClick={() => setAbierto((v) => !v)}
            aria-expanded={abierto}
            className="ml-auto inline-flex items-center text-[11px] font-semibold text-gray-400 hover:text-white transition-colors"
          >
            {abierto ? "Ocultar" : "Ver recomendaciones"}
          </button>
        )}
        {mala && onRepetirFoto && (
          <button
            type="button"
            onClick={onRepetirFoto}
            className="inline-flex items-center gap-1.5 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-1.5 text-[11px] font-semibold text-red-300 hover:bg-red-500/20 transition-colors"
          >
            <Camera size={12} /> Tomar otra foto
          </button>
        )}
        {mala && onBuscarIgualmente && (
          <button
            type="button"
            onClick={onBuscarIgualmente}
            className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 text-[11px] font-semibold text-gray-300 hover:text-white transition-colors"
          >
            Buscar igualmente
          </button>
        )}
      </div>

      {abierto && (
        <div className="mt-2.5 space-y-1.5">
          {calidad.problemas.length > 0 && (
            <ul className="space-y-0.5 text-[11px] text-white/80" data-testid="calidad-problemas">
              {calidad.problemas.map((p) => (
                <li key={p} data-testid="calidad-problema" className="flex gap-1.5">
                  <AlertTriangle size={11} className="shrink-0 mt-0.5 text-white/40" />
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          )}
          {calidad.recomendaciones.length > 0 && (
            <ul className="space-y-0.5 text-[11px] text-white/70">
              {calidad.recomendaciones.map((r) => (
                <li key={r}>› {r}</li>
              ))}
            </ul>
          )}
          <dl className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-white/60">
            <div className="flex gap-1">
              <dt>Brillo</dt>
              <dd className="font-mono font-semibold">{Math.round(calidad.brillo * 100)}%</dd>
            </div>
            <div className="flex gap-1">
              <dt>Nitidez</dt>
              <dd className="font-mono font-semibold">{calidad.nitidez.toFixed(4)}</dd>
            </div>
            <div className="flex gap-1">
              <dt>Resolución</dt>
              <dd className="font-mono font-semibold">
                {calidad.resolucion.ancho}×{calidad.resolucion.alto}
              </dd>
            </div>
            <div className="flex gap-1">
              <dt>Tamaño</dt>
              <dd className="font-mono font-semibold">{Math.round(calidad.bytesArchivo / 1024)} KB</dd>
            </div>
          </dl>
        </div>
      )}
    </section>
  );
}