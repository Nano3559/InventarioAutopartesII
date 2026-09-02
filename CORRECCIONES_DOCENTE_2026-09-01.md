# Correcciones del Docente — 01/09/2026 (verificado en código)

> Estatus: cada punto marcado como **[C]** = confirmado en código (con archivo:línea),
> **[⚡] = pendiente de confirmar/reproducción**, **[✅] = ya implementado correctamente.
> Backend `origin/main` = `96b0af3` · Frontend `origin/main` = `96b0af3`.
> 2ª pasada (01/09/2026): backend 100 % leído (módulos, `prisma`, `seed`, `jobs`, `config`, `app.ts`, middlewares) + frontend auditado por módulo + móvil. Ver "NOTAS — 2ª PASADA" al final.
> 3ª pasada (02/09/2026): tareas de Ross R1-R23 implementadas (backend), migración `add_unique_nit` generada y aplicada en Neon, 18 pruebas automatizadas OK (`npm test`), `tsc` limpio. Pendiente: `prisma generate` (archivo de engine bloqueado por proceso node), recrear admin si hace falta.

---

## A. PENDIENTES CRÍTICOS

|  #  | Punto                                                        | Estado     | Evidencia / detalle                                                                                        |
|-----|--------------------------------------------------------------|------------|------------------------------------------------------------------------------------------------------------|
| A1  | Aplicar autorización por rol en TODAS las rutas backend      | **[✅]**   | `authorizeModule` usado en `movements` (POST) y `prices` (PUT); `authorize("ADMIN")` en users (CRUD+GET), costs (POST/PUT/DELETE), import mayorista y register. (R1) |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A2  | Restringir datos y operaciones a la tienda del usuario       | **[✅]**   | `returns` POST valida `sale.locationId === user.locationId` y `GET /sale/:saleId` aísla por TIENDA; `wholesale` POST tiene lógica TIENDA; `requests`, `payments` y reportes `/sales`+`/monthly` filtran por tienda. (R4/R5/R8/R19/R20/R11) |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A3  | Rol TIENDA accede al Inventario desde App.tsx                | **[✅]**   | Erika (E1): ruta `inventario` incluye `"TIENDA"` en `allowedRoles`; Sidebar oculta enlace para TIENDA (E15). |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A4  | Evitar sobreventas: productos repetidos / ventas simultáneas | **[✅]**   | `sales.routes.ts` y `wholesale.routes.ts` deduplican `items` por `productId` (suma cantidades) vía `utils/saleItems.ts` antes de validar stock, con tests. (R3/R5) |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A5  | Validar cantidades, precios, pagos e IDs en backend          | **[✅]** | Ventas y mayorista validan `quantity>0` (entero) y `unitPrice>0` por ítem (`utils/saleItems.ts`); pagos validados. (R3/R5) |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A6  | Evitar devoluciones superiores a la cantidad vendida         | **[✅]**   | `returns.routes.ts` valida `quantity ≤ saleItem.quantity` y descontando devoluciones previas del mismo sale+product; monto = `unitPrice × quantity`. (R4) |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A7  | Proteger pagos adicionales contra saldo pendiente            | **[✅]** | `payments.routes.ts` POST exige `amount > 0`, no permite superar el pendiente (total − pagado − devuelto) y valida la tienda de la venta. Resumen resta devoluciones. (R20) |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A8  | Botón "Solicitar a almacén" en ProductDetailPage.tsx         | **[✅]**   | Erika (E4): botón conectado a la API; backend POST /requests usa `req.user.userId` y valida tienda. (R8)    |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A9  | Validar ubicación en ventas mayoristas                       | **[✅]**   | `wholesale.routes.ts`: precedencia corregida; TIENDA usa y valida su propia ubicación (403 si body pide otra); ADMIN usa `locationId` del body o la suya. (R5) |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A10 | Restringir CRUD de usuarios a ADMIN                          | **[✅]**   | `users.routes.ts`: `authorize("ADMIN")` en `GET /`, `GET /roles`, `POST`, `PUT /:id` y `DELETE /:id`; solo `/me` y `/me/preferences` quedan autenticados. (R2) |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| A11 | Proteger el endpoint público de registro                     | **[✅]**   | `auth.routes.ts` POST /register ahora usa `authenticate, authorize("ADMIN")`, exige `roleId` (sin default) y valida que el rol/ubicación existan. (R18) |
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
| B2  | Stock nunca negativo                              | **[✅]** | `inventory.routes.ts` PUT valida `stock >= 0` (entero). La sobreventa quedó mitigada con deduplicación (A4). (R10) |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| B3  | Auditoría al modificar stock manualmente          | **[✅]** | `inventory.routes.ts` PUT registra `AuditLog` (old/new stock y minStock) con `userId` del token. (R10)       |
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
| C1  | Búsqueda específica por código OEM                           | **✅/⚡** | Backend `search` incluye `oemCode` en el OR (`products.routes.ts:29`) y hay filtro `?oemCode=` (41). El    |
|     |                                                              |            | buscador de SalesPage usa `search` genérico → OEM ya funcionaría; falta filtro dedicado en la UI.          |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| C2  | Vendedor válido y perteneciente a la tienda                  | **[C]**    | Solo se valida que sea "Vendedor 1/2/3" (`sales.routes.ts:253-255`). No se valida que pertenezca a la      |
|     |                                                              |            | tienda (no hay relación user-vendedor).                                                                    |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| C3  | Probar venta desde el navegador                              | **⚡**     | Docente reporta pantalla negra. Código normal OK (search/cart/pago). Verificar en producción; revisar      |
|     |                                                              |            |`setLocations(r.data)` (locations devuelve array plano) y el modal de pago.                                 |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| C4  | Verificar stock antes/después de venta real                  | **⚡**     | A probar en vivo. Riesgo de A4 (duplicados).                                                               |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| C5  | Dashboard y reportes después de vender                       | **⚡**     | A probar; el dashboard usa datos reales, pero hay bug `criticalStock` inflado (K1).                        |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| C6  | Ventas con productos duplicados                              | **[✅]**   | items deduplicados por productId en POST ventas y mayorista (`utils/saleItems.ts`). (R3/R5)                |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| C7  | Pagos combinados desde la interfaz                           | **✅/⚡**  | Frontend permite múltiples métodos (`addPaymentMethod`). Backend acepta varios pagos. Probar end-to-end.  |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| C8  | Vista/nota de venta sin aislamiento de tienda                | **[✅]**   | `sales.routes.ts` `GET /:id/nota` y `GET /:id` devuelven 403 si TIENDA y la venta es de otra ubicación.    |
|     |                                                              |            |(R19)                                                                                                       |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

