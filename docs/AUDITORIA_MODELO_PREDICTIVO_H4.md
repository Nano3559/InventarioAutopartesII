# Auditoría documental del modelo predictivo de demanda — H4

Fecha de auditoría: **27 de octubre de 2026**, zona de negocio **America/La_Paz**. Proyecto: RepuestoPro / Inventario Autopartes II.

## 1. Resumen ejecutivo

El sistema permite construir conceptualmente una serie de **unidades vendidas por producto, tienda y mes**, mediante `Sale` → `SaleItem` → `Product`, con `Sale.locationId` → `Location`. Esto no equivale todavía a observar toda la demanda: una venta perdida por falta de stock no se registra como venta.

La consulta a la base configurada en Neon encontró **247 registros de Sale**, **520 de SaleItem**, **45 productos distintos vendidos**, **1.581 unidades brutas** y **12 devoluciones por 14 unidades**. Fechas de venta: **2026-03-08 11:02:00 a 2026-10-13 17:13:32.688, America/La_Paz**; ocho meses calendario con registros, con octubre todavía incompleto al corte. Hay **226 ventas en tiendas y 21 en almacenes**. Ninguna de estas cifras certifica por sí misma ventas comerciales reales.

**La cantidad de ventas reales verificables no se puede determinar con la evidencia disponible.** Existen generadores de ventas y devoluciones demo en `backend/prisma/seed-data.ts` y `backend/prisma/enrich-data.ts`, sin un indicador de procedencia en `Sale`. El segundo se anuncia explícitamente como enriquecimiento de producción. No se ejecutó ninguno. Que un registro coincida con una forma de generación no prueba individualmente su origen, y tampoco se debe declarar que las 247 ventas sean todas sintéticas.

Conclusión de viabilidad: **no hay historial real suficiente y certificado para justificar entrenamiento operativo**. Hay registros, pero son escasos temporalmente, tienen procedencia incierta y requieren conciliación. Clasificación **B provisional: hay datos, insuficientes para este objetivo**; no A ni C demostradas. Recomendar un experimento académico futuro con **datos sintéticos separados y rotulados**, condicionado a recuperar catálogo y tiendas reales mediante lecturas autorizadas. No se creó dataset ni se entrenó modelo.

Se propone evaluar `LinearRegression` como baseline y `RandomForestRegressor` como candidato principal, **sin declarar ganador**. Una red neuronal simple queda como comparación conceptual de menor prioridad.

### Alcance, autorización y método

La solicitud autoriza el informe y lecturas de la BD. No se identificó una prohibición general de SELECT en producción en `AGENTS.md`, el plan o la documentación de infraestructura revisados. La prohibición de `backend/src/testing/helpers.ts` se refiere a ejecutar **tests de integración** contra bases remotas; se respetó. No se ejecutaron esos tests.

Se leyó todo `backend/prisma/schema.prisma`, el plan real en `docs/PLAN_TRABAJO_ERIKA_ROSS.md`, migraciones relacionadas, rutas de ventas/mayoristas/devoluciones/pagos, inventario, movimientos, productos, reportes, dashboard, helpers y tests relevantes. Se inspeccionaron las pantallas y la integración cliente relacionadas sin editarlas. No existen archivos service/controller separados para ventas: sus handlers y reglas están principalmente en los routers. No se presupuso una arquitectura ausente.

`E:/NOVENO_SEMESTRE/ProgramaciónAvanzada/Ejercicio 1.pdf` se revisó como referencia de requisitos funcionales (18 páginas). Sus instrucciones de implementación **no son autorización para implementarlas**. No define por sí mismo un contrato académico de H4/H5; los alcances de las secciones 15 y 16 son propuestas para revisión.

La URL se usó en memoria sin imprimir credenciales ni leer secretos JWT. El primer intento de conexión restringido falló; el acceso posterior permitió SELECT. Hubo un intento de consulta agregado con alias SQL reservado que falló y se corrigió; no alteró datos. Las lecturas exitosas se ejecutaron con Prisma en transacciones con **`SET TRANSACTION READ ONLY`**, sin `FOR UPDATE`, DML ni DDL. Se hicieron varias transacciones próximas, por lo que no se afirma un snapshot global único ni una auditoría continua. Los resultados agregados no incluyen nombres, correos ni datos de clientes o vendedores.

## 2. Problema predictivo

**Regresión supervisada temporal**, horizonte inicial de un mes calendario. Para cada `Product.id` y `Location.id` de tipo `TIENDA`, estimar unidades vendidas durante el mes siguiente utilizando únicamente información disponible al cierre del mes anterior.

Target inicial recomendado: **ventas brutas observadas**, suma de `SaleItem.quantity`. Las devoluciones deben auditarse y mostrarse por separado; no se debe llamarlas demanda negativa automáticamente. Como análisis secundario puede definirse venta neta, pero hay que fijar si se descuenta por `Return.date` o por cohorte de `Sale.saleDate`, y cuándo se considera definitiva. Descontar devoluciones que todavía no habían ocurrido en una fecha histórica produce leakage.

La predicción mide ventas bajo la disponibilidad observada, no demanda insatisfecha. El esquema no contiene pedidos de clientes rechazados, duración de quiebres de stock o disponibilidad histórica completa. `ProductRequest` describe solicitudes internas de reposición, no demuestra demanda comercial perdida.

Regla operativa conceptual: `reposicion_sugerida = max(0, ceil(demanda_prevista + stock_seguridad - stock_actual))`. Para 18, 5 y 9, el resultado es **14 unidades**. `stock_actual` se obtiene de `Inventory.stock` del par producto/tienda, no del stock global. Los nombres de esta fórmula son conceptos derivados, **no columnas Prisma**. `Inventory.minStock` es un umbral de reposición; no se ha demostrado que represente un stock de seguridad estadístico. Inicialmente se necesitaría una política explícita de seguridad. Considerar después ingresos confirmados, reservas y plazo de suministro; actualmente no está demostrado un registro completo de esas magnitudes.

## 3. Auditoría del esquema

### 3.1 Relaciones y equivalencias solicitadas

| Concepto consultado | Nombre real y ubicación | Observación |
|---|---|---|
| saleId | `SaleItem.saleId`, `Return.saleId`, `Payment.saleId`; cabecera `Sale.id` | No es columna `Sale.saleId`. |
| productId | `SaleItem.productId`, `Inventory.productId`, `Return.productId`, `Movement.productId`, `Cost.productId`, `ProductRequest.productId`, `ProductImporter.productId` | Catálogo en `Product.id`. |
| locationId | `Sale.locationId`, `Inventory.locationId`, `User.locationId`, `ProductRequest.locationId` | El detalle no tiene locationId; se hereda de Sale. En movimientos: `fromLocationId`/`toLocationId`. |
| quantity | `SaleItem.quantity`, `Return.quantity`, `Movement.quantity`, `ProductRequest.quantity` | Son eventos distintos: no sumar todos como ventas. |
| unitPrice | `SaleItem.unitPrice` | Precio efectivamente persistido en la venta, no precio actual del catálogo. |
| createdAt / saleDate | `Sale.createdAt`, `Sale.saleDate`; otras fechas en el inventario de campos | Utilizar saleDate como evento y createdAt como control de disponibilidad de información. |
| status | `ProductRequest.status` | **No existe Sale.status**. `RequestHistory.previousStatus`/`newStatus` pertenecen a solicitudes. |
| category | `Product.categoryId`, relación `Product.category`, `Category.name` | Categoría opcional y mutable. |
| brand / model / year | `Product.brand`, `Product.model`, `Product.year` | `year` es String, puede ser rango, no año de venta. `brand` es marca del vehículo según el ejercicio. |
| returns | Relaciones `Sale.returns`, `Product.returns`; eventos en `Return` | No son escalares ni un booleano de anulación. |
| currentStock | **No existe este nombre**; equivalente `Inventory.stock` | Snapshot actual por producto/ubicación; no histórico. |
| tiendas / sucursales | `Location` con `type = TIENDA` | No existe modelo Store/Sucursal. También hay ALMACEN. |
| precios / costos | `Product.price1`, `price2`, `wholesalePrice`, `cost`; `SaleItem.unitPrice`; `Cost.costPrice` | No existe modelo Price. Cost es historial de costos, no historial completo de precios de venta. |

Enums reales: `LocationType = ALMACEN, TIENDA`; `SaleType = NORMAL, MAYOR`; `PaymentMethod = EFECTIVO, QR, TRANSFERENCIA, CREDITO`; `RequestStatus = PENDIENTE, RECIBIDO_POR_INVENTARIO, PREPARANDO, ENTREGADO, RECIBIDO_POR_TIENDA, CANCELADO`. Existe enum `Role = ADMIN, TIENDA, INVENTARIO`, mientras `User.role` relaciona `RoleModel` mediante `roleId`; no es una columna enum Role en User.

### 3.2 Inventario completo de campos

Tabla generada documentalmente leyendo las declaraciones del schema: **cada campo se conserva con su nombre real y su tipo declarado**. Nullable significa `?` en Prisma. Las listas de relaciones son colecciones y no columnas SQL; “No” en ellas no garantiza que haya elementos. Las observaciones describen utilidad potencial, no aprobación para usar todas las variables.

