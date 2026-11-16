/** No expone SQL ni altera datos para ocultar un esquema incompatible. */
export function dashboardFailure(error: unknown) {
  const code = error && typeof error === "object" && "code" in error ? String(error.code) : "";
  if (["P2021", "P2022"].includes(code)) {
    return { status: 503, code: "DASHBOARD_SCHEMA_UNAVAILABLE", message: "El dashboard no está disponible porque la estructura de datos no coincide con esta versión del sistema. Se requiere revisión técnica. No se modificaron datos." };
  }
  if (["P1000", "P1001", "P1002", "P1008", "P1017", "P2024"].includes(code)) {
    return { status: 503, code: "DASHBOARD_DATABASE_UNAVAILABLE", message: "No se pudo conectar con los datos del dashboard. Intente nuevamente o contacte al administrador." };
  }
  return { status: 500, code: "DASHBOARD_UNAVAILABLE", message: "No se pudo cargar el dashboard. Contacte al administrador si el problema continúa." };
}
