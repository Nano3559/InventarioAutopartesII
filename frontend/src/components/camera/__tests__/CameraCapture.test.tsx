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

  it("captura la imagen y entrega un archivo a onCapture", async () => {
    mediaExitosa();
    simularVideoListo();
    simularCanvasyVideo();

    render(<CameraCapture {...props} />);

    const capturar = await screen.findByRole("button", { name: "Capturar pieza" });
    fireEvent.click(capturar);

    await waitFor(() => {
      expect(onCapture).toHaveBeenCalled();
    });
    const archivo = onCapture.mock.calls[0][0] as File;
    expect(archivo).toBeInstanceOf(File);
    expect(archivo.type).toBe("image/jpeg");
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
