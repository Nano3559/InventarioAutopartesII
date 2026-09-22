import { test } from "node:test";
import assert from "node:assert/strict";
import { mapearCategoria, CATEGORY_MAP } from "../categoryMapping";
import { normalizarTexto, coincidenTextos } from "../normalize";

const CATALOGO = ["Frenos", "Motor", "Carrocería", "Eléctrico", "Filtros", "Suspensión", "Transmisión"];

test("identidad exacta: detección igual a categoría existente", () => {
  assert.equal(mapearCategoria(CATALOGO, "Frenos"), "Frenos");
  assert.equal(mapearCategoria(CATALOGO, "Motor"), "Motor");
});

test("coincidencia sin acentos ni mayúsculas", () => {
  assert.equal(mapearCategoria(CATALOGO, "CARROCERÍA"), "Carrocería");
  assert.equal(mapearCategoria(CATALOGO, "carrocería"), "Carrocería");
  assert.equal(mapearCategoria(CATALOGO, "Eléctrico"), "Eléctrico");
});

test("alias: 'faro' resuelve a Carrocería", () => {
  assert.equal(mapearCategoria(CATALOGO, "Faro"), "Carrocería");
  assert.equal(mapearCategoria(CATALOGO, "faro delantero"), "Carrocería");
});

test("alias por palabra contenida: 'pastilla de freno' → Frenos", () => {
  assert.equal(mapearCategoria(CATALOGO, "pastillas de freno"), "Frenos");
  assert.equal(mapearCategoria(CATALOGO, "Disco de freno"), "Frenos");
});

test("clase desconocida → null (no inventa categorías)", () => {
  assert.equal(mapearCategoria(CATALOGO, "Repuesto raro XXYZ"), null);
  assert.equal(mapearCategoria(CATALOGO, ""), null);
});

test("alias con destino inexistente en el catálogo → null", () => {
  assert.equal(mapearCategoria(["Motor", "Eléctrico"], "Faro"), null);
});

test("CATEGORY_MAP no tiene claves vacías ni duplicadas (invariantes)", () => {
  const keys = Object.keys(CATEGORY_MAP);
  for (const key of keys) assert.ok(normalizarTexto(key).length > 0, `clave vacía: '${key}'`);
  assert.equal(new Set(keys).size, keys.length, "claves duplicadas en CATEGORY_MAP");
  assert.ok(keys.length >= 20, "el mapa debe cubrir las piezas solicitadas");
});

test("coincidenTextos: comparación sin acentos y por subcadena", () => {
  assert.ok(coincidenTextos("Toyota", "toyota"));
  assert.ok(coincidenTextos("Hilux", "hilux"));
  assert.ok(coincidenTextos("Frenos", "frenos"));
  assert.ok(!coincidenTextos("Toyota", "Chevrolet"));
});