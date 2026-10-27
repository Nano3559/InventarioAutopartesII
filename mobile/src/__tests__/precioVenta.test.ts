import { test } from "node:test";
import assert from "node:assert/strict";
import { precioVentaNormal, totalCarrito } from "../utils/precioVenta.ts";
test("POR MENOR y POR MAYOR corresponden al nivel elegido", () => {
  assert.equal(precioVentaNormal({ price1: 250, wholesalePrice: 200 }, "POR_MENOR"), 250);
  assert.equal(precioVentaNormal({ price1: "250", wholesalePrice: "200" }, "POR_MAYOR"), 200);
});
test("no hay fallback de un nivel no configurado", () => {
  assert.throws(() => precioVentaNormal({ price1: 250, wholesalePrice: 0 }, "POR_MAYOR"));
});
test("carrito suma niveles y redondea precios antes del subtotal", () => {
  assert.equal(totalCarrito([{ producto: { price1: 250, wholesalePrice: 200 }, cantidad: 2, priceMode: "POR_MAYOR" }, { producto: { price1: 100 }, cantidad: 1 }]), 500);
  assert.equal(totalCarrito([{ producto: { price1: 33.333, wholesalePrice: 22.226 }, cantidad: 3, priceMode: "POR_MAYOR" }]), 66.69);
  assert.equal(totalCarrito([]), 0);
});
