# Plan de Trabajo — RepuestoPro
## Distribución de tareas

| Quién     | Responsabilidad                                                                     |
|-----------|-------------------------------------------------------------------------------------|
| **Ross**  | TODO el backend: modelos, migraciones, endpoints, seed, lógica                      |
| **Erika** | TODO el frontend: UI de columnas, PDF, reportes, configuración, búsqueda por imagen |

---

## Progreso general

| Área                                         | Estado           |
|----------------------------------------------|----------------- |
| Ross-1 - Backend de columnas                 |  Completo        |
| Ross-2 - Datos de entrega (venta mayor)      |  Completo        |
| Ross-3 - Rol VENDEDOR + categorías           |  Completo        |
| Ross-4 - Rellenar BD (seed)                  |  Completo        |
| Ross-5 - Reposición "al día siguiente"       |  Completo        |
| Extra - Búsqueda por imagen (backend)        |  Completo        |
| Erika-1 - UI de columnas                     |  Completo        |
| Erika-2 - PDF notas/cotización               |  Casi completo   |
| Erika-3 - Reportes flexibles + diario        |  Completo        |
| Erika-4 - Settings rol/categorías            |  Completo        |
| Extra - Búsqueda por imagen (frontend/móvil) |  Pendiente       |
| Deploy final (Vercel + Railway)              |  Pendiente       |

---

# Ross (Backend)

---

## 1. Backend de columnas (ocultar / mostrar / reordenar)

- `PUT /permissions/roles/:id/columns` funciona (permite `columnConfig` con `__categorias`).
- `GET/PUT /users/me/preferences` funciona y Erika lo consume correctamente.
- `GET /permissions/me` devuelve `role`, `permissions`, `columnConfig` (lo usa `authStore`).
- `GET /products/filters` devuelve `categories` (lo usa `SettingsPage`).

- [x] Verificar `PUT /permissions/roles/:id/columns` (`permissions.routes.ts:95-132`).
- [x] Verificar `GET/PUT /users/me/preferences` (`users.routes.ts:165-198`).
- [x] Confirmar `GET /permissions/roles/modules` devuelve las columnas por módulo.
- [x] Confirmar que `columnConfig` del rol incluya columnas reales de Inventario y Ventas.
- [x] Asegurar que devuelvan columnas permitidas por rol **y** por usuario combinadas.

---

## 2. Datos de entrega en venta mayor (BD)

- `Sale` tiene `paraQuien`, `lugarEntrega`, `datosFactura`, `formaPago` (`String?`).
- Migración aplicada a Neon vía `prisma db execute`.
- `wholesale.routes.ts` guarda los 4 campos (literal o inferidos: `paraQuien←clienteName`, `datosFactura←NIT`, `formaPago←primer método de pago`).
- `GET /sales/:id/nota` muestra la sección "Datos de entrega" en notas mayoristas.
- Prueba real en producción ✓ · `npm run build` ✓.

- [x] Agregar a `Sale` los campos de entrega.
- [x] Crear migración SQL y aplicar a Neon (sin `prisma migrate dev`).
- [x] Guardar los campos en `wholesale.routes.ts` al crear la venta mayor.
- [x] Devolver los campos en el response para la nota/PDF.
- [x] Incluirlos en `GET /sales/:id/nota` para la nota.

---

## 3. Rol VENDEDOR (Fernando) con categorías visibles

- Rol `VENDEDOR` (id 4) con permisos `["ventas", "inventario", "solicitudes", "devoluciones"]`.
- `columnConfig.__categorias = ["Frenos", "Motor", "Eléctrico"]`.
- Usuario `fernando@inventario.com / vendedor123` (id 6).
- Login ✓ · `GET /api/permissions/permissions/me` devuelve rol, permisos y categorías ✓.

### Rol y usuario
- [x] Agregar rol `VENDEDOR` al seed/BD.
- [x] Definir los módulos que ve un VENDEDOR (ventas, inventario solo-lectura, solicitudes, devoluciones).
- [x] Crear el usuario "Fernando".

