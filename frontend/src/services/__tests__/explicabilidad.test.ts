import { describe, it, expect } from "vitest";
import { explicarCandidato } from "../explicabilidad";
import type { VisionCandidatoPublico } from "../../types/vision";

function candidato(overrides: Partial<VisionCandidatoPublico> = {}): VisionCandidatoPublico {
  return {
    id: 1,
    itemCode: "FRN-001",
    name: "Freno de disco delantero",
    brand: "Brembo",
    model: "206",
    year: "2018",
    image: null,
    categoria: "brake_rotor",
    price1: 450,
    compatibilidad: { verificada: false, score: 0, coincidencias: [], nota: "" },
    disponibilidad: { nivel: "NO_DISPONIBLE", etiqueta: "Sin stock" },
    disponibilidadPorSucursal: [],
    ...overrides,
  };
}

describe("explicabilidad — evidencia real, sin campos sin respaldo", () => {
  it("muestra la evidencia de código exacta con el campo concreto", () => {
    const r = explicarCandidato(
      candidato({
        scoreEvidencia: 10,
        evidencias: [
          { campo: "oemCode", codigoProducto: "90915-YZZD2", codigoDetectado: "90915YZZD2", tipo: "exacta", peso: 10 },
        ],
      })
    );

    const textos = r.map((m) => m.texto);
    expect(textos).toContain("Categoría visual coincide");
    expect(textos).toContain("Código OEM exacto: 90915YZZD2");
    expect(r.find((m) => m.texto === "Código OEM exacto: 90915YZZD2")!.tipo).toBe("ok");
    expect(r.find((m) => m.texto === "Categoría visual coincide")!.tipo).toBe("ok");
  });

  it("NO dice 'Compatibilidad verificada' cuando el backend no la verificó", () => {
    const r = explicarCandidato(candidato({ scoreEvidencia: 6 }));

    const textos = r.map((m) => m.texto);
    expect(textos.some((t) => t.startsWith("Compatibilidad verificada"))).toBe(false);
    expect(textos).toContain("Compatibilidad no verificada: no se comprobó contra tu vehículo");
  });

  it("lista las coincidencias de vehículo que confirmó el backend", () => {
    const r = explicarCandidato(
      candidato({
        compatibilidad: { verificada: true, score: 3, coincidencias: ["marca", "modelo"], nota: "" },
        scoreEvidencia: 0,
        evidencias: [],
      })
    );

    const textos = r.map((m) => m.texto);
    expect(textos).toContain("Marca");
    expect(textos).toContain("Modelo");
    expect(textos.some((t) => t.startsWith("Compatibilidad verificada"))).toBe(false);
  });

  it("sin evidencia de código avisa que solo coincide por categoría", () => {
    const r = explicarCandidato(candidato({ evidencias: [], scoreEvidencia: 0 }));

    expect(r.map((m) => m.texto)).toContain("Solo coincide por categoría: no se leyó ningún código en la foto");
  });

  it("no afirma disponibilidad cuando el inventario dice que no hay stock", () => {
    const r = explicarCandidato(candidato({ evidencias: [], scoreEvidencia: 0 }));

    expect(r.some((m) => m.texto === "Disponible" || m.texto.startsWith("Disponible:"))).toBe(false);
    expect(r.map((m) => m.texto)).toContain("Sin stock disponible en este momento");
  });

  it("muestra 'Disponible' solo cuando el backend lo indicó", () => {
    const r = explicarCandidato(
      candidato({ disponibilidad: { nivel: "DISPONIBLE", etiqueta: "Disponible" }, scoreEvidencia: 6, evidencias: [
        { campo: "itemCode", codigoProducto: "FRN-001", codigoDetectado: "FRN001", tipo: "exacta", peso: 6 },
      ] })
    );

    expect(r.map((m) => m.texto)).toContain("Disponible");
  });

  it("no inventa ninguna línea sin fuente real", () => {
    const r = explicarCandidato(candidato());
    const permitidas = [
      "Categoría visual coincide",
      "Código OEM exacto: ",
      "Código OEM parcial: ",
      "Código de fábrica exacto: ",
      "Código de fábrica parcial: ",
      "Código de pieza exacto: ",
      "Código de pieza parcial: ",
      "Compatibilidad no verificada: no se comprobó contra tu vehículo",
      "Solo coincide por categoría: no se leyó ningún código en la foto",
      "Sin stock disponible en este momento",
      "Disponible",
    ];

    for (const motivo of r) {
      const esDeVehiculo = ["Marca", "Modelo", "Año"].some((p) => motivo.texto === p);
      const esPermitido = permitidas.some((p) => motivo.texto.startsWith(p));
      expect(esDeVehiculo || esPermitido).toBe(true);
    }
  });
});