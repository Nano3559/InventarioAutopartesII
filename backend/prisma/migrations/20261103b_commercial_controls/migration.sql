-- Aditiva. No certifica ni completa referencias bancarias o facturas históricas.
CREATE TYPE "SaleStatus" AS ENUM ('CONFIRMED', 'VOIDED');
ALTER TABLE "Sale" ADD COLUMN "status" "SaleStatus" NOT NULL DEFAULT 'CONFIRMED',
 ADD COLUMN "voidReason" TEXT, ADD COLUMN "voidedAt" TIMESTAMP(3), ADD COLUMN "voidedById" INTEGER;
CREATE TABLE "ReceivingAccount" (
 "id" SERIAL NOT NULL PRIMARY KEY, "code" TEXT NOT NULL, "name" TEXT NOT NULL, "active" BOOLEAN NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX "ReceivingAccount_code_key" ON "ReceivingAccount"("code");
ALTER TABLE "Payment" ADD COLUMN "receivingAccountId" INTEGER, ADD COLUMN "bankReference" TEXT,
 ADD COLUMN "bankOperationDate" TEXT, ADD COLUMN "verifiedAt" TIMESTAMP(3), ADD COLUMN "verifiedById" INTEGER;
ALTER TABLE "Payment" ADD CONSTRAINT "Payment_receivingAccountId_fkey" FOREIGN KEY ("receivingAccountId") REFERENCES "ReceivingAccount"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "Payment" ADD CONSTRAINT "Payment_verifiedById_fkey" FOREIGN KEY ("verifiedById") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;
CREATE UNIQUE INDEX "Payment_receivingAccountId_bankReference_bankOperationDate_key" ON "Payment"("receivingAccountId", "bankReference", "bankOperationDate");
CREATE TABLE "PurchaseInvoice" (
 "id" SERIAL NOT NULL PRIMARY KEY, "supplierId" INTEGER NOT NULL, "documentIdentity" TEXT NOT NULL,
 "identityKey" TEXT NOT NULL, "contentHash" TEXT NOT NULL, "result" JSONB NOT NULL,
 "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT "PurchaseInvoice_supplierId_fkey" FOREIGN KEY ("supplierId") REFERENCES "Supplier"("id") ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE UNIQUE INDEX "PurchaseInvoice_supplierId_identityKey_key" ON "PurchaseInvoice"("supplierId", "identityKey");
ALTER TABLE "Cost" ADD COLUMN "purchaseInvoiceId" INTEGER;
ALTER TABLE "Cost" ADD CONSTRAINT "Cost_purchaseInvoiceId_fkey" FOREIGN KEY ("purchaseInvoiceId") REFERENCES "PurchaseInvoice"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "Sale" ADD CONSTRAINT "Sale_void_metadata_valid" CHECK (
 "status" <> 'VOIDED' OR ("voidedAt" IS NOT NULL AND "voidedById" IS NOT NULL AND length(trim("voidReason")) >= 10)
);
