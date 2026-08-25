# Division de Tareas - Sistema de Inventario y Ventas
## Proyecto: RepuestoPro - InventarioAutopartesII

---

## Integrantes

| Nombre | Rama | Enfoque |
|--------|------|---------|
| Erika | `erika` | Frontend (interfaces, estilos, componentes) |
| Ross | `ross` | Backend (APIs, base de datos, logica de negocio) |

---

## ESTADO ACTUAL - LO QUE YA ESTA HECHO

### Completado por ambos
- [x] Base de datos: 17 modelos Prisma, 5 enums, 2 migraciones
- [x] Seed de datos: 18 productos, 7 ubicaciones, 5 usuarios, ventas, movimientos, solicitudes, importadoras
- [x] Despliegue: Vercel (frontend), Railway (backend), Neon (BD)
- [x] Auth: login, registro, JWT, middleware de proteccion
- [x] Dashboard: estadisticas reales, graficas Recharts, stock critico
- [x] Layout admin: sidebar, header, rutas protegidas
- [x] Layout publico: navbar, footer responsivo
- [x] Ruta / y /contacto funcionales

### Completado por Erika
- [x] Pagina de productos publicos (filtros, busqueda, paginacion)
- [x] Detalle de producto publico
- [x] Navbar publico responsivo con hamburger menu
- [x] Footer publico (4 columnas)
- [x] Componente ProductImage con fallback
- [x] Seccion de importadoras

### Completado por Ross
- [x] Landing Page (Hero, Beneficios, Productos destacados, Busqueda, Mayorista/Minorista, CTA)
- [x] Pagina de Contacto (formulario, info, importadoras, WhatsApp)
- [x] Boton WhatsApp responsivo
- [x] API publica: 6 endpoints funcionando (products, products/:id, filters, filters/models, filters/years, importers)
- [x] Fix Docker cache en Railway (.dockerignore, rm -rf dist)
- [x] .env.production para Vercel
- [x] prisma migrate deploy en Dockerfile

---

## TAREAS DE ERIKA (FRONTEND)

### Sprint 1 - Prioridad ALTA - Ejercicio 1: Inventario
- [x] Dashboard conectado a APIs reales
- [x] **Pagina Inventario** (`/panel/inventario`):
  - Tabla completa con columnas: ID | Fabricante | Producto | Marca | Modelo | Ano | Codigo OEM | Codigo Fabrica | Imagen | Precio 1 | Precio 2 | Stock
  - Buscador de productos
  - Filtros: Marca, Fabricante, Producto, Modelo, Ano, Codigo OEM, Codigo Fabrica
  - Boton "Nuevo Producto" con modal/formulario completo
  - Acciones por fila: Ver, Editar, Eliminar, Ver stock por ubicacion
  - Paginacion de tabla
  - Mensajes de confirmacion/error
- [x] **Detalle de Producto** (`/panel/inventario/:id`):
  - Informacion completa del producto
  - Stock por cada ubicacion (4 almacenes + 3 tiendas) en tabla
  - Formulario de edicion
  - Boton "Solicitar a almacen" cuando stock = 0

### Sprint 2 - Prioridad ALTA - Ejercicio 2: Ventas
- [x] **Pagina Ventas** (`/panel/ventas`):
  - Buscar producto por codigo, nombre, marca, modelo, codigo OEM
  - Lista de resultados con imagen, nombre, precio, stock disponible
  - Carrito de venta: agregar productos con cantidad y precio
  - Calculo automatico de subtotales y total
  - Resumen de venta antes de confirmar (tabla con Producto | Cantidad | Precio | Subtotal | TOTAL)
  - Boton "Confirmar venta"
- [x] **Registro de pago** (modal o paso adicional):
  - Multiples metodos: Efectivo, QR, Credito, Transferencia
  - Suma de pagos vs total (validar que sea igual)
  - Permitir combinar metodos (ej: Efectivo Bs.1000 + QR Bs.500)
- [x] **Facturacion** (pregunta "Requiere factura?"):
  - Si/No
  - Si: formulario CI/NIT, Nombre, Celular
- [x] **Historial de ventas** (tabla con filtros por fecha, tienda, tipo)

### Sprint 3 - Prioridad MEDIA - Ejercicios 3 y 4
- [x] **Pagina Devoluciones** (`/panel/devoluciones`):
  - Buscar venta original
  - Seleccionar producto de la venta
  - Formulario: motivo, cantidad, monto a devolver, metodo de devolucion
  - Confirmar devolucion
  - Tabla historial de devoluciones
- [x] **Pagina Solicitudes** (`/panel/solicitudes`):
  - Formulario nueva solicitud: producto, cantidad, tienda solicitante
  - Lista de solicitudes con filtros por estado
  - Estados visibles: Pendiente, En preparacion, Enviado, Recibido, Cancelado
  - Boton "Solicitar a almacen" desde detalle de producto (stock = 0)
  - Cambio de estado desde la lista (para encargado de inventario)

