import path from "path";
import { createWorker } from "tesseract.js";
import type { Worker as TesseractWorker } from "tesseract.js";
import { logger } from "./logger";

/**
 * OCR compartido del backend (Tesseract).
 *
 * Antes vivía dentro de `modules/products/searchImage.service.ts`. Se extrajo aquí
 * para que la búsqueda por imagen (texto) y la búsqueda por visión (híbrido
 * YOLO + OCR) reutilicen **un único worker**: dos instancias cargarían dos copias
 * del modelo de Tesseract, duplicando memoria y competedendo por CPU en el mismo
 * proceso, que es exactamente lo que un endpoint de inferencia no necesita.
 *
 * `searchImage.service.ts` mantiene su API pública: solo delega en `ocrExtract`.
 */

// Datos de idioma locales para OCR (evita descargas en cada request).
// Resolución robusta de la ruta: `__dirname` apunta a src/shared/utils (o dist/...);
// el paquete vive en la raíz del backend, así que subimos hasta la raíz y bajamos a
// node_modules. Fallback a process.cwd() por si el build cambia la estructura.
const OCR_LANG_PATH = (() => {
  const candidates = [
    path.join(__dirname, "../../../node_modules/@tesseract.js-data/eng/4.0.0"),
    path.join(process.cwd(), "node_modules", "@tesseract.js-data", "eng", "4.0.0"),
  ];
  for (const candidate of candidates) {
    try {
      if (require("fs").existsSync(candidate)) return candidate;
    } catch {
      /* ignorar */
    }
  }
  return candidates[0];
})();

// Worker reutilizable: se crea UNA vez por proceso (los datos del modelo se cargan
// una sola vez en lugar de hacerlo por request) y las llamadas a recognize se
// serializan para evitar carreras sobre el mismo worker.
let ocrWorkerPromise: Promise<TesseractWorker | null> | null = null;
let ocrQueue: Promise<unknown> = Promise.resolve();

function getOcrWorker(): Promise<TesseractWorker | null> {
  if (!ocrWorkerPromise) {
    ocrWorkerPromise = createWorker("eng", 1, {
      langPath: OCR_LANG_PATH,
      gzip: true,
      // Sin errorHandler tesseract.js lanza sincrónicamente (uncaughtException) cuando un
      // job del worker rechaza (p. ej. imagen corrupta), tumbando el proceso aunque la
      // promesa de recognize sí se rechace. El handler evita ese throw global; el rechazo
      // de recognize lo captura el caller.
      errorHandler: (ocrError) => logger.warn("OCR worker error", { error: (ocrError as Error)?.message }),
    }).catch((initError) => {
      logger.error("OCR init falló", { error: (initError as Error)?.message });
      ocrWorkerPromise = null;
      return null;
    });
  }
  return ocrWorkerPromise;
}

/**
 * Extrae el texto de una imagen. **Nunca lanza**: si el worker no pudo iniciar o
 * `recognize` falla, devuelve texto vacío y deja registrado el motivo.
 *
 * Que no lanza es un requisito de diseño del flujo híbrido: el OCR es una *evidencia
 * adicional*, nunca un requisito. Si el OCR falla, la detección visual de YOLO debe
 * seguir funcionando igual.
 */
export async function ocrExtract(buffer: Buffer): Promise<string> {
  const task = ocrQueue.then(async () => {
    const worker = await getOcrWorker();
    if (!worker) return "";
    try {
      const ctx = await worker.recognize(buffer);
      return ctx.data.text || "";
    } catch (ocrError) {
      // El worker quedó en estado inválido: descartarlo para que el próximo request lo recree.
      ocrWorkerPromise = null;
      logger.warn("OCR falló", { error: (ocrError as Error)?.message });
      return "";
    }
  });
  ocrQueue = task.catch(() => undefined);
  return task;
}

/** Variante que sí propaga el error, para quien necesite distinguir el fallo. */
export async function ocrExtractEstricto(buffer: Buffer): Promise<string> {
  const worker = await getOcrWorker();
  if (!worker) throw new Error("OCR no disponible");
  const ctx = await worker.recognize(buffer);
  return ctx.data.text || "";
}