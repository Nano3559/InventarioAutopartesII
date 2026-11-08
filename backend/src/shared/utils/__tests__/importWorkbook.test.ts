import { test } from "node:test";
import assert from "node:assert/strict";
import * as XLSX from "xlsx";
import { readImportWorkbook, MAX_IMPORT_ROWS } from "../importWorkbook";
const excel = (rows: unknown[][]) => {
  const book = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(book, XLSX.utils.aoa_to_sheet(rows), "Factura");
  return XLSX.write(book, { type: "buffer", bookType: "xlsx", compression: true }) as Buffer;
};
test("importa la primera hoja válida sin alterar sus cantidades", () => {
  const book = readImportWorkbook(excel([["codigo", "cantidad"], ["P-1", 3]]));
  assert.equal(book.Sheets.Factura.B2.v, 3);
});
test("rechaza filas excesivas sin aceptar una importación truncada", () => {
  assert.throws(() => readImportWorkbook(excel(Array.from({ length: MAX_IMPORT_ROWS + 2 }, (_, i) => [i]))), /Divida el archivo/);
});
test("rechaza tamaño expandido excesivo antes de descomprimir", () => {
  const bytes = Buffer.alloc(80);
  bytes.writeUInt32LE(0x04034b50, 0);
  bytes.writeUInt32LE(0x02014b50, 12);
  bytes.writeUInt32LE(33 * 1024 * 1024, 36);
  bytes.writeUInt32LE(0x06054b50, 58);
  bytes.writeUInt16LE(1, 68);
  bytes.writeUInt32LE(46, 70);
  bytes.writeUInt32LE(12, 74);
  assert.throws(() => readImportWorkbook(bytes), /descomprimidos/);
});
