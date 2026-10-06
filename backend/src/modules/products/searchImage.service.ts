import { PrismaClient } from "@prisma/client";
import multer from "multer";
import { ocrExtract } from "../../shared/utils/ocr";

const prisma = new PrismaClient();

const ALLOWED_MIME = ["image/jpeg", "image/png", "image/webp"];

const IMAGE_STOPWORDS = new Set(["img", "imagen", "image", "photo", "foto", "producto", "product", "part", "ref", "cod", "code", "dsc", "dscn", "captura", "nuevo", "venta", "jpeg", "jpg", "png", "webp", "2024", "2023", "2022", "the", "and", "for", "con", "numero", "number", "original", "oem", "referencia", "repuesto", "accesorio", "universal", "calidad", "estandar"]);

// Upload específico para búsqueda por imagen (memoria, 5 MB, solo JPG/PNG/WebP, un archivo)
export const imageUpload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 5 * 1024 * 1024, files: 1 },
  fileFilter: (_req, file, cb) => {
    if (ALLOWED_MIME.includes(file.mimetype)) {
      return cb(null, true);
    }
    const err: any = new Error("Tipo de archivo no permitido");
    err.code = "INVALID_FILE_TYPE";
    cb(err);
  },
});

/**
 * Criterio único de disponibilidad, igual al catálogo público.
 * No expone el stock exacto.
 */
export function computeAvailability(stockTotal: number): string {
  if (stockTotal > 10) return "Disponible";
  if (stockTotal > 0) return "Pocas unidades";
  return "Consultar disponibilidad";
}

export interface ProductoConScore {
  producto: any;
  score: number;
}

export interface ResultadoBusquedaImagen {
  keywords: string[];
  results: ProductoConScore[];
}

/**
 * Flujo compartido: imagen → tokens del nombre de archivo → OCR → búsqueda → ranking.
 * Cada endpoint controla la autorización y la serialización de su respuesta.
 */
export async function procesarBusquedaPorImagen(file: Express.Multer.File): Promise<ResultadoBusquedaImagen> {
  // Normalizar el nombre del archivo: quitar extensión, guiones/guiones bajos y tokens genéricos/códigos
  const raw = file.originalname.toLowerCase().replace(/\.[^.]+$/, "");

  const tokenPool = new Set<string>();
  const pushToken = (w: string) => {
    if (w.length > 2 && !/^\d+$/.test(w) && !IMAGE_STOPWORDS.has(w)) tokenPool.add(w);
  };

  raw
    .replace(/[_\-\.\+\(\)\[\]]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .forEach(pushToken);

  // Extraer el contenido real de la imagen (OCR) además del nombre del archivo.
  // El worker es único en todo el proceso (shared/utils/ocr) y nunca lanza:
  // si el OCR falla se sigue buscando con los tokens del nombre de archivo.
  const ocrText = await ocrExtract(file.buffer);

  ocrText
    .toLowerCase()
    .split(/[\s,;/|]+/)
    .map((t) => t.replace(/[^\w.-]/g, "").replace(/-/g, ""))
    .forEach(pushToken);

  const keywords = Array.from(tokenPool);

  if (keywords.length === 0) {
    return { keywords, results: [] };
  }

  // Buscar por múltiples campos y rankear por cantidad de coincidencias
  const products = await prisma.product.findMany({
    where: {
      AND: [
        {
          OR: keywords.flatMap((kw) => [
            { name: { contains: kw, mode: "insensitive" as const } },
            { brand: { contains: kw, mode: "insensitive" as const } },
            { model: { contains: kw, mode: "insensitive" as const } },
            { itemCode: { contains: kw, mode: "insensitive" as const } },
            { oemCode: { contains: kw, mode: "insensitive" as const } },
            { factoryCode: { contains: kw, mode: "insensitive" as const } },
            { detail: { contains: kw, mode: "insensitive" as const } },
            { manufacturer: { contains: kw, mode: "insensitive" as const } },
          ]),
        },
      ],
    },
    include: {
      category: true,
      inventories: {
        include: { location: { select: { id: true, name: true, type: true } } },
      },
    },
    take: 50,
  });

  // Rankear: cuantas más keywords coincidan con el nombre/marca/modelo/códigos, mejor
  const results = products
    .map((p) => {
      const haystack = `${p.name} ${p.brand} ${p.model} ${p.itemCode} ${p.oemCode || ""} ${p.factoryCode || ""} ${p.detail || ""}`.toLowerCase();
      const matches = keywords.filter((kw) => haystack.includes(kw)).length;
      return { producto: p, score: matches };
    })
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 20);

  return { keywords, results };
}

/**
 * Serialización para el endpoint público: únicamente datos seguros.
 * NUNCA expone price2, wholesalePrice, cost, totalStock, locations ni datos por almacén.
 */
export function serializeProductoPublico(producto: any, score: number) {
  const stockTotal = (producto.inventories || []).reduce((sum: number, inv: any) => sum + inv.stock, 0);
  return {
    id: producto.id,
    itemCode: producto.itemCode,
    name: producto.name,
    brand: producto.brand,
    model: producto.model,
    year: producto.year,
    detail: producto.detail,
    detalles: producto.detalles,
    image: producto.image,
    category: producto.category?.name || null,
    price1: Number(producto.price1),
    availability: computeAvailability(stockTotal),
    score,
  };
}

/**
 * Decide el alcance de ubicación de la serialización interna.
 *
 * La política vive en `shared/utils/scope.ts` y es una allow-list (ADMIN/INVENTARIO
 * tienen vista global; cualquier otro rol queda acotado a su locationId, que es null
 * si no tiene ubicación asignada). No es "todo lo que no sea TIENDA" porque el nombre
 * del rol viene de RoleModel.name (tabla data-driven editable): con un deny-list, un
 * rol futuro sin ubicación recibiría la vista global de stock. Un TIENDA sin ubicación
 * se rechaza antes con requireTiendaLocation; aquí null significa "sin inventarios
 * visibles", nunca "vista global".
 */
export { ROLES_CON_VISTA_GLOBAL, resolveLocationScope } from "../../shared/utils/scope";


/**
 * Serialización para el endpoint interno: conserva el contrato existente
 * (misma forma que consumen el panel y el móvil). El score corresponde al
 * ranking real de coincidencias (el endpoint anterior lo entregaba fijo en 1).
 *
 * `locationScope` acota la vista a UNA ubicación. Se usa para usuarios TIENDA:
 * sin él, `totalStock` y `locations` sumarían el stock de todas las tiendas y del
 * almacén, lo que filtra existencias de terceros. Con scope, el total y la lista
 * de ubicaciones reflejan solo la tienda del usuario (mismo nombre de campo, así
 * que el móvil no necesita cambios). ADMIN/INVENTARIO pasan null y conservan la
 * vista global, que es su operación legítima.
 */
export function serializeProductoInterno(producto: any, score: number, locationScope: number | null = null) {
  const inventariosVisibles: any[] = locationScope
    ? (producto.inventories || []).filter((i: any) => i.location?.id === locationScope)
    : producto.inventories || [];

  const totalStock = inventariosVisibles.reduce((sum: number, inv: any) => sum + inv.stock, 0);
  return {
    id: producto.id,
    itemCode: producto.itemCode,
    name: producto.name,
    brand: producto.brand,
    model: producto.model,
    year: producto.year,
    price1: Number(producto.price1),
    price2: Number(producto.price2),
    image: producto.image,
    score,
    totalStock,
    locations: inventariosVisibles.map((i: any) => ({
      name: i.location.name,
      type: i.location.type,
      stock: i.stock,
    })),
  };
}