/**
 * Calidad de imagen para el MODO ESCANEO INTELIGENTE.
 *
 * Objetivo: advertir ANTES de gastar una inferencia cuando la foto difícilmente
 * puede dar una buena clasificación. Es un aviso, nunca un bloqueo: el usuario
 * siempre decide si sigue.
 *
 * Indicadores deterministas y baratos, sin IA adicional:
 *   - brillo     → luminancia media (Rec. 709)
 *   - contraste  → desviación estándar de la luminancia
 *   - nitidez    → varianza del Laplaciano (métrica clásica de desenfoque)
 *   - resolución → dimensiones reales de la foto
 *   - tamaño     → peso del archivo
 *
 * Por qué la nitidez no engaña tanto: las métricas se calculan sobre una copia
 * reducida a `LADO_ANALISIS` px. Así los umbrales no dependen de la resolución de
 * origen y una foto que llega borrosa por haber sido reescalada se detecta como
 * borrosa, que es exactamente lo que verá el modelo.
 *
 * LIMITACIÓN HONESTA: los umbrales son heurísticos, NO están calibrados. No se
 * pueden calibrar con curvas sobre el dataset porque el dataset no existe (ver
 * docs/AUDITORIA_IMPLEMENTACION_IA_VISION.md). Además una pieza sobre fondo liso
 * genera poca varianza de Laplaciano aunque esté nítida: por eso una nitidez baja
 * solo|es motivo de "mala" cuando además el contraste es bajo.
 */

export type NivelCalidad = "buena" | "regular" | "mala";

export interface MetricasImagen {
  /** Luminancia media 0..1. */
  brillo: number;
  /** Desviación estándar de la luminancia 0..1. */
  contraste: number;
  /** Varianza del Laplaciano. Mayor = más nítida. */
  nitidez: number;
  resolucion: { ancho: number; alto: number; megapixeles: number };
  bytesArchivo: number;
}

export interface ReporteCalidad extends MetricasImagen {
  estado: NivelCalidad;
  /** Motivos concretos del veredicto, para poder explicarlo. */
  problemas: string[];
  /** Qué hacer al usuario, accionable y verificable a simple vista. */
  recomendaciones: string[];
}

/** Lado máximo del lienzo de análisis. Smaller = más rápido y umbrales estables. */
export const LADO_ANALISIS = 256;

/** Umbrales heurísticos. Ver la nota de limitación al final del archivo. */
export const UMBRALES = {
  brilloMinimoMala: 0.15,
  brilloMaximoMala: 0.93,
  brilloMinimoRegular: 0.28,
  brilloMaximoRegular: 0.82,
  contrasteMinimo: 0.05,
  nitidezMala: 0.0004,
  nitidezRegular: 0.003,
  ladoMinimoMala: 320,
  ladoMinimoRegular: 640,
  bytesMinimoSospechoso: 15 * 1024,
} as const;

/** Rec. 709: ponderación perceptual de los canales. */
function luminancia(r: number, g: number, b: number): number {
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
}

/**
 * Métricas puras a partir de los píxeles de un lienzo ya dibujado.
 *
 * Se separa de cualquier acceso al DOM para poder testearla con arrays sintéticos
 * (imagen oscura, borrosa, correcta) sin depender de la implementación de canvas
 * de jsdom.
 */
export function calcularMetricas(datos: Uint8ClampedArray, ancho: number, alto: number): MetricasImagen {
  if (ancho <= 0 || alto <= 0 || datos.length < ancho * alto * 4) {
    return { brillo: 0, contraste: 0, nitidez: 0, resolucion: { ancho, alto, megapixeles: 0 }, bytesArchivo: 0 };
  }

  const pixeles = new Float64Array(ancho * alto);
  let suma = 0;
  for (let i = 0; i < pixeles.length; i++) {
    const j = i * 4;
    const y = luminancia(datos[j], datos[j + 1], datos[j + 2]);
    pixeles[i] = y;
    suma += y;
  }
  const brillo = suma / pixeles.length;

  let sumaCuadrados = 0;
  for (let i = 0; i < pixeles.length; i++) {
    const d = pixeles[i] - brillo;
    sumaCuadrados += d * d;
  }
  const contraste = Math.sqrt(sumaCuadrados / pixeles.length);

  // Laplaciano 3x3 con borde ignorado (no hay vecinos fuera de la imagen).
  let sumaLap = 0;
  let sumaLap2 = 0;
  let n = 0;
  for (let y = 1; y < alto - 1; y++) {
    for (let x = 1; x < ancho - 1; x++) {
      const i = y * ancho + x;
      const lap =
        4 * pixeles[i] - pixeles[i - 1] - pixeles[i + 1] - pixeles[i - ancho] - pixeles[i + ancho];
      sumaLap += lap;
      sumaLap2 += lap * lap;
      n++;
    }
  }
  const nitidez = n > 0 ? Math.max(0, sumaLap2 / n - (sumaLap / n) ** 2) : 0;

  return {
    brillo,
    contraste,
    nitidez,
    resolucion: { ancho, alto, megapixeles: (ancho * alto) / 1_000_000 },
    bytesArchivo: 0,
  };
}

