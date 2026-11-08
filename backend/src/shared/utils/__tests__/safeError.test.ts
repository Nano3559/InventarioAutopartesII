import { test } from "node:test";
import assert from "node:assert/strict";
import { safeError } from "../safeError";
test("el registro conserva el código sin mensajes, SQL, cuerpos ni credenciales", () => {
  assert.deepEqual(safeError({ code: "P2002", message: "password=secreto", query: "SELECT privado", body: { token: "secreto" } }), { code: "P2002" });
  assert.deepEqual(safeError(new Error("cadena privada")), { code: "INTERNAL_ERROR" });
  assert.deepEqual(safeError({ code: "https://usuario:clave@servidor" }), { code: "INTERNAL_ERROR" });
});
