import * as XLSX from "xlsx";
import { errorDominio } from "./errorDominio";

export const MAX_IMPORT_ROWS = 5000;
const MAX_EXPANDED = 32 * 1024 * 1024;

/** Comprueba el directorio ZIP antes de que el lector expanda un XLSX. */
function checkArchive(bytes: Buffer): void {
  if (bytes.readUInt16LE(0) !== 0x4b50) return; // XLS antiguo u otro formato que valida el lector.
  let end = -1;
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65557); i--) {
    if (bytes.readUInt32LE(i) === 0x06054b50 && i + 22 + bytes.readUInt16LE(i + 20) === bytes.length) { end = i; break; }
  }
  if (end < 0) throw errorDominio("Archivo Excel comprimido inválido");
  const entries = bytes.readUInt16LE(end + 10), directorySize = bytes.readUInt32LE(end + 12);
  let cursor = bytes.readUInt32LE(end + 16), expanded = 0;
  const directoryEnd = cursor + directorySize;
  if (entries > 1000 || bytes.readUInt16LE(end + 4) || bytes.readUInt16LE(end + 6) || directoryEnd !== end) throw errorDominio("Excel demasiado complejo o formato ZIP no admitido");
  for (let i = 0; i < entries; i++) {
    if (cursor + 46 > end || bytes.readUInt32LE(cursor) !== 0x02014b50) throw errorDominio("Directorio Excel inválido");
    expanded += bytes.readUInt32LE(cursor + 24);
    if (expanded > MAX_EXPANDED) throw errorDominio("Excel excede 32 MB descomprimidos. Divida el archivo");
    cursor += 46 + bytes.readUInt16LE(cursor + 28) + bytes.readUInt16LE(cursor + 30) + bytes.readUInt16LE(cursor + 32);
    if (cursor > end) throw errorDominio("Directorio Excel inválido");
  }
  if (cursor !== directoryEnd) throw errorDominio("Directorio Excel inconsistente");
}

export function readImportWorkbook(bytes: Buffer): XLSX.WorkBook {
  if (bytes.length < 4 || bytes.length > 10 * 1024 * 1024) throw errorDominio("Excel vacío o mayor a 10 MB");
  checkArchive(bytes);
  let workbook: XLSX.WorkBook;
  try { workbook = XLSX.read(bytes, { type: "buffer", sheets: 0, sheetRows: MAX_IMPORT_ROWS + 2, cellHTML: false, cellStyles: false }); }
  catch { throw errorDominio("No se pudo leer Excel. Compruebe formato y contenido"); }
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  if (!sheet) throw errorDominio("El archivo no contiene una primera hoja válida");
  const ref = sheet["!fullref"] || sheet["!ref"];
  if (ref) {
    const range = XLSX.utils.decode_range(ref);
    if (range.e.r >= MAX_IMPORT_ROWS + 1 || range.e.c >= 100) throw errorDominio(`Excel admite hasta ${MAX_IMPORT_ROWS} filas de datos y 100 columnas. Divida el archivo`);
  }
  return workbook;
}
