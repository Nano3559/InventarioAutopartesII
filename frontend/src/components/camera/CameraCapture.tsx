import { useEffect, useRef, useState } from "react";
import { Camera, CameraOff, RefreshCw, X, AlertTriangle, ImageOff } from "lucide-react";

type CameraStatus = "solicitando" | "capturando" | "denegado" | "no_disponible" | "error";

interface CameraCaptureProps {
  onCapture: (file: File) => void;
  onClose: () => void;
  captureLabel?: string;
}

export default function CameraCapture({ onCapture, onClose, captureLabel = "Tomar foto" }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [status, setStatus] = useState<CameraStatus>("solicitando");
  const [mensaje, setMensaje] = useState<string | null>(null);

  const detenerStream = () => {
    const stream = streamRef.current;
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
  };

  const conectarStream = (stream: MediaStream) => {
    streamRef.current = stream;
    if (!videoRef.current) return;
    videoRef.current.srcObject = stream;
    const intentarPlay = () => {
      const play = videoRef.current?.play();
      if (play && typeof play.then === "function") {
        play.then(() => setStatus("capturando")).catch(() => setStatus("error"));
      } else {
        setStatus("capturando");
      }
    };
    if (videoRef.current.readyState >= 2) intentarPlay();
    else videoRef.current.onloadedmetadata = intentarPlay;
  };

  const arrancar = async () => {
    const media = navigator.mediaDevices;
    if (!media || typeof media.getUserMedia !== "function") {
      setStatus("no_disponible");
      return;
    }
    setStatus("solicitando");
    try {
      const stream = await media.getUserMedia({ video: { facingMode: "environment" }, audio: false });
      conectarStream(stream);
    } catch {
      setStatus("denegado");
    }
  };

  useEffect(() => {
    let cancelado = false;
    const media = navigator.mediaDevices;
    if (!media || typeof media.getUserMedia !== "function") {
      setStatus("no_disponible");
      return () => undefined;
    }
    media
      .getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then((stream) => {
        if (cancelado) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        conectarStream(stream);
      })
      .catch(() => {
        if (!cancelado) setStatus("denegado");
      });
    return () => {
      cancelado = true;
      detenerStream();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const capturar = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.videoWidth === 0 || video.videoHeight === 0) {
      setStatus("error");
      setMensaje("No se pudo capturar la imagen. Reintenta.");
      return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      setStatus("error");
      setMensaje("No se pudo procesar la captura.");
      return;
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!blob) {
        setStatus("error");
        setMensaje("No se pudo generar la imagen de la captura.");
        return;
      }
      const file = new File([blob], `captura-vision-${Date.now()}.jpg`, { type: "image/jpeg" });
      detenerStream();
      onCapture(file);
    }, "image/jpeg", 0.85);
  };

  const cerrar = () => {
    detenerStream();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-dark-950/90 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-lg bg-dark-900 border border-white/[0.08] rounded-2xl overflow-hidden shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2 text-white font-semibold">
            <Camera size={18} className="text-primary-400" />
            Buscar pieza por cámara
          </div>
          <button onClick={cerrar} className="p-2 text-gray-400 hover:text-white rounded-lg transition-colors" type="button" aria-label="Cerrar cámara">
            <X size={18} />
          </button>
        </div>

        <div className="relative aspect-square bg-black">
          <video ref={videoRef} muted playsInline className="w-full h-full object-contain" />

          {status !== "capturando" && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center">
              {status === "solicitando" && (
                <>
                  <div className="animate-spin h-8 w-8 border-2 border-primary-500 border-t-transparent rounded-full" />
                  <p className="text-gray-400 text-sm">Preparando cámara...</p>
                </>
              )}
              {status === "denegado" && (
                <>
                  <AlertTriangle size={32} className="text-red-400" />
                  <p className="text-gray-200 text-sm font-medium">No se pudo acceder a la cámara</p>
                  <p className="text-gray-500 text-xs">Asegúrate de permitir el acceso a la cámara en tu navegador.</p>
                  <div className="flex gap-2">
                    <button onClick={arrancar} className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white text-sm rounded-xl" type="button">
                      <RefreshCw size={14} /> Reintentar
                    </button>
                  </div>
                </>
              )}
              {status === "no_disponible" && (
                <>
                  <ImageOff size={32} className="text-gray-500" />
                  <p className="text-gray-200 text-sm font-medium">La cámara no está disponible en este dispositivo</p>
                  <p className="text-gray-500 text-xs">Tu navegador no permite la captura desde la cámara. Usa la búsqueda por imagen.</p>
                </>
              )}
              {status === "error" && (
                <>
                  <CameraOff size={32} className="text-red-400" />
                  <p className="text-gray-200 text-sm font-medium">{mensaje || "Ocurrió un error con la cámara"}</p>
                  <div className="flex gap-2">
                    <button onClick={arrancar} className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white text-sm rounded-xl" type="button">
                      <RefreshCw size={14} /> Reintentar
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        <canvas ref={canvasRef} className="hidden" aria-hidden="true" />

        <div className="p-5">
          {status === "capturando" ? (
            <div className="space-y-3">
              <button
                onClick={capturar}
                className="w-full inline-flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-500 text-white px-4 py-3 rounded-xl text-sm font-semibold transition-all"
                type="button"
              >
                <Camera size={16} /> {captureLabel}
              </button>
              <p className="text-gray-500 text-xs text-center">
                La foto se usa solo para la búsqueda; no se guarda en el servidor.
              </p>
            </div>
          ) : (
            <p className="text-gray-500 text-xs text-center">
              La foto se usa solo para la búsqueda; no se guarda en el servidor.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}