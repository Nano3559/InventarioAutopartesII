import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import VisionResultsPanel, { VisionVehiculoForm, VisionEntregaSeleccion } from "../VisionResultsPanel";
import { VisionAnalysis, VisionCandidatoPublico } from "../../../types/vision";
import { ReporteCalidad } from "../../../services/imageQuality";

const vehiculo: VisionVehiculoForm = { marca: "Toyota", modelo: "Corolla", anio: "2018" };
const entrega: VisionEntregaSeleccion = { modalidad: "recoger", sucursalId: null };

function cand(itemCode: string, name: string, overrides: Partial<VisionCandidatoPublico> = {}): VisionCandidatoPublico {
  return {
    id: Number(itemCode.replace(/\D/g, "")),
    itemCode,
    name,
    brand: "Bosch",
    model: "Corolla",
    year: "2018",
    image: null,
    categoria: "elect",
    price1: 200,
    nivelCoincidencia: "categoria",
    claseCoincide: false,
    compatibilidad: { verificada: false, score: 0, coincidencias: [], nota: "" },
    disponibilidad: { nivel: "DISPONIBLE", etiqueta: "Disponible" },
    disponibilidadPorSucursal: [],
    disponibilidadPorSucursalPublica: [],
    ...overrides,
  };
}

function baseResultado(conVehiculo: boolean): VisionAnalysis {
  return {
    version: "1.0",
    consultadoEn: "2026-01-01T00:00:00.000Z",
    proveedor: "http",
    deteccion: {
      categoria: "alternador",
      confianza: 0.9,
      confianzaBaja: false,
      categoriaMapeada: "eléctrico",
      boundingBox: { x: 0.2, y: 0.1, width: 0.5, height: 0.6 },
      textoDetectado: ["ALT", "120A"],
      codigosDetectados: ["AZ012"],
    },
    vehiculo: conVehiculo ? { marca: "Toyota", modelo: "Corolla", anio: "2018" } : { marca: null, modelo: null, anio: null },
    categoriaCatalogo: { id: 3, nombre: "Eléctrico" },
    candidatos: [
      // Mejor coincidencia: código OEM leído en la foto.
      cand("UX-001", "Alternador 120A Corolla", {
        scoreEvidencia: 10,
        evidencias: [{ campo: "oemCode", codigoProducto: "AZ-012", codigoDetectado: "AZ012", tipo: "exacta", peso: 10 }],
        compatibilidad: conVehiculo ? { verificada: true, score: 8, coincidencias: ["marca", "modelo"], nota: "" } : { verificada: false, score: 0, coincidencias: [], nota: "" },
      }),
      cand("UX-002", "Motor de arranque Corolla"),
      cand("UX-003", "Sensor de árbol de levas"),
      cand("UX-004", "Bomba de aceite Corolla"),
    ],
    compatibilidad: {
      consultada: conVehiculo,
      fuente: "base_datos_interna",
      metodologia: "baseline-catalog",
      consultadoEn: "2026-01-01T00:00:00.000Z",
      vehiculo: conVehiculo ? { marca: "Toyota", modelo: "Corolla", anio: "2018" } : null,
      verificadas: conVehiculo ? 1 : 0,
      noVerificadas: conVehiculo ? 3 : 4,
      nota: "",
    },
    entrega: { modalidades: ["recoger"], sucursales: [{ id: 1, nombre: "Tienda Norte", tipo: "TIENDA" }] },
    nota: "",
  };
}

const calidadBuena: ReporteCalidad = {
  brillo: 0.6,
  contraste: 0.3,
  nitidez: 0.02,
  resolucion: { ancho: 1200, alto: 900, megapixeles: 1.08 },
  bytesArchivo: 400 * 1024,
  estado: "buena",
  problemas: [],
  recomendaciones: [],
};

const calidadRegular: ReporteCalidad = {
  brillo: 0.7,
  contraste: 0.1,
  nitidez: 0.002,
  resolucion: { ancho: 700, alto: 500, megapixeles: 0.35 },
  bytesArchivo: 100 * 1024,
  estado: "regular",
  problemas: ["La nitidez es baja.", "La foto tiene poco contraste."],
  recomendaciones: ["Sostené el teléfono quieto y revisá que la pieza esté enfocada."],
};

