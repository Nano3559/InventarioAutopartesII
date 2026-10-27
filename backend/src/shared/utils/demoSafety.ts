/** Los generadores demo nunca se ejecutan en producción, remotos ni bases operativas. */
export function assertDemoDatabase(url: string | undefined, env: NodeJS.ProcessEnv = process.env): void {
  if (env.NODE_ENV === "production" || env.ALLOW_DEMO_DATA !== "1" || !url) throw new Error("Demo bloqueada. Requiere entorno local, ALLOW_DEMO_DATA=1 y una base terminada en _demo");
  let parsed: URL;
  try { parsed = new URL(url); } catch { throw new Error("DATABASE_URL inválida para demo"); }
  if (!["postgresql:", "postgres:"].includes(parsed.protocol) || !["127.0.0.1", "localhost", "[::1]"].includes(parsed.hostname) || !/^\/[a-zA-Z0-9_]+_demo$/.test(parsed.pathname)) {
    throw new Error("Demo bloqueada. Solo se permiten bases locales dedicadas terminadas en _demo");
  }
}
