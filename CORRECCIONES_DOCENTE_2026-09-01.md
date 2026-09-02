# Correcciones del Docente — 01/09/2026 (verificado en código)

> Estatus: cada punto marcado como **[C]** = confirmado en código (con archivo:línea),
> **[⚡] = pendiente de confirmar/reproducción**, **[✅] = ya implementado correctamente.
> Backend `origin/main` = `96b0af3` · Frontend `origin/main` = `96b0af3`.
> 2ª pasada (01/09/2026): backend 100 % leído (módulos, `prisma`, `seed`, `jobs`, `config`, `app.ts`, middlewares) + frontend auditado por módulo + móvil. Ver "NOTAS — 2ª PASADA" al final.

---

## A. PENDIENTES CRÍTICOS

|  #  | Punto                                                        | Estado     | Evidencia / detalle                                                                                        |
|-----|--------------------------------------------------------------|------------|------------------------------------------------------------------------------------------------------------|
| A1  | Aplicar autorización por rol en TODAS las rutas backend      | **[C]**    | `authorizeModule` existe en `auth.ts` pero se usa en **0 rutas**. Además, rutas CRUD abiertas solo con     |
|     |                                                              |            |`authenticate`:  usuarios (A7), costos (E2), movimientos (D1), import mayorista (F2).                       |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A2  | Restringir datos y operaciones a la tienda del usuario       | **[C]**    | Ventas y solicitudes GET sí filtran por TIENDA; pero **returns POST** NO valida la tienda de la venta (D3) |
|     |                                                              |            | y **wholesale POST** NO tiene lógica TIENDA (F1).                                                          |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A3  | Rol TIENDA accede al Inventario desde App.tsx                | **[C]**    | `frontend/src/App.tsx:69-78`: rutas `inventario` solo `allowedRoles={["ADMIN","INVENTARIO"]}` → TIENDA es  |
|     |                                                              |            | redirigido. Backend `GET /products` es público, así que solo falla el frontend.                            |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A4  | Evitar sobreventas: productos repetidos / ventas simultáneas | **[C]**    | `sales.routes.ts:307-323`: el chequeo de stock es por ítem contra BD antes de descontar; si `items` trae el|
|     |                                                              |            | mismo productId 2 veces, ambos pasan el check y luego se descuentan 2 veces → posible stock negativo. No   |
|     |                                                              |            | hay deduplicación ni lock.                                                                                 |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A5  | Validar cantidades, precios, pagos e IDs en backend          | **[C/⚡]** | Ventas validan payments y vendedor, pero NO validan `quantity>0` ni `unitPrice>0` por ítem (`sales.routes. |
|     |                                                              |            |ts:243-255`, `saleItemsData` línea 326). Pagos deben igualar el total exacto (línea 337-340). Mayorista     |
|     |                                                              |            | permite precio 0 (F4).                                                                                     |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A6  | Evitar devoluciones superiores a la cantidad vendida         | **[C]**    | `returns.routes.ts:139-141` valida `quantity ≤ saleItem.quantity`, PERO no descuenta devoluciones previas  |
|     |                                                              |            | del mismo sale+product → se puede devolver 2 veces el total.                                               |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A7  | Proteger pagos adicionales contra saldo pendiente            | **[C]**    | No existe concepto de "pago adicional sobre saldo pendiente"; el backend exige `totalPaid === total` exacto|
|     |                                                              |            | (`sales.routes.ts:337-340`). OK para venta única, pero no hay flujo de parcial/adicional.                  |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A8  | Botón "Solicitar a almacén" en ProductDetailPage.tsx         | **[C]**    | `ProductDetailPage.tsx:135`: `<button>` sin `onClick`. Las solicitudes solo se crean por venta (stock 0).  |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A9  | Validar ubicación en ventas mayoristas                       | **[C]**    | **BUG de precedencia**: `wholesale.routes.ts:29` → `user.locationId || locationId ? Number(locationId) :   |
|     |                                                              |            | null`. Con TIENDA que tiene location y sin body `locationId`, `Number(undefined)` = `NaN`.                 |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A10 | Restringir CRUD de usuarios a ADMIN                          | **[C]**    | `users.routes.ts` completo (líneas 10-219): solo `router.use(authenticate)`, **sin** `authorize("ADMIN")`  |
|     |                                                              |            | en POST/PUT/DELETE. Cualquier TIENDA puede crear/editar/borrar usuarios. Además `GET /` (13-39) y `GET /   |
|     |                                                              |            |roles` (42-53) exponen a cualquier autenticado la lista completa (email/rol/ubicación).                     |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A11 | Proteger el endpoint público de registro                     | **[C]**    | `auth.routes.ts:12-58`: `POST /api/auth/register` es **público** y usa `roleId: roleId || 1` (línea 32). En|
|     |                                                              |            | BD fresca el rol id 1 = **ADMIN** (`seed.ts:11-15`) ⇒ cualquiera puede registrarse y obtener token ADMIN.  |
|     |                                                              |            | **Prioridad máxima.**                                                                                      |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

