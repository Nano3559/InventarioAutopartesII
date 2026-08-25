# Corrección de Observaciones

## Distribución de tareas

---

# Erika

## 1. Inventario

### Estructura de datos
- [ ] Agregar el campo `detalles` al inventario.
- [ ] Reemplazar la columna visible `calidad` por `detalles`.
- [ ] Revisar los cambios necesarios en base de datos, backend y frontend.
- [ ] Permitir múltiples valores separados por `/` en:
  - [ ] Marca.
  - [ ] Modelo.
  - [ ] Año.

Ejemplo:

```text
Marca: Toyota/Nissan
Modelo: Tacoma/Frontier
Año: 05-08/12-16
```

### Lógica de rangos de años
- [ ] Implementar la interpretación de rangos de años.

Casos:

- `13-15` → incluye 2013, 2014 y 2015.
- `13` → corresponde únicamente a 2013.
- `13-` → corresponde a 2013 en adelante.
- [ ] Permitir múltiples rangos separados por `/`.
- [ ] Validar rangos incorrectos.
- [ ] Definir mensaje de validación para valores como `15-13`.

### Permisos en Inventario
- [ ] Las tiendas pueden visualizar inventario.
- [ ] Las tiendas no pueden editar inventario.
- [ ] Los encargados de inventario pueden visualizar inventario.
- [ ] Los encargados de inventario no pueden editar inventario.
- [ ] Confirmar si el administrador puede editar inventario libremente.

---

## 2. Búsqueda de Inventario

### Autocompletado
- [ ] Implementar sugerencias mientras el usuario escribe.
- [ ] Autocompletado para Marca.
- [ ] Autocompletado para Modelo.
- [ ] Autocompletado para Año.
- [ ] Evaluar otras columnas donde corresponda aplicar sugerencias.

Ejemplo:

`Toy` → sugerir `Toyota`.

### Búsqueda exacta por columna
- [ ] Permitir búsqueda específica por Marca.
- [ ] Permitir búsqueda específica por Modelo.
- [ ] Permitir búsqueda específica por Año.
- [ ] Considerar correctamente valores múltiples separados por `/`.

Ejemplo:

Si un producto tiene:

`Toyota/Nissan`

una búsqueda por:

`Toyota`

debe encontrar el producto.

### Búsqueda por rangos de años
- [ ] Aplicar la misma lógica de rangos utilizada en Inventario.
- [ ] Permitir buscar años incluidos dentro de un rango.

Ejemplo:

Producto:

`13-15`

Búsqueda:

`14`

Resultado:

Debe encontrar el producto.

- [ ] Preparar esta lógica para que pueda reutilizarse posteriormente en Ventas.

---

## 3. Solicitudes

### Nota opcional
- [ ] Agregar campo de nota al crear una solicitud.
- [ ] La nota debe ser opcional.
- [ ] Mostrar la nota en el detalle de la solicitud cuando exista.

### Flujo de estados
Implementar los siguientes estados:

- [ ] Solicitud creada.
- [ ] Recibido por Inventario.
- [ ] Preparando.
- [ ] Entregado.
- [ ] Recibido por Tienda o Administrador.

### Permisos para cambio de estado

#### Encargado de Inventario
- [ ] Puede marcar como Recibido.
- [ ] Puede cambiar a Preparando.
- [ ] Puede cambiar a Entregado.

#### Tienda / Administrador
- [ ] Puede confirmar la recepción final.

### Historial de estados
Registrar:

- [ ] Estado anterior.
- [ ] Estado nuevo.
- [ ] Usuario que realizó el cambio.
- [ ] Rol del usuario.
- [ ] Fecha.
- [ ] Hora.

### Notificaciones
- [ ] Notificar a la tienda cuando cambie el estado de su solicitud.
- [ ] Mostrar claramente el nuevo estado.
- [ ] Verificar que la notificación corresponda a la tienda que realizó la solicitud.

---

# Ross

## 4. Ventas

### Restricción por tienda
- [ ] Cada tienda solo puede vender productos asignados a su propia tienda.
- [ ] Impedir que una tienda venda inventario correspondiente a otra tienda.
- [ ] Aplicar la validación también desde backend.

### Vendedores
Cada tienda debe manejar tres vendedores internos.

- [ ] Permitir seleccionar Vendedor 1.
- [ ] Permitir seleccionar Vendedor 2.
- [ ] Permitir seleccionar Vendedor 3.
- [ ] Guardar el vendedor asociado a la venta.
- [ ] Mostrar el vendedor en el detalle de venta.
- [ ] Permitir filtrar las ventas por vendedor.

### Administrador
- [ ] El administrador puede vender en nombre de cualquier tienda.
- [ ] Permitir seleccionar la tienda al registrar la venta.
- [ ] Permitir seleccionar el vendedor correspondiente.

