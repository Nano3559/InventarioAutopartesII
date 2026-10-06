import { describe, it, expect } from "vitest";
import { combinarDetecciones, debeOfrecerSegundaFoto, categoriaDe, CONFIANZA_ALTA } from "../multiView";
import type { VisionDeteccionRespuesta } from "../../types/vision";

function deteccion(categoria: string, confianza: number, categoriaMapeada: string | null = null): VisionDeteccionRespuesta {
  return {
    categoria,
    confianza,
    confianzaBaja: confianza < 0.55,
    categoriaMapeada,
    boundingBox: { x: 0.1, y: 0.1, width: 0.5, height: 0.5 },
  };
}

describe("multiView — combinación de dos detecciones REALES", () => {
  it("misma categoría en las dos fotos → Confirmado por 2 imágenes", () => {
    const r = combinarDetecciones([deteccion("oil_filter", 0.62), deteccion("oil_filter", 0.71)]);

    expect(r.estado).toBe("confirmado");
    expect(r.etiqueta).toBe("Confirmado por 2 imágenes");
    expect(r.categoriaElegida).toBe("oil_filter");
    expect(r.vistas).toHaveLength(2);
  });

  it("la comparación normaliza mayúsculas, tildes y separadores", () => {
    const r = combinarDetecciones([deteccion("Bomba de Agua", 0.6), deteccion("BOMBA-DE-AGUA", 0.7)]);

    expect(r.estado).toBe("confirmado");
    expect(categoriaDe(deteccion("Bomba de Agua", 0.5))).toBe(categoriaDe(deteccion("BOMBA DE AGUA", 0.5)));
  });

  it("prioriza la categoria del catálogo (categoriaMapeada) sobre la etiqueta cruda de YOLO", () => {
    const r = combinarDetecciones([
      deteccion("filter", 0.6, "Filtro de aceite"),
      deteccion("oil_filter", 0.7, "Filtro de aceite"),
    ]);

    expect(r.estado).toBe("confirmado");
    expect(categoriaDe(deteccion("filter", 0.6, "Filtro de aceite"))).toBe("filtrodeaceite");
  });

  it("categorías distintas → Resultados inconsistentes y muestra ambas posibilidades", () => {
    const r = combinarDetecciones([deteccion("oil_filter", 0.72), deteccion("air_filter", 0.66)]);

    expect(r.estado).toBe("inconsistente");
    expect(r.etiqueta).toBe("Resultados inconsistentes");
    expect(r.categoriaElegida).toBe("oil_filter");
    expect(r.categoriaAlternativa).toBe("air_filter");
    expect(r.indiceVistaAlternativa).toBe(1);
    expect(r.detalle).toMatch(/oil_filter/);
    expect(r.detalle).toMatch(/air_filter/);
  });

  it("una de las dos no clasifica → Identificación no confirmada y se conserva la otra", () => {
    const r = combinarDetecciones([deteccion("radiator", 0.64), deteccion("", 0)]);

    expect(r.estado).toBe("no_confirmado");
    expect(r.etiqueta).toBe("Identificación no confirmada");
    expect(r.categoriaElegida).toBe("radiator");
    expect(r.detalle).toMatch(/sin confirmar/);
  });

  it("una sola foto → Identificación no confirmada", () => {
    const r = combinarDetecciones([deteccion("brake_pad", 0.7)]);

    expect(r.estado).toBe("no_confirmado");
    expect(r.etiqueta).toBe("Identificación no confirmada");
    expect(r.detalle).toMatch(/otra foto/i);
  });

  it("NUNCA promedia confianzas: confianzaYolo es exactamente la de una vista", () => {
    const a = deteccion("oil_filter", 0.9);
    const b = deteccion("oil_filter", 0.6);
    const r = combinarDetecciones([a, b]);

    expect([a.confianza, b.confianza]).toContain(r.confianzaYolo);
    expect(r.confianzaYolo).not.toBeCloseTo((a.confianza + b.confianza) / 2, 5);
    expect(r.detalle).not.toMatch(/%/);
  });

  it("no emite ningún porcentaje cuando las categorías coinciden", () => {
    const r = combinarDetecciones([deteccion("oil_filter", 0.62), deteccion("oil_filter", 0.71)]);
    expect(r.etiqueta).not.toMatch(/%|probabilidad|confianza \d/i);
  });
});

describe("multiView — zona de oferta de la segunda foto", () => {
  it("confianza en zona media → se ofrece confirmar", () => {
    expect(debeOfrecerSegundaFoto(deteccion("oil_filter", 0.7))).toBe(true);
  });

  it("confianza alta → no se molesta al usuario", () => {
    expect(debeOfrecerSegundaFoto(deteccion("oil_filter", CONFIANZA_ALTA))).toBe(false);
    expect(debeOfrecerSegundaFoto(deteccion("oil_filter", 0.95))).toBe(false);
  });
});