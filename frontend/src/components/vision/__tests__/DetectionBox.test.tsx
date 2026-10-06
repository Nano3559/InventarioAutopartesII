import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import DetectionBox from "../DetectionBox";

const IMAGEN = "blob:mock-foto";

describe("DetectionBox — overlay del bounding box normalizado (0..1)", () => {
  it("dibuja la caja con porcentajes sobre la imagen", () => {
    render(
      <DetectionBox
        src={IMAGEN}
        alt="Foto de la pieza"
        boundingBox={{ x: 0.2, y: 0.3, width: 0.5, height: 0.4 }}
        categoria="oil_filter"
        confianza={0.87}
      />
    );

    const caja = screen.getByTestId("vision-bounding-box");
    expect(caja.style.left).toBe("20%");
    expect(caja.style.top).toBe("30%");
    expect(caja.style.width).toBe("50%");
    expect(caja.style.height).toBe("40%");
  });

  it("muestra categoría y confianza redondeada en la caja", () => {
    render(
      <DetectionBox
        src={IMAGEN}
        alt="Foto de la pieza"
        boundingBox={{ x: 0.1, y: 0.1, width: 0.5, height: 0.5 }}
        categoria="oil_filter"
        confianza={0.874}
      />
    );

    expect(screen.getByTestId("vision-bounding-box").textContent).toContain("oil_filter");
    expect(screen.getByTestId("vision-bounding-box").textContent).toContain("87%");
    expect(screen.getByRole("img", { name: /oil_filter/ })).toBeTruthy();
  });

  it("sin bounding box: no dibuja caja pero sí muestra la imagen y lo explica", () => {
    render(
      <DetectionBox src={IMAGEN} alt="Foto de la pieza" boundingBox={null} categoria="radiator" confianza={0.4} />
    );

    expect(screen.queryByTestId("vision-bounding-box")).toBeNull();
    expect(screen.getByAltText("Foto de la pieza")).toBeTruthy();
    expect(screen.getByText(/no indicó una zona concreta/i)).toBeTruthy();
  });

  it("acota coordenadas fuera de rango en vez de romper el layout", () => {
    render(
      <DetectionBox
        src={IMAGEN}
        alt="Foto de la pieza"
        boundingBox={{ x: -0.4, y: 1.4, width: 0.3, height: 0.3 }}
        categoria="alternator"
        confianza={0.5}
      />
    );

    const caja = screen.getByTestId("vision-bounding-box");
    expect(caja.style.left).toBe("0%");
    expect(caja.style.top).toBe("100%");
  });

  it("una caja degenerada (sin área) no se dibuja", () => {
    render(
      <DetectionBox
        src={IMAGEN}
        alt="Foto de la pieza"
        boundingBox={{ x: 0.5, y: 0.5, width: 0, height: 0 }}
        categoria="brake_pad"
        confianza={0.5}
      />
    );

    expect(screen.queryByTestId("vision-bounding-box")).toBeNull();
  });
});