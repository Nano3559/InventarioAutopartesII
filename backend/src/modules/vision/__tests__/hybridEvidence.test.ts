import { test } from "node:test";
import assert from "node:assert/strict";
import {
  PESOS_CODIGO,
  evaluarEvidenciasCodigo,
  evaluarYRanquear,
  extraerCodigos,
  extraerTokensSignificativos,
  normalizarCodigo,
  resumirEvidencias,
} from "../hybridEvidence";

test("normalizarCodigo ignora guiones, espacios y mayúsculas", () => {
  assert.equal(normalizarCodigo("90915-yzzd2"), "90915YZZD2");
  assert.equal(normalizarCodigo("1K0 615 301"), "1K0615301");
  assert.equal(normalizarCodigo("LF-15D"), "LF15D");
});

test("extraerCodigos toma tokens con letras y dígitos, no palabras sueltas", () => {
  const codigos = extraerCodigos("FILTRO 90915-YZZD2 TOYOTA HILUX");
  assert.ok(codigos.includes("90915YZZD2"), "debe normalizar el código con guion");
  assert.ok(!codigos.includes("TOYOTA"), "palabras sin dígitos no son códigos");
  assert.ok(!codigos.includes("HILUX"), "palabras sin dígitos no son códigos");
});

test("extraerCodigos no inventa códigos: texto vacío o sin nada parecido", () => {
  assert.deepEqual(extraerCodigos(""), []);
  assert.deepEqual(extraerCodigos(null), []);
  assert.deepEqual(extraerCodigos("solo palabras sin numeros"), []);
});

test("extraerCodigos reensambla códigos troceados por espacios", () => {
  const codigos = extraerCodigos("REF 1K0 615 301 ORIGINAL");
  assert.ok(codigos.includes("1K0615301"), "debe unir el código troceado");
});

test("regresión: una palabra sueta junto al código NO se pega al código", () => {
  // Sin este filtro el trío "FILTRO 90915 YZZD2" generaba el código inexistente
  // "FILTRO90915YZZD2" y "90915 YZZD2 TOYOTA" generaba "90915YZZD2TOYOTA",
  // produciendo coincidencias falsas en el ranking.
  const codigos = extraerCodigos("FILTRO 90915-YZZD2 TOYOTA HILUX");
  assert.ok(!codigos.some((c) => c.includes("TOYOTA") || c.includes("HILUX") || c.includes("FILTRO")), `no debe containir palabras: ${codigos.join(",")}`);
  assert.ok(codigos.includes("90915YZZD2"), "el código real debe seguir detectándose");
});

test("extraerCodigos deduplica el mismo código con y sin separadores", () => {
  const codigos = extraerCodigos("90915-YZZD2 90915YZZD2");
  assert.equal(codigos.filter((c) => c === "90915YZZD2").length, 1);
});

test("sin códigos detectados: score 0 y sin evidencias", () => {
  const r = evaluarEvidenciasCodigo({ oemCode: "90915YZZD2", factoryCode: null, itemCode: "SKU-1" }, []);
  assert.equal(r.score, 0);
  assert.deepEqual(r.evidencias, []);
});

test("coincidencia exacta de oemCode pesa más que factoryCode e itemCode", () => {
  const producto = { oemCode: "90915-YZZD2", factoryCode: "ABC-999", itemCode: "SKU-1" };

  const oem = evaluarEvidenciasCodigo(producto, ["90915YZZD2"]);
  const factory = evaluarEvidenciasCodigo(producto, ["ABC999"]);
  const item = evaluarEvidenciasCodigo(producto, ["SKU1"]);

  assert.equal(oem.score, PESOS_CODIGO.oemCode);
  assert.equal(factory.score, PESOS_CODIGO.factoryCode);
  assert.equal(item.score, PESOS_CODIGO.itemCode);
  assert.ok(oem.score > factory.score, "oemCode debe valer más que factoryCode");
  assert.ok(factory.score > item.score, "factoryCode debe valer más que itemCode");
});

test("coincidencia parcial vale menos que la exacta y se marca como parcial", () => {
  const producto = { oemCode: "90915YZZD2", factoryCode: null, itemCode: "SKU-1" };
  const r = evaluarEvidenciasCodigo(producto, ["90915Y"]);
  assert.equal(r.evidencias.length, 1);
  assert.equal(r.evidencias[0].tipo, "parcial");
  assert.equal(r.evidencias[0].peso, PESOS_CODIGO.parcial);
  assert.ok(r.score < PESOS_CODIGO.oemCode, "la parcial no puede valer como la exacta");
});

test("coincidencia parcial demasiado corta se ignora (evita ruido)", () => {
  const producto = { oemCode: "90915YZZD2", factoryCode: null, itemCode: "SKU-1" };
  const r = evaluarEvidenciasCodigo(producto, ["909"]);
  assert.equal(r.score, 0);
});

test("campos null se omiten sin romper la evaluación", () => {
  const r = evaluarEvidenciasCodigo({ oemCode: null, factoryCode: null, itemCode: "SKU-1" }, ["SKU1"]);
  assert.equal(r.score, PESOS_CODIGO.itemCode);
  assert.equal(r.evidencias.length, 1);
  assert.equal(r.evidencias[0].campo, "itemCode");
});

test("un mismo campo no acumula evidencia repetida por variantes del código", () => {
  const producto = { oemCode: "90915-YZZD2", factoryCode: null, itemCode: "SKU-1" };
  const r = evaluarEvidenciasCodigo(producto, ["90915YZZD2", "90915-YZZD2"]);
  assert.equal(r.evidencias.length, 1, "el mismo campo no debe contar dos veces");
});

