import { test } from "node:test";
import assert from "node:assert/strict";
import { inicioDiaNegocio, finDiaNegocio, rangoFechasNegocio, rangoMesNegocio, ZONA_NEGOCIO } from "../rangoFechas";

/**
 * El borde de los reportes debe ser el día de NEGOCIO (America/La_Paz, UTC-4),
 * no el día del servidor. Antes se usaba new Date("YYYY-MM-DD") + setHours, que
 * dejaba fuera eventos de la noche del último día.
 */

const iso = (d: Date | null | undefined): string | null => (d ? d.toISOString() : null);

/** Renderiza un instante UTC como fecha/hora local del negocio ("YYYY-MM-DD HH:mm:ss"). */
const fechaLocal = (d: Date): string =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: ZONA_NEGOCIO,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })
    .format(d)
    .replace(",", "");

test("ZONA_NEGOCIO es America/La_Paz", () => {
  assert.equal(ZONA_NEGOCIO, "America/La_Paz");
});

test("inicioDiaNegocio convierte 00:00 de La Paz a las 04:00Z", () => {
  assert.equal(iso(inicioDiaNegocio("2026-09-28")), "2026-09-28T04:00:00.000Z");
});

test("finDiaNegocio incluye todo el último día (23:59:59.999 local = 03:59:59.999Z del día siguiente)", () => {
  assert.equal(iso(finDiaNegocio("2026-09-30")), "2026-10-01T03:59:59.999Z");
});

test("finDiaNegocio es posterior a inicioDiaNegocio del mismo día", () => {
  const inicio = inicioDiaNegocio("2026-02-15")!.getTime();
  const fin = finDiaNegocio("2026-02-15")!.getTime();
  assert.ok(fin > inicio);
  // Duración del día de negocio completo.
  assert.equal(fin - inicio, 24 * 60 * 60 * 1000 - 1);
});

test("rangoFechasNegocio arma gte/lte inclusivos", () => {
  const rango = rangoFechasNegocio("2026-09-01", "2026-09-30");
  assert.equal(iso(rango.gte), "2026-09-01T04:00:00.000Z");
  assert.equal(iso(rango.lte), "2026-10-01T03:59:59.999Z");
});

test("rangoFechasNegocio permite solo un extremo", () => {
  assert.equal(iso(rangoFechasNegocio("2026-09-01", undefined).gte), "2026-09-01T04:00:00.000Z");
  assert.equal(rangoFechasNegocio("2026-09-01", undefined).lte, undefined);
  assert.equal(iso(rangoFechasNegocio(undefined, "2026-09-01").lte), "2026-09-02T03:59:59.999Z");
  assert.equal(rangoFechasNegocio(undefined, "2026-09-01").gte, undefined);
});

test("una fecha inválida se ignora en vez de romper el reporte", () => {
  for (const invalida of ["", "ayer", "2026-13-01", "2026-02-31", "28-09-2026", "2026/09/28"]) {
    assert.equal(inicioDiaNegocio(invalida), null, `debería rechazar ${JSON.stringify(invalida)}`);
    assert.equal(finDiaNegocio(invalida), null, `debería rechazar ${JSON.stringify(invalida)}`);
  }
  // El extremo inválido se omite; el válido sigue aplicándose.
  const rango = rangoFechasNegocio("2026-09-01", "no-es-fecha");
  assert.equal(iso(rango.gte), "2026-09-01T04:00:00.000Z");
  assert.equal(rango.lte, undefined);
});

test("acepta surrounding whitespace sin romper", () => {
  assert.equal(iso(inicioDiaNegocio(" 2026-09-28 ")), "2026-09-28T04:00:00.000Z");
});

test("rangoMesNegocio cubre el mes completo en la zona del negocio", () => {
  const septiembre = rangoMesNegocio("2026-09");
  assert.ok(septiembre);
  assert.equal(iso(septiembre.gte), "2026-09-01T04:00:00.000Z");
  // 30 de septiembre 23:59:59.999 en La Paz = 2026-10-01T03:59:59.999Z
  assert.equal(iso(septiembre.lte), "2026-10-01T03:59:59.999Z");
});

test("rangoMesNegocio respeta la longitud real de cada mes", () => {
  const febrero2028 = rangoMesNegocio("2028-02"); // año bisiesto
  assert.equal(iso(febrero2028!.gte), "2028-02-01T04:00:00.000Z");
  // El último día 23:59:59.999 en La Paz (UTC-4) es 03:59:59.999Z del día siguiente.
  assert.equal(iso(febrero2028!.lte), "2028-03-01T03:59:59.999Z");
  assert.match(fechaLocal(febrero2028!.lte), /^2028-02-29 /, "el último día local debe ser 29/02");

  const febrero2027 = rangoMesNegocio("2027-02");
  assert.equal(iso(febrero2027!.lte), "2027-03-01T03:59:59.999Z");
  assert.match(fechaLocal(febrero2027!.lte), /^2027-02-28 /);

  const diciembre = rangoMesNegocio("2026-12");
  assert.ok(diciembre);
  assert.equal(iso(diciembre.gte), "2026-12-01T04:00:00.000Z");
  assert.equal(iso(diciembre.lte), "2027-01-01T03:59:59.999Z");
  assert.match(fechaLocal(diciembre.lte), /^2026-12-31 /);
});

test("rangoMesNegocio rechaza meses inválidos en vez de construir una fecha NaN", () => {
  for (const invalido of [
    undefined,
    null,
    "",
    "2026",
    "abc",
    "2026-13",
    "2026-00",
    "2026-9",
    "2026-09-01",
    "26-09",
    "2026/09",
    " 2026-09 ",
    "0050-09",
  ]) {
    // Nota: " 2026-09 " sí es válido por diseño (whitespace permitido), se prueba aparte.
    if (invalido === " 2026-09 ") continue;
    assert.equal(rangoMesNegocio(invalido), null, `debería rechazar ${JSON.stringify(invalido)}`);
  }
  assert.ok(rangoMesNegocio(" 2026-09 "), "el whitespace alrededor se tolera");
});

test("rangoMesNegocio ignora el año 0-99 (Date.UTC lo interpretaría como 19xx)", () => {
  assert.equal(rangoMesNegocio("0050-09"), null);
  assert.equal(inicioDiaNegocio("0050-09-28"), null);
});