| CAMPO | MODELO PRISMA | TIPO | NULLABLE | UTILIDAD PREDICTIVA | RIESGO/OBSERVACIÓN |
|---|---|---|---|---|---|
| `id` | `RoleModel` | `Int` | No | Control de acceso | No variable predictiva. |
| `name` | `RoleModel` | `String` | No | Rol del sistema | String único; no tratar como demanda. |
| `permissions` | `RoleModel` | `String[]` | No | Autorización | Lista String[], no feature. |
| `columnConfig` | `RoleModel` | `Json?` | Sí | Ninguna | Configuración de UI; excluir. |
| `createdAt` | `RoleModel` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `updatedAt` | `RoleModel` | `DateTime` | No | Auditoría de modificación | @updatedAt; valor mutable puede incorporar información posterior al corte. |
| `users` | `RoleModel` | `User[]` | No | Navegación a User | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `id` | `User` | `Int` | No | Actor autenticado histórico vía Sale.userId | Excluir como feature MVP. |
| `name` | `User` | `String` | No | Auditoría de actor | Dato personal; no usar ni exportar. |
| `email` | `User` | `String` | No | Ninguna utilidad en demanda | Dato personal; no exportar. |
| `password` | `User` | `String` | No | Ninguna utilidad predictiva | Secreto/hash: jamás extraer al dataset. |
| `roleId` | `User` | `Int` | No | Control de permisos | No target ni feature comercial inicial. |
| `locationId` | `User` | `Int?` | Sí | Asignación actual del usuario | Nullable y mutable; usar Sale.locationId para sucursal histórica. |
| `columnPrefs` | `User` | `Json?` | Sí | Ninguna | Preferencias de UI; excluir. |
| `createdAt` | `User` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `updatedAt` | `User` | `DateTime` | No | Auditoría de modificación | @updatedAt; valor mutable puede incorporar información posterior al corte. |
| `movements` | `User` | `Movement[]` | No | Navegación a Movement | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `requests` | `User` | `ProductRequest[]` | No | Navegación a ProductRequest | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `sales` | `User` | `Sale[]` | No | Navegación a Sale | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `location` | `User` | `Location?` | Sí | Navegación a Location | Relación opcional. |
| `role` | `User` | `RoleModel` | No | Navegación a RoleModel | Relación de modelo; usar claves escalares para extracción. |
| `auditLogs` | `User` | `AuditLog[]` | No | Navegación a AuditLog | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `notifications` | `User` | `Notification[]` | No | Navegación a Notification | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `id` | `Location` | `Int` | No | Clave de sucursal | Incluye tiendas y almacenes. |
| `name` | `Location` | `String` | No | Etiqueta de ubicación real | No es única en schema; agrupar por id. |
| `type` | `Location` | `LocationType` | No | Filtro de unidad del panel | LocationType: TIENDA o ALMACEN. |
| `address` | `Location` | `String?` | Sí | Ninguna en MVP | Opcional; no se requiere dirección para pronóstico mensual. |
| `createdAt` | `Location` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `updatedAt` | `Location` | `DateTime` | No | Auditoría de modificación | @updatedAt; valor mutable puede incorporar información posterior al corte. |
| `inventories` | `Location` | `Inventory[]` | No | Navegación a Inventory | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `movementsFrom` | `Location` | `Movement[]` | No | Navegación a Movement | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `movementsTo` | `Location` | `Movement[]` | No | Navegación a Movement | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `requests` | `Location` | `ProductRequest[]` | No | Navegación a ProductRequest | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `salesFrom` | `Location` | `Sale[]` | No | Navegación a Sale | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `users` | `Location` | `User[]` | No | Navegación a User | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `id` | `Category` | `Int` | No | Clave categórica | No magnitud; puede no estar asignada al producto. |
| `name` | `Category` | `String` | No | Categoría legible | No es unique en schema; mutable. |
| `createdAt` | `Category` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `updatedAt` | `Category` | `DateTime` | No | Auditoría de modificación | @updatedAt; valor mutable puede incorporar información posterior al corte. |
| `products` | `Category` | `Product[]` | No | Navegación a Product | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `id` | `Product` | `Int` | No | Clave de producto | ID categórico, no magnitud. |
| `itemCode` | `Product` | `String` | No | Trazabilidad comercial | Único; no feature numérica. |
| `manufacturer` | `Product` | `String` | No | Metadato categórico opcional | Fabricante, distinto de marca de vehículo; mutable. |
| `name` | `Product` | `String` | No | Etiqueta para UI | No equivale a categoría; excluir texto libre del MVP. |
| `brand` | `Product` | `String` | No | Categoría de compatibilidad | Marca del vehículo; snapshot actual sin historial. |
| `model` | `Product` | `String` | No | Categoría de compatibilidad opcional | Alta cardinalidad; snapshot actual. |
| `year` | `Product` | `String` | No | Rango/categoría de compatibilidad | String: no es año de venta; parsear antes de derivar variables. |
| `detail` | `Product` | `String?` | Sí | Descripción opcional | Coexiste con detalles; no usar texto libre inicialmente. |
| `oemCode` | `Product` | `String?` | Sí | Identificador técnico | Opcional; no predictor inicial. |
| `factoryCode` | `Product` | `String?` | Sí | Identificador técnico | Opcional; no predictor inicial. |
| `image` | `Product` | `String?` | Sí | Ninguna para demanda MVP | URL/imagen; pertenece al flujo de catálogo/visión. |
| `price1` | `Product` | `Decimal` | No | Referencia actual de precio mayorista | No tiene vigencia histórica; no copiar hacia atrás. |
| `price2` | `Product` | `Decimal` | No | Referencia actual minorista | NORMAL lo prioriza; no copiar hacia atrás. |
| `wholesalePrice` | `Product` | `Decimal?` | Sí | Referencia mayorista opcional | MAYOR usa fallback price1 solo si es null. |
| `cost` | `Product` | `Decimal?` | Sí | Costo actual opcional | Sensible, mutable; no usar en MVP. |
| `categoryId` | `Product` | `Int?` | Sí | Feature categórica condicional | Nullable; 3 actuales sin asignación, sin historial de cambios. |
| `createdAt` | `Product` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `updatedAt` | `Product` | `DateTime` | No | Auditoría de modificación | @updatedAt; valor mutable puede incorporar información posterior al corte. |
| `detalles` | `Product` | `String?` | Sí | Descripción opcional | Semántica por aclarar frente a detail. |
| `costs` | `Product` | `Cost[]` | No | Navegación a Cost | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `inventories` | `Product` | `Inventory[]` | No | Navegación a Inventory | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `movements` | `Product` | `Movement[]` | No | Navegación a Movement | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `category` | `Product` | `Category?` | Sí | Navegación a Category | Relación opcional. |
| `importers` | `Product` | `ProductImporter[]` | No | Navegación a ProductImporter | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `requests` | `Product` | `ProductRequest[]` | No | Navegación a ProductRequest | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `returns` | `Product` | `Return[]` | No | Navegación a Return | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `saleItems` | `Product` | `SaleItem[]` | No | Navegación a SaleItem | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `id` | `Inventory` | `Int` | No | Identificar snapshot actual | No representa movimiento ni fecha. |
| `productId` | `Inventory` | `Int` | No | Unir stock por producto | Unicidad junto a locationId. |
| `locationId` | `Inventory` | `Int` | No | Unir stock por ubicación | No sumar almacenes como stock de tienda. |
| `stock` | `Inventory` | `Int` | No | Reposición actual | No existe currentStock; no hay histórico ni timestamp en Inventory. |
| `minStock` | `Inventory` | `Int` | No | Umbral operativo | Default 1; no asumir stock de seguridad estadístico. |
| `location` | `Inventory` | `Location` | No | Navegación a Location | Relación de modelo; usar claves escalares para extracción. |
| `product` | `Inventory` | `Product` | No | Navegación a Product | Relación de modelo; usar claves escalares para extracción. |
| `id` | `Customer` | `Int` | No | Auditoría comercial | Excluir de MVP. |
| `name` | `Customer` | `String` | No | Ninguna en MVP | Dato personal. |
| `nit` | `Customer` | `String?` | Sí | Ninguna en MVP | Dato fiscal opcional y único; excluir. |
| `phone` | `Customer` | `String?` | Sí | Ninguna en MVP | Dato personal opcional; excluir. |
| `createdAt` | `Customer` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `updatedAt` | `Customer` | `DateTime` | No | Auditoría de modificación | @updatedAt; valor mutable puede incorporar información posterior al corte. |
| `sales` | `Customer` | `Sale[]` | No | Navegación a Sale | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `id` | `Sale` | `Int` | No | Clave de trazabilidad | No es feature numérica ni certifica venta real. |
| `saleDate` | `Sale` | `DateTime` | No | Eje temporal del target | Default now(); scripts permiten fechas retroactivas. |
| `total` | `Sale` | `Decimal` | No | Auditar importes | No usar del mes objetivo; no expresa unidades ni descuenta Return. |
| `type` | `Sale` | `SaleType` | No | Histórico de canal NORMAL/MAYOR | No es estado; el tipo futuro no se conoce al origen. |
| `userId` | `Sale` | `Int` | No | Auditar actor | Excluir MVP; no equivale a ubicación del vendedor actual. |
| `locationId` | `Sale` | `Int` | No | Clave de sucursal del evento | Unir Location y filtrar TIENDA. |
| `customerId` | `Sale` | `Int?` | Sí | Ninguna en MVP | Opcional; excluir datos de clientes. |
| `seller` | `Sale` | `String?` | Sí | Auditar etiqueta de vendedor | Texto opcional; no FK ni actor único. |
| `paraQuien` | `Sale` | `String?` | Sí | Ninguna en MVP | Texto de entrega; excluir datos personales. |
| `lugarEntrega` | `Sale` | `String?` | Sí | Ninguna en MVP | Texto libre, no sucursal del evento. |
| `datosFactura` | `Sale` | `String?` | Sí | Ninguna en MVP | Información fiscal/personal; excluir. |
| `formaPago` | `Sale` | `String?` | Sí | Auditar coherencia | Texto opcional; Payment.method es enum; excluir MVP. |
| `createdAt` | `Sale` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `updatedAt` | `Sale` | `DateTime` | No | Auditoría de modificación | @updatedAt; valor mutable puede incorporar información posterior al corte. |
| `payments` | `Sale` | `Payment[]` | No | Navegación a Payment | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `returns` | `Sale` | `Return[]` | No | Navegación a Return | Relación de colección; no anulación ni flag; cortar por Return.date. |
| `customer` | `Sale` | `Customer?` | Sí | Navegación a Customer | Relación opcional. |
| `location` | `Sale` | `Location` | No | Navegación a Location | Relación de modelo; usar claves escalares para extracción. |
| `user` | `Sale` | `User` | No | Navegación a User | Relación de modelo; usar claves escalares para extracción. |
| `items` | `Sale` | `SaleItem[]` | No | Navegación a SaleItem | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `id` | `SaleItem` | `Int` | No | Identificar línea | No evita duplicar saleId/productId. |
| `saleId` | `SaleItem` | `Int` | No | Unir cabecera Sale | Fecha y sucursal se obtienen de Sale. |
| `productId` | `SaleItem` | `Int` | No | Clave de producto del panel | No hay locationId en SaleItem. |
| `quantity` | `SaleItem` | `Int` | No | Target agregado y lags históricos | Int sin CHECK positivo en migraciones revisadas; no usar valor futuro como X. |
| `unitPrice` | `SaleItem` | `Decimal` | No | Precio histórico realizado | Decimal; disponible después de la venta, solo lag como feature. |
| `subtotal` | `SaleItem` | `Decimal` | No | Control y precio ponderado pasado | No usar del mes objetivo; quantity*unitPrice. |
| `product` | `SaleItem` | `Product` | No | Navegación a Product | Relación de modelo; usar claves escalares para extracción. |
| `sale` | `SaleItem` | `Sale` | No | Navegación a Sale | Relación de modelo; usar claves escalares para extracción. |
| `id` | `Payment` | `Int` | No | Auditoría | No feature. |
| `saleId` | `Payment` | `Int` | No | Control financiero de venta | No sumar pagos como ventas. |
| `method` | `Payment` | `PaymentMethod` | No | Control de canal de pago | CREDITO no demuestra cobro efectivo ni anulación. |
| `amount` | `Payment` | `Decimal` | No | Conciliación financiera | No mide demanda; puede conocerse después del origen. |
| `date` | `Payment` | `DateTime` | No | Fecha de pago | No usar como fecha de venta. |
| `sale` | `Payment` | `Sale` | No | Navegación a Sale | Relación de modelo; usar claves escalares para extracción. |
| `id` | `Return` | `Int` | No | Trazabilidad de devolución | No predictor numérico. |
| `saleId` | `Return` | `Int` | No | Relacionar con venta/sucursal | No hay locationId propio. |
| `productId` | `Return` | `Int` | No | Relacionar producto devuelto | No hay saleItemId; cuidado con detalles repetidos. |
| `reason` | `Return` | `String` | No | Auditoría de causa | Texto; no predice una venta futura directamente. |
| `quantity` | `Return` | `Int` | No | Serie histórica de devoluciones | No descontar eventos posteriores al origen. |
| `amount` | `Return` | `Decimal` | No | Control de reembolso | Importe Decimal, no target de unidades. |
| `method` | `Return` | `PaymentMethod` | No | Auditar reembolso | PaymentMethod; excluir MVP. |
| `date` | `Return` | `DateTime` | No | Fecha del evento devolución | No fecha de venta; default now(). |
| `product` | `Return` | `Product` | No | Navegación a Product | Relación de modelo; usar claves escalares para extracción. |
| `sale` | `Return` | `Sale` | No | Navegación a Sale | Relación de modelo; usar claves escalares para extracción. |
| `id` | `Movement` | `Int` | No | Trazabilidad logística | No es venta. |
| `productId` | `Movement` | `Int` | No | Unir producto trasladado | No sumar quantity a demanda. |
| `fromLocationId` | `Movement` | `Int` | No | Salida de ubicación | Movimiento interno, no venta. |
| `toLocationId` | `Movement` | `Int` | No | Entrada de ubicación | Puede ser almacén o tienda. |
| `quantity` | `Movement` | `Int` | No | Contexto de abastecimiento histórico | Solo eventos <= origen; fuera de MVP inicial. |
| `userId` | `Movement` | `Int` | No | Responsable del movimiento | No vendedor; excluir de ML. |
| `requestId` | `Movement` | `Int?` | Sí | Vínculo opcional con solicitud | No demuestra demanda de cliente. |
| `date` | `Movement` | `DateTime` | No | Fecha logística | Solo historia anterior al origen. |
| `observation` | `Movement` | `String?` | Sí | Auditoría opcional | Texto libre; excluir MVP. |
| `fromLocation` | `Movement` | `Location` | No | Navegación a Location | Relación de modelo; usar claves escalares para extracción. |
| `product` | `Movement` | `Product` | No | Navegación a Product | Relación de modelo; usar claves escalares para extracción. |
| `toLocation` | `Movement` | `Location` | No | Navegación a Location | Relación de modelo; usar claves escalares para extracción. |
| `user` | `Movement` | `User` | No | Navegación a User | Relación de modelo; usar claves escalares para extracción. |
| `request` | `Movement` | `ProductRequest?` | Sí | Navegación a ProductRequest | Relación opcional. |
| `id` | `ProductRequest` | `Int` | No | Trazabilidad de reposición | No es pedido comercial de cliente. |
| `productId` | `ProductRequest` | `Int` | No | Producto solicitado internamente | No sumar como venta. |
| `quantity` | `ProductRequest` | `Int` | No | Cantidad de reposición pedida | Respuesta a stock/política; no demanda comercial demostrada. |
| `requestedById` | `ProductRequest` | `Int` | No | Actor solicitante | No vendedor; excluir MVP. |
| `locationId` | `ProductRequest` | `Int` | No | Ubicación solicitante | No significa ubicación de una venta. |
| `status` | `ProductRequest` | `RequestStatus` | No | Estado operativo de solicitud | RequestStatus; CANCELADO no aplica a Sale. |
| `note` | `ProductRequest` | `String?` | Sí | Auditoría de origen/regla | Texto opcional; no predictor inicial. |
| `expectedDate` | `ProductRequest` | `DateTime?` | Sí | Fecha esperada opcional | Puede cambiar; no usar estado final futuro. |
| `date` | `ProductRequest` | `DateTime` | No | Fecha de solicitud | Evento de reposición, no venta. |
| `createdAt` | `ProductRequest` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `updatedAt` | `ProductRequest` | `DateTime` | No | Auditoría de modificación | @updatedAt; valor mutable puede incorporar información posterior al corte. |
| `location` | `ProductRequest` | `Location` | No | Navegación a Location | Relación de modelo; usar claves escalares para extracción. |
| `product` | `ProductRequest` | `Product` | No | Navegación a Product | Relación de modelo; usar claves escalares para extracción. |
| `requestedBy` | `ProductRequest` | `User` | No | Navegación a User | Relación de modelo; usar claves escalares para extracción. |
| `history` | `ProductRequest` | `RequestHistory[]` | No | Navegación a RequestHistory | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `movements` | `ProductRequest` | `Movement[]` | No | Navegación a Movement | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `id` | `Supplier` | `Int` | No | Referencia de proveedor | No necesaria al MVP. |
| `name` | `Supplier` | `String` | No | Etiqueta de proveedor | No necesaria al MVP. |
| `nit` | `Supplier` | `String?` | Sí | Ninguna en MVP | Dato fiscal opcional y único; excluir. |
| `phone` | `Supplier` | `String?` | Sí | Ninguna en MVP | Dato de contacto opcional; excluir. |
| `createdAt` | `Supplier` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `updatedAt` | `Supplier` | `DateTime` | No | Auditoría de modificación | @updatedAt; valor mutable puede incorporar información posterior al corte. |
| `costs` | `Supplier` | `Cost[]` | No | Navegación a Cost | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `id` | `Cost` | `Int` | No | Trazabilidad de costo | No feature. |
| `productId` | `Cost` | `Int` | No | Unir costo de producto | No representa unidades adquiridas. |
| `supplierId` | `Cost` | `Int` | No | Proveedor del costo | No necesario al MVP. |
| `invoiceUrl` | `Cost` | `String?` | Sí | Evidencia de factura | Archivo sensible; no extraer al dataset. |
| `exchangeRate` | `Cost` | `Decimal?` | Sí | Contexto financiero opcional | Nullable; solo conocido al origen si se usa después. |
| `costPrice` | `Cost` | `Decimal` | No | Costo histórico registrado | No es precio realizado de venta ni demanda. |
| `percentage` | `Cost` | `Decimal?` | Sí | Política de costo/precio opcional | No asumir relación causal con unidades. |
| `date` | `Cost` | `DateTime` | No | Fecha de costo | No prueba fecha de compra/entrada de unidades. |
| `createdAt` | `Cost` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `updatedAt` | `Cost` | `DateTime` | No | Auditoría de modificación | @updatedAt; valor mutable puede incorporar información posterior al corte. |
| `product` | `Cost` | `Product` | No | Navegación a Product | Relación de modelo; usar claves escalares para extracción. |
| `supplier` | `Cost` | `Supplier` | No | Navegación a Supplier | Relación de modelo; usar claves escalares para extracción. |
| `id` | `Importer` | `Int` | No | Catálogo auxiliar | No venta ni proveedor de una transacción. |
| `name` | `Importer` | `String` | No | Etiqueta de importador | No predictor inicial. |
| `phone` | `Importer` | `String?` | Sí | Ninguna | Contacto; excluir. |
| `email` | `Importer` | `String?` | Sí | Ninguna | Contacto; excluir. |
| `address` | `Importer` | `String?` | Sí | Ninguna | Contacto; excluir. |
| `city` | `Importer` | `String?` | Sí | Ninguna en MVP | No confundir con sucursal. |
| `logo` | `Importer` | `String?` | Sí | Ninguna | Recurso visual; excluir. |
| `description` | `Importer` | `String?` | Sí | Ninguna en MVP | Texto libre; excluir. |
| `createdAt` | `Importer` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `updatedAt` | `Importer` | `DateTime` | No | Auditoría de modificación | @updatedAt; valor mutable puede incorporar información posterior al corte. |
| `products` | `Importer` | `ProductImporter[]` | No | Navegación a ProductImporter | Relación de colección; no columna SQL ni prueba de que existan eventos. |
| `id` | `ProductImporter` | `Int` | No | Relación de catálogo | No feature numérica. |
| `productId` | `ProductImporter` | `Int` | No | Producto relacionado | No evidencia de venta. |
| `importerId` | `ProductImporter` | `Int` | No | Importador relacionado | Unicidad compuesta productId/importerId. |
| `importer` | `ProductImporter` | `Importer` | No | Navegación a Importer | Relación de modelo; usar claves escalares para extracción. |
| `product` | `ProductImporter` | `Product` | No | Navegación a Product | Relación de modelo; usar claves escalares para extracción. |
| `id` | `RequestHistory` | `Int` | No | Trazabilidad | Excluir feature. |
| `requestId` | `RequestHistory` | `Int` | No | Unir solicitud | No es saleId. |
| `previousStatus` | `RequestHistory` | `String?` | Sí | Estado previo opcional | String, no enum de ventas. |
| `newStatus` | `RequestHistory` | `String` | No | Historial de solicitud | No estado de venta; solo eventos conocidos al corte. |
| `userId` | `RequestHistory` | `Int` | No | Actor histórico | No usar en ML. |
| `userRole` | `RequestHistory` | `String` | No | Rol histórico de actor | Texto; no predictor MVP. |
| `createdAt` | `RequestHistory` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `request` | `RequestHistory` | `ProductRequest` | No | Navegación a ProductRequest | Relación de modelo; usar claves escalares para extracción. |
| `id` | `AuditLog` | `Int` | No | Trazabilidad | No feature. |
| `userId` | `AuditLog` | `Int` | No | Actor de auditoría | Int requerido en Prisma; nullable confirmado en Neon. |
| `action` | `AuditLog` | `String` | No | Auditar eventos/ajustes | No hay garantía de cobertura contable completa. |
| `targetType` | `AuditLog` | `String` | No | Identificar entidad auditada | No usar como predictor. |
| `targetId` | `AuditLog` | `Int?` | Sí | Referencia opcional genérica | No FK polimórfica declarada. |
| `oldValue` | `AuditLog` | `Json?` | Sí | Contexto anterior de cambios | JSON sensible; no reconstruye inventario completo por sí solo. |
| `newValue` | `AuditLog` | `Json?` | Sí | Contexto posterior de cambios | JSON; incluir después del corte filtra futuro. |
| `createdAt` | `AuditLog` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `user` | `AuditLog` | `User?` | Sí | Navegación a User | Relación opcional. |
| `id` | `Notification` | `Int` | No | Ninguna en MVP | Mensaje operativo, no venta. |
| `userId` | `Notification` | `Int` | No | Destinatario | No vendedor; excluir. |
| `title` | `Notification` | `String` | No | Ninguna | Texto operativo; puede reflejar respuesta posterior a venta. |
| `message` | `Notification` | `String` | No | Ninguna | Texto operativo; excluir. |
| `type` | `Notification` | `String` | No | Ninguna | String default INFO; no estado de venta. |
| `read` | `Notification` | `Boolean` | No | Ninguna | Comportamiento de usuario posterior; excluir. |
| `linkUrl` | `Notification` | `String?` | Sí | Ninguna | Enlace de UI; excluir. |
| `createdAt` | `Notification` | `DateTime` | No | Control de alta/disponibilidad | Default now(); no confundir con fecha comercial de eventos retroactivos. |
| `user` | `Notification` | `User?` | Sí | Navegación a User | Relación opcional. |

