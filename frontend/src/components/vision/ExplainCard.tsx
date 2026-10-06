import { useState } from "react";
import type { VisionCandidatoPublico } from "../../types/vision";
import { explicarCandidato } from "../../services/explicabilidad";

interface Props {
  candidato: VisionCandidatoPublico;
  /** false cuando la búsqueda no incluyó vehículo (compatibilidad no evaluada). */
  hayVehiculo?: boolean;
}

/**
 * Explicabilidad directa en cada tarjeta, en modo compacto: la razón o razones
 * principales a la vista y el resto detrás de "Ver evidencias". Cada línea tiene
 * evidencia real detrás (ver services/explicabilidad.ts); si no hay ninguna, no
 * se muestra la caja.
 */
export default function ExplainCard({ candidato, hayVehiculo = true }: Props) {
  const [verTodas, setVerTodas] = useState(false);
  const motivos = explicarCandidato(candidato, { hayVehiculo });
  if (motivos.length === 0) return null;

  const visibles = verTodas ? motivos : motivos.slice(0, 2);
  const ocultas = motivos.length - visibles.length;

  return (
    <div
      className="mt-2 rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-2.5"
      data-testid={`motivos-${candidato.itemCode}`}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">¿Por qué aparece?</p>
      <ul className="mt-1.5 space-y-1 text-[11px]">
        {visibles.map((m) => (
          <li key={m.texto} className={m.tipo === "ok" ? "text-emerald-300/90" : "text-amber-300/90"}>
            <span aria-hidden="true">{m.tipo === "ok" ? "✓" : "⚠"}</span> {m.texto}
          </li>
        ))}
      </ul>
      {ocultas > 0 && (
        <button
          type="button"
          onClick={() => setVerTodas((v) => !v)}
          data-testid={`evidencias-${candidato.itemCode}`}
          className="mt-1.5 text-[11px] font-semibold text-primary-300 hover:text-primary-200 transition-colors"
        >
          {verTodas ? "Ver menos" : `Ver evidencias (${motivos.length})`}
        </button>
      )}
    </div>
  );
}