---

## B. INVENTARIO

|  #  | Punto                                             | Estado  | Evidencia / detalle                                                                                                      |
|-----|---------------------------------------------------|---------|--------------------------------------------------------------------------------------------------------------------------|
| B1  | Filtros visibles: modelo, año, OEM, fábrica       | **[C]** | UI solo envía `search/brand/manufacturer` (`InventoryPage.tsx:111-116`). Backend ya soporta `model/year/oemCode/         |
|     |                                                   |         |factoryCode` (`products.routes.ts:40-42,66-69`) pero no se usan. Falta UI de Año + año en el selector. Además `yearRanges.|
|     |                                                   |         |ts:44-58`: `expandYearRanges` trata un rango abierto `"13-"` como **un solo año**(solo 2013) cuando el comentario dice    |
|     |                                                   |         |"2013 en adelante" ⇒ la búsqueda/autocompletado de Año no matchea años posteriores.                                       |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| B2  | Stock nunca negativo                              | **[C]** | `inventory.routes.ts:82-105`: `PUT /:id` acepta cualquier `stock` sin validar `>= 0`. Además la sobreventa (A4) puede    |
|     |                                                   |         | dejar negativo.                                                                                                          |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| B3  | Auditoría al modificar stock manualmente          | **[C]** | `inventory.routes.ts` PUT no registra movimiento/auditoría. Solo existe `Movement` para transferencias.                  |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| B4  | Validar que la ubicación exista en import Excel   | **[C]** | `products.routes.ts:504-507`: con `locationId` inexistente, `findMany` devuelve `[]` y el producto se crea **sin         |
|     |                                                   |         |inventario**, en silencio (no hay error).                                                                                 |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| B5  | Stock importado asignado a la ubicación indicada  | **[C]** | Con `locationId` → upsert con `rowStock` (`products.routes.ts:479-481`). Sin `locationId` → crea en TODAS con stock 0    |
|     |                                                   |         |(504-507). Import acepta un único `locationId` global por archivo (444), no por fila.                                     |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| B6  | Restringir consulta de inventario por rol y tienda| **[C]** | `inventory.routes.ts:11-50` GET no filtra por rol/tienda (cualquiera autenticado ve todo). `GET /api/products`, `/       |
|     |                                                   |         |filters` y `/:id` **ni siquiera usan `authenticate`** (`products.routes.ts:14,112,135`) ⇒ sin login se expone `price1/    |
|     |                                                   |         |price2/wholesalePrice/cost/stock` de todo el catálogo.                                                                    |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| B7  | Columna "Proveedor"                               | **[C]** | No está en `DEFAULT_COLUMNS.inventario` (`permissions.routes.ts:17`). Solo existe `supplier` por Cost.                   |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| B8  | Código fábrica duplicado                          | **[C]** | Import mapea `itemCode ← "Codigo fabrica"` (`products.routes.ts:428`) Y `factoryCode ← "Código fábrica"/"codigo fabrica"`|
|     |                                                   |         | (436). Ambas leen la misma fuente → ambigüedad.                                                                          |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

---

## C. VENTAS NORMALES

