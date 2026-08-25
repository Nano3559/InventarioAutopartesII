# Corrección de Observaciones

## Distribución de tareas

---

# Erika

## 1. Inventario

### Estructura de datos
- [x] Agregar el campo `detalles` al inventario.
- [x] Reemplazar la columna visible `calidad` por `detalles`.
- [x] Revisar los cambios necesarios en base de datos, backend y frontend.
- [x] Permitir múltiples valores separados por `/` en:
  - [x] Marca.
  - [x] Modelo.
  - [x] Año.

Ejemplo:

```text
Marca: Toyota/Nissan
Modelo: Tacoma/Frontier
Año: 05-08/12-16
```

### Lógica de rangos de años
- [x] Implementar la interpretación de rangos de años.

Casos:

- `13-15` → incluye 2013, 2014 y 2015.
- `13` → corresponde únicamente a 2013.
- `13-` → corresponde a 2013 en adelante.
- [x] Permitir múltiples rangos separados por `/`.
- [x] Validar rangos incorrectos.
- [x] Definir mensaje de validación para valores como `15-13`.

### Permisos en Inventario
- [x] Las tiendas pueden visualizar inventario.
- [x] Las tiendas no pueden editar inventario.
- [x] Los encargados de inventario pueden visualizar inventario.
- [x] Los encargados de inventario no pueden editar inventario.
- [x] Confirmar si el administrador puede editar inventario libremente.

---

## 2. Búsqueda de Inventario

### Autocompletado
- [x] Implementar sugerencias mientras el usuario escribe.
- [x] Autocompletado para Marca.
- [x] Autocompletado para Modelo.
- [x] Autocompletado para Año.
- [x] Evaluar otras columnas donde corresponda aplicar sugerencias.

Ejemplo:

`Toy` → sugerir `Toyota`.

### Búsqueda exacta por columna
- [x] Permitir búsqueda específica por Marca.
- [x] Permitir búsqueda específica por Modelo.
- [x] Permitir búsqueda específica por Año.
- [x] Considerar correctamente valores múltiples separados por `/`.

Ejemplo:

Si un producto tiene:

`Toyota/Nissan`

una búsqueda por:

`Toyota`

debe encontrar el producto.

### Búsqueda por rangos de años
- [x] Aplicar la misma lógica de rangos utilizada en Inventario.
- [x] Permitir buscar años incluidos dentro de un rango.

Ejemplo:

Producto:

`13-15`

Búsqueda:

`14`

Resultado:

Debe encontrar el producto.

- [x] Preparar esta lógica para que pueda reutilizarse posteriormente en Ventas.

---

## 3. Solicitudes

### Nota opcional
- [x] Agregar campo de nota al crear una solicitud.
- [x] La nota debe ser opcional.
- [x] Mostrar la nota en el detalle de la solicitud cuando exista.

### Flujo de estados
Implementar los siguientes estados:

- [x] Solicitud creada.
- [x] Recibido por Inventario.
- [x] Preparando.
- [x] Entregado.
- [x] Recibido por Tienda o Administrador.

### Permisos para cambio de estado

#### Encargado de Inventario
- [x] Puede marcar como Recibido.
- [x] Puede cambiar a Preparando.
- [x] Puede cambiar a Entregado.

#### Tienda / Administrador
- [x] Puede confirmar la recepción final.

### Historial de estados
Registrar:

- [x] Estado anterior.
- [x] Estado nuevo.
- [x] Usuario que realizó el cambio.
- [x] Rol del usuario.
- [x] Fecha.
- [x] Hora.

### Notificaciones
- [x] Notificar a la tienda cuando cambie el estado de su solicitud.
- [x] Mostrar claramente el nuevo estado.
- [x] Verificar que la notificación corresponda a la tienda que realizó la solicitud.

---

# Ross

## 4. Ventas

### Restricción por tienda
- [x] Cada tienda solo puede vender productos asignados a su propia tienda.
- [x] Impedir que una tienda venda inventario correspondiente a otra tienda.
- [x] Aplicar la validación también desde backend.

### Vendedores
Cada tienda debe manejar tres vendedores internos.

- [x] Permitir seleccionar Vendedor 1.
- [x] Permitir seleccionar Vendedor 2.
- [x] Permitir seleccionar Vendedor 3.
- [x] Guardar el vendedor asociado a la venta.
- [x] Mostrar el vendedor en el detalle de venta.
- [x] Permitir filtrar las ventas por vendedor.

### Administrador
- [x] El administrador puede vender en nombre de cualquier tienda.
- [x] Permitir seleccionar la tienda al registrar la venta.
- [x] Permitir seleccionar el vendedor correspondiente.

### Búsqueda en Ventas
- [x] Aplicar el mismo sistema de búsqueda utilizado en Inventario.
- [x] Implementar autocompletado.
- [x] Implementar búsqueda exacta por columna.
- [x] Aplicar la lógica de rangos de años.
- [x] Reutilizar la lógica creada en Inventario.

