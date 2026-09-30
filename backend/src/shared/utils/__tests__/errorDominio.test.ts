import { test } from "node:test";
import assert from "node:assert/strict";
import { ErrorDominio, esErrorDominio, errorDominio } from "../errorDominio";

/**
 * `sales` y `wholesale` respondían antes 400 con `error.message` para CUALQUIER error,
 * así que un TypeError o un fallo de Prisma devolvía 400 y exponía el mensaje interno.
 * Ahora solo ErrorDominio produce 400 con texto propio; el resto va al 500 genérico.
 */

test("un error de dominio conserva su mensaje y se reconoce", () => {
  const err = errorDominio("Stock insuficiente");
  assert.equal(err.message, "Stock insuficiente");
  assert.equal(err.name, "ErrorDominio");
  assert.equal(esErrorDominio(err), true);
  assert.ok(err instanceof Error);
});

test("los errores internos NO se confunden con errores de dominio", () => {
  assert.equal(esErrorDominio(new Error("connect ECONNREFUSED 10.0.0.5:5432")), false);
  assert.equal(esErrorDominio(new TypeError("Cannot read properties of undefined")), false);
  assert.equal(esErrorDominio({ message: "Stock insuficiente" }), false, "un objeto con la misma forma no cuenta");
  assert.equal(esErrorDominio("texto"), false);
  assert.equal(esErrorDominio(undefined), false);
  assert.equal(esErrorDominio(null), false);
});

test("un error con mensaje de dominio pero clase equivocada se trata como interno", () => {
  // Clasificar por el texto del mensaje filtraría detalles internos: cualquier error
  // cuya cadena contuviera esas palabras se convertiría en un 400 con texto del sistema.
  class Impostor extends Error {}
  const err = new Impostor("Stock insuficiente para X. Disponible: 3, solicitado: 9");
  assert.equal(esErrorDominio(err), false);
});

test("un error de Prisma con mensaje de negocio tampoco pasa como dominio", () => {
  const prismaError: any = new Error("Unique constraint failed on the fields: (`productId`)");
  prismaError.code = "P2002";
  assert.equal(esErrorDominio(prismaError), false);
});

test("ErrorDominio se distingue de un Error normal por identidad de clase", () => {
  assert.notEqual(ErrorDominio.prototype, Error.prototype);
  assert.ok(new ErrorDominio("x") instanceof ErrorDominio);
  assert.ok(!(new Error("x") instanceof ErrorDominio));
});
