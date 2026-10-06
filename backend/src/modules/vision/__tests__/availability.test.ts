import { test } from "node:test";
import assert from "node:assert/strict";
import { computeSafeAvailability, availabilityView, sucursalDisponiblePublica } from "../availability";

test("umbrales: >10 Disponible, 1..10 Pocas unidades, 0 Consultar", () => {
  assert.equal(computeSafeAvailability(100), "DISPONIBLE");
  assert.equal(computeSafeAvailability(11), "DISPONIBLE");
  assert.equal(computeSafeAvailability(10), "POCAS_UNIDADES");
  assert.equal(computeSafeAvailability(1), "POCAS_UNIDADES");
  assert.equal(computeSafeAvailability(0), "NO_DISPONIBLE");
  assert.equal(computeSafeAvailability(-2), "NO_DISPONIBLE");
});

test("availabilityView expone la etiqueta en español", () => {
  assert.deepEqual(availabilityView(15), { nivel: "DISPONIBLE", etiqueta: "Disponible" });
  assert.deepEqual(availabilityView(3), { nivel: "POCAS_UNIDADES", etiqueta: "Pocas unidades" });
  assert.deepEqual(availabilityView(0), { nivel: "NO_DISPONIBLE", etiqueta: "Consultar disponibilidad" });
});

test("sucursalDisponiblePublica emite SOLO sucursalId + nombre + nivel (DTO mínimo)", () => {
  const row = sucursalDisponiblePublica(7, "Tienda Norte", 12);
  // El DTO público jamás lleva stock, locationId, tipo ni etiqueta.
  assert.deepEqual(Object.keys(row).sort(), ["nivel", "nombre", "sucursalId"]);
  assert.deepEqual(row, { sucursalId: 7, nombre: "Tienda Norte", nivel: "DISPONIBLE" });
});

test("sucursalDisponiblePublica conserva los umbrales seguros sin exponer cantidades", () => {
  assert.equal(sucursalDisponiblePublica(1, "Tienda A", 50).nivel, "DISPONIBLE");
  assert.equal(sucursalDisponiblePublica(2, "Tienda B", 4).nivel, "POCAS_UNIDADES");
  assert.equal(sucursalDisponiblePublica(3, "Tienda C", 0).nivel, "NO_DISPONIBLE");
});