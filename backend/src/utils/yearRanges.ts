/**
 * Lógica de rangos de años:
 * - "13-15" → incluye 2013, 2014, 2015
 * - "13" → corresponde únicamente a 2013
 * - "13-" → corresponde a 2013 en adelante
 * - Múltiples rangos separados por "/": "13-15/16-18"
 */

export interface YearRange {
  start: number;
  end: number | null;
}

export function parseYearRange(range: string): YearRange | null {
  const trimmed = range.trim();
  if (!trimmed) return null;

  if (trimmed.endsWith("-")) {
    const start = parseInt(trimmed.replace("-", ""), 10);
    if (isNaN(start)) return null;
    return { start, end: null };
  }

  if (trimmed.includes("-")) {
    const [startStr, endStr] = trimmed.split("-");
    const start = parseInt(startStr, 10);
    const end = parseInt(endStr, 10);
    if (isNaN(start) || isNaN(end)) return null;
    return { start, end };
  }

  const single = parseInt(trimmed, 10);
  if (isNaN(single)) return null;
  return { start: single, end: single };
}

export function parseMultipleYearRanges(value: string): YearRange[] {
  return value
    .split("/")
    .map((part) => parseYearRange(part.trim()))
    .filter((r): r is YearRange => r !== null);
}

export function expandYearRanges(ranges: YearRange[]): number[] {
  const years = new Set<number>();
  for (const range of ranges) {
    if (range.end === null) {
      years.add(range.start);
    } else {
      const min = Math.min(range.start, range.end);
      const max = Math.max(range.start, range.end);
      for (let y = min; y <= max; y++) {
        years.add(y);
      }
    }
  }
  return [...years].sort((a, b) => a - b);
}

export function yearMatchesRanges(searchYear: number, storedYear: string): boolean {
  const ranges = parseMultipleYearRanges(storedYear);
  const expanded = expandYearRanges(ranges);
  return expanded.includes(searchYear);
}

export function validateYearRanges(value: string): string | null {
  if (!value.trim()) return null;

  const parts = value.split("/");
  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;

    const range = parseYearRange(trimmed);
    if (!range) {
      return `Rango de año inválido: "${trimmed}". Use formato "13", "13-15" o "13-"`;
    }

    if (range.end !== null && range.start > range.end) {
      return `Rango inválido: "${trimmed}". El año inicial (${range.start}) no puede ser mayor al final (${range.end})`;
    }
  }

  return null;
}

export function getYearRangeLabel(range: YearRange): string {
  if (range.end === null) return `${range.start}-`;
  if (range.start === range.end) return `${range.start}`;
  return `${range.start}-${range.end}`;
}
