export class VisionServiceError extends Error {
  readonly status: number;
  readonly codigo: string;
  /**
   * Datos adicionales de la respuesta de error (p. ej. recomendaciones de captura).
   * Aditivo: los errores que no lo definen devuelven el mismo body de siempre.
   */
  readonly payload: Record<string, unknown> | null;

  constructor(status: number, codigo: string, message: string, payload: Record<string, unknown> | null = null) {
    super(message);
    this.name = "VisionServiceError";
    this.status = status;
    this.codigo = codigo;
    this.payload = payload;
  }
}

/**
 * Recomendaciones accionables cuando la imagen no permite clasificar o la confianza
 * queda por debajo del umbral. Se devuelven junto al 422 para que el usuario sepa
 * cómo tomar la foto en lugar de solo recibir un rechazo.
 *
 * Son genéricas y verificables a simple vista (encuadre, luz, una sola pieza, rótulo
 * legible). No promete resultados ni promete una mejora medible: el umbral se
 * calibrará con curvas P/R cuando exista ground truth.
 */
export const RECOMENDACIONES_CAPTURA = [
  "Encuadra una sola pieza, centrada y ocupando la mayor parte de la imagen.",
  "Usa fondo liso y uniforme, sin manos, herramientas ni otras piezas alrededor.",
  "Buena iluminación frontal, sin reflejos fuertes ni sombras duras sobre la pieza.",
  "Si la pieza tiene etiqueta o código grabado, acércate para que el texto sea legible.",
  "Evita imágenes borrosas, con movimiento o muy alejadas.",
];

export const VisionErrores = {
  imagenRequerida: new VisionServiceError(400, "VISION_IMAGEN_REQUERIDA", "Debe subir una imagen"),
  requestInvalido: (message: string) =>
    new VisionServiceError(400, "VISION_REQUEST_INVALIDO", message || "Parámetros de la solicitud inválidos"),
  noClasificada: () =>
    new VisionServiceError(422, "VISION_NO_CLASIFICADA", "La imagen es válida pero no se pudo clasificar la pieza", {
      recomendaciones: RECOMENDACIONES_CAPTURA,
    }),
  bajaConfianza: () =>
    new VisionServiceError(422, "VISION_BAJA_CONFIANZA", "No se pudo identificar la pieza con suficiente confianza", {
      recomendaciones: RECOMENDACIONES_CAPTURA,
    }),
  servicioNoDisponible: () =>
    new VisionServiceError(503, "VISION_NO_DISPONIBLE", "El servicio de visión no está disponible"),
  tiempoAgotado: () =>
    new VisionServiceError(504, "VISION_TIMEOUT", "El servicio de visión tardó demasiado en responder"),
  respuestaInvalida: () =>
    new VisionServiceError(503, "VISION_RESPUESTA_INVALIDA", "El servicio de visión devolvió una respuesta inválida"),
};