import { test } from "node:test";
import assert from "node:assert/strict";
import { evaluarCompatibilidadProducto, BaseDatosInternaProvider } from "../compatibility";

const FRENO_HILUX = { brand: "Toyota", model: "Hilux", year: "2020-2024" };

test("sin vehículo: no verificada, sin inventar coincidencias", () => {
  const r = evaluarCompatibilidadProducto(FRENO_HILUX, null);
  assert.equal(r.verificada, false);
  assert.equal(r.score, 0);
  assert.deepEqual(r.coincidencias, []);
  assert.match(r.nota, /no verificada/);
});

test("coincidencia total: marca+modelo+año", () => {
  const r = evaluarCompatibilidadProducto(FRENO_HILUX, { marca: "Toyota", modelo: "Hilux", anio: "2020" });
  assert.equal(r.verificada, true);
  assert.deepEqual(r.coincidencias.sort(), ["anio", "marca", "modelo"].sort());
  assert.equal(r.score, 10);
});

test("año en rango del producto pero modelo distinto: no verificada", () => {
  const r = evaluarCompatibilidadProducto(FRENO_HILUX, { marca: "Toyota", modelo: "Corolla", anio: "2022" });
  assert.equal(r.verificada, false);
  assert.deepEqual(r.coincidencias, ["marca", "anio"]);
  assert.equal(r.score, 5);
});

test("marca sin acentos y plural/curvatura en comparación", () => {
  const r = evaluarCompatibilidadProducto(FRENO_HILUX, { marca: "toyota", modelo: "hilux", anio: "2020-2024" });
  assert.equal(r.verificada, true);
});

test("vehículo con solo marca no puede verificarse (faltan campos pedidos)", () => {
  const r = evaluarCompatibilidadProducto(FRENO_HILUX, { marca: "Toyota" });
  assert.equal(r.verificada, false);
  assert.deepEqual(r.coincidencias, ["marca"]);
});

test("ranking del proveedor: verificados primero por score", async () => {
  const provider = new BaseDatosInternaProvider();
  const candidatos = [
    { brand: "Toyota", model: "Corolla", year: "2018" },
    { brand: "Toyota", model: "Hilux", year: "2020-2024" },
    { brand: "Chevrolet", model: "Aveo", year: "2015" },
  ];
  const evaluados = await provider.evaluarCandidatos(candidatos, { marca: "Toyota", modelo: "Hilux", anio: "2020" });
  assert.equal(evaluados[0].candidato.model, "Hilux");
  assert.equal(evaluados[0].compatibilidad.verificada, true);
  assert.equal(new Set(evaluados.map((e) => e.compatibilidad.verificada)).size >= 2, true);
});

test("proveedor expone tipo trazable", () => {
  const provider = new BaseDatosInternaProvider();
  assert.equal(provider.tipo, "base_datos_interna");
});