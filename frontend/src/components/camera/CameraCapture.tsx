import { useEffect, useRef, useState } from "react";
import { Camera, CameraOff, RefreshCw, X, AlertTriangle, ImageOff, Search } from "lucide-react";

type CameraStatus = "solicitando" | "capturando" | "denegado" | "no_disponible" | "error";

export interface CameraVehiculo {
  marca?: string;
  modelo?: string;
  anio?: string;
}

interface Captura {
  file: File;
  url: string;
  ancho: number;
  alto: number;
}

interface CameraCaptureProps {
  onCapture: (file: File, vehiculo?: CameraVehiculo) => void;
  onClose: () => void;
  captureLabel?: string;
}

export default function CameraCapture({ onCapture, onClose, captureLabel = "Tomar foto" }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const urlRef = useRef<string | null>(null);
  const [status, setStatus] = useState<CameraStatus>("solicitando");
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [captura, setCaptura] = useState<Captura | null>(null);
  const [marca, setMarca] = useState("");
  const [modelo, setModelo] = useState("");
  const [anio, setAnio] = useState("");

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
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
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
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      const url = URL.createObjectURL(file);
      urlRef.current = url;
      // El stream queda activo bajo la preview: "Repetir foto" vuelve a la cámara
      // sin volver a pedir permiso. Se detiene al cerrar o desmontar el modal.
      setCaptura({ file, url, ancho: canvas.width, alto: canvas.height });
    }, "image/jpeg", 0.85);
  };

  const buscar = () => {
    if (!captura) return;
    onCapture(captura.file, {
      marca: marca || undefined,
      modelo: modelo || undefined,
      anio: anio || undefined,
    });
  };

  const repetir = () => {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    urlRef.current = null;
    setCaptura(null);
    setMarca("");
    setModelo("");
    setAnio("");
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

          {captura && (
            <div className="absolute inset-0 bg-black">
              <img src={captura.url} alt="Captura de cámara" className="w-full h-full object-contain" data-testid="vision-captura-preview" />
              <span className="absolute bottom-2 right-2 px-2 py-1 bg-dark-950/80 border border-white/[0.06] text-gray-300 text-[11px] rounded-lg">
                Resolución: {captura.ancho} × {captura.alto}
              </span>
            </div>
          )}

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
          {captura ? (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-2">
                <input
                  value={marca}
                  onChange={(e) => setMarca(e.target.value)}
                  placeholder="Marca"
                  aria-label="Marca del vehículo"
                  className="px-3 py-2.5 bg-dark-800/60 border border-white/[0.06] rounded-xl text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-primary-500 outline-none w-full"
                />
                <input
                  value={modelo}
                  onChange={(e) => setModelo(e.target.value)}
                  placeholder="Modelo"
                  aria-label="Modelo del vehículo"
                  className="px-3 py-2.5 bg-dark-800/60 border border-white/[0.06] rounded-xl text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-primary-500 outline-none w-full"
                />
                <input
                  value={anio}
                  onChange={(e) => setAnio(e.target.value)}
                  placeholder="Año"
                  aria-label="Año del vehículo"
                  className="px-3 py-2.5 bg-dark-800/60 border border-white/[0.06] rounded-xl text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-primary-500 outline-none w-full"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={buscar}
                  className="flex-1 inline-flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-500 text-white px-4 py-3 rounded-xl text-sm font-semibold transition-all"
                  type="button"
                >
                  <Search size={16} /> Buscar
                </button>
                <button
                  onClick={repetir}
                  className="inline-flex items-center justify-center gap-2 px-4 py-3 bg-dark-800/60 border border-white/[0.06] text-gray-300 hover:text-white hover:border-white/[0.12] rounded-xl text-sm font-medium transition-all"
                  type="button"
                >
                  <RefreshCw size={16} /> Repetir foto
                </button>
              </div>
              <p className="text-gray-500 text-xs text-center">
                La foto se usa solo para la búsqueda; no se guarda en el servidor.
              </p>
            </div>
          ) : status === "capturando" ? (
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