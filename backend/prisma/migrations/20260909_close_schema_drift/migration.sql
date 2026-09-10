-- Cierra el drift entre schema.prisma y las migraciones históricas.
-- Estrategia NO destructiva: solo ADD/CREATE/RENAME conservando datos.
-- No se altera ninguna migración existente; esta es una migración progresiva formal.

-- 1. RequestStatus: añade los nuevos estados del schema actual.
--    Los valores legados (EN_PREPARACION, ENVIADO, RECIBIDO) se conservan como
--    valores huérfanos del tipo para no invalidar filas existentes de ProductRequest.
ALTER TYPE "RequestStatus" ADD VALUE IF NOT EXISTS 'RECIBIDO_POR_INVENTARIO';
ALTER TYPE "RequestStatus" ADD VALUE IF NOT EXISTS 'PREPARANDO';
ALTER TYPE "RequestStatus" ADD VALUE IF NOT EXISTS 'ENTREGADO';
ALTER TYPE "RequestStatus" ADD VALUE IF NOT EXISTS 'RECIBIDO_POR_TIENDA';

-- 2. Product: el schema actual usa `detalles` (y el import de productos lo escribe)
--    mientras la migración histórica creó `quality` (columna legada del mismo dato).
--    Renombrar conserva los datos existentes sin pérdida.
ALTER TABLE "Product" RENAME COLUMN "quality" TO "detalles";

-- 3. ProductRequest: nota y fecha esperada para la reposición automática.
ALTER TABLE "ProductRequest" ADD COLUMN "note" TEXT,
ADD COLUMN "expectedDate" TIMESTAMP(3);

-- 4. RoleModel: configuración de columnas por rol.
ALTER TABLE "RoleModel" ADD COLUMN "columnConfig" JSONB;

-- 5. User: preferencias de columnas por usuario (archivo suelto add_seller_columnPrefs.sql).
ALTER TABLE "User" ADD COLUMN "columnPrefs" JSONB;

-- 6. Sale: columnas del flujo mayorista (solo añadidas; los campos son opcionales).
ALTER TABLE "Sale" ADD COLUMN "seller" TEXT,
ADD COLUMN "paraQuien" TEXT,
ADD COLUMN "lugarEntrega" TEXT,
ADD COLUMN "datosFactura" TEXT,
ADD COLUMN "formaPago" TEXT;

-- 7. RequestHistory: historial de estados de solicitudes.
CREATE TABLE "RequestHistory" (
    "id" SERIAL NOT NULL,
    "requestId" INTEGER NOT NULL,
    "previousStatus" TEXT,
    "newStatus" TEXT NOT NULL,
    "userId" INTEGER NOT NULL,
    "userRole" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "RequestHistory_pkey" PRIMARY KEY ("id")
);

-- 8. AuditLog: auditoría global.
CREATE TABLE "AuditLog" (
    "id" SERIAL NOT NULL,
    "userId" INTEGER NOT NULL,
    "action" TEXT NOT NULL,
    "targetType" TEXT NOT NULL,
    "targetId" INTEGER,
    "oldValue" JSONB,
    "newValue" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "AuditLog_pkey" PRIMARY KEY ("id")
);

-- 9. Notification: notificaciones por usuario.
CREATE TABLE "Notification" (
    "id" SERIAL NOT NULL,
    "userId" INTEGER NOT NULL,
    "title" TEXT NOT NULL,
    "message" TEXT NOT NULL,
    "type" TEXT NOT NULL DEFAULT 'INFO',
    "read" BOOLEAN NOT NULL DEFAULT false,
    "linkUrl" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Notification_pkey" PRIMARY KEY ("id")
);

-- 10. Claves foráneas y índices.

-- Prisma 5.22 interpreta estas relaciones opcionales con ON DELETE RESTRICT
-- (mismo policy que el resto del schema: nunca perder auditoría/notificaciones
-- silenciosamente). Se crean directamente con RESTRICT para que la BD coincida
-- exactamente con lo que Prisma espera.
ALTER TABLE "RequestHistory" ADD CONSTRAINT "RequestHistory_requestId_fkey" FOREIGN KEY ("requestId") REFERENCES "ProductRequest"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "AuditLog" ADD CONSTRAINT "AuditLog_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "Notification" ADD CONSTRAINT "Notification_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- El schema declara nit como @unique (índice único completo). La migración previa
-- creó índices únicos parciales (WHERE nit IS NOT NULL); en PostgreSQL el
-- comportamiento con NULL es idéntico (los NULL no colisionan). Se reemplazan por
-- el índice único completo del schema sin pérdida de datos ni reglas de unicidad.
DROP INDEX IF EXISTS "Customer_nit_key";
DROP INDEX IF EXISTS "Supplier_nit_key";
CREATE UNIQUE INDEX "Customer_nit_key" ON "Customer"("nit");
CREATE UNIQUE INDEX "Supplier_nit_key" ON "Supplier"("nit");