### Búsqueda en Ventas
- [ ] Aplicar el mismo sistema de búsqueda utilizado en Inventario.
- [ ] Implementar autocompletado.
- [ ] Implementar búsqueda exacta por columna.
- [ ] Aplicar la lógica de rangos de años.
- [ ] Reutilizar la lógica creada en Inventario.

---

## 5. Devoluciones

### Identificación de venta
- [ ] Toda devolución debe requerir el ID de la venta.
- [ ] Verificar que la venta exista antes de registrar la devolución.

### Ventas recientes
- [ ] Mostrar primero las ventas más recientes.
- [ ] Permitir buscar una venta por ID.

### Filtrado según usuario

#### Tienda
- [ ] Mostrar únicamente las ventas pertenecientes a su tienda.

#### Administrador
- [ ] Permitir consultar ventas de cualquier tienda.

#### Vendedor
- [ ] Permitir filtrar ventas por vendedor cuando corresponda.

### Reversión de stock
- [ ] Confirmar si una devolución devuelve automáticamente el producto al inventario.
- [ ] Confirmar si la devolución debe pasar primero por aprobación.
- [ ] Implementar el comportamiento una vez definida la regla.

---

## 6. Gestión de Roles y Permisos

### Panel centralizado
- [ ] Crear un módulo o panel llamado `Gestión de Roles y Permisos`.
- [ ] Permitir configurar módulos visibles por rol.
- [ ] Permitir configurar columnas visibles por rol.
- [ ] Guardar estas configuraciones sin necesidad de modificar código.

### Módulos visibles por rol
- [ ] Configurar Inventario.
- [ ] Configurar Ventas.
- [ ] Configurar Solicitudes.
- [ ] Configurar Devoluciones.
- [ ] Permitir agregar nuevos módulos en el futuro.

Ejemplo:

Para Tienda:

- [ ] Inventario.
- [ ] Ventas.
- [ ] Solicitudes.
- [ ] Devoluciones.
- [ ] Otros módulos según configuración del administrador.

### Restricción de acceso
- [ ] Un módulo oculto no debe aparecer en el menú.
- [ ] Un módulo oculto tampoco debe ser accesible mediante URL directa.
- [ ] Validar permisos desde backend.
- [ ] Validar permisos desde frontend.

### Columnas visibles por rol
- [ ] Configurar columnas visibles de Inventario.
- [ ] Configurar columnas visibles de Ventas.
- [ ] Mostrar solamente las columnas permitidas para cada rol.
- [ ] Impedir que el usuario habilite columnas restringidas por el administrador.

### Preferencias personales
Dentro de las columnas permitidas por el administrador:

- [ ] Permitir cambiar el orden.
- [ ] Permitir ocultar columnas.
- [ ] Permitir volver a mostrar columnas.
- [ ] Guardar preferencias individuales por usuario.

### Auditoría de permisos
Registrar:

- [ ] Administrador que realizó el cambio.
- [ ] Rol modificado.
- [ ] Permiso modificado.
- [ ] Valor anterior.
- [ ] Valor nuevo.
- [ ] Fecha.
- [ ] Hora.

---

# Tareas compartidas / coordinación

## Búsqueda
- [ ] Erika desarrolla la lógica base de búsqueda en Inventario.
- [ ] Ross reutiliza esa lógica en Ventas.
- [ ] Mantener el mismo comportamiento de búsqueda en ambos módulos.

## Roles y permisos
- [ ] Ross desarrolla la configuración general de roles y permisos.
- [ ] Erika aplica las restricciones correspondientes en Inventario y Solicitudes.
- [ ] Ross aplica las restricciones correspondientes en Ventas y Devoluciones.

## Pruebas integrales
- [ ] Verificar que Tienda no pueda editar Inventario.
- [ ] Verificar que Encargado de Inventario no pueda editar Inventario.
- [ ] Verificar que Tienda solo pueda vender productos de su tienda.
- [ ] Verificar que el Administrador pueda operar según sus permisos.
- [ ] Verificar el flujo completo de Solicitudes.
- [ ] Verificar las restricciones de acceso por módulo.
- [ ] Verificar las restricciones de columnas.
- [ ] Verificar búsquedas por marca, modelo y año.
- [ ] Verificar rangos de año.
- [ ] Verificar Devoluciones.

---

# Pendientes de confirmación

- [ ] Confirmar si el Administrador puede editar libremente Inventario.
- [ ] Confirmar si las devoluciones regresan automáticamente el producto al stock.
- [ ] Confirmar si las devoluciones requieren aprobación.
- [ ] Confirmar si existirán módulos obligatorios que no puedan ocultarse.
- [ ] Confirmar si existirán columnas obligatorias que no puedan ocultarse.
- [ ] Confirmar si el ID debe mostrarse obligatoriamente en determinadas tablas.
- [ ] Confirmar si los vendedores serán usuarios registrados o solamente opciones internas de cada tienda.