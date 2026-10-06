import { test } from "node:test";
import assert from "node:assert/strict";
import { CLASES_VISUALES, coincideClaseVisual, resolverClaseVisual } from "../claseVisual";

/** Etiquetas canónicas que ia-service emite en `deteccion.categoria`. */
const ETIQUETAS_IA_SERVICE: Array<[string, string]> = [
  ["pastilla de freno", "brake_pad"],
  ["disco de freno", "brake_rotor"],
  ["caliper", "brake_caliper"],
  ["alternador", "alternator"],
  ["filtro de aceite", "oil_filter"],
  ["filtro de aire", "air_filter"],
  ["radiador", "radiator"],
  ["faro", "headlight"],
];

test("invariante: son exactamente las 8 clases reales del modelo, sin duplicados", () => {
  assert.equal(CLASES_VISUALES.length, 8, "el checkpoint V3 tiene nc: 8");
  assert.equal(new Set(CLASES_VISUALES.map((c) => c.id)).size, 8, "ids únicos");
  assert.equal(new Set(CLASES_VISUALES.map((c) => c.etiqueta)).size, 8, "etiquetas únicas");
  for (const clase of CLASES_VISUALES) {
    assert.ok(clase.terminos.length > 0, `${clase.id} debe tener términos`);
    for (const termino of clase.terminos) {
      assert.equal(termino, termino.toLowerCase().trim(), `término en minúsculas: ${termino}`);
      assert.ok(!/[A-ZÁÉÍÓÚÑ]/.test(termino), `sin mayúsculas/acentos en: ${termino}`);
    }
  }
});

test("resolverClaseVisual resuelve cada etiqueta canónica de ia-service", () => {
  for (const [etiqueta, id] of ETIQUETAS_IA_SERVICE) {
    const clase = resolverClaseVisual(etiqueta);
    assert.ok(clase, `la etiqueta "${etiqueta}" debe resolver a una clase real`);
    assert.equal(clase.id, id, `la etiqueta "${etiqueta}" debe mapear a ${id}`);
  }
});

test("resolverClaseVisual tolera plural, mayúsculas y acentos de la detección", () => {
  assert.equal(resolverClaseVisual("Pastillas de Freno")?.id, "brake_pad");
  assert.equal(resolverClaseVisual("DISCO DE FRENO")?.id, "brake_rotor");
  assert.equal(resolverClaseVisual("FARO")?.id, "headlight");
});

test("resolverClaseVisual acepta el id en inglés como respaldo", () => {
  for (const [etiqueta, id] of ETIQUETAS_IA_SERVICE) {
    assert.equal(resolverClaseVisual(id)?.id, id, `el id "${id}" debe resolver a sí mismo`);
    assert.ok(resolverClaseVisual(etiqueta));
  }
});

test("resolverClaseVisual NO inventa clases: desconocido y vacío dan null", () => {
  assert.equal(resolverClaseVisual("transmision"), null, "no es una clase del modelo");
  assert.equal(resolverClaseVisual("bujia"), null, "no es una clase del modelo");
  assert.equal(resolverClaseVisual(""), null);
  assert.equal(resolverClaseVisual(null), null);
  assert.equal(resolverClaseVisual(undefined), null);
  assert.equal(resolverClaseVisual("   "), null);
});

test("coincideClaseVisual detecta el nombre de la pieza correcta", () => {
  const alternador = resolverClaseVisual("alternador");
  assert.ok(coincideClaseVisual("Alternador Toyota Hilux 2.4", alternador));
  assert.ok(coincideClaseVisual("ALTERNADOR DENSO 12V", alternador));
  assert.ok(!coincideClaseVisual("Foco Halógeno H4", alternador));
  assert.ok(!coincideClaseVisual("Sensor de Oxígeno", alternador));
  assert.ok(!coincideClaseVisual("Marcha de Arranque", alternador));
});

test("coincideClaseVisual respeta límites de palabra: no cruza dentro de una palabra", () => {
  const faro = resolverClaseVisual("faro");
  assert.ok(coincideClaseVisual("Faro delantero halógeno", faro));
  assert.ok(coincideClaseVisual("Faro LED H4", faro));
  assert.ok(!coincideClaseVisual("Faroled genérico", faro), "un cruce dentro de la palabra no cuenta");
});

test("coincideClaseVisual tolera puntuación y orden distinto en el nombre", () => {
  const pastilla = resolverClaseVisual("pastilla de freno");
  assert.ok(coincideClaseVisual("Juego de pastillas de freno delanteras", pastilla));
  assert.ok(coincideClaseVisual("Pastillas delanteras Toyota", pastilla), "palabra principal basta");
  assert.ok(coincideClaseVisual("Filtro de aceite, 15W40", resolverClaseVisual("filtro de aceite")));
});

test("coincideClaseVisual no mezcla categorías afines", () => {
  const aceite = resolverClaseVisual("filtro de aceite");
  const aire = resolverClaseVisual("filtro de aire");
  assert.ok(!coincideClaseVisual("Filtro de aire K&N", aceite));
  assert.ok(!coincideClaseVisual("Filtro de aceite Mann", aire));
  assert.ok(coincideClaseVisual("Filtro de aire K&N", aire));
});

test("coincideClaseVisual devuelve false si no hay clase resoluble (prioridad 7)", () => {
  assert.ok(!coincideClaseVisual("Alternador Toyota", null));
  assert.ok(!coincideClaseVisual("", resolverClaseVisual("alternador")));
  assert.ok(!coincideClaseVisual(null, resolverClaseVisual("alternador")));
  assert.ok(!coincideClaseVisual(undefined, resolverClaseVisual("alternador")));
});
