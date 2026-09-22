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

export interface VisionDeteccionRespuesta {
  categoria: string;
  confianza: number;
  confianzaBaja: boolean;
  categoriaMapeada: string | null;
  boundingBox: VisionBoundingBox | null;
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
  compatibilidad: VisionCompatibilidadCandidato;
  disponibilidad: VisionDisponibilidadView;
  disponibilidadPorSucursal: VisionDisponibilidadSucursal[];
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
  escenarioMock?: string;
  signal?: AbortSignal;
}