---

## D. DEVOLUCIONES

|  #  | Punto                                    | Estado    | Evidencia / detalle                                                                                                             |
|-----|------------------------------------------|---------- |---------------------------------------------------------------------------------------------------------------------------------|
| D1  | No devolver dos veces la misma cantidad  | **[✅]** | `returns.routes.ts` suma devoluciones previas del mismo sale+product y limita la máxima adicional. (R4)                         |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| D2  | Monto devuelto = precio vendido          | **[✅]** | `returns.routes.ts` valida `amount ≈ item.unitPrice × quantity` (±0.01). (R4)                                                   |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| D3  | Impedir devoluciones de otra tienda      | **[✅]** | **POST valida** `sale.locationId === user.locationId` (403 si otra tienda). `GET /returns/sale/:saleId` también aísla por TIENDA.|
|     |                                          |           | (R4/R19)                                                                                                                        |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| D4  | Inventario se incrementa tras devolución | **✅**   | `returns.routes.ts:147-151`: `inventory.upsert` con `increment: quantity`. Correcto.                                             |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

---

## E. SOLICITUDES Y REPOSICIÓN

|  #  | Punto                                             | Estado     | Evidencia / detalle                                                                                              |
|-----|---------------------------------------------------|------------|------------------------------------------------------------------------------------------------------------------|
| E1  | Restringir `requestedById` al usuario autenticado | **[✅]**   | `requests.routes.ts` POST toma `requestedById = req.user.userId` (nunca del body). (R8)                          |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| E2  | Restringir `locationId` a la tienda del usuario   | **[✅]**   | POST: TIENDA usa solo `req.user.locationId` (403 si intenta otra). Detalle `GET /:id` también aísla. (R8)        |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| E3  | Impedir cancelar solicitudes de otras tiendas     | **[✅]**   | DELETE valida: solo ADMIN/INVENTARIO o TIENDA propietaria de la solicitud pueden cancelar. (R8)                  |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| E4  | Flujo Tienda→Inventario→Entrega→Recepción         | **✅/⚡** | Transiciones definidas (`requests.routes.ts:17-24`) y permisos por rol correctos (172-177). Probar E2E.          |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| E5  | Notificaciones al usuario correcto                | **✅**     | Notifican a `existing.requestedById` (210-220) y job notifica a usuarios INVENTARIO.                             |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| E6  | Notificaciones navegan a la solicitud             | **[✅]**   | Rutas manuales y job usan `linkUrl: "/panel/solicitudes"` (el job ya no usa `/requests/:id`). (R9/E9-E10)        |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| E7  | Venta→Stock 0→Solicitud automática→Notif→Prep     | **[C/⚡]** | Se crea solicitud solo si `newStock === 0` y almacén tiene stock (`sales.routes.ts:373-401`). Probar en vivo.    |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| E8  | Reposición cuando stock < mínimo                  | **[✅]**   | El job `replenishJob.ts` ahora genera solicitudes automáticas cuando `stock < minStock` en tiendas (sin solicitud|
|     |                                                   |            | abierta, con disponibilidad en almacén y notificación a INVENTARIO). (R9)                                        |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| E9  | Job no salte estados importantes                  | **[✅]**   | `PENDIENTE → RECIBIDO_POR_INVENTARIO` (respeta `VALID_TRANSITIONS`); no salta directo a PREPARANDO. (R9)         |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| E10 | Enlace del job coincide con ruta frontend         | **[✅]**   | Job genera `/panel/solicitudes`. (R9, duplicado de E6)                                                           |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

