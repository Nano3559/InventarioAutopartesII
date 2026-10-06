import { logger } from "../../shared/utils/logger";

/**
 * Evidencias de OCR para el pipeline híbrido de visión (YOLO + códigos).
 *
 * Principio de diseño: el OCR es **evidencia de identificación**, no de
 * compatibilidad. Que el código leído en la foto coincida con el `oemCode` de un
 * producto indica que probablemente es la misma pieza; NO demuestra que sea el
 * repuesto correcto para un vehículo concreto. Por eso nada en este módulo marca
 * `verificada` ni altera el campo `compatibilidad`: eso sigue siendo dominio de
 * `compatibility.ts`.
 *
 * Política de pesos: PROVISIONAL y documentada como tal. Los pesos definitivos por
 * clase exigen curvas P/R calculadas sobre un ground truth, y hoy no existe dataset
 * en el repositorio (ver docs/AUDITORIA_IMPLEMENTACION_IA_VISION.md), así que no
 * se pueden calibrar. Se orderan por autoridad del campo:
 *
 *   oemCode       (10) → número de parte del fabricante: máxima autoridad
 *   factoryCode   ( 8) → referencia interna del proveedor/distribuidor
 *   itemCode      ( 6) → SKU propio del catálogo
 *
 * Una coincidencia parcial (un código contiene al otro) vale menos y se reporta
 * como `parcial` para que la interfaz pueda mostrar el grado real de certeza.
 */

export interface EvidenciaCodigo {
  campo: "oemCode" | "factoryCode" | "itemCode";
  codigoProducto: string;
  codigoDetectado: string;
  tipo: "exacta" | "parcial";
  peso: number;
}

export interface ResultadoEvidencias {
  score: number;
  evidencias: EvidenciaCodigo[];
}

export interface ProductoEvidencia {
  oemCode: string | null;
  factoryCode: string | null;
  itemCode: string;
}

/** Longitud mínima para que un código (ya unido) se considere válido. */
const LONGITUD_MIN_CODIGO = 5;
/**
 * Longitud mínima para aceptar un token Aislado como código.
 * Mayor que la del código unido porque los segmentos sueltos de un código con
 * guion ("90915-YZZD2" → "YZZD2") no son códigos por sí mismos: son ruido.
 */
const LONGITUD_MIN_TOKEN = 6;
/** Longitud máxima de un código, para acotar el trabajo de matching. */
const LONGITUD_MAX_CODIGO = 32;
/** Longitud mínima para aceptar una coincidencia parcial (evita ruido tipo "12345"). */
const LONGITUD_MIN_PARCIAL = 6;
/** Tope de tokens considerados por request, para acotar el trabajo de matching. */
const MAX_CODIGOS = 24;
/** Tope de evidencias por producto, para que la UI no reciba listas inmanejables. */
const MAX_EVIDENCIAS = 6;

export const PESOS_CODIGO = {
  oemCode: 10,
  factoryCode: 8,
  itemCode: 6,
  parcial: 3,
} as const;

/**
 * Normaliza un código para comparar: sin separadores, en mayúsculas.
 * "90915-yzzd2", "90915 YZZD2" y "90915YZZD2" deben compararse iguales, porque el
 * OCR introduce y elimina guiones/espacios por igual.
 */
export function normalizarCodigo(valor: string): string {
  return valor.toUpperCase().replace(/[^A-Z0-9]/g, "");
}

/**
 * Extrae tokens candidatos a código de pieza del texto devuelto por Tesseract.
 *
 * Un código de autoparte mezcla letras y dígitos ("90915YZZD2", "1K0615301",
 * "LF15D", "047650P010"). Se aceptan tokens con ambos, y además se reensamblan
 * tríos separados por espacio ("1K0 615 301") porque así los imprime Tesseract
 * cuando el código está troceado en la etiqueta.
 */