|  #  | Punto                                                        | Estado     | Evidencia / detalle                                                                                        |
|-----|--------------------------------------------------------------|------------|------------------------------------------------------------------------------------------------------------|
| C1 | Búsqueda específica por código OEM | **✅/⚡** | Backend `search` incluye `oemCode` en el OR (`products.routes.ts:29`) y hay filtro `?oemCode=` (41). El buscador de SalesPage usa `search` genérico → OEM ya funcionaría; falta filtro dedicado en la UI. |
| C2 | Vendedor válido y perteneciente a la tienda | **[C]** | Solo se valida que sea "Vendedor 1/2/3" (`sales.routes.ts:253-255`). No se valida que pertenezca a la tienda (no hay relación user-vendedor). |
| C3 | Probar venta desde el navegador | **⚡** | Docente reporta pantalla negra. Código normal OK (search/cart/pago). Verificar en producción; revisar `setLocations(r.data)` (locations devuelve array plano) y el modal de pago. |
| C4 | Verificar stock antes/después de venta real | **⚡** | A probar en vivo. Riesgo de A4 (duplicados). |
| C5 | Dashboard y reportes después de vender | **⚡** | A probar; el dashboard usa datos reales, pero hay bug `criticalStock` inflado (K1). |
| C6 | Ventas con productos duplicados | **[C]** | Falta deduplicar `items` por `productId` (ver A4). |
| C7 | Pagos combinados desde la interfaz | **✅/⚡** | Frontend permite múltiples métodos (`addPaymentMethod`). Backend acepta varios pagos. Probar end-to-end. |
| C8 | Vista/nota de venta sin aislamiento de tienda | **[C]** | `sales.routes.ts:73-88` (`GET /:id/nota`) y `208-238` (`GET /:id`) solo usan `authenticate`: un TIENDA puede leer e imprimir la nota de cualquier venta por ID. |

---

## D. DEVOLUCIONES

| # | Punto | Estado | Evidencia / detalle |
|---|-------|--------|----------------------|
| D1 | No devolver dos veces la misma cantidad | **[C]** | `returns.routes.ts:143-153`: valida contra `saleItem.quantity`, no contra devoluciones previas → se puede devolver el total 2 veces (ver A6). |
| D2 | Monto devuelto = precio vendido | **[C]** | `returns.routes.ts:123`: `amount` es libre, no se compara con `item.unitPrice * quantity`. |
| D3 | Impedir devoluciones de otra tienda | **[C]** | GET filtra por TIENDA (`returns.routes.ts:25-29`), pero **POST no valida** `sale.locationId === user.locationId` (131-141). Además `GET /returns/sale/:saleId` (58-99) tampoco aísla por TIENDA: ReturnsPage localiza ventas por ese ID sin límite de tienda. |
| D4 | Inventario se incrementa tras devolución | **✅** | `returns.routes.ts:147-151`: `inventory.upsert` con `increment: quantity`. Correcto. |

---

## E. SOLICITUDES Y REPOSICIÓN

| # | Punto | Estado | Evidencia / detalle |
|---|-------|--------|----------------------|
| E1 | Restringir `requestedById` al usuario autenticado | **[C]** | `requests.routes.ts:103`: toma `requestedById` del body, NO fuerza `req.user.userId`. |
| E2 | Restringir `locationId` a la tienda del usuario | **[C]** | `requests.routes.ts:102`: `locationId` del body sin validar contra tienda del TIENDA (GET sí filtra, POST no). |
| E3 | Impedir cancelar solicitudes de otras tiendas | **[C]** | DELETE (`requests.routes.ts:231-273`) no valida rol ni tienda: cualquier TIENDA puede cancelar cualquier solicitud. |
| E4 | Flujo Tienda→Inventario→Entrega→Recepción | **✅/⚡** | Transiciones definidas (`requests.routes.ts:17-24`) y permisos por rol correctos (172-177). Probar E2E. |
| E5 | Notificaciones al usuario correcto | **✅** | Notifican a `existing.requestedById` (210-220) y job notifica a usuarios INVENTARIO. |
| E6 | Notificaciones navegan a la solicitud | **[C]** | En rutas manuales `linkUrl: "/panel/solicitudes"` (listado). El job usa `/requests/${req.id}` (`replenishJob.ts:46`) que **NO coincide** con la ruta real `/panel/solicitudes`. |
| E7 | Venta→Stock 0→Solicitud automática→Notif→Prep | **[C/⚡]** | Se crea solicitud solo si `newStock === 0` y almacén tiene stock (`sales.routes.ts:373-401`). Probar en vivo. |
| E8 | Reposición cuando stock < mínimo | **[C]** | NO existe: la solicitud automática solo se crea en `newStock === 0`. El job (replenishJob) no genera solicitudes por `stock < minStock`. |
| E9 | Job no salte estados importantes | **[C]** | `replenishJob.ts:24` pasa `PENDIENTE → PREPARANDO` directo, saltando `RECIBIDO_POR_INVENTARIO` que define `VALID_TRANSITIONS` (17-19). |
| E10 | Enlace del job coincide con ruta frontend | **[C]** | Job genera `/requests/:id` (`replenishJob.ts:46`); ruta real `/panel/solicitudes`. (duplicado de E6) |

