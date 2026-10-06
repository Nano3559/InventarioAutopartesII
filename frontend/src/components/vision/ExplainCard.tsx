import type { VisionCandidatoPublico } from "../../types/vision";
import { explicarCandidato } from "../../services/explicabilidad";

interface Props {
  candidato: VisionCandidatoPublico;
}

/**
 * "¿Por qué aparece este producto?" — versión compacta para el panel.
 * Solo lista líneas con evidencia real; si no hay ninguna, no muestra la caja.
 */
export default function ExplainCard({ candidato }: Props) {
  const motivos = explicarCandidato(candidato);
  if (motivos.length === 0) return null;

  const aFavor = motivos.filter((m) => m.tipo === "ok");
  const avisos = motivos.filter((m) => m.tipo === "aviso");

  return (
    <details className="mt-2 rounded-lg border border-slate-200 bg-slate-50/70">
      <summary className="cursor-pointer select-none px-3 py-2 text-xs font-semibold text-slate-700 hover:text-primary-700">
        ¿Por qué aparece este producto?
      </summary>

      <div className="space-y-2 px-3 pb-2.5">
        {aFavor.length > 0 && (
          <ul className="space-y-0.5 text-[11px] text-slate-700">
            {aFavor.map((m) => (
              <li key={m.texto}>
                <span className="text-emerald-600">✓</span> {m.texto}
              </li>
            ))}
          </ul>
        )}
        {avisos.length > 0 && (
          <ul className="space-y-0.5 text-[11px] text-amber-700">
            {avisos.map((m) => (
              <li key={m.texto}>
                <span>⚠</span> {m.texto}
              </li>
            ))}
          </ul>
        )}
      </div>
    </details>
  );
}