import { test } from "node:test";
import assert from "node:assert/strict";
import {
  PESOS_CODIGO,
  evaluarEvidenciasCodigo,
  evaluarYRanquear,
  extraerCodigos,
  extraerTokensSignificativos,
  nivelCoincidenciaDe,
  normalizarCodigo,
  resumirEvidencias,
} from "../hybridEvidence";
import { resolverClaseVisual } from "../claseVisual";

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

// --- Ranking V2: prioridades estrictas ---

const CANDIDATO = (name: string, itemCode: string, oemCode: string | null = null, factoryCode: string | null = null) => ({
  name,
  itemCode,
  oemCode,
  factoryCode,
});

const SIN_COMPAT = { verificada: false, score: 0 };

test("V2 exactaPorCampo registra qué campo coincidió exactamente", () => {
  const producto = CANDIDATO("Alternador", "SKU-1", "90915-YZZD2", "ABC-999");
  const soloOem = evaluarEvidenciasCodigo(producto, ["90915YZZD2"]);
  assert.deepEqual(soloOem.exactaPorCampo, { oem: true, factory: false, item: false });

  const dos = evaluarEvidenciasCodigo(producto, ["90915YZZD2", "ABC999"]);
  assert.deepEqual(dos.exactaPorCampo, { oem: true, factory: true, item: false });

  const parcial = evaluarEvidenciasCodigo(producto, ["90915Y"]);
  assert.deepEqual(parcial.exactaPorCampo, { oem: false, factory: false, item: false }, "la parcial no es exacta");

  const ninguno = evaluarEvidenciasCodigo(producto, []);
  assert.deepEqual(ninguno.exactaPorCampo, { oem: false, factory: false, item: false });
});

test("V2: sin vehículo y sin OCR, la clase YOLO separa al Alternador del resto de Eléctrico", () => {
  // Caso real reportado: la categoría "Eléctrico" devolvía Foco, Marcha, Sensor y
  // Módulo antes que el Alternador, porque todos empataban en score 0.
  const clase = resolverClaseVisual("alternador");
  const candidatos = [
    CANDIDATO("Foco Halógeno H4 12V", "SKU-FOCO"),
    CANDIDATO("Foco LED H7 24V", "SKU-FOCO2"),
    CANDIDATO("Alternador Toyota Hilux 100A", "SKU-ALT"),
    CANDIDATO("Marcha de Arranque 1.8kW", "SKU-MARCHA"),
    CANDIDATO("Módulo de Encendido", "SKU-MOD"),
    CANDIDATO("Sensor MAP Bosch", "SKU-MAP"),
    CANDIDATO("Sensor de Oxígeno", "SKU-O2"),
  ].map((producto) => ({ producto, compatibilidad: SIN_COMPAT }));

  const r = evaluarYRanquear(candidatos, [], { clase });

  assert.equal(r[0].producto.name, "Alternador Toyota Hilux 100A", "la pieza detectada debe ir primera");
  assert.equal(r[0].evidencia.claseCoincide, true);
  assert.equal(r[0].evidencia.score, 0, "sin OCR no hay score de código");
  assert.equal(nivelCoincidenciaDe(r[0].evidencia), "media", "coincidencia por tipo, no por categoría");
  assert.ok(
    r.slice(1).every((c) => !c.evidencia.claseCoincide),
    "los demás solo pueden estar por categoría"
  );
  assert.ok(r.slice(1).every((c) => nivelCoincidenciaDe(c.evidencia) === "categoria"));
});

test("V2: la prioridad 5 no le gana a las prioridades 2-4 (código exacto)", () => {
  const clase = resolverClaseVisual("alternador");
  const r = evaluarYRanquear(
    [
      { producto: CANDIDATO("Alternador Genérico", "SKU-ALT"), compatibilidad: SIN_COMPAT },
      { producto: CANDIDATO("Módulo de Encendido", "SKU-MOD", "90915YZZD2"), compatibilidad: SIN_COMPAT },
    ],
    ["90915YZZD2"],
    { clase }
  );
  assert.equal(r[0].producto.itemCode, "SKU-MOD", "el OEM exacto (prioridad 2) va antes que la clase (5)");
  assert.equal(nivelCoincidenciaDe(r[0].evidencia), "fuerte");
});