---

## F. MOVIMIENTOS

|  #  | Punto                                                | Estado     | Evidencia / detalle                                                                                                |
|-----|------------------------------------------------------|------------|--------------------------------------------------------------------------------------------------------------------|
| F1  | Restringir movimientos a ADMIN/INVENTARIO            | **[✅]**  | `movements.routes.ts` POST usa `authorizeModule("movimientos")` (ADMIN siempre pasa; INVENTARIO tiene el permiso en|
|     |                                                      |            | seed). Ningún TIENDA puede registrar movimientos. (R6)                                                             |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| F2  | Validar origen/destino por tipo de ubicación         | **[✅]**  | POST exige `fromLocation.type === "ALMACEN"` y `toLocation.type === "TIENDA"` (400 en otro caso). (R6)             |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| F3  | Evitar movimientos simultáneos con stock incorrecto  | **[C]**    | `decrement`/`increment` atómicos (95-114) mitigan races, pero sin bloqueo de fila explícito.                       |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| F4  | Probar stock antes/después de movimiento             | **⚡**    | Lógica con transacción OK; probar en vivo.                                                                         |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| F5  | Relacionar movimientos con solicitudes               | **[C]**    | Modelo `Movement` no tiene `requestId`; no se enlaza.                                                              |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

---

## G. COSTOS Y PROVEEDORES

|  #  | Punto                                      | Estado    | Evidencia / detalle                                                                                        |
|-----|--------------------------------------------|-----------|------------------------------------------------------------------------------------------------------------|
| G1  | Restringir costos/proveedores a ADMIN      | **[✅]** | `costs.routes.ts` POST/PUT/DELETE usan `authorize("ADMIN")`; `GET /invoice/:filename` sirve facturas a autenticados. (R7) |
| G2  | Visualizar/descargar facturas subidas      | **[✅]** | Nuevo `GET /api/costs/invoice/:filename` sirve el archivo desde `backend/uploads` (path-safe via `path.basename`, 404 si no existe). (R7)  |
| G3  | Validar MIME real de facturas              | **[✅]** | `multer.fileFilter` verifica extensión Y MIME (`application/pdf`, `image/jpeg`, `image/png`); error 400 con mensaje claro. (R7) |
| G4  | Crear correctamente directorio uploads     | **[✅]** | `costs.routes.ts` crea `backend/uploads` con `fs.mkdirSync(...,{recursive:true})` al cargar el módulo. (R7) |
| G5  | Auditoría de modificaciones/eliminaciones  | **[✅]** | PUT/DELETE registran `AuditLog` CREATE/UPDATE/DELETE_COST con old/new y `userId`. (R7) |
| G6  | Definir cálculo:
  - Costo factura
  - Costo con tipo de cambio
  - Costo con porcentaje
  - Costo tienda +10% | **[C/⚡]** | `Cost` tiene `costPrice/exchangeRate/percentage/invoiceUrl` (`schema.prisma:216`). El **costo tienda +10%** se implementó en `/monthly`: `storeCost = productsCost × 1.1` (G7). Pendiente: validar cómo se calcula el costo con tipo de cambio/porcentaje al crear el Cost. Granularidad: costo es **por factura** (cada Cost = una factura) → OK la parte "por factura". |