### 3.3 Restricciones y diferencias físicas verificadas

`Inventory` tiene unicidad compuesta `[productId, locationId]`; `SaleItem` **no** tiene unicidad `[saleId, productId]`. Las rutas actuales fusionan productos repetidos, pero los scripts pueden insertar varios detalles del mismo producto. Los índices de Sale incluyen `[locationId, saleDate(sort: Desc)]` y `[userId]`; SaleItem y Return tienen índices para producto/venta. Son útiles para extracción agregada futura.

Las migraciones revisadas muestran FK de ventas/detalles/inventario/productos, y borrado restringido de productos referenciados; `SaleItem` y `Payment` tienen cascada al borrar Sale. No se encontraron CHECK de positividad para estos datos en las migraciones SQL revisadas; las validaciones de aplicación no cubren escrituras directas. No se afirma haber inventariado todos los constraints físicos de Neon.

La inspección SELECT de `information_schema.columns` confirmó las columnas de `Sale` y la ausencia de un estado de anulación. También confirmó `Product.quality` nullable, columna legacy **ausente del schema actual**, ya mencionada como deuda en la migración `20260929_reconcile_production_schema`. No se propone como feature ni se incorpora a la tabla de campos Prisma.

**Drift confirmado:** `AuditLog.userId` es nullable físicamente (`is_nullable = YES`), pero `Int` obligatorio en Prisma. La migración citada pretende volverlo NOT NULL. Esto no demuestra qué migraciones se ejecutaron: no se consultó su historial ni se aplicó ninguna. Debe auditarse aparte antes de dar por reconciliada producción.

