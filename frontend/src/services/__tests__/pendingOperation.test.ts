import { describe, it, expect, beforeEach } from "vitest";
import { pendingOperationId, completeOperation } from "../pendingOperation";
describe("identidad persistente de operaciones", () => {
  beforeEach(() => localStorage.clear());
  it("reutiliza la identidad después de un resultado desconocido y renueva solo al confirmar", () => {
    localStorage.setItem("user", JSON.stringify({ id: 7 }));
    const id = pendingOperationId("SALE_NORMAL");
    expect(pendingOperationId("SALE_NORMAL")).toBe(id);
    completeOperation("SALE_NORMAL");
    expect(pendingOperationId("SALE_NORMAL")).not.toBe(id);
  });
  it("separa usuarios y dominios sin almacenar importes ni datos personales", () => {
    localStorage.setItem("user", JSON.stringify({ id: 7 }));
    const sale = pendingOperationId("SALE_NORMAL");
    expect(pendingOperationId("RETURN")).not.toBe(sale);
    localStorage.setItem("user", JSON.stringify({ id: 8 }));
    expect(pendingOperationId("SALE_NORMAL")).not.toBe(sale);
    expect(localStorage.getItem("repuestopro:pending:7:SALE_NORMAL")).toBe(sale);
  });
});