| G7  | Mostrar costos de tienda en reporte mensual| **[✅]** | `/monthly` ahora obtiene costos del mes por tienda, calcula `productsCost = Σ costo×cantidad`, `storeCost = productsCost × 1.1` y los suma en summary. (R11) |
| G8  | Unicidad de NIT proveedores y clientes     | **[✅]** | `schema.prisma`: `Customer.nit` y `Supplier.nit` ahora `String? @unique`; migración `20260902130000_add_unique_nit` creada y **aplicada** en Neon. (R12) |

---

## H. PRECIOS

|  #  | Punto                                               | Estado     | Evidencia / detalle                                                                                        |
|-----|-----------------------------------------------------|------------|------------------------------------------------------------------------------------------------------------|
| H1  | Modificación de precios solo autorizados            | **[✅]**  | `prices.routes.ts` `PUT /:productId` → `router.use(authenticate), authorizeModule("precios")` (ADMIN siempre; TIENDA ya no puede fijar precios). (R21) |
| H1b | Validar precio > 0 en PUT precios                   | **[✅]**  | `prices.routes.ts` valida `wholesalePrice > 0` (y numérico finito); 400 si no. (R21) |
| H2  | Precios positivos y numéricos                       | **[✅]**  | Import valida `price1/price2/wholesalePrice` numéricos; PUT mayorista valida `unitPrice/wholesalePrice > 0`. (R5/R21) |
| H3  | Porcentajes 20-80 calculados correctamente          | **⚡**    | `PERCENTAGES=[20..80]` en prices.routes (verificado antes). Probar con fórmula. |
| H4  | "Exportar Excel" genera CSV                         | **[C]**    | Export de precios genera CSV con headers (`prices.routes.ts` /export). Docente pide Excel real or formato correcto. |
| H5  | Usar costo registrado en Cost, no solo Product.cost | **[C]**    | `prices.routes.ts` usa `costs[0]?.costPrice` con fallback a `product.cost` → usa el último Cost, correcto parcialmente (solo último, no el de la factura seleccionada). |

---

## I. VENTA MAYORISTA

|  #  | Punto                                          | Estado     | Evidencia / detalle                                                                                        |
|-----|------------------------------------------------|------------|------------------------------------------------------------------------------------------------------------|
| I1  | Restringir import Excel a ADMIN                | **[✅]**   | `wholesale.routes.ts` `/import` → `router.use(authenticate), authorize("ADMIN")`. (R5) |
| I2  | Validar stock antes de confirmar               | **✅**     | `wholesale.routes.ts:79-89` valida stock por ítem. |
| I3  | Impedir ventas mayoristas con precio cero      | **[✅]**   | `wholesale.routes.ts` exige `unitPrice > 0` por ítem (400 si 0). (R5) |
| I4  | Múltiples métodos de pago en la UI             | **✅**     | Frontend permite varios; backend acepta array (`payments` 24-26). |
| I5  | Validar ubicación de la venta mayorista        | **[✅]**   | Ver A9: precedencia corregida en `wholesale.routes.ts`. TIENDA usa y valida su propia ubicación (403 si body pide otra); ADMIN usa `locationId` del body o su ubicación, con fallback solo si no tiene. (R5) |
| I6  | PDF desde venta persistida, no solo modal      | **[C]**     | `WholesalePage.tsx:174-193` `printNota` genera HTML del objeto en memoria; la venta normal usa html2canvas del modal (`SalesPage.tsx:283-300`). No se genera PDF desde la BD. |
| I7  | PDF incluya cliente, productos, pagos, entrega | **✅**     | `printNota` incluye cliente, fecha, productos, total y pagos. Datos de entrega (lugar/para quién) presentes. |

