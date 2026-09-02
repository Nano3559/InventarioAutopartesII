-- CreateIndex
CREATE UNIQUE INDEX "Customer_nit_key" ON "Customer"("nit") WHERE "nit" IS NOT NULL;

-- CreateIndex
CREATE UNIQUE INDEX "Supplier_nit_key" ON "Supplier"("nit") WHERE "nit" IS NOT NULL;