---

## F. MOVIMIENTOS

| # | Punto | Estado | Evidencia / detalle |
|---|-------|--------|----------------------|
| F1 | Restringir movimientos a ADMIN/INVENTARIO | **[C]** | `movements.routes.ts:10-135`: solo `router.use(authenticate)`, **sin** `authorize("ADMIN","INVENTARIO")` en POST. Cualquier TIENDA puede mover stock. |
| F2 | Validar origen/destino por tipo de ubicación | **[C]** | Solo valida `fromLocationId !== toLocationId` (70-72). No valida tipos (ALMACEN→TIENDA). |
| F3 | Evitar movimientos simultáneos con stock incorrecto | **[C]** | `decrement`/`increment` atómicos (95-114) mitigan races, pero sin bloqueo de fila explícito. |
| F4 | Probar stock antes/después de movimiento | **⚡** | Lógica con transacción OK; probar en vivo. |
| F5 | Relacionar movimientos con solicitudes | **[C]** | Modelo `Movement` no tiene `requestId`; no se enlaza. |

---

## G. COSTOS Y PROVEEDORES

| # | Punto | Estado | Evidencia / detalle |
|---|-------|--------|----------------------|
| G1 | Restringir costos/proveedores a ADMIN | **[C]** | `costs.routes.ts:12-221`: solo `authenticate`, sin `authorize("ADMIN")` en POST/PUT/DELETE. |
| G2 | Visualizar/descargar facturas subidas | **[C]** | Se devuelve `invoiceUrl` (`costs.routes.ts:77,128`) pero **no hay endpoint** para servir el archivo (sin `GET /:id/invoice` ni estático). |
| G3 | Validar MIME real de facturas | **[C]** | `costs.routes.ts:25-29`: filtra solo por extensión (`.pdf/.jpg/...`), no valida MIME real. |
| G4 | Crear correctamente directorio uploads | **[C/⚡]** | `multer.diskStorage` destino `path.join(__dirname,"../../../uploads")` (14-20). Si no existe, falla; falta `fs.mkdirSync(...,{recursive:true})`. |
| G5 | Auditoría de modificaciones/eliminaciones | **[C]** | PUT/DELETE (`costs.routes.ts:143-221`) no registran auditoría. |
| G6 | Definir cálculo:
  - Costo factura
  - Costo con tipo de cambio
  - Costo con porcentaje
  - Costo tienda +10% | **[C]** | `Cost` tiene `costPrice/exchangeRate/percentage/invoiceUrl` (`schema.prisma:216`). **No existe el +10% tienda ni reporte con costos por tienda** (G7). Granularidad: costo es **por factura** (cada Cost = una factura) → OK la parte "por factura". |
| G7 | Mostrar costos de tienda en reporte mensual | **[C]** | `reports.routes.ts /monthly` (210-292) **solo suma ventas/devueltas**, NO costos ni "costo tienda". Portada dice "con costos" pero no calcula. |
| G8 | Unicidad de NIT proveedores y clientes | **[C]** | `schema.prisma`: `Customer.nit` (107) y `Supplier.nit` (206) NO son `@unique`. |

---

## H. PRECIOS

