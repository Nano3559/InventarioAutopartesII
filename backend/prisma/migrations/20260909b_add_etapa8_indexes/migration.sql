-- ETAPA 8 (Ross): índices aditivos para queries frecuentes de inventario,
-- ventas, movimientos, solicitudes, auditoría y notificaciones.
-- Migración NO destructiva: solo CREATE INDEX + CREATE INDEX. No toca datos.

-- Inventory: listado y replenish por ubicación (inventario de una tienda/almacén)
CREATE INDEX "Inventory_locationId_idx" ON "Inventory"("locationId");

-- Sale: ventas por usuario; listado por tienda ordenado por fecha descendente
CREATE INDEX "Sale_userId_idx" ON "Sale"("userId");
CREATE INDEX "Sale_locationId_saleDate_idx" ON "Sale"("locationId", "saleDate" DESC);

-- SaleItem: reportes de ventas por producto; pre-check de borrado de producto
CREATE INDEX "SaleItem_productId_idx" ON "SaleItem"("productId");

-- Payment: pagos por venta (FK con onDelete Cascade requiere índice)
CREATE INDEX "Payment_saleId_idx" ON "Payment"("saleId");

-- Return: devoluciones por venta y por producto (reportes)
CREATE INDEX "Return_saleId_idx" ON "Return"("saleId");
CREATE INDEX "Return_productId_idx" ON "Return"("productId");

-- Movement: historial por producto; entradas/ORM de tienda
CREATE INDEX "Movement_productId_idx" ON "Movement"("productId");
CREATE INDEX "Movement_toLocationId_idx" ON "Movement"("toLocationId");

-- ProductRequest: job de reposición (status + expectedDate); listado por tienda;
-- solicitudes de un usuario
CREATE INDEX "ProductRequest_status_expectedDate_idx" ON "ProductRequest"("status", "expectedDate");
CREATE INDEX "ProductRequest_locationId_idx" ON "ProductRequest"("locationId");
CREATE INDEX "ProductRequest_requestedById_idx" ON "ProductRequest"("requestedById");

-- RequestHistory: línea de tiempo por solicitud (FK sin índice)
CREATE INDEX "RequestHistory_requestId_idx" ON "RequestHistory"("requestId");

-- AuditLog: auditoría por usuario; listado ordenado descendente
CREATE INDEX "AuditLog_userId_idx" ON "AuditLog"("userId");
CREATE INDEX "AuditLog_createdAt_idx" ON "AuditLog"("createdAt" DESC);

-- Notification: bandeja por usuario (filtra por leído/no leído)
CREATE INDEX "Notification_userId_read_idx" ON "Notification"("userId", "read");

-- Cost: histórico por producto; por proveedor
CREATE INDEX "Cost_productId_idx" ON "Cost"("productId");
CREATE INDEX "Cost_supplierId_idx" ON "Cost"("supplierId");

-- ProductImporter: productos de un importador (borrado/consulta)
CREATE INDEX "ProductImporter_importerId_idx" ON "ProductImporter"("importerId");