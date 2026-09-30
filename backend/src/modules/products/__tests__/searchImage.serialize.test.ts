import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  resolveLocationScope,
  serializeProductoPublico,
  serializeProductoInterno,
} from "../searchImage.service";

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
    { stock: 8, location: { id: 90, name: "ALMACEN A", type: "ALMACEN" } },
    { stock: 4, location: { id: 10, name: "TIENDA A", type: "TIENDA" } },
    { stock: 6, location: { id: 20, name: "TIENDA B", type: "TIENDA" } },
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
    assert.equal(resultado.totalStock, 18);
    assert.deepEqual(resultado.locations, [
      { name: "ALMACEN A", type: "ALMACEN", stock: 8 },
      { name: "TIENDA A", type: "TIENDA", stock: 4 },
      { name: "TIENDA B", type: "TIENDA", stock: 6 },
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

describe("Aislamiento por ubicación en la búsqueda por imagen (TIENDA)", () => {
  it("un TIENDA solo ve el stock y la ubicación de su propia tienda", () => {
    const resultado = serializeProductoInterno(FIXTURE, 0.6, 10);

    assert.equal(resultado.totalStock, 4, "el totalStock debe ser solo el de su tienda");
    assert.deepEqual(resultado.locations, [{ name: "TIENDA A", type: "TIENDA", stock: 4 }]);

    const serializado = JSON.stringify(resultado);
    assert.equal(serializado.includes("ALMACEN A"), false, "no debe filtrar el nombre del almacén");
    assert.equal(serializado.includes("TIENDA B"), false, "no debe filtrar el nombre de otra tienda");
  });

  it("otro TIENDA ve un totalStock distinto para el mismo producto (no hay total compartido)", () => {
    const tiendaA = serializeProductoInterno(FIXTURE, 0.6, 10);
    const tiendaB = serializeProductoInterno(FIXTURE, 0.6, 20);

    assert.equal(tiendaA.totalStock, 4);
    assert.equal(tiendaB.totalStock, 6);
    assert.notEqual(tiendaA.totalStock, tiendaB.totalStock);
    assert.deepEqual(tiendaB.locations, [{ name: "TIENDA B", type: "TIENDA", stock: 6 }]);
  });

  it("si el producto no tiene inventario en la tienda del usuario, totalStock es 0 y locations va vacío", () => {
    const resultado = serializeProductoInterno(FIXTURE, 0.6, 999);

    assert.equal(resultado.totalStock, 0);
    assert.deepEqual(resultado.locations, []);
  });

  it("ADMIN e INVENTARIO conservan la vista global (sin scope)", () => {
    for (const rol of ["ADMIN", "INVENTARIO"]) {
      assert.equal(resolveLocationScope({ role: rol, locationId: null }), null, `${rol} debe ver todas las ubicaciones`);
      const resultado = serializeProductoInterno(FIXTURE, 0.6, resolveLocationScope({ role: rol }));
      assert.equal(resultado.totalStock, 18);
      assert.equal(resultado.locations.length, 3);
    }
  });

  it("resolveLocationScope acota a TIENDA y nunca amplía el alcance", () => {
    assert.equal(resolveLocationScope({ role: "TIENDA", locationId: 10 }), 10);
    assert.equal(resolveLocationScope({ role: "TIENDA", locationId: null }), null, "sin ubicación no se amplia el alcance");
    assert.equal(resolveLocationScope(undefined), null);
    assert.equal(resolveLocationScope(null), null);
  });
});