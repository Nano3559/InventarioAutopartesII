import { createServer, IncomingMessage, Server, ServerResponse } from "node:http";

/**
 * Doble de `ia-service` EXCLUSIVO de tests.
 *
 * El runtime no tiene ningun proveedor simulado: `HttpVisionProvider` siempre
 * habla por HTTP real. Para poder verificar los caminos de error (503 por IA
 * caida, 504 por timeout, 401 por clave incorrecta) los tests levantan este
 * servidor HTTP local en 127.0.0.1 y fijan `VISION_IA_URL` a su URL. Asi se
 * ejercita el mismo codigo de red, cabeceras y multipart que en produccion,
 * incluyendo el `fetch` y el `X-Vision-Key` reales.
 *
 * Este modulo vive en `src/testing/` y NUNCA se importa desde el codigo de
 * la aplicacion.
 */

/** Escenarios que el doble sabe responder, en lugar del antiguo header `x-vision-mock-scenario`. */
export type EscenarioIa =
  | "default"
  | "ninguna"
  | "baja_confianza"
  | "categoria_desconocida"
  | "invalida"
  | "no_autorizado"
  | "caida"
  | "timeout";

export interface FakeIa {
  url: string;
  /** Cambia el comportamiento de la siguiente(s) peticion(es). */
  setEscenario: (escenario: EscenarioIa) => void;
  /** Clave que el doble exige en `X-Vision-Key`; `null` = no exigir clave. */
  setClaveEsperada: (clave: string | null) => void;
  /** Peticiones multipart recibidas (para aserciones de transporte). */
  peticiones: () => Array<{ contentType: string; visionKey: string | null; bytes: number }>;
  close: () => Promise<void>;
}

const DETECCIONES: Record<string, Array<{ categoria: string; confianza: number; boundingBox?: Record<string, number> }>> = {
  default: [{ categoria: "Frenos", confianza: 0.94, boundingBox: { x: 0.2, y: 0.3, width: 0.6, height: 0.5 } }],
  baja_confianza: [{ categoria: "Frenos", confianza: 0.31 }],
  categoria_desconocida: [{ categoria: "Instrumento desconocido XXYZ", confianza: 0.9 }],
  ninguna: [],
};

function leerBody(req: IncomingMessage): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const partes: Buffer[] = [];
    req.on("data", (c: Buffer) => partes.push(c));
    req.on("end", () => resolve(Buffer.concat(partes)));
    req.on("error", reject);
  });
}

function responderJson(res: ServerResponse, status: number, payload: unknown): void {
  const cuerpo = Buffer.from(JSON.stringify(payload));
  res.writeHead(status, { "content-type": "application/json", "content-length": String(cuerpo.length) });
  res.end(cuerpo);
}

export async function startFakeIaServer(claveEsperadaInicial: string | null = null): Promise<FakeIa> {
  let escenario: EscenarioIa = "default";
  let claveEsperada: string | null = claveEsperadaInicial;
  const registro: Array<{ contentType: string; visionKey: string | null; bytes: number }> = [];

  const server: Server = createServer((req, res) => {
    void (async () => {
      const url = req.url ?? "/";

      if (url.startsWith("/vision/health")) {
        return responderJson(res, 200, { status: "ok", modelLoaded: true, model: "fake-yolo", device: "test" });
      }

      if (url !== "/vision/detect" || req.method !== "POST") {
        return responderJson(res, 404, { detail: "not found" });
      }

      const body = await leerBody(req);
      const contentType = String(req.headers["content-type"] ?? "");
      const visionKey = (req.headers["x-vision-key"] as string | undefined) ?? null;
      registro.push({ contentType, visionKey, bytes: body.length });

      // El backend debe enviar multipart con un archivo; si no, no estamos
      // probando el transporte real y el test pasaria por un falso positivo.
      if (!contentType.startsWith("multipart/form-data") || !body.includes("filename=")) {
        return responderJson(res, 400, { detail: "se esperaba multipart/form-data con campo image" });
      }

      if (claveEsperada !== null && visionKey !== claveEsperada) {
        return responderJson(res, 401, { detail: "X-Vision-Key invalido" });
      }

      if (escenario === "caida") {
        return responderJson(res, 500, { detail: "fallo interno del modelo" });
      }

      if (escenario === "timeout") {
        // No responde: el backend debe aplicar su propio timeout y devolver 504.
        return;
      }

      if (escenario === "invalida") {
        // Contrato roto: `detecciones` con elementos sin la forma exigida.
        return responderJson(res, 200, { detectado: true, detecciones: [{ categoria: "Frenos", score: "alto" }] });
      }

      return responderJson(res, 200, {
        detectado: (DETECCIONES[escenario] ?? []).length > 0,
        modelo: "fake-yolo",
        consultadoEn: new Date().toISOString(),
        detecciones: DETECCIONES[escenario] ?? [],
      });
    })().catch(() => {
      if (!res.headersSent) res.writeHead(500);
      res.end();
    });
  });

  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => resolve());
  });

  const address = server.address();
  if (!address || typeof address === "string") {
    throw new Error("TESTING: no se pudo obtener el puerto del doble de ia-service.");
  }

  // `unref` evita que el doble mantenga vivo el proceso de test cuando la suite
  // que lo levanto no lo cierra explicitamente.
  server.unref();

  return {
    url: `http://127.0.0.1:${address.port}`,
    setEscenario: (nuevo) => {
      escenario = nuevo;
    },
    setClaveEsperada: (clave) => {
      claveEsperada = clave;
    },
    peticiones: () => [...registro],
    close: () =>
      new Promise<void>((resolveClose) => {
        if (typeof (server as unknown as { closeAllConnections?: () => void }).closeAllConnections === "function") {
          (server as unknown as { closeAllConnections: () => void }).closeAllConnections();
        }
        server.close(() => resolveClose());
      }),
  };
}