import { useState } from "react";
import { VisionDisponibilidadSucursalPublica } from "../../types/vision";

/** Estados visuales de la recogida: 🟢 Disponible / 🟡 Pocas unidades / ⚪ No disponible. */
const GLYFOS: Record<VisionDisponibilidadSucursalPublica["nivel"], string> = {
  DISPONIBLE: "🟢",
  POCAS_UNIDADES: "🟡",
  NO_DISPONIBLE: "⚪",
};

const ETIQUETA_ESTADO: Record<VisionDisponibilidadSucursalPublica["nivel"], string> = {
  DISPONIBLE: "Disponible",
  POCAS_UNIDADES: "Pocas unidades",
  NO_DISPONIBLE: "No disponible",
};

const ETIQUETA_CLASES: Record<VisionDisponibilidadSucursalPublica["nivel"], string> = {
  DISPONIBLE: "text-green-400",
  POCAS_UNIDADES: "text-yellow-400",
  NO_DISPONIBLE: "text-gray-500",
};

const MAX_VISIBLES = 3;

interface DisponibilidadSucursalesProps {
  itemCode: string;
  sucursales: VisionDisponibilidadSucursalPublica[];
  /** La mejor coincidencia destaca un poco más su sección de disponibilidad. */
  esPrincipal?: boolean;
}

/**
 * Sección compacta de DISPONIBILIDAD por sucursal dentro de la card. Muestra
 * hasta 3 sucursales TIENDA y permite expandir al resto. La fuente es el DTO
 * público seguro (`disponibilidadPorSucursalPublica`), así que jamás puede
 * renderizar stock exacto, ubicación interna ni almacenes.
 */
export default function DisponibilidadSucursales({ itemCode, sucursales, esPrincipal = false }: DisponibilidadSucursalesProps) {
  const [verTodas, setVerTodas] = useState(false);
  const visibles = verTodas ? sucursales : sucursales.slice(0, MAX_VISIBLES);
  const hayMas = sucursales.length > MAX_VISIBLES;

  return (
    <section
      aria-label="Disponibilidad por sucursal"
      data-testid={`disp-seccion-${itemCode}`}
      className={`mt-2 rounded-lg border p-2.5 ${
        esPrincipal ? "border-green-500/20 bg-green-500/[0.04]" : "border-white/[0.06] bg-white/[0.02]"
      }`}
    >
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">Disponibilidad</p>
      {sucursales.length > 0 ? (
        <>
          <ul className="mt-1.5 space-y-1">
            {visibles.map((s) => (
              <li
                key={s.sucursalId}
                data-testid={`disp-sucursal-${itemCode}-${s.sucursalId}`}
                className="flex items-baseline gap-1.5 text-xs"
              >
                <span aria-hidden="true" className="text-[10px] leading-none">{GLYFOS[s.nivel]}</span>
                <span className="text-gray-400 truncate">{s.nombre}</span>
                <span className={`font-medium ${ETIQUETA_CLASES[s.nivel]}`}>{ETIQUETA_ESTADO[s.nivel]}</span>
              </li>
            ))}
          </ul>
          {hayMas && (
            <button
              type="button"
              onClick={() => setVerTodas((v) => !v)}
              data-testid={`disp-ver-todas-${itemCode}`}
              className="mt-1.5 text-[11px] font-semibold text-primary-300 hover:text-white"
            >
              {verTodas ? "Ocultar sucursales" : `Ver todas las sucursales (${sucursales.length})`}
            </button>
          )}
        </>
      ) : (
        <p className="mt-1 text-xs text-gray-500" data-testid={`disp-vacio-${itemCode}`}>
          No disponible para recogida actualmente.
        </p>
      )}
    </section>
  );
}