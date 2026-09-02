-- AlterTable
ALTER TABLE "Movement" ADD COLUMN "requestId" INTEGER;

-- AddForeignKey
ALTER TABLE "Movement" ADD CONSTRAINT "Movement_requestId_fkey" FOREIGN KEY ("requestId") REFERENCES "ProductRequest"("id") ON DELETE SET NULL ON UPDATE CASCADE;
