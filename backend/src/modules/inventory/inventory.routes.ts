import { Router, Response } from "express";
import { PrismaClient } from "@prisma/client";
import { authenticate, authorize, requireTiendaLocation } from "../../shared/middlewares/auth";
import { AuthRequest } from "../../shared/types";
import {
  UsuarioConAlcance,
  alcanceInventario,
  puedeVerCostos,
  puedeVerPrecioMayorista,
  ROLES_CON_INVENTARIO,
  ROLES_QUE_AJUSTAN_INVENTARIO,
} from "../../shared/utils/scope";

const router = Router();
const prisma = new PrismaClient();

router.use(authenticate);
router.use(requireTiendaLocation);
// Allow-list de lectura. Antes estas rutas solo exigían `authenticate`, así que un rol
// creado en el futuro en el panel (RoleModel es data-driven) heredaba el inventario de
// toda la cadena solo por tener sesión. TIENDA se conserva: consultar el stock de su
// tienda es su flujo funcional. Ver ROLES_CON_INVENTARIO en shared/utils/scope.ts.
router.use(authorize(...ROLES_CON_INVENTARIO));

/**
 * Columnas de Product que el módulo de inventario necesita mostrar.
 *
 * Se declara un `select` explícito en lugar de `product: true` a propósito: con
 * `include: { product: true` )` cualquier campo nuevo de Product (costo, precio
 * mayorista, datos de proveedor) entraría en la respuesta sin revisión. El inventario
 * no necesita ninguno de esos campos, así que se piden solo los que se usan.
 */
const PRODUCTO_INVENTARIO = {
  select: { name: true, itemCode: true, brand: true, model: true },
} as const;

const UBICACION_INVENTARIO = { select: { id: true, name: true, type: true } } as const;

/**
 * Columnas de Product que además necesita la escritura, porque ahí se aplica la
 * política financiera por rol en lugar de omitir los campos.
 */
const PRODUCTO_CON_FINANZEROS = {
  select: { name: true, itemCode: true, brand: true, model: true, cost: true, wholesalePrice: true },
} as const;

type FilaInventario = {
  id: number;
  productId: number;
  locationId: number;
  stock: number;
  minStock: number;
  product: {
    name: string;
    itemCode: string;
    brand: string | null;
    model: string | null;
    cost?: number | null;
    wholesalePrice?: number | null;
  };
  location: { id: number; name: string; type: string } | null;
};

/** Campos que devuelve `serializarInventario`; los financieros solo si el rol los tiene. */
interface InventarioSerializado {
  id: number;
  productId: number;
  locationId: number;
  stock: number;
  minStock: number;
  productName: string;
  itemCode: string;
  brand: string | null;
  model: string | null;
  locationName: string | null;
  locationType: string | null;
  wholesalePrice?: number | null;
  cost?: number | null;
}

/**
 * Forma única de respuesta de un registro de inventario.
 *
 * `incluirFinancieros` decide si se aplican las allow-lists financieras. En lectura
 * vale `false`: ningún rol recibe costo ni precio mayorista por esta vía, que es el
 * comportamiento que ya tenían estas rutas. En la escritura del ajuste vale `true`, y
 * entonces `cost` y `wholesalePrice` se conceden con los MISMOS helpers que usa
 * /api/products, no con un permiso propio: si esas allow-lists cambian, esta respuesta
 * cambia con ellas.
 */
function serializarInventario(
  inv: FilaInventario,
  user?: UsuarioConAlcance | null,
  incluirFinancieros = false,
): InventarioSerializado {
  const item: InventarioSerializado = {
    id: inv.id,
    productId: inv.productId,
    locationId: inv.locationId,
    stock: inv.stock,
    minStock: inv.minStock,
    productName: inv.product.name,
    itemCode: inv.product.itemCode,
    brand: inv.product.brand,
    model: inv.product.model,
    locationName: inv.location?.name ?? null,
    locationType: inv.location?.type ?? null,
  };
  if (incluirFinancieros) {
    if (puedeVerPrecioMayorista(user)) item.wholesalePrice = inv.product.wholesalePrice;
    if (puedeVerCostos(user)) item.cost = inv.product.cost;
  }
  return item;
}

