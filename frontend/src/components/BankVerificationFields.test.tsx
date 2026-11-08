import { beforeEach, describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import BankVerificationFields from "./BankVerificationFields";
vi.mock("../services/api", () => ({ default: { get: vi.fn().mockResolvedValue({ data: { accounts: [{ id: 1, code: "CUENTA_01", name: "Cuenta empresa" }] } }), post: vi.fn() } }));
vi.mock("../stores/authStore", () => ({ useAuthStore: (select: any) => select({ user: { role: "TIENDA" } }) }));
describe("comprobación bancaria manual", () => {
  beforeEach(() => vi.clearAllMocks());
  it("explica la verificación y no permite al vendedor registrar cuentas", async () => {
    render(<BankVerificationFields onChange={vi.fn()} />);
    expect(await screen.findByRole("option", { name: /CUENTA_01/ })).toBeInTheDocument();
    expect(screen.getByText(/La aplicación no consulta al banco/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Registrar cuenta receptora" })).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox")).not.toBeChecked();
  });
  it("cambiar la referencia invalida una comprobación anterior", () => {
    const changed = vi.fn();
    render(<BankVerificationFields value={{ receivingAccountId: 1, reference: "ABC001", operationDate: "2026-11-03", confirmed: true }} onChange={changed} />);
    fireEvent.change(screen.getByLabelText("Referencia del abono"), { target: { value: "ABC002" } });
    expect(changed).toHaveBeenCalledWith({ receivingAccountId: 1, reference: "ABC002", operationDate: "2026-11-03", confirmed: false });
  });
});