### Sprint 4 - Prioridad MEDIA - Ejercicios 5 y 9
- [x] **Pagina Movimientos** (`/panel/movimientos`):
  - Formulario: producto, cantidad, origen (almacen/tienda), destino (almacen/tienda), observacion
  - Historial de movimientos en tabla
  - Filtros por fecha, producto, ubicacion origen, ubicacion destino
- [x] **Pagina Pagos** (integrada en Ventas):
  - Registro de pagos multiples por venta
  - Historial de pagos con filtros
  - Resumen: total pagado vs total venta

### Sprint 5 - Prioridad BAJA - Ejercicios 6, 7, 8
- [x] **Pagina Costos** (`/panel/costos`):
  - Formulario: subir factura (upload), proveedor, tipo de cambio, porcentaje, producto, costo
  - Lista de costos registrados
  - CRUD de proveedores (nombre, NIT, telefono)
- [x] **Pagina Precios** (`/panel/precios`):
  - Tabla de precios calculados desde costo: Costo | +20% | +30% | +40% | +50% | +60% | +70% | +80% | Precio Mayor
  - Edicion manual de precio por mayor
  - Boton "Exportar a Excel" (Codigo fabrica, Producto, Marca, Modelo, Anos, Detalle, Precio mayor)
- [x] **Pagina Venta por Mayor** (`/panel/ventas-mayor`):
  - Formulario manual de productos
  - Boton "Importar Excel" (columnas: Codigo fabrica, Descripcion, Producto, Marca, Modelo, Anos, Detalle, Precio mayor)
  - Datos del cliente: nombre, para quien es el pedido, lugar de entrega, datos para factura, forma de pago
  - Entrega: Cochabamba / Otra ubicacion
  - Generar nota de venta (PDF o formato printable)
- [x] **Pagina Reportes** (`/panel/reportes`):
  - Filtros: Marca, Auto/modelo, Mes, Tienda, Proveedor, Producto
  - Tablas de resultados: ventas, inventario, costos
  - Reporte mensual por tienda
- [x] **Pagina Configuracion** (`/panel/configuracion`):
  - Gestionar usuarios
  - Gestionar roles/permisos

### Tareas adicionales Erika
- [x] Responsive completo del admin (sidebar colapsa en celular)
- [ ] Modales consistentes en todos los CRUD
- [ ] Mensajes de confirmacion/error en todas las acciones
- [ ] Estados de carga (spinners/skeletons) en todas las paginas

---

## TAREAS DE ROSS (BACKEND)

### Sprint 1 - Prioridad ALTA - Ejercicio 1: Productos e Inventario
- [x] API Productos: stub registrado en app.ts
- [x] **API Productos CRUD** (`/api/products`):
  - GET / — listar con filtros (marca, fabricante, modelo, ano, OEM, fabrica) y busqueda
  - GET /:id — detalle con stock por ubicacion
  - POST — crear producto (validar campos obligatorios)
  - PUT /:id — editar producto
  - DELETE /:id — eliminar (con validacion de ventas asociadas)
- [x] **API Inventario** (`/api/inventory`):
  - GET / — listar todo el inventario
  - GET /:productId — stock por ubicacion de un producto
  - PUT /:id — actualizar stock manualmente
- [x] **API Ubicaciones** (`/api/locations`):
  - GET / — listar almacenes y tiendas

### Sprint 2 - Prioridad ALTA - Ejercicio 2: Ventas
- [x] **API Ventas** (`/api/sales`):
  - POST — crear venta normal
    - Recibe: items[], pagos[], customerId?, requiereFactura, datosFactura?
    - Valida stock suficiente de cada item
    - Descuenta stock automaticamente
    - Crea pagos asociados
    - Si stock llega a 0, genera solicitud automatica a almacen (ejercicio 12)
  - GET / — listar ventas (filtros: fecha, tienda, tipo)
  - GET /:id — detalle de venta con items y pagos
- [x] **API Pagos** (`/api/payments`):
  - POST — registrar pago adicional a una venta
  - GET — listar pagos
- [x] **API Clientes** (`/api/customers`):
  - POST — crear/registro
  - GET — listar
  - GET /:id — detalle

### Sprint 3 - Prioridad MEDIA - Ejercicios 3 y 4
- [x] **API Devoluciones** (`/api/returns`):
  - POST — registrar devolucion
    - Valida que la venta exista
    - Devuelve stock automaticamente
    - Registra motivo, cantidad, monto, metodo
  - GET / — listar devoluciones
