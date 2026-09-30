/**
 * Única fuente de verdad del alcance por rol.
 *
 * ANTES estas reglas vivían duplicadas en tres módulos con dos formas distintas:
 * allow-list en reports (`ROLES_CON_COSTOS`) y search-image
 * (`ROLES_CON_VISTA_GLOBAL`), y deny-list (`role !== "TIENDA"`, `!esTienda`) en
 * products y vision. La deny-list es un fallo de seguridad: el nombre del rol
 * viene de `RoleModel.name`, una tabla data-driven editable desde el panel, así que
 * un rol creado en el futuro (p. ej. "CAJERO") caería del lado permitido y recibiría
 * costos de compra y existencias de toda la cadena sin revisión.
 *
 * Regla: por defecto NO se concede nada. Solo los roles explícitos acceden.
 */

/** Roles con alcance global (operan sobre toda la cadena, todas las tiendas). */
export const ROLES_CON_VISTA_GLOBAL = new Set(["ADMIN", "INVENTARIO"]);

/**
 * Roles autorizados a ver información financiera interna: costo de compra, utilidad
 * y margen. Deliberadamente es el MISMO conjunto que la vista global: quien ve los
 * costos de la cadena necesita ver la cadena. El móvil (TIENDA) queda fuera.
 */
export const ROLES_CON_COSTOS = ROLES_CON_VISTA_GLOBAL;

/**
 * Roles autorizados a ver el precio mayorista (`Product.wholesalePrice`).
 *
 * Allow-list, no deny-list, por el mismo motivo que `ROLES_CON_COSTOS`: un rol nuevo
 * o desconocido no debe heredar el precio mayorista solo por estar autenticado.
 *
 * Por qué los TRES roles actuales, y no solo ADMIN. Esto NO es una suposición, son los
 * consumidores reales que se verificaron en el frontend:
 *
 *  - ADMIN     → `/panel/precios` (lectura y edición), `/panel/ventas-mayor`,
 *                `/panel/inventario` y `/panel/inventario/:id`.
 *  - TIENDA    → `/panel/ventas-mayor` (`WholesalePage.tsx:113`): el precio del carrito
 *                MAYORISTA sale de aquí, y el servidor cobra `wholesalePrice ?? price1`
 *                (`wholesale.routes.ts:150`). Si el campo desapareciera, el carrito
 *                caería a `price1` y el backend rechazaría el pago por total distinto.
 *                Además edita el precio desde el formulario de producto.
 *  - INVENTARIO→ `/panel/inventario` y `/panel/inventario/:id`, donde el campo
 *                "Precio Mayor" es un input editable sin gate de rol
 *                (`InventoryPage.tsx:592`, `ProductDetailPage.tsx:245`).
 *
 * Reducir este conjunto exige un cambio coordinado en esas pantallas: el input se
 * manda en el guardado como `wholesalePrice: form.wholesalePrice ? Number(...) : null`,
 * así que ocultarlo sin tocar el formulario haría que un guardado borrase el precio
 * mayorista almacenado.
 */
export const ROLES_CON_PRECIO_MAYORISTA = new Set(["ADMIN", "TIENDA", "INVENTARIO"]);

/**
 * Roles autorizados a CONSULTAR el módulo de inventario (`GET /api/inventory` y
 * `GET /api/inventory/product/:productId`).
 *
 * Allow-list, no deny-list, por el mismo motivo que el resto del archivo: el nombre
 * del rol viene de `RoleModel.name`, una tabla data-driven editable desde el panel, así
 * que un rol creado en el futuro caería del lado permitido y vería las existencias de
 * toda la cadena solo por tener sesión.
 *
 * TIENDA entra porque consultar el stock de SU tienda es parte de su flujo funcional
 * (vende y necesita saber qué hay). Lo que TIENDA NO puede hacer es ampliar ese
 * alcance: `tieneAlcanceGlobal` + `resolveLocationScope` lo acotan a su `locationId`.
 */
export const ROLES_CON_INVENTARIO = new Set(["ADMIN", "INVENTARIO", "TIENDA"]);

/**
 * Roles autorizados a AJUSTAR stock/minStock directamente (`PUT /api/inventory/:id`).
 *
 * Es deliberadamente MÁS ESTRECHO que `ROLES_CON_INVENTARIO`: poder consultar
 * existencias no implica poder escribir en ellas. El manual funcional asigna a ADMIN
 * la edición de inventario y a INVENTARIO el control físico de la mercadería, mientras
 * que TIENDA consulta stock, vende y solicita productos: su stock se mueve por los
 * flujos de venta, reposición y devolución, nunca editando el registro a mano.
 *
 * Los dos son roles de `ROLES_CON_VISTA_GLOBAL`, así que el ajuste no necesita acotarse
 * por ubicación: opera sobre la cadena, que es exactamente su périmètre.
 */
