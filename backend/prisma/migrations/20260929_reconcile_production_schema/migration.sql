-- ============================================================================
-- 20260929_reconcile_production_schema
-- ============================================================================
-- Reconcilia el schema REAL de producción con el estado declarado en
-- schema.prisma. Es una migración FORWARD-ONLY: no borra datos, no elimina
-- columnas y no reconstruye índices.
--
-- Contexto: producción (Neon) tiene el schema aplicado parcialmente y fuera
-- del historial de Prisma, por lo que su estado difiere de la migración
-- 20260909_close_schema_drift en cuatro puntos. Esta migración converge ambos
-- mundos al mismo estado final, y es idempotente: produce el mismo resultado
-- tanto si el punto de partida es una base limpia que ya ejecutó
-- close_schema_drift, como si es el estado real de producción.
--
-- Precondición asumida: "AuditLog"."userId" ya está cubierto por la FK
-- "AuditLog_userId_fkey" en ambos estados de partida, por lo que no puede
-- haber userId huérfanos y la recreation de la FK no puede fallar.
--
-- FUERA DE ALCANCE POR DECISIÓN EXPLÍCITA (no se tocan en esta migración):
--   * Product."quality"          -> LEGACY COLUMN / DEUDA TÉCNICA POST-ENTREGA.
--                                    Se conserva intacta aunque esté vacía.
--   * RequestHistory_userId_fkey -> FK extra no declarada en schema.prisma.
--                                    Es más restrictiva y se conserva.
--   * "Customer_nit_key" y "Supplier_nit_key" -> se mantienen los índices
--                                    únicos PARCIALES (WHERE nit IS NOT NULL)
--                                    ya existentes, funcionalmente equivalentes
--                                    a un índice único completo en PostgreSQL.
--                                    Diferencia histórica documentada, sin
--                                    DROP + CREATE.
--
-- Auditoría previa en producción (read-only) que habilita este cambio:
--   SELECT COUNT(*) FROM "AuditLog" WHERE "userId"    IS NULL;  -- 0
--   SELECT COUNT(*) FROM "AuditLog" WHERE "targetType" IS NULL;  -- 0
-- ============================================================================

-- 1) "AuditLog"."userId": NULL -> NOT NULL (columna required en schema.prisma).
--    Si algún día existieran NULL la migración ABORTA en lugar de inventar
--    un userId: no se puede atribuir una auditoría a un usuario inexistente.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM "AuditLog" WHERE "userId" IS NULL) THEN
        RAISE EXCEPTION
            'reconcile_production_schema: "AuditLog"."userId" tiene % fila(s) con NULL. No se inventa informacion: corrige esos NULL manualmente y vuelve a ejecutar la migracion.',
            (SELECT COUNT(*) FROM "AuditLog" WHERE "userId" IS NULL);
    END IF;
END
$$;

ALTER TABLE "AuditLog" ALTER COLUMN "userId" SET NOT NULL;

-- 2) "AuditLog_userId_fkey": sustituir ON DELETE SET NULL por ON DELETE RESTRICT.
--    Se elimina solo la restricción y se recrea acto seguido (mismo nombre,
--    mismos tipos, ninguna fila afectada). RESTRICT impide que un borrado de
--    usuario deje auditorias huerfanas silenciosamente.
ALTER TABLE "AuditLog" DROP CONSTRAINT IF EXISTS "AuditLog_userId_fkey";
ALTER TABLE "AuditLog" ADD CONSTRAINT "AuditLog_userId_fkey"
    FOREIGN KEY ("userId") REFERENCES "User"("id")
    ON DELETE RESTRICT ON UPDATE CASCADE;

-- 3) "AuditLog"."targetType": NULL -> NOT NULL (columna required en schema.prisma).
--    Misma politica que el punto 1: si hay NULL, la migracion ABORTA.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM "AuditLog" WHERE "targetType" IS NULL) THEN
        RAISE EXCEPTION
            'reconcile_production_schema: "AuditLog"."targetType" tiene % fila(s) con NULL. No se inventa informacion: corrige esos NULL manualmente y vuelve a ejecutar la migracion.',
            (SELECT COUNT(*) FROM "AuditLog" WHERE "targetType" IS NULL);
    END IF;
END
$$;

ALTER TABLE "AuditLog" ALTER COLUMN "targetType" SET NOT NULL;

-- 4) "Notification"."type": default canonico 'INFO'.
--    SET DEFAULT solo afecta a filas futuras; NO modifica filas existentes
--    (que hoy ya contienen 'INFO'/'WARNING' en mayusculas).
ALTER TABLE "Notification" ALTER COLUMN "type" SET DEFAULT 'INFO';
