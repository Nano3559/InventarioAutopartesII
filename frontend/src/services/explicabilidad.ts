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

/** Motivos a favor: categoría visual y evidencia de código leída por OCR. */
function motivosCoincidencia(candidato: VisionCandidatoPublico): MotivoCandidato[] {
  const motivos: MotivoCandidato[] = [];

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
function motivosAviso(candidato: VisionCandidatoPublico): MotivoCandidato[] {
  const avisos: MotivoCandidato[] = [];

  if (!candidato.compatibilidad.verificada) {
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

/** Lista completa de "¿Por qué aparece este producto?". */
export function explicarCandidato(candidato: VisionCandidatoPublico): MotivoCandidato[] {
  return [...motivosCoincidencia(candidato), ...motivosVehiculo(candidato), ...motivosDisponibilidad(candidato), ...motivosAviso(candidato)];
}

function capitalizar(texto: string): string {
  const t = texto.trim();
  return t.charAt(0).toUpperCase() + t.slice(1);
}