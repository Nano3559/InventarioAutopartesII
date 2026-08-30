# Plan de Trabajo — Pendientes y Correcciones

> Proyecto: Sistema de Inventario y Ventas ("RepuestoPro").
> Este documento recoge TODO lo pendiente según la revisión del código, las observaciones, sugerencias de mejora y observaciones. Se organiza por persona para que **no se pisen los archivos**.
>

---

## Distribución de tareas

- **Ross:** TODO el backend (modelos, migraciones, endpoints, seed, lógica).
- **Erika:** TODO el frontend (UI de columnas, PDF, reportes, configuración, búsqueda por imagen).

---

# Ross (Backend)

---

## 1. Tablas editables: backend de columnas ocultar / mostrar / reordenar

> Esta es la observación del Inge. El backend de columnas **ya está implementado**,
> pero hay que completarlo/verificarlo para que el frontend de Erika pueda consumirlo.

### Verificar y completar el backend de columnas
- [ ] Verificar que `PUT /permissions/roles/:id/columns` (columnConfig por rol) funcione correctamente en `permissions.routes.ts:95-132`.
- [ ] Verificar que `GET/PUT /users/me/preferences` (columnPrefs por usuario) funcione en `users.routes.ts:165-198`.
- [ ] Confirmar que `GET /permissions/roles/modules` devuelva las columnas por módulo (`defaultColumns` en `permissions.routes.ts:16-19`).
- [ ] Confirmar que el `columnConfig` del rol incluya columnas reales de Inventario y Ventas.
- [ ] Asegurar que los endpoints devuelvan las columnas permitidas por rol Y por usuario de forma combinada.

---

## 2. Guardar datos de entrega en venta mayor (BD)

> La venta mayor captura `lugarEntrega`, `paraQuien`, `datosFactura`, `formaPago`
> (`WholesalePage.tsx:128,291-298`) y los envía al backend, **pero el backend los descarta**
> (`wholesale.routes.ts:17` los recibe pero no los guarda). El modelo `Sale` no tiene esas columnas.

### Schema
- [ ] Agregar a `Sale` (o un modelo `SaleDelivery`) los campos: `paraQuien`, `lugarEntrega`, `datosFactura`, `formaPago`.

### Migración
- [ ] Crear migración SQL y aplicar a la BD de Neon (NO usar `prisma migrate dev`).

### Backend lógico
- [ ] En `wholesale.routes.ts:102-118` guardar esos campos al crear la venta mayor.
- [ ] Devolver esos campos en el response para que el frontend los muestre en la nota/PDF.
- [ ] Incluir esos campos también en `GET /sales/:id/nota` (backend) para que la nota los muestre.

---

## 3. Crear rol VENDEDOR (Fernando) con categorías visibles

### Rol nuevo (backend)
- [ ] Agregar rol `VENDEDOR` al seed/BD (`backend/prisma/seed-data.ts` y seed del `RoleModel`).
- [ ] Definir los módulos que ve un VENDEDOR (sugerencia: ventas, inventario solo-lectura, solicitudes, devoluciones).

### Categorías visibles por rol (backend)
- [ ] Agregar campo de categorías permitidas por rol (reusar `columnConfig` o agregar `allowedCategories Json?` a `RoleModel`).
- [ ] Endpoint `GET /permissions/roles` devuelve también las categorías permitidas.
- [ ] Agregar endpoint (si no existe) para actualizar las categorías de un rol.
- [ ] Filtrar los productos/inventario por categorías permitidas en los endpoints respectivos cuando el usuario es VENDEDOR.

### Verificación (backend)
- [ ] Al consultar la API como VENDEDOR, solo devuelve las categorías/módulos asignados.

---

## 4. Rellenar la base de datos con datos suficientes (backend/seed)

> Estado actual en BD: **19 productos, 8 clientes, 6 proveedores, 7 categorías, 176 ventas,
> 41 movimientos, 0 costos, 0 importers, 1 devolución**. Falta masa de datos.

### Seed
- [ ] Aumentar productos (apuntar a 40-60+) repartidos en las 7 categorías.
- [ ] Agregar **Costos** para cada producto (1-2 registros por producto con proveedor, costo, tipo de cambio, porcentaje, fecha).
- [ ] Agregar **Importadores** (8-10) con sus relaciones `ProductImporter`.
- [ ] Agregar más devoluciones (hoy solo 1).
- [ ] Distribuir ventas en varios días/semanas/meses (para probar reportes flexibles).

