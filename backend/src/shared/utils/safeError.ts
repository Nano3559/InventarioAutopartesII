/** Los errores del ORM pueden incluir SQL, argumentos o credenciales. */
export function safeError(error: unknown): { code: string } {
  const code = error && typeof error === "object" && "code" in error ? String(error.code) : "INTERNAL_ERROR";
  return { code: /^[A-Z][A-Z0-9_]{1,60}$/.test(code) ? code : "INTERNAL_ERROR" };
}
