-- ETAPA 9 (Ross): una sola solicitud ABIERTA de reposición por producto y ubicación.
--
-- PROBLEMA: el job de reposición comprobaba "ya existe una solicitud abierta?" con
-- findFirst y luego creaba la fila en otra sentencia (TOCTOU). Dos corridas
-- simultáneas del job (o dos procesos) veían "sin solicitud abierta" a la vez y
-- creaban dos solicitudes idénticas. Además el chequeo omitía el estado ENTREGADO
-- (mercadería ya salida del almacén pero todavía no recibida por la tienda), que
-- sigue siendo una solicitud abierta.
--
-- REGLA DE NEGOCIO IMPLEMENTADA: como máximo UNA solicitud en estado activo por
-- (producto, ubicación solicitante). Estados activos = PENDIENTE, RECIBIDO_POR_INVENTARIO,
-- PREPARANDO, ENTREGADO. RECIBIDO_POR_TIENDA y CANCELADO son terminales, así que tras
-- cerrar o cancelar una solicitud SÍ se permite crear la siguiente (el histórico se
-- preserva intacto).
--
-- La regla se aplica igual a solicitudes manuales y automáticas: una tienda no debe
-- tener dos pedidos del mismo autoparte en curso, sin importar quién lo generó.
--
-- MIGRACIÓN NO DESTRUCTIVA: solo crea un índice. No modifica ni borra filas, no altera
-- columnas y no reescribe el enum de estados. Antes de crearla se verificó que no
-- hubiera solicitudes con duplicados activos, por lo que el índice se crea sin
-- necesidad de limpiar datos.
--
-- ÍNDICE PARCIAL: solo cubre las filas activas, de modo que el histórico de solicitudes
-- cerradas puede seguir acumulando repeticiones del mismo producto sin estorbar. Se
-- declara a mano porque Prisma no permite expresar índices con WHERE en el schema.
-- Debe mantenerse sincronizado con REQUEST_STATUS_ACTIVOS en
-- backend/src/utils/replenish.ts.

CREATE UNIQUE INDEX "ProductRequest_solicitud_abierta_unica"
  ON "ProductRequest" ("productId", "locationId")
  WHERE "status" IN ('PENDIENTE', 'RECIBIDO_POR_INVENTARIO', 'PREPARANDO', 'ENTREGADO');
