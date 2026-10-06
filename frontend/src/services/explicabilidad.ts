/**
 * Explicabilidad: por qué el motor de catálogo propone cada producto.
 *
 * Regla dura: solo se muestra una línea si hay evidencia REAL detrás. Nada de
 * "marca compatible" si el producto no tiene marca cargada, ni "disponible" si el
 * inventario dice que no. Una línea sin respaldo es peor que no tener línea.
 *
 * La función es pura: recibe el candidato serializado por el backend y devuelve
 * motivos verificables. Es la misma información que ya viaja en
 * `candidato.evidencias` y `candidato.compatibilidad.coincidencias`, nada más.
 */

import type { VisionCandidatoPublico } from "../types/vision";

export interface MotivoCandidato {
  /** `ok` = evidencia a favor, `aviso` = límite o ausencia de verificación. */
  tipo: "ok" | "aviso";
  texto: string;
}

const ETIQUETA_CAMPO: Record<string, string> = {
  oemCode: "Código OEM",
  factoryCode: "Código de fábrica",
  itemCode: "Código de pieza",
};

/** Motivos a favor: tipo de pieza, categoría visual y evidencia de código leída por OCR. */
function motivosCoincidencia(candidato: VisionCandidatoPublico): MotivoCandidato[] {
  const motivos: MotivoCandidato[] = [];

  if (candidato.claseCoincide) {
    motivos.push({ tipo: "ok", texto: "Tipo de pieza coincide" });
  }
  if (candidato.categoria) {
    motivos.push({ tipo: "ok", texto: "Categoría visual coincide" });
  }

  for (const evidencia of candidato.evidencias ?? []) {
    const campo = ETIQUETA_CAMPO[evidencia.campo] ?? evidencia.campo;
    const tipo = evidencia.tipo === "exacta" ? "exacto" : "parcial";
    motivos.push({ tipo: "ok", texto: `${campo} ${tipo}: ${evidencia.codigoDetectado}` });
  }

  return motivos;
}

/**
 * Motivos del vehículo: solo los campos que el backend confirmó como
 * coincidencia. `compatibilidad.coincidencias` viene del proveedor real
 * (compatibility.ts), no de una suposición del frontend.
 */
function motivosVehiculo(candidato: VisionCandidatoPublico): MotivoCandidato[] {
  return (candidato.compatibilidad.coincidencias ?? []).map((campo) => ({ tipo: "ok" as const, texto: capitalizar(campo) }));
}

function motivosDisponibilidad(candidato: VisionCandidatoPublico): MotivoCandidato[] {
  const nivel = candidato.disponibilidad?.nivel;
  if (!nivel || nivel === "NO_DISPONIBLE") return [];
  const etiqueta = candidato.disponibilidad.etiqueta?.trim();
  return [{ tipo: "ok", texto: etiqueta && etiqueta !== "Disponible" ? `Disponible: ${etiqueta}` : "Disponible" }];
}

/** Avisos: límites honestos del resultado. */
function motivosAviso(candidato: VisionCandidatoPublico, hayVehiculo: boolean): MotivoCandidato[] {
  const avisos: MotivoCandidato[] = [];

  // Con vehículo: aviso breve por tarjeta ("⚠ No verificada"). Sin vehículo el
  // aviso NO se repite en cada producto: la UI lo globaliza con la llamada a
  // acción "Agrega tu vehículo para verificar compatibilidad" (ver
  // VisionResultsPanel). Repetirlo en N cards sería ruido, no información.
  if (!candidato.compatibilidad.verificada && hayVehiculo) {
    avisos.push({ tipo: "aviso", texto: "Compatibilidad no verificada: no se comprobó contra tu vehículo" });
  }
  if (!candidato.evidencias?.length) {
    avisos.push({ tipo: "aviso", texto: "Solo coincide por categoría: no se leyó ningún código en la foto" });
  }
  if (candidato.disponibilidad?.nivel === "NO_DISPONIBLE") {
    avisos.push({ tipo: "aviso", texto: "Sin stock disponible en este momento" });
  }

  return avisos;
}

export interface OpcionesExplicacion {
  /** false cuando la búsqueda no incluyó vehículo: la compatibilidad no se evaluó. */
  hayVehiculo?: boolean;
}

/** Lista completa de "¿Por qué aparece este producto?". */
export function explicarCandidato(
  candidato: VisionCandidatoPublico,
  opciones?: OpcionesExplicacion
): MotivoCandidato[] {
  const hayVehiculo = opciones?.hayVehiculo ?? true;
  return [
    ...motivosCoincidencia(candidato),
    ...motivosVehiculo(candidato),
    ...motivosDisponibilidad(candidato),
    ...motivosAviso(candidato, hayVehiculo),
  ];
}

function capitalizar(texto: string): string {
  const t = texto.trim();
  return t.charAt(0).toUpperCase() + t.slice(1);
}