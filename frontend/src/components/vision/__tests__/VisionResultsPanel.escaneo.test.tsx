
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import VisionResultsPanel, { VisionVehiculoForm, VisionEntregaSeleccion } from "../VisionResultsPanel";
import { VisionAnalysis, VisionCandidatoPublico } from "../../../types/vision";
import { ReporteCalidad } from "../../../services/imageQuality";
import { combinarDetecciones } from "../../../services/multiView";

const vehiculo: VisionVehiculoForm = { marca: "Toyota", modelo: "", anio: "" };
const entrega: VisionEntregaSeleccion = { modalidad: "recoger", sucursalId: null };

const candidato: VisionCandidatoPublico = {
  id: 1,
  itemCode: "FRN-001",
  name: "Zapata de freno trasera",
  brand: "Bosch",
  model: "Corolla",
  year: "2018",
  image: "freno.jpg",
  categoria: "frenos",
  price1: 120.5,
  scoreEvidencia: 10,
  evidencias: [
    { campo: "oemCode", codigoProducto: "90915-YZZD2", codigoDetectado: "90915YZZD2", tipo: "exacta", peso: 10 },
  ],
  compatibilidad: { verificada: false, score: 1, coincidencias: ["freno"], nota: "" },
  disponibilidad: { nivel: "DISPONIBLE", etiqueta: "Disponible" },
  disponibilidadPorSucursal: [],
};

function base(confianza = 0.94): VisionAnalysis {
  return {
    version: "1.0",
    consultadoEn: "2026-01-01T00:00:00.000Z",
    proveedor: "http",
    deteccion: {
      categoria: "freno de tambor",
      confianza,
      confianzaBaja: false,
      categoriaMapeada: "frenos",
      boundingBox: { x: 0, y: 0, width: 200, height: 200 },
      textoDetectado: ["90915", "YZZD2"],
      codigosDetectados: ["90915YZZD2"],
    },
    vehiculo: { marca: null, modelo: null, anio: null },
    categoriaCatalogo: null,
    candidatos: [candidato],
    compatibilidad: {
      consultada: false,
      fuente: "base_datos_interna",
      metodologia: "baseline-catalog",
      consultadoEn: "2026-01-01T00:00:00.000Z",
      vehiculo: null,
      verificadas: 0,
      noVerificadas: 1,
      nota: "",
    },
    entrega: { modalidades: ["recoger"], sucursales: [{ id: 1, nombre: "Tienda Norte", tipo: "TIENDA" }] },
    nota: "",
  };
}

const calidad: ReporteCalidad = {
  brillo: 0.1,
  contraste: 0.2,
  nitidez: 0.01,
  resolucion: { ancho: 800, alto: 600, megapixeles: 0.48 },
  bytesArchivo: 300 * 1024,
  estado: "mala",
  problemas: ["La foto está muy oscura (brillo 10%)."],
  recomendaciones: ["Buscá más luz o acercá la pieza a una fuente de luz."],
};