// GET / — Listar todo el inventario con información de producto y ubicación
router.get("/", async (req: AuthRequest, res: Response) => {
  try {
    const { locationId, lowStock } = req.query;

    // Sustituye al `if (role === "TIENDA")` anterior. La diferencia: un rol que no
    // sea TIENDA ya no cae automáticamente en la vista global, y un ?locationId solo
    // se aplica a quien tiene alcance global (ADMIN/INVENTARIO).
    const alcance = alcanceInventario(req.user, locationId);
    const where: Record<string, unknown> = {};
    if (alcance !== null) where.locationId = alcance;

    const inventories = await prisma.inventory.findMany({
      where,
      include: {
        product: PRODUCTO_INVENTARIO,
        location: UBICACION_INVENTARIO,
      },
      orderBy: { product: { name: "asc" } },
    });

    let result = inventories.map((inv) => serializarInventario(inv as unknown as FilaInventario, req.user));

    if (lowStock === "true") {
      result = result.filter((r) => r.stock <= r.minStock);
    }

    res.json(result);
  } catch (error) {
    console.error("Error al listar inventario:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// GET /product/:productId — Stock por ubicación de un producto
router.get("/product/:productId", async (req: AuthRequest, res: Response) => {
  try {
    const productId = Number(req.params.productId);
    const inventoryWhere: Record<string, unknown> = { productId };
    const alcance = alcanceInventario(req.user);
    if (alcance !== null) inventoryWhere.locationId = alcance;

    const inventories = await prisma.inventory.findMany({
      where: inventoryWhere,
      include: { location: UBICACION_INVENTARIO },
      orderBy: { location: { name: "asc" } },
    });

    const stockTotal = inventories.reduce((sum, inv) => sum + inv.stock, 0);

    res.json({
      productId,
      stockTotal,
      locations: inventories.map((inv) => ({
        id: inv.id,
        locationId: inv.location.id,
        locationName: inv.location.name,
        locationType: inv.location.type,
        stock: inv.stock,
        minStock: inv.minStock,
      })),
    });
  } catch (error) {
    console.error("Error al obtener stock:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

// PUT /:id — Actualizar stock manualmente con motivo
//
// Allow-list de escritura, más estrecha que la de lectura: consultar existencias no
// habilita a escribirlas. ADMIN edita inventario e INVENTARIO controla físicamente la
// mercadería (manual funcional); TIENDA queda en 403 porque su stock se mueve por los
// flujos de venta, reposición y devolución, no editando el registro a mano.
router.put("/:id", authorize(...ROLES_QUE_AJUSTAN_INVENTARIO), async (req: AuthRequest, res: Response) => {
  try {
    const id = Number(req.params.id);
    const { stock, minStock, reasonType, reason } = req.body;

    const existing = await prisma.inventory.findUnique({ where: { id } });
    if (!existing) {
      return res.status(404).json({ message: "Registro de inventario no encontrado" });
    }

    const data: any = {};
    let stockChanged = false;
    if (stock != null) {
      const s = Number(stock);
      if (!Number.isInteger(s) || s < 0) {
        return res.status(400).json({ message: "El stock debe ser un entero mayor o igual a 0" });
      }
      data.stock = s;
      stockChanged = s !== existing.stock;
    }
    if (minStock != null) {
      const m = Number(minStock);
      if (!Number.isInteger(m) || m < 0) {
        return res.status(400).json({ message: "El stock mínimo debe ser un entero mayor o igual a 0" });
      }
      data.minStock = m;
    }

    const validReasons = ["COMPRA", "AJUSTE", "DEVOLUCION", "MERMA"];
    if (reasonType != null && reasonType !== "" && !validReasons.includes(reasonType)) {
      return res.status(400).json({ message: "El motivo debe ser COMPRA, AJUSTE, DEVOLUCION o MERMA" });
    }
    if (stockChanged && (!reasonType || reasonType === "")) {
      return res.status(400).json({ message: "Selecciona el motivo del ajuste de stock (COMPRA, AJUSTE, DEVOLUCION o MERMA)" });
    }

    const updated = await prisma.inventory.update({
      where: { id },
      data,
      include: { product: PRODUCTO_CON_FINANZEROS, location: UBICACION_INVENTARIO },
    });

    await prisma.auditLog.create({
      data: {
        userId: req.user!.userId,
        action: "UPDATE_INVENTORY",
        targetType: "INVENTORY",
        targetId: id,
        oldValue: { stock: existing.stock, minStock: existing.minStock },
        newValue: { stock: updated.stock, minStock: updated.minStock, reasonType: reasonType || null, reason: reason || null },
      },
    });

    // Antes devolvía el registro crudo con `product: true`, es decir el Product
    // completo (price1, price2, costo y cualquier campo futuro). Ahora pasa por la
    // política de allow-lists: solo viajan los campos del `select`, y `cost` y
    // `wholesalePrice` se conceden por rol, igual que en /api/products.
    res.json(serializarInventario(updated as unknown as FilaInventario, req.user, true));
  } catch (error) {
    console.error("Error al actualizar inventario:", error);
    res.status(500).json({ message: "Error interno del servidor" });
  }
});

export default router;