### Categorías visibles por rol
- [x] Campo de categorías permitidas por rol (reuso de `columnConfig.__categorias`).
- [x] `GET /permissions/roles` devuelve `columnConfig` (incluye `__categorias`).
- [x] Actualizar categorías por rol vía `PUT /permissions/roles/:id/columns`.
- [ ] **Filtrado backend** de productos por categoría del rol (VENDEDOR).

> **Nota (decisión):** `GET /products` es público y Erika ya filtra en el frontend. El filtrado en el backend requeriría autenticar el GET; se decidió dejar el filtrado frontend por ahora para no arriesgar rupturas. Mejora futura opcional.

### Verificación
- [x] Como VENDEDOR devuelve módulos y categorías asignados (login + `GET /permissions/me`).
- [x] El frontend de Erika funciona con el rol creado.

---

## 4. Rellenar la base de datos (seed)

- **56 productos** (antes 19) en las 7 categorías.
- **112 costos** (2 por producto, con proveedor, tipo de cambio, porcentaje, fecha).
- **10 importadores** con **83 relaciones ProductImporter**.
- **12 devoluciones** (antes 1).
- **234 ventas** distribuidas en marzo–septiembre 2026 (para reportes flexibles).
- **8 proveedores** únicos (duplicados eliminados).
- Corregido el bug del seed (`campo quality` inexistente) y arrays exportados a `seed-data.ts`.

- [x] Aumentar productos (40-60+) en las 7 categorías.
- [x] Agregar costos por producto.
- [x] Agregar importadores y relaciones `ProductImporter`.
- [x] Agregar más devoluciones.
- [x] Distribuir ventas en varios días/semanas/meses.
- [x] Revisar idempotencia del seed (no romper datos reales).
- [x] Aplicar el seed a producción.

---

## 5. Reposición automática "al día siguiente"

- `ProductRequest` tiene `expectedDate DateTime?` (migración aplicada a Neon).
- `sales.routes.ts` y `wholesale.routes.ts` crean la solicitud con `expectedDate = nextDayAt8()` (mañana 8:00).
- **Decisión:** la solicitud solo se crea si el almacén tiene stock suficiente (`almacenInv.stock >= requestQty`); si no, no se genera.
- Instalado `node-cron` + `src/jobs/replenishJob.ts`: job diario (08:05, `America/La_Paz`) que activa solicitudes PENDIENTE vencidas → `PREPARANDO`, crea `RequestHistory` y notifica a INVENTARIO. Integrado en `server.ts`.
- Corregidos estados inválidos del enum viejo en `ProductRequest`.
- Job probado en producción ✓ · `npm run build` ✓.

- [x] Agregar `expectedDate DateTime?` a `ProductRequest`.
- [x] Crear la solicitud con `expectedDate = mañana a las 8:00`.
- [x] (Opcional) `node-cron` + job diario que active solicitudes vencidas.
- [x] Decidir si la solicitud se crea siempre o solo con stock (solo con stock en almacén).

---

# Erika (Frontend)

---

## 1. UI de columnas (ocultar / mostrar / reordenar)

- [x] Crear `ColumnManager.tsx` (componente genérico de selección de columnas).
- [x] Modal con checkboxes para mostrar/ocultar cada columna.
- [x] Permitir reordenar columnas (subir/bajar o drag).
- [x] Guardar las columnas elegidas (estado/localStorage).
- [x] Aplicarlo en Inventario (`InventoryPage.tsx`).
- [x] Aplicarlo en Ventas — carrito (`SalesPage.tsx`).
- [x] Aplicarlo en Ventas — historial (`SalesPage.tsx`).
- [x] Consumir `GET/PUT /users/me/preferences`.
- [x] Consumir `GET /permissions/roles/modules` y el `columnConfig` del rol.
- [x] Respetar `columnConfig` del rol (solo columnas permitidas).
- [x] Exponer `columnConfig` desde `authStore`.
- [x] Verificar: columna oculta desaparece y reordenación funciona.