---

## J. REPORTES

|  #  | Punto                                                | Estado     | Evidencia / detalle                                                                                        |
|-----|------------------------------------------------------|------------|------------------------------------------------------------------------------------------------------------|
| J1  | Filtros por marca, modelo, proveedor, producto       | **[C/⚡]** | `/sales` soporta brand/model y ahora `supplierId` combinado con marca/modelo (backend). UI: Erika preparó filtros de marca/modelo/proveedor; falta que la UI los envíe. (R11/E11) |
| J2  | Filtro proveedor recibe supplierId pero no lo aplica | **[✅]**   | `supplierId` aplicado: `productFilter.costs = { some: { supplierId } }` (unión con brand/model) + totalCount consistente. (R11) |
| J3  | Costos por tienda en reporte mensual                 | **[✅]**   | Ver G7: `/monthly` incluye `costs` del mes por tienda, `productsCost` y `storeCost` (+10%). (R11) |
| J4  | Reportes coinciden con BD | **[C]** | `/sales` suma real. `/monthly` mezcla ventas sin devolver. "Corregir reporte diario para respetar tienda": mensual NO filtra por `req.user` TIENDA (J5). |
| J5  | Reporte diario/mensual respete filtro tienda         | **[✅]**   | `/monthly` filtra ventas y devoluciones por la ubicación del TIENDA (403/usuario TIENDA solo ve su tienda); `/sales` también. (R11) |
| J6  | Rango de fechas a devoluciones                       | **✅**     | Mensual filtra returns por fecha (`reports.routes.ts:228-231`). Endpoint de devoluciones no tiene rango, pero monthly sí. |
| J7  | Excel real cuando se pida Excel                      | **[C]**     | Exports generan CSV (H4). |
| J8  | Escapar comas/comillas/saltos en CSV                 | **⚡**     | Revisar builders CSV (precios/export) para escaping. |
| J9  | Exportación PDF de reportes                          | [C/⚡]     | No hay exportación PDF de reportes; solo venta (html2canvas) y printNota. |
| J10 | Paginación sin clamp en reportes/precios             | **[✅]**   | `reports.routes.ts /sales` (limit ≤500), `prices.routes.ts` GET (limit ≤200) y `wholesale.routes.ts` GET usan `skipClamped/takeClamped`. (R23) |

---

## K. OTROS

