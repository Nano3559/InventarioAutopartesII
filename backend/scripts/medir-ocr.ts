/**
 * Medición de rendimiento del OCR híbrido (FASE F).
 *
 * Responde una pregunta concreta: el OCR ¿hace más lenta la búsqueda por imagen?
 * El backend lanza el OCR en paralelo con la llamada a `ia-service`, así que el
 * costo real NO es "OCR + visión" sino lo que sobra del OCR sobre la visión.
 *
 * Uso:  npx tsx scripts/medir-ocr.ts [ruta/a/imagen.jpg]
 * Las métricas se imprimen; el script no modifica nada ni toca la base de datos.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { ocrExtract } from "../src/shared/utils/ocr";

const MB = 1024 * 1024;

function memoriaProceso(): number {
  return process.memoryUsage().rss / MB;
}

function percentil(valores: number[], p: number): number {
  const ordenados = [...valores].sort((a, b) => a - b);
  const idx = Math.min(ordenados.length - 1, Math.ceil((p / 100) * ordenados.length) - 1);
  return ordenados[Math.max(0, idx)];
}

const resumen = (valores: number[]) => ({
  n: valores.length,
  promedio_ms: Math.round(valores.reduce((a, b) => a + b, 0) / valores.length),
  p50_ms: Math.round(percentil(valores, 50)),
  p95_ms: Math.round(percentil(valores, 95)),
  min_ms: Math.round(Math.min(...valores)),
  max_ms: Math.round(Math.max(...valores)),
});

async function main() {
  const arg = process.argv[2];
  const porDefecto = path.join(process.env.TEMP ?? ".", "opencode", "vision-test", "cand1.jpg");
  const imagenPath = arg && readFileSyncSafe(arg) ? arg : porDefecto;

  if (!imagenPath || !readFileSyncSafe(imagenPath)) {
    console.error("No se encontró una imagen para medir. Uso: npx tsx scripts/medir-ocr.ts <imagen.jpg>");
    process.exit(1);
  }

  const buffer = readFileSync(imagenPath);
  console.log(`Imagen: ${imagenPath} (${Math.round(buffer.length / 1024)} KB)`);
  console.log(`RAM inicial: ${memoriaProceso().toFixed(0)} MB\n`);

  // --- Carga en frío: incluye crear el worker y cargar eng.traineddata ---
  const t0 = Date.now();
  await ocrExtract(buffer);
  const frio = Date.now() - t0;
  console.log(`1) PRIMERA llamada (carga del modelo Tesseract): ${frio} ms`);
  console.log(`   RAM tras cargar: ${memoriaProceso().toFixed(0)} MB\n`);

  // --- Latencia caliente ---
  const ITERACIONES = 5;
  const tiempos: number[] = [];
  for (let i = 0; i < ITERACIONES; i++) {
    const t = Date.now();
    const texto = await ocrExtract(buffer);
    tiempos.push(Date.now() - t);
    if (i === 0) console.log(`   (muestra de texto reconocido: ${texto.replace(/\s+/g, " ").trim().slice(0, 60) || "<vacío>"})`);
  }
  console.log(`\n2) OCR caliente x${ITERACIONES}:`, resumen(tiempos));

  // --- El punto clave: Vision y OCR en paralelo ---
  // Se simula la espera de `ia-service` (YOLO en CPU) para ver cuánto suma el OCR.
  // En paralelo ambas arrancan a la vez, así que el total es el MAYOR de las dos,
  // NO la suma: por eso el OCR queda oculto mientras la visión tarda más.
  const LATENCIA_VISION_SIMULADA = 2700;
  const latenciaOcr = resumen(tiempos).p50_ms;

  const serie = LATENCIA_VISION_SIMULADA + latenciaOcr;
  const paralelo = Math.max(LATENCIA_VISION_SIMULADA, latenciaOcr);
  const sobrecosto = Math.max(0, paralelo - LATENCIA_VISION_SIMULADA);

  console.log(`\n3) Impacto sobre la latencia total del request:`);
  console.log(`   OCR solo (p50):                         ${latenciaOcr} ms`);
  console.log(`   visión sola (simulada):                 ${LATENCIA_VISION_SIMULADA} ms`);
  console.log(`   si el OCR fuera EN SERIE:               ${serie} ms (+${latenciaOcr} ms)`);
  console.log(`   implementado EN PARALELO:              ${paralelo} ms (+${sobrecosto} ms)`);
  console.log(
    sobrecosto > 200
      ? `   AVISO: el OCR aporta ${sobrecosto} ms porque es más lento que la visión.`
      : `   El OCR queda oculto tras la latencia de visión: no añade tiempo de espera.`
  );

  console.log(`\n4) RAM final: ${memoriaProceso().toFixed(0)} MB`);
  console.log(
    "\nNota: el modelo de Tesseract queda cargado en el proceso del backend. Es el mismo" +
      "\nworker que usa la búsqueda por imagen, así que no hay una segunda copia (ver shared/utils/ocr.ts)."
  );
  process.exit(0);
}

function readFileSyncSafe(p: string): boolean {
  try {
    return readFileSync(p).length > 0;
  } catch {
    return false;
  }
}

main().catch((e) => {
  console.error("Fallo la medición:", (e as Error)?.message);
  process.exit(1);
});