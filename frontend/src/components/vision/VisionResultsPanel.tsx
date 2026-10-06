import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Loader2, Camera, RefreshCw, X, PackageSearch, Truck, ShoppingCart, Check, ScanLine, AlertCircle, AlertTriangle } from "lucide-react";
import ProductImage from "../public/ProductImage";
import { VisionAnalysis, VisionCandidatoPublico, VisionEvidenciaCodigo } from "../../types/vision";
import { BorradorVentaVision } from "../../services/saleDraft";
import { ReporteCalidad } from "../../services/imageQuality";
import { VerificacionMultiVista, debeOfrecerSegundaFoto } from "../../services/multiView";
import DetectionBox from "./DetectionBox";
import QualityBadge from "./QualityBadge";
import ExplainCard from "./ExplainCard";
import PipelineStrip from "./PipelineStrip";
import MultiVistaPanel from "./MultiVistaPanel";
import DisponibilidadSucursales from "./DisponibilidadSucursales";

export interface VisionVehiculoForm {
  marca: string;
  modelo: string;
  anio: string;
}

export interface VisionEntregaSeleccion {
  modalidad: "recoger" | "delivery";
  sucursalId: number | null;
}

interface VisionResultsPanelProps {
  nombreFoto?: string;
  /** URL de la foto capturada, para dibujar el bounding box sobre la imagen real. */
  vistaPreviaUrl?: string | null;
  resultado: VisionAnalysis | null;
  loading: boolean;
  error: string | null;
  /** Recomendaciones de captura del 422, si el backend las envió. */
  recomendaciones?: string[];
  /** Medición de calidad de la foto antes de enviarla al modelo. */
  calidad?: ReporteCalidad | null;
  /** true cuando la foto es "mala" y hay que advertir antes de gastar la inferencia. */
  advertirCalidad?: boolean;
  onContinuarDeTodosModos?: () => void;
  onDescartarPorCalidad?: () => void;
  /** Veredicto multi-vista; null si el usuario no tomó una segunda foto. */
  verificacion?: VerificacionMultiVista | null;
  /** Dispara la captura de la segunda foto para confirmar la categoría. */
  onConfirmarConSegundaFoto?: () => void;
  vehiculo: VisionVehiculoForm;
  onVehiculoChange: (campo: keyof VisionVehiculoForm, valor: string) => void;
  onBuscar: () => void;
  onRepetirFoto: () => void;
  onCerrar: () => void;
  entrega: VisionEntregaSeleccion;
  onCambiarEntrega: (seleccion: VisionEntregaSeleccion) => void;
  onLlevarAVenta: (borrador: BorradorVentaVision) => void;
}

/** Etiqueta legible del campo de código; el backend manda el nombre crudo. */
const ETIQUETA_CAMPO: Record<VisionEvidenciaCodigo["campo"], string> = {
  oemCode: "Código OEM",
  factoryCode: "Código de fábrica",
  itemCode: "Código de item",
};

const disponibilidadClases = (nivel: string) => {
  if (nivel === "DISPONIBLE") return "text-green-400 bg-green-500/10 border-green-500/20";
  if (nivel === "POCAS_UNIDADES") return "text-yellow-400 bg-yellow-500/10 border-yellow-500/20";
  return "text-gray-400 bg-gray-500/10 border-gray-500/20";
};

/**
 * Nombre legible del proveedor que informa el contrato, sin inventarlo en la UI.
 *
 * El backend siempre consulta el modelo real (`ia-service` + YOLO), así que no
 * existe una etiqueta de simulación: cualquier valor distinto de `http` se
 * muestra tal cual para no ocultarlo si el contrato cambiara.
 */
const ETIQUETA_PROVEEDOR: Record<string, string> = {
  http: "ia-service (modelo real)",
};

const etiquetaProveedor = (proveedor: string) => ETIQUETA_PROVEEDOR[proveedor] ?? `Proveedor: ${proveedor}`;

const capitalizar = (texto: string) => (texto.trim().charAt(0).toUpperCase() + texto.trim().slice(1)) || texto;

/** Nombre legible de la pieza detectada: la etiqueta de clase es la identificación. */
const tituloPieza = (r: VisionAnalysis) => capitalizar(r.deteccion.categoria ?? r.deteccion.categoriaMapeada ?? "Pieza");

/** El vehículo estuvo presente solo si el backend recibió al menos un campo. */
const hayVehiculoEn = (r: VisionAnalysis | null) =>
  !!r?.compatibilidad.vehiculo &&
  [r.compatibilidad.vehiculo.marca, r.compatibilidad.vehiculo.modelo, r.compatibilidad.vehiculo.anio].some(Boolean);

