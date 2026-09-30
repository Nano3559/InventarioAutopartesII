import { test } from "node:test";
import assert from "node:assert/strict";
import { precioVentaNormal, subtotalLinea, totalCarrito } from "../utils/precioVenta.ts";

/**
 * El TPV móvil fallaba con 400 en TODA venta porque mandaba el total calculado con
 * price1 (mayorista) mientras el backend cobra price2 (minorista) y valida que el pago
 * coincida. Estos tests fijan la regla minorista compartida con el backend.
 *
 * Caso real de la semilla: FRN-001 tiene price1=250, price2=280.
 */

test("usa price2 como precio minorista cuando está definido", () => {
  assert.equal(precioVentaNormal({ price1: 250, price2: 280 }), 280);
});

test("cae a price1 cuando price2 no está definido o es cero", () => {
  assert.equal(precioVentaNormal({ price1: 250 }), 250);
  assert.equal(precioVentaNormal({ price1: 250, price2: null }), 250);
  assert.equal(precioVentaNormal({ price1: 250, price2: 0 }), 250);
});

test("acepta price2 y price1 como string (los llegan así desde la API)", () => {
  assert.equal(precioVentaNormal({ price1: "250", price2: "280" }), 280);
  assert.equal(precioVentaNormal({ price1: "250", price2: "0" }), 250);
});

test("el subtotal de la línea usa el precio minorista, no el mayorista", () => {
  assert.equal(subtotalLinea({ price1: 250, price2: 280 }, 3), 840);
});

test("el total del carrito suma los subtotales minoristas", () => {
  const total = totalCarrito([
    { producto: { price1: 250, price2: 280 }, cantidad: 2 },
    { producto: { price1: 100, price2: 0 }, cantidad: 1 },
  ]);
  assert.equal(total, 660);
});

test("el total redondea a 2 decimales como espera la validación del backend", () => {
  const total = totalCarrito([{ producto: { price1: 33.333, price2: 66.666 }, cantidad: 3 }]);
  assert.equal(total, 200);
  assert.equal(Number(total.toFixed(2)), total);
});

test("un carrito vacío vale 0", () => {
  assert.equal(totalCarrito([]), 0);
});

test("el caso de la venta que fallaba: price1 != price2 produce el importe que el backend cobra", () => {
  // 2 x 280 = 560. Con price1 (250) el TPV mandaba 500 y el backend respondía 400.
  const total = totalCarrito([{ producto: { price1: 250, price2: 280 }, cantidad: 2 }]);
  assert.equal(total, 560);
  assert.notEqual(total, 500);
});