- [x] **API Solicitudes** (`/api/requests`):
  - POST — crear solicitud (tienda pide a almacen)
  - PUT /:id — cambiar estado (PENDIENTE -> EN_PREPARACION -> ENVIADO -> RECIBIDO)
  - GET / — listar con filtros por estado y tienda
  - DELETE /:id — cancelar solicitud

### Sprint 4 - Prioridad MEDIA - Ejercicio 5: Movimientos
- [x] **API Movimientos** (`/api/movements`):
  - POST — registrar movimiento
    - Valida stock suficiente en origen
    - Descuenta stock origen
    - Suma stock destino
    - Registra usuario, fecha, observacion
  - GET / — historial con filtros (fecha, producto, ubicacion)

### Sprint 5 - Prioridad MEDIA - Ejercicios 6 y 7
- [x] **API Costos** (`/api/costs`):
  - POST — registrar costo con factura (upload multer)
  - GET / — listar costos
  - PUT /:id — editar costo
- [x] **API Proveedores** (`/api/suppliers`):
  - POST — crear proveedor
  - GET / — listar
  - PUT /:id — editar
  - DELETE /:id — eliminar
- [x] **API Precios** (`/api/prices`):
  - GET / — calcular precios desde costo con todos los porcentajes
  - PUT /:productId — actualizar precio por mayor
  - GET /export — exportar a Excel (xlsx)

### Sprint 6 - Prioridad BAJA - Ejercicios 8, 10, 11, 12, 13
- [x] **API Venta por Mayor** (`/api/wholesale`):
  - POST — crear venta mayorista (misma logica que venta normal pero con validaciones de mayorista)
  - POST /import — importar desde Excel
- [x] **API Nota de Venta**:
  - GET /api/sales/:id/nota — generar nota de venta (PDF o HTML)
- [x] **API Reportes** (`/api/reports`):
  - GET /sales — ventas filtradas (marca, modelo, mes, tienda, proveedor)
  - GET /inventory — stock por ubicacion
  - GET /suppliers — reporte por proveedor
  - GET /monthly — reporte mensual por tienda con costos
- [x] **Reposicion automatica** (logica interna):
  - Cuando stock de un producto llega a 0 en cualquier tienda
  - Generar automaticamente una ProductRequest al almacen correspondiente
  - Implementar como middleware o trigger en el POST de ventas
- [x] **Busqueda por imagen** (funcionalidad adicional):
  - POST /api/products/search-image — recibe imagen, busca coincidencias
  - Utilizar descripcion del producto para matching

### Tareas adicionales Ross
- [x] Crear modulo `customers` en backend/src/modules/ (falta completamente)
- [x] Crear modulo `suppliers` en backend/src/modules/ (falta completamente)
- [x] Actualizar seed con: pagos en ventas, devoluciones, costos con facturas, precios calculados
- [x] Validaciones robustas en todos los endpoints (campos obligatorios, tipos de dato)
- [x] Manejo de errores consistente (mensajes claros al frontend)

---

## FLUJO PRINCIPAL A IMPLEMENTAR (CRITERIO DE EVALUACION)

```
1. INVENTARIO
   → Tabla de productos con filtros
   → CRUD completo
   → Stock por ubicacion (4 almacenes + 3 tiendas)

2. VENTA (ejercicio clave)
   → Buscar producto
   → Seleccionar cantidad y precio
   → Confirmar venta
   → Registrar pago (multiples metodos)
   → Facturacion (CI/NIT)
   → DESCONTAR stock de Tienda
   → Si stock = 0, GENERAR solicitud automatica a almacen
   → Generar nota de venta

3. MOVIMIENTOS
   → Encargado recibe solicitud
   → Registra movimiento: Almacen X → Tienda Y
   → Actualiza stock en ambas ubicaciones

4. PRECIOS Y COSTOS
   → Admin registra costo + factura
   → Sistema calcula precios con porcentajes
   → Exportar a Excel

5. REPORTES
   → Filtrar por marca, modelo, mes, tienda
   → Reporte mensual por tienda con costos
   → Todo lo anterior aparece aqui
```

---

## ORDEN DE INTEGRACION

1. Erika trabaja en su rama `erika`
2. Ross trabaja en su rama `ross`
3. Prioridad: primero Sprint 1 y 2 (Inventario + Ventas = lo mas visible)
4. Cuando ambos tengan avance, hacer Pull Request a `main`
5. Revisar que no haya conflictos
6. Merge a `main`

---

## NOTAS IMPORTANTES

- Cada uno NUNCA hace push directo a `main`
- Siempre trabajar en la rama propia
- Comunicarse antes de modificar archivos compartidos (schema.prisma, package.json, app.ts)
- Backend en Railway: https://inventarioautopartesii-production-cacf.up.railway.app
- Frontend en Vercel: https://inventario-autopartes-ii.vercel.app
- Credenciales de prueba: admin@inventario.com / admin123, tienda1@inventario.com / tienda123