| # | Punto | Estado | Evidencia / detalle |
|---|-------|--------|----------------------|
| H1 | Modificación de precios solo autorizados | **[C]** | `prices.routes.ts:77-105` `PUT /:productId` solo `router.use(authenticate)`, **sin** `authorize("ADMIN")`; cualquier rol puede fijar `wholesalePrice`. |
| H1b | Validar precio > 0 en PUT precios | **[C]** | `prices.routes.ts:82-96` acepta cualquier número (incluso negativo/NaN→aplica `Number` y guarda); no valida > 0. |
| H2 | Precios positivos y numéricos | **[C]** | Import acepta `price1=""→0` (`products.routes.ts:438-440`); el PUT de mayorista no valida > 0 (H1b). |
| H3 | Porcentajes 20-80 calculados correctamente | **⚡** | `PERCENTAGES=[20..80]` en prices.routes (verificado antes). Probar con fórmula. |
| H4 | "Exportar Excel" genera CSV | **[C]** | Export de precios genera CSV con headers (`prices.routes.ts` /export). Docente pide Excel real or formato correcto. |
| H5 | Usar costo registrado en Cost, no solo Product.cost | **[C]** | `prices.routes.ts` usa `costs[0]?.costPrice` con fallback a `product.cost` → usa el último Cost, correcto parcialmente (solo último, no el de la factura seleccionada). |

---

## I. VENTA MAYORISTA

| # | Punto | Estado | Evidencia / detalle |
|---|-------|--------|----------------------|
| I1 | Restringir import Excel a ADMIN | **[C]** | `wholesale.routes.ts:191-265` `/import` solo `router.use(authenticate)`, **sin** `authorize("ADMIN")`. |
| I2 | Validar stock antes de confirmar | **✅** | `wholesale.routes.ts:79-89` valida stock por ítem. |
| I3 | Impedir ventas mayoristas con precio cero | **[C]** | `wholesale.routes.ts:93`: `unitPrice = item.unitPrice || item.wholesalePrice || 0` → puede ser 0 y no se valida. |
| I4 | Múltiples métodos de pago en la UI | **✅** | Frontend permite varios; backend acepta array (`payments` 24-26). |
| I5 | Validar ubicación de la venta mayorista | **[C]** | Ver A9: `wholesale.routes.ts:29` bug de precedencia (`user.locationId || locationId ? Number(locationId) : null`). Además, para **ADMIN sin `locationId`** en el body, el fallback toma la **primera tienda** de la BD (`wholesale.routes.ts:37-43`): la venta del admin va siempre a esa tienda. La UI (`WholesalePage.tsx`) **no tiene selector de ubicación** y nunca envía `locationId`. |
| I6 | PDF desde venta persistida, no solo modal | **[C]** | `WholesalePage.tsx:174-193` `printNota` genera HTML del objeto en memoria; la venta normal usa html2canvas del modal (`SalesPage.tsx:283-300`). No se genera PDF desde la BD. |
| I7 | PDF incluya cliente, productos, pagos, entrega | **✅** | `printNota` incluye cliente, fecha, productos, total y pagos. Datos de entrega (lugar/para quién) presentes. |

---

## J. REPORTES

| # | Punto | Estado | Evidencia / detalle |
|---|-------|--------|----------------------|
| J1 | Filtros por marca, modelo, proveedor, producto | **[C]** | `/sales` soporta brand/model (`reports.routes.ts:38-55`) pero NO `producto` ni `proveedor` en la UI. |
| J2 | Filtro proveedor recibe supplierId pero no lo aplica | **[C]** | `reports.routes.ts:14` deserializa `supplierId` pero **jamás lo usa** en `where`. |
| J3 | Costos por tienda en reporte mensual | **[C]** | Ver G7: `/monthly` no tiene costos. |
| J4 | Reportes coinciden con BD | **[C]** | `/sales` suma real. `/monthly` mezcla ventas sin devolver. "Corregir reporte diario para respetar tienda": mensual NO filtra por `req.user` TIENDA (J5). |
| J5 | Reporte diario/mensual respete filtro tienda | **[C]** | `/monthly` (220-232) trae TODAS las ubicaciones sin filtrar por rol TIENDA. |
| J6 | Rango de fechas a devoluciones | **✅** | Mensual filtra returns por fecha (`reports.routes.ts:228-231`). Endpoint de devoluciones no tiene rango, pero monthly sí. |
| J7 | Excel real cuando se pida Excel | **[C]** | Exports generan CSV (H4). |
| J8 | Escapar comas/comillas/saltos en CSV | **⚡** | Revisar builders CSV (precios/export) para escaping. |
| J9 | Exportación PDF de reportes | [C/⚡] | No hay exportación PDF de reportes; solo venta (html2canvas) y printNota. |
| J10 | Paginación sin clamp en reportes/precios | **[C]** | `reports.routes.ts:57-58` y `prices.routes.ts:28-29` usan `skip/take` crudos del query (sin `Math.min/max(1,...)` como el resto de módulos). |

