/** Límite finito, orden estable y snapshot evitan seguir un total que crece al vender. */
export async function collectReportPages(get: (url: string) => Promise<{ data: any }>, params: URLSearchParams) {
  const query = new URLSearchParams(params);
  query.set("limit", "500");
  const first = await get(`/reports/sales?${query}`);
  const pages = Number(first.data.pagination?.pages ?? 1);
  if (!Number.isInteger(pages) || pages < 0 || pages > 10000) throw new Error("Cantidad de páginas de reporte inválida");
  if (first.data.snapshotMaxId !== undefined) query.set("snapshotMaxId", String(first.data.snapshotMaxId));
  const sales = [...first.data.sales];
  const ids = new Set(sales.map((s: { id: number }) => s.id));
  for (let page = 2; page <= pages; page++) {
    query.set("page", String(page));
    const next = await get(`/reports/sales?${query}`);
    for (const sale of next.data.sales) {
      if (ids.has(sale.id)) throw new Error("El reporte cambió durante la lectura. Vuelva a consultar");
      ids.add(sale.id);
      sales.push(sale);
    }
  }
  return { sales, summary: first.data.summary };
}
