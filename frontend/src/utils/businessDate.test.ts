import { describe, it, expect } from "vitest";
import { formatBusinessDate, formatBusinessTime } from "./businessDate";
describe("fechas de negocio", () => {
  it("el inicio UTC de febrero todavía pertenece a enero en La Paz", () => {
    expect(formatBusinessDate("2026-02-01T03:30:00Z")).toBe(formatBusinessDate("2026-01-31"));
    expect(formatBusinessTime("2026-02-01T03:30:00Z", { hour: "2-digit", minute: "2-digit", hour12: false })).toBe("23:30");
  });
  it("las claves de calendario no retroceden un día al mostrarse", () => {
    expect(formatBusinessDate("2026-02-01")).toBe(formatBusinessDate("2026-02-01T16:00:00Z"));
  });
});