---

## K. OTROS

| # | Punto | Estado | Evidencia / detalle |
|---|-------|--------|----------------------|
| K1 | Bug `criticalStock` inflado (dashboard) | **[C]** | `dashboard.routes.ts` cuenta `lowStockItems` sin filtrar `stock <= minStock` → reporta números inflados. |
| K2 | Búsqueda por imagen | **[C]** | Analiza nombre de archivo + coincidencias, no visión real del contenido. Ruta `POST /products/search-image`. |
| K3 | Móvil: InventoryScreen/SalesScreen placeholders | **[C]** | Solo `ScannerScreen` funcional. `LoginScreen` con TODO, `InventoryScreen`/`SalesScreen` placeholders. |
| K4 | URL backend móvil (localhost) | **[C]** | `mobile/src/services/api.ts:3` usa `http://localhost:3000/api` fijo; el interceptor agrega el token y en 401 lo borra y cierra sesión (10-27). Falta variable/IP configurable por build. |
| K5 | Seed idempotente | **[C]** | Roles/ubicaciones usan `upsert`, proveedores/clientes `createMany skipDuplicates` (`seed.ts:11-60`, `seed-data.ts:199-206`). Ventas/movimientos/solicitudes/costos **se generan random sin idempotencia** → duplican al re-correr. |
| K6 | Cantidades seed vs doc | **[C/⚡]** | `seed-data.ts` genera cantidades aleatorias; documentar valores reales. |
| K7 | Migrations vs schema sincronizados | **⚡** | Se debe correr `prisma migrate diff`/check. Existe `20260819182416_init`. |
| K8 | Estado real producción (Neon/Railway/Vercel) | **⚡** | Vercel fork en `ce645da` (atrasado), `origin/main` = `96b0af3`. Verificar deploy. |
| K9 | Pruebas automatizadas | **[C]** | No hay suite de tests (autenticación, roles, stock, devoluciones, solicitudes, movimientos, ventas, reportes, imagen). |
| K10 | Docs contradictorios en PLAN_TRABAJO_MARTES | **⚡** | Revisar estados inconsistentes. |
| K11 | Variables de entorno documentadas | [C/⚡] | `frontend/.env.production` apunta a Railway. No hay `.env.example` documentado para backend (DATABASE_URL, JWT, etc.). |
| K12 | `GET /locations` inconsistente | **[C]** | Devuelve array plano (`locations.routes.ts:16`); otros endpoints `{...}`. Frontend parchea con `res.data.locations || res.data`. |
| K13 | `JWT_SECRET` por defecto | **[C]** | `config/index.ts:6`: `process.env.JWT_SECRET || "secret-key"` ⇒ si no se define en Railway, los tokens se firman con una clave pública conocida (validación de tokens/registro ético en riesgo junto a A11). |
| K14 | Seed otorga a TIENDA permiso `inventario` (inconsistencia con A3) | **[C]** | `seed.ts:20,29`: `permissions` de TIENDA incluye `inventario`; el `Sidebar.tsx:13,40` muestra el enlace a TIENDA, pero `App.tsx:69-78` redirige a `/panel` ⇒ enlace visible con ruta inaccesible. |
| K15 | Fallback de permisos solo para ADMIN | **[C]** | `authStore.ts:47-57,79-88`: si `GET /permissions/permissions/me` falla, solo ADMIN recibe permisos; un TIENDA quedaría con la sidebar vacía (solo Dashboard). |

---

## TAREAS — ERIKA (FRONTEND)

