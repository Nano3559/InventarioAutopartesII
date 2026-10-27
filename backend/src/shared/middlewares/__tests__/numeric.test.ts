import { test } from "node:test";
import assert from "node:assert/strict";
import { parsePositiveInt, parsePositiveDecimal, parseId } from "../validate";
test("enteros y IDs respetan el rango PostgreSQL", () => {
  for (const value of [0, -1, 1.5, Infinity, NaN, 2147483648, true]) assert.throws(() => parsePositiveInt(value, "Cantidad"));
  assert.throws(() => parseId("2147483648"));
  assert.equal(parsePositiveInt("12", "Cantidad"), 12);
});
test("decimales rechazan infinitos, booleanos, vacío y exceso de importe", () => {
  for (const value of [Infinity, -Infinity, NaN, true, "", null, -1, 1000000001]) assert.throws(() => parsePositiveDecimal(value, "Importe"));
  assert.equal(parsePositiveDecimal("12.34", "Importe"), 12.34);
  assert.equal(parsePositiveDecimal(0, "Porcentaje"), 0);
});
