export interface Pagination {
  page: number;
  limit: number;
  skip: number;
  take: number;
}

/**
 * Sanea page/limit de strings de query. Nunca devuelve NaN, negativos ni
 * decimales: page >= 1 (entero), limit entre 1 y maxLimit (entero). Evita
 * 500s silenciosos con query strings inválidos (?page=abc, ?limit=0, ?page=2.5).
 */
export function parsePagination(page: unknown, limit: unknown, maxLimit = 100): Pagination {
  const parsedPage = Math.floor(Math.max(1, Number(page) || 1));
  const take = Math.floor(Math.min(maxLimit, Math.max(1, Number(limit) || 20)));
  return { page: parsedPage, limit: take, skip: (parsedPage - 1) * take, take };
}