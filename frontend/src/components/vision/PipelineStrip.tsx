import type { ReporteCalidad } from "../../services/imageQuality";
import type { VisionAnalysis } from "../../types/vision";
import type { VerificacionMultiVista } from "../../services/multiView";

interface Props {
  analisis: VisionAnalysis;
  deteccion: VisionAnalysis["deteccion"];
  calidad: ReporteCalidad | null;
  verificacion?: VerificacionMultiVista | null;
}

const TEXTO_ESTADO: Record<string, string> = {
  buena: "buena",
  regular: "regular",
  mala: "mala",
};

/**
 * Recorrido del análisis, pensado para explicación técnica:
 * Foto → Control de calidad → YOLO → OCR → Catálogo → Compatibilidad → Disponibilidad.
 *
 * La página lo envuelve en un `<details>` colapsado por defecto ("Ver detalles
 * del análisis"): no ocupa el encabezado principal, solo se abre quien quiere
 * seguir los pasos de la defensa.
 */
export default function PipelineStrip({ analisis, deteccion, calidad, verificacion }: Props) {
  const codigos = deteccion.codigosDetectados ?? [];
  const hayDisponibles = analisis.candidatos.some((c) => c.disponibilidad?.nivel !== "NO_DISPONIBLE");
  const compatOk = (analisis.compatibilidad.verificadas ?? 0) > 0;

  const etapas: Array<{ etiqueta: string; estado: "ok" | "parcial" | "vacio" }> = [
    { etiqueta: "Foto", estado: "ok" },
    {
      // Nunca "n/d": si la medición no se pudo hacer se dice explícitamente.
      etiqueta: calidad ? `Control de calidad · ${TEXTO_ESTADO[calidad.estado]}` : "Control de calidad · no medido",
      estado: calidad ? (calidad.estado === "buena" ? "ok" : "parcial") : "vacio",
    },
    {
      etiqueta: `YOLO · ${Math.round(deteccion.confianza * 100)}%`,
      estado: deteccion.confianzaBaja ? "parcial" : "ok",
    },
    { etiqueta: codigos.length ? `OCR · ${codigos.length} código(s)` : "OCR · sin códigos", estado: codigos.length ? "ok" : "vacio" },
    { etiqueta: `${analisis.candidatos.length} candidato(s)`, estado: analisis.candidatos.length ? "ok" : "vacio" },
    { etiqueta: compatOk ? "Compatibilidad · verificada" : "Compatibilidad · no evaluada", estado: compatOk ? "ok" : "parcial" },
    { etiqueta: hayDisponibles ? "Disponibilidad · disponible" : "Disponibilidad · sin stock", estado: hayDisponibles ? "ok" : "parcial" },
  ];

  const badgeEstado = (estado: "ok" | "parcial" | "vacio") =>
    estado === "ok"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
      : estado === "parcial"
        ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
        : "border-white/[0.06] bg-white/[0.03] text-gray-500";

  return (
    <nav aria-label="Pipeline del análisis" className="flex flex-wrap items-center gap-1.5">
      {etapas.map((e, i) => (
        <span key={e.etiqueta} className="flex items-center gap-1.5">
          {i > 0 && <span className="text-[10px] text-gray-600">→</span>}
          <span
            className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${badgeEstado(e.estado)}`}
            data-estado={e.estado}
          >
            {e.etiqueta}
          </span>
        </span>
      ))}

      {verificacion?.estado === "confirmado" && (
        <>
          <span className="text-[10px] text-gray-600">→</span>
          <span className="rounded-full border border-emerald-400/40 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-300">
            Confirmado con 2 ángulos
          </span>
        </>
      )}
      {verificacion?.estado === "inconsistente" && (
        <>
          <span className="text-[10px] text-gray-600">→</span>
          <span className="rounded-full border border-amber-400/40 bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold text-amber-300">
            Resultados inconsistentes
          </span>
        </>
      )}
    </nav>
  );
}