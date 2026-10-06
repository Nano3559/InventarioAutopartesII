import { normalizarTexto } from "./normalize";

/**
 * Catálogo de las clases REALES que el modelo YOLO de producción puede predecir.
 *
 * Fuente ÚNICA (no se inventan ni se agregan clases):
 *   ia-service/app/services/inference.py
 *     - CLASSES_ESPERADAS       → ids canónicos, en el orden 0..7 del checkpoint
 *     - CLASE_YOLO_A_CATEGORIA  → etiqueta en español que el servicio de visión
 *                                 emite en `deteccion.categoria`
 *
 * El backend recibe la etiqueta ya traducida ("alternador", "pastilla de freno",
 * "faro", …), así que la resolución se hace contra esa etiqueta; el id en inglés se
 * conserva como respaldo y como documentación del contrato.
 *
 * Derivación de `terminos` — SOLO a partir de la propia clase:
 *   1. la etiqueta ES literal,
 *   2. su variante plural (única variante morfológica permitida),
 *   3. la palabra principal de la etiqueta, para tolerar orden distinto
 *      ("juego de pastillas de freno") o ausencia del complemento ("pastillas
 *      delanteras"),
 *   4. el id en inglés del modelo.
 * No se incorporan sinónimos comerciales ("generator", "pinza", "head lamp"): el
 * modelo no los predice y agregarlos introduciría coincidencias que ningún
 * entrenamiento respalda. Esa es una limitación conocida y documentada, no un
 * hueco a rellenar con intuición.
 */
export interface ClaseVisual {
  /** Id canónico del modelo (orden del checkpoint). */
  id: string;
  /** Etiqueta en español que emite `ia-service` en `deteccion.categoria`. */
  etiqueta: string;
  /** Términos derivados de la clase, en minúsculas y sin acentos. */
  terminos: string[];
}

export const CLASES_VISUALES: readonly ClaseVisual[] = [
  {
    id: "brake_pad",
    etiqueta: "pastilla de freno",
    terminos: ["pastilla de freno", "pastillas de freno", "pastilla", "pastillas", "brake pad", "brake_pad"],
  },
  {
    id: "brake_rotor",
    etiqueta: "disco de freno",
    terminos: ["disco de freno", "discos de freno", "disco", "discos", "brake rotor", "brake_rotor"],
  },
  {
    id: "brake_caliper",
    etiqueta: "caliper",
    terminos: ["caliper", "calipers", "brake caliper", "brake_caliper"],
  },
  {
    id: "alternator",
    etiqueta: "alternador",
    terminos: ["alternador", "alternadores", "alternator"],
  },
  {
    id: "oil_filter",
    etiqueta: "filtro de aceite",
    terminos: ["filtro de aceite", "filtros de aceite", "oil filter", "oil_filter"],
  },
  {
    id: "air_filter",
    etiqueta: "filtro de aire",
    terminos: ["filtro de aire", "filtros de aire", "air filter", "air_filter"],
  },
  {
    id: "radiator",
    etiqueta: "radiador",
    terminos: ["radiador", "radiadores", "radiator"],
  },
  {
    id: "headlight",
    etiqueta: "faro",
    terminos: ["faro", "faros", "headlight"],
  },
];

/**
 * ¿`norm` contiene `termino` rodeado de límites de palabra?
 *
 * Se tolera puntuación como límite ("filtro de aceite, 15W40" sí contiene
 * "filtro de aceite") pero NO se acepta un cruce dentro de una palabra
 * ("faroled" no contiene "faro"). `normalizarTexto` ya dejó todo en minúsculas
 * y sin acentos.
 */
function contieneTermino(norm: string, termino: string): boolean {
  let desde = 0;
  for (;;) {
    const i = norm.indexOf(termino, desde);
    if (i < 0) return false;
    const antes = i === 0 ? " " : norm[i - 1];
    const despues = i + termino.length >= norm.length ? " " : norm[i + termino.length];
    if (!/[a-z0-9]/.test(antes) && !/[a-z0-9]/.test(despues)) return true;
    desde = i + 1;
  }
}

/**
 * Resuelve la clase visual detectada por YOLO a una de las clases reales del modelo.
 *
 * 1. Igualdad exacta con la etiqueta ES o con el id YOLO (el caso normal: el
 *    servicio de visión ya emite la etiqueta canónica).
 * 2. Contención de términos, eligiendo el término más largo para que
 *    "filtro de aceite" no sea capturado por una clase con término más corto.
 *
 * Devuelve `null` si la detección no corresponde a ninguna clase real: no se
 * inventa una clase para no perder la trazabilidad.
 */
export function resolverClaseVisual(deteccion: string | null | undefined): ClaseVisual | null {
  if (!deteccion) return null;
  const norm = normalizarTexto(deteccion);
  if (!norm) return null;

  for (const clase of CLASES_VISUALES) {
    if (normalizarTexto(clase.etiqueta) === norm || normalizarTexto(clase.id) === norm) return clase;
  }

  let mejor: { clase: ClaseVisual; largo: number } | null = null;
  for (const clase of CLASES_VISUALES) {
    for (const termino of clase.terminos) {
      if (!contieneTermino(norm, termino)) continue;
      if (!mejor || termino.length > mejor.largo) mejor = { clase, largo: termino.length };
    }
  }
  return mejor?.clase ?? null;
}

/**
 * ¿El nombre del producto corresponde a la pieza que el modelo detectó?
 *
 * Es la prioridad 5 del Ranking V2. Solo puntúa cuando la clase existe; si no hay
 * detección resoluble, devuelve `false` y el candidato queda en la prioridad 7
 * (coincidencia por categoría), que es exactamente lo que debe ocurrir.
 */
export function coincideClaseVisual(
  nombreProducto: string | null | undefined,
  clase: ClaseVisual | null | undefined
): boolean {
  if (!clase || !nombreProducto) return false;
  const norm = normalizarTexto(nombreProducto);
  if (!norm) return false;
  return clase.terminos.some((termino) => contieneTermino(norm, termino));
}
