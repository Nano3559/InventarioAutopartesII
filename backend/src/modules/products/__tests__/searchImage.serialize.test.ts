import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { serializeProductoPublico, serializeProductoInterno } from "../searchImage.service";

const FIXTURE: any = {
  id: 1,
  itemCode: "ABC-123",
  name: "Freno trasero",
  brand: "TEST",
  model: "TEST",
  year: "2020",
  detail: "detalle público",
  detalles: { calibrado: "si" },
  image: "https://example.test/img.png",
  category: { name: "Frenos" },
  price1: 120.5,
  price2: 100,
  wholesalePrice: 90,
  cost: 50,
  inventories: [
    { stock: 8, location: { name: "ALMACEN A", type: "ALMACEN" } },
    { stock: 4, location: { name: "TIENDA A", type: "TIENDA" } },
  ],
};

describe("Serialización de resultados de búsqueda por imagen", () => {
  it("el endpoint público NUNCA expone datos protegidos (precio2, costo, mayorista, stock ni ubicaciones)", () => {
    const resultado = serializeProductoPublico(FIXTURE, 0.95);

    assert.equal(resultado.id, 1);
    assert.equal(resultado.itemCode, "ABC-123");
    assert.equal(resultado.name, "Freno trasero");
    assert.equal(resultado.category, "Frenos");
    assert.equal(resultado.price1, 120.5);
    assert.equal(resultado.availability, "Disponible");
    assert.equal(resultado.score, 0.95);

    for (const campoProtegido of ["price2", "wholesalePrice", "cost", "totalStock", "locations"]) {
      assert.equal(
        Object.prototype.hasOwnProperty.call(resultado, campoProtegido),
        false,
        `el campo protegido "${campoProtegido}" no debe existir en la salida pública`
      );
    }
  });

  it("el endpoint interno sí expone price2, stock total y ubicaciones, pero tampoco costo ni mayorista", () => {
    const resultado = serializeProductoInterno(FIXTURE, 0.6);

    assert.equal(resultado.price2, 100);
    assert.equal(resultado.totalStock, 12);
    assert.deepEqual(resultado.locations, [
      { name: "ALMACEN A", type: "ALMACEN", stock: 8 },
      { name: "TIENDA A", type: "TIENDA", stock: 4 },
    ]);
    assert.equal(resultado.score, 0.6);

    for (const campoProtegido of ["wholesalePrice", "cost"]) {
      assert.equal(
        Object.prototype.hasOwnProperty.call(resultado, campoProtegido),
        false,
        `el campo "${campoProtegido}" no debe existir en la salida interna`
      );
    }
  });
});