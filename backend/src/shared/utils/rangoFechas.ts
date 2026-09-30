/**
 * Rango de fechas de negocio para los reportes.
 *
 * PROBLEMA QUE RESUELVE: los listados de ventas/devoluciones/reportes recibían
 * `startDate`/`endDate` como "YYYY-MM-DD" (lo que envía un <input type="date">)
 * y los convertían con `new Date("2026-09-28")` / `end.setHours(23,59,59,999)`.
 * Eso fija el límite del día en la zona horaria del SERVIDOR, que no es la del
 * negocio (America/La_Paz). Consecuencias reales observadas:
 *   - en un servidor en UTC+X, una venta de las 22:30 del último día quedaba
 *     FUERA del reporte de ese mismo día;
 *   - en devoluciones el límite era la medianoche del endDate, así que se perdía
 *     el día final completo para cualquier usuario.
 *
 * La solución es convertir el día de negocio a un intervalo de instantes UTC
 * explícito, independiente de la zona del servidor. Se usa la misma zona que el
 * job de reposición (America/La_Paz) para que reportes y reposición coincidan.
 */

const ZONA_NEGOCIO = "America/La_Paz";

const FORMATO_FECHA = /^\d{4}-\d{2}-\d{2}$/;
const FORMATO_MES = /^\d{4}-(0[1-9]|1[0-2])$/;

/** `Date.UTC` interpreta 0-99 como 1900-1999, así que se exige anio >= 1000. */
const ANIO_MINIMO = 1000;

/** Descompone "YYYY-MM-DD" en { anio, mes, dia } o null si no es una fecha válida. */
function partes(fecha: unknown): { anio: number; mes: number; dia: number } | null {
  if (typeof fecha !== "string") return null;
  const valor = fecha.trim();
  if (!FORMATO_FECHA.test(valor)) return null;
  const [anio, mes, dia] = valor.split("-").map(Number);
  if (anio < ANIO_MINIMO) return null;
  // Rechaza desbordamientos como 2026-02-31 o 2026-13-01.
  const verificado = new Date(Date.UTC(anio, mes - 1, dia));
  if (
    verificado.getUTCFullYear() !== anio ||
    verificado.getUTCMonth() !== mes - 1 ||
    verificado.getUTCDate() !== dia
  )
    return null;
  return { anio, mes, dia };
}

/** Minutos que hay que sumar a UTC para obtener la hora local de `timeZone`. */
function offsetZona(timeZone: string, instante: Date): number {
  const partes = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hour12: false,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(instante);

  const valor = (tipo: Intl.DateTimeFormatPartTypes): number => Number(partes.find((p) => p.type === tipo)?.value ?? "0");
  const hora = valor("hour") % 24;

  const comoUtc = Date.UTC(
    valor("year"),
    valor("month") - 1,
    valor("day"),
    hora,
    valor("minute"),
    valor("second")
  );

  return Math.round((comoUtc - instante.getTime()) / 60000);
}

/**
 * Instante UTC que corresponde a las HH:MM de un día de negocio.
 * Se itera dos veces para resolver correctamente los cambios de hora de verano.
 */
function instanteEnZonaNegocio(
  anio: number,
  mes: number,
  dia: number,
  hora: number,
  minuto: number,
  segundo = 0,
  milisegundo = 0
): Date {
  const naive = Date.UTC(anio, mes - 1, dia, hora, minuto, segundo, milisegundo);
  let instante = new Date(naive - offsetZona(ZONA_NEGOCIO, new Date(naive)) * 60000);
  instante = new Date(naive - offsetZona(ZONA_NEGOCIO, instante) * 60000);
  return instante;
}

/** 00:00:00.000 del día de negocio indicado, como instante UTC. null si la fecha no es válida. */
export function inicioDiaNegocio(fecha: unknown): Date | null {
  const p = partes(fecha);
  if (!p) return null;
  return instanteEnZonaNegocio(p.anio, p.mes, p.dia, 0, 0);
}

/** 23:59:59.999 del día de negocio indicado, como instante UTC. null si la fecha no es válida. */
export function finDiaNegocio(fecha: unknown): Date | null {
  const p = partes(fecha);
  if (!p) return null;
  return instanteEnZonaNegocio(p.anio, p.mes, p.dia, 23, 59, 59, 999);
}

/**
 * Construye el filtro `{ gte, lte }` a partir de startDate/endDate opcionales.
 * - startDate "2026-09-01" -> desde las 00:00:00.000 de ese día de negocio.
 * - endDate   "2026-09-30" -> hasta las 23:59:59.999 de ese día de negocio (incluido).
 * - Una fecha inválida se ignora (no se aplica ese extremo) en vez de romper el reporte.
 */
export function rangoFechasNegocio(
  startDate?: unknown,
  endDate?: unknown
): { gte?: Date; lte?: Date } {
  const rango: { gte?: Date; lte?: Date } = {};
  const gte = inicioDiaNegocio(startDate);
  if (gte) rango.gte = gte;
  const lte = finDiaNegocio(endDate);
  if (lte) rango.lte = lte;
  return rango;
}

/**
 * Rango del mes de negocio completo a partir de "YYYY-MM".
 *
 * Devuelve el intervalo 00:00:00.000 del día 1 hasta 23:59:59.999 del último día
 * del mes, como instantes UTC independientes de la zona del servidor (mismo
 * criterio que rangoFechasNegocio). Devuelve null si el mes no tiene el formato
 * válido, para que el endpoint pueda responder 400 en vez de construir una
 * fecha inválida (NaN -> 500).
 */
export function rangoMesNegocio(mes: unknown): { gte: Date; lte: Date } | null {
  if (typeof mes !== "string") return null;
  const valor = mes.trim();
  if (!FORMATO_MES.test(valor)) return null;
  const [anio, mesNumero] = valor.split("-").map(Number);
  if (anio < ANIO_MINIMO) return null;
  // Día 0 del mes siguiente = último día del mes pedido.
  const ultimoDia = new Date(Date.UTC(anio, mesNumero, 0)).getUTCDate();
  return {
    gte: instanteEnZonaNegocio(anio, mesNumero, 1, 0, 0),
    lte: instanteEnZonaNegocio(anio, mesNumero, ultimoDia, 23, 59, 59, 999),
  };
}

/** Valida un par "YYYY" + "YYYY-MM" (o "MM") del reporte mensual. null si es inválido. */
export function validarMesNegocio(mes: unknown): { anio: number; mes: number } | null {
  const rango = rangoMesNegocio(mes);
  if (!rango) return null;
  const [anio, mesNumero] = String(mes).trim().split("-").map(Number);
  return { anio, mes: mesNumero };
}

export { ZONA_NEGOCIO };
