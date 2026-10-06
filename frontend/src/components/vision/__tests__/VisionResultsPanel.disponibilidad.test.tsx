import { describe, it, expect, vi } from "vitest";
import { useState } from "react";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import VisionResultsPanel, { VisionVehiculoForm, VisionEntregaSeleccion } from "../VisionResultsPanel";
import {
  VisionAnalysis,
  VisionCandidatoPublico,
  VisionDisponibilidadSucursalPublica,
} from "../../../types/vision";
import { BorradorVentaVision } from "../../../services/saleDraft";

const vehiculo: VisionVehiculoForm = { marca: "Toyota", modelo: "Corolla", anio: "2018" };
const entrega: VisionEntregaSeleccion = { modalidad: "recoger", sucursalId: null };

interface Input extends Partial<VisionCandidatoPublico> {
  itemCode: string;
  name: string;
  sucursales?: VisionDisponibilidadSucursalPublica[];
}

function cand({ itemCode, name, sucursales = [], ...rest }: Input): VisionCandidatoPublico {
  return {
    id: Number(itemCode.replace(/\D/g, "")),
    itemCode,
    name,
    brand: "Bosch",
    model: "Corolla",
    year: "2018",
    image: null,
    categoria: "frenos",
    price1: 200,
    nivelCoincidencia: "categoria",
    claseCoincide: false,
    compatibilidad: { verificada: false, score: 0, coincidencias: [], nota: "" },
    disponibilidad: { nivel: "DISPONIBLE", etiqueta: "Disponible" },
    disponibilidadPorSucursal: [],
    disponibilidadPorSucursalPublica: sucursales,
    ...rest,
  };
}

const BRANCHES = [
  { id: 101, nombre: "Tienda 1", tipo: "TIENDA" },
  { id: 102, nombre: "Tienda 2", tipo: "TIENDA" },
  { id: 103, nombre: "Tienda 3", tipo: "TIENDA" },
  { id: 104, nombre: "Tienda 4", tipo: "TIENDA" },
];

function baseResultado(candidatos: VisionCandidatoPublico[], conVehiculo = true): VisionAnalysis {
  return {
    version: "1.0",
    consultadoEn: "2026-01-01T00:00:00.000Z",
    proveedor: "http",
    deteccion: {
      categoria: "freno",
      confianza: 0.92,
      confianzaBaja: false,
      categoriaMapeada: "frenos",
      boundingBox: { x: 0.2, y: 0.1, width: 0.5, height: 0.6 },
    },
    vehiculo: conVehiculo ? { marca: "Toyota", modelo: "Corolla", anio: "2018" } : { marca: null, modelo: null, anio: null },
    categoriaCatalogo: { id: 2, nombre: "Frenos" },
    candidatos,
    compatibilidad: {
      consultada: conVehiculo,
      fuente: "base_datos_interna",
      metodologia: "baseline-catalog",
      consultadoEn: "2026-01-01T00:00:00.000Z",
      vehiculo: conVehiculo ? { marca: "Toyota", modelo: "Corolla", anio: "2018" } : null,
      verificadas: 0,
      noVerificadas: candidatos.length,
      nota: "",
    },
    entrega: { modalidades: ["recoger", "delivery"], sucursales: BRANCHES },
    nota: "",
  };
}

