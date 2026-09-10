import { existsSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import type { Server } from "node:http";
import type { Express } from "express";

/**
 * Utilidades compartidas para los tests de integración (*.itest.ts).
 *
 * La base de datos de prueba SIEMPRE debe ser local (127.0.0.1/localhost).
 * Nunca se ejecutan pruebas contra bases remotas (Neon, Railway, etc.): si la
 * DATABASE_URL no apunta a un host de loopback se aborta la ejecución.
 */

const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost", "::1"]);
const RESERVED_JWT = new Set(["secret", "secret-key"]);

export function assertLocalTestUrl(url: string): void {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    throw new Error("TESTING: DATABASE_URL no es una URL válida.");
  }
  if (parsed.protocol !== "postgresql:" && parsed.protocol !== "postgres:") {
    throw new Error(`TESTING: protocolo no soportado en DATABASE_URL: ${parsed.protocol}`);
  }
  if (!LOCAL_HOSTS.has(parsed.hostname)) {
    throw new Error(
      `TESTING: DATABASE_URL debe apuntar a una base local de prueba (127.0.0.1/localhost). ` +
        `Se recibió el host "${parsed.hostname}". Nunca se ejecutan pruebas contra bases remotas como Neon.`
    );
  }
}

// Conexiones por pool de Prisma: suficiente para los tests de concurrencia
// (R6.10/R6.12 hacen 2 peticiones paralelas por cliente) y acotado para no
// superar max_connections del clúster local con varios procesos de test en paralelo.
const TEST_CONNECTION_LIMIT = 3;

function resolveDatabaseUrl(): string {
  let url: string;
  if (process.env.DATABASE_URL) {
    assertLocalTestUrl(process.env.DATABASE_URL);
    url = process.env.DATABASE_URL;
  } else {
    const clusterFile = path.join(tmpdir(), "opencode", "pgtest", "dburl.txt");
    if (!existsSync(clusterFile)) {
      throw new Error(
        `TESTING: no hay DATABASE_URL en el entorno ni clúster local en ${clusterFile}. ` +
          "Exporte DATABASE_URL y JWT_SECRET de prueba antes de ejecutar npm run test:integration."
      );
    }
    url = readFileSync(clusterFile, "utf8").trim();
    assertLocalTestUrl(url);
  }
  const parsed = new URL(url);
  parsed.searchParams.set("connection_limit", String(TEST_CONNECTION_LIMIT));
  return parsed.toString();
}

/**
 * Configura el entorno de test (DATABASE_URL y JWT_SECRET) ANTES de que se
 * importe app.ts (que a su vez importa ./config y los routers). Se invoca al
 * importar este módulo; por eso en cada archivo *.itest.ts este es el primer
 * import. Los módulos _real_ app/router se importan de forma diferida.
 */
export function resolveTestEnv(): void {
  // Siempre con override: el entorno de test jamás debe firmar con el secreto real.
  process.env.JWT_SECRET = "itest-secret-2f8c1a9d5b7e3f406572";
  process.env.DATABASE_URL = resolveDatabaseUrl();
  if (process.env.JWT_SECRET.length < 16 || RESERVED_JWT.has(process.env.JWT_SECRET)) {
    throw new Error("TESTING: JWT_SECRET de prueba inválido (mínimo 16 caracteres y no reservado).");
  }
}

resolveTestEnv();

let appSingleton: Express | undefined;

async function getApp(): Promise<Express> {
  if (!appSingleton) {
    const { default: app } = await import("../app");
    appSingleton = app;
  }
  return appSingleton;
}

export interface TestServer {
  baseUrl: string;
  close: () => Promise<void>;
}

export async function startTestServer(): Promise<TestServer> {
  const app = await getApp();
  const server: Server = await new Promise((resolve, reject) => {
    const srv = app.listen(0, "127.0.0.1", () => resolve(srv));
    srv.on("error", reject);
  });
  const address = server.address();
  if (!address || typeof address === "string") {
    throw new Error("TESTING: no se pudo obtener el puerto del servidor.");
  }
  return {
    baseUrl: `http://127.0.0.1:${address.port}`,
    close: () =>
      new Promise<void>((resolveClose) => {
        // Cierra sockets keep-alive (undici) para que server.close() resuelva de forma
        // determinista; de lo contrario el proceso del test quedaría vivo tras los tests.
        if (typeof (server as any).closeAllConnections === "function") {
          server.closeAllConnections();
        }
        server.close(() => resolveClose());
      }),
  };
}

export function jsonHeaders(token?: string): Record<string, string> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (token) headers.authorization = `Bearer ${token}`;
  return headers;
}

export async function postJson(baseUrl: string, pathname: string, body: unknown, token?: string): Promise<Response> {
  return fetch(`${baseUrl}${pathname}`, {
    method: "POST",
    headers: jsonHeaders(token),
    body: JSON.stringify(body),
  });
}

export async function loginAndGetToken(baseUrl: string, email: string, password: string): Promise<string> {
  const res = await postJson(baseUrl, "/api/auth/login", { email, password });
  if (res.status !== 200) {
    throw new Error(`TESTING: el login falló con ${res.status}: ${await res.text()}`);
  }
  const body: any = await res.json();
  if (!body.token || typeof body.token !== "string") {
    throw new Error("TESTING: login válido no devolvió un token.");
  }
  return body.token;
}