test("un candidato con dos campos coincidentes acumula y ordena por peso", () => {
  const producto = { oemCode: "90915YZZD2", factoryCode: "ABC999", itemCode: "SKU-1" };
  const r = evaluarEvidenciasCodigo(producto, ["ABC999", "90915YZZD2"]);
  assert.equal(r.score, PESOS_CODIGO.oemCode + PESOS_CODIGO.factoryCode);
  assert.equal(r.evidencias[0].campo, "oemCode", "la evidencia de mayor peso va primero");
});

test("las evidencias son trazables: nunca verifican compatibilidad", () => {
  const producto = { oemCode: "90915-YZZD2", factoryCode: null, itemCode: "SKU-1" };
  const r = evaluarEvidenciasCodigo(producto, ["90915YZZD2"]);
  const evidencia = r.evidencias[0];
  assert.equal(evidencia.codigoProducto, "90915-YZZD2");
  assert.equal(evidencia.codigoDetectado, "90915YZZD2");
  assert.equal(evidencia.tipo, "exacta");
  assert.ok(!("verificada" in evidencia), "la evidencia no debe llevar un flag de compatibilidad");
  assert.match(resumirEvidencias(r.evidencias), /oemCode 90915-YZZD2 \(exacta\)/);
});

test("resumirEvidencias es explícito cuando no hay coincidencias", () => {
  assert.match(resumirEvidencias([]), /Sin códigos/);
});

test("tokens de texto descartan ruido y un solo carácter", () => {
  const tokens = extraerTokensSignificativos("FILTRO de aceite BOSCH 90915 YZZD2 imagen jpeg");
  assert.ok(tokens.includes("FILTRO"));
  assert.ok(tokens.includes("ACEITE"));
  assert.ok(tokens.includes("BOSCH"));
  assert.ok(!tokens.includes("IMG"), "el ruido debe filtrarse");
  assert.ok(!tokens.some((t) => t.length < 3), "no debe haber tokens de 1-2 caracteres");
});

test("tokens de texto vacío no rompen", () => {
  assert.deepEqual(extraerTokensSignificativos(""), []);
  assert.deepEqual(extraerTokensSignificativos(null), []);
});
// --- Ranking híbrido (evaluarYRanquear) ---

const PRODUCTO = (oem: string | null, item: string) => ({
  itemCode: item,
  oemCode: oem,
  factoryCode: null,
  nombre: `Producto ${item}`,
});

test("ranking: la evidencia de código sube al candidato con oemCode coincidente", () => {
  const r = evaluarYRanquear(
    [
      { producto: PRODUCTO(null, "SKU-A"), compatibilidad: { verificada: false, score: 0 } },
      { producto: PRODUCTO("90915YZZD2", "SKU-B"), compatibilidad: { verificada: false, score: 0 } },
    ],
    ["90915YZZD2"]
  );
  assert.equal(r[0].producto.itemCode, "SKU-B", "el candidato con el código leído debe ir primero");
  assert.equal(r[0].evidencia.score, PESOS_CODIGO.oemCode);
  assert.equal(r[1].evidencia.score, 0);
});

test("ranking: la compatibilidad verificada SIEMPRE gana al código exacto", () => {
  // Regla de negocio crítica: el código identifica la pieza, no prueba que sea la
  // correcta para ese vehículo. No debe desplazar a un producto verificado.
  const r = evaluarYRanquear(
    [
      { producto: PRODUCTO("90915YZZD2", "SKU-CODIGO"), compatibilidad: { verificada: false, score: 5 } },
      { producto: PRODUCTO(null, "SKU-VERIFICADO"), compatibilidad: { verificada: true, score: 10 } },
    ],
    ["90915YZZD2"]
  );
  assert.equal(r[0].producto.itemCode, "SKU-VERIFICADO", "verificado debe ir antes que el código exacto");
  assert.equal(r[1].producto.itemCode, "SKU-CODIGO");
  assert.equal(r[1].evidencia.score, PESOS_CODIGO.oemCode, "el candidato con código conserva su evidencia");
});

test("ranking: a igual compatibilidad verificada, gana mayor evidencia de código", () => {
  const r = evaluarYRanquear(
    [
      { producto: PRODUCTO(null, "SKU-SIN"), compatibilidad: { verificada: false, score: 5 } },
      { producto: PRODUCTO("90915YZZD2", "SKU-CON"), compatibilidad: { verificada: false, score: 5 } },
    ],
    ["90915YZZD2"]
  );
  assert.equal(r[0].producto.itemCode, "SKU-CON");
});

test("ranking: sin códigos, conserva el orden por compatibilidad", () => {
  const r = evaluarYRanquear(
    [
      { producto: PRODUCTO(null, "SKU-BAJO"), compatibilidad: { verificada: false, score: 1 } },
      { producto: PRODUCTO(null, "SKU-ALTO"), compatibilidad: { verificada: false, score: 9 } },
    ],
    []
  );
  assert.equal(r[0].producto.itemCode, "SKU-ALTO");
  assert.ok(r.every((c) => c.evidencia.score === 0));
});

test("ranking: no reordena la entrada del llamador (sin mutación)", () => {
  const entrada = [
    { producto: PRODUCTO(null, "SKU-1"), compatibilidad: { verificada: false, score: 0 } },
    { producto: PRODUCTO("90915YZZD2", "SKU-2"), compatibilidad: { verificada: false, score: 0 } },
  ];
  const copia = entrada.map((e) => ({ ...e }));
  evaluarYRanquear(entrada, ["90915YZZD2"]);
  assert.deepEqual(entrada, copia, "evaluarYRanquear no debe mutar el array recibido");
});
