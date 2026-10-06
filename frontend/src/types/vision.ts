export type VisionAvailabilityLevel = "DISPONIBLE" | "POCAS_UNIDADES" | "NO_DISPONIBLE";

export interface VisionBoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface VisionVehiculoQuery {
  marca?: string;
  modelo?: string;
  anio?: string;
}

export interface VisionEvidenciaCodigo {
  campo: "oemCode" | "factoryCode" | "itemCode";
  codigoProducto: string;
  codigoDetectado: string;
  tipo: "exacta" | "parcial";
  peso: number;
}

export interface VisionDeteccionRespuesta {
  categoria: string;
  confianza: number;
  confianzaBaja: boolean;
  categoriaMapeada: string | null;
  boundingBox: VisionBoundingBox | null;
  /** Evidencia OCR (híbrido). Vacío si no se leyó texto utilizable. */
  textoDetectado?: string[];
  /** Códigos de pieza normalizados leídos del rótulo de la imagen. */
  codigosDetectados?: string[];
}

export interface VisionDisponibilidadView {
  nivel: VisionAvailabilityLevel;
  etiqueta: string;
}

export interface VisionDisponibilidadSucursal extends VisionDisponibilidadView {
  locationId: number;
  nombre: string;
  tipo: string;
}

/**
 * Disponibilidad POR SUCURSAL del contrato PÚBLICO (recogida). DTO mínimo y
 * seguro: nombre de la sucursal + bucket de disponibilidad. Nunca lleva stock,
 * `locationId`, `tipo` ni `etiqueta` (ver disponibilidadPorSucursalPublica).
 */
export interface VisionDisponibilidadSucursalPublica {
  sucursalId: number;
  nombre: string;
  nivel: VisionAvailabilityLevel;
}

export interface VisionCompatibilidadCandidato {
  verificada: boolean;
  score: number;
  coincidencias: string[];
  nota: string;
}

export interface VisionCandidatoPublico {
  id: number;
  itemCode: string;
  name: string;
  brand: string | null;
  model: string | null;
  year: string | null;
  image: string | null;
  categoria: string | null;
  price1: number;
  /**
   * Puntaje de evidencia OCR. Distinto de `compatibilidad.score`: aquel mide
   * coincidencia de vehículo, este coincidencia de código leído en la foto.
   */
  scoreEvidencia?: number;
  /**
   * Grado de coincidencia real de este candidato con la foto. `categoria` significa
   * que el único vínculo es compartir categoría con la clase detectada: la interfaz
   * debe decir "Coincidencia por categoría" en lugar de anunciar un score 0.
   */
  nivelCoincidencia: "fuerte" | "media" | "categoria";
  /** Prioridad 5 del Ranking V2: el nombre del producto corresponde a la pieza detectada. */
  claseCoincide: boolean;
  evidencias?: VisionEvidenciaCodigo[];
  compatibilidad: VisionCompatibilidadCandidato;
  disponibilidad: VisionDisponibilidadView;
  disponibilidadPorSucursal: VisionDisponibilidadSucursal[];
  /**
   * Desglose PÚBLICO de disponibilidad para recogida, por sucursal TIENDA.
   * Solo sucursalId + nombre + bucket seguro. Puede venir vacío/ausente cuando
   * no hay sucursal de recogida para el producto.
   */
  disponibilidadPorSucursalPublica?: VisionDisponibilidadSucursalPublica[];
}

export interface VisionCompatibilidadConsulta {
  consultada: boolean;
  fuente: string;
  metodologia: string;
  consultadoEn: string;
  vehiculo: { marca: string | null; modelo: string | null; anio: string | null } | null;
  verificadas: number;
  noVerificadas: number;
  nota: string;
}

export interface VisionSucursal {
  id: number;
  nombre: string;
  tipo: string;
}

export interface VisionEntrega {
  modalidades: Array<"recoger" | "delivery">;
  sucursales: VisionSucursal[];
}

export interface VisionAnalysis {
  version: string;
  consultadoEn: string;
  proveedor: string;
  deteccion: VisionDeteccionRespuesta;
  vehiculo: { marca: string | null; modelo: string | null; anio: string | null } | null;
  categoriaCatalogo: { id: number; nombre: string } | null;
  candidatos: VisionCandidatoPublico[];
  compatibilidad: VisionCompatibilidadConsulta;
  entrega: VisionEntrega;
  nota?: string;
}

export interface VisionRequestOptions {
  vehiculo?: VisionVehiculoQuery;
  signal?: AbortSignal;
}