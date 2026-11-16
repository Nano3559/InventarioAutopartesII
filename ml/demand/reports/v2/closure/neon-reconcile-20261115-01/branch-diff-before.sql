-- CreateEnum
CREATE TYPE "MovementStatus" AS ENUM ('LEGACY', 'IN_TRANSIT', 'RECEIVED');

-- CreateEnum
CREATE TYPE "ReturnDisposition" AS ENUM ('LEGACY', 'PENDING_INSPECTION', 'SELLABLE', 'NOT_SELLABLE', 'MIXED');

-- CreateEnum
CREATE TYPE "SaleStatus" AS ENUM ('CONFIRMED', 'VOIDED');

-- DropForeignKey
ALTER TABLE "AuditLog" DROP CONSTRAINT "AuditLog_userId_fkey";

-- DropForeignKey
ALTER TABLE "RequestHistory" DROP CONSTRAINT "RequestHistory_userId_fkey";

-- AlterTable
ALTER TABLE "AuditLog" ALTER COLUMN "userId" SET NOT NULL,
ALTER COLUMN "targetType" SET NOT NULL;

-- AlterTable
ALTER TABLE "Cost" ADD COLUMN     "purchaseInvoiceId" INTEGER;

-- AlterTable
ALTER TABLE "Movement" ADD COLUMN     "receivedAt" TIMESTAMP(3),
ADD COLUMN     "receivedQuantity" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "status" "MovementStatus" NOT NULL DEFAULT 'LEGACY';

-- AlterTable
ALTER TABLE "Notification" ALTER COLUMN "type" SET DEFAULT 'INFO';

-- AlterTable
ALTER TABLE "Payment" ADD COLUMN     "bankOperationDate" TEXT,
ADD COLUMN     "bankReference" TEXT,
ADD COLUMN     "receivingAccountId" INTEGER,
ADD COLUMN     "verifiedAt" TIMESTAMP(3),
ADD COLUMN     "verifiedById" INTEGER;

-- AlterTable
ALTER TABLE "Product" DROP COLUMN "quality";

-- AlterTable
ALTER TABLE "Return" ADD COLUMN     "debtReduction" DECIMAL(65,30) NOT NULL DEFAULT 0,
ADD COLUMN     "discardedQuantity" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "disposition" "ReturnDisposition" NOT NULL DEFAULT 'LEGACY',
ADD COLUMN     "inspectedAt" TIMESTAMP(3),
ADD COLUMN     "refundAmount" DECIMAL(65,30) NOT NULL DEFAULT 0,
ADD COLUMN     "restockedQuantity" INTEGER NOT NULL DEFAULT 0;

-- AlterTable
ALTER TABLE "Sale" ADD COLUMN     "status" "SaleStatus" NOT NULL DEFAULT 'CONFIRMED',
ADD COLUMN     "voidReason" TEXT,
ADD COLUMN     "voidedAt" TIMESTAMP(3),
ADD COLUMN     "voidedById" INTEGER;

-- CreateTable
CREATE TABLE "ReceivingAccount" (
    "id" SERIAL NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "active" BOOLEAN NOT NULL DEFAULT true,

    CONSTRAINT "ReceivingAccount_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PurchaseInvoice" (
    "id" SERIAL NOT NULL,
    "supplierId" INTEGER NOT NULL,
    "documentIdentity" TEXT NOT NULL,
    "identityKey" TEXT NOT NULL,
    "contentHash" TEXT NOT NULL,
    "result" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "PurchaseInvoice_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "ReceivingAccount_code_key" ON "ReceivingAccount"("code");

-- CreateIndex
CREATE UNIQUE INDEX "PurchaseInvoice_supplierId_identityKey_key" ON "PurchaseInvoice"("supplierId", "identityKey");

-- CreateIndex
CREATE INDEX "AuditLog_userId_idx" ON "AuditLog"("userId");

-- CreateIndex
CREATE INDEX "AuditLog_createdAt_idx" ON "AuditLog"("createdAt" DESC);

-- CreateIndex
CREATE INDEX "Cost_productId_idx" ON "Cost"("productId");

-- CreateIndex
CREATE INDEX "Cost_supplierId_idx" ON "Cost"("supplierId");

-- CreateIndex
CREATE UNIQUE INDEX "Customer_nit_key" ON "Customer"("nit");

-- CreateIndex
CREATE INDEX "Inventory_locationId_idx" ON "Inventory"("locationId");

-- CreateIndex
CREATE INDEX "Movement_productId_idx" ON "Movement"("productId");

-- CreateIndex
CREATE INDEX "Movement_toLocationId_idx" ON "Movement"("toLocationId");

-- CreateIndex
CREATE INDEX "Movement_status_date_idx" ON "Movement"("status", "date");

-- CreateIndex
CREATE INDEX "Notification_userId_read_idx" ON "Notification"("userId", "read");

-- CreateIndex
CREATE INDEX "Payment_saleId_idx" ON "Payment"("saleId");

-- CreateIndex
CREATE UNIQUE INDEX "Payment_receivingAccountId_bankReference_bankOperationDate_key" ON "Payment"("receivingAccountId", "bankReference", "bankOperationDate");

-- CreateIndex
CREATE INDEX "ProductImporter_importerId_idx" ON "ProductImporter"("importerId");

-- CreateIndex
CREATE INDEX "ProductRequest_status_expectedDate_idx" ON "ProductRequest"("status", "expectedDate");

-- CreateIndex
CREATE INDEX "ProductRequest_locationId_idx" ON "ProductRequest"("locationId");

-- CreateIndex
CREATE INDEX "ProductRequest_requestedById_idx" ON "ProductRequest"("requestedById");

-- CreateIndex
CREATE INDEX "RequestHistory_requestId_idx" ON "RequestHistory"("requestId");

-- CreateIndex
CREATE INDEX "Return_saleId_idx" ON "Return"("saleId");

-- CreateIndex
CREATE INDEX "Return_productId_idx" ON "Return"("productId");

-- CreateIndex
CREATE INDEX "Return_disposition_date_idx" ON "Return"("disposition", "date");

-- CreateIndex
CREATE INDEX "Sale_userId_idx" ON "Sale"("userId");

-- CreateIndex
CREATE INDEX "Sale_locationId_saleDate_idx" ON "Sale"("locationId", "saleDate" DESC);

-- CreateIndex
CREATE INDEX "SaleItem_productId_idx" ON "SaleItem"("productId");

-- CreateIndex
CREATE UNIQUE INDEX "Supplier_nit_key" ON "Supplier"("nit");

-- AddForeignKey
ALTER TABLE "Payment" ADD CONSTRAINT "Payment_receivingAccountId_fkey" FOREIGN KEY ("receivingAccountId") REFERENCES "ReceivingAccount"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Payment" ADD CONSTRAINT "Payment_verifiedById_fkey" FOREIGN KEY ("verifiedById") REFERENCES "User"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PurchaseInvoice" ADD CONSTRAINT "PurchaseInvoice_supplierId_fkey" FOREIGN KEY ("supplierId") REFERENCES "Supplier"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Cost" ADD CONSTRAINT "Cost_purchaseInvoiceId_fkey" FOREIGN KEY ("purchaseInvoiceId") REFERENCES "PurchaseInvoice"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AuditLog" ADD CONSTRAINT "AuditLog_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;