|  #  | Punto                                                             | Estado     | Evidencia / detalle                                                                                   |
|-----|-------------------------------------------------------------------|------------|-------------------------------------------------------------------------------------------------------|
| K1  | Bug `criticalStock` inflado (dashboard)                           | **[✅]**  | `dashboard.routes.ts` filtra `stock <= minStock` para `criticalStock` y `productsWithLowStock`. (R15) |
| K2  | Búsqueda por imagen                                               | **[✅]**  | Ruta `POST /products/search-image` ejecuta OCR real del contenido con `tesseract.js` (lenguaje `eng`, datos locales `@tesseract.js-data/eng`); pool de tokens = nombre de archivo + texto OCR. (R16) |
| K3  | Móvil: InventoryScreen/SalesScreen placeholders                   | **[✅]**  | Erika (E10): pantallas completadas, Login real, URL configurable y protección por sesión/rol. |
| K4  | URL backend móvil (localhost)                                     | **[✅]**  | Erika (E10): URL configurable por entorno con respaldo a localhost. |
| K5  | Seed idempotente                                                  | **[✅]**  | `seed-data.ts` guarda por conteo en ventas (NORMAL/MAYOR), movimientos, solicitudes, devoluciones, costos e importadoras (skip + log si ya existen). (R13) |
| K6  | Cantidades seed vs doc                                            | **[C/⚡]**| `seed-data.ts` genera cantidades aleatorias; documentar valores reales. |
| K7  | Migrations vs schema sincronizados                                | **[✅]**  | `prisma migrate status` OK; migración `20260902130000_add_unique_nit` aplicada en Neon (`migrate deploy`); `init` seguida de la nueva migración. (R13) |
| K8  | Estado real producción (Neon/Railway/Vercel)                      | **⚡**    | Vercel fork en `ce645da` (atrasado), `origin/main` = `96b0af3`. Verificar deploy. |
| K9  | Pruebas automatizadas                                             | **[✅]**  | Suite creada (R17): `npm test` = `tsx --test` con 18 tests en `saleItems`, `yearRanges` y `validate` (dedupe/cantidades/precios, rangos de años, validación de esquema). |
| K10 | Docs contradictorios en PLAN_TRABAJO_MARTES                       | **⚡**    | Revisar estados inconsistentes. |
| K11 | Variables de entorno documentadas                                 | [C/⚡]    | `frontend/.env.production` apunta a Railway. No hay `.env.example` documentado para backend (DATABASE_URL, JWT, etc.). |
| K12 | `GET /locations` inconsistente                                    | **[✅]**  | `locations.routes.ts` responde `res.json({ locations })`. (R14) |
| K13 | `JWT_SECRET` por defecto                                          | **[✅]**  | `config/index.ts`: en producción (NODE_ENV=production/railway) **falla al arrancar** si falta o es "secret-key"; en dev solo advierte. Definir `JWT_SECRET` real en Railway. (R18) |
| K14 | Seed otorga a TIENDA permiso `inventario` (inconsistencia con A3) | **[C]**   | `seed.ts:20,29`: `permissions` de TIENDA incluye `inventario`; el `Sidebar.tsx:13,40` muestra el enlace a TIENDA, pero `App.tsx:69-78` redirige a `/panel` ⇒ enlace visible con ruta inaccesible. |
| K15 | Fallback de permisos solo para ADMIN                              | **[C]**   | `authStore.ts:47-57,79-88`: si `GET /permissions/permissions/me` falla, solo ADMIN recibe permisos; un TIENDA quedaría con la sidebar vacía (solo Dashboard). |

---

## TAREAS — ERIKA (FRONTEND)

- [x] E1. `App.tsx:69-78`: agregar `"TIENDA"` a `allowedRoles` de `inventario` e `inventario/:id` (A3).
- [x] E2. Filtros de inventario: UI para Modelo, Año (con rangos `13-`/`13-15`), OEM, Fábrica; conectar `?year=`, `?oemCode=`, `?model=`, `?factoryCode=` (`InventoryPage`). Backend ya soporta.
- [x] E3. Autocompletado de Modelo y Año (solo hay Marca/Fabricante).
- [x] E4. Botón "Solicitar a almacén" (`ProductDetailPage.tsx:135`) → crear solicitud vía API con `requestedById=req.user`.
- [ ] E5. Módulo ventas: reproducir pantalla negra en consola del navegador (body/fondo global `bg-dark-950`); verificar build Vercel (fork en `ce645da` atrasado) — ver C3 y NOTAS al final.
- [ ] E5. Módulo ventas: reproducir pantalla negra en consola del navegador (body/fondo global `bg-dark-950`); verificar build Vercel (fork en `ce645da` atrasado) — ver C3 y NOTAS al final. *(Corrección de render implementada; falta prueba visual en Vercel.)*
- [x] E6. Columna "Proveedor" en inventario y detalle (desde `Cost.supplier`).
- [x] E7. Export de precios como Excel real (o renombrar a CSV) + escapar CSV.
- [x] E8. Import: poder elegir ubicación/stock y validar que exista; opción de fila→ubicación.
- [x] E9. Notificaciones: `linkUrl` correcto a `/panel/solicitudes` y navegar al abrir (E6).
- [x] E10. Móvil: completar InventoryScreen/SalesScreen, Login real, URL backend configurable, protección por sesión/rol (K3, K4).
- [ ] E11. Reportes: filtros de marca/modelo/proveedor/producto en la UI; checkbox no-factura OK. *(UI implementada; falta que el backend aplique proveedor/producto.)*
- [x] E12. PDF mayorista desde datos persistentes (I6) con cliente/productos/pagos/entrega.
- [x] E13. Añadir ErrorBoundary global (cualquier error de render deja pantalla negra por `bg-dark-950`) + revisar consola (C3).
- [x] E14. `authStore.ts`: si falla `GET /permissions/permissions/me`, dar permisos mínimos también para TIENDA (K15).
- [x] E15. Sidebar: ocultar enlace "Inventario" para TIENDA mientras `App.tsx` lo bloquee, o arreglar A3 (K14).

