-- Aditiva. LEGACY conserva saldos y hechos históricos sin inferir recepciones o reintegros.
CREATE TYPE "MovementStatus" AS ENUM ('LEGACY', 'IN_TRANSIT', 'RECEIVED');
CREATE TYPE "ReturnDisposition" AS ENUM ('LEGACY', 'PENDING_INSPECTION', 'SELLABLE', 'NOT_SELLABLE', 'MIXED');
ALTER TABLE "Movement"
  ADD COLUMN "status" "MovementStatus" NOT NULL DEFAULT 'LEGACY',
  ADD COLUMN "receivedQuantity" INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN "receivedAt" TIMESTAMP(3);
ALTER TABLE "Return"
  ADD COLUMN "disposition" "ReturnDisposition" NOT NULL DEFAULT 'LEGACY',
  ADD COLUMN "restockedQuantity" INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN "discardedQuantity" INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN "debtReduction" DECIMAL(65,30) NOT NULL DEFAULT 0,
  ADD COLUMN "refundAmount" DECIMAL(65,30) NOT NULL DEFAULT 0,
  ADD COLUMN "inspectedAt" TIMESTAMP(3);
ALTER TABLE "Movement" ADD CONSTRAINT "Movement_received_quantity_valid" CHECK (
  "status" = 'LEGACY' OR ("quantity" > 0 AND "receivedQuantity" >= 0 AND "receivedQuantity" <= "quantity")
);
ALTER TABLE "Return" ADD CONSTRAINT "Return_inspection_quantities_valid" CHECK (
  "disposition" = 'LEGACY' OR ("quantity" > 0 AND "restockedQuantity" >= 0 AND "discardedQuantity" >= 0
    AND "restockedQuantity" + "discardedQuantity" <= "quantity")
);
ALTER TABLE "Return" ADD CONSTRAINT "Return_financial_allocation_valid" CHECK (
  "disposition" = 'LEGACY' OR ("debtReduction" >= 0 AND "refundAmount" >= 0
    AND "debtReduction" + "refundAmount" = "amount")
);
CREATE INDEX "Movement_status_date_idx" ON "Movement"("status", "date");
CREATE INDEX "Return_disposition_date_idx" ON "Return"("disposition", "date");