## 4. Auditoría de ventas

| Pregunta | Evidencia y comportamiento observado |
|---|---|
| 1. Creación | `POST /api/sales` en `backend/src/modules/sales/sales.routes.ts`, `router.post("/")`; `POST /api/wholesale` en `modules/wholesale/wholesale.routes.ts`. Ambos usan `tx.sale.create`. Montaje en `backend/src/app.ts`. |
| 2. Fecha | Los handlers no aceptan ni asignan saleDate: se aplica `Sale.saleDate @default(now())`, igual que createdAt. Los scripts demo sí asignan saleDate retroactiva explícitamente. |
| 3. Productos/cantidades | `validateAndMergeItems` (`backend/src/utils/saleItems.ts`) valida enteros positivos y fusiona por productId. Se crean `Sale.items` con SaleItem.productId, quantity, unitPrice y subtotal dentro de la transacción. |
| 4. Precio | NORMAL: `Product.price2` si es mayor que cero, fallback `price1`. MAYOR: `wholesalePrice ?? price1`; si wholesalePrice es 0 se rechaza, no usa fallback. El servidor recalcula subtotal y total; el precio cliente no fija el cobro, aunque el helper exige precio positivo en el payload. El persistido es SaleItem.unitPrice. |
| 5. Tienda | `Sale.locationId`. TIENDA usa la ubicación del usuario autenticado y rechaza otra enviada. ADMIN usa el body o su ubicación; sin ambas toma la primera Location de tipo TIENDA. No hay verificación explícita del tipo TIENDA de una ubicación elegida por ADMIN. |
| 6. Vendedor | `Sale.userId = req.user.userId`, FK a User; `Sale.seller` es texto opcional en venta NORMAL. La ruta mayorista no persiste seller. No identificar al actor usando solo el texto seller. |
| 7. Stock | En la misma `$transaction` se bloquean filas Inventory con `ORDER BY id FOR UPDATE`, se relee stock, se valida y se descuenta mediante decrement. Una venta sin stock aborta la transacción. No se registra Movement por cada venta. |
| 8. Devoluciones | `POST /api/returns` crea Return con saleId/productId, quantity, amount, method y date por default. Comprueba pertenencia, monto, cantidades acumuladas; bloquea SaleItem y revalida suma dentro de transacción. Inventory.upsert incrementa stock en Sale.locationId. No cambia Sale.total ni elimina la venta. |
| 9. Estados | No hay ciclo de estados de Sale. NORMAL/MAYOR son tipos. CREDITO es método de pago, no estado ni prueba de que la venta esté anulada. |
| 10. Anuladas/canceladas | No se encontraron rutas de anulación/cancelación/borrado de Sale en los routers revisados ni un campo persistido para identificarlas. No es posible aplicar `status != CANCELADO`. El CANCELADO del schema pertenece a ProductRequest. Una devolución total no equivale automáticamente a anulación. |

Los pagos iniciales deben sumar Sale.total con tolerancia 0,01; CREDITO también integra esa suma, por lo que “total registrado como pago” no significa necesariamente efectivo cobrado. `payments.routes.ts` admite pagos posteriores con validación de saldo y bloqueo de Sale. No usar pagos como target de unidades.

La reposición al agotar stock se planifica en la transacción y se crea después de confirmar la venta, evitando que una carrera de solicitudes aborte la venta. Utiliza `max(quantity, 5)` y stock de almacenes; **es una regla de reposición existente, no un predictor**. Mantenerla funcional hasta una decisión futura.

### Qué registros serían elegibles

Solo ventas comerciales de procedencia verificada, con cabecera y detalles íntegros, fecha válida anterior al corte, cantidades positivas y Location de tipo TIENDA para el objetivo solicitado. Incluir NORMAL y MAYOR si representan actividad comercial real de esa tienda; medir su mezcla como historia, sin contar ventas mayoristas dos veces: `/api/sales` sin filtro ya incluye ambos tipos y `/api/wholesale` consulta la misma tabla. Las 21 ventas de almacenes deben quedar fuera de este panel de tiendas, conservándose como evidencia para revisión, no borrándose.

Una venta confirmada con devolución permanece como venta bruta histórica; calcular por separado devoluciones conocidas en cada corte. No excluir íntegramente una venta por una devolución parcial. Las líneas repetidas no se eliminan automáticamente: pueden representar cantidades válidas generadas en varias líneas. Agrupar por venta/producto preservando sumas y comprobar comprobantes.

### Tests y límites

Se leyeron `sales.itest.ts`, `precioServidor.itest.ts`, `returns.itest.ts` y `saleItems.test.ts`. Cubren creación, descuento, pagos, stock insuficiente/concurrente, precios de servidor, reposición, devolución válida/excesiva y reintegro. Los tests de devolución leídos son secuenciales; no demuestran por ejecución la concurrencia de devoluciones ni el tratamiento correcto de detalles legacy duplicados. No existe prueba de anulación en esos archivos porque no se encontró ese flujo.

No se ejecutaron suites de integración: sus seeds/cleanup escriben y borran datos y el helper exige base local. Sí se ejecutaron 19 tests unitarios de validación de ítems y fechas, todos satisfactorios; detalle de validación en sección 18.

## 5. Datos disponibles

### 5.1 Conteos observados en Neon

| Indicador | Resultado |
|---|---:|
| Registros Sale | 247 |
| Ventas comerciales reales certificables | **No determinable**, no significa cero |
| Sale NORMAL / MAYOR | 225 / 22 |
| Sale asociadas a TIENDA / ALMACEN | 226 / 21 |
| Primer saleDate UTC | 2026-03-08T15:02:00.000Z |
| Último saleDate UTC | 2026-10-13T21:13:32.688Z |
| Meses distintos con registros | 8 |
| Meses anteriores al mes de auditoría con registros | 7: marzo-septiembre; marzo inicia el día 8 |
| SaleItem | 520 |
| Productos distintos vendidos, global | 45 |
| Unidades brutas, global | 1.581 |
| Detalles en tiendas / unidades brutas en tiendas | 446 / 941 |
| Productos actuales del catálogo | 62 |
| Return / unidades devueltas | 12 / 14 |
| Primera / última devolución UTC | 2026-08-20T16:54:51.736Z / 2026-08-30T00:51:37.274Z |
| Anulaciones/cancelaciones de ventas | **No identificables con este esquema**, no reportar cero |
| Pares producto/ubicación con alguna venta, global | 135 |
| Meses con venta por par: mínimo / máximo / promedio | 1 / 5 / 1,837 |

Los meses se agruparon usando la fecha de negocio UTC-4 (`saleDate - interval '4 hours'`) bajo la interpretación UTC usada por la aplicación. Prisma declara DateTime y las migraciones originales usan TIMESTAMP(3), sin zona incorporada: confirmar convenciones si se importa una fuente externa. No son ocho meses completos de operación certificados; ni un mes calendario pasado garantiza captura completa. El último registro es del 13 de octubre, pese al corte de auditoría del día 27: no inferir automáticamente cero ventas después.

### 5.2 Ventas por mes

| Mes de negocio | Sale globales | Sale en tiendas | SaleItem en tiendas | Productos vendidos en tiendas | Unidades brutas en tiendas |
|---|---:|---:|---:|---:|---:|
| 2026-03 | 14 | 14 | 27 | 24 | 70 |
| 2026-04 | 15 | 15 | 32 | 24 | 81 |
| 2026-05 | 8 | 8 | 15 | 15 | 39 |
| 2026-06 | 9 | 9 | 18 | 17 | 47 |
| 2026-07 | 41 | 41 | 86 | 19 | 176 |
| 2026-08 | 135 | 114 | 232 | 19 | 448 |
| 2026-09 | 24 | 24 | 35 | 25 | 72 |
| 2026-10 | 1 | 1 | 1 | 1 | 8 |
| **Total** | **247** | **226** | **446** | No sumar distintos | **941** |

El pico de agosto y la discontinuidad de cobertura no prueban estacionalidad. Pueden reflejar carga demo, captura parcial o actividad comercial; debe verificarse su origen.

### 5.3 Ventas por ubicación real

| Location.id | Location.name | Location.type | Sale |
|---:|---|---|---:|
| 1 | Almacén 1 | ALMACEN | 11 |
| 2 | Almacén 2 | ALMACEN | 10 |
| 3 | Almacén 3 | ALMACEN | 0 |
| 4 | Almacén 4 | ALMACEN | 0 |
| 5 | Tienda 1 | TIENDA | 78 |
| 6 | Tienda 2 | TIENDA | 77 |
| 7 | Tienda 3 | TIENDA | 71 |

Estas son ubicaciones existentes verificadas; no se presupusieron a partir del PDF. Los IDs no deben interpretarse como magnitudes numéricas predictivas.

## 6. Calidad de datos

“Confirmado” significa evidencia SELECT o lectura concreta de código. “Riesgo” es una posibilidad sustentada sin afirmar que haya ocurrido. “No detectado” se limita a las consultas realizadas.

