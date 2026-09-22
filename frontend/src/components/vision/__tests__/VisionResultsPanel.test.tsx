import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import VisionResultsPanel, {
  VisionVehiculoForm,
  VisionEntregaSeleccion,
} from "../VisionResultsPanel";
import { VisionAnalysis } from "../../../types/vision";

const vehiculo: VisionVehiculoForm = { marca: "Toyota", modelo: "", anio: "" };
const entrega: VisionEntregaSeleccion = { modalidad: "recoger", sucursalId: null };

const resultado: VisionAnalysis = {
  version: "mock-1",
  consultadoEn: "2026-01-01T00:00:00.000Z",
  proveedor: "mock",
  deteccion: {
    categoria: "freno de tambor",
    confianza: 0.94,
    confianzaBaja: false,
    categoriaMapeada: "frenos",
    boundingBox: { x: 0, y: 0, width: 200, height: 200 },
  },
  vehiculo: { marca: null, modelo: null, anio: null },
  categoriaCatalogo: null,
  candidatos: [
    {
      id: 1,
      itemCode: "FRN-001",
      name: "Zapata de freno trasera",
      brand: "Bosch",
      model: "Corolla",
      year: "2018",
      image: "freno.jpg",
      categoria: "frenos",
      price1: 120.5,
      compatibilidad: { verificada: true, score: 8, coincidencias: ["freno"], nota: "" },
      disponibilidad: { nivel: "DISPONIBLE", etiqueta: "Disponible" },
      disponibilidadPorSucursal: [
        { locationId: 1, nombre: "Tienda Norte", tipo: "TIENDA", nivel: "DISPONIBLE", etiqueta: "Disponible" },
      ],
    },
  ],
  compatibilidad: {
    consultada: false,
    fuente: "mock",
    metodologia: "mock",
    consultadoEn: "2026-01-01T00:00:00.000Z",
    vehiculo: null,
    verificadas: 1,
    noVerificadas: 0,
    nota: "",
  },
  entrega: {
    modalidades: ["recoger", "delivery"],
    sucursales: [
      { id: 1, nombre: "Tienda Norte", tipo: "TIENDA" },
    ],
  },
  nota: "",
};

function renderPanel(props: Partial<Parameters<typeof VisionResultsPanel>[0]> = {}) {
  const defaults = {
    nombreFoto: "captura-vision-123.jpg",
    resultado: null,
    loading: false,
    error: null,
    vehiculo,
    onVehiculoChange: vi.fn(),
    onBuscar: vi.fn(),
    onRepetirFoto: vi.fn(),
    onCerrar: vi.fn(),
    entrega,
    onCambiarEntrega: vi.fn(),
    onLlevarAVenta: vi.fn(),
  };
  return render(
    <MemoryRouter>
      <VisionResultsPanel {...defaults} {...props} />
    </MemoryRouter>
  );
}

