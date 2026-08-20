# Division de Tareas - Sistema de Inventario y Ventas
## Proyecto: RepuestoPro - InventarioAutopartesII

---

## Integrantes

| Nombre | Rama | Enfoque |
|--------|------|---------|
| Erika | `erika` | Frontend (interfaces, estilos, componentes) |
| Ross | `ross` | Backend (APIs, base de datos, logica de negocio) |

---

## TAREAS DE ERIKA (FRONTEND)

### Sprint 1 - Prioridad ALTA
- [ ] Dashboard conectado a APIs reales (estadisticas, graficos con Recharts)
- [ ] Pagina de Inventario: tabla completa con columnas del enunciado
  - ID | Fabricante | Producto | Marca | Modelo | Ano | Codigo OEM | Codigo Fabrica | Imagen | Precio 1 | Precio 2 | Stock
- [ ] Buscador de productos en inventario
- [ ] Filtros: Marca, Fabricante, Producto, Modelo, Ano, Codigo OEM, Codigo Fabrica
- [ ] Boton "Nuevo Producto" con modal/formulario
- [ ] Acciones por fila: Ver, Editar, Eliminar, Ver stock por ubicacion

### Sprint 2 - Prioridad MEDIA
- [ ] Detalle de Producto (pagina /inventario/:id)
  - Informacion completa del producto
  - Stock por cada ubicacion (4 almacenes + 3 tiendas)
  - Boton "Solicitar a almacen"
- [ ] Pagina de Ventas
  - Buscar producto por codigo, nombre, marca, modelo, codigo OEM
  - Agregar productos al carrito (cantidad, precio)
  - Calculo automatico de subtotales y total
  - Resumen de venta antes de confirmar
- [ ] Registro de pago (multiples metodos: Efectivo, QR, Credito, Transferencia)
- [ ] Pregunta "Requiere factura?" con formulario CI/NIT, nombre, celular

### Sprint 3 - Prioridad MEDIA
- [ ] Pagina de Devoluciones
  - Seleccionar producto
  - Motivo de devolucion
  - Cantidad y monto
  - Metodo de devolucion
- [ ] Pagina de Solicitudes a almacen
  - Formulario: producto, cantidad, tienda solicitante
  - Estados: Pendiente, En preparacion, Enviado, Recibido, Cancelado
  - Lista de solicitudes con filtros por estado

### Sprint 4 - Prioridad BAJA
- [ ] Pagina de Movimientos
  - Formulario: producto, cantidad, origen, destino, observacion
  - Historial de movimientos
- [ ] Pagina de Costos
  - Subir facturas
  - Registrar proveedor, tipo de cambio, porcentaje
- [ ] Pagina de Precios
  - Tabla con costos + porcentajes (+20%, +30%, +40%, +50%, +60%, +70%, +80%)
  - Precio por mayor (edicion manual)
  - Boton exportar a Excel

### Sprint 5 - Prioridad BAJA
- [ ] Venta por mayor
  - Formulario manual + importar Excel
  - Datos del cliente (nombre, para quien, lugar de entrega, factura, forma de pago)
  - Generar nota de venta
- [ ] Reportes con filtros (marca, modelo, mes, tienda, proveedor, producto)
- [ ] Configuracion

---

## TAREAS DE ROSS (BACKEND)

### Sprint 1 - Prioridad ALTA
- [ ] API de Productos (CRUD completo)
  - GET /api/products (listar con filtros y busqueda)
  - GET /api/products/:id (detalle con stock por ubicacion)
  - POST /api/products (crear)
  - PUT /api/products/:id (editar)
  - DELETE /api/products/:id (eliminar)
- [ ] API de Inventarios
  - GET /api/inventory (listar todo)
  - GET /api/inventory/:productId (stock por ubicacion)
  - PUT /api/inventory/:id (actualizar stock)
- [ ] API de Ubicaciones
  - GET /api/locations (listar almacenes y tiendas)
- [ ] Seed data completo
  - Productos de ejemplo (repuestos automotrices reales)
  - Stock inicial en cada ubicacion
  - Categorias de productos

### Sprint 2 - Prioridad MEDIA
- [ ] API de Ventas
  - POST /api/sales (crear venta con items y pagos)
  - GET /api/sales (listar ventas)
  - GET /api/sales/:id (detalle de venta)
  - Validar stock antes de confirmar
  - Descontar stock automaticamente
- [ ] API de Pagos
  - POST /api/payments (registrar pago)
  - Soporte para multiples metodos en una venta
- [ ] API de Clientes
  - POST /api/customers (crear/registro)
  - GET /api/customers (listar)

### Sprint 3 - Prioridad MEDIA
- [ ] API de Devoluciones
  - POST /api/returns (registrar devolucion)
  - Devolver stock automaticamente
  - GET /api/returns (listar devoluciones)
- [ ] API de Solicitudes
  - POST /api/requests (crear solicitud)
  - PUT /api/requests/:id (cambiar estado)
  - GET /api/requests (listar con filtros)
- [ ] API de Movimientos
  - POST /api/movements (registrar movimiento)
  - Validar stock en origen
  - Descontar origen, sumar destino
  - GET /api/movements (historial)

### Sprint 4 - Prioridad BAJA
- [ ] API de Costos
  - POST /api/costs (registrar costo con factura)
  - GET /api/costs (listar)
- [ ] API de Proveedores
  - CRUD de proveedores
- [ ] API de Precios
  - GET /api/prices (calcular precios desde costo con porcentajes)
  - PUT /api/prices/:productId (editar precio por mayor)

### Sprint 5 - Prioridad BAJA
- [ ] API de Reportes
  - GET /api/reports/sales (filtrar por marca, modelo, mes, tienda)
  - GET /api/reports/inventory (stock por ubicacion)
  - GET /api/reports/suppliers (ventas por proveedor)
- [ ] Importar Excel (POST /api/products/import)
- [ ] Exportar Excel (GET /api/products/export)
- [ ] Reposicion automatica (cuando stock = 0, crear solicitud)

---

## FLUJO PRINCIPAL A IMPLEMENTAR

```
Venta en Tienda 1
  → Buscar producto
  → Seleccionar cantidad y precio
  → Confirmar venta
  → Registrar pago
  → DESCONTAR stock de Tienda 1
  → Si stock = 0, GENERAR solicitud a almacen
  → Aparecer en REPORTES
```

---

## ORDEN DE INTEGRACION

1. Erika trabaja en su rama `erika`
2. Ross trabaja en su rama `ross`
3. Cuando ambos tengan avance significativo, hacer Pull Request a `main`
4. Revisar que no haya conflictos
5. Merge a `main`

---

## NOTAS IMPORTANTES

- Cada uno NUNCA hace push directo a `main`
- Siempre trabajar en la rama propia
- Comunicarse antes de modificar archivos compartidos (package.json, schema.prisma)
- El backend debe estar corriendo en puerto 3000
- El frontend debe estar corriendo en puerto 5173
- Las credenciales de prueba estan en seed.ts