test("V2: prioridad 2 > 3 > 4 estricta, aunque el puntaje total sea menor", () => {
  // OEM solo (10) le gana a fábrica+item (14): la jerarquía es estricta, no se promedia.
  const r = evaluarYRanquear(
    [
      { producto: CANDIDATO("A", "SKU-ITEM", null, "FAB-1"), compatibilidad: SIN_COMPAT },
      { producto: CANDIDATO("B", "SKU-OEM", "90915YZZD2"), compatibilidad: SIN_COMPAT },
    ],
    ["90915YZZD2", "FAB1", "SKUITEM"],
    {}
  );
  assert.equal(r[0].producto.itemCode, "SKU-OEM", "prioridad 2 (OEM exacto) por encima de 3 y 4");
  assert.equal(r[1].producto.itemCode, "SKU-ITEM");
  assert.ok(
    r[1].evidencia.score > r[0].evidencia.score,
    "el perdedor acumula más puntos (fábrica+item) pero pierde la jerarquía"
  );
});

test("V2: fábrica exacto (3) le gana a itemCode exacto (4)", () => {
  const r = evaluarYRanquear(
    [
      { producto: CANDIDATO("A", "SKU-ITEM", null, null), compatibilidad: SIN_COMPAT },
      { producto: CANDIDATO("B", "SKU-OTHER", null, "FAB-1"), compatibilidad: SIN_COMPAT },
    ],
    ["FAB1", "SKUITEM"],
    {}
  );
  assert.equal(r[0].producto.itemCode, "SKU-OTHER", "prioridad 3 por encima de la 4");
});

test("V2: la compatibilidad verificada (prioridad 1) sigue ganándolo todo", () => {
  const clase = resolverClaseVisual("alternador");
  const r = evaluarYRanquear(
    [
      { producto: CANDIDATO("Alternador Toyota", "SKU-ALT", "90915YZZD2"), compatibilidad: SIN_COMPAT },
      { producto: CANDIDATO("Foco Halógeno", "SKU-FOCO"), compatibilidad: { verificada: true, score: 12 } },
    ],
    ["90915YZZD2"],
    { clase }
  );
  assert.equal(r[0].producto.itemCode, "SKU-FOCO", "verificada desplaza al OEM exacto y a la clase");
});

test("V2: la coincidencia de clase separa empatados pero no desplaza a la compatibilidad", () => {
  const clase = resolverClaseVisual("faro");
  const r = evaluarYRanquear(
    [
      { producto: CANDIDATO("Faro LED H7", "SKU-FARO"), compatibilidad: SIN_COMPAT },
      { producto: CANDIDATO("Parachoques delantero", "SKU-PAR"), compatibilidad: { verificada: false, score: 3 } },
    ],
    [],
    { clase }
  );
  assert.equal(r[0].producto.itemCode, "SKU-FARO", "prioridad 5 por encima de la 6");
});

test("V2 sin contexto de clase mantiene el comportamiento anterior (prioridad 7 residual)", () => {
  const r = evaluarYRanquear(
    [
      { producto: CANDIDATO("Foco Halógeno", "SKU-FOCO"), compatibilidad: SIN_COMPAT },
      { producto: CANDIDATO("Alternador Toyota", "SKU-ALT"), compatibilidad: SIN_COMPAT },
    ],
    [],
    {}
  );
  assert.ok(r.every((c) => !c.evidencia.claseCoincide), "sin clase no puede haber prioridad 5");
  assert.ok(r.every((c) => nivelCoincidenciaDe(c.evidencia) === "categoria"));
  assert.deepEqual(
    r.map((c) => c.producto.itemCode),
    ["SKU-FOCO", "SKU-ALT"],
    "el orden estable de entrada se conserva"
  );
});

test("nivelCoincidenciaDe clasifica fuerte / media / categoria", () => {
  const exacta = evaluarEvidenciasCodigo(CANDIDATO("A", "SKU-1", "90915YZZD2"), ["90915YZZD2"]);
  assert.equal(nivelCoincidenciaDe(exacta), "fuerte");

  const parcial = evaluarEvidenciasCodigo(CANDIDATO("A", "SKU-1", "90915YZZD2"), ["90915Y"]);
  assert.equal(nivelCoincidenciaDe(parcial), "media");

  const porClase = evaluarEvidenciasCodigo(
    CANDIDATO("Alternador Toyota", "SKU-1"),
    [],
    resolverClaseVisual("alternador")
  );
  assert.equal(nivelCoincidenciaDe(porClase), "media");
  assert.equal(porClase.claseCoincide, true);
  assert.equal(porClase.score, 0);

  const soloCategoria = evaluarEvidenciasCodigo(CANDIDATO("Sensor MAP", "SKU-1"), []);
  assert.equal(nivelCoincidenciaDe(soloCategoria), "categoria");
  assert.equal(soloCategoria.claseCoincide, false);
});
