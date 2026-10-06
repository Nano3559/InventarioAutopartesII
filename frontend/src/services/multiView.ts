/**
 * Confirmación por segunda foto (multi-vista) del MODO ESCANEO INTELIGENTE.
 *
 * Principio rector: solo se combinan detecciones REALES producidas por YOLO. No
 * se promedian confianzas ni se calcula ninguna probabilidad: dos fotos que
 * coinciden en la categoría dicen "visto dos veces", no "88 % de probabilidad".
 *
 * Por eso el tipo de resultado es una etiqueta de texto y no un número. El
 * campo `confianzaYolo` sigue siendo exactamente la confianza que devolvió el
 * modelo para la vista elegida.
 */

import type { VisionDeteccionRespuesta } from "../types/vision";

export type EstadoConfirmacion = "confirmado" | "inconsistente" | "no_confirmado";

export type EtiquetaConfirmacion = "Confirmado por 2 imágenes" | "Identificación no confirmada" | "Resultados inconsistentes";

export interface VerificacionMultiVista {
  estado: EstadoConfirmacion;
  etiqueta: EtiquetaConfirmacion;
  /** Explicación en lenguaje llano de cómo se llegó al veredicto. */
  detalle: string;
  /** Categoría mostrada por defecto, o null si ninguna de las vistas clasificó. */
  categoriaElegida: string | null;
  /** Índice dentro de `vistas` de la vista elegida. */
  indiceVistaElegida: number;
  /** Confianza YOLO de la vista elegida. Nunca promediada. */
  confianzaYolo: number;
  /** 1 vista si el usuario no tomó la segunda foto, 2 si la tomó. */
  vistas: VisionDeteccionRespuesta[];
  /** La categoría de la vista descartada, para poder mostrar ambas posibilidades. */
  categoriaAlternativa: string | null;
  indiceVistaAlternativa: number | null;
}

/**
 * Zona de confianza media: ahí tiene sentido pedir una segunda foto. Por encima
 * de `CONFIANZA_ALTA` no se molesta al usuario; por debajo de `CONFIANZA_MINIMA`
 * el backend ya responde 422 y nunca llega a la UI.
 *
 * El 0.80 es una decisión de producto, no una propiedad entrenada del modelo.
 */
export const CONFIANZA_MINIMA = 0.55;
export const CONFIANZA_ALTA = 0.8;

/** ¿Corresponde pedir la segunda foto para esta detección? */
export function debeOfrecerSegundaFoto(deteccion: VisionDeteccionRespuesta): boolean {
  return deteccion.confianza >= CONFIANZA_MINIMA && deteccion.confianza < CONFIANZA_ALTA;
}

/** Categoría comparable: la del catálogo si existe, si no la etiqueta cruda de YOLO. */
export function categoriaDe(deteccion: VisionDeteccionRespuesta): string | null {
  const cruda = deteccion.categoriaMapeada ?? deteccion.categoria;
  const limpia = normalizar(cruda ?? "");
  return limpia.length ? limpia : null;
}

function normalizar(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "");
}

function etiquetaLegible(deteccion: VisionDeteccionRespuesta): string {
  return deteccion.categoriaMapeada ?? deteccion.categoria ?? "sin categoría";
}

/**
 * Aplica la regla de combinación sobre las detecciones reales.
 *
 *   1 vista                      → Identificación no confirmada
 *   2 vistas, misma categoría    → Confirmado por 2 imágenes
 *   2 vistas, categorías         → Resultados inconsistentes
 *   2 vistas, una sin clasificar → Identificación no confirmada (se conserva la otra)
 */
export function combinarDetecciones(vistas: VisionDeteccionRespuesta[]): VerificacionMultiVista {
  const limpias = vistas.filter(Boolean).slice(0, 2);

  if (limpias.length === 0) {
    return {
      estado: "no_confirmado",
      etiqueta: "Identificación no confirmada",
      detalle: "No hay detecciones para comparar.",
      categoriaElegida: null,
      indiceVistaElegida: -1,
      confianzaYolo: 0,
      vistas: [],
      categoriaAlternativa: null,
      indiceVistaAlternativa: null,
    };
  }

  if (limpias.length === 1) {
    const unica = limpias[0];
    return {
      estado: "no_confirmado",
      etiqueta: "Identificación no confirmada",
      detalle: `Resultado de una sola imagen (${etiquetaLegible(unica)}). Tomá otra foto para confirmarlo.`,
      categoriaElegida: etiquetaLegible(unica),
      indiceVistaElegida: 0,
      confianzaYolo: unica.confianza,
      vistas: limpias,
      categoriaAlternativa: null,
      indiceVistaAlternativa: null,
    };
  }

  const [a, b] = limpias;
  const ca = categoriaDe(a);
  const cb = categoriaDe(b);

  // Una de las dos no clasificó: se conserva la otra, pero sin confirmar.
  if (!ca || !cb) {
    const clasificada = ca ? a : b;
    const indice = ca ? 0 : 1;
    const sinClasificar = ca ? "la segunda" : "la primera";
    return {
      estado: "no_confirmado",
      etiqueta: "Identificación no confirmada",
      detalle: `La detección de ${sinClasificar} no pudo clasificar la pieza, así que se conserva ${etiquetaLegible(clasificada)} de la otra foto sin confirmar.`,
      categoriaElegida: etiquetaLegible(clasificada),
      indiceVistaElegida: indice,
      confianzaYolo: clasificada.confianza,
      vistas: limpias,
      categoriaAlternativa: null,
      indiceVistaAlternativa: null,
    };
  }

  if (ca === cb) {
    return {
      estado: "confirmado",
      etiqueta: "Confirmado por 2 imágenes",
      detalle: `Las dos imágenes se clasificaron como ${etiquetaLegible(a)}. Coincidencia entre vistas reales, no probabilidad calculada.`,
      categoriaElegida: etiquetaLegible(a),
      indiceVistaElegida: a.confianza >= b.confianza ? 0 : 1,
      confianzaYolo: a.confianza >= b.confianza ? a.confianza : b.confianza,
      vistas: limpias,
      categoriaAlternativa: null,
      indiceVistaAlternativa: null,
    };
  }

  // Categorías distintas: se muestran ambas posibilidades sin elegir una.
  const elegido = a.confianza >= b.confianza ? 0 : 1;
  return {
    estado: "inconsistente",
    etiqueta: "Resultados inconsistentes",
    detalle: `La primera foto sugiere ${etiquetaLegible(a)} y la segunda ${etiquetaLegible(b)}. No se declara confirmación: revisá las dos o tomá otra.`,
    categoriaElegida: etiquetaLegible(elegido === 0 ? a : b),
    indiceVistaElegida: elegido,
    confianzaYolo: elegido === 0 ? a.confianza : b.confianza,
    vistas: limpias,
    categoriaAlternativa: etiquetaLegible(elegido === 0 ? b : a),
    indiceVistaAlternativa: elegido === 0 ? 1 : 0,
  };
}