---

## 5. Devoluciones

### Identificación de venta
- [x] Toda devolución debe requerir el ID de la venta.
- [x] Verificar que la venta exista antes de registrar la devolución.

### Ventas recientes
- [x] Mostrar primero las ventas más recientes.
- [x] Permitir buscar una venta por ID.

### Filtrado según usuario

#### Tienda
- [x] Mostrar únicamente las ventas pertenecientes a su tienda.

#### Administrador
- [x] Permitir consultar ventas de cualquier tienda.

#### Vendedor
- [x] Permitir filtrar ventas por vendedor cuando corresponda.

### Reversión de stock
- [x] Confirmar si una devolución devuelve automáticamente el producto al inventario. → Sí, se revierte automáticamente.
- [x] Confirmar si la devolución debe pasar primero por aprobación. → No, se aplica directamente.
- [x] Implementar el comportamiento una vez definida la regla.

---

## 6. Gestión de Roles y Permisos

### Panel centralizado
- [x] Crear un módulo o panel llamado `Gestión de Roles y Permisos`.
- [x] Permitir configurar módulos visibles por rol.
- [x] Permitir configurar columnas visibles por rol.
- [x] Guardar estas configuraciones sin necesidad de modificar código.

### Módulos visibles por rol
- [x] Configurar Inventario.
- [x] Configurar Ventas.
- [x] Configurar Solicitudes.
- [x] Configurar Devoluciones.
- [x] Permitir agregar nuevos módulos en el futuro.

Ejemplo:

Para Tienda:

- [x] Inventario.
- [x] Ventas.
- [x] Solicitudes.
- [x] Devoluciones.
- [x] Otros módulos según configuración del administrador.

### Restricción de acceso
- [x] Un módulo oculto no debe aparecer en el menú.
- [x] Un módulo oculto tampoco debe ser accesible mediante URL directa.
- [x] Validar permisos desde backend.
- [x] Validar permisos desde frontend.

### Columnas visibles por rol
- [x] Configurar columnas visibles de Inventario.
- [x] Configurar columnas visibles de Ventas.
- [x] Mostrar solamente las columnas permitidas para cada rol.
- [x] Impedir que el usuario habilite columnas restringidas por el administrador.

### Preferencias personales
Dentro de las columnas permitidas por el administrador:

- [x] Permitir cambiar el orden.
- [x] Permitir ocultar columnas.
- [x] Permitir volver a mostrar columnas.
- [x] Guardar preferencias individuales por usuario.

### Auditoría de permisos
Registrar:

- [x] Administrador que realizó el cambio.
- [x] Rol modificado.
- [x] Permiso modificado.
- [x] Valor anterior.
- [x] Valor nuevo.
- [x] Fecha.
- [x] Hora.

---

# Tareas compartidas / coordinación

## Búsqueda
- [x] Erika desarrolla la lógica base de búsqueda en Inventario.
- [x] Ross reutiliza esa lógica en Ventas.
- [x] Mantener el mismo comportamiento de búsqueda en ambos módulos.

## Roles y permisos
- [x] Ross desarrolla la configuración general de roles y permisos.
- [x] Erika aplica las restricciones correspondientes en Inventario y Solicitudes.
- [x] Ross aplica las restricciones correspondientes en Ventas y Devoluciones.

## Pruebas integrales
- [x] Verificar que Tienda no pueda editar Inventario.
- [x] Verificar que Encargado de Inventario no pueda editar Inventario.
- [x] Verificar que Tienda solo pueda vender productos de su tienda.
- [x] Verificar que el Administrador pueda operar según sus permisos.
- [x] Verificar el flujo completo de Solicitudes.
- [x] Verificar las restricciones de acceso por módulo.
- [x] Verificar las restricciones de columnas.
- [x] Verificar búsquedas por marca, modelo y año.
- [x] Verificar rangos de año.
- [x] Verificar Devoluciones.

---

# Pendientes de confirmación

- [x] Confirmar si el Administrador puede editar libremente Inventario. → Sí, ya está implementado así (solo ADMIN puede crear/editar/eliminar productos).
- [x] Confirmar si las devoluciones regresan automáticamente el producto al stock. → Sí, ya estaba implementado.
- [x] Confirmar si la devolución debe pasar primero por aprobación. → No, se aplica directamente sin aprobación.
- [x] Confirmar si existirán módulos obligatorios que no puedan ocultarse. → No, todos los módulos pueden ocultarse según configuración del admin.
- [x] Confirmar si existirán columnas obligatorias que no puedan ocultarse. → No, todas las columnas pueden ocultarse según configuración del admin.
- [x] Confirmar si el ID debe mostrarse obligatoriamente en determinadas tablas. → No, el ID es una columna configurable como cualquier otra.
- [x] Confirmar si los vendedores serán usuarios registrados o solamente opciones internas de cada tienda. → Opciones internas (Vendedor 1, Vendedor 2, Vendedor 3).