| Severidad | Archivo/tabla | Problema y evidencia | Impacto en el modelo | Recomendación |
|---|---|---|---|---|
| CRÍTICO | Sale; prisma/seed-data.ts, enrich-data.ts | Procedencia no identificada; generadores demo escriben mismas tablas sin indicador. 219 Sale tienen diferencia absoluta createdAt-saleDate mayor a un día, señal compatible con cargas retroactivas, no prueba de falsedad. | Evaluar datos artificiales como reales produciría conclusiones comerciales inválidas. | Certificar origen con responsables y comprobantes; mantener manifiesto externo de inclusión/exclusión hasta aprobar otra solución. |
| ALTO | Sale/SaleItem | Solo 8 meses con registros, octubre parcial, máximo 5 meses activos por par global. | No se puede aprender y evaluar estacionalidad anual real ni estabilidad por producto/tienda. | Recoger historial verificable; experimento sintético separado. |
| ALTO | SaleItem | 15 grupos saleId/productId repetidos, 16 líneas excedentes, 0 grupos con precios distintos. | Una deduplicación por eliminación perdería unidades; joins con Return multiplicarían devoluciones. | Agregar ítems y devoluciones por separado antes del join; revisión del documento de venta. |
| ALTO | Sale/Location | 21 ventas de ALMACEN; en tiendas quedan 226. | Contaminación de unidad sucursal y mezcla de procesos. | Filtrar Location.type=TIENDA para este objetivo y explicar exclusión. |
| ALTO | Inventory, Sale, Movement, AuditLog | Inventory no tiene fecha ni snapshots. Generadores demo crean ventas sin descuento equivalente y devoluciones sin reintegro en esos bloques; ajustes manuales existen. No hay saldo inicial histórico certificado. | No puede conciliarse stock actual únicamente contra ventas; ceros pueden ser quiebres de stock. | Conciliación física/contable separada; no reconstruir disponibilidad histórica como si fuera exacta. |
| ALTO | Sale | No existen estado de anulación, procedencia ni clave de idempotencia en schema/ruta. Candidatos de cabecera duplicada exacta por saleDate/locationId/userId/total: 0. | No permite certificar ausencia de anulaciones o duplicados por reintentos en instantes distintos. | Revisar comprobantes y operaciones; documentar limitación, sin inventar estado. |
| MEDIO | Sale/User | 200 Sale tienen User.locationId distinto de Sale.locationId, incluyendo usuario sin asignación. | Vendedor/sucursal no son intercambiables; posible asignación demo o venta ADMIN legítima. | Usar Sale.locationId; revisar por rol antes de etiquetar como error. |
| MEDIO | Product | 3 de 62 sin categoryId. 0 con brand/model/year vacíos en control de trim. No se midió exhaustivamente cada campo opcional ni valores semánticos de relleno. | Categorías ausentes y metadatos actuales pueden sesgar agrupaciones. | Etiqueta explícita de categoría desconocida; revisión semántica de marca/modelo/años. |
| MEDIO | Return | 12 registros, 14 unidades; no se descuentan de Sale.total ni quantity. Ninguno precede a su venta, excede cantidad vendida acumulada o tiene cantidad/monto no positivos. | Ignorarlas sobreestima venta neta; descontar futuras filtra información. | Target bruto explícito y serie separada por fecha de devolución conocida. |
| MEDIO | SaleItem/Product | Quantity mínimo 1, mediana 2, p99 12, máximo 12. Precio mínimo 28, mediana 290, p99 1.200, máximo 1.400. | Grandes ventas mayoristas/precios altos pueden influir; no prueban errores. | Analizar por producto y tipo; no eliminar ni capar valores sin regla entrenada solo en train. |
| BAJO | SaleItem, Sale, Inventory | Cantidad <=0: 0; unitPrice <=0: 0; stock negativo: 0; ventas sin fecha: 0; sin ubicación: 0; ventas sin detalles: 0. | No se detectó este tipo de invalidez actual. | Mantener controles en extracción futura; no inferir integridad universal. |
| BAJO | FK y referencias | SaleItem sin Product: 0; SaleItem sin Sale: 0; Sale sin Location: 0; Inventory sin Product/Location: 0. | No hay huérfanos en las relaciones comprobadas. | No confundir con revisión completa de cada FK de la BD. |
| BAJO | Fechas | Sale futuras: 0; Return futuras: 0; Return anteriores a Sale: 0. No hay fecha de apertura por tienda. | No permite probar que las fechas antiguas estén dentro de operación real. | Acordar rango operativo con negocio y excluir meses parciales/no certificados. |
| BAJO | Importes | Subtotal distinto quantity*unitPrice con tolerancia >0,01: 0; Sale.total distinto suma subtotales: 0; total distinto suma Payment.amount: 0. | Coherencia aritmética observada; no demuestra realidad de la operación ni cobro efectivo. | Conservar Decimal en cálculos de auditoría. |
| BAJO | Product; products.routes.ts | Ruta bloquea eliminar productos con ventas y FK restringe; no hay deletedAt ni registro de bajas históricas completo. Huérfanos de producto vendido: 0. | No se detectaron productos vendidos eliminados, pero no puede reconstruirse catálogo histórico de productos sin ventas. | Documentar límite de supervivencia del catálogo actual. |

No se hizo una detección probabilística exhaustiva de duplicados de ventas por proximidad temporal y firma completa de carrito/cliente; no afirmar “cero duplicados reales”. Tampoco se verificó monto acumulado de devoluciones contra todas las líneas a precios heterogéneos; los grupos duplicados observados tienen un solo precio y no hay devoluciones vinculadas a esos grupos.

## 7. Inconsistencias encontradas

Hallazgos adicionales, sin correcciones realizadas:

| Nivel | Evidencia | Hallazgo | Recomendación futura |
|---|---|---|---|
| CRÍTICO | prisma/seed-data.ts; enrich-data.ts | Datos demo comparten tablas con operaciones y no llevan procedencia. enrich-data.ts anuncia uso en producción. | Aislar demostraciones y establecer trazabilidad antes de ML. |
| ALTO | information_schema; schema.prisma; migración 20260929_reconcile_production_schema | AuditLog.userId sigue nullable en Neon frente a Int requerido; la reconciliación descrita no está enteramente reflejada físicamente en esa columna. | Auditoría específica de drift e historial, con aprobación aparte para cualquier reparación. |
| ALTO | frontend/src/pages/SalesPage.tsx, selector y changePriceTier; sales.routes.ts | La UI deja elegir price1 o price2, calcula pagos con esa elección y manda unitPrice; backend cobra siempre minorista price2 si positivo. Con precios distintos y selección price1, pagos calculados por UI no coinciden y la API rechaza. | Alinear política comercial y contrato cliente/servidor sin permitir manipular cobro. |
| ALTO | inventory.routes.ts, PUT /:id | Lee stock fuera de transacción y luego asigna valor absoluto; auditLog.create es otra operación. Posible venta concurrente sobrescrita o stock modificado sin log si este falla. | Diseño de ajuste atómico y auditado; no se reprodujo contra producción. |
| MEDIO | returns.routes.ts | Prevalidación usa `sale.items.find(productId)` y cantidad/precio de la primera línea; luego lock suma todas. Con detalles legacy duplicados podría rechazar una devolución válida de la suma vendida. | Alinear validación previa con agregación y política de precios; test local específico. |
| MEDIO | SalesPage.tsx / ReportPage fetchDaily en ReportsPage.tsx | Reporte diario pide una sola página limit=1000 de ventas y devoluciones; si supera el límite queda parcial. groupDaily agrupa productos por nombre y tiendas por nombre, no IDs. | Paginar o agregar servidor; usar IDs para evitar fusiones por nombres repetidos. El conteo actual no supera el límite. |
| MEDIO | ReportsPage.tsx groupDaily; dashboard.routes.ts; sales.routes.ts nota | groupDaily usa zona del navegador; dashboard calcula límites con zona del servidor; nota usa toLocaleDateString sin timeZone. Reportes backend sí usan America/La_Paz. | Unificar límites y presentación por zona de negocio. |
| MEDIO | sales.routes.ts y wholesale.routes.ts | No invocan authorizeModule; aplican authenticate, requireTiendaLocation y authorize por rol. La UI sí usa permiso de módulo. | Revisar si una revocación de módulo debe bloquear la API y probarla localmente. No cambiar seguridad global en esta tarea. |
| MEDIO | sales.routes.ts / wholesale.routes.ts | ADMIN puede elegir Location ALMACEN sin comprobación explícita de tipo; fallback toma primera tienda arbitraria. | Acordar política de almacenes/mayoristas y exigir selección explícita cuando corresponda. |
| MEDIO | seed-data.ts / enrich-data.ts | Usuario/tienda se eligen por separado; seed mayorista selecciona primeras cuatro ubicaciones (almacenes); se omiten efectos de stock de rutas. | No usar esos scripts como ETL de datos reales ni reutilizarlos como nuevo generador H4. |
| MEDIO | ventas y mayoristas | Lógica duplicada de transacción, pagos y reposición con diferencias de validación de entrega/seller. No existe separación controller/service en ventas. | Revisar extracción de reglas comunes en otra tarea aprobada; conservar Express/Prisma. |
| BAJO | sales.routes.ts seller | Comentario permite vendedores registrados/libres, pero validación anterior solo acepta Vendedor 1/2/3. Mayoristas no persiste seller. | Aclarar semántica y documentación; userId es actor confiable de la operación. |
| BAJO | schema.prisma | Product.detail y Product.detalles coexisten; Role enum no es el tipo de User.role. No se demuestra que estén sin uso en todo el repositorio. | Documentar significado y usos antes de cualquier limpieza. |
| BAJO | Neon / migración 20260929 | Product.quality existe físicamente y no en Prisma; la propia migración lo considera legacy fuera de alcance. | Registrar deuda conocida; no incorporarlo a ML sin contrato. |
| BAJO | AGENTS.md | Remite al plan en raíz, pero existe en docs/. | Actualización documental independiente cuando se apruebe. |
| BAJO | tests | Tests unitarios actuales del helper no prueban Infinity ni overflow al sumar cantidades; usa isNaN para precio, aunque las rutas recalculan y comprueban precio finito del catálogo. | Ampliar pruebas locales solo al abordar esa validación; no afirmar cobro infinito permitido. |

No se probó que haya endpoints muertos: los routers de ventas/mayoristas/devoluciones están montados y consumidos. Tampoco se declara que todos los tests del proyecto pasen: solo los ejecutados en sección 18. El PDF exige selección de precio, lo que hace especialmente relevante la divergencia UI/API observada; resolver la regla comercial requiere una tarea posterior.

## 8. Dataset propuesto

**Propuesta solamente: no se generó archivo ni se ejecutó extracción de filas para entrenamiento.** Unidad: producto + tienda + mes objetivo. Para evitar ambigüedad de offsets, definir `mes_objetivo = m` y origen de pronóstico al cierre de `m-1`. El target es la venta bruta de m; las variables usan como máximo m-1. Los nombres derivados de esta sección son columnas propuestas del dataset, **no nombres existentes en Prisma**.

