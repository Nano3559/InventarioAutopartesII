import { describe, it, expect, beforeEach } from "vitest";
import {
  guardarBorradorVision,
  leerBorradorVision,
  limpiarBorradorVision,
  BorradorVentaVision,
} from "../saleDraft";

const borrador: BorradorVentaVision = {
  origen: "vision",
  creadoEn: "2026-09-21T00:00:00.000Z",
  producto: { itemCode: "FRN-001", nombre: "Zapata de freno trasera", cantidad: 2 },
  entrega: { modalidad: "recoger", sucursalId: 1, sucursalNombre: "Tienda Norte" },
};

describe("saleDraft", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("guarda y lee un borrador de visión", () => {
    guardarBorradorVision(borrador);
    const leido = leerBorradorVision();
    expect(leido).toEqual(borrador);
  });

  it("lee null cuando no hay borrador guardado", () => {
    expect(leerBorradorVision()).toBeNull();
  });

  it("limpiarBorradorVision elimina el borrador", () => {
    guardarBorradorVision(borrador);
    limpiarBorradorVision();
    expect(leerBorradorVision()).toBeNull();
  });

  it("ignora datos corruptos o de otro origen", () => {
    localStorage.setItem(
      "borrador_venta_vision",
      JSON.stringify({ origen: "otro", producto: {} })
    );
    expect(leerBorradorVision()).toBeNull();

    localStorage.setItem("borrador_venta_vision", "no-json{");
    expect(leerBorradorVision()).toBeNull();
  });

  it("guarda un borrador con modalidad delivery y texto libre", () => {
    const conDelivery: BorradorVentaVision = {
      origen: "vision",
      creadoEn: "2026-09-21T00:00:00.000Z",
      producto: { itemCode: "ACE-100", nombre: "Aceite 5W30", cantidad: 1 },
      entrega: {
        modalidad: "delivery",
        sucursalId: null,
        sucursalNombre: "",
        lugarEntrega: "Av. Arce 123, La Paz",
        paraQuien: "Pedro",
      },
    };
    guardarBorradorVision(conDelivery);
    expect(leerBorradorVision()).toEqual(conDelivery);
  });
});