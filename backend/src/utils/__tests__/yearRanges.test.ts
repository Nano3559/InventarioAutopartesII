import { test } from "node:test";
import assert from "node:assert/strict";
import {
  parseYearRange,
  parseMultipleYearRanges,
  expandYearRanges,
  yearMatchesRanges,
  yearRangesOverlap,
} from "../yearRanges";

test("rango cerrado '13-15' produce 2013-2015", () => {
  assert.deepEqual(expandYearRanges([{ start: 2013, end: 2015 }]), [2013, 2014, 2015]);
});

test("año corto '13-' determinista para años idénticos", () => {
  const expanded = expandYearRanges([{ start: 2013, end: null }]);
  const sorted = [...expanded].sort((a, b) => a - b);
  assert.equal(sorted[0], 2013);
  assert.ok(sorted.length >= 1);
});

test("'13-15/16-18' múltiples rangos", () => {
  const ranges = parseMultipleYearRanges("13-15/16-18");
  assert.equal(ranges.length, 2);
  const expanded = expandYearRanges(ranges);
  assert.deepEqual(expanded, [2013, 2014, 2015, 2016, 2017, 2018]);
});

test("yearMatchesRanges con rango abierto incluye el año actual", () => {
  assert.ok(yearMatchesRanges(new Date().getFullYear(), "10-"));
});

test("yearMatchesRanges excluye año fuera de rango", () => {
  assert.ok(!yearMatchesRanges(2000, "13-15"));
});

test("parseYearRange de 2 dígitos normaliza a 2000+/1900+", () => {
  assert.deepEqual(parseYearRange("13"), { start: 2013, end: 2013 });
  assert.deepEqual(parseYearRange("90-99"), { start: 1990, end: 1999 });
});

test("range with end < start keeps expand sorted", () => {
  const expanded = expandYearRanges([{ start: 2015, end: 2013 }]);
  assert.deepEqual(expanded, [2013, 2014, 2015]);
});

test("yearRangesOverlap con rangos solapados", () => {
  assert.ok(yearRangesOverlap("13-15", "14-16"));
  assert.ok(yearRangesOverlap("14-16", "13-15"));
  assert.ok(yearRangesOverlap("13", "13-15"));
  assert.ok(yearRangesOverlap("13-15", "13"));
});

test("yearRangesOverlap con rangos disjuntos", () => {
  assert.ok(!yearRangesOverlap("13-15", "16-18"));
  assert.ok(!yearRangesOverlap("16-18", "13-15"));
});

test("yearRangesOverlap con rangos multi", () => {
  assert.ok(yearRangesOverlap("13-15/20-22", "21"));
  assert.ok(!yearRangesOverlap("13-15/20-22", "23"));
});