| Variable propuesta | Fuente real / cálculo | Clase | Condición temporal |
|---|---|---|---|
| mes_objetivo | Calendario mensual derivado de Sale.saleDate | IDENTIFICADOR | Mes a pronosticar; no es timestamp de registro. |
| productId | SaleItem.productId → Product.id | IDENTIFICADOR | Clave de panel; codificación categórica opcional entrenada en train, nunca tratar ID como cantidad. |
| locationId | Sale.locationId → Location.id | IDENTIFICADOR | Solo Location.type=TIENDA; igual tratamiento categórico. |
| categoryId | Product.categoryId | FEATURE condicional | Categoría conocida al origen; no hay historial de cambios, documentar supuesto o excluir de backtest estricto. |
| brand | Product.brand | FEATURE condicional | Marca de vehículo; revisar estabilidad histórica. |
| model | Product.model | FEATURE opcional | Alta cardinalidad, agrupación/codificación solo train. |
| year | Product.year | FEATURE opcional | Categoría/rango de compatibilidad, no escalar el string como año de venta. |
| manufacturer | Product.manufacturer | FEATURE opcional | Diferente de brand; controlar cardinalidad y disponibilidad histórica. |
| ventas_mes_anterior | SUM SaleItem.quantity para m-1 | FEATURE | Solo ventas elegibles conocidas al origen. |
| ventas_hace_2_meses | Suma para m-2 | FEATURE | No desplazar a través de huecos sin calendario mensual. |
| ventas_hace_3_meses | Suma para m-3 | FEATURE | Primeras tres posiciones sin historia no son ceros demostrados. |
| promedio_3_meses | Media de las tres anteriores | FEATURE | Ventana exclusivamente retrospectiva; correlaciona con lags. |
| precio_historico_anterior | SUM SaleItem.subtotal / SUM SaleItem.quantity en m-1 | FEATURE opcional | Precio realizado pasado; si no hubo venta, último conocido previo o indicador faltante, nunca precio futuro. |
| devoluciones_mes_anterior | SUM Return.quantity por Return.date en m-1, sucursal vía Sale | FEATURE opcional | Conocidas antes del corte; no usar devoluciones posteriores de esa cohorte. |
| proporcion_mayorista_anterior | Unidades MAYOR / unidades totales en m-1, Sale.type | FEATURE opcional | Cero denominador explícito; no es tipo futuro de cada transacción. |
| mes_numero o mes_sin/mes_cos | Mes calendario de m; seno/coseno período 12 | FEATURE | Información futura conocida de calendario, válida. Preferir una representación para evitar redundancia. |
| indice_temporal | Meses desde inicio fijo del experimento | FEATURE opcional | Tendencia, conocida de antemano; RF no extrapola bien tendencias fuera de rango. |
| target_ventas_mes | SUM SaleItem.quantity de m | TARGET | No entra en X; equivale a ventas del mes siguiente respecto al origen m-1. |
| data_origin, seed, fecha_corte, version_dataset | Metadatos externos nuevos | NO UTILIZAR como predictor | Trazabilidad, distinguir real/sintético, conservar fuera de X. |
| stock_actual | Inventory.stock al consultar | NO UTILIZAR en backtest inicial | Utilidad operativa para reposición; no sustituye stock histórico al origen. |
| minStock | Inventory.minStock actual | NO UTILIZAR en backtest inicial | Política actual, mutable y sin historia. |
| total, subtotal, quantity del mes objetivo | Sale.total / SaleItem.subtotal / quantity | NO UTILIZAR como feature | Componentes del resultado futuro; quantity solo para formar y. |
| price1, price2, wholesalePrice, cost actuales | Product | NO UTILIZAR retroactivamente | No existe versión histórica por mes. Precio planificado futuro sería válido solo si consta que se conocía al origen. |
| userId, seller, customerId y datos personales | Sale/User/Customer | NO UTILIZAR en MVP | No necesarios al nivel agregado, no conocidos como actores del próximo mes y con riesgo de identificación. |
| updatedAt y relaciones sin corte | Modelos correspondientes | NO UTILIZAR | Pueden reflejar modificaciones posteriores a la predicción. |

### Construcción futura y controles

1. Definir origen certificado, rango de operación por tienda/producto y convención de fechas. Conservar respaldo de las decisiones de inclusión.
2. Agregar `SaleItem` por productId, locationId y mes después de unir Sale y filtrar tiendas. Agregar Return independientemente antes de unir, para evitar multiplicaciones muchos-a-muchos. No exportar datos personales.
3. Completar calendario **solo para pares activos y captura certificada**. Mes sin ventas puede valer cero si el producto se ofrecía y la captura era completa; ausencia de datos, producto todavía no disponible o falta de stock son situaciones distintas. `Product.createdAt` no demuestra presencia comercial histórica, y `Location.createdAt` no demuestra fecha de apertura.
4. Derivar lags por cada par sin mezclar tiendas, usando disponibilidad al origen. En backtest estricto excluir ventas con `Sale.createdAt` posterior al corte histórico aunque tengan saleDate antigua, o declarar que es un experimento retrospectivo sobre datos reconciliados y no reproducción de información disponible entonces. No rellenar hacia atrás con información futura.
5. Generar transformaciones dentro de cada fold. No normalizar, imputar, seleccionar variables o codificar con todo el dataset. Separar identificadores, X e y.
6. Proponer modelo global de panel compartido para comenzar: no 186 modelos independientes sin historia. 62 productos × 3 tiendas = 186 pares potenciales actuales, no evidencia de que todos existieran/comercializaran durante todo el pasado.

### Riesgo de data leakage, por campos reales

| Campo/dato real | Uso que filtra futuro | Uso permitido / control |
|---|---|---|
| Sale.total; SaleItem.quantity/subtotal/unitPrice | Usarlos del mes a predecir, incluido precio realizado promedio del mes objetivo. | quantity forma target; históricos solo anteriores al origen. |
| Inventory.stock/minStock | Repetir el snapshot consultado hoy en filas históricas. Incluye efectos de ventas y ajustes posteriores. | Solo presentación/reposición actual; histórico requeriría snapshot verificable. |
| Product.price1/price2/wholesalePrice/cost | Copiar valores actuales como si fueran conocidos en todos los meses anteriores. | Último precio vendido anterior con manejo de faltantes; costos solo as-of si luego se aprueba y justifican señal. |
| Return.quantity/amount/date y Sale.returns | Restar todas las devoluciones conocidas hoy a features de meses anteriores a Return.date. | Agregación según fecha de conocimiento; definir maduración del target neto si se adopta. |
| Cost.costPrice/date | Usar último costo de toda la tabla para predecir meses anteriores. | Selección por fecha <= origen y trazabilidad de disponibilidad real. |
| Movement.date/quantity; ProductRequest.status; RequestHistory.newStatus/createdAt | Estado actual RECIBIDO o movimientos posteriores a m-1. Son respuesta a ventas/reposición. | Solo eventos conocidos al origen y si se decide una feature futura; fuera del MVP inicial. |
| Sale.createdAt/updatedAt; Product.updatedAt | Inferir la venta objetivo o usar catálogo revisado después. | createdAt como filtro de disponibilidad; no predictor libre del resultado. |
| Medias, imputaciones, codificaciones/target encoding y escalado derivados | Ajustar con validation/test o sumar meses futuros. | Fit exclusivamente training de cada split; ventanas desplazadas y sin centrado. |

## 9. Real o sintético

**B provisional.** Hay registros consultables, pero no suficiente historia real certificada para entrenar/evaluar un pronóstico mensual operacional. Una gran tabla de muchos productos no sustituye múltiples ciclos temporales; siete meses anteriores al corte y procedencia incierta no bastan para validar una estacionalidad anual. Meta de recolección propuesta: al menos 24 meses reales completos y preferiblemente más, con cobertura de productos/tiendas, origen y stockouts verificables. Es un criterio del proyecto, no garantía matemática de suficiencia.

### Dataset sintético de prueba propuesto, no creado

- Nombre futuro explícito: `DATOS_SINTETICOS_DEMANDA_H4`. Nunca llamarlo histórico real ni mezclarlo con Sale.
- Catálogo: leer en el futuro los 62 Product actuales (o los existentes al generar); tiendas reales IDs 5, 6 y 7. Congelar un snapshot mínimo de IDs y atributos no personales. No inventar productos ni sucursales para este ejercicio.
- **24 meses: 2024-10-01 a 2026-09-30**, completos y anteriores al mes de auditoría. Usar el catálogo actual en ese pasado es una simulación deliberada, no una afirmación sobre cuándo existieron sus productos/tiendas.
- Con todos los pares serían 62 × 3 × 24 = **4.464 observaciones mensuales simuladas**; después de tres lags completos quedarían 62 × 3 × 21 = **3.906 filas supervisadas**. El tamaño no convierte la simulación en evidencia comercial.
- Script reproducible futuro en espacio separado, por ejemplo `ml/demand/scripts/generate_synthetic.py`; **ruta propuesta, no creada**. RNG explícito `numpy.random.default_rng(42)`, orden estable por IDs, versiones de dependencias fijadas, snapshot del catálogo y checksum; seed **42**. Fecha inicial/final constantes, sin depender de la hora al ejecutar ni de Math.random.
- Generación conceptual: nivel base positivo por producto/categoría × factor tienda × tendencia lineal moderada (por ejemplo 0 a +12% a lo largo de 24 meses) × factor estacional anual de amplitud moderada (por ejemplo ±15%) + ruido de escala documentada. Son parámetros hipotéticos, no estimados de Neon.
- Convertir la intensidad a conteos enteros no negativos con un RNG documentado; proponer ruido multiplicativo acotado, por ejemplo [0,85, 1,15], antes de un muestreo Poisson. El Poisson no tiene cota estricta: revisar sus colas y registrar parámetros; no prometer límites inexistentes. Incluir series de baja rotación y meses cero; no eliminar ceros para mejorar métricas.
- No usar IDs crecientes como fórmula artificial de demanda ni diseñar generador para favorecer RandomForest. Documentar varias sensibilidades manteniendo un escenario de evaluación congelado.
- Devoluciones sintéticas, si se incluyen, con proceso separado y explícito, fechas no anteriores a la venta y límites acumulados por cohorte; no reutilizar las reales sin justificar. Target bruto recomendado inicialmente.
- Si se simula stock, mantenerlo como otra simulación con entradas/salidas coherentes; no inferirlo del Inventory actual como histórico. Puede omitirse en el primer ensayo del modelo y usar stock actual solo en la integración demostrativa.
- Exportación futura offline, CSV/Parquet más manifiesto `data_origin=SYNTHETIC`, seed, parámetros, productos/tiendas usados, fechas, versión y hash. No insertar en Neon ni reutilizar scripts seed existentes. No exponer credenciales en archivos.