export function extraerCodigos(textoOcr: string | null | undefined): string[] {
  if (!textoOcr) return [];

  const vistos = new Set<string>();
  const out: string[] = [];

  const agregar = (normalizado: string) => {
    if (normalizado.length < LONGITUD_MIN_CODIGO || normalizado.length > LONGITUD_MAX_CODIGO) return;
    if (vistos.has(normalizado)) return;
    vistos.add(normalizado);
    out.push(normalizado);
  };

  // 1) Códigos con separador interno (guion, punto o barra): "90915-YZZD2", "LF.15D".
  //    Van primero y son los más fiables, porque el separador forma parte del código.
  for (const match of textoOcr.match(/[A-Za-z0-9]+(?:[-./][A-Za-z0-9]+)+/g) ?? []) {
    const normalizado = normalizarCodigo(match);
    if (/\d/.test(normalizado) && /[A-Za-z]/.test(normalizado)) agregar(normalizado);
  }

  const tokens = textoOcr.split(/[^A-Za-z0-9]+/).filter(Boolean);

  // 2) Tokens individuales (letras + dígitos, longitud suficiente).
  for (const token of tokens) {
    if (token.length < LONGITUD_MIN_TOKEN || token.length > LONGITUD_MAX_CODIGO) continue;
    if (!/\d/.test(token)) continue;
    if (!/[A-Za-z]/.test(token)) continue;
    agregar(normalizarCodigo(token));
  }

  // 3) Reensamble de tríos separados por un espacio: "1K0 615 301" → "1K0615301".
  //    Solo se reensambla si CADA segmento parece parte de un código: un segmento
  //    alfanumérico corto o con dígitos. Una palabra suelta ("TOYOTA", "FILTRO",
  //    "ORIGINAL") queda fuera, porque sin este filtro "FILTRO 90915 YZZD2" produciría
  //    el código inexistente "FILTRO90915YZZD2" y contaminaría el ranking con
  //    coincidencias falsas.
  const segmentoDeCodigo = (t: string) => /\d/.test(t) || t.length <= 5;
  for (let i = 0; i + 2 < tokens.length; i++) {
    const segmentos = [tokens[i], tokens[i + 1], tokens[i + 2]];
    if (!segmentos.every(segmentoDeCodigo)) continue;
    const trio = segmentos.join("");
    if (trio.length > LONGITUD_MIN_CODIGO && trio.length <= LONGITUD_MAX_CODIGO && /\d/.test(trio) && /[A-Za-z]/.test(trio)) {
      agregar(normalizarCodigo(trio));
    }
  }

  return out.slice(0, MAX_CODIGOS);
}

/**
 * Tokens de texto legibles para mostrar en la interfaz (`deteccion.textoDetectado`).
 *
 * No es el texto OCR crudo: se descartan tokens de un solo carácter, ruido típico de
 * una captura y los términos genéricos que no distinguen una pieza de otra, para que
 * la UI muestre algo que el usuario pueda comparar con lo que realmente ve en su foto.
 */
const RUIDO_OCR = new Set([
  "img", "imagen", "image", "photo", "foto", "jpeg", "jpg", "png", "webp",
  "the", "and", "for", "con", "new", "tipo", "parte", "part", "code", "cod", "ref",
  "product", "producto", "original", "replacement", "calidad", "calidad",
]);
const MAX_TOKENS_TEXTO = 20;

export function extraerTokensSignificativos(textoOcr: string | null | undefined): string[] {
  if (!textoOcr) return [];
  const vistos = new Set<string>();
  const out: string[] = [];
  for (const raw of textoOcr.split(/[^A-Za-z0-9]+/)) {
    const token = raw.toUpperCase();
    if (token.length < 3) continue;
    if (RUIDO_OCR.has(token.toLowerCase())) continue;
    if (vistos.has(token)) continue;
    vistos.add(token);
    out.push(token);
    if (out.length >= MAX_TOKENS_TEXTO) break;
  }
  return out;
}

/** ¿`a` y `b` son el mismo código, o uno contiene al otro de forma suficiente? */
function relacion(a: string, b: string): "exacta" | "parcial" | null {
  if (a === b) return "exacta";
  const [corto, largo] = a.length <= b.length ? [a, b] : [b, a];
  if (corto.length >= LONGITUD_MIN_PARCIAL && largo.includes(corto)) return "parcial";
  return null;
}

/**
 * Evalúa un producto contra los códigos leídos.
 * El orden de campos (oemCode → factoryCode → itemCode) determina qué evidencia se
 * reporta primero cuando un mismo código coincide en varios campos del mismo producto.
 */