describe("VisionResultsPanel", () => {
  it("muestra el nombre de la foto capturada", () => {
    renderPanel({ nombreFoto: "foto-prueba.jpg" });
    expect(screen.getByText(/foto-prueba\.jpg/)).toBeInTheDocument();
  });

  it("muestra indicador de carga mientras busca", () => {
    renderPanel({ loading: true });
    expect(screen.getByText("Analizando imagen...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /buscando/i })).toBeDisabled();
  });

  it("muestra el error y permite repetir la foto", () => {
    const onRepetirFoto = vi.fn();
    renderPanel({ error: "No se pudo clasificar la imagen", onRepetirFoto });
    expect(screen.getByText("No se pudo clasificar la imagen")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /otra foto/i }));
    expect(onRepetirFoto).toHaveBeenCalled();
  });

  it("notifica onVehiculoChange al editar los campos del vehículo", () => {
    const onVehiculoChange = vi.fn();
    renderPanel({ onVehiculoChange });

    fireEvent.change(screen.getByLabelText("Marca del vehículo"), { target: { value: "Honda" } });
    expect(onVehiculoChange).toHaveBeenCalledWith("marca", "Honda");
  });

  it("muestra candidatos con compatibilidad y disponibilidad", () => {
    renderPanel({ resultado });

    expect(screen.getByText("Confianza 94%")).toBeInTheDocument();
    expect(screen.getByText("Zapata de freno trasera")).toBeInTheDocument();
    expect(screen.getByText("Disponible")).toBeInTheDocument();
    expect(screen.getByText("Bs. 120.50")).toBeInTheDocument();
    expect(screen.getByText("1 de 1 candidatos mostrados verifican compatibilidad")).toBeInTheDocument();
  });

  it("muestra selector de entrega con sucursales y notifica el cambio", () => {
    const onCambiarEntrega = vi.fn();
    renderPanel({ resultado, onCambiarEntrega });

    expect(screen.getByLabelText("Modalidad de entrega")).toBeInTheDocument();
    expect(screen.getByLabelText("Sucursal de entrega")).toBeInTheDocument();
    expect(screen.getByText("Tienda Norte")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Modalidad de entrega"), { target: { value: "delivery" } });
    expect(onCambiarEntrega).toHaveBeenCalledWith({ modalidad: "delivery", sucursalId: null });
  });

  it("ejecuta onBuscar al presionar Buscar", () => {
    const onBuscar = vi.fn();
    renderPanel({ onBuscar });
    fireEvent.click(screen.getByRole("button", { name: "Buscar" }));
    expect(onBuscar).toHaveBeenCalled();
  });

  it("cierra el panel al presionar el botón de cerrar", () => {
    const onCerrar = vi.fn();
    renderPanel({ onCerrar });
    fireEvent.click(screen.getByLabelText("Cerrar resultados"));
    expect(onCerrar).toHaveBeenCalled();
  });

  it("selecciona un candidato y prepara la venta para recoger en la sucursal con stock", () => {
    const onLlevarAVenta = vi.fn();
    const onCambiarEntrega = vi.fn();
    renderPanel({ resultado, onLlevarAVenta, onCambiarEntrega });

    fireEvent.click(screen.getByRole("button", { name: "Seleccionar para venta" }));
    expect(screen.getByText("Seleccionado")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Cantidad a preparar"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar venta" }));

    expect(onLlevarAVenta).toHaveBeenCalledTimes(1);
    const borrador = onLlevarAVenta.mock.calls[0][0];
    expect(borrador.origen).toBe("vision");
    expect(borrador.producto).toEqual({ itemCode: "FRN-001", nombre: "Zapata de freno trasera", cantidad: 3 });
    expect(borrador.entrega).toEqual({ modalidad: "recoger", sucursalId: 1, sucursalNombre: "Tienda Norte" });
  });

  it("prepara la venta en modalidad delivery con lugar de entrega y destinatario", () => {
    const onLlevarAVenta = vi.fn();
    renderPanel({
      resultado,
      entrega: { modalidad: "delivery", sucursalId: null },
      onLlevarAVenta,
    });

    fireEvent.click(screen.getByRole("button", { name: "Seleccionar para venta" }));

    fireEvent.change(screen.getByLabelText("Lugar de entrega"), { target: { value: "Zona Sur, La Paz" } });
    fireEvent.change(screen.getByLabelText("Entregar a"), { target: { value: "María" } });
    fireEvent.click(screen.getByRole("button", { name: "Preparar venta" }));

    const borrador = onLlevarAVenta.mock.calls[0][0];
    expect(borrador.entrega).toEqual({
      modalidad: "delivery",
      sucursalId: null,
      sucursalNombre: "",
      lugarEntrega: "Zona Sur, La Paz",
      paraQuien: "María",
    });
    expect(borrador.producto.cantidad).toBe(1);
  });

  it("impide preparar la venta para recoger si ninguna sucursal tiene stock del candidato", () => {
    const sinStockResultado: VisionAnalysis = {
      ...resultado,
      candidatos: [
        {
          ...resultado.candidatos[0],
          disponibilidad: { nivel: "NO_DISPONIBLE", etiqueta: "Sin stock" },
          disponibilidadPorSucursal: [
            { locationId: 1, nombre: "Tienda Norte", tipo: "TIENDA", nivel: "NO_DISPONIBLE", etiqueta: "Sin stock" },
          ],
        },
      ],
    };
    const onLlevarAVenta = vi.fn();
    renderPanel({ resultado: sinStockResultado, onLlevarAVenta });

    fireEvent.click(screen.getByRole("button", { name: "Seleccionar para venta" }));
    expect(screen.getByText("Sin sucursales con stock")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preparar venta" })).toBeDisabled();
  });
});