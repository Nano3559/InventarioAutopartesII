-- AlterTable
ALTER TABLE "Product" ADD COLUMN     "quality" TEXT;

-- CreateTable
CREATE TABLE "Importer" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "phone" TEXT,
    "email" TEXT,
    "address" TEXT,
    "city" TEXT,
    "logo" TEXT,
    "description" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Importer_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ProductImporter" (
    "id" SERIAL NOT NULL,
    "productId" INTEGER NOT NULL,
    "importerId" INTEGER NOT NULL,

    CONSTRAINT "ProductImporter_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "ProductImporter_productId_importerId_key" ON "ProductImporter"("productId", "importerId");

-- AddForeignKey
ALTER TABLE "ProductImporter" ADD CONSTRAINT "ProductImporter_productId_fkey" FOREIGN KEY ("productId") REFERENCES "Product"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ProductImporter" ADD CONSTRAINT "ProductImporter_importerId_fkey" FOREIGN KEY ("importerId") REFERENCES "Importer"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
