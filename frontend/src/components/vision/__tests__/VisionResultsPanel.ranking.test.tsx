import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import VisionResultsPanel, { VisionVehiculoForm, VisionEntregaSeleccion } from "../VisionResultsPanel";
import { VisionAnalysis, VisionCandidatoPublico } from "../../../types/vision";

const vehiculo: VisionVehiculoForm = { marca: "Toyota", modelo: "Corolla", anio: "2018" };
const entrega: VisionEntregaSeleccion = { modalidad: "recoger", sucursalId: null };

interface Input extends Partial<VisionCandidatoPublico> {
  itemCode: string;
  name: string;
  price1: number;
}

function cand({ itemCode, name, price1, ...rest }: Input): VisionCandidatoPublico {
  return {
    id: Number(itemCode.replace(/\D/g, "")),
    itemCode,
    name,
    brand: "Bosch",
    model: "Corolla",
    year: "2018",
    image: null,
    categoria: "elect",
    price1,
    nivelCoincidencia: "fuerte",
    claseCoincide: false,
    compatibilidad: { verificada: false, score: 0, coincidencias: [], nota: "" },
    disponibilidad: { nivel: "DISPONIBLE", etiqueta: "Disponible" },
    disponibilidadPorSucursal: [],
    disponibilidadPorSucursalPublica: [],
    ...rest,
  };
}

const ranking: VisionCandidatoPublico[] = [
  // 1. OEM exacto y compatibilidad verificada: debe ganar siempre.
  cand({
    itemCode: "CMP-001",
    name: "Alternador 120A Corolla",
    price1: 950,
    scoreEvidencia: 10,
    nivelCoincidencia: "fuerte",
    evidencias: [{ campo: "oemCode", codigoProducto: "AZ-012", codigoDetectado: "AZ012", tipo: "exacta", peso: 10 }],
    compatibilidad: { verificada: true, score: 8, coincidencias: ["marca", "modelo"], nota: "" },
  }),
  // 2. Sin código pero el nombre coincide con la clase detectada (prioridad 5).
  cand({
    itemCode: "CMP-002",
    name: "Bomba de agua Corolla",
    price1: 320,
    nivelCoincidencia: "media",
    claseCoincide: true,
    scoreEvidencia: 0,
  }),
  // 3-5. Solo de la misma categoría: "Coincidencia por categoría".
  cand({ itemCode: "CMP-003", name: "Bobina de encendido", price1: 210, nivelCoincidencia: "categoria", scoreEvidencia: 0 }),
  cand({ itemCode: "CMP-004", name: "Sensor de oxígeno", price1: 185, nivelCoincidencia: "categoria", scoreEvidencia: 0 }),
  cand({ itemCode: "CMP-005", name: "Bujía iridium", price1: 65, nivelCoincidencia: "categoria", scoreEvidencia: 0 }),
];

function resultado(): VisionAnalysis {
  return {
    version: "1.0",
    consultadoEn: "2026-01-01T00:00:00.000Z",
    proveedor: "http",
    deteccion: {
      categoria: "alternador",
      confianza: 0.85,
      confianzaBaja: false,
      categoriaMapeada: "eléctrico",
      boundingBox: { x: 0.2, y: 0.1, width: 0.5, height: 0.6 },
    },
    vehiculo: { marca: "Toyota", modelo: "Corolla", anio: "2018" },
    categoriaCatalogo: { id: 3, nombre: "Eléctrico" },
    candidatos: ranking,
    compatibilidad: {
      consultada: true,
      fuente: "base_datos_interna",
      metodologia: "baseline-catalog",
      consultadoEn: "2026-01-01T00:00:00.000Z",
      vehiculo: { marca: "Toyota", modelo: "Corolla", anio: "2018" },
      verificadas: 1,
      noVerificadas: 4,
      nota: "",
    },
    entrega: { modalidades: ["recoger"], sucursales: [{ id: 1, nombre: "Tienda Norte", tipo: "TIENDA" }] },
    nota: "",
  };
}

function renderPanel(props: Partial<Parameters<typeof VisionResultsPanel>[0]> = {}) {
  return render(
    <MemoryRouter>
      <VisionResultsPanel
        nombreFoto="alternador.jpg"
        resultado={resultado()}
        loading={false}
        error={null}
        vehiculo={vehiculo}
        onVehiculoChange={vi.fn()}
        onBuscar={vi.fn()}
        onRepetirFoto={vi.fn()}
        onCerrar={vi.fn()}
        entrega={entrega}
        onCambiarEntrega={vi.fn()}
        onLlevarAVenta={vi.fn()}
        {...props}
      />
    </MemoryRouter>
  );
}

