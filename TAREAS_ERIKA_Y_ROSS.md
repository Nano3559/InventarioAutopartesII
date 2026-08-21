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
- [x] **Sprint 1 COMPLETADO** — Inventario CRUD completo

### Completado por Erika
- [x] Pagina de productos publicos (filtros, busqueda, paginacion)
- [x] Detalle de producto publico
- [x] Navbar publico responsivo con hamburger menu
- [x] Footer publico (4 columnas)
- [x] Componente ProductImage con fallback
- [x] Seccion de importadoras
- [x] **Sprint 1 Frontend** — Inventario, Detalle, Modal, Acciones, Paginacion, Toasts

### Completado por Ross
- [x] Landing Page (Hero, Beneficios, Productos destacados, Busqueda, Mayorista/Minorista, CTA)
- [x] Pagina de Contacto (formulario, info, importadoras, WhatsApp)
- [x] Boton WhatsApp responsivo
- [x] API publica: 6 endpoints funcionando (products, products/:id, filters, filters/models, filters/years, importers)
- [x] Fix Docker cache en Railway (.dockerignore, rm -rf dist)
- [x] .env.production para Vercel
- [x] prisma migrate deploy en Dockerfile
- [x] **Sprint 1 Backend** — API Products CRUD, API Inventory, API Locations, Control de roles

---

## SPRINT 1 — COMPLETADO (20/08/2026)

### Frontend (Erika)
- [x] Pagina `/panel/inventario` con tabla completa (13 columnas: ID, Fabricante, Producto, Marca, Modelo, Ano, Codigo OEM, Codigo Fabrica, Imagen, Precio 1, Precio 2, Stock, Acciones)
- [x] Buscador en tiempo real con boton limpiar
- [x] Filtros colapsables: Marca, Fabricante (selects dinamicos desde API)
- [x] Paginacion con navegacion (anterior/siguiente/numeros de pagina)
- [x] Modal "Nuevo Producto" con todos los campos obligatorios y opcionales
- [x] Modal "Editar Producto" con precarga de datos
- [x] Modal confirmacion de eliminacion
- [x] Modal "Stock por Ubicacion" (lista almacenes y tiendas con stock/minStock)
- [x] Boton "Solicitar a almacen" visible cuando stock = 0
- [x] Toasts de exito/error en todas las acciones CRUD
- [x] Pagina `/panel/inventario/:id` con detalle completo del producto
- [x] Sidebar de stock por ubicacion (Almacenes + Tiendas con indicadores de color)
- [x] Formulario de edicion inline con Guardar/Cancelar
- [x] Lista de importadores asociados al producto
- [x] Indicadores de stock: rojo (0), amarillo (<=minStock), verde (>minStock)
- [x] Componente `RoleRoute` para control de acceso por rol
- [x] Sidebar filtrado segun el rol del usuario

### Backend (Ross)
- [x] API `GET /api/products` — listado con filtros, busqueda y paginacion
- [x] API `GET /api/products/filters` — marcas, fabricantes, categorias
- [x] API `GET /api/products/:id` — detalle con stock por ubicacion e importadores
- [x] API `POST /api/products` — crear producto con validacion de itemCode unico
- [x] API `PUT /api/products/:id` — editar producto
- [x] API `DELETE /api/products/:id` — eliminar con validacion de ventas asociadas
- [x] API `GET /api/inventory` — listado con filtros (ubicacion, stock bajo)
- [x] API `GET /api/inventory/product/:id` — stock por ubicacion
- [x] API `PUT /api/inventory/:id` — actualizar stock manualmente
- [x] API `GET /api/locations` — listar ubicaciones

### Control de acceso
- [x] ADMIN: acceso completo a todas las rutas
- [x] INVENTARIO: inventario, solicitudes, movimientos, costos, precios
- [x] TIENDA: ventas, ventas por mayor, devoluciones, solicitudes, reportes
- [x] Dashboard visible para todos los roles