export const ROLES_QUE_AJUSTAN_INVENTARIO = new Set(["ADMIN", "INVENTARIO"]);

export interface UsuarioConAlcance {
  role?: string;
  locationId?: number | null;
}

/** ¿Este usuario tiene alcance global sobre todas las ubicaciones? */
export function tieneAlcanceGlobal(user?: UsuarioConAlcance | null): boolean {
  return !!user && ROLES_CON_VISTA_GLOBAL.has(user.role ?? "");
}

/** ¿Este usuario puede ver costos/utilidad/margen? Allow-list, nunca deny-list. */
export function puedeVerCostos(user?: UsuarioConAlcance | null): boolean {
  return !!user && ROLES_CON_COSTOS.has(user.role ?? "");
}

/** ¿Este usuario puede ver el precio mayorista? Allow-list, nunca deny-list. */
export function puedeVerPrecioMayorista(user?: UsuarioConAlcance | null): boolean {
  return !!user && ROLES_CON_PRECIO_MAYORISTA.has(user.role ?? "");
}

/**
 * Resuelve el alcance de ubicación serializado en las respuestas internas.
 *
 * Devuelve `null` para los roles con vista global, y el `locationId` del usuario en
 * cualquier otro caso. Un rol desconocido o sin ubicación devuelve `null`, es decir
 * "sin inventarios visibles", y NUNCA "vista global": quien tiene la vista global la
 * tiene por nombre de rol, no por defecto.
 *
 * Un TIENDA sin ubicación se rechaza antes con `requireTiendaLocation`; aquí ese caso
 * no debe ocurrir y, si ocurre, no amplía el alcance.
 */
export function resolveLocationScope(user?: UsuarioConAlcance | null): number | null {
  if (tieneAlcanceGlobal(user)) return null;
  return user?.locationId ?? null;
}

/**
 * Valor centinela de `alcanceDeFiltro`: el usuario no tiene ubicación asignada, así que
 * no se le puede acotar a ninguna tienda y no debe ver el reporte global.
 */
export const SIN_ALCANCE = -1;

/**
 * Alcance de ubicación para un reporte filtrable.
 *
 * - `null`  → vista global (solo roles de la allow-list).
 * - `> 0`   → forzar el filtro a esa ubicación, ignorando `?locationId`.
 * - `SIN_ALCANCE` → rechazar con 403; el usuario no tiene ubicación.
 *
 * Sustituye al patrón `if (role === "TIENDA")`, que concedía vista global a cualquier
 * otro rol, incluidos los futuros o desconocidos. Aquí por defecto no se concede
 * nada: un rol sin ubicación asignada es rechazado, no ve el reporte global.
 */
export function alcanceDeFiltro(user?: UsuarioConAlcance | null): number | null {
  if (tieneAlcanceGlobal(user)) return null;
  return user?.locationId ?? SIN_ALCANCE;
}

/**
 * Alcance de ubicación para CONSULTAR INVENTARIO (`/api/inventory` y
 * `/api/inventory/product/:productId`), ya resuelto a un valor usable como filtro.
 *
 * Se apoya en `alcanceDeFiltro` y no lo reimplementa:
 *
 *  - `null`   → vista global, sin filtro (solo `ROLES_CON_VISTA_GLOBAL`).
 *  - `> 0`    → forzado a esa ubicación, ignorando el parámetro solicitado. Es lo que
 *               impide a un TIENDA (o a un rol sin vista global) ampliar su alcance con
 *               `?locationId`.
 *  - `SIN_ALCANCE` → sin resultados. Un usuario sin ubicación no ve el inventario de
 *               nadie en vez de caer en la vista global.
 *
 * A diferencia de `alcanceDeFiltro`, aquí el `locationId` solicitado SÍ se aplica, pero
 * solo cuando el rol tiene vista global; para el resto se ignora.
 */
export function alcanceInventario(user: UsuarioConAlcance | null | undefined, locationIdSolicitado?: unknown): number | null {
  const alcance = alcanceDeFiltro(user);
  if (alcance === SIN_ALCANCE) return SIN_ALCANCE;
  if (alcance !== null) return alcance;

  // Vista global: ahora sí se honra el ?locationId pedido.
  if (locationIdSolicitado === undefined || locationIdSolicitado === null || locationIdSolicitado === "") {
    return null;
  }
  const pedido = Number(locationIdSolicitado);
  return Number.isInteger(pedido) ? pedido : SIN_ALCANCE;
}
