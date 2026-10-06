
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import VisionResultsPanel, { VisionVehiculoForm, VisionEntregaSeleccion } from "../VisionResultsPanel";
import { VisionAnalysis } from "../../../types/vision";

const vehiculo: VisionVehiculoForm = { marca: "Toyota", modelo: "", anio: "" };
const entrega: VisionEntregaSeleccion = { modalidad: "recoger", sucursalId: null };

const resultado: VisionAnalysis = {
  version: "1.0",
  consultadoEn: "2026-01-01T00:00:00.000Z",
  proveedor: "http",
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
    fuente: "base_datos_interna",
    metodologia: "baseline-catalog",
    consultadoEn: "2026-01-01T00:00:00.000Z",
    vehiculo: null,
    verificadas: 1,
    noVerificadas: 0,
    nota: "",
  },
  entrega: {
    modalidades: ["recoger", "delivery"],
    sucursales: [{ id: 1, nombre: "Tienda Norte", tipo: "TIENDA" }],
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

describe("VisionResultsPanel — evidencia OCR y bounding box", () => {
  const resultadoHibrido: VisionAnalysis = {
    ...resultado,
    deteccion: {
      ...resultado.deteccion,
      boundingBox: { x: 0.25, y: 0.1, width: 0.5, height: 0.5 },
      textoDetectado: ["FILTRO", "ACEITE"],
      codigosDetectados: ["90915YZZD2"],
    },
    candidatos: [
      {
        ...resultado.candidatos[0],
        scoreEvidencia: 10,
        evidencias: [
          { campo: "oemCode", codigoProducto: "90915-YZZD2", codigoDetectado: "90915YZZD2", tipo: "exacta", peso: 10 },
        ],
      },
    ],
  };

  it("dibuja el bounding box sobre la foto capturada", () => {
    renderPanel({ resultado: resultadoHibrido, vistaPreviaUrl: "blob:mock-foto" });
    const caja = screen.getByTestId("vision-bounding-box");
    expect(caja.style.left).toBe("25%");
    expect(caja.style.width).toBe("50%");
  });

  it("sin vista previa no renderiza el overlay", () => {
    renderPanel({ resultado: resultadoHibrido });
    expect(screen.queryByTestId("vision-bounding-box")).toBeNull();
  });

  it("muestra los códigos leídos en la foto", () => {
    renderPanel({ resultado: resultadoHibrido });
    expect(screen.getByTestId("vision-codigos").textContent).toContain("90915YZZD2");
    expect(screen.getByTestId("vision-ocr-evidencia").textContent).toContain("FILTRO");
  });

  it("aclara que el código no confirma compatibilidad con el vehículo", () => {
    renderPanel({ resultado: resultadoHibrido });
    expect(screen.getByTestId("vision-ocr-evidencia").textContent?.toLowerCase()).toContain("no confirma");
  });

  it("etiqueta la evidencia del candidato con el nombre del código legible", () => {
    renderPanel({ resultado: resultadoHibrido });
    expect(screen.getByTestId("evidencia-FRN-001").textContent).toContain("Código coincide");
    expect(screen.getByText(/Código OEM: 90915-YZZD2/)).toBeTruthy();
  });

  it("explica el criterio de orden del ranking", () => {
    renderPanel({ resultado: resultadoHibrido });
    expect(screen.getByTestId("vision-ranking-nota").textContent).toContain("compatibilidad verificada");
  });

  it("sin evidencia de código no muestra la nota de ranking ni los chips", () => {
    renderPanel({ resultado });
    expect(screen.queryByTestId("vision-ranking-nota")).toBeNull();
    expect(screen.queryByTestId("vision-codigos")).toBeNull();
    expect(screen.queryByTestId("evidencia-FRN-001")).toBeNull();
  });
});

describe("VisionResultsPanel — recomendaciones de captura", () => {
  it("lista las recomendaciones cuando la detección falla por baja confianza", () => {
    renderPanel({
      resultado: null,
      error: "No se pudo identificar la pieza con suficiente confianza.",
      recomendaciones: ["Encuadra una sola pieza", "Usa fondo liso"],
    });
    const lista = screen.getByTestId("vision-recomendaciones");
    expect(lista.textContent).toContain("Encuadra una sola pieza");
    expect(lista.textContent).toContain("Usa fondo liso");
  });

  it("no muestra el bloque si no hay recomendaciones", () => {
    renderPanel({ resultado: null, error: "Fallo", recomendaciones: [] });
    expect(screen.queryByTestId("vision-recomendaciones")).toBeNull();
  });
});
