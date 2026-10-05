import { test, describe, before, after, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { startFakeIaServer, FakeIa } from "../../../testing/fakeIaServer";
import { HttpVisionProvider, withVisionTimeout } from "../vision.provider";
import { visionConfig } from "../vision.config";
import { VisionServiceError } from "../vision.errors";

/**
 * El proveedor de vision es SIEMPRE HTTP real: no existe ninguna clase simulada
 * en el runtime. Estos tests lo ejercitan contra un servidor HTTP local real
 * (`src/testing/fakeIaServer`), de modo que se cubren el `fetch`, el multipart,
 * la cabecera `X-Vision-Key` y los caminos de error tal como ocurren en
 * produccion.
 */

const IMAGEN = {
  buffer: Buffer.from("bytes de una foto de una pastilla de freno"),
  mimetype: "image/jpeg",
  originalName: "freno.jpg",
};

let ia: FakeIa;
const provider = new HttpVisionProvider();

before(async () => {
  ia = await startFakeIaServer();
});

// `visionConfig` se construye al importar el modulo, asi que cada test parte de
// una base conocido (IA apuntando al doble local) y ajusta lo que necesite.
beforeEach(() => {
  (visionConfig as { iaUrl: string | null }).iaUrl = ia.url;
  (visionConfig as { iaKey: string | null }).iaKey = null;
  (visionConfig as { timeoutMs: number }).timeoutMs = 8000;
  ia.setEscenario("default");
  ia.setClaveEsperada(null);
});

after(async () => {
  await ia.close();
});

async function esperaVisionServiceError(p: Promise<unknown>): Promise<VisionServiceError> {
  try {
    await p;
  } catch (error) {
    assert.ok(error instanceof VisionServiceError, `se esperaba VisionServiceError, se obtuvo ${String(error)}`);
    return error;
  }
  throw new Error("se esperaba un VisionServiceError y la llamada resolvio");
}

describe("HttpVisionProvider contra un ia-service real de test", () => {
  test("detección válida: devuelve detecciones y proveedor 'http'", async () => {
    const r = await provider.detectar(IMAGEN);
    assert.equal(r.proveedor, "http");
    assert.equal(r.detecciones.length, 1);
    assert.equal(r.detecciones[0].categoria, "Frenos");
    assert.ok((r.detecciones[0].confianza ?? 0) >= 0.9);
    assert.ok(r.detecciones[0].boundingBox, "una detección real debe traer boundingBox");
  });

  test("envía multipart real con el campo image (no una llamada vacía)", async () => {
    await provider.detectar(IMAGEN);
    const ultima = ia.peticiones().at(-1);
    assert.ok(ultima, "el doble deberia haber recibido una petición");
    assert.ok(ultima!.contentType.startsWith("multipart/form-data"));
    assert.ok(ultima!.bytes > 0);
  });

  test("IA que no detecta nada: array de detecciones vacío (no es error)", async () => {
    ia.setEscenario("ninguna");
    const r = await provider.detectar(IMAGEN);
    assert.deepEqual(r.detecciones, []);
  });

  test("baja confianza llega como dato, no como error del proveedor", async () => {
    ia.setEscenario("baja_confianza");
    const r = await provider.detectar(IMAGEN);
    assert.equal(r.detecciones[0].categoria, "Frenos");
    assert.ok(r.detecciones[0].confianza < 0.4);
  });

  test("categoría desconocida llega como dato (el mapeo decide en el service)", async () => {
    ia.setEscenario("categoria_desconocida");
    const r = await provider.detectar(IMAGEN);
    assert.equal(r.detecciones[0].categoria, "Instrumento desconocido XXYZ");
  });

  test("IA caída (500) -> 503 VISION_NO_DISPONIBLE, nunca una detección inventada", async () => {
    ia.setEscenario("caida");
    const err = await esperaVisionServiceError(provider.detectar(IMAGEN));
    assert.equal(err.status, 503);
    assert.equal(err.codigo, "VISION_NO_DISPONIBLE");
  });

  test("IA exige X-Vision-Key y no coincide (401) -> 503 controlado", async () => {
    ia.setClaveEsperada("clave-que-el-backend-no-envia");
    const err = await esperaVisionServiceError(provider.detectar(IMAGEN));
    assert.equal(err.status, 503);
    assert.equal(err.codigo, "VISION_NO_DISPONIBLE");
  });

  test("el backend envía X-Vision-Key cuando está configurado", async () => {
    ia.setClaveEsperada("clave-compartida-de-test");
    (visionConfig as { iaKey: string | null }).iaKey = "clave-compartida-de-test";
    const r = await provider.detectar(IMAGEN);
    assert.equal(r.detecciones.length, 1);
    assert.equal(ia.peticiones().at(-1)?.visionKey, "clave-compartida-de-test");
  });

  test("IA que no responde -> 504 VISION_TIMEOUT por el timeout del propio provider", async () => {
    ia.setEscenario("timeout");
    (visionConfig as { timeoutMs: number }).timeoutMs = 400;
    const err = await esperaVisionServiceError(provider.detectar(IMAGEN));
    assert.equal(err.status, 504);
    assert.equal(err.codigo, "VISION_TIMEOUT");
  });

  test("respuesta con contrato inválido -> 503 VISION_RESPUESTA_INVALIDA", async () => {
    ia.setEscenario("invalida");
    const err = await esperaVisionServiceError(provider.detectar(IMAGEN));
    assert.equal(err.status, 503);
    assert.equal(err.codigo, "VISION_RESPUESTA_INVALIDA");
  });

  test("sin VISION_IA_URL configurada -> 503, no hay ruta a una detección simulada", async () => {
    (visionConfig as { iaUrl: string | null }).iaUrl = null;
    const err = await esperaVisionServiceError(provider.detectar(IMAGEN));
    assert.equal(err.status, 503);
    assert.equal(err.codigo, "VISION_NO_DISPONIBLE");
  });

  test("IA inalcanzable (puerto cerrado) -> 503, no una detección inventada", async () => {
    (visionConfig as { iaUrl: string | null }).iaUrl = "http://127.0.0.1:1";
    const err = await esperaVisionServiceError(provider.detectar(IMAGEN));
    assert.equal(err.status, 503);
    assert.equal(err.codigo, "VISION_NO_DISPONIBLE");
  });
});

describe("withVisionTimeout", () => {
  test("deja pasar el valor si la promesa resuelve a tiempo", async () => {
    const r = await withVisionTimeout(Promise.resolve("ok"), 500);
    assert.equal(r, "ok");
  });

  test("corta con 504 VISION_TIMEOUT si la promesa no llega a tiempo", async () => {
    const lento = new Promise<string>((resolve) => setTimeout(() => resolve("tarde"), 400));
    const err = await esperaVisionServiceError(withVisionTimeout(lento, 100));
    assert.equal(err.status, 504);
    assert.equal(err.codigo, "VISION_TIMEOUT");
  });
});