### Aplicación
- [ ] Revisar si el seed es idempotente o se corre en BD de prueba (no romper datos reales).
- [ ] Aplicar el seed a la BD de producción.

---

## 5. Reposición automática "al día siguiente"

> Hoy la solicitud se genera **inmediatamente** al llegar el stock a 0
> (`sales.routes.ts:362-390` y `wholesale.routes.ts:132-153`). El enunciado pide "al día siguiente".

### Backend
- [ ] Agregar a `ProductRequest` el campo `expectedDate DateTime?`.
- [ ] Al llegar el stock a 0, crear la solicitud con `expectedDate = mañana a las 8:00` en lugar de `now()`.
- [ ] (Opcional) Instalar `node-cron` y un job diario que active las solicitudes cuyo `expectedDate` ya llegó.
- [ ] Revisar si la solicitud se crea siempre o solo cuando el almacén tenga stock (decisión documentada).

---

# Erika (Frontend)

---

## 1. Tablas editables: UI de columnas ocultar / mostrar / reordenar

> Esta es la observación del Inge y actualmente **no hay ninguna UI** en el frontend.
> Las tablas son HTML estático con columnas fijas. Ross deja el backend listo (tarea Ross-1),
> Erika construye la interfaz y la conecta.

### Componente de columnas
- [x] Crear componente genérico de selección de columnas (`frontend/src/components/ColumnManager.tsx`).
- [x] Modal con checkboxes para mostrar/ocultar cada columna.
- [x] Permitir reordenar columnas (subir/bajar o drag).
- [x] Guardar las columnas elegidas (estado/localStorage) para no perderlas al recargar.

### Aplicar en las tablas
- [x] Aplicar el componente en la tabla de Inventario (`InventoryPage.tsx`, columnas fijas en `:312-324`).
- [x] Aplicar el componente en la tabla de Ventas — carrito (`SalesPage.tsx:403-409`).
- [x] Aplicar el componente en la tabla de Ventas — historial (`SalesPage.tsx:552-562`).

### Conectar con backend (lo que expone Ross)
- [x] Consumir `GET/PUT /users/me/preferences` para guardar/recuperar columnas por usuario.
- [x] Consumir `GET /permissions/roles/modules` y el `columnConfig` del rol para saber qué columnas se permiten.
- [x] Respetar el `columnConfig` del rol: el usuario solo modifica las columnas permitidas por el admin.
- [x] Exponer el `columnConfig` del rol desde `authStore` (hoy se ignora en `authStore.ts:26,56`).

### Verificación
- [x] Una columna oculta desaparece de la tabla y la reordenación funciona correctamente.

---

## 2. Nota de venta y cotización → exportar a PDF real

> Hoy la nota es HTML imprimible (`SalesPage.tsx` modal de confirmación y `WholesalePage.tsx:171-187`).
> **No existe ninguna librería PDF.** La cotización "en vista" ya existe en el modal de confirmación
> (`SalesPage.tsx:784-836`), falta que se exporte.

### Generación de PDF
- [x] Instalar librería PDF en frontend (`jspdf` + `html2canvas` o `pdfmake`).
- [x] Agregar botón "Exportar PDF" en la nota de venta normal (modal de confirmación de `SalesPage.tsx`).
- [x] Agregar botón "Exportar PDF" en la nota de venta mayorista (`WholesalePage.tsx`).
- [x] Generar el PDF con: título "RepuestoPro", cliente, tabla de productos, cantidades, precios, subtotal, total, pagos, pie.

### Datos de entrega en la nota
- [ ] Mostrar en la nota/PDF los campos de entrega (lugar, para quién, factura) que Ross guarda en BD (tarea Ross-2).

---

## 3. Reportes flexibles: rango fecha-a-fecha + reporte diario por tienda

> El backend `GET /reports/sales` ya acepta `startDate`/`endDate` (`reports.routes.ts:20-28`),
> pero el frontend solo usa `month`. Ross ajusta `/reports/monthly` (tarea Ross-1b si aplica),
> Erika hace la UI flexible.