export function evaluarEvidenciasCodigo(producto: ProductoEvidencia, codigos: string[]): ResultadoEvidencias {
  const evidencias: EvidenciaCodigo[] = [];
  if (!codigos.length) return { score: 0, evidencias };

  let score = 0;
  const campos: Array<{ campo: keyof ProductoEvidencia; valor: string | null; peso: number }> = [
    { campo: "oemCode", valor: producto.oemCode, peso: PESOS_CODIGO.oemCode },
    { campo: "factoryCode", valor: producto.factoryCode, peso: PESOS_CODIGO.factoryCode },
    { campo: "itemCode", valor: producto.itemCode, peso: PESOS_CODIGO.itemCode },
  ];

  for (const { campo, valor, peso } of campos) {
    if (!valor) continue;
    const codigoProducto = normalizarCodigo(valor);
    for (const codigoDetectado of codigos) {
      const tipo = relacion(codigoProducto, codigoDetectado);
      if (!tipo) continue;
      const pesoFinal = tipo === "exacta" ? peso : PESOS_CODIGO.parcial;
      score += pesoFinal;
      evidencias.push({
        campo: campo as EvidenciaCodigo["campo"],
        codigoProducto: valor,
        codigoDetectado,
        tipo,
        peso: pesoFinal,
      });
      // Un campo no aporta más de una vez: seguir barajando códigos del mismo campo
      // solo sumaría ruido (p. ej. el mismo código con y sin guion).
      break;
    }
  }

  evidencias.sort((a, b) => b.peso - a.peso);
  return { score, evidencias: evidencias.slice(0, MAX_EVIDENCIAS) };
}

/** Resumen legible de las coincidencias para la interfaz y los logs. */
export function resumirEvidencias(evidencias: EvidenciaCodigo[]): string {
  if (!evidencias.length) return "Sin códigos detectados en la imagen.";
  return evidencias
    .map((e) => `${e.campo} ${e.codigoProducto} (${e.tipo})`)
    .join(" · ");
}

/** Compatibilidad mínima necesaria para ordenar. Evita acoplarse a `compatibility.ts`. */
export interface CompatibilidadOrdenable {
  verificada: boolean;
  score: number;
}

export interface CandidatoEvaluado<T, C extends CompatibilidadOrdenable = CompatibilidadOrdenable> {
  producto: T;
  compatibilidad: C;
  evidencia: ResultadoEvidencias;
}

/**
 * Calcula la evidencia OCR de cada candidato y devuelve el ranking final.
 *
 * Regla de orden, en este orden y sin excepciones:
 *   1. compatibilidad verificada (marca + modelo + año confirmados)
 *   2. evidencia de código leída en la foto
 *   3. puntaje de compatibilidad
 *
 * El punto 1 va primero a propósito: un `oemCode` exacto leído en la etiqueta sube
 * mucho en el ranking, pero NO puede desplazar a un producto verificado contra el
 * vehículo del usuario, porque el código identifica la pieza y no demuestra que sea
 * la correcta para ese auto. Prometer lo contrario sería inventar compatibilidad.
 */
export function evaluarYRanquear<T extends ProductoEvidencia, C extends CompatibilidadOrdenable>(
  evaluados: Array<{ producto: T; compatibilidad: C }>,
  codigos: string[]
): Array<CandidatoEvaluado<T, C>> {
  return evaluados
    .map((entry) => ({ ...entry, evidencia: evaluarEvidenciasCodigo(entry.producto, codigos) }))
    .sort((a, b) => {
      if (b.compatibilidad.verificada !== a.compatibilidad.verificada) {
        return b.compatibilidad.verificada ? 1 : -1;
      }
      if (b.evidencia.score !== a.evidencia.score) return b.evidencia.score - a.evidencia.score;
      return b.compatibilidad.score - a.compatibilidad.score;
    });
}

/**
 * Registra en el log la evidencia global del request (no por producto): qué códigos
 * se leyeron y cuántos productos quedaron con coincidencia. Sin volcar el texto OCR
 * completo, que puede contener datos de la etiqueta del cliente.
 */
export function logEvidenciasGlobales(codigos: string[], productosConEvidencia: number, totalProductos: number): void {
  if (!codigos.length) return;
  logger.info("[OCR-HIBRIDO] códigos detectados en la imagen.", {
    codigos,
    productosConEvidencia,
    totalProductos,
  });
}