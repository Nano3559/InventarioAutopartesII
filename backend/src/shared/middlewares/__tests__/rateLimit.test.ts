import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import express from "express";
import type { Server } from "node:http";
import * as rateLimitModule from "../rateLimit";

/**
 * Límites de tasa (`shared/middlewares/rateLimit`).
 *
 *  - `generalLimiter` sigue siendo 300/15 min por IP y es la ÚNICA protección de
 *   Cuota que queda en /api/vision/... tras eliminar el limiter específico.
 *  - El módulo NO debe exportar limiters de visión: reintroducirlos es lo que
 *    volvió a bloquear la búsqueda por cámara tras unas pocas capturas.
 *  - Los limiters de OCR (legacy) y de login NO se tocan en esta tarea.
 *
 * Cada test levanta su propia app Express con un limiter recién construido, así
 * que el estado del store nunca se comparte entre tests ni con las suites de
 * integración, que corren en otro proceso.
 */

let server: Server;
let baseUrl = "";
let puerto = 0;

/** Levanta una app con el limiter recibido y devuelve el server. */
async function appConLimiter(limiter: express.RequestHandler): Promise<Server> {
  const app = express();
  app.get("/api/health", limiter, (_req, res) => {
    res.json({ status: "ok" });
  });
  return new Promise<Server>((resolve) => {
    const s = app.listen(0, "127.0.0.1", () => resolve(s));
  });
}

async function urlDe(server_: Server): Promise<string> {
  const address = server_.address();
  const puerto_ = typeof address === "object" && address ? address.port : 0;
  return `http://127.0.0.1:${puerto_}/api/health`;
}

before(async () => {
  server = await appConLimiter(rateLimitModule.generalLimiter);
  baseUrl = await urlDe(server);
  puerto = Number(new URL(baseUrl).port);
});

after(async () => {
  if (server) await new Promise<void>((resolve) => server.close(() => resolve()));
});

test("el módulo NO exporta limiters específicos de visión", () => {
  const exportados = Object.keys(rateLimitModule);
  assert.ok(
    !exportados.includes("visionPublicLimiter"),
    "visionPublicLimiter no debe existir: bloqueaba el flujo público tras 5 detecciones",
  );
  assert.ok(
    !exportados.includes("visionAuthenticatedLimiter"),
    "visionAuthenticatedLimiter no debe existir: el flujo interno se cubre con el generalLimiter",
  );
});

test("generalLimiter sigue montado y con límite 300 por ventana", async () => {
  const res = await fetch(baseUrl);
  assert.equal(res.status, 200);
  assert.equal(res.headers.get("ratelimit-limit"), "300", "el límite global sigue siendo 300");
  assert.ok(res.headers.get("ratelimit-policy"), "expone la política de la ventana");
});

test("generalLimiter bloquea con 429 al superar 300 peticiones en la ventana", async () => {
  // Se recorren exactamente 300 más las que ya consumió el test anterior; la primera
  // petición que exceda el presupuesto debe recibir 429, no un 200 silencioso.
  let status429 = 0;
  let ultimoEstado = 0;
  const TOTAL = 320;
  for (let i = 0; i < TOTAL; i++) {
    const res = await fetch(baseUrl);
    ultimoEstado = res.status;
    if (res.status === 429) {
      status429++;
      // El cuerpo del limiter debe traer el mensaje genérico, no el de visión.
      if (status429 === 1) {
        const body: any = await res.json();
        assert.equal(body.status, 429);
        assert.ok(body.message, "mensaje genérico de límite presente");
        assert.ok(
          !String(body.message).includes("visión"),
          "el mensaje del límite global no debe hablar de visión: ya no hay quota de visión",
        );
      }
    }
  }
  assert.equal(ultimoEstado, 429, "la última petición que excede el presupuesto global debe ser 429");
  assert.ok(status429 > 0, "el generalLimiter debe rechazar al superar 300");
});

test("loginLimiter y los limiters de OCR se mantienen sin cambios", () => {
  assert.ok(rateLimitModule.loginLimiter, "loginLimiter sigue exportado");
  assert.ok(rateLimitModule.ocrPublicLimiter, "ocrPublicLimiter (legacy OCR) sigue exportado");
  assert.ok(rateLimitModule.ocrAuthenticatedLimiter, "ocrAuthenticatedLimiter (legacy OCR) sigue exportado");
  assert.ok(puerto > 0, "la app de prueba quedó escuchando en un puerto real");
});
