export const BUSINESS_TIME_ZONE = "America/La_Paz";
export function formatBusinessDate(value: string | Date, options: Intl.DateTimeFormatOptions = {}): string {
  const date = typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T12:00:00-04:00`) : new Date(value);
  return date.toLocaleDateString("es-BO", { ...options, timeZone: BUSINESS_TIME_ZONE });
}
export function formatBusinessTime(value: string | Date, options: Intl.DateTimeFormatOptions = {}): string {
  return new Date(value).toLocaleTimeString("es-BO", { ...options, timeZone: BUSINESS_TIME_ZONE });
}

export function formatBusinessDateTime(value: string | Date): string {
  return new Date(value).toLocaleString("es-BO", { timeZone: BUSINESS_TIME_ZONE });
}