type Problema = { nivel: NivelCalidad; motivo: string; consejo: string };

/**
 * Veredicto a partir de métricas ya calculadas. Función pura y determinista:
 * es donde viven los umbrales y donde se prueban los casos de la defensa.
 */
export function evaluarCalidad(m: MetricasImagen): ReporteCalidad {
  const problemas: Problema[] = [];
  const { brillo, contraste, nitidez, resolucion, bytesArchivo } = m;
  const ladoMenor = Math.min(resolucion.ancho, resolucion.alto);

  if (brillo < UMBRALES.brilloMinimoMala) {
    problemas.push({ nivel: "mala", motivo: `La foto está muy oscura (brillo ${pct(brillo)}).`, consejo: "Buscá más luz o acercá la pieza a una fuente de luz." });
  } else if (brillo < UMBRALES.brilloMinimoRegular) {
    problemas.push({ nivel: "regular", motivo: `La foto está algo oscura (brillo ${pct(brillo)}).`, consejo: "Buscá más luz o acercá la pieza a una fuente de luz." });
  } else if (brillo > UMBRALES.brilloMaximoMala) {
    problemas.push({ nivel: "mala", motivo: `La foto está demasiado clara, se quemaron los detalles (brillo ${pct(brillo)}).`, consejo: "Evitá el flash directo y tapá parcialmente la luz." });
  } else if (brillo > UMBRALES.brilloMaximoRegular) {
    problemas.push({ nivel: "regular", motivo: `La foto está algo sobreexpuesta (brillo ${pct(brillo)}).`, consejo: "Evitá el flash directo y tapá parcialmente la luz." });
  }

  // Nitidez baja solo vuelve la foto "mala" si además es de bajo contraste:
  // una pieza nítida sobre fondo liso tiene poca varianza sin estar borrosa.
  if (nitidez < UMBRALES.nitidezMala) {
    problemas.push(
      contraste < UMBRALES.contrasteMinimo
        ? { nivel: "mala", motivo: "La foto está borrosa y con poco contraste.", consejo: "Sostené el teléfono quieto y revisá que la pieza esté enfocada." }
        : { nivel: "regular", motivo: "La foto se ve algo suave.", consejo: "Sostené el teléfono quieto y revisá que la pieza esté enfocada." }
    );
  } else if (nitidez < UMBRALES.nitidezRegular) {
    problemas.push({ nivel: "regular", motivo: "La nitidez es baja.", consejo: "Sostené el teléfono quieto y revisá que la pieza esté enfocada." });
  }

  if (contraste < UMBRALES.contrasteMinimo) {
    problemas.push({ nivel: "regular", motivo: "La foto tiene poco contraste.", consejo: "Usá un fondo más liso y con distinto color al de la pieza." });
  }

  if (ladoMenor > 0 && ladoMenor < UMBRALES.ladoMinimoMala) {
    problemas.push({ nivel: "mala", motivo: `Resolución baja (${resolucion.ancho}×${resolucion.alto}).`, consejo: "Acercá la pieza para que la foto tenga más detalle." });
  } else if (ladoMenor > 0 && ladoMenor < UMBRALES.ladoMinimoRegular) {
    problemas.push({ nivel: "regular", motivo: `Resolución justa (${resolucion.ancho}×${resolucion.alto}).`, consejo: "Acercá la pieza para que la foto tenga más detalle." });
  }

  if (bytesArchivo > 0 && bytesArchivo < UMBRALES.bytesMinimoSospechoso) {
    problemas.push({ nivel: "regular", motivo: "El archivo es muy pequeño, la foto puede tener muy poco detalle.", consejo: "Tomá la foto a mayor resolución." });
  }

  const estado: NivelCalidad = problemas.some((p) => p.nivel === "mala")
    ? "mala"
    : problemas.some((p) => p.nivel === "regular")
      ? "regular"
      : "buena";

  return { ...m, estado, problemas: problemas.map((p) => p.motivo), recomendaciones: [...new Set(problemas.map((p) => p.consejo))] };
}

