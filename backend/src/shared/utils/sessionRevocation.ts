import { createHash } from "crypto";
import type { Prisma } from "@prisma/client";

export const tokenDigest = (token: string): string => createHash("sha256").update(token).digest("hex");

/** Revoca sesiones en la misma transacción que cambia las credenciales o el alcance. */
export async function revokeUserSessions(tx: Prisma.TransactionClient, actorId: number, userId: number) {
  await tx.auditLog.create({ data: {
    userId: actorId, action: "REVOKE_USER_SESSIONS", targetType: "USER", targetId: userId,
    newValue: { reason: "CREDENTIALS_OR_SCOPE_CHANGED" },
  } });
}
