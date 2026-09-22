import { test } from "node:test";
import assert from "node:assert/strict";
import {
  esVisionDetection,
  esBoundingBoxValido,
  validarRespuestaVision,
} from "../contract";

test("esBoundingBoxValido acepta caja correcta", () => {
  assert.ok(esBoundingBoxValido({ x: 0.2, y: 0.3, width: 0.6, height: 0.5 }));
});

test("esBoundingBoxValido rechaza cajas con campos faltantes o no numéricos", () => {
  assert.ok(!esBoundingBoxValido({ x: 0.2, y: 0.3, width: 0.6 }));
  assert.ok(!esBoundingBoxValido({ x: "0", y: 0.3, width: 0.6, height: 0.5 }));
  assert.ok(!esBoundingBoxValido(null));
});

test("esVisionDetection valida categoria y confianza en [0,1]", () => {
  assert.ok(esVisionDetection({ categoria: "Frenos", confianza: 0.94 }));
  assert.ok(esVisionDetection({ categoria: "Frenos", confianza: 0 }));
  assert.ok(esVisionDetection({ categoria: "Frenos", confianza: 1 }));
  assert.ok(!esVisionDetection({ categoria: "Frenos", confianza: 1.1 }));
  assert.ok(!esVisionDetection({ categoria: "Frenos", confianza: NaN }));
  assert.ok(!esVisionDetection({ categoria: "", confianza: 0.9 }));
  assert.ok(!esVisionDetection({ categoria: 42, confianza: 0.9 }));
});

test("esVisionDetection valida boundingBox cuando existe", () => {
  assert.ok(esVisionDetection({ categoria: "Frenos", confianza: 0.8, boundingBox: { x: 0, y: 0, width: 1, height: 1 } }));
  assert.ok(esVisionDetection({ categoria: "Frenos", confianza: 0.8, boundingBox: null }));
  assert.ok(!esVisionDetection({ categoria: "Frenos", confianza: 0.8, boundingBox: { x: 3 } }));
});

test("validarRespuestaVision marca inválida una respuesta que no es array", () => {
  assert.deepEqual(validarRespuestaVision(null), { valida: false, detecciones: [] });
  assert.deepEqual(validarRespuestaVision("frenos"), { valida: false, detecciones: [] });
});

test("validarRespuestaVision marca inválida si algún ítem no cumple el contrato", () => {
  const resultado = validarRespuestaVision([{ categoria: "Frenos", confianza: 0.94 }, { categoria: "X", confianza: 25 }]);
  assert.equal(resultado.valida, false);
  assert.equal(resultado.detecciones.length, 1, "Conserva las detecciones válidas ya parseadas");
});

test("validarRespuestaVision acepta un array válido completo", () => {
  const detecciones = [
    { categoria: "Frenos", confianza: 0.94 },
    { categoria: "Faro", confianza: 0.6, boundingBox: { x: 0, y: 0, width: 1, height: 1 } },
  ];
  const resultado = validarRespuestaVision(detecciones);
  assert.equal(resultado.valida, true);
  assert.equal(resultado.detecciones.length, 2);
  assert.deepEqual(resultado.detecciones, detecciones);
});

test("validarRespuestaVision acepta array vacío (implica no clasificada)", () => {
  const resultado = validarRespuestaVision([]);
  assert.equal(resultado.valida, true);
  assert.equal(resultado.detecciones.length, 0);
});