describe("Ranking V2 — identificación en el panel", () => {
  it("muestra la pieza detectada con categoría del catálogo y confianza real", () => {
    renderPanel();

    const hero = screen.getByTestId("vision-pieza");
    expect(hero.textContent).toContain("Alternador");
    expect(hero.textContent).toContain("Eléctrico");
    expect(screen.getByTestId("vision-confianza-modelo").textContent).toBe("85%");
  });

  it("el orden mostrado respeta el ranking: el verificado/OEM va primero", () => {
    renderPanel();

    const ids = screen.getAllByTestId(/candidato-CMP-/).map((e) => e.getAttribute("data-testid"));
    expect(ids).toEqual(["candidato-CMP-001", "candidato-CMP-002", "candidato-CMP-003"]);
    expect(screen.getByTestId("candidato-CMP-001").textContent).toContain("Alternador 120A Corolla");
  });
});

describe("Ranking V2 — solo 3 tarjetas por defecto", () => {
  it("muestra 3 candidatos y ofrece 'Ver otros 2 resultados'", () => {
    renderPanel();

    expect(screen.getByText("Alternador 120A Corolla")).toBeTruthy();
    expect(screen.getByText("Bomba de agua Corolla")).toBeTruthy();
    expect(screen.getByText("Bobina de encendido")).toBeTruthy();
    expect(screen.queryByText("Sensor de oxígeno")).toBeNull();

    expect(screen.getByTestId("vision-ver-mas").textContent).toContain("Ver otros 2 resultados");
  });

  it("revela el resto al ampliar y permite volver a contraer", () => {
    renderPanel();

    fireEvent.click(screen.getByTestId("vision-ver-mas"));
    expect(screen.getByText("Sensor de oxígeno")).toBeTruthy();
    expect(screen.getByText("Bujía iridium")).toBeTruthy();

    fireEvent.click(screen.getByText("Mostrar menos"));
    expect(screen.queryByText("Sensor de oxígeno")).toBeNull();
  });
});

describe("Ranking V2 — chips de coincidencia honestos", () => {
  it("el score solo aparece con evidencia de código, con su tooltip aclaratorio", () => {
    renderPanel();

    const score = screen.getByTestId("score-CMP-001");
    expect(score.textContent).toBe("Coincidencia por código");
    expect(score.getAttribute("title")).toContain("score 10");
    expect(score.getAttribute("title")).toMatch(/motor de búsqueda del catálogo/i);
    expect(score.getAttribute("title")).toMatch(/modelo de IA/i);

    expect(screen.queryByTestId("score-CMP-002")).toBeNull();
  });

  it("muestra 'Coincidencia por tipo de pieza' cuando el nombre coincide con la clase", () => {
    renderPanel();
    const chip = screen.getByTestId("nivel-CMP-002");
    expect(chip.textContent).toBe("Coincidencia por tipo de pieza");
  });

  it("NO anuncia un score 0: dice 'Coincidencia por categoría'", () => {
    renderPanel();
    const chip = screen.getByTestId("nivel-CMP-003");
    expect(chip.textContent).toBe("Coincidencia por categoría");
    expect(chip.textContent).not.toContain("0");
    expect(screen.queryByTestId("score-CMP-003")).toBeNull();
  });

  it("distingue compatibilidad verificada de no verificada cuando hay vehículo", () => {
    renderPanel();

    expect(screen.getAllByText("✓ Compatible").length).toBeGreaterThan(0);
    expect(screen.getAllByText("⚠ No verificada").length).toBeGreaterThan(0);
    expect(screen.queryByText("Vehículo no indicado")).toBeNull();
    expect(screen.getByText(/1 de 5 candidatos verifican compatibilidad con Toyota Corolla 2018/)).toBeTruthy();
  });
});

describe("Ranking V2 — sin vehículo el panel lo dice", () => {
  it("reemplaza el conteo por la llamada a la acción global y chips moderados", () => {
    const sinVehiculo: VisionAnalysis = {
      ...resultado(),
      vehiculo: { marca: null, modelo: null, anio: null },
      compatibilidad: { ...resultado().compatibilidad, vehiculo: null, verificadas: 0, noVerificadas: 5 },
      candidatos: ranking.map((c) => ({ ...c, compatibilidad: { ...c.compatibilidad, verificada: false } })),
    };

    renderPanel({ resultado: sinVehiculo });

    expect(screen.getByTestId("vision-resumen-compatibilidad").textContent).toContain("Agrega tu vehículo para verificar compatibilidad");
    expect(screen.getAllByText("Vehículo no indicado").length).toBeGreaterThan(0);
    expect(screen.queryByText("✓ Compatible")).toBeNull();
    expect(screen.queryByText("⚠ No verificada")).toBeNull();
  });
});

describe("Ranking V2 — footer sticky de acciones", () => {
  it("ofrece 'Tomar otra foto' y 'Cerrar' al pie del panel", () => {
    const onRepetirFoto = vi.fn();
    const onCerrar = vi.fn();
    renderPanel({ onRepetirFoto, onCerrar });

    fireEvent.click(screen.getByRole("button", { name: /Tomar otra foto/ }));
    expect(onRepetirFoto).toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Cerrar" }));
    expect(onCerrar).toHaveBeenCalled();
  });
});