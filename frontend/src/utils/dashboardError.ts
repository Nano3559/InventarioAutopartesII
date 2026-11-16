export function dashboardError(error: unknown): string {
  const response = (error as { response?: { status?: number; data?: { code?: string } }; code?: string })?.response;
  if (response?.data?.code === "DASHBOARD_SCHEMA_UNAVAILABLE") return "La estructura de datos no coincide con esta versión del sistema. El dashboard requiere revisión técnica. Puede acceder a los demás módulos desde el menú.";
  if (response?.status === 403) return "Su usuario no tiene permiso para consultar el dashboard.";
  if (response?.status === 401) return "La sesión venció. Inicie sesión nuevamente.";
  if (response?.status === 503) return "Los datos del dashboard no están disponibles temporalmente. Puede acceder a los demás módulos desde el menú.";
  if (!response) return "No se pudo contactar con el backend. Compruebe que está iniciado y que la dirección de la API corresponde a RepuestoPro.";
  return "No se pudieron cargar los datos del dashboard. Intente nuevamente. Si continúa, solicite una revisión técnica.";
}
