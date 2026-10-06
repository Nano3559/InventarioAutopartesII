import { describe, it, expect } from "vitest";
import { calcularMetricas, evaluarCalidad, ReporteCalidad, UMBRALES } from "../imageQuality";

const ANCHO = 120;
const ALTO = 90;

/** Pixeles uniformes (color plano `v` en 0..255). */
function plano(v: number): Uint8ClampedArray {
  const datos = new Uint8ClampedArray(ANCHO * ALTO * 4);
  for (let i = 0; i < ANCHO * ALTO; i++) {
    datos[i * 4] = v;
    datos[i * 4 + 1] = v;
    datos[i * 4 + 2] = v;
    datos[i * 4 + 3] = 255;
  }
  return datos;
}

/** Gradiente horizontal suave: desenfoque sin perder contraste. */
function degradado(): Uint8ClampedArray {
  const datos = new Uint8ClampedArray(ANCHO * ALTO * 4);
  for (let y = 0; y < ALTO; y++) {
    for (let x = 0; x < ANCHO; x++) {
      const i = (y * ANCHO + x) * 4;
      const v = Math.round((x / (ANCHO - 1)) * 255);
      datos[i] = v;
      datos[i + 1] = v;
      datos[i + 2] = v;
      datos[i + 3] = 255;
    }
  }
  return datos;
}

/** Ruido determinista (PRNG lineal): textura de alta frecuencia = nítido. */
function textura(): Uint8ClampedArray {
  const datos = new Uint8ClampedArray(ANCHO * ALTO * 4);
  let semilla = 123456789;
  for (let i = 0; i < ANCHO * ALTO; i++) {
    semilla = (semilla * 1664525 + 1013904223) >>> 0;
    const v = semilla >>> 24;
    datos[i * 4] = v;
    datos[i * 4 + 1] = v;
    datos[i * 4 + 2] = v;
    datos[i * 4 + 3] = 255;
  }
  return datos;
}

/**
 * Evalúa el contenido del píxel en aislamiento: se inyecta una resolución
 * suficiente (1024×768, por encima del umbral de 640) y un peso de archivo
 * normal para que el veredicto dependa SOLO de brillo/contraste/nitidez.
 * La resolución se prueba aparte.
 */
function evaluarContenido(datos: Uint8ClampedArray): ReporteCalidad {
  const metricas = calcularMetricas(datos, ANCHO, ALTO);
  return evaluarCalidad({
    ...metricas,
    resolucion: { ancho: 1024, alto: 768, megapixeles: 0.79 },
    bytesArchivo: 300 * 1024,
  });
}

describe("imageQuality — indicadores deterministas sin IA", () => {
  it("imagen oscura → estado mala y recomienda mejorar la luz", () => {
    const reporte = evaluarContenido(plano(15));

    expect(reporte.brillo).toBeLessThan(UMBRALES.brilloMinimoMala);
    expect(reporte.estado).toBe("mala");
    expect(reporte.problemas.join(" ")).toMatch(/oscura/i);
    expect(reporte.recomendaciones.join(" ")).toMatch(/luz/i);
  });

  it("imagen demasiado clara (quemada) → estado mala", () => {
    const reporte = evaluarContenido(plano(253));

    expect(reporte.estado).toBe("mala");
    expect(reporte.problemas.join(" ")).toMatch(/demasiado clara|sobreexpuesta/i);
  });

  it("imagen borrosa sin contraste → estado mala", () => {
    const reporte = evaluarContenido(plano(128));

    expect(reporte.nitidez).toBeLessThan(UMBRALES.nitidezMala);
    expect(reporte.contraste).toBeLessThan(UMBRALES.contrasteMinimo);
    expect(reporte.estado).toBe("mala");
    expect(reporte.problemas.join(" ")).toMatch(/borrosa/i);
    expect(reporte.recomendaciones.join(" ")).toMatch(/enfocada|quieto/i);
  });

  it("degradado suave: sin ruido pero con contraste → regular, nunca mala", () => {
    const reporte = evaluarContenido(degradado());

    expect(reporte.nitidez).toBeLessThan(UMBRALES.nitidezMala);
    expect(reporte.estado).toBe("regular");
  });

  it("imagen correcta con textura, buen brillo y contraste → estado buena sin recomendaciones", () => {
    const reporte = evaluarContenido(textura());

    expect(reporte.nitidez).toBeGreaterThan(UMBRALES.nitidezRegular);
    expect(reporte.contraste).toBeGreaterThan(UMBRALES.contrasteMinimo);
    expect(reporte.estado).toBe("buena");
    expect(reporte.recomendaciones).toEqual([]);
    expect(reporte.problemas).toEqual([]);
  });

  it("resolución insuficiente se evalúa aparte del contenido", () => {
    const base = evaluarContenido(textura());
    const reporte = evaluarCalidad({ ...base, resolucion: { ancho: 200, alto: 150, megapixeles: 0.03 } });

    expect(reporte.estado).toBe("mala");
    expect(reporte.problemas.join(" ")).toMatch(/Resolución baja/);
  });

  it("archivo sospechosamente pequeño avisa pero no bloquea", () => {
    const base = evaluarContenido(textura());
    const reporte = evaluarCalidad({ ...base, bytesArchivo: 4 * 1024 });

    expect(reporte.estado).toBe("regular");
    expect(reporte.problemas.join(" ")).toMatch(/muy pequeño/i);
  });

  it("es determinista: dos medidas idénticas dan el mismo veredicto", () => {
    const datos = textura();
    expect(evaluarContenido(datos)).toEqual(evaluarContenido(datos));
  });
});