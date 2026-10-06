import { Eye, AlertTriangle, CheckCircle2, HelpCircle } from "lucide-react";
import type { VerificacionMultiVista } from "../../services/multiView";

interface Props {
  verificacion: VerificacionMultiVista | null;
  /** true si la confianza está en zona media y aún no hay segunda foto. */
  ofrece: boolean;
  onConfirmar?: () => void;
}

const ESTILO: Record<string, { chip: string; icono: typeof Eye; color: string }> = {
  confirmado: { chip: "border-emerald-400/40 bg-emerald-500/10", icono: CheckCircle2, color: "text-emerald-300" },
  inconsistente: { chip: "border-amber-400/40 bg-amber-500/10", icono: AlertTriangle, color: "text-amber-300" },
  no_confirmado: { chip: "border-white/[0.08] bg-white/[0.03]", icono: HelpCircle, color: "text-gray-300" },
};

/**
 * Confirmación con segunda foto.
 *
 * Tres salidas posibles, siempre con texto y nunca con porcentaje inventado:
 *   - Confirmado por 2 imágenes
 *   - No confirmado
 *   - Resultados inconsistentes
 *
 * En el caso inconsistente se muestran las dos posibilidades detectadas y se
 * pide otra foto; no se elige una por promedio.
 */
export default function MultiVistaPanel({ verificacion, ofrece, onConfirmar }: Props) {
  if (ofrece) {
    return (
      <section className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-3.5" data-testid="vision-ofrece-segunda-foto">
        <div className="flex items-start gap-2.5">
          <Eye size={16} className="text-primary-400 shrink-0 mt-0.5" />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white">¿Querés confirmar con otra foto?</p>
            <p className="text-xs text-gray-400 mt-1">
              La confianza del modelo está en un nivel medio. Una segunda foto desde otro ángulo puede reforzar o desmentir la
              categoría detectada.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onConfirmar}
          className="mt-3 inline-flex items-center gap-2 bg-dark-700 hover:bg-primary-600 border border-white/10 text-white px-4 py-2 rounded-lg text-xs font-semibold transition-colors"
        >
          <Eye size={14} /> Confirmar con otra foto
        </button>
      </section>
    );
  }

  if (!verificacion) return null;

  const estilo = ESTILO[verificacion.estado] ?? ESTILO.no_confirmado;
  const Icono = estilo.icono;

  return (
    <section className={`rounded-xl border p-3.5 ${estilo.chip}`} data-testid="vision-verificacion" data-estado={verificacion.estado}>
      <div className="flex items-center gap-2">
        <Icono size={16} className={`${estilo.color} shrink-0`} />
        <h3 className={`text-sm font-semibold ${estilo.color}`}>{verificacion.etiqueta}</h3>
      </div>

      <p className="text-xs text-gray-300 mt-1.5">{verificacion.detalle}</p>

      {verificacion.estado === "inconsistente" && verificacion.vistas.length > 1 && (
        <ul className="mt-2.5 space-y-1" data-testid="vision-posibilidades">
          {verificacion.vistas.map((vista, i) => (
            <li
              key={`${vista.categoria}-${i}`}
              className="text-xs text-gray-200 bg-dark-900/50 border border-white/[0.06] rounded-lg px-2.5 py-1.5 flex items-center justify-between gap-2"
            >
              <span>
                {i === 0 ? "1.ª foto" : "2.ª foto"}: <span className="font-semibold">{vista.categoriaMapeada ?? vista.categoria}</span>
              </span>
              <span className="font-mono text-gray-400">{Math.round(vista.confianza * 100)}%</span>
            </li>
          ))}
        </ul>
      )}

      {verificacion.estado !== "inconsistente" && verificacion.vistas.length > 1 && (
        <p className="text-[11px] text-gray-500 mt-1.5">
          Confianza del modelo de la vista elegida: {Math.round(verificacion.confianzaYolo * 100)}%. Es la de YOLO, no un valor combinado.
        </p>
      )}
    </section>
  );
}