---

## 2. Nota de venta y cotización → PDF real

- [x] Instalar librería PDF (`jspdf` + `html2canvas`).
- [x] Botón "Exportar PDF" en la nota normal (modal de `SalesPage.tsx`).
- [x] Botón "Exportar PDF" en la nota mayorista (`WholesalePage.tsx`).
- [x] PDF con: "RepuestoPro", cliente, tabla de productos, cantidades, precios, subtotal, total, pagos, pie.

### Datos de entrega en la nota
- [ ] Mostrar en la nota/PDF los campos de entrega (lugar, para quién, factura) que Ross guarda en BD (Ross-2).

> **Pendiente:** el frontend captura los campos al crear la venta, pero no los muestra en la nota/PDF.

---

## 3. Reportes flexibles (rango fechas + diario por tienda)

### Filtro flexible de fechas
- [x] Reemplazar el filtro de mes por dos inputs de fecha (desde → hasta).
- [x] Usar `startDate`/`endDate` en `fetchSales()`.
- [x] Permitir cualquier rango: día, semana, mes, trimestre, año.

### Reporte diario por tienda
- [x] Tab "Diario por Tienda" que agrupa ventas por día.
- [x] Mostrar por tienda: total del día, n° de ventas, productos vendidos, devoluciones.
- [x] Exportar el reporte diario a CSV/Excel.

---

## 4. Rol VENDEDOR: categorías y módulos en Settings

- [x] Mostrar el rol VENDEDOR en `SettingsPage.tsx`.
- [x] Asignar módulos visibles al rol VENDEDOR (y a los existentes).
- [x] Asignar **categorías visibles** al rol (y a los existentes).
- [x] Guardar los cambios consumiendo los endpoints de Ross.
- [x] Filtrar Inventario/búsqueda/productos por categorías permitidas (VENDEDOR).
- [x] Verificar que Fernando solo vea sus categorías y módulos al loguearse.

---

# Tarea conjunta / opcional
## Búsqueda por imagen real 

### Backend (Ross) 
- [x] Mejorar `POST /api/products/search-image`.

### Frontend (Erika) ⬜
- [ ] Crear UI "Buscar por imagen" (subir foto) que consuma el endpoint.
- [ ] Mostrar resultados: Producto, Marca, Modelo, Código, Stock, Precio.

### Móvil (opcional) ⬜
- [ ] Completar `ScannerScreen.tsx` con `expo-image-picker`/`expo-camera`.

---

# Verificación final (antes de subir)

- [x] Tablas de Inventario y Ventas permiten ocultar/mostrar/reordenar columnas según rol y preferencias.
- [x] La nota (normal y mayorista) se descarga como PDF real con cliente, productos, total y pagos.
- [x] Los reportes aceptan fecha desde → hasta y hay vista diaria por tienda con detalle.
- [x] El rol VENDEDOR (Fernando) existe y solo ve las categorías/módulos asignados.
- [x] La venta mayor guarda lugar de entrega, para quién y datos de factura.
- [x] La BD tiene cantidad considerable de productos, costos, importadores y ventas en varias fechas.
- [x] La reposición automática se programa para el día siguiente.
- [ ] (Opcional) Búsqueda por imagen con UI funcionando. *(Backend Completado; falta Frontend.)*
- [x] TypeScript compila en backend y frontend (`npm run build` sin errores).
- [ ] No se rompe nada en producción (Vercel + Railway) y las credenciales de seed siguen funcionando. *(Pendiente deploy.)*

---

## Pendientes de Erika

- [ ] Mostrar los datos de entrega en la nota/PDF de la venta mayor (PDF).
- [ ] UI "Buscar por imagen" (subir foto) + mostrar resultados.
- [ ] `ScannerScreen.tsx` móvil (`expo-image-picker`/`expo-camera`).
- [ ] (Con Ross) Deploy final y verificación en producción.

---