function renderPanel(props: Partial<Parameters<typeof VisionResultsPanel>[0]> = {}) {
  return render(
    <MemoryRouter>
      <VisionResultsPanel
        nombreFoto="captura.jpg"
        resultado={base()}
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

describe("MODO ESCANEO INTELIGENTE — score separado de confianza IA", () => {
  it("la confianza del modelo y el score de coincidencia viven en elementos distintos", () => {
    renderPanel();

    const confianza = screen.getByText("Confianza del modelo 94%");
    const score = screen.getByTestId("score-FRN-001");

    expect(confianza).toBeTruthy();
    expect(score.textContent).toContain("Score de coincidencia 10");
    expect(confianza).not.toBe(score);
  });

  it("en ninguna parte aparece la frase 'Confianza IA'", () => {
    renderPanel();
    expect(document.body.textContent).not.toMatch(/Confianza IA/i);
  });

  it("el score se explica como decisión del motor de catálogo, no del modelo", () => {
    renderPanel();
    const score = screen.getByTestId("score-FRN-001");
    expect(score.getAttribute("title")).toMatch(/motor de catálogo/i);
    expect(score.getAttribute("title")).toMatch(/YOLO/i);
  });

  it("NO declara compatibilidad verificada cuando el backend no la verificó", () => {
    renderPanel();

    expect(screen.getByText("Compatibilidad no verificada")).toBeInTheDocument();
    expect(screen.queryByText("Compatibilidad verificada")).toBeNull();
  });
});

describe("MODO ESCANEO INTELIGENTE — explicabilidad", () => {
  it("ofrece la sección ¿Por qué aparece este producto?", () => {
    renderPanel();

    expect(screen.getByText("¿Por qué aparece este producto?")).toBeTruthy();
    const detalle = screen.getByText("¿Por qué aparece este producto?").closest("details")!;
    expect(detalle.textContent).toContain("Categoría visual coincide");
    expect(detalle.textContent).toContain("Código OEM exacto: 90915YZZD2");
    expect(detalle.textContent).toContain("Compatibilidad no verificada");
  });
});

describe("MODO ESCANEO INTELIGENTE — calidad de imagen", () => {
  it("muestra el veredicto de calidad y el aviso de menor precisión", () => {
    renderPanel({ calidad });

    expect(screen.getByText(/Calidad de la foto: Mala/i)).toBeTruthy();
    expect(screen.getByText(/puede reducir la precisión/i)).toBeTruthy();
    expect(screen.getByText(/oscura/i)).toBeTruthy();
  });

  it("sin medición de calidad no dibuja nada", () => {
    renderPanel({ calidad: null });
    expect(screen.queryByText(/Calidad de la foto/i)).toBeNull();
  });

  it("advierte antes de buscar sin bloquear: los dos caminos están disponibles", () => {
    renderPanel({ advertirCalidad: true, resultado: null, calidad, onContinuarDeTodosModos: vi.fn(), onDescartarPorCalidad: vi.fn() });

    expect(screen.getByTestId("vision-aviso-calidad")).toBeTruthy();
    expect(screen.getByText("Buscar de todos modos")).toBeTruthy();
    expect(screen.getByText(/Tomar otra foto/)).toBeTruthy();
  });
});

describe("MODO ESCANEO INTELIGENTE — pipeline visible", () => {
  it("resume el recorrido completo con valores reales", () => {
    renderPanel();

    const nav = screen.getByLabelText("Pipeline del análisis");
    expect(nav.textContent).toContain("Foto");
    expect(nav.textContent).toContain("BoundingBox");
    expect(nav.textContent).toContain("YOLO · 94%");
    expect(nav.textContent).toContain("OCR · 1 código(s)");
    expect(nav.textContent).toContain("candidato(s)");
    expect(nav.textContent).toContain("Disponible");
  });
});

describe("MODO ESCANEO INTELIGENTE — segunda foto", () => {
  it("ofrece confirmar cuando la confianza está en zona media", () => {
    renderPanel({ resultado: base(0.65) });

    expect(screen.getByTestId("vision-ofrece-segunda-foto")).toBeTruthy();
    expect(screen.getByText(/¿Querés confirmar con otra foto\?/)).toBeTruthy();
  });

  it("NO ofrece segunda foto cuando la confianza es alta", () => {
    renderPanel({ resultado: base(0.94) });
    expect(screen.queryByTestId("vision-ofrece-segunda-foto")).toBeNull();
  });

  it("muestra 'Confirmado por 2 imágenes' cuando las dos fotos coinciden", () => {
    const detecciones = [base(0.62).deteccion, base(0.71).deteccion];
    const verificacion = combinarDetecciones(detecciones);

    renderPanel({ verificacion });

    expect(screen.getByTestId("vision-verificacion").getAttribute("data-estado")).toBe("confirmado");
    expect(screen.getByText("Confirmado por 2 imágenes")).toBeTruthy();
    expect(screen.getByText(/Confirmado con 2 ángulos/)).toBeTruthy();
  });

  it("muestra 'Resultados inconsistentes' con las dos posibilidades", () => {
    const a = base(0.72);
    const b = base(0.66);
    b.deteccion.categoria = "aire acondicionado";
    b.deteccion.categoriaMapeada = "aire";

    renderPanel({ verificacion: combinarDetecciones([a.deteccion, b.deteccion]) });

    expect(screen.getByTestId("vision-verificacion").getAttribute("data-estado")).toBe("inconsistente");
    expect(screen.getAllByText("Resultados inconsistentes").length).toBeGreaterThan(0);
    expect(screen.getByTestId("vision-posibilidades").textContent).toContain("1.ª foto");
    expect(screen.getByTestId("vision-posibilidades").textContent).toContain("2.ª foto");
  });

  it("no declara confirmación cuando solo hay una foto", () => {
    renderPanel({ verificacion: combinarDetecciones([base(0.62).deteccion]) });

    expect(screen.getByText("No confirmado")).toBeTruthy();
    expect(screen.queryByText("Confirmado por 2 imágenes")).toBeNull();
  });
});