### Filtro flexible de fechas
- [x] En `ReportsPage.tsx`, reemplazar el filtro de mes por dos inputs de fecha (desde → hasta).
- [x] Usar `startDate`/`endDate` en `fetchSales()` (hoy `:71` solo envía `month`).
- [x] Permitir elegir cualquier rango: día, semana, mes, trimestre, año.

### Nuevo reporte diario detallado por tienda
- [x] Crear tab "Diario por Tienda" que agrupe ventas por día.
- [x] Mostrar por tienda: total del día, n° de ventas, productos vendidos (nombre, cantidad, subtotal), devoluciones.
- [x] Exportar el reporte diario a CSV/Excel.

---

## 4. Rol VENDEDOR: configurar categorías y módulos en Settings (frontend)

> Ross crea el rol VENDEDOR y el campo de categorías en backend (tarea Ross-3).
> Erika construye la interfaz para asignar categorías y módulos.

### Configuración de rol en SettingsPage
- [x] En `SettingsPage.tsx`, mostrar el nuevo rol VENDEDOR.
- [x] Permitir al admin asignar módulos visibles al rol VENDEDOR (y a los existentes).
- [x] Permitir al admin asignar **categorías visibles** al rol VENDEDOR (y a los existentes).
- [x] Guardar esos cambios consumiendo los endpoints que expone Ross.

### Aplicar el filtro de categorías en el frontend
- [x] Filtrar Inventario / búsqueda / productos por las categorías permitidas cuando el usuario es VENDEDOR.
- [x] Verificar que Fernando al loguearse solo vea sus categorías y módulos en el menú y en las páginas.

---

# Tarea conjunta / opcional

## Búsqueda por imagen real (si da tiempo)

> Existe `POST /api/products/search-image` (`products.routes.ts:307-372`) pero solo lee el nombre del
> archivo; no analiza la imagen. No hay ninguna UI que la consuma.

### Backend (Ross)
- [ ] Mejorar `POST /api/products/search-image` para analizar mejor la imagen (OCR o keywords).

### Frontend (Erika)
- [ ] Crear UI "Buscar por imagen" (subir foto) que consuma el endpoint.
- [ ] Mostrar los resultados: Producto, Marca, Modelo, Código, Stock, Precio.

### Móvil (opcional)
- [ ] Completar `ScannerScreen.tsx` con `expo-image-picker`/`expo-camera`.

---

# Orden de implementación recomendado

| Paso | Tarea | Quién | Depende de |
|------|-------|-------|------------|
| 1 | **Ross-1** Backend de columnas | Ross | — |
| 2 | **Erika-1** UI de columnas | Erika | Ross-1 |
| 3 | **Ross-2** Datos de entrega en BD | Ross | — |
| 4 | **Erika-2** PDF notas/cotización | Erika | Ross-2 (entrega) |
| 5 | **Ross-3** Rol VENDEDOR + categorías (backend) | Ross | — |
| 6 | **Erika-4** Settings rol/categorías (frontend) | Erika | Ross-3 |
| 7 | **Ross-4** Rellenar datos (seed) | Ross | — |
| 8 | **Ross-5** Reposición al día siguiente | Ross | — |
| 9 | **Erika-3** Reportes flexibles + diario | Erika | — |
| 10 | **Opcional** Búsqueda por imagen | Ross+Erika | — |

---

# Verificación final (antes de subir)

- [x] Tablas de Inventario y Ventas permiten ocultar/mostrar/reordenar columnas según rol y preferencias del usuario.
- [x] La nota de venta (normal y mayorista) se descarga como PDF real con cliente, productos, total y pagos.
- [x] Los reportes aceptan fecha desde → hasta y hay vista diaria por tienda con detalle.
- [x] El rol VENDEDOR (Fernando) existe y solo ve las categorías/módulos asignados.
- [ ] La venta mayor guarda lugar de entrega, para quién y datos de factura.
- [ ] La BD tiene cantidad considerable de productos, costos, importadores y ventas en varias fechas.
- [ ] La reposición automática se programa para el día siguiente.
- [ ] (Opcional) Búsqueda por imagen con UI funcionando.
- [ ] TypeScript compila en backend y frontend (`npm run build` sin errores).
- [ ] No se rompe nada en producción (Vercel + Railway) y las credenciales de seed siguen funcionando.

---

*Documento generado a partir de la revisión del código. No se han hecho commits.*
