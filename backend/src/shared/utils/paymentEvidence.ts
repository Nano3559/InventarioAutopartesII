import type { Prisma } from "@prisma/client";
import { errorDominio } from "./errorDominio";
import { inicioDiaNegocio, fechaNegocio } from "./rangoFechas";

export function bankReferenceConflict(error: any): boolean {
  return error?.code === "P2002" && String(error?.meta?.target).includes("bankReference");
}

/** La declaración la realiza el operador. No es una confirmación automática del banco. */
export async function paymentEvidence(tx: Prisma.TransactionClient, payments: any[], actorId: number) {
  const result = [];
  for (const payment of payments) {
    const basic = { method: payment.method, amount: payment.amount };
    if (!["QR", "TRANSFERENCIA"].includes(payment.method) || payment.amount === 0) { result.push(basic); continue; }
    const evidence = payment.bankVerification;
    if (!evidence || evidence.confirmed !== true) throw errorDominio("Compruebe el abono bancario y confirme su verificación manual");
    if (!Number.isSafeInteger(evidence.receivingAccountId) || evidence.receivingAccountId < 1) throw errorDominio("Seleccione una cuenta receptora registrada");
    const account = await tx.receivingAccount.findUnique({ where: { id: evidence.receivingAccountId } });
    if (!account?.active) throw errorDominio("Cuenta receptora no disponible");
    if (typeof evidence.reference !== "string") throw errorDominio("Referencia bancaria requerida");
    const reference = evidence.reference.normalize("NFKC").trim().replace(/\s+/g, " ").toUpperCase();
    if (reference.length < 3 || reference.length > 120) throw errorDominio("La referencia bancaria debe tener entre 3 y 120 caracteres");
    const date = evidence.operationDate;
    if (typeof date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(date)) throw errorDominio("Fecha bancaria requerida en formato YYYY-MM-DD");
    if (!inicioDiaNegocio(date)) throw errorDominio("Fecha bancaria inválida");
    if (date > fechaNegocio(new Date())) throw errorDominio("La fecha bancaria no puede ser futura");
    if (result.some((p: any) => p.receivingAccountId === account.id && p.bankReference === reference && p.bankOperationDate === date)) throw errorDominio("La referencia bancaria está repetida dentro del pago");
    const duplicate = await tx.payment.findFirst({ where: { receivingAccountId: account.id, bankReference: reference, bankOperationDate: date }, select: { id: true } });
    if (duplicate) throw errorDominio("La referencia bancaria ya fue registrada en esta cuenta y fecha");
    await tx.auditLog.create({ data: { userId: actorId, action: "CONFIRM_BANK_RECEIPT", targetType: "RECEIVING_ACCOUNT", targetId: account.id,
      newValue: { reference, operationDate: date, amount: payment.amount, method: payment.method, manualVerification: true } } });
    result.push({ ...basic, receivingAccountId: account.id, bankReference: reference, bankOperationDate: date,
      verifiedAt: new Date(), verifiedById: actorId });
  }
  return result;
}