const pct = (v: number) => `${Math.round(v * 100)}%`;

export interface LienzoLike {
  width: number;
  height: number;
  getContext(id: "2d"): { getImageData(x: number, y: number, w: number, h: number): { data: Uint8ClampedArray } } | null;
}

/**
 * Mide sobre un lienzo ya dibujado. Aislada del resto para poder testearla
 * inyectando un contexto falso.
 */
export function medirDesdeLienzo(lienzo: LienzoLike, anchoOriginal: number, altoOriginal: number, bytesArchivo: number): ReporteCalidad {
  const ctx = lienzo.getContext("2d");
  if (!ctx || lienzo.width <= 0 || lienzo.height <= 0) {
    return evaluarCalidad({ brillo: 0, contraste: 0, nitidez: 0, resolucion: { ancho: anchoOriginal, alto: altoOriginal, megapixeles: (anchoOriginal * altoOriginal) / 1_000_000 }, bytesArchivo });
  }
  const { data } = ctx.getImageData(0, 0, lienzo.width, lienzo.height);
  const metricas = calcularMetricas(data, lienzo.width, lienzo.height);
  return evaluarCalidad({
    ...metricas,
    // Se reporta la resolución REAL de la foto, no la del lienzo de análisis.
    resolucion: { ancho: anchoOriginal, alto: altoOriginal, megapixeles: (anchoOriginal * altoOriginal) / 1_000_000 },
    bytesArchivo,
  });
}

/** Límite de espera del decodificador. La calidad es opcional: jamás cuelga la búsqueda. */
const TIMEOUT_DECODE_MS = 2500;

/**
 * Punto de entrada en navegador: dibuja la foto reducida y la mide.
 *
 * Si el navegador no puede decodificar la imagen devuelve `null` y el flujo
 * continúa sin aviso: la calidad es un extra, nunca un requisito. Por eso se
 * comprueba el soporte de canvas ANTES de cargar el archivo y se pone techo de
 * tiempo al decodificador.
 */
export async function analizarCalidadImagen(file: File): Promise<ReporteCalidad | null> {
  if (typeof document === "undefined") return null;

  let lienzo: HTMLCanvasElement;
  try {
    lienzo = document.createElement("canvas");
    lienzo.width = LADO_ANALISIS;
    lienzo.height = LADO_ANALISIS;
    // jsdom y navegadores sin canvas devuelven null: sin soporte, sin medición.
    if (!lienzo.getContext("2d", { willReadFrequently: true })) return null;
  } catch {
    return null;
  }

  try {
    const resultado = await Promise.race([
      medir(file),
      new Promise<Decodificado | null>((resolve) => setTimeout(() => resolve(null), TIMEOUT_DECODE_MS)),
    ]);
    if (!resultado) return null;

    const { bitmap, ancho, alto } = resultado;
    lienzo.width = ancho;
    lienzo.height = alto;
    const ctx = lienzo.getContext("2d", { willReadFrequently: true });
    if (!ctx) return null;
    ctx.drawImage(bitmap as CanvasImageSource, 0, 0, ancho, alto);
    if ("close" in bitmap && typeof bitmap.close === "function") bitmap.close();

    return medirDesdeLienzo(lienzo, resultado.anchoOriginal, resultado.altoOriginal, file.size);
  } catch {
    return null;
  }
}

interface Decodificado {
  bitmap: ImageBitmap | HTMLImageElement;
  ancho: number;
  alto: number;
  anchoOriginal: number;
  altoOriginal: number;
}

async function medir(file: File): Promise<Decodificado | null> {
  const bitmap = await crearBitmap(file);
  if (!bitmap) return null;
  const escala = Math.min(1, LADO_ANALISIS / Math.max(bitmap.width, bitmap.height));
  const ancho = Math.max(1, Math.round(bitmap.width * escala));
  const alto = Math.max(1, Math.round(bitmap.height * escala));
  return { bitmap, ancho, alto, anchoOriginal: bitmap.width, altoOriginal: bitmap.height };
}

async function crearBitmap(file: File): Promise<ImageBitmap | HTMLImageElement | null> {
  if (typeof createImageBitmap === "function") {
    try {
      return await createImageBitmap(file);
    } catch {
      /* se intenta la vía <img> */
    }
  }
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(null);
    };
    img.src = url;
  });
}