function renderPanel(props: Partial<Parameters<typeof VisionResultsPanel>[0]> = {}) {
  return render(
    <MemoryRouter>
      <VisionResultsPanel
        nombreFoto="freno.jpg"
        resultado={null}
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

/** Harness ESTATAL: permite que cambiar la sucursal en el panel actualice `entrega`. */
function Harness({
  candidatos,
  conVehiculo = true,
  entregaInicial = entrega,
  onLlevarAVenta = vi.fn(),
}: {
  candidatos: VisionCandidatoPublico[];
  conVehiculo?: boolean;
  entregaInicial?: VisionEntregaSeleccion;
  onLlevarAVenta?: (borrador: BorradorVentaVision) => void;
}) {
  const [e, setE] = useState<VisionEntregaSeleccion>(entregaInicial);
  return (
    <MemoryRouter>
      <VisionResultsPanel
        nombreFoto="freno.jpg"
        resultado={baseResultado(candidatos, conVehiculo)}
        loading={false}
        error={null}
        vehiculo={vehiculo}
        onVehiculoChange={vi.fn()}
        onBuscar={vi.fn()}
        onRepetirFoto={vi.fn()}
        onCerrar={vi.fn()}
        entrega={e}
        onCambiarEntrega={setE}
        onLlevarAVenta={onLlevarAVenta}
      />
    </MemoryRouter>
  );
}

describe("DISPONIBILIDAD por sucursal — sección compacta en cada card", () => {
  const FE2 = cand({
    itemCode: "DISP-FE2",
    name: "Zapata freno FE2",
    sucursales: [
      { sucursalId: 101, nombre: "Tienda 1", nivel: "DISPONIBLE" },
      { sucursalId: 102, nombre: "Tienda 2", nivel: "POCAS_UNIDADES" },
      { sucursalId: 103, nombre: "Tienda 3", nivel: "NO_DISPONIBLE" },
    ],
  });

  it("muestra los tres estados con su glifo, sin stickers numéricos de stock", () => {
    renderPanel({ resultado: baseResultado([FE2]) });

    const seccion = screen.getByTestId("disp-seccion-DISP-FE2");
    expect(within(seccion).getAllByText("Disponible").length).toBeGreaterThan(0);
    expect(within(seccion).getByText("Pocas unidades")).toBeInTheDocument();
    expect(within(seccion).getByText("No disponible")).toBeInTheDocument();
    expect(seccion.textContent).toContain("🟢");
    expect(seccion.textContent).toContain("🟡");
    expect(seccion.textContent).toContain("⚪");
    // La sección muestra buckets, jamás la cantidad exacta que simula el stock.
    expect(seccion.textContent).not.toContain("42");
    expect(seccion.textContent).not.toContain("7");
  });

  it("muestra por defecto hasta 3 sucursales y 'Ver todas las sucursales' si hay más", () => {
    renderPanel({
      resultado: baseResultado([
        cand({
          itemCode: "DISP-MAS",
          name: "Disco MAS",
          sucursales: [
            { sucursalId: 101, nombre: "Tienda 1", nivel: "DISPONIBLE" },
            { sucursalId: 102, nombre: "Tienda 2", nivel: "DISPONIBLE" },
            { sucursalId: 103, nombre: "Tienda 3", nivel: "DISPONIBLE" },
            { sucursalId: 104, nombre: "Tienda 4", nivel: "DISPONIBLE" },
          ],
        }),
      ]),
    });

    const seccion = screen.getByTestId("disp-seccion-DISP-MAS");
    expect(screen.getByTestId("disp-sucursal-DISP-MAS-101")).toBeInTheDocument();
    expect(screen.getByTestId("disp-sucursal-DISP-MAS-102")).toBeInTheDocument();
    expect(screen.getByTestId("disp-sucursal-DISP-MAS-103")).toBeInTheDocument();
    expect(screen.queryByTestId("disp-sucursal-DISP-MAS-104")).toBeNull();
    expect(within(seccion).getAllByRole("listitem")).toHaveLength(3);

    fireEvent.click(screen.getByTestId("disp-ver-todas-DISP-MAS"));
    expect(screen.getByTestId("disp-sucursal-DISP-MAS-104")).toBeInTheDocument();
    expect(within(seccion).getAllByRole("listitem")).toHaveLength(4);
    expect(within(seccion).getByText("Ocultar sucursales")).toBeInTheDocument();
  });

  it("sin sucursales de recogida avisa en la card", () => {
    renderPanel({ resultado: baseResultado([cand({ itemCode: "DISP-VAC", name: "Bomba VAC" })]) });
    expect(screen.getByTestId("disp-vacio-DISP-VAC").textContent).toBe("No disponible para recogida actualmente.");
  });

  it("el bloque '¿Cómo quieres recibirlo?' solo aparece tras 'Seleccionar para venta'", () => {
    renderPanel({ resultado: baseResultado([FE2]) });
    expect(screen.queryByText("¿Cómo quieres recibirlo?")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Seleccionar para venta" }));
    expect(screen.getByText("¿Cómo quieres recibirlo?")).toBeInTheDocument();
    expect(screen.getAllByText("Zapata freno FE2").length).toBeGreaterThanOrEqual(2);
  });

  it("Top 3: las tres mejores coincidencias conservan el layout con su sección", () => {
    renderPanel({
      resultado: baseResultado([
        cand({ itemCode: "DISP-A1", name: "Producto A1" }), cand({ itemCode: "DISP-A2", name: "Producto A2" }), cand({ itemCode: "DISP-A3", name: "Producto A3" }), cand({ itemCode: "DISP-A4", name: "Producto A4" }),
      ]),
    });

    expect(screen.getByTestId("disp-seccion-DISP-A1")).toBeInTheDocument();
    expect(screen.getByTestId("disp-seccion-DISP-A2")).toBeInTheDocument();
    expect(screen.getByTestId("disp-seccion-DISP-A3")).toBeInTheDocument();
    expect(screen.queryByTestId("disp-seccion-DISP-A4")).toBeNull();
    expect(screen.getByTestId("vision-mejor-coincidencia")).toBeInTheDocument();
  });

  it("disponibilidad y compatibilidad son independientes: 'Vehículo no indicado' + sucursal 🟢", () => {
    renderPanel({
      resultado: baseResultado(
        [cand({ itemCode: "DISP-IND", name: "Alternador IND", sucursales: [{ sucursalId: 101, nombre: "Tienda 1", nivel: "DISPONIBLE" }] })],
        false
      ),
    });

    expect(screen.getAllByText("Vehículo no indicado").length).toBeGreaterThan(0);
    const seccion = screen.getByTestId("disp-seccion-DISP-IND");
    expect(within(seccion).getByText("Disponible")).toBeInTheDocument();
  });
});

describe("Preparar venta — recoger en sucursal", () => {
  const candidato = cand({
    itemCode: "DISP-VT1",
    name: "Bomba VT1",
    sucursales: [
      { sucursalId: 101, nombre: "Tienda 1", nivel: "DISPONIBLE" },
      { sucursalId: 102, nombre: "Tienda 2", nivel: "POCAS_UNIDADES" },
      { sucursalId: 103, nombre: "Tienda 3", nivel: "NO_DISPONIBLE" },
    ],
  });

  it("solo ofrece sucursales válidas en el selector y auto-prefiere la primera", () => {
    const onLlevarAVenta = vi.fn();
    render(<Harness candidatos={[candidato]} onLlevarAVenta={onLlevarAVenta} />);

    fireEvent.click(screen.getByRole("button", { name: "Seleccionar para venta" }));

    expect(screen.getByRole("option", { name: "Tienda 1" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Tienda 2" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Tienda 3" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Continuar con venta" }));

    const borrador = onLlevarAVenta.mock.calls[0][0] as BorradorVentaVision;
    expect(borrador.entrega).toEqual({ modalidad: "recoger", sucursalId: 101, sucursalNombre: "Tienda 1" });
  });

  it("conserva la sucursal elegida y el stepper de cantidad en el borrador", () => {
    const onLlevarAVenta = vi.fn();
    render(<Harness candidatos={[candidato]} onLlevarAVenta={onLlevarAVenta} />);

    fireEvent.click(screen.getByRole("button", { name: "Seleccionar para venta" }));
    fireEvent.change(screen.getByLabelText("Sucursal de entrega"), { target: { value: "102" } });
    fireEvent.click(screen.getByRole("button", { name: "Aumentar cantidad" }));
    fireEvent.click(screen.getByRole("button", { name: "Continuar con venta" }));

    expect(screen.getByTestId("vision-cantidad").textContent).toBe("2");
    const borrador = onLlevarAVenta.mock.calls[0][0] as BorradorVentaVision;
    expect(borrador.entrega).toEqual({ modalidad: "recoger", sucursalId: 102, sucursalNombre: "Tienda 2" });
    expect(borrador.producto).toEqual({ itemCode: "DISP-VT1", nombre: "Bomba VT1", cantidad: 2 });
  });
});

describe("Preparar venta — delivery", () => {
  it("oculta el selector de sucursal y prepara el borrador sin sucursal", () => {
    const onLlevarAVenta = vi.fn();
    const candidato = cand({ itemCode: "DISP-DV", name: "Filtro DV", sucursales: [{ sucursalId: 101, nombre: "Tienda 1", nivel: "DISPONIBLE" }] });
    render(<Harness candidatos={[candidato]} entregaInicial={{ modalidad: "delivery", sucursalId: null }} onLlevarAVenta={onLlevarAVenta} />);

    fireEvent.click(screen.getByRole("button", { name: "Seleccionar para venta" }));

    expect(screen.queryByLabelText("Sucursal de entrega")).toBeNull();
    fireEvent.change(screen.getByLabelText("Lugar de entrega"), { target: { value: "Obrajes, La Paz" } });
    fireEvent.change(screen.getByLabelText("Entregar a"), { target: { value: "Carlos" } });
    fireEvent.click(screen.getByRole("button", { name: "Continuar con venta" }));

    const borrador = onLlevarAVenta.mock.calls[0][0] as BorradorVentaVision;
    expect(borrador.entrega).toEqual({
      modalidad: "delivery",
      sucursalId: null,
      sucursalNombre: "",
      lugarEntrega: "Obrajes, La Paz",
      paraQuien: "Carlos",
    });
  });
});