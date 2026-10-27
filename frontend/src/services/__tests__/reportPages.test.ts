import { describe, it, expect, vi } from "vitest";
import { collectReportPages } from "../reportPages";
describe("reporte paginado", () => {
  it("conserva filtros y snapshot en un recorrido finito aunque crezca pages", async () => {
    const get = vi.fn().mockResolvedValueOnce({ data: { sales: [{ id: 2 }], pagination: { pages: 2 }, snapshotMaxId: 2, summary: { count: 2 } } }).mockResolvedValueOnce({ data: { sales: [{ id: 1 }], pagination: { pages: 300 } } });
    const result = await collectReportPages(get, new URLSearchParams({ startDate: "2026-09-30", brand: "Toyota" }));
    expect(result.sales.map(s=>s.id)).toEqual([2,1]);
    expect(get).toHaveBeenCalledTimes(2);
    expect(get.mock.calls[1][0]).toContain("snapshotMaxId=2");
    expect(get.mock.calls[1][0]).toContain("startDate=2026-09-30");
  });
  it("rechaza duplicados y una cantidad de páginas inválida", async () => {
    const duplicate = vi.fn().mockResolvedValue({ data: { sales: [{ id: 1 }], pagination: { pages: 2 } } });
    await expect(collectReportPages(duplicate, new URLSearchParams())).rejects.toThrow(/cambió/);
    await expect(collectReportPages(async()=>({data:{sales:[],pagination:{pages:Infinity}}}),new URLSearchParams())).rejects.toThrow(/inválida/);
  });
});