/** `marca + modelo + año` completos, como pide la UX de compatibilidad. */
const tieneVehiculoCompleto = (v: VisionVehiculoForm) =>
  v.marca.trim() !== "" && v.modelo.trim() !== "" && v.anio.trim() !== "";

/** Producto → "Bosch Corolla · 2018" (vehículo o rango que declara el catálogo). */
const rangoProducto = (p: VisionCandidatoPublico) => {
  const partes = [p.brand, p.model].filter(Boolean).join(" ");
  if (partes && p.year) return `${partes} · ${p.year}`;
  return partes || p.year || "—";
};

/** Etiqueta del estado de calidad; jamás "n/d". Si no hay medición, "No disponible". */
function etiquetaCalidad(calidad: ReporteCalidad | null): string {
  if (!calidad) return "No disponible";
  return calidad.estado === "buena" ? "Buena" : calidad.estado === "regular" ? "Regular" : "Mala";
}

/**
 * Chip de coincidencia del motor de catálogo. Jamás se llama "Confianza IA":
 * esa es de YOLO. El score numérico (si lo hay) vive en el tooltip de la defensa.
 */
function chipCoincidencia(p: VisionCandidatoPublico) {
  const score = p.scoreEvidencia ?? 0;
  if (score > 0) {
    return {
      estilo: "text-indigo-300 bg-indigo-500/10 border-indigo-500/20",
      texto: "Coincidencia por código",
      titulo: `Coincidencia de código (score ${score}). Este score corresponde al motor de búsqueda del catálogo. No es la confianza del modelo de IA.`,
      esScore: true,
    };
  }
  if (p.claseCoincide) {
    return {
      estilo: "text-cyan-300 bg-cyan-500/10 border-cyan-500/20",
      texto: "Coincidencia por tipo de pieza",
      titulo: "El nombre de este producto corresponde a la pieza detectada en la foto.",
      esScore: false,
    };
  }
  return {
    estilo: "text-gray-400 bg-gray-500/10 border-gray-500/20",
    texto: "Coincidencia por categoría",
    titulo: "El único vínculo de este producto con la foto es compartir categoría.",
    esScore: false,
  };
}

/**
 * Chip de compatibilidad honesto:
 *   - verificada:          "✓ Compatible"
 *   - no verificada (con vehículo en la búsqueda): "⚠ No verificada"
 *   - sin vehículo:        "Vehículo no indicado" (discreto; el CTA es global)
 */
function chipCompatibilidad(p: VisionCandidatoPublico, haVehiculo: boolean) {
  if (p.compatibilidad.verificada) {
    return { texto: "✓ Compatible", cls: "text-green-400 bg-green-500/10 border-green-500/20" };
  }
  return haVehiculo
    ? { texto: "⚠ No verificada", cls: "text-amber-400 bg-amber-500/10 border-amber-500/20" }
    : { texto: "Vehículo no indicado", cls: "text-gray-400 bg-gray-500/10 border-gray-500/20" };
}

