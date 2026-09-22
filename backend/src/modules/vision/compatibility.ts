import { yearRangesOverlap } from "../../utils/yearRanges";
import { coincidenTextos } from "./normalize";

export interface VehiculoQuery {
  marca?: string | null;
  modelo?: string | null;
  anio?: string | null;
}

export interface CompatibilidadProducto {
  verificada: boolean;
  score: number;
  coincidencias: string[];
  nota: string;
}

export interface CompatibilidadConsulta {
  consultada: boolean;
  fuente: string;
  metodologia: string;
  consultadoEn: string;
  vehiculo: { marca: string | null; modelo: string | null; anio: string | null } | null;
  verificadas: number;
  noVerificadas: number;
  nota: string;
}

export interface CandidatoConCompatibilidad<T> {
  candidato: T;
  compatibilidad: CompatibilidadProducto;
}

export function evaluarCompatibilidadProducto(producto: { brand: string; model: string; year: string }, vehiculo: VehiculoQuery | null): CompatibilidadProducto {
  const tieneDatos = !!vehiculo && (!!vehiculo.marca || !!vehiculo.modelo || !!vehiculo.anio);
  if (!tieneDatos) {
    return {
      verificada: false,
      score: 0,
      coincidencias: [],
      nota: "Sin vehículo proporcionado; compatibilidad no verificada.",
    };
  }

  const coincidencias: string[] = [];
  let score = 0;

  if (vehiculo!.marca) {
    if (coincidenTextos(producto.brand, vehiculo!.marca!)) {
      coincidencias.push("marca");
      score += 3;
    }
  }
  if (vehiculo!.modelo) {
    if (coincidenTextos(producto.model, vehiculo!.modelo!)) {
      coincidencias.push("modelo");
      score += 5;
    }
  }
  if (vehiculo!.anio) {
    if (yearRangesOverlap(vehiculo!.anio!, producto.year)) {
      coincidencias.push("anio");
      score += 2;
    }
  }

  const camposPedidos = [vehiculo!.marca, vehiculo!.modelo, vehiculo!.anio].filter(Boolean).length;
  const tieneMarcaYModelo = !!vehiculo!.marca && !!vehiculo!.modelo;
  const todasConcuerdan = coincidencias.length === camposPedidos;
  const verificada = tieneMarcaYModelo && todasConcuerdan;

  let nota: string;
  if (verificada) {
    nota = "Compatibilidad verificada contra el catálogo interno (marca, modelo y año confirmados).";
  } else if (camposPedidos < 2) {
    nota = "Vehículo insuficiente: se requieren al menos marca y modelo para validar compatibilidad.";
  } else {
    nota = "No se encontraron coincidencias suficientes; compatibilidad no verificada.";
  }

  return { verificada, score, coincidencias, nota };
}

/**
 * Abstracción de compatibilidad (TC-6). Implementaciones futuras (APIs del
 * fabricante/distribuidor, búsqueda web controlada) deben conservar la
 * trazabilidad: fuente, fecha de consulta y confianza; sin inventar
 * compatibilidades. Las externas quedan como stubs hasta tener proveedor real.
 */
export interface ProveedorExternoCompatibilidad {
  readonly tipo: string;
  readonly fuente: string;
  readonly fechaConsulta: string;
  readonly confianza: number;
  readonly timeoutMs: number;
  readonly usaCache: boolean;
  readonly fallback: boolean;
  evaluarCandidatos<T extends { brand: string; model: string; year: string }>(
    candidatos: T[],
    vehiculo: VehiculoQuery | null
  ): Promise<CandidatoConCompatibilidad<T>[]>;
}

export interface CompatibilityProvider {
  readonly tipo: string;
  evaluarCandidatos<T extends { brand: string; model: string; year: string }>(
    candidatos: T[],
    vehiculo: VehiculoQuery | null
  ): Promise<CandidatoConCompatibilidad<T>[]>;
}

export class BaseDatosInternaProvider implements CompatibilityProvider {
  readonly tipo = "base_datos_interna";

  async evaluarCandidatos<T extends { brand: string; model: string; year: string }>(
    candidatos: T[],
    vehiculo: VehiculoQuery | null
  ): Promise<CandidatoConCompatibilidad<T>[]> {
    const evaluados: CandidatoConCompatibilidad<T>[] = candidatos.map((candidato) => ({
      candidato,
      compatibilidad: evaluarCompatibilidadProducto(candidato, vehiculo),
    }));
    return evaluados.sort((a, b) => {
      if (b.compatibilidad.verificada !== a.compatibilidad.verificada) {
        return b.compatibilidad.verificada ? 1 : -1;
      }
      return b.compatibilidad.score - a.compatibilidad.score;
    });
  }
}

export class CompatibilityProviderFactory {
  static crear(tipo: "base_datos_interna" | string): CompatibilityProvider {
    if (tipo === "base_datos_interna") return new BaseDatosInternaProvider();
    return new BaseDatosInternaProvider();
  }
}