## TAREAS — ROSS (BACKEND)

- [x] R1. Aplicar `authorizeModule` en TODAS las rutas (A1). *(Uso: movements POST `authorizeModule("movimientos")`, prices PUT `authorizeModule("precios")`, más `authorize("ADMIN")` en users/costs/import/register.)*
- [x] R2. `users.routes.ts`: agregar `authorize("ADMIN")` a POST/PUT/DELETE (A10). *(También en GET / y GET /roles.)*
- [x] R3. `sales.routes.ts`: deduplicar `items` por productId, validar `quantity>0`, `unitPrice>0` (A4/A5). *(Utility `utils/saleItems.ts` con tests.)*
- [x] R4. `returns.routes.ts`: descontar devoluciones previas, validar tienda (POST), validar monto = price×qty (A6, D1-D3).
- [x] R5. `wholesale.routes.ts:29`: corregir bug de precedencia; agregar lógica TIENDA; `authorize("ADMIN")` en `/import`; validar precio > 0 (A9, F1, I1, I3).
- [x] R6. `movements.routes.ts`: `authorizeModule("movimientos")` (F1); validar tipos de ubicación (F2).
- [x] R7. `costs.routes.ts`: `authorize("ADMIN")`; endpoint `GET /invoice/:filename` para ver/descargar factura; validar MIME real; crear dir uploads; auditoría (G1-G5).
- [x] R8. `requests.routes.ts`: `requestedById = req.user.userId` en POST; validar `locationId` de TIENDA; restringir DELETE por rol/tienda (E1-E3).
- [x] R9. `replenishJob.ts`: corregir `linkUrl` a `/panel/solicitudes`, no saltar `RECIBIDO_POR_INVENTARIO`, generar reposición por `stock < minStock` (E8-E10).
- [x] R10. `inventory.routes.ts`: validar `stock >= 0`; registrar auditoría en PUT manual (B2-B3).
- [x] R11. Reportes: `supplierId` aplicado en `where` (J2); incluir costos por tienda en `/monthly` (J3); filtrar por tienda del TIENDA (J5); costos tienda +10% (G6-G7).
- [x] R12. schema: `@unique` en `Customer.nit` y `Supplier.nit` (G8). *(Migración `20260902130000_add_unique_nit` creada y aplicada en Neon con `prisma migrate deploy`.)*
- [x] R13. Migration sync + seed idempotente (ventas/movimientos/costos/devueltos) (K5, K7). *(Guardas por conteo en `seed-data.ts`; migrations verificadas sincronizadas.)*
- [x] R14. `GET /locations` consistente con `{locations}` (K12).
- [x] R15. `dashboard.routes.ts`: fix criticalStock (K1).
- [x] R16. Búsqueda por imagen: análisis real del contenido (OCR con `tesseract.js` + datos `eng` locales) (K2).
- [x] R17. Suite de pruebas automatizadas (K9). *(Scripts `npm test`/`npm run test:watch` con `tsx --test`; 18 tests OK.)*
- [x] R18. Proteger `POST /auth/register` (solo ADMIN) + `JWT_SECRET` con fail-fast en producción (A11, K13).
- [x] R19. Aislar por TIENDA: `GET /sales/:id`, `GET /sales/:id/nota`, `GET /returns/sale/:saleId` (C8, D3).
- [x] R20. `payments.routes.ts`: validar `amount > 0`, no superar el pendiente de la venta (resta devoluciones), validar tienda de la venta (A7/C).
- [x] R21. `prices.routes.ts`: `authorizeModule("precios")` en PUT + validar `wholesalePrice > 0` (H1, H1b).
- [x] R22. `yearRanges.ts`: el rango abierto `"13-"` debe cubrir desde el año dado hasta el año actual (B1). *(Ya corregido por Erika: `expandYearRanges` expande hasta `new Date().getFullYear()`; verificado con tests.)*
- [x] R23. Reportes/precios/mayorista: clamp de `skip/take` (J10).

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
