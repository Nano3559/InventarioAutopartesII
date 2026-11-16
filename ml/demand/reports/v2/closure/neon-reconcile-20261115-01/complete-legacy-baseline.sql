-- Complete only missing effects of the legacy baseline. TEST BRANCH FIRST.
-- No historical row values are rewritten. Product.quality remains untouched.
BEGIN;
DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM "AuditLog" WHERE "userId" IS NULL OR "targetType" IS NULL) THEN
  RAISE EXCEPTION 'Legacy audit NULLs require a human decision';
 END IF;
 IF EXISTS (SELECT 1 FROM "AuditLog" a LEFT JOIN "User" u ON u.id=a."userId" WHERE u.id IS NULL) THEN
  RAISE EXCEPTION 'Legacy audit has orphan users';
 END IF;
END $$;
ALTER TABLE "AuditLog" ALTER COLUMN "userId" SET NOT NULL;
ALTER TABLE "AuditLog" ALTER COLUMN "targetType" SET NOT NULL;
ALTER TABLE "AuditLog" DROP CONSTRAINT "AuditLog_userId_fkey";
ALTER TABLE "AuditLog" ADD CONSTRAINT "AuditLog_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "Notification" ALTER COLUMN "type" SET DEFAULT 'INFO';
-- These exact DROP/CREATE index effects belong to close_schema_drift.
-- Transactional replacement preserves uniqueness without a concurrent-write gap.
DROP INDEX "Customer_nit_key";
DROP INDEX "Supplier_nit_key";
CREATE UNIQUE INDEX "Customer_nit_key" ON "Customer"("nit");
CREATE UNIQUE INDEX "Supplier_nit_key" ON "Supplier"("nit");
COMMIT;
