import assert from "node:assert/strict";
import { test, describe } from "node:test";
import { resolverVisionModo } from "../vision.config";

/**
 * El proveedor de vision es unico: siempre HTTP real contra ia-service. No hay
 * `VISION_MODE` ni ninguna forma de activar detecciones simuladas, asi que estos
 * tests fijan la regla que importa: con URL se usa el modelo real y sin URL el
 * endpoint falla cerrado con 503 en cualquier entorno.
 */
describe("resolucion del proveedor de vision (solo HTTP real)", () => {
  test("el modo siempre es http: no existe modo simulado", () => {
    for (const env of [{}, { VISION_IA_URL: "http://ia:8000" }, { NODE_ENV: "production" }]) {
      assert.equal(resolverVisionModo(env).modo, "http");
    }
  });

  test("VISION_IA_URL presente: usa el modelo real y no requiere nada mas", () => {
    const r = resolverVisionModo({ VISION_IA_URL: "http://ia:8000" });
    assert.equal(r.modo, "http");
    assert.equal(r.requiereIA, false);
  });

  test("sin VISION_IA_URL: requiereIA (503), tambien en desarrollo", () => {
    const r = resolverVisionModo({});
    assert.equal(r.requiereIA, true, "sin URL debe responder 503, no simular");
    assert.equal(r.produccion, false);
  });

  test("sin VISION_IA_URL en produccion: falla cerrado, nunca una deteccion simulada", () => {
    const r = resolverVisionModo({ NODE_ENV: "production" });
    assert.equal(r.modo, "http");
    assert.equal(r.requiereIA, true);
    assert.equal(r.produccion, true);
  });

  test("produccion con VISION_IA_URL usa el modelo real", () => {
    const r = resolverVisionModo({ NODE_ENV: "production", VISION_IA_URL: "http://ia:8000" });
    assert.equal(r.modo, "http");
    assert.equal(r.requiereIA, false);
    assert.equal(r.produccion, true);
  });

  test("NODE_ENV=Production (mayusculas) tambien cuenta como produccion", () => {
    assert.equal(resolverVisionModo({ NODE_ENV: "Production" }).produccion, true);
  });

  test("test/development nunca se consideran produccion", () => {
    for (const env of ["test", "development", "", "staging"]) {
      const r = resolverVisionModo({ NODE_ENV: env });
      assert.equal(r.produccion, false, `NODE_ENV=${env} no debe ser produccion`);
      assert.equal(r.requiereIA, true, "sin URL sigue fallando cerrado con 503");
    }
  });

  test("una VISION_IA_URL solo con espacios se trata como ausente", () => {
    assert.equal(resolverVisionModo({ VISION_IA_URL: "   " }).requiereIA, true);
  });
});