function renderPanel(props: Partial<Parameters<typeof VisionResultsPanel>[0]> = {}) {
  return render(
    <MemoryRouter>
      <VisionResultsPanel
        nombreFoto="alternador.jpg"
        resultado={baseResultado(true)}
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

describe("MODO ESCANEO INTELIGENTE — calidad honesta, jamás 'n/d'", () => {
  it("calidad buena: una sola línea verde sin botones ni números sueltos", () => {
    renderPanel({ calidad: calidadBuena });

    expect(screen.getByTestId("vision-calidad-badge")).toBeInTheDocument();
    expect(screen.getByText("Calidad buena")).toBeInTheDocument();
    expect(screen.queryByText("Ver recomendaciones")).toBeNull();
    expect(document.body.textContent).not.toContain("n/d");
  });

  it("calidad regular: veredicto compacto y métricas solo al expandir", () => {
    renderPanel({ calidad: calidadRegular });

    expect(screen.getByText("Calidad regular")).toBeInTheDocument();
    expect(screen.queryByText("Nitidez")).toBeNull();

    fireEvent.click(screen.getByText("Ver recomendaciones"));
    expect(screen.getByTestId("calidad-problemas")).toBeInTheDocument();
    expect(screen.getByText("Nitidez")).toBeInTheDocument();
    expect(screen.getByText("Brillo")).toBeInTheDocument();
  });

  it("calidad mala: la imagen puede reducir la precisión, con salida hacia adelante", () => {
    renderPanel({
      calidad: { ...calidadRegular, estado: "mala", problemas: ["La foto está muy oscura (brillo 10%)."] },
    });

    expect(screen.getByText("La imagen puede reducir la precisión")).toBeInTheDocument();
    expect(screen.getAllByText("Tomar otra foto").length).toBeGreaterThan(0);
    expect(screen.getByText("Buscar igualmente")).toBeInTheDocument();
  });

  it("sin medición: hero dice 'No disponible' y el pipeline 'no medido'", () => {
    renderPanel({ resultado: baseResultado(false), calidad: null });

    expect(screen.getByTestId("vision-hero-calidad").textContent).toBe("No disponible");
    expect(screen.getByTestId("vision-detalles-analisis").textContent).toContain("Control de calidad · no medido");
    expect(document.body.textContent).not.toContain("n/d");
  });
});

describe("MODO ESCANEO INTELIGENTE — compatibilidad con vehículo", () => {
  it("sin vehículo: CTA global y chips 'Vehículo no indicado' sin repetir aviso", () => {
    renderPanel({ resultado: baseResultado(false) });

    expect(screen.getByTestId("vision-resumen-compatibilidad").textContent).toContain("Agrega tu vehículo para verificar compatibilidad");
    expect(screen.getAllByText("Vehículo no indicado").length).toBeGreaterThan(0);
    expect(screen.queryByText("✓ Compatible")).toBeNull();
    expect(screen.queryByText("⚠ No verificada")).toBeNull();
    expect(document.body.textContent).not.toContain("Compatibilidad no verificada");
  });

  it("con vehículo: verificado destaca en verde y el resto en ámbar", () => {
    renderPanel();

    const chipVerificado = screen.getByText("✓ Compatible");
    expect(chipVerificado).toBeInTheDocument();
    expect(screen.getAllByText("⚠ No verificada").length).toBeGreaterThan(0);
  });
});

describe("MODO ESCANEO INTELIGENTE — OCR y pipeline colapsables", () => {
  it("OCR: el recuento es primario y los códigos se abren bajo demanda", () => {
    renderPanel();

    const region = screen.getByTestId("vision-ocr-evidencia");
    expect(region.textContent).toContain("OCR · 1 código(s) detectado(s)");
    expect(region.textContent).toContain("Ver códigos");
    // El contenido sigue en el DOM, pero el resumen deja claro que está plegado.
    expect(region.textContent).toContain("AZ012");
    fireEvent.click(screen.getByText("Ver códigos"));
    expect(region.textContent).toContain("Ocultar");
  });

  it("pipeline: 'Ver detalles del análisis' guarda el recorrido técnico", () => {
    renderPanel();

    expect(screen.getByText("Ver detalles del análisis")).toBeInTheDocument();
    const detalles = screen.getByTestId("vision-detalles-analisis");
    expect(detalles.textContent).toContain("YOLO · 90%");
    expect(detalles.textContent).toContain("OCR · 1 código(s)");
    expect(detalles.textContent).toContain("4 candidato(s)");
  });

  it("los resultados se miden contra el vehículo elegido", () => {
    renderPanel({ resultado: baseResultado(true) });

    expect(screen.getByTestId("vision-resumen-compatibilidad").textContent).toContain("Toyota Corolla 2018");
  });
});

describe("MODO ESCANEO INTELIGENTE — Mejores coincidencias", () => {
  it("destaca la primera con la etiqueta 'Mejor coincidencia' y limita a 3", () => {
    renderPanel();

    expect(screen.getByTestId("vision-mejor-coincidencia").textContent).toBe("Mejor coincidencia");
    expect(screen.getByText("Alternador 120A Corolla")).toBeInTheDocument();
    expect(screen.queryByText("Bomba de aceite Corolla")).toBeNull();
    expect(screen.getByTestId("vision-ver-mas").textContent).toContain("Ver otros 1 resultados");
  });

  it("amplía y vuelve a contraer la lista", () => {
    renderPanel();

    fireEvent.click(screen.getByTestId("vision-ver-mas"));
    expect(screen.getByText("Bomba de aceite Corolla")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Mostrar menos"));
    expect(screen.queryByText("Bomba de aceite Corolla")).toBeNull();
  });
});

describe("MODO ESCANEO INTELIGENTE — vehículo como bloque propio", () => {
  it("pide marca, modelo y año antes de permitir verificar compatibilidad", () => {
    renderPanel({ vehiculo: { marca: "Toyota", modelo: "", anio: "" } });

    expect(screen.getByText("¿Para qué vehículo lo buscas?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Verificar compatibilidad" })).toBeDisabled();
    expect(screen.getByTestId("vision-vehiculo-ayuda").textContent).toContain("marca, modelo y año");
  });

  it("habilita la verificación cuando el vehículo está completo", () => {
    renderPanel({ vehiculo: { marca: "Toyota", modelo: "Corolla", anio: "2018" } });

    expect(screen.getByRole("button", { name: "Verificar compatibilidad" })).not.toBeDisabled();
  });
});