export default function VisionResultsPanel({
  nombreFoto,
  vistaPreviaUrl,
  resultado,
  loading,
  error,
  recomendaciones = [],
  calidad = null,
  advertirCalidad = false,
  onContinuarDeTodosModos,
  onDescartarPorCalidad,
  verificacion = null,
  onConfirmarConSegundaFoto,
  vehiculo,
  onVehiculoChange,
  onBuscar,
  onRepetirFoto,
  onCerrar,
  entrega,
  onCambiarEntrega,
  onLlevarAVenta,
}: VisionResultsPanelProps) {
  const confianza = resultado ? Math.round(resultado.deteccion.confianza * 100) : 0;
  const codigosDetectados = resultado?.deteccion.codigosDetectados ?? [];
  const textoDetectado = resultado?.deteccion.textoDetectado ?? [];
  const candidatosConEvidencia = resultado?.candidatos.filter((c) => (c.evidencias?.length ?? 0) > 0).length ?? 0;
  const ofreceSegundaFoto = resultado ? debeOfrecerSegundaFoto(resultado.deteccion) : false;
  const hayDobleVista = !!verificacion && verificacion.vistas.length > 1;
  const hayVehiculo = hayVehiculoEn(resultado);
  const piezaTitulo = resultado ? tituloPieza(resultado) : "";
  const categoriaPieza = resultado
    ? (resultado.categoriaCatalogo?.nombre ?? resultado.deteccion.categoriaMapeada ?? resultado.deteccion.categoria ?? "Sin clasificar")
    : "";
  const vehiculoConsulta = resultado?.compatibilidad.vehiculo
    ? [resultado.compatibilidad.vehiculo.marca, resultado.compatibilidad.vehiculo.modelo, resultado.compatibilidad.vehiculo.anio]
        .filter(Boolean)
        .join(" ")
    : "";

  // Selección de producto con stock suficiente para preparar la venta (WB-8).
  const [seleccionado, setSeleccionado] = useState<number | null>(null);
  const [cantidad, setCantidad] = useState(1);
  const [lugarEntrega, setLugarEntrega] = useState("");
  const [paraQuien, setParaQuien] = useState("");
  // Mostrar todos los resultados o solo los 3 primeros.
  const [verTodos, setVerTodos] = useState(false);

  useEffect(() => {
    setSeleccionado(null);
    setCantidad(1);
    setLugarEntrega("");
    setParaQuien("");
    setVerTodos(false);
  }, [resultado?.consultadoEn]);

  const candidatoSeleccionado = resultado?.candidatos.find((c) => c.id === seleccionado) ?? null;
  const candidatosVisibles = resultado ? (verTodos ? resultado.candidatos : resultado.candidatos.slice(0, 3)) : [];
  // Solo las sucursales con disponibilidad real son seleccionables para recoger.
  const sucursalesDisponibles = candidatoSeleccionado
    ? (candidatoSeleccionado.disponibilidadPorSucursalPublica ?? []).filter((s) => s.nivel !== "NO_DISPONIBLE")
    : [];
  const puedePrepararVenta =
    candidatoSeleccionado !== null &&
    (entrega.modalidad !== "recoger" || sucursalesDisponibles.length > 0);

  const seleccionarProducto = (candidatoId: number) => {
    setSeleccionado(candidatoId);
    setCantidad(1);
    const disponibles = (
      resultado?.candidatos.find((c) => c.id === candidatoId)?.disponibilidadPorSucursalPublica ?? []
    ).filter((s) => s.nivel !== "NO_DISPONIBLE");
    if (disponibles.length > 0 && !disponibles.some((s) => s.sucursalId === entrega.sucursalId)) {
      onCambiarEntrega({ ...entrega, sucursalId: disponibles[0].sucursalId });
    }
  };

  const prepararVenta = () => {
    const candidato = candidatoSeleccionado;
    if (!candidato) return;
    if (entrega.modalidad === "recoger" && sucursalesDisponibles.length === 0) return;

    const sucursal = entrega.modalidad === "recoger"
      ? (sucursalesDisponibles.find((s) => s.sucursalId === entrega.sucursalId) ?? sucursalesDisponibles[0])
      : null;

    const borrador: BorradorVentaVision = {
      origen: "vision",
      creadoEn: new Date().toISOString(),
      producto: { itemCode: candidato.itemCode, nombre: candidato.name, cantidad },
      entrega: sucursal
        ? { modalidad: "recoger", sucursalId: sucursal.sucursalId, sucursalNombre: sucursal.nombre }
        : {
            modalidad: "delivery",
            sucursalId: null,
            sucursalNombre: "",
            lugarEntrega: lugarEntrega.trim(),
            paraQuien: paraQuien.trim(),
          },
    };
    onLlevarAVenta(borrador);
  };

  const vehiculoCompleto = tieneVehiculoCompleto(vehiculo);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-dark-950/90 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-6xl bg-dark-900 border border-white/[0.08] rounded-2xl overflow-hidden shadow-2xl my-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06] sticky top-0 bg-dark-900 z-10">
          <div className="flex items-center gap-2 text-white font-semibold">
            <PackageSearch size={18} className="text-primary-400" />
            Búsqueda por cámara
          </div>
          <button onClick={onCerrar} className="p-2 text-gray-400 hover:text-white rounded-lg transition-colors" type="button" aria-label="Cerrar resultados">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 max-h-[calc(100vh-8.5rem)] overflow-y-auto space-y-4">
          {nombreFoto && (
            <p className="text-xs text-gray-500">
              Foto capturada: <span className="text-gray-400">{nombreFoto}</span>
            </p>
          )}

          {/* Advertencia previa a la inferencia: se ve cuando la foto es claramente
              mala. NO bloquea: siempre existe el botón para buscar igual. */}
          {advertirCalidad && calidad && (
            <section
              className="rounded-xl border border-red-500/30 bg-red-500/10 p-4"
              data-testid="vision-aviso-calidad"
              role="alert"
            >
              <div className="flex items-start gap-2.5">
                <AlertTriangle size={18} className="text-red-400 shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-red-300">La fotografía puede afectar el reconocimiento.</p>
                  <details className="mt-2">
                    <summary className="cursor-pointer select-none text-[11px] font-semibold text-red-200/80">
                      Ver recomendaciones
                    </summary>
                    <ul className="mt-2 space-y-1 text-xs text-red-200/80">
                      {calidad.problemas.map((p) => (
                        <li key={p} className="flex gap-1.5">
                          <span aria-hidden="true">•</span>
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                    {calidad.recomendaciones.length > 0 && (
                      <div className="mt-2.5">
                        <p className="text-[11px] font-semibold text-red-200/70 uppercase tracking-wider">Qué hacer</p>
                        <ul className="mt-1 space-y-1 text-xs text-red-100/80">
                          {calidad.recomendaciones.map((r) => (
                            <li key={r} className="flex gap-1.5">
                              <span aria-hidden="true">›</span>
                              <span>{r}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    <p className="mt-2.5 text-[11px] text-red-100/60">
                      Igual puedes buscar: la calidad es un consejo, no un requisito.
                    </p>
                  </details>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={onContinuarDeTodosModos}
                  className="inline-flex items-center gap-2 bg-red-500 hover:bg-red-400 text-dark-950 px-4 py-2 rounded-lg text-xs font-semibold transition-colors"
                >
                  Buscar de todos modos
                </button>
                <button
                  type="button"
                  onClick={onDescartarPorCalidad}
                  className="inline-flex items-center gap-2 text-red-200 hover:text-white border border-red-500/40 px-4 py-2 rounded-lg text-xs font-semibold transition-colors"
                >
                  <Camera size={13} /> Tomar otra foto
                </button>
              </div>
            </section>
          )}

          {error && (
            <div className="flex items-start justify-between gap-3 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
              <div className="min-w-0">
                <p className="text-red-300 text-sm">{error}</p>
                {recomendaciones.length > 0 && (
                  <div className="mt-2.5" data-testid="vision-recomendaciones">
                    <p className="text-[11px] font-semibold text-red-200/80 flex items-center gap-1.5">
                      <AlertCircle size={12} /> Para mejorar la foto:
                    </p>
                    <ul className="mt-1.5 space-y-1">
                      {recomendaciones.map((recomendacion) => (
                        <li key={recomendacion} className="text-xs text-red-200/80 flex gap-1.5">
                          <span aria-hidden="true">·</span>
                          <span>{recomendacion}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
              <button onClick={onRepetirFoto} className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-500/20 text-red-200 text-xs rounded-lg hover:bg-red-500/30" type="button">
                <Camera size={13} /> Otra foto
              </button>
            </div>
          )}

          {loading && (
            <div className="flex flex-col items-center justify-center gap-3 py-10">
              <Loader2 size={28} className="animate-spin text-primary-400" />
              <p className="text-gray-400 text-sm">Analizando imagen...</p>
            </div>
          )}

          {!loading && !error && resultado && (
            <>
              {/* Jerarquía principal en dos columnas (desktop): izquierda la foto
                  con el bounding box; derecha la identificación. En mobile se
                  apilan (identificación primero). */}
              <div className={vistaPreviaUrl ? "grid gap-4 lg:grid-cols-[minmax(0,42%)_1fr] items-start" : "grid gap-4"}>
                {vistaPreviaUrl && (
                  <div className="order-2 lg:order-1 space-y-3">
                    <DetectionBox
                      src={vistaPreviaUrl}
                      alt={`Foto analizada: ${resultado.deteccion.categoria}`}
                      boundingBox={resultado.deteccion.boundingBox}
                      categoria={resultado.deteccion.categoria}
                      confianza={resultado.deteccion.confianza}
                    />
                  </div>
                )}

                <div className="order-1 lg:order-2 space-y-3 min-w-0">
                  {/* Identificación: dato duro de la pieza detectada, sin inventar nada. */}
                  <section
                    className="rounded-2xl border border-primary-500/20 bg-gradient-to-br from-primary-500/10 via-transparent to-transparent p-4"
                    aria-label="Pieza identificada"
                    data-testid="vision-pieza"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary-400">Pieza identificada</p>
                      {verificacion && (
                        <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md border text-gray-300 bg-white/[0.04] border-white/[0.08]">
                          {verificacion.etiqueta}
                        </span>
                      )}
                    </div>
                    <h2 className="mt-1 text-xl font-bold text-white">{piezaTitulo}</h2>

                    <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs">
                      <div className="flex items-center justify-between gap-2 rounded-lg bg-white/[0.03] border border-white/[0.04] px-2.5 py-2">
                        <dt className="text-gray-400">Confianza del modelo</dt>
                        <dd className="font-mono font-semibold text-white" data-testid="vision-confianza-modelo">
                          {confianza}%
                        </dd>
                      </div>
                      <div className="flex items-center justify-between gap-2 rounded-lg bg-white/[0.03] border border-white/[0.04] px-2.5 py-2">
                        <dt className="text-gray-400">Categoría</dt>
                        <dd className="font-semibold text-white truncate">{categoriaPieza}</dd>
                      </div>
                      <div className="flex items-center justify-between gap-2 rounded-lg bg-white/[0.03] border border-white/[0.04] px-2.5 py-2">
                        <dt className="text-gray-400">Proveedor</dt>
                        <dd className="font-semibold text-white truncate">{etiquetaProveedor(resultado.proveedor)}</dd>
                      </div>
                      <div className="flex items-center justify-between gap-2 rounded-lg bg-white/[0.03] border border-white/[0.04] px-2.5 py-2">
                        <dt className="text-gray-400">OCR</dt>
                        <dd className="font-mono font-semibold text-cyan-300" data-testid="vision-hero-ocr">
                          {codigosDetectados.length ? `${codigosDetectados.length} código(s)` : "sin códigos"}
                        </dd>
                      </div>
                      <div className="flex items-center justify-between gap-2 rounded-lg bg-white/[0.03] border border-white/[0.04] px-2.5 py-2">
                        <dt className="text-gray-400">Calidad</dt>
                        <dd className="font-semibold text-white" data-testid="vision-hero-calidad">
                          {etiquetaCalidad(calidad)}
                        </dd>
                      </div>
                      {vehiculoConsulta && (
                        <div className="flex items-center justify-between gap-2 rounded-lg bg-white/[0.03] border border-white/[0.04] px-2.5 py-2">
                          <dt className="text-gray-400">Vehículo</dt>
                          <dd className="font-semibold text-white truncate">{vehiculoConsulta}</dd>
                        </div>
                      )}
                    </dl>
                  </section>

                  <QualityBadge calidad={calidad} onRepetirFoto={onRepetirFoto} onBuscarIgualmente={onBuscar} />

                  {/* Veredicto multi-vista y oferta de la segunda foto. */}
                  <MultiVistaPanel
                    verificacion={verificacion}
                    ofrece={ofreceSegundaFoto && !hayDobleVista}
                    onConfirmar={onConfirmarConSegundaFoto}
                  />

                  {/* OCR compacto: el recuento es primario, los códigos se abren. */}
                  {(codigosDetectados.length > 0 || textoDetectado.length > 0) && (
                    <details className="group rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-2.5" data-testid="vision-ocr-evidencia">
                      <summary className="cursor-pointer select-none flex items-center gap-2 text-xs font-semibold text-gray-300 hover:text-white">
                        <ScanLine size={13} className="text-cyan-400" />
                        OCR · {codigosDetectados.length > 0 ? `${codigosDetectados.length} código(s) detectado(s)` : "texto leído"}
                        <span className="ml-auto text-[11px] font-medium text-gray-500 group-open:hidden">Ver códigos</span>
                        <span className="ml-auto text-[11px] font-medium text-gray-500 hidden group-open:inline">Ocultar</span>
                      </summary>
                      <div className="mt-2.5 space-y-2">
                        {codigosDetectados.length > 0 && (
                          <div className="flex flex-wrap gap-1.5" data-testid="vision-codigos">
                            {codigosDetectados.map((codigo) => (
                              <span key={codigo} className="text-[11px] font-mono px-2 py-0.5 rounded-md border text-cyan-300 bg-cyan-500/10 border-cyan-500/20">
                                {codigo}
                              </span>
                            ))}
                          </div>
                        )}
                        {textoDetectado.length > 0 && (
                          <p className="text-[11px] text-gray-500 leading-relaxed">{textoDetectado.join(" · ")}</p>
                        )}
                        <p className="text-[11px] text-gray-600">
                          El código ayuda a identificar la pieza; no confirma por sí solo que sea compatible con tu vehículo.
                        </p>
                      </div>
                    </details>
                  )}
                </div>
              </div>

              {/* Vehículo como bloque propio, debajo del resultado principal. */}
              <section className="rounded-2xl border border-white/[0.06] bg-dark-800/30 p-4" data-testid="vision-vehiculo-block">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-primary-400">¿Para qué vehículo lo buscas?</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_110px_auto]">
                  <input
                    value={vehiculo.marca}
                    onChange={(e) => onVehiculoChange("marca", e.target.value)}
                    placeholder="Marca"
                    aria-label="Marca del vehículo"
                    className="px-3 py-2.5 bg-dark-900/50 border border-white/[0.06] rounded-xl text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-primary-500 outline-none"
                  />
                  <input
                    value={vehiculo.modelo}
                    onChange={(e) => onVehiculoChange("modelo", e.target.value)}
                    placeholder="Modelo"
                    aria-label="Modelo del vehículo"
                    className="px-3 py-2.5 bg-dark-900/50 border border-white/[0.06] rounded-xl text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-primary-500 outline-none"
                  />
                  <input
                    value={vehiculo.anio}
                    onChange={(e) => onVehiculoChange("anio", e.target.value)}
                    placeholder="Año"
                    aria-label="Año del vehículo"
                    className="px-3 py-2.5 bg-dark-900/50 border border-white/[0.06] rounded-xl text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-primary-500 outline-none w-full"
                  />
                  <button
                    onClick={onBuscar}
                    disabled={loading || !vehiculoCompleto}
                    className="inline-flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-500 text-white px-5 py-2.5 rounded-xl text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    type="button"
                  >
                    {loading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                    {loading ? "Buscando..." : "Verificar compatibilidad"}
                  </button>
                </div>
                {!vehiculoCompleto && (
                  <p className="mt-2 text-xs text-gray-500 leading-relaxed" data-testid="vision-vehiculo-ayuda">
                    La foto identifica la pieza sin depender del vehículo, pero la compatibilidad solo se confirma si indicás marca, modelo y año.
                  </p>
                )}
              </section>

              {resultado.candidatos.length === 0 ? (
                <div className="text-center py-10 bg-dark-800/30 border border-white/[0.06] rounded-2xl">
                  <PackageSearch size={40} className="text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-300 text-sm">{resultado.nota || "No se encontraron productos para la pieza detectada."}</p>
                </div>
              ) : (
                <>
                  <section aria-label="Mejores coincidencias">
                    <div className="flex flex-wrap items-end justify-between gap-2">
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">Mejores coincidencias</h3>
                      <div className="text-xs text-gray-500" data-testid="vision-resumen-compatibilidad">
                        {hayVehiculo ? (
                          <p>
                            {`${resultado.compatibilidad.verificadas} de ${resultado.candidatos.length} candidatos verifican compatibilidad con ${[resultado.compatibilidad.vehiculo!.marca, resultado.compatibilidad.vehiculo!.modelo, resultado.compatibilidad.vehiculo!.anio].filter(Boolean).join(" ")}.`}
                          </p>
                        ) : (
                          <p>{`Agrega tu vehículo para verificar compatibilidad.`}</p>
                        )}
                      </div>
                    </div>
                    {resultado.compatibilidad.nota ? <p className="mt-1 text-xs italic text-gray-600">{resultado.compatibilidad.nota}</p> : null}
                    {candidatosConEvidencia > 0 && (
                      <p className="mt-1 text-[11px] text-gray-600" data-testid="vision-ranking-nota">
                        El orden prioriza la compatibilidad verificada con tu vehículo; luego la coincidencia exacta de código (OEM &gt; fábrica &gt; item), luego el tipo de pieza. El resto aparece solo por compartir categoría.
                      </p>
                    )}

                    <div className="grid gap-3 mt-3">
                      {candidatosVisibles.map((producto, index) => {
                        const coincidencia = chipCoincidencia(producto);
                        const compat = chipCompatibilidad(producto, hayVehiculo);
                        const primera = index === 0;
                        return (
                          <div
                            key={producto.id}
                            data-testid={`candidato-${producto.itemCode}`}
                            className={`rounded-xl border p-3 transition-all ${
                              seleccionado === producto.id
                                ? "border-primary-500/40 ring-1 ring-primary-500/30"
                                : primera
                                  ? "border-primary-500/30 bg-primary-500/[0.04]"
                                  : "bg-dark-800/30 border-white/[0.06]"
                            }`}
                          >
                            <Link
                              to={`/productos/${producto.id}`}
                              className="group block"
                            >
                              <div className="flex gap-3">
                                <div className="shrink-0 w-20 h-20 bg-dark-900/50 rounded-lg overflow-hidden flex items-center justify-center">
                                  <ProductImage image={producto.image} category={producto.categoria} name={producto.name} />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <p className="text-sm font-semibold text-white line-clamp-2 group-hover:text-primary-300 transition-colors">{producto.name}</p>
                                    {primera && (
                                      <span
                                        className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border border-primary-400/40 bg-primary-500/15 text-primary-300"
                                        data-testid="vision-mejor-coincidencia"
                                      >
                                        Mejor coincidencia
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-xs text-gray-500 mt-0.5">{rangoProducto(producto)}</p>
                                  <p className="text-xs text-gray-500">Código: {producto.itemCode}</p>
                                  <div className="flex flex-wrap items-center gap-2 mt-2">
                                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border uppercase tracking-wider ${disponibilidadClases(producto.disponibilidad.nivel)}`}>
                                      {producto.disponibilidad.etiqueta}
                                    </span>
                                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border uppercase tracking-wider ${compat.cls}`} title={producto.compatibilidad.nota}>
                                      {compat.texto}
                                    </span>
                                    {(producto.evidencias?.length ?? 0) > 0 && (
                                      <span
                                        className="text-[10px] font-semibold px-2 py-0.5 rounded-md border uppercase tracking-wider text-cyan-300 bg-cyan-500/10 border-cyan-500/20"
                                        title={producto.evidencias!.map((e) => `${ETIQUETA_CAMPO[e.campo]}: ${e.codigoProducto} (${e.tipo})`).join(" · ")}
                                        data-testid={`evidencia-${producto.itemCode}`}
                                      >
                                        Código coincide
                                      </span>
                                    )}
                                    {/* Score de COINCIDENCIA (motor de catálogo: pesos OEM 10,
                                        fábrica 8, item 6). Jamás se llama "Confianza IA": esa es
                                        la de YOLO y aparece arriba. */}
                                    <span
                                      className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border uppercase tracking-wider ${coincidencia.estilo}`}
                                      title={coincidencia.titulo}
                                      data-testid={coincidencia.esScore ? `score-${producto.itemCode}` : `nivel-${producto.itemCode}`}
                                    >
                                      {coincidencia.texto}
                                    </span>
                                    <span className="text-amber-400 text-xs font-semibold ml-auto">Bs. {Number(producto.price1).toFixed(2)}</span>
                                  </div>
                                </div>
                              </div>
                            </Link>
                            <DisponibilidadSucursales
                              itemCode={producto.itemCode}
                              sucursales={producto.disponibilidadPorSucursalPublica ?? []}
                              esPrincipal={primera}
                            />
                            <ExplainCard candidato={producto} hayVehiculo={hayVehiculo} />
                            <div className="mt-2.5 flex justify-end">
                              {seleccionado === producto.id ? (
                                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-green-400 bg-green-500/10 border border-green-500/20 px-3 py-1.5 rounded-lg">
                                  <Check size={13} /> Seleccionado
                                </span>
                              ) : (
                                <button
                                  onClick={() => seleccionarProducto(producto.id)}
                                  type="button"
                                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary-300 hover:text-white bg-primary-500/10 hover:bg-primary-500/20 border border-primary-500/30 px-3 py-1.5 rounded-lg transition-all"
                                >
                                  <ShoppingCart size={13} /> Seleccionar para venta
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {resultado.candidatos.length > 3 && (
                      <button
                        type="button"
                        onClick={() => setVerTodos((v) => !v)}
                        data-testid="vision-ver-mas"
                        className="mt-3 w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-4 py-2.5 text-xs font-semibold text-gray-300 hover:text-white transition-colors"
                      >
                        {verTodos ? "Mostrar menos" : `Ver otros ${resultado.candidatos.length - 3} resultados`}
                      </button>
                    )}
                  </section>
                </>
              )}

              {/* Explicación técnica: colapsada por defecto, para la defensa. */}
              <details className="rounded-xl border border-white/[0.06] bg-white/[0.03] px-3 py-2.5" data-testid="vision-detalles-analisis">
                <summary className="cursor-pointer select-none text-xs font-semibold text-gray-300 hover:text-white">
                  Ver detalles del análisis
                </summary>
                <div className="mt-2.5">
                  <PipelineStrip analisis={resultado} deteccion={resultado.deteccion} calidad={calidad} verificacion={verificacion} />
                </div>
              </details>

              {candidatoSeleccionado && (
                <div className="bg-dark-800/30 border border-white/[0.06] rounded-xl p-4 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-gray-300 text-sm font-medium">
                      <ShoppingCart size={15} className="text-primary-400" />
                      ¿Cómo quieres recibirlo?
                    </div>
                    <p className="text-xs text-gray-500 truncate">{candidatoSeleccionado.name}</p>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3 items-end">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Modalidad</label>
                      <select
                        value={entrega.modalidad}
                        onChange={(e) => onCambiarEntrega({ ...entrega, modalidad: e.target.value as "recoger" | "delivery" })}
                        aria-label="Modalidad de entrega"
                        className="w-full px-3 py-2.5 bg-dark-900/50 border border-white/[0.06] rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                      >
                        <option value="recoger">Recoger en sucursal</option>
                        <option value="delivery">Delivery</option>
                      </select>
                    </div>
                    {entrega.modalidad === "recoger" && (
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Sucursal para recoger</label>
                        <select
                          value={entrega.sucursalId ?? ""}
                          onChange={(e) => onCambiarEntrega({ ...entrega, sucursalId: e.target.value ? Number(e.target.value) : null })}
                          aria-label="Sucursal de entrega"
                          className="w-full px-3 py-2.5 bg-dark-900/50 border border-white/[0.06] rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                        >
                          {sucursalesDisponibles.length > 0 ? (
                            sucursalesDisponibles.map((s) => (
                              <option key={s.sucursalId} value={s.sucursalId}>{s.nombre}</option>
                            ))
                          ) : (
                            <option value="" disabled>Sin sucursales disponibles</option>
                          )}
                        </select>
                        {sucursalesDisponibles.length === 0 && (
                          <p className="text-xs text-red-400 mt-1.5">Ese producto no está disponible para recoger en ninguna sucursal.</p>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3 items-end">
                    <div role="group" aria-label="Cantidad a preparar">
                      <label className="block text-xs text-gray-500 mb-1">Cantidad</label>
                      <div className="inline-flex items-center rounded-xl border border-white/[0.06] bg-dark-900/50 overflow-hidden">
                        <button
                          type="button"
                          onClick={() => setCantidad((c) => Math.max(1, c - 1))}
                          aria-label="Disminuir cantidad"
                          className="px-3 py-2.5 text-gray-300 hover:text-white transition-colors"
                        >
                          −
                        </button>
                        <span data-testid="vision-cantidad" className="w-10 text-center text-white text-sm font-semibold tabular-nums">
                          {cantidad}
                        </span>
                        <button
                          type="button"
                          onClick={() => setCantidad((c) => Math.min(99, c + 1))}
                          aria-label="Aumentar cantidad"
                          className="px-3 py-2.5 text-gray-300 hover:text-white transition-colors"
                        >
                          +
                        </button>
                      </div>
                    </div>
                    {entrega.modalidad === "delivery" && (
                      <div className="sm:col-span-1">
                        <div className="grid gap-3">
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">Lugar de entrega</label>
                            <input
                              type="text"
                              value={lugarEntrega}
                              onChange={(e) => setLugarEntrega(e.target.value)}
                              placeholder="Dirección o punto de entrega"
                              aria-label="Lugar de entrega"
                              className="w-full px-3 py-2.5 bg-dark-900/50 border border-white/[0.06] rounded-xl text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-primary-500 outline-none"
                            />
                          </div>
                          <div>
                            <label className="block text-xs text-gray-500 mb-1">Entregar a</label>
                            <input
                              type="text"
                              value={paraQuien}
                              onChange={(e) => setParaQuien(e.target.value)}
                              placeholder="Nombre de quien recibe"
                              aria-label="Entregar a"
                              className="w-full px-3 py-2.5 bg-dark-900/50 border border-white/[0.06] rounded-xl text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-primary-500 outline-none"
                            />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-xs text-gray-600 flex items-center gap-1.5">
                      <Truck size={13} />
                      {entrega.modalidad === "recoger"
                        ? "Seleccioná la sucursal para reservar la pieza (próximamente)."
                        : "El reparto coordina la entrega a tu dirección (próximamente)."}
                    </p>
                    <button
                      onClick={prepararVenta}
                      disabled={!puedePrepararVenta}
                      type="button"
                      className="inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all"
                    >
                      <Check size={15} /> Continuar con venta
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          {!loading && !error && !resultado && !advertirCalidad && (
            <div className="text-center py-10">
              <Camera size={36} className="text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">Tomá una foto de la pieza para buscarla en el catálogo.</p>
              <button onClick={onRepetirFoto} className="mt-4 inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-500 text-white px-5 py-2.5 rounded-xl text-sm font-semibold" type="button">
                <Camera size={16} /> Tomar foto
              </button>
            </div>
          )}

          {!loading && !error && resultado && (
            <div className="sticky bottom-0 -mx-5 mt-5 flex items-center justify-end gap-3 border-t border-white/[0.06] bg-dark-900/95 px-5 py-3 backdrop-blur">
              <div className="flex flex-wrap gap-3">
                <button onClick={onRepetirFoto} className="inline-flex items-center gap-2 text-gray-300 hover:text-white text-sm" type="button">
                  <Camera size={16} /> Tomar otra foto
                </button>
                <button onClick={onCerrar} className="inline-flex items-center gap-2 text-gray-300 hover:text-white text-sm" type="button">
                  <X size={16} /> Cerrar
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}