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
 * Tira compacta que hace visible el pipeline de la demo en una sola pasada:
 * foto → bbox → YOLO → OCR → calidad → candidatos → evidencias → stock.
 *
 * Un solo renglón de chips. No reemplaza a los componentes, solo resume el
 * recorrido para que el docente pueda seguirlo sin que le cuenten pasos sueltos.
 */
export default function PipelineStrip({ analisis, deteccion, calidad, verificacion }: Props) {
  const codigos = deteccion.codigosDetectados ?? [];
  const hayEvidencia = analisis.candidatos.some((c) => (c.evidencias?.length ?? 0) > 0);
  const hayDisponibles = analisis.candidatos.some((c) => c.disponibilidad?.nivel !== "NO_DISPONIBLE");

  const etapas: Array<{ etiqueta: string; estado: "ok" | "parcial" | "vacio" }> = [
    { etiqueta: "Foto", estado: "ok" },
    { etiqueta: deteccion.boundingBox ? "BoundingBox" : "Imagen completa", estado: deteccion.boundingBox ? "ok" : "parcial" },
    {
      etiqueta: `YOLO · ${Math.round(deteccion.confianza * 100)}%`,
      estado: deteccion.confianzaBaja ? "parcial" : "ok",
    },
    { etiqueta: codigos.length ? `OCR · ${codigos.length} código(s)` : "OCR · sin códigos", estado: codigos.length ? "ok" : "vacio" },
    {
      etiqueta: calidad ? `Calidad · ${TEXTO_ESTADO[calidad.estado]}` : "Calidad · n/d",
      estado: calidad ? (calidad.estado === "buena" ? "ok" : "parcial") : "vacio",
    },
    { etiqueta: `${analisis.candidatos.length} candidato(s)`, estado: analisis.candidatos.length ? "ok" : "vacio" },
    { etiqueta: hayEvidencia ? "Evidencias" : "Sin evidencias", estado: hayEvidencia ? "ok" : "vacio" },
    { etiqueta: hayDisponibles ? "Disponible" : "Sin stock", estado: hayDisponibles ? "ok" : "parcial" },
  ];

  const badgeEstado = (estado: "ok" | "parcial" | "vacio") =>
    estado === "ok"
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : estado === "parcial"
        ? "bg-amber-50 text-amber-700 border-amber-200"
        : "bg-slate-100 text-slate-500 border-slate-200";

  return (
    <nav aria-label="Pipeline del análisis" className="flex flex-wrap items-center gap-1.5">
      {etapas.map((e, i) => (
        <span key={e.etiqueta} className="flex items-center gap-1.5">
          {i > 0 && <span className="text-[10px] text-slate-300">→</span>}
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
          <span className="text-[10px] text-slate-300">→</span>
          <span className="rounded-full border border-emerald-300 bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-800">
            Confirmado con 2 ángulos
          </span>
        </>
      )}
      {verificacion?.estado === "inconsistente" && (
        <>
          <span className="text-[10px] text-slate-300">→</span>
          <span className="rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
            Resultados inconsistentes
          </span>
        </>
      )}
    </nav>
  );
}