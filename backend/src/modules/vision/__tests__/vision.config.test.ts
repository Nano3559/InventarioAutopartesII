import assert from "node:assert/strict";
import { test, describe } from "node:test";
import { resolverVisionMode } from "../vision.config";

describe("resolucion explicita del modo de vision", () => {
  test("desarrollo sin variables cae en mock", () => {
    const r = resolverVisionMode({});
    assert.equal(r.modo, "mock");
    assert.equal(r.requiereIA, false);
    assert.equal(r.produccion, false);
  });

  test("desarrollo con VISION_IA_URL usa el modelo real", () => {
    const r = resolverVisionMode({ VISION_IA_URL: "http://ia:8000" });
    assert.equal(r.modo, "http");
    assert.equal(r.requiereIA, false);
  });

  test("VISION_MODE=http explicito sin URL NUNCA degrada a mock", () => {
    const r = resolverVisionMode({ VISION_MODE: "http" });
    assert.equal(r.modo, "http");
    assert.equal(r.requiereIA, true, "sin URL el endpoint debe responder 503, no simular");
  });

  test("VISION_MODE=remote es alias de http", () => {
    assert.equal(resolverVisionMode({ VISION_MODE: "remote" }).modo, "http");
    assert.equal(resolverVisionMode({ VISION_MODE: "REMOTE" }).modo, "http");
  });

  test("VISION_MODE=mock explicito manda incluso en produccion", () => {
    const r = resolverVisionMode({ NODE_ENV: "production", VISION_MODE: "mock" });
    assert.equal(r.modo, "mock");
    assert.equal(r.produccion, true);
  });

  test("PRODUCCION sin VISION_IA_URL nunca activa mock: queda remoto sin URL (503)", () => {
    const r = resolverVisionMode({ NODE_ENV: "production" });
    assert.equal(r.modo, "http");
    assert.equal(r.requiereIA, true, "produccion sin IA configurada debe fallar cerrado");
  });

  test("PRODUCCION con VISION_IA_URL usa el modelo real", () => {
    const r = resolverVisionMode({ NODE_ENV: "production", VISION_IA_URL: "http://ia:8000" });
    assert.equal(r.modo, "http");
    assert.equal(r.requiereIA, false);
  });

  test("NODE_ENV=Production (mayusculas) tambien cuenta como produccion", () => {
    assert.equal(resolverVisionMode({ NODE_ENV: "Production" }).modo, "http");
  });

  test("VISION_MODE con valor desconocido se ignora y se aplica la regla por URL", () => {
    assert.equal(resolverVisionMode({ VISION_MODE: "raro" }).modo, "mock");
    assert.equal(resolverVisionMode({ VISION_MODE: "raro", VISION_IA_URL: "http://ia:8000" }).modo, "http");
  });

  test("test/development nunca se consideran produccion", () => {
    for (const env of ["test", "development", "", "staging"]) {
      const r = resolverVisionMode({ NODE_ENV: env });
      assert.equal(r.produccion, false, `NODE_ENV=${env} no debe ser produccion`);
      assert.equal(r.modo, "mock");
    }
  });
});