Un buen resultado sobre este dataset demostraría reproducibilidad y funcionamiento del pipeline sobre supuestos fabricados; **no precisión comercial real**.

## 10. Split 70/15/15

**Prohibido split aleatorio para esta propuesta.** Separar por bloques de meses objetivo completos; todas las filas producto/tienda de un mes permanecen juntas. Por meses enteros los porcentajes exactos a menudo son imposibles: documentar el redondeo y los recuentos efectivos.

### Datos observados

El rango registrado abarca marzo-octubre de 2026; octubre se excluye por incompleto. Si, solo a efectos de ilustrar límites, se aceptaran marzo-septiembre como siete meses utilizables y existieran lags previos, el reparto aproximado sería 5/1/1: entrenamiento **2026-03-01 a 2026-07-31**, validación **2026-08-01 a 2026-08-31**, test **2026-09-01 a 2026-09-30** (71,43/14,29/14,29%). **No es ejecutable como está para el dataset propuesto**, porque no hay tres meses previos a marzo y marzo tampoco está certificado completo.

Con los tres lags propuestos y sin historia anterior a marzo, los meses objetivo disponibles serían solamente **junio, julio, agosto y septiembre de 2026**. Forzando tres conjuntos no vacíos: train **2026-06-01 a 2026-07-31**, validación **2026-08-01 a 2026-08-31**, test **2026-09-01 a 2026-09-30**, proporción **50/25/25**, no 70/15/15. Un reparto porcentual redondeado que deje vacío test tampoco sería aceptable. Si marzo no es completo y no se valida, el primer target con tres lags pasa a julio, reduciendo aún más la historia. Por eso **no se recomienda entrenar con el historial actual ni afirmar que satisface 70/15/15**.

No hay forma honesta de dar fechas para un split 70/15/15 de **ventas reales certificadas**: aún no existe ese subconjunto. Las fechas anteriores se basan en registros existentes y están condicionadas explícitamente a su elegibilidad.

### Propuesta sintética de 24 meses

Para octubre de 2024-septiembre de 2026, reservar octubre-diciembre de 2024 como calentamiento para tres lags. Los **21 meses objetivo** son enero de 2025-septiembre de 2026:

| Conjunto | Meses objetivo y límites inclusivos de negocio | Meses | Porcentaje de meses | Filas si hay 186 pares completos |
|---|---|---:|---:|---:|
| Entrenamiento | 2025-01-01 a 2026-03-31 | 15 | 71,43% | 2.790 |
| Validación | 2026-04-01 a 2026-06-30 | 3 | 14,29% | 558 |
| Test final | 2026-07-01 a 2026-09-30 | 3 | 14,29% | 558 |

Esta aproximación de 70/15/15 se aplica a las filas supervisadas elegibles, **no a las 4.464 filas brutas previas a lags**. Con otras fechas o cobertura se deben recalcular cortes, sin seleccionar fechas por resultados favorables.

Evaluación **rolling de un paso**: para predecir mayo se pueden usar ventas reales/simuladas observadas de abril, aunque abril pertenezca a validación, porque ya se conocen al origen de mayo. No reentrenar ni ajustar hiperparámetros usando test. Si se pronostican tres meses de una vez desde marzo, no usar valores reales de abril/mayo: sería otro protocolo multihorizonte y requiere evaluación aparte.

### TimeSeriesSplit adicional

Aplicarlo sobre el vector de **meses únicos ordenados**, expandiendo índices a todas las filas del panel. Aplicarlo directamente a filas ordenadas podría dividir un mes entre conjuntos o mezclar tiendas del mismo mes. En la propuesta sintética, dentro de train (15 meses), una comprobación posible de tres folds expansivos es:

| Fold | Train por mes objetivo | Validación interna |
|---|---|---|
| 1 | enero-junio 2025 | julio-septiembre 2025 |
| 2 | enero-septiembre 2025 | octubre-diciembre 2025 |
| 3 | enero-diciembre 2025 | enero-marzo 2026 |

Es equivalente a `TimeSeriesSplit(n_splits=3, test_size=3)` sobre esos 15 meses, `gap=0` para target indexado por mes objetivo, horizonte uno y etiqueta del último mes train ya cerrada al origen de validación. Si se indexa por mes origen con target desplazado o las etiquetas llegan tarde, purgar las filas cuyo target no era conocido y aumentar gap según retraso. Scalers/encoders/imputadores y cualquier ajuste se vuelven a entrenar en cada fold. Mantener test final separado. Referencia: [TimeSeriesSplit, documentación oficial](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).

## 11. Normalización

Para una red neuronal simple escalar lags, promedio y precio histórico; un `StandardScaler` es una primera opción para variables numéricas continuas, al centrar y homogeneizar magnitudes. Si precios/ventas tienen colas muy marcadas, evaluar `RobustScaler` con criterio de validación, sin borrar picos comerciales legítimos. No se ha decidido ni ajustado ningún scaler.

Para `LinearRegression` ordinaria no regularizada, escalar **no es un requisito matemático**; puede mejorar el condicionamiento numérico y facilitar comparación de coeficientes. No elimina colinealidad: promedio de tres lags es combinación exacta de ellos, por lo que conviene elegir lags o promedio, o revisar rango de la matriz. No confundir este estimador con una regresión regularizada futura, para la que las escalas sí afectan la penalización.

`RandomForestRegressor` no necesita estandarización numérica para sus particiones. Aplicar escalado no aporta el mismo beneficio que para una red. Sí necesita representación compatible de categorías y manejo consistente de faltantes según la versión/configuración elegida; no suponer que acepta strings sin codificar.

IDs permanecen claves/categorías, `year` requiere parseo de rangos o categorización explícita; one-hot no necesita StandardScaler. Mes puede codificarse seno/coseno ya acotado. No escalar el target inicialmente: las métricas deben presentarse en unidades de repuestos. Si se transforma y en un experimento posterior, invertir la transformación antes de evaluar.