- [ ] E1. `App.tsx:69-78`: agregar `"TIENDA"` a `allowedRoles` de `inventario` e `inventario/:id` (A3).
- [ ] E2. Filtros de inventario: UI para Modelo, Año (con rangos `13-`/`13-15`), OEM, Fábrica; conectar `?year=`, `?oemCode=`, `?model=`, `?factoryCode=` (`InventoryPage`). Backend ya soporta.
- [ ] E3. Autocompletado de Modelo y Año (solo hay Marca/Fabricante).
- [ ] E4. Botón "Solicitar a almacén" (`ProductDetailPage.tsx:135`) → crear solicitud vía API con `requestedById=req.user`.
- [ ] E5. Módulo ventas: reproducir pantalla negra en consola del navegador (body/fondo global `bg-dark-950`); verificar build Vercel (fork en `ce645da` atrasado) — ver C3 y NOTAS al final.
- [ ] E6. Columna "Proveedor" en inventario y detalle (desde `Cost.supplier`).
- [ ] E7. Export de precios como Excel real (o renombrar a CSV) + escapar CSV.
- [ ] E8. Import: poder elegir ubicación/stock y validar que exista; opción de fila→ubicación.
- [ ] E9. Notificaciones: `linkUrl` correcto a `/panel/solicitudes` y navegar al abrir (E6).
- [ ] E10. Móvil: completar InventoryScreen/SalesScreen, Login real, URL backend configurable, protección por sesión/rol (K3, K4).
- [ ] E11. Reportes: filtros de marca/modelo/proveedor/producto en la UI; checkbox no-factura OK.
- [ ] E12. PDF mayorista desde datos persistentes (I6) con cliente/productos/pagos/entrega.
- [ ] E13. Añadir ErrorBoundary global (cualquier error de render deja pantalla negra por `bg-dark-950`) + revisar consola (C3).
- [ ] E14. `authStore.ts`: si falla `GET /permissions/permissions/me`, dar permisos mínimos también para TIENDA (K15).
- [ ] E15. Sidebar: ocultar enlace "Inventario" para TIENDA mientras `App.tsx` lo bloquee, o arreglar A3 (K14).

## TAREAS — ROSS (BACKEND)

- [ ] R1. Aplicar `authorizeModule` en TODAS las rutas (A1).
- [ ] R2. `users.routes.ts`: agregar `authorize("ADMIN")` a POST/PUT/DELETE (A10).
- [ ] R3. `sales.routes.ts`: deduplicar `items` por productId, validar `quantity>0`, `unitPrice>0` (A4/A5).
- [ ] R4. `returns.routes.ts`: descontar devoluciones previas, validar tienda (POST), validar monto = price×qty (A6, D1-D3).
- [ ] R5. `wholesale.routes.ts:29`: corregir bug de precedencia; agregar lógica TIENDA; `authorize("ADMIN")` en `/import`; validar precio > 0 (A9, F1, I1, I3).
- [ ] R6. `movements.routes.ts`: `authorize("ADMIN","INVENTARIO")` (F1); validar tipos de ubicación (F2).
- [ ] R7. `costs.routes.ts`: `authorize("ADMIN")`; endpoint para ver/descargar factura; validar MIME; crear dir uploads; auditoría (G1-G5).
- [ ] R8. `requests.routes.ts`: `requestedById = req.user.userId` en POST; validar `locationId` de TIENDA; restringir DELETE por rol/tienda (E1-E3).
- [ ] R9. `replenishJob.ts`: corregir `linkUrl`, no saltar `RECIBIDO_POR_INVENTARIO`, generar reposición por `stock < minStock` (E8-E10).
- [ ] R10. `inventory.routes.ts`: validar `stock >= 0`; registrar auditoría en PUT manual (B2-B3).
- [ ] R11. Reportes: `supplierId` aplicado en `where` (J2); incluir costos por tienda en `/monthly` (J3); filtrar por tienda del TIENDA (J5); costos tienda +10% (G6-G7).
- [ ] R12. $schema$: `@unique` en `Customer.nit` y `Supplier.nit` (G8).
- [ ] R13. Migration sync + seed idempotente (ventas/movimientos/costos/devueltos) (K5, K7).
- [ ] R14. `GET /locations` consistente con pagination/`{locations}` (K12).
- [ ] R15. `dashboard.routes.ts`: fix criticalStock (K1).
- [ ] R16. Búsqueda por imagen: análisis real del contenido, no solo nombre (K2).
- [ ] R17. Suite de pruebas automatizadas (K9).
- [ ] R18. Proteger `POST /auth/register` (solo ADMIN / desactivado) + `JWT_SECRET` real en Railway (A11, K13).
- [ ] R19. Aislar por TIENDA: `GET /sales/:id`, `GET /sales/:id/nota`, `GET /returns/sale/:saleId` (C8, D3).
- [ ] R20. `payments.routes.ts`: validar `amount > 0`, no superar el pendiente de la venta, validar tienda de la venta (A7/C).
- [ ] R21. `prices.routes.ts`: `authorize("ADMIN")` en PUT + validar `wholesalePrice > 0` (H1, H1b).
- [ ] R22. `yearRanges.ts`: el rango abierto `"13-"` debe cubrir desde el año dado hasta el año actual (B1).
- [ ] R23. Reportes/precios: clamp de `skip/take` (J10).

