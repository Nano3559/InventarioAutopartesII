import { test } from "node:test";
import assert from "node:assert/strict";
import { validateAndMergeItems } from "../saleItems";
import { salePrice, validatePriceConfiguration, validatePayments, MAX_QUANTITY, lineSubtotal } from "../../shared/utils/pricing";
const product = { price1: 100, price2: 120, wholesalePrice: 80, cost: 60 };
test("resuelve ambos modos del catálogo e ignora importes arbitrarios", () => {
  for (const unitPrice of [0, -1, Infinity, 999999]) {
    const [i] = validateAndMergeItems([{ productId: 1, quantity: 2, priceMode: "POR_MAYOR", unitPrice }]);
    assert.equal(salePrice(product, i.priceMode), 80);
  }
  assert.equal(salePrice(product, "PRICE1"), 100);
  assert.equal(salePrice(product, "WHOLESALE"), 80);
});
test("fusiona cantidades conservando modo y rechaza modos mezclados", () => {
  assert.deepEqual(validateAndMergeItems([{ productId: 1, quantity: 2 }, { productId: 1, quantity: 3 }]), [{ productId: 1, quantity: 5, priceMode: "POR_MENOR" }]);
  assert.throws(() => validateAndMergeItems([{ productId: 1, quantity: 2, priceMode: "POR_MENOR" }, { productId: 1, quantity: 3, priceMode: "POR_MAYOR" }]));
});
test("rechaza cantidades, IDs y niveles fuera del contrato", () => {
  for (const quantity of [0, -1, 1.5, Infinity, NaN, MAX_QUANTITY + 1, true]) assert.throws(() => validateAndMergeItems([{ productId: 1, quantity }]));
  for (const productId of [0, NaN, Infinity, true]) assert.throws(() => validateAndMergeItems([{ productId, quantity: 1 }]));
  assert.throws(() => validateAndMergeItems([{ productId: 1, quantity: 1, priceTier: "FREE" }]));
  assert.throws(() => validateAndMergeItems([]));
  assert.throws(() => validateAndMergeItems([{ productId: 1, quantity: MAX_QUANTITY }, { productId: 1, quantity: 1 }]));
});
test("mayorista exige precio exclusivo y coherente frente a costo y ambos modos", () => {
  for (const wholesalePrice of [null, 0, 121, 50, Infinity]) assert.throws(() => salePrice({ ...product, wholesalePrice }, "WHOLESALE"));
  assert.throws(() => validatePriceConfiguration({ ...product, price1: 59 }));
  assert.doesNotThrow(() => validatePriceConfiguration({ ...product, wholesalePrice: 60 }));
});
test("pagos combinados incluyen crédito como asignación, no permiten infinito ni negativos", () => {
  assert.deepEqual(validatePayments([{ method: "EFECTIVO", amount: 30 }, { method: "CREDITO", amount: 70 }]).map((p) => p.amount), [30, 70]);
  for (const amount of [-1, Infinity, NaN, true]) assert.throws(() => validatePayments([{ method: "QR", amount }]));
  assert.throws(() => validatePayments([{ method: "FREE", amount: 1 }]));
  assert.throws(() => lineSubtotal(MAX_QUANTITY, 100));
});
