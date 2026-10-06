import type { ReporteCalidad } from "../../services/imageQuality";

const ESTILO_ESTADO: Record<ReporteCalidad["estado"], { chip: string; punto: string; texto: string }> = {
  buena: { chip: "bg-emerald-50 text-emerald-700 border-emerald-200", punto: "bg-emerald-500", texto: "Buena" },
  regular: { chip: "bg-amber-50 text-amber-700 border-amber-200", punto: "bg-amber-500", texto: "Regular" },
  mala: { chip: "bg-red-50 text-red-700 border-red-200", punto: "bg-red-500", texto: "Mala" },
};

interface Props {
  calidad: ReporteCalidad | null;
}

/**
 * Aviso de calidad previo a la búsqueda. Nunca bloquea: informa el veredicto y
 * deja que el usuario decida. Los números se muestran como dato medido, sin
 * inventar un "score de IA".
 */
export default function QualityBadge({ calidad }: Props) {
  if (!calidad) return null;
  const estilo = ESTILO_ESTADO[calidad.estado];
  const lado = Math.min(calidad.resolucion.ancho, calidad.resolucion.alto);

  return (
    <section className={`rounded-xl border p-3 ${estilo.chip}`} aria-label="Calidad de la imagen">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`inline-block h-2 w-2 rounded-full ${estilo.punto}`} aria-hidden="true" />
        <h3 className="text-sm font-semibold">Calidad de la foto: {estilo.texto}</h3>
        {calidad.estado !== "buena" && (
          <span className="text-xs font-medium">Esta foto puede reducir la precisión del resultado.</span>
        )}
      </div>

      <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] opacity-90">
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
          <dt>Lado menor</dt>
          <dd className="font-mono font-semibold">{lado} px</dd>
        </div>
        <div className="flex gap-1">
          <dt>Tamaño</dt>
          <dd className="font-mono font-semibold">{Math.round(calidad.bytesArchivo / 1024)} KB</dd>
        </div>
      </dl>

      {calidad.problemas.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-[11px] opacity-90" aria-label="Motivos del veredicto">
          {calidad.problemas.map((p) => (
            <li key={p} data-testid="calidad-problema">
              <span className="opacity-70">•</span> {p}
            </li>
          ))}
        </ul>
      )}

      {calidad.recomendaciones.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-[11px] opacity-90">
          {calidad.recomendaciones.map((r) => (
            <li key={r}>• {r}</li>
          ))}
        </ul>
      )}
    </section>
  );
}