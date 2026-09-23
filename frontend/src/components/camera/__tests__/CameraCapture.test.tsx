import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CameraCapture from "../CameraCapture";

const streamFalso = {
  getTracks: () => [{ stop: vi.fn(), kind: "video" }],
} as unknown as MediaStream;

function sinMediaDevices() {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: undefined,
  });
}

function mediaDenegada() {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: vi
        .fn()
        .mockRejectedValue(new DOMException("Permiso denegado", "NotAllowedError")),
    },
  });
}

function mediaExitosa() {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: vi.fn().mockResolvedValue(streamFalso),
    },
  });
}

function simularVideoListo() {
  Object.defineProperty(HTMLMediaElement.prototype, "play", {
    configurable: true,
    value: vi.fn().mockResolvedValue(undefined),
  });
  Object.defineProperty(HTMLMediaElement.prototype, "readyState", {
    configurable: true,
    value: 4,
  });
}

function simularCanvasyVideo() {
  Object.defineProperty(HTMLVideoElement.prototype, "videoWidth", {
    configurable: true,
    value: 640,
  });
  Object.defineProperty(HTMLVideoElement.prototype, "videoHeight", {
    configurable: true,
    value: 480,
  });
  Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
    configurable: true,
    value: () => ({ drawImage: vi.fn() }),
  });
  Object.defineProperty(HTMLCanvasElement.prototype, "toBlob", {
    configurable: true,
    value: (cb: (blob: Blob | null) => void) => {
      cb(new Blob(["imagen"], { type: "image/jpeg" }));
    },
  });
}

describe("CameraCapture", () => {
  const onCapture = vi.fn();
  const props = {
    onCapture,
    onClose: vi.fn(),
    captureLabel: "Capturar pieza",
  };

  beforeEach(() => {
    onCapture.mockClear();
    props.onClose.mockClear();

    // jsdom no implementa URL.createObjectURL: se polifillea para la preview.
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:mock-captura"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("muestra cámara no disponible cuando mediaDevices no existe", async () => {
    sinMediaDevices();
    render(<CameraCapture {...props} />);

    await waitFor(() => {
      expect(
        screen.getByText("La cámara no está disponible en este dispositivo")
      ).toBeInTheDocument();
    });
  });

  it("muestra permiso denegado con botón Reintentar", async () => {
    mediaDenegada();
    render(<CameraCapture {...props} />);

    await waitFor(() => {
      expect(screen.getByText("No se pudo acceder a la cámara")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /reintentar/i })).toBeInTheDocument();
  });

  it("captura, muestra la preview real y recién al pulsar Buscar entrega el archivo", async () => {
    mediaExitosa();
    simularVideoListo();
    simularCanvasyVideo();

    render(<CameraCapture {...props} />);

    const capturar = await screen.findByRole("button", { name: "Capturar pieza" });
    fireEvent.click(capturar);

    const preview = await screen.findByTestId("vision-captura-preview");
    expect(preview).toBeInTheDocument();
    expect(screen.getByText("Resolución: 640 × 480")).toBeInTheDocument();
    expect(onCapture).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Marca del vehículo"), { target: { value: "Toyota" } });
    fireEvent.click(screen.getByRole("button", { name: /buscar/i }));

    await waitFor(() => {
      expect(onCapture).toHaveBeenCalledTimes(1);
    });
    const archivo = onCapture.mock.calls[0][0] as File;
    expect(archivo).toBeInstanceOf(File);
    expect(archivo.type).toBe("image/jpeg");
    expect(onCapture.mock.calls[0][1]).toEqual({ marca: "Toyota", modelo: undefined, anio: undefined });
  });

  it("repite la foto y vuelve a la cámara sin entregar el archivo", async () => {
    mediaExitosa();
    simularVideoListo();
    simularCanvasyVideo();

    render(<CameraCapture {...props} />);

    const capturar = await screen.findByRole("button", { name: "Capturar pieza" });
    fireEvent.click(capturar);

    const repetir = await screen.findByRole("button", { name: /repetir foto/i });
    fireEvent.click(repetir);

    expect(screen.queryByTestId("vision-captura-preview")).not.toBeInTheDocument();
    expect(onCapture).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Capturar pieza" })).toBeInTheDocument();
  });

  it("cierra la cámara al pulsar el botón de cierre", async () => {
    mediaDenegada();
    render(<CameraCapture {...props} />);

    const cerrar = await screen.findByLabelText("Cerrar cámara");
    fireEvent.click(cerrar);

    await waitFor(() => {
      expect(props.onClose).toHaveBeenCalled();
    });
  });
});