---

## VERIFICACIÓN FINAL

- [ ] Ventas: sin pantalla negra, sin sobreventa con duplicados, stock correcto antes/después.
- [ ] Devoluciones: no doble devolución, solo de propia tienda, monto correcto, stock incrementado.
- [ ] Solicitudes: flujo completo E2E, notificaciones correctas y navegables, cancelación solo propia.
- [ ] Mayorista: precio no 0, ubicación correcta, import solo ADMIN, PDF real.
- [ ] Reportes: proveedor filtrado, costos por tienda, tienda solo su data, Excel real.
- [ ] Movimientos seguros y auditados. Stock nunca negativo.
- [ ] CRUD usuarios/costos/movimientos solo roles permitidos.
- [ ] Seed idempotente + migrations sincronizadas + deploy Vercel actualizado (`ce645da`→`96b0af3`).

---

## NOTAS — 2ª PASADA DE VERIFICACIÓN (01/09/2026)

Backend leído al 100 % (módulos completos, `prisma/schema.prisma`, `seed.ts`/`seed-data.ts`, `jobs/replenishJob.ts`, `config/*`, `server.ts`, `app.ts`, middlewares `auth`/`validate`). Frontend auditado por módulo; móvil revisado.

**Correcciones/confirmaciones de esta pasada:**
- ✅ `public.routes.ts:65-70`: el filtro `?year=` SÍ filtra post-fetch (`yearMatchesRanges`); no es no-op. (Las líneas 35-40 del `where` de Prisma son no-op, pero el filtro JS resuelve.)
- ✅ `permissions.routes.ts`: `PUT /roles/:id/permissions`, `PUT /roles/:id/columns` y `GET /audit` SÍ requieren `authorize("ADMIN")` (50, 95, 135). Solo `GET /roles` y `GET /roles/modules` son `authenticate`.
- ✅ `notifications.routes.ts`: scoped por `userId` del token con ownership checks; sin conflicto `/:id/read` vs `/read-all` (coincide con la UI de `Header`).
- 🚨 **Crítico** — `auth.routes.ts:32` `roleId: roleId || 1` ⇒ `POST /api/auth/register` público crea ADMIN (rol 1 en seed). **Prioridad máxima (A11/R18).**
- 🚨 `users.routes.ts`: CRUD y listado con solo `authenticate` (A10) — escalada directa vía `PUT /users/:id` cambiando `roleId`.
- 🚨 Mayorista (A9/I5): TIENDA **siempre** falla (`Number(undefined)=NaN`), y en modo mayorista el ADMIN no tiene selector de tienda (la venta cae en la primera tienda).
- Seguridad/JWT: `config/index.ts:6` usa `"secret-key"` por defecto y el rol viaja en el payload del token (stale hasta 24 h si un admin cambia el rol) — `auth.ts` `authorize`.
- Pantalla negra ventas (C3/E5): `SalesPage.tsx` (893 líneas) sin error evidente en código; `MainLayout`/`index.css` usan `bg-dark-950` global y no hay ErrorBoundary ⇒ **cualquier** error de render produce una página negra. Repro pendiente en consola del navegador (prod Vercel = fork `ce645da` atrasado vs `96b0af3`).