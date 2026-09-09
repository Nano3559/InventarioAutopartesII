import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import LoginPage from "../LoginPage";

const mockLoginFn = vi.fn().mockResolvedValue(undefined);

vi.mock("../../stores/authStore", () => ({
  useAuthStore: Object.assign(
    vi.fn(() => ({ login: mockLoginFn })),
    {
      getState: vi.fn(() => ({ login: mockLoginFn })),
    }
  ),
}));

vi.mock("../../services/api", () => ({
  default: {
    post: vi.fn(),
  },
}));

vi.mock("react-hot-toast", () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const apiMock = await import("../../services/api");
const toastMock = await import("react-hot-toast");

const mockedApiPost = apiMock.default.post as ReturnType<typeof vi.fn>;
const mockedToastSuccess = toastMock.default.success as ReturnType<typeof vi.fn>;
const mockedToastError = toastMock.default.error as ReturnType<typeof vi.fn>;

function renderLogin() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLoginFn.mockReset();
    mockLoginFn.mockResolvedValue(undefined);
  });

  it("renderiza campo de email", () => {
    renderLogin();
    expect(screen.getByPlaceholderText(/correo@ejemplo.com/i)).toBeInTheDocument();
  });

  it("renderiza campo de password", () => {
    renderLogin();
    expect(screen.getByPlaceholderText("••••••••")).toBeInTheDocument();
  });

  it("renderiza botón de ingresar", () => {
    renderLogin();
    expect(screen.getByRole("button", { name: /ingresar/i })).toBeInTheDocument();
  });

  it("renderiza formulario con campos requeridos", () => {
    renderLogin();
    const emailInput = screen.getByPlaceholderText(/correo@ejemplo.com/i);
    const passwordInput = screen.getByPlaceholderText("••••••••");
    expect(emailInput).toBeRequired();
    expect(passwordInput).toBeRequired();
  });

  it("permite escribir credenciales", async () => {
    const user = userEvent.setup();
    renderLogin();

    const emailInput = screen.getByPlaceholderText(/correo@ejemplo.com/i);
    const passwordInput = screen.getByPlaceholderText("••••••••");

    await user.type(emailInput, "test@test.com");
    await user.type(passwordInput, "password123");

    expect(emailInput).toHaveValue("test@test.com");
    expect(passwordInput).toHaveValue("password123");
  });

  it("submit llama a api.post con credenciales", async () => {
    const user = userEvent.setup();
    mockedApiPost.mockResolvedValue({
      data: { user: { name: "Test", role: "ADMIN" }, token: "tok" },
    });

    renderLogin();

    await user.type(screen.getByPlaceholderText(/correo@ejemplo.com/i), "a@b.com");
    await user.type(screen.getByPlaceholderText("••••••••"), "pass");
    await user.click(screen.getByRole("button", { name: /ingresar/i }));

    expect(mockedApiPost).toHaveBeenCalledWith("/auth/login", {
      email: "a@b.com",
      password: "pass",
    });
  });

  it("login exitoso llama a authStore.login", async () => {
    const user = userEvent.setup();
    const mockUser = { name: "Carlos", role: "ADMIN" };
    mockedApiPost.mockResolvedValue({
      data: { user: mockUser, token: "tok123" },
    });

    renderLogin();

    await user.type(screen.getByPlaceholderText(/correo@ejemplo.com/i), "a@b.com");
    await user.type(screen.getByPlaceholderText("••••••••"), "pass");
    await user.click(screen.getByRole("button", { name: /ingresar/i }));

    await waitFor(() => {
      expect(mockLoginFn).toHaveBeenCalledWith(mockUser, "tok123");
    });
  });

  it("login exitoso muestra toast de éxito", async () => {
    const user = userEvent.setup();
    mockedApiPost.mockResolvedValue({
      data: { user: { name: "Carlos" }, token: "tok" },
    });

    renderLogin();

    await user.type(screen.getByPlaceholderText(/correo@ejemplo.com/i), "a@b.com");
    await user.type(screen.getByPlaceholderText("••••••••"), "pass");
    await user.click(screen.getByRole("button", { name: /ingresar/i }));

    await waitFor(() => {
      expect(mockedToastSuccess).toHaveBeenCalledWith("Bienvenido, Carlos");
    });
  });

  it("login fallido muestra toast de error", async () => {
    const user = userEvent.setup();
    mockedApiPost.mockRejectedValue({
      response: { data: { message: "Credenciales inválidas" } },
    });

    renderLogin();

    await user.type(screen.getByPlaceholderText(/correo@ejemplo.com/i), "a@b.com");
    await user.type(screen.getByPlaceholderText("••••••••"), "wrong");
    await user.click(screen.getByRole("button", { name: /ingresar/i }));

    await waitFor(() => {
      expect(mockedToastError).toHaveBeenCalledWith("Credenciales inválidas");
    });
  });

  it("login fallido sin message muestra error genérico", async () => {
    const user = userEvent.setup();
    mockedApiPost.mockRejectedValue({ response: { data: {} } });

    renderLogin();

    await user.type(screen.getByPlaceholderText(/correo@ejemplo.com/i), "a@b.com");
    await user.type(screen.getByPlaceholderText("••••••••"), "wrong");
    await user.click(screen.getByRole("button", { name: /ingresar/i }));

    await waitFor(() => {
      expect(mockedToastError).toHaveBeenCalledWith("Error al iniciar sesión");
    });
  });

  it("botón se deshabilita durante loading", async () => {
    const user = userEvent.setup();
    let resolveLogin!: () => void;
    const loginPromise = new Promise<void>((r) => {
      resolveLogin = r;
    });
    mockLoginFn.mockReturnValue(loginPromise);
    mockedApiPost.mockResolvedValue({
      data: { user: { name: "Test" }, token: "tok" },
    });

    renderLogin();

    await user.type(screen.getByPlaceholderText(/correo@ejemplo.com/i), "a@b.com");
    await user.type(screen.getByPlaceholderText("••••••••"), "pass");
    await user.click(screen.getByRole("button", { name: /ingresar/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /ingresando/i })).toBeDisabled();
    });

    resolveLogin();
  });

  it("toggle show/hide password funciona", async () => {
    const user = userEvent.setup();
    renderLogin();

    const passwordInput = screen.getByPlaceholderText("••••••••");
    expect(passwordInput).toHaveAttribute("type", "password");

    const toggleButton = screen.getByRole("button", { name: "" });
    await user.click(toggleButton);

    expect(passwordInput).toHaveAttribute("type", "text");
  });
});
