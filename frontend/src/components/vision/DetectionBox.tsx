import { VisionBoundingBox } from "../../types/vision";

interface DetectionBoxProps {
  src: string;
  alt: string;
  boundingBox: VisionBoundingBox | null | undefined;
  categoria: string;
  confianza: number;
}

/** Acota un valor normalizado (0..1) al rango válido. */
const acotar = (valor: number) => Math.min(1, Math.max(0, Number.isFinite(valor) ? valor : 0));

/**
 * Vista previa de la foto con la caja de la pieza detectada encima.
 *
 * `boundingBox` viene NORMALIZADO (0..1) desde `ia-service`, no en píxeles: son
 * fracciones de ancho y alto de la imagen. Por eso el overlay usa porcentajes.
 *
 * Detalle de maquetado que importa para que la caja caiga donde debe: la imagen se
 * renderiza con `w-full h-auto` y SIN `object-contain`, dentro de un contenedor que
 * la envuelve exactamente. Con `object-contain` sobre un contenedor de otra
 * proporción, la imagen se letalía con bandas negras y el porcentaje del overlay se
 * calcularía sobre el contenedor, no sobre la foto: la caja quedaría desplazada.
 */
export default function DetectionBox({ src, alt, boundingBox, categoria, confianza }: DetectionBoxProps) {
  const confianzaPct = Math.round(confianza * 100);
  // Una caja solo se dibuja si tiene área real (ancho y alto positivos). Sumar
  // x+width no sirve: una caja en (0.5, 0.5) con tamaño 0 daría > 0 y se pintaría
  // un recuadro de un píxel sin sentido.
  const cajaValida =
    !!boundingBox && acotar(boundingBox.width) > 0 && acotar(boundingBox.height) > 0;

  return (
    <figure className="m-0" data-testid="vision-deteccion-box">
      <div className="relative inline-block max-w-full">
        <img src={src} alt={alt} className="block w-full h-auto max-h-72 rounded-xl border border-white/[0.06] object-left-top" />
        {cajaValida && (
          <div
            data-testid="vision-bounding-box"
            role="img"
            aria-label={`Pieza detectada: ${categoria} (${confianzaPct}% de confianza)`}
            className="absolute border-2 border-primary-400 rounded-md shadow-[0_0_0_9999px_rgba(0,0,0,0.35)] pointer-events-none"
            style={{
              left: `${acotar(boundingBox!.x) * 100}%`,
              top: `${acotar(boundingBox!.y) * 100}%`,
              width: `${acotar(boundingBox!.width) * 100}%`,
              height: `${acotar(boundingBox!.height) * 100}%`,
            }}
          >
            <span className="absolute -top-6 left-0 whitespace-nowrap text-[10px] font-semibold px-1.5 py-0.5 rounded bg-primary-500 text-white">
              {categoria} · {confianzaPct}%
            </span>
          </div>
        )}
      </div>
      <figcaption className="mt-1.5 text-[11px] text-gray-500">
        {cajaValida
          ? "La caja marca la zona que el modelo tomó como pieza."
          : "El modelo no indicó una zona concreta; la clasificación se hizo sobre la imagen completa."}
      </figcaption>
    </figure>
  );
}