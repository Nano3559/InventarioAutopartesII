/** Adaptador explícito para los fixtures históricos que representan abonos comprobados. */
import { randomUUID } from "crypto";
import type { SeedContext } from "./seed";
import { postJson } from "./helpers";
import { fechaNegocio } from "../shared/utils/rangoFechas";
export async function postVerifiedBankFixture(ctx: SeedContext, baseUrl: string, path: string, body: any, token?: string) {
  const bank = (p: any) => ["QR", "TRANSFERENCIA"].includes(p?.method) && !p.bankVerification;
  if (!bank(body) && !body.payments?.some(bank)) return postJson(baseUrl, path, body, token);
  const account = await ctx.prisma.receivingAccount.upsert({ where: { code: `TEST_${ctx.ns.toUpperCase()}_BANK` },
    create: { code: `TEST_${ctx.ns.toUpperCase()}_BANK`, name: "Cuenta ficticia de prueba" }, update: {} });
  const verified = (p: any) => bank(p) ? { ...p, bankVerification: { confirmed: true, receivingAccountId: account.id, reference: randomUUID(), operationDate: fechaNegocio() } } : p;
  return postJson(baseUrl, path, { ...verified(body), ...(body.payments ? { payments: body.payments.map(verified) } : {}) }, token);
}
