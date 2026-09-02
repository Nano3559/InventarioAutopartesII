import { test } from "node:test";
import assert from "node:assert/strict";
import { parseId, parsePositiveInt, parsePositiveDecimal, parseString } from "../validate";

test("parseId solo acepta enteros >= 1", () => {
  assert.equal(parseId("5"), 5);
  assert.throws(() => parseId("0"), /ID inválido/);
  assert.throws(() => parseId("-1"), /ID inválido/);
  assert.throws(() => parseId("a"), /ID inválido/);
});

test("parsePositiveInt solo acepta enteros >= 1", () => {
  assert.equal(parsePositiveInt("3", "Cantidad"), 3);
  assert.throws(() => parsePositiveInt("0", "Cantidad"), /Cantidad debe ser un número entero positivo/);
  assert.throws(() => parsePositiveInt("2.5", "Cantidad"), /Cantidad debe ser un número entero positivo/);
});

test("parsePositiveDecimal acepta 0 (se valida >0 en cada caso)", () => {
  assert.equal(parsePositiveDecimal("12.5", "Costo"), 12.5);
  assert.equal(parsePositiveDecimal("0", "Costo"), 0);
  assert.throws(() => parsePositiveDecimal("-4", "Costo"), /Costo debe ser un número positivo/);
});

test("parseString obligatorio", () => {
  assert.equal(parseString("  Hola  ", "Nombre"), "Hola");
  assert.equal(parseString(undefined, "Nota"), null);
  assert.throws(() => parseString("", "Nombre", { required: true }), /Nombre es obligatorio/);
  assert.throws(() => parseString(123, "Nombre"), /Nombre debe ser texto/);
});