---

## SPRINT 2 — TAREAS ACTUALES

### TAREAS DE ERIKA (FRONTEND)

#### Sprint 2 - Prioridad ALTA - Ejercicio 2: Ventas
- [ ] **Pagina Ventas** (`/panel/ventas`):
  - Buscar producto por codigo, nombre, marca, modelo, codigo OEM
  - Lista de resultados con imagen, nombre, precio, stock disponible
  - Carrito de venta: agregar productos con cantidad y precio
  - Calculo automatico de subtotales y total
  - Resumen de venta antes de confirmar (tabla con Producto | Cantidad | Precio | Subtotal | TOTAL)
  - Boton "Confirmar venta"
- [ ] **Registro de pago** (modal o paso adicional):
  - Multiples metodos: Efectivo, QR, Credito, Transferencia
  - Suma de pagos vs total (validar que sea igual)
  - Permitir combinar metodos (ej: Efectivo Bs.1000 + QR Bs.500)
- [ ] **Facturacion** (pregunta "Requiere factura?"):
  - Si/No
  - Si: formulario CI/NIT, Nombre, Celular
- [ ] **Historial de ventas** (tabla con filtros por fecha, tienda, tipo)

### TAREAS DE ROSS (BACKEND)

#### Sprint 2 - Prioridad ALTA - Ejercicio 2: Ventas
- [ ] **API Ventas** (`/api/sales`):
  - POST — crear venta normal
    - Recibe: items[], pagos[], customerId?, requiereFactura, datosFactura?
    - Valida stock suficiente de cada item
    - Descuenta stock automaticamente
    - Crea pagos asociados
    - Si stock llega a 0, genera solicitud automatica a almacen
  - GET / — listar ventas (filtros: fecha, tienda, tipo)
  - GET /:id — detalle de venta con items y pagos
- [ ] **API Pagos** (`/api/payments`):
  - POST — registrar pago adicional a una venta
  - GET — listar pagos
- [ ] **API Clientes** (`/api/customers`):
  - POST — crear/registro
  - GET — listar
  - GET /:id — detalle

---

## SPRINTS FUTUROS (referencia)

### Sprint 3 - Prioridad MEDIA - Ejercicios 3 y 4
- [ ] **Devoluciones** — Buscar venta, seleccionar producto, motivo, cantidad, monto, metodo
- [ ] **Solicitudes** — Formulario, lista con estados, cambio de estado, "Solicitar a almacen"

### Sprint 4 - Prioridad MEDIA - Ejercicio 5
- [ ] **Movimientos** — Formulario (producto, cantidad, origen, destino, observacion), historial, filtros

### Sprint 5 - Prioridad BAJA - Ejercicios 6, 7, 8, 9
- [ ] **Costos** — Upload factura, proveedor, tipo de cambio, porcentaje
- [ ] **Precios** — Tabla calculada desde costo, edicion manual, exportar Excel
- [ ] **Venta por Mayor** — Formulario manual, importar Excel, datos cliente, nota de venta PDF
- [ ] **Reportes** — Filtros (marca, modelo, mes, tienda), tablas de resultados
- [ ] **Configuracion** — Gestionar usuarios, roles/permisos

### Tareas adicionales
- [ ] Responsive completo del admin (sidebar colapsa en celular)
- [ ] Modales consistentes en todos los CRUD
- [ ] Estados de carga (spinners/skeletons) en todas las paginas

---

## FLUJO PRINCIPAL A IMPLEMENTAR (CRITERIO DE EVALUACION)

```
1. INVENTARIO ✅
   → Tabla de productos con filtros
   → CRUD completo
   → Stock por ubicacion (4 almacenes + 3 tiendas)

2. VENTA (ejercicio clave) — SPRINT 2
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
- Sprint 1 COMPLETADO: APIs CRUD funcionando + Frontend completo con control de roles
