import { test } from "node:test";
import assert from "node:assert/strict";
import { validateAndMergeItems } from "../saleItems";

test("valida y mantiene ítems únicos", () => {
  const items = validateAndMergeItems([
    { productId: 1, quantity: 2, unitPrice: 10 },
    { productId: 2, quantity: 1, unitPrice: 5 },
  ]);
  assert.deepEqual(items, [
    { productId: 1, quantity: 2, unitPrice: 10 },
    { productId: 2, quantity: 1, unitPrice: 5 },
  ]);
});

test("deduplica productos repetidos sumando cantidades", () => {
  const items = validateAndMergeItems([
    { productId: 1, quantity: 2, unitPrice: 10 },
    { productId: 1, quantity: 3, unitPrice: 10 },
    { productId: 1, quantity: 1, unitPrice: 10 },
  ]);
  assert.deepEqual(items, [{ productId: 1, quantity: 6, unitPrice: 10 }]);
});

test("acepta wholesalePrice como precio si no hay unitPrice", () => {
  const items = validateAndMergeItems([
    { productId: 5, quantity: 3, wholesalePrice: 25 },
  ]);
  assert.deepEqual(items, [{ productId: 5, quantity: 3, unitPrice: 25 }]);
});

test("rechaza cantidad no entera menor a 1", () => {
  assert.throws(
    () => validateAndMergeItems([{ productId: 1, quantity: 0, unitPrice: 10 }]),
    /cantidad del producto 1 debe ser un entero mayor a 0/
  );
});

test("rechaza precio unitario menor o igual a 0", () => {
  assert.throws(
    () => validateAndMergeItems([{ productId: 1, quantity: 1, unitPrice: 0 }]),
    /precio unitario del producto 1 debe ser mayor a 0/
  );
});

test("rechaza productId inválido", () => {
  assert.throws(
    () => validateAndMergeItems([{ productId: 0, quantity: 1, unitPrice: 10 }]),
    /productId válido/
  );
  assert.throws(
    () => validateAndMergeItems([{ quantity: 1, unitPrice: 10 }]),
    /productId válido/
  );
});

test("rechaza lista vacía", () => {
  assert.throws(() => validateAndMergeItems([]), /al menos un ítem/);
});