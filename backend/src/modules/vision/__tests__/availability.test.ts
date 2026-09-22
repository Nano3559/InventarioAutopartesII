import { test } from "node:test";
import assert from "node:assert/strict";
import { computeSafeAvailability, availabilityView } from "../availability";

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