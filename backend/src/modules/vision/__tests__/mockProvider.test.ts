import { test } from "node:test";
import assert from "node:assert/strict";
import { MockVisionProvider } from "../vision.provider";
import { VisionServiceError } from "../vision.errors";

const provider = new MockVisionProvider();
const IMAGEN = { buffer: Buffer.from("foto simulada de una pastilla de freno"), mimetype: "image/jpeg", originalName: "freno.jpg" };

test("mock default devuelve detección 'Frenos' con confianza alta y proveedor trazable", async () => {
  const r = await provider.detectar(IMAGEN);
  assert.equal(r.proveedor, "mock");
  assert.ok(r.detecciones.length > 0);
  assert.equal(r.detecciones[0].categoria, "Frenos");
  assert.ok(r.detecciones[0].confianza >= 0.9);
  assert.ok(r.detecciones[0].boundingBox);
});

test("mock 'ninguna' devuelve array vacío (no clasificada)", async () => {
  const r = await provider.detectar(IMAGEN, "ninguna");
  assert.deepEqual(r.detecciones, []);
});

test("mock 'baja_confianza' devuelve confianza baja", async () => {
  const r = await provider.detectar(IMAGEN, "baja_confianza");
  assert.ok(r.detecciones[0].confianza < 0.4);
});

test("mock 'error' lanza VISION_NO_DISPONIBLE", async () => {
  await assert.rejects(
    () => provider.detectar(IMAGEN, "error"),
    (err) => err instanceof VisionServiceError && err.status === 503 && err.codigo === "VISION_NO_DISPONIBLE"
  );
});

test("escenario desconocido cae a default sin romperse", async () => {
  const r = await provider.detectar(IMAGEN, "no-existe");
  assert.equal(r.detecciones[0].categoria, "Frenos");
});