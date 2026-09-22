export class VisionServiceError extends Error {
  readonly status: number;
  readonly codigo: string;

  constructor(status: number, codigo: string, message: string) {
    super(message);
    this.name = "VisionServiceError";
    this.status = status;
    this.codigo = codigo;
  }
}

export const VisionErrores = {
  imagenRequerida: new VisionServiceError(400, "VISION_IMAGEN_REQUERIDA", "Debe subir una imagen"),
  requestInvalido: (message: string) =>
    new VisionServiceError(400, "VISION_REQUEST_INVALIDO", message || "Parámetros de la solicitud inválidos"),
  noClasificada: () =>
    new VisionServiceError(422, "VISION_NO_CLASIFICADA", "La imagen es válida pero no se pudo clasificar la pieza"),
  bajaConfianza: () =>
    new VisionServiceError(422, "VISION_BAJA_CONFIANZA", "No se pudo identificar la pieza con suficiente confianza"),
  servicioNoDisponible: () =>
    new VisionServiceError(503, "VISION_NO_DISPONIBLE", "El servicio de visión no está disponible"),
  tiempoAgotado: () =>
    new VisionServiceError(504, "VISION_TIMEOUT", "El servicio de visión tardó demasiado en responder"),
  respuestaInvalida: () =>
    new VisionServiceError(503, "VISION_RESPUESTA_INVALIDA", "El servicio de visión devolvió una respuesta inválida"),
};