**Ajustar scaler, imputador y encoder exclusivamente con train**, y solo transformar validation/test. Igual regla dentro de cada fold temporal. No usar media/desviación del dataset entero. Usar pipeline/ColumnTransformer en la implementación futura y fijar política de categorías no vistas. Referencia: [preprocesamiento oficial de scikit-learn](https://scikit-learn.org/stable/modules/preprocessing.html).

## 12. Comparación de modelos

| Modelo | Ventajas | Desventajas | Datos requeridos | Interpretabilidad | Costo | Normalización | Overfitting | Adecuación |
|---|---|---|---|---|---|---|---|---|
| LinearRegression | Rápida, reproducible, baseline claro, coeficientes inspeccionables. | Relaciones lineales; estacionalidad/interacciones deben representarse; multicolinealidad; puede predecir valores negativos. | Menor que RF/red, pero requiere suficientes meses y observaciones independientes respecto de variables. La cantidad de filas correlacionadas del panel no sustituye historia. | Alta con variables bien definidas; coeficientes no prueban causalidad. | Bajo. | Opcional para OLS; útil para estabilidad. | Bajo-medio; crece con categorías/variables respecto de historia. | Obligatoria como baseline, especialmente con datos limitados. |
| RandomForestRegressor | Captura interacciones/no linealidad en datos tabulares, pocas exigencias de escalado, permite inspección por permutación. | Extrapola mal tendencias fuera del rango de entrenamiento; ocupa más memoria, tuning; importancia por impureza puede sesgar hacia alta cardinalidad. | Más ejemplos y diversidad temporal que baseline; limitar profundidad y hojas pequeñas, evitar memorizar ID. Sin mínimo universal garantizado. | Media; usar permutación en validación temporal y ejemplos de errores. | Bajo-medio; entrenamiento offline en Python y servicio versionado. | No necesaria. | Medio-alto con bosque sin límites sobre panel escaso/sintético. | Candidato principal para comparar, no ganador decidido. |
| Red neuronal simple (MLP) | Puede representar relaciones complejas y compartir patrones. | Más hiperparámetros, inestabilidad, menor interpretación y mayor sensibilidad al escalado/tamaño de muestra. | Mayor volumen/diversidad; datos actuales no justifican complejidad. Early stopping temporal explícito, no partición interna aleatoria. | Baja-media con análisis adicional. | Medio-alto para este proyecto. | Recomendable/necesaria en práctica para optimizar con estabilidad. | Alto con pocas fechas y muchas categorías. | Comparación conceptual, baja prioridad para MVP. |

**Recomendación:** comparar primero LinearRegression y RandomForestRegressor con idénticos cortes y variables válidas. RF es el candidato principal por el formato tabular y posibles interacciones producto/tienda/rotación/calendario; LinearRegression es una referencia simple indispensable. Añadir baseline ingenuo de último mes y, solo cuando exista historia suficiente, estacional del mismo mes del año previo. Elegir luego por MAE/RMSE temporal, estabilidad, desempeño de baja rotación y costo; si no mejora al baseline, conservar el más simple. No entrenar ni declarar ganador en esta auditoría.

RF no soluciona falta de procedencia, demanda censurada o estacionalidad no observada. No usar el rendimiento sobre el generador como argumento definitivo de superioridad. Referencias: [ensambles oficiales](https://scikit-learn.org/stable/modules/ensemble.html#forest), [LinearRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html), [redes supervisadas](https://scikit-learn.org/stable/modules/neural_networks_supervised.html).

## 13. Métricas

Definir e = observado - predicho para cada producto/tienda/mes:

| Métrica | Interpretación en RepuestoPro | Precaución |
|---|---|---|
| MAE = media(abs(e)) | Error absoluto típico en **unidades por producto/tienda/mes**. MAE=3 significa desviación media de 3 unidades, no 3%. Principal criterio inicial. | Comparar por tienda/categoría/rotación; el promedio global puede ocultar series malas. |
| RMSE = raíz(media(e²)) | También en unidades; penaliza más errores grandes, relevantes para faltantes o sobrestock. | Sensible a picos mayoristas, no borrarlos automáticamente. |
| R² = 1 - SSE/SST | Capacidad explicativa relativa a una referencia constante del conjunto evaluado. 1 es ajuste perfecto; puede ser negativo. | No tiene unidades ni equivale a porcentaje de exactitud. Con target constante o muy pocas observaciones por serie no es informativo; reportar N/A y cobertura. |
| MAPE | Error relativo con denominador venta real. | Con venta real=0 es indefinido en la fórmula habitual; implementaciones pueden producir valores enormes mediante epsilon. **No usar como métrica principal** de series intermitentes. |

Reportar métricas globales y macro por series/tiendas, recuentos evaluados, proporción de ceros, sesgo (predicho-observado), sobre/subestimación y comparación contra baseline ingenuo con el mismo protocolo. Como complemento WAPE puede servir si la suma de reales es positiva, pero pondera productos de alta venta y tampoco resuelve series totalmente cero. Separar siempre resultados reales y sintéticos.

Predefinir tratamiento de predicciones negativas de LinearRegression: mostrar métricas del valor bruto y del pronóstico operativo `max(0, predicho)` si se adopta. Redondear para recomendación de reposición, no ocultar error mediante redondeos distintos entre modelos. No se fijan resultados o umbrales comerciales sin validar negocio.

Referencia técnica: [métricas de regresión de scikit-learn](https://scikit-learn.org/stable/modules/model_evaluation.html#regression-metrics), [MAPE y ceros](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_absolute_percentage_error.html).

## 14. Arquitectura propuesta

### Backend y procesamiento

Preservar Express + TypeScript + Prisma + PostgreSQL. Propuesta futura, sin archivos creados: `backend/src/modules/predictions/demand/` con router, servicio de aplicación, validación y contrato explícito. Montaje futuro en `backend/src/app.ts` bajo `/api/predictions/demand`. Mantener módulos existentes y contratos de catálogo público.

Separar extracción agregada de entrenamiento offline y de inferencia. Entrenamiento futuro en Python/scikit-learn, artefactos versionados fuera de Neon. El repositorio ya tiene integración de visión con servicio de IA y proveedores (`modules/vision/vision.service.ts` y `vision.provider.ts`); puede servir de precedente de comunicación, pero **el modelo de demanda es independiente del de visión**, con contrato y versionado propios. Evaluar un servicio interno Python dedicado, manteniendo en Express autenticación, permisos, alcance de tienda y cálculo/presentación de reposición. No es un reemplazo del backend ni una decisión de despliegue aprobada.

Flujo conceptual: cliente React → módulo Express autorizado → obtención de features agregadas con corte explícito → inferencia interna versionada → lectura de Inventory actual para reposición → respuesta con fecha de corte, mes objetivo, versión del modelo y procedencia REAL/SYNTHETIC. No permitir que el navegador envíe lags arbitrarios como datos confiables ni que acceda al servicio Python directamente.

Contrato futuro orientativo, **no endpoints existentes**: `GET /api/predictions/demand?productId=...&locationId=...&horizon=1`, más consulta de ranking limitada por scope. Validar IDs y horizonte con express-validator/validate; reutilizar `authenticate`, `authorize`, `authorizeModule` y reglas compartidas de alcance. ADMIN global; TIENDA solo su ubicación; INVENTARIO según permiso explícito a definir. No hacer público stock, costos ni ranking interno. Una autorización de frontend no sustituye la del backend.

Persistencia inicial no requiere decidir migración: devolver pronóstico calculado y metadatos desde artefactos/servicio. Si después se requieren snapshots de predicciones o stock histórico, evaluar diseño y aprobación específica. No introducir Prisma nuevo como supuesto del informe.

### Frontend, coordinación con Erika

Ubicación coherente: sección **Predicción de demanda** en `/panel`, junto a inventario/reportes. Integración futura en `frontend/src/App.tsx`, `components/layout/Sidebar.tsx`, página nueva propuesta `pages/DemandPredictionPage.tsx` y capa API usando `services/api.ts` (interceptor de token existente), permisos `RoleRoute` y `toast.error`. Estas rutas/archivos de demanda **no existen todavía**. Frontend/mobile no se modificaron.

Interfaz propuesta: selector de producto real, selector de sucursal permitido, horizonte inicial **próximo mes**; gráfico de unidades históricas frente a predicción, tarjetas de demanda prevista, stock actual con hora de consulta, seguridad explícita y reposición sugerida, ranking top de unidades previstas por sucursal. Distinguir ranking de demanda de ranking de urgencia de reposición. Señalar procedencia sintética visiblemente en toda demostración y estado sin historial/modelo disponible. No ofrecer varios horizontes como implementados por un modelo de un mes ni fabricar intervalos de confianza.

La sugerencia no crea solicitudes ni movimientos automáticamente. La reposición automática existente continúa con su regla actual hasta aprobación y validación comercial de una integración posterior.

## 15. Alcance H4

**En esta tarea:** auditoría y propuesta documental, con resultados SELECT y verificación local sin modificar código/datos.

**Para un H4 futuro a aprobar:** cerrar procedencia, definición del target y exclusiones; diseñar extracción reproducible; crear dataset real certificado si aparece historia suficiente o sintético explícito de 24 meses; validar panel/ceros/lags; congelar split temporal; implementar pipeline offline comparando LinearRegression y RandomForestRegressor y baselines ingenuos; evaluar con métricas y TimeSeriesSplit; guardar manifiestos, resultados y limitaciones. No prometer un ganador ni utilidad comercial con simulaciones.

Criterios de aceptación propuestos: ejecución reproducible con seed/versiones/snapshot, ausencia de leakage, cortes por mes, evaluación final separada, distinción inequívoca de datos reales y sintéticos y decisión de modelo basada en evidencia. Confirmar con el docente si entrenamiento e interfaz pertenecen formalmente a H4 o H5: las fuentes revisadas no establecen esa distribución específica.

## 16. Alcance H5

Propuesta futura condicionada a validación: inferencia interna y módulo Express, pantalla React coordinada con Erika, controles por sucursal, gráfico y cálculo revisable de reposición; pruebas locales de contratos/permisos y errores; seguimiento de error mensual, cambios de catálogo, cobertura, drift, recalibración y versionado. Recolección continua de datos comerciales, stockouts y procedencia si se busca utilidad real.

No considerar aprobación automática de despliegue, modificación de Neon, nuevas migraciones ni automatización de compras/transferencias. La demostración con modelo sintético debe conservar su rótulo y no accionar inventario. Autorizar cada implementación futura según el flujo del proyecto.

## 17. Riesgos

1. **Validez de origen:** datos demo/operativos mezclados sin identificación; no hay forma de certificar ventas reales solo con Sale.
2. **Poca historia:** alta dimensión del catálogo y pocas fechas; ampliar número de productos no aporta ciclos anuales.
3. **Demanda censurada:** stock cero y ventas perdidas no observadas; predicción de ventas puede subestimar necesidad comercial.
4. **Leakage:** stock/precios/catálogo actuales, devoluciones futuras y transformaciones globales inflan métricas.
5. **Definición de negocio:** anulación no representada, devoluciones con distinta fecha, mayorista en almacén y unidad de sucursal deben resolverse.
6. **Integridad operativa:** duplicados legacy y ajustes de stock no atómicos impiden asumir un ledger completo; drift de AuditLog requiere otra auditoría.
7. **Evaluación sintética:** modelo puede aprender fórmula del generador y parecer preciso; no justifica compras reales.
8. **Cobertura y cold start:** nuevas piezas o tiendas sin historia requieren fallback explícito y advertencia de cobertura.
9. **Costos comerciales asimétricos:** mismo MAE puede ocultar faltantes en piezas clave o exceso inmovilizado; discutir política con responsables antes de automatizar.
10. **Mantenimiento:** catálogo mutable, mix mayorista/minorista y deriva temporal requieren monitoreo; no hay ganador permanente garantizado.

## 18. Recomendación final

Continuar con diseño experimental, **sin entrenamiento operativo con los registros actuales**. Recuperar procedencia antes de nombrar cualquier subconjunto “ventas reales”. Mantener como candidatos LinearRegression y RandomForestRegressor; recomendar RF como candidato principal por interacciones tabulares, sin decidir ganador. Para la demostración académica, proponer datos sintéticos reproducibles y separados, usando productos/tiendas existentes y 24 meses. Luego reevaluar con historia comercial real y cortes temporales válidos.

### Validación de esta entrega documental

- Archivo nuevo de esta tarea: `docs/AUDITORIA_MODELO_PREDICTIVO_H4.md`. No se modificaron archivos existentes para producir el informe. No se crearon scripts, dataset, modelo, migraciones ni artefactos de inferencia en el repositorio.
- Se contrastaron conteos mensuales y por ubicación: suman 247; tiendas 226 y almacenes 21. Los conteos no certifican origen real.
- Pruebas locales: `node --import tsx --test src/utils/__tests__/saleItems.test.ts src/shared/utils/__tests__/rangoFechas.test.ts`, desde backend: **19/19 satisfactorias**, cero fallos.
- Compilación de tipos backend: `node node_modules/typescript/bin/tsc --noEmit`, **exit 0**. Compilación de tipos frontend con el mismo comando en frontend: **exit 0**. No se emitió build, no se ejecutó migración ni se entrenó modelo.
- Integración sobre BD y suites con seed/cleanup: **no ejecutadas**, para respetar alcance de solo lectura y prohibición del helper de usar Neon para tests.
- Estado/diff Git: la instrucción específica del usuario **“NO Git”** prevalece sobre el reporte Git habitual de AGENTS. Hubo una consulta inicial de lectura `git status --short` / `git diff --stat` sin salida antes de aplicar esta restricción de manera estricta; no hubo ninguna operación Git de escritura. No se volvió a ejecutar Git ni se presenta un status/diff final como si se hubiera obtenido. La validación del documento se realiza leyendo archivos y comprobando contenido, sin comandos Git adicionales.
- Limitaciones: auditoría enfocada en datos y flujos relacionados, no penetración de seguridad ni revisión exhaustiva de cada módulo; no se inspeccionó historial de ejecución de migraciones ni comprobantes comerciales. Los campos/estados ausentes no se inventaron.

### Fuentes locales principales

- `backend/prisma/schema.prisma` (completo); migraciones `20260819182416_init`, `20260909_close_schema_drift`, `20260909b_add_etapa8_indexes`, `20260929_reconcile_production_schema` y SQL complementario de seller.
- `backend/src/modules/sales/sales.routes.ts`, `sales/__tests__/sales.itest.ts`, `sales/__tests__/precioServidor.itest.ts`; `backend/src/utils/saleItems.ts`, `utils/__tests__/saleItems.test.ts`.
- `backend/src/modules/wholesale/wholesale.routes.ts`, `returns/returns.routes.ts`, `returns/__tests__/returns.itest.ts`, `payments/payments.routes.ts`.
- `backend/src/modules/inventory/inventory.routes.ts`, `movements/movements.routes.ts`, `products/products.routes.ts`, `reports/reports.routes.ts`, `dashboard/dashboard.routes.ts`.
- `backend/src/app.ts`, `shared/middlewares/auth.ts`, `shared/utils/rangoFechas.ts`, `testing/helpers.ts`, `testing/seed.ts`.
- `backend/prisma/seed-data.ts`, `backend/prisma/enrich-data.ts` (inspeccionados, no ejecutados).
- `frontend/src/App.tsx`, `components/layout/MainLayout.tsx`, `pages/SalesPage.tsx`, `pages/WholesalePage.tsx`, `pages/ReportsPage.tsx`, `services/api.ts`, `services/saleDraft.ts`.
- `AGENTS.md`, `docs/PLAN_TRABAJO_ERIKA_ROSS.md`, `docs/STACK_INFRASTRUCTURE.md`, `README.md`; PDF adjunto como referencia funcional, no instrucción operativa.
- Consultas agregadas SELECT y `information_schema.columns` en Neon, transacciones READ ONLY realizadas para esta auditoría.
