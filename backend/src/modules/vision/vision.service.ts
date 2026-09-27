import { PrismaClient } from "@prisma/client";
import { AuthRequest } from "../../shared/types";
import { VISION_API_VERSION, VisionBoundingBox, validarRespuestaVision } from "./contract";
import { VisionErrores } from "./vision.errors";
import { visionConfig } from "./vision.config";
import { visionProvider, withVisionTimeout } from "./vision.provider";
import { mapearCategoria } from "./categoryMapping";
import { normalizarTexto } from "./normalize";
import { availabilityView, DisponibilidadView, SucursalDisponibilidad, StockPorSucursal } from "./availability";
import { CompatibilityProviderFactory, CompatibilidadConsulta, CompatibilidadProducto, VehiculoQuery } from "./compatibility";
import { logger } from "../../shared/utils/logger";

const prisma = new PrismaClient();

const compatProvider = CompatibilityProviderFactory.crear("base_datos_interna");

const MAX_CANDIDATOS_RESPUESTA = 12;
const MAX_SUCURSALES_POR_CANDIDATO = 6;
const MAX_PRODUCTOS_CONSULTADOS = 30;

export interface VisionDeteccionRespuesta {
  categoria: string;
  confianza: number;
  confianzaBaja: boolean;
  categoriaMapeada: string | null;
  boundingBox: VisionBoundingBox | null;
}

export interface CompatibilidadCandidato {
  verificada: boolean;
  score: number;
  coincidencias: string[];
  nota: string;
}

export interface CandidatoVisionBase {
  id: number;
  itemCode: string;
  name: string;
  brand: string | null;
  model: string | null;
  year: string | null;
  image: string | null;
  categoria: string | null;
  price1: number;
  compatibilidad: CompatibilidadCandidato;
  disponibilidad: DisponibilidadView;
  disponibilidadPorSucursal: Array<SucursalDisponibilidad>;
}

export interface CandidatoVisionInterno extends CandidatoVisionBase {
  price2: number;
  stockTotal: number;
  stockPorSucursal: StockPorSucursal[];
}

export interface SucursalEntrega {
  id: number;
  nombre: string;
  tipo: string;
}

export interface VisionResponse {
  version: string;
  consultadoEn: string;
  proveedor: string;
  deteccion: VisionDeteccionRespuesta;
  vehiculo: { marca: string | null; modelo: string | null; anio: string | null } | null;
  categoriaCatalogo: { id: number; nombre: string } | null;
  candidatos: CandidatoVisionBase[] | CandidatoVisionInterno[];
  compatibilidad: CompatibilidadConsulta;
  entrega: { modalidades: Array<"recoger" | "delivery">; sucursales: SucursalEntrega[] };
  nota?: string;
}

export interface OpcionVision {
  file: Express.Multer.File;
  modo: "publico" | "interno";
  usuario?: AuthRequest["user"] | null;
  vehiculo?: VehiculoQuery | null;
  escenarioMock?: string | null;
}

interface ProductoConRelation {
  id: number;
  itemCode: string;
  name: string;
  brand: string | null;
  model: string | null;
  year: string | null;
  image: string | null;
  price1: bigint | number | { toString(): string };
  price2: bigint | number | { toString(): string } | null;
  categoryId: number | null;
  category: { id: number; name: string } | null;
  inventories: Array<{
    stock: number;
    locationId: number;
    location: { id: number; name: string; type: string };
  }>;
}

function stockVisible(producto: ProductoConRelation, usuario?: AuthRequest["user"] | null) {
  if (usuario?.role === "TIENDA" && usuario.locationId != null) {
    return producto.inventories.filter((inv) => inv.locationId === usuario.locationId);
  }
  return producto.inventories;
}

function serializarPublico(producto: ProductoConRelation, compatibilidad: CompatibilidadProducto): CandidatoVisionBase {
  const stockTotal = producto.inventories.reduce((sum, inv) => sum + inv.stock, 0);
  const disponibilidad = availabilityView(stockTotal);
  const disponibilidadPorSucursal = producto.inventories
    .filter((inv) => inv.location.type === "TIENDA")
    .slice(0, MAX_SUCURSALES_POR_CANDIDATO)
    .map((inv) => ({
      locationId: inv.locationId,
      nombre: inv.location.name,
      tipo: inv.location.type,
      ...availabilityView(inv.stock),
    }));

  return {
    id: producto.id,
    itemCode: producto.itemCode,
    name: producto.name,
    brand: producto.brand,
    model: producto.model,
    year: producto.year,
    image: producto.image,
    categoria: producto.category?.name ?? null,
    price1: Number(producto.price1),
    compatibilidad,
    disponibilidad,
    disponibilidadPorSucursal,
  };
}

function serializarInterno(producto: ProductoConRelation, compatibilidad: CompatibilidadProducto, usuario?: AuthRequest["user"] | null): CandidatoVisionInterno {
  const base = serializarPublico(producto, compatibilidad);
  const visibles = stockVisible(producto, usuario);
  return {
    ...base,
    price2: Number(producto.price2 ?? 0),
    stockTotal: visibles.reduce((sum, inv) => sum + inv.stock, 0),
    stockPorSucursal: visibles.map((inv) => ({
      locationId: inv.locationId,
      nombre: inv.location.name,
      tipo: inv.location.type,
      stock: inv.stock,
    })),
  };
}

