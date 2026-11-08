import type { Prisma } from "@prisma/client";
import { money } from "./pricing";

export async function saleBalance(tx: Prisma.TransactionClient, saleId: number, total: number) {
  const [payments, returns] = await Promise.all([
    tx.payment.aggregate({ where: { saleId, method: { not: "CREDITO" } }, _sum: { amount: true } }),
    tx.return.aggregate({ where: { saleId }, _sum: { amount: true, refundAmount: true, debtReduction: true } }),
  ]);
  const paid = Number(payments._sum.amount || 0);
  const returned = Number(returns._sum.amount || 0);
  const refunded = Number(returns._sum.refundAmount || 0);
  return { paid, returned, refunded, debtReduced: Number(returns._sum.debtReduction || 0),
    pending: money(Math.max(0, total - paid - returned + refunded), "Saldo pendiente", true) };
}