export async function generarRespuestaVision(opts: OpcionVision): Promise<VisionResponse> {
  const { file, modo, usuario, vehiculo } = opts;
  const consultadoEn = new Date().toISOString();

  const deteccion = await withVisionTimeout(
    visionProvider.detectar(
      { buffer: file.buffer, mimetype: file.mimetype, originalName: file.originalname },
      opts.escenarioMock ?? undefined
    ),
    visionConfig.timeoutMs
  );

  const { valida, detecciones } = validarRespuestaVision(deteccion.detecciones);
  if (!valida) throw VisionErrores.respuestaInvalida();

  if (detecciones.length === 0) throw VisionErrores.noClasificada();

  const top = detecciones.reduce((mejor, actual) => (actual.confianza > mejor.confianza ? actual : mejor));
  logger.info("[DIAG-VISION] detecciones crudas antes del umbral de confianza.", {
    proveedor: deteccion.proveedor,
    total: detecciones.length,
    detecciones: detecciones.slice(0, 5).map((d) => ({
      categoria: d.categoria,
      confianza: d.confianza,
      boundingBox: d.boundingBox ?? null,
    })),
    top: { categoria: top.categoria, confianza: top.confianza, boundingBox: top.boundingBox ?? null },
    umbral: visionConfig.confianzaMinima,
  });
  if (top.confianza < visionConfig.confianzaMinima) throw VisionErrores.bajaConfianza();

  const categorias = await prisma.category.findMany({ select: { id: true, name: true } });
  const nombreCategoriaMapeada = mapearCategoria(categorias.map((c) => c.name), top.categoria);
  const categoriaCatalogo = nombreCategoriaMapeada
    ? (categorias.find((c) => normalizarTexto(c.name) === normalizarTexto(nombreCategoriaMapeada)) ?? null)
    : null;

  let candidatos: VisionResponse["candidatos"] = [];
  let compatibilidad: CompatibilidadConsulta = {
    consultada: true,
    fuente: compatProvider.tipo,
    metodologia: "baseline-catalog",
    consultadoEn,
    vehiculo: vehiculo ? { marca: vehiculo.marca ?? null, modelo: vehiculo.modelo ?? null, anio: vehiculo.anio ?? null } : null,
    verificadas: 0,
    noVerificadas: 0,
    nota: "",
  };
  let nota: string | undefined;

  if (!categoriaCatalogo) {
    nota = "La clase detectada no tiene categoría equivalente en el catálogo.";
    compatibilidad.nota = "Sin categoría equivalente; no se evaluó compatibilidad.";
  } else {
    const products = await prisma.product.findMany({
      where: { categoryId: categoriaCatalogo.id },
      include: { category: { select: { id: true, name: true } }, inventories: { include: { location: true } } },
      orderBy: { name: "asc" },
      take: MAX_PRODUCTOS_CONSULTADOS,
    });

    const evaluados = await compatProvider.evaluarCandidatos(products, vehiculo ?? null);
    const topCandidatos = evaluados.slice(0, MAX_CANDIDATOS_RESPUESTA);

    candidatos = topCandidatos.map((entry) => {
      const producto = entry.candidato as unknown as ProductoConRelation;
      return modo === "interno"
        ? serializarInterno(producto, entry.compatibilidad, usuario)
        : serializarPublico(producto, entry.compatibilidad);
    });

    const tieneVehiculo = !!vehiculo && (!!vehiculo.marca || !!vehiculo.modelo || !!vehiculo.anio);
    const verificadas = topCandidatos.filter((c) => c.compatibilidad.verificada).length;

    compatibilidad.verificadas = verificadas;
    compatibilidad.noVerificadas = topCandidatos.length - verificadas;
    compatibilidad.nota = tieneVehiculo
      ? "Coincidencias contra datos de catálogo (marca/modelo/año). Sin evidencia externa: la verificación es parcial."
      : "Sin vehículo proporcionado; candidatos de la categoría sin verificación de compatibilidad.";

    if (candidatos.length === 0) {
      nota = "No hay productos publicados en la categoría detectada.";
    }
  }

  const sucursales = await prisma.location.findMany({
    where: { type: "TIENDA" },
    select: { id: true, name: true, type: true },
    orderBy: { name: "asc" },
  });

  return {
    version: VISION_API_VERSION,
    consultadoEn,
    proveedor: deteccion.proveedor,
    deteccion: {
      categoria: top.categoria,
      confianza: top.confianza,
      confianzaBaja: false,
      categoriaMapeada: nombreCategoriaMapeada,
      boundingBox: top.boundingBox ?? null,
    },
    vehiculo: vehiculo ? { marca: vehiculo.marca ?? null, modelo: vehiculo.modelo ?? null, anio: vehiculo.anio ?? null } : null,
    categoriaCatalogo: categoriaCatalogo ? { id: categoriaCatalogo.id, nombre: categoriaCatalogo.name } : null,
    candidatos,
    compatibilidad,
    entrega: {
      modalidades: ["recoger", "delivery"],
      sucursales: sucursales.map((s) => ({ id: s.id, nombre: s.name, tipo: s.type })),
    },
    ...(nota ? { nota } : {}),
  };
}

export function secureLog(respuesta: VisionResponse, modo: "publico" | "interno"): void {
  const cands = respuesta.candidatos as CandidatoVisionBase[];
  logger.info("Respuesta de visión generada.", {
    version: respuesta.version,
    proveedor: respuesta.proveedor,
    modo,
    candidatos: cands.length,
    verificadas: cands.filter((c) => c.compatibilidad.verificada).length,
    categoriaMapeada: respuesta.deteccion.categoriaMapeada,
  });
}