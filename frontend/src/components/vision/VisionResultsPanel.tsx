import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Loader2, Camera, RefreshCw, X, PackageSearch, Truck, Store, ShoppingCart, Check } from "lucide-react";
import ProductImage from "../public/ProductImage";
import { VisionAnalysis } from "../../types/vision";
import { BorradorVentaVision } from "../../services/saleDraft";

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
  resultado: VisionAnalysis | null;
  loading: boolean;
  error: string | null;
  vehiculo: VisionVehiculoForm;
  onVehiculoChange: (campo: keyof VisionVehiculoForm, valor: string) => void;
  onBuscar: () => void;
  onRepetirFoto: () => void;
  onCerrar: () => void;
  entrega: VisionEntregaSeleccion;
  onCambiarEntrega: (seleccion: VisionEntregaSeleccion) => void;
  onLlevarAVenta: (borrador: BorradorVentaVision) => void;
}

const disponibilidadClases = (nivel: string) => {
  if (nivel === "DISPONIBLE") return "text-green-400 bg-green-500/10 border-green-500/20";
  if (nivel === "POCAS_UNIDADES") return "text-yellow-400 bg-yellow-500/10 border-yellow-500/20";
  return "text-gray-400 bg-gray-500/10 border-gray-500/20";
};

export default function VisionResultsPanel({
  nombreFoto,
  resultado,
  loading,
  error,
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

  // Selección de producto con stock suficiente para preparar la venta (WB-8).
  const [seleccionado, setSeleccionado] = useState<number | null>(null);
  const [cantidad, setCantidad] = useState(1);
  const [lugarEntrega, setLugarEntrega] = useState("");
  const [paraQuien, setParaQuien] = useState("");

  useEffect(() => {
    setSeleccionado(null);
    setCantidad(1);
    setLugarEntrega("");
    setParaQuien("");
  }, [resultado?.consultadoEn]);

  const candidatoSeleccionado = resultado?.candidatos.find((c) => c.id === seleccionado) ?? null;
  const sucursalesConStock = candidatoSeleccionado
    ? candidatoSeleccionado.disponibilidadPorSucursal.filter((s) => s.nivel !== "NO_DISPONIBLE")
    : [];
  const puedePrepararVenta =
    candidatoSeleccionado !== null &&
    !(entrega.modalidad === "recoger" && sucursalesConStock.length === 0);

  const seleccionarProducto = (candidatoId: number) => {
    setSeleccionado(candidatoId);
    setCantidad(1);
    const disponibles = (
      resultado?.candidatos.find((c) => c.id === candidatoId)?.disponibilidadPorSucursal ?? []
    ).filter((s) => s.nivel !== "NO_DISPONIBLE");
    if (disponibles.length > 0 && !disponibles.some((s) => s.locationId === entrega.sucursalId)) {
      onCambiarEntrega({ ...entrega, sucursalId: disponibles[0].locationId });
    }
  };

  const prepararVenta = () => {
    const candidato = candidatoSeleccionado;
    if (!candidato) return;
    if (entrega.modalidad === "recoger" && sucursalesConStock.length === 0) return;

    const sucursal = entrega.modalidad === "recoger"
      ? (sucursalesConStock.find((s) => s.locationId === entrega.sucursalId) ?? sucursalesConStock[0])
      : null;

    const borrador: BorradorVentaVision = {
      origen: "vision",
      creadoEn: new Date().toISOString(),
      producto: { itemCode: candidato.itemCode, nombre: candidato.name, cantidad },
      entrega: sucursal
        ? { modalidad: "recoger", sucursalId: sucursal.locationId, sucursalNombre: sucursal.nombre }
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

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-dark-950/90 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-3xl bg-dark-900 border border-white/[0.08] rounded-2xl overflow-hidden shadow-2xl my-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06] sticky top-0 bg-dark-900 z-10">
          <div className="flex items-center gap-2 text-white font-semibold">
            <PackageSearch size={18} className="text-primary-400" />
            Búsqueda por cámara
          </div>
          <button onClick={onCerrar} className="p-2 text-gray-400 hover:text-white rounded-lg transition-colors" type="button" aria-label="Cerrar resultados">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 max-h-[calc(100vh-10rem)] overflow-y-auto space-y-4">
          {nombreFoto && (
            <p className="text-xs text-gray-500">
              Foto capturada: <span className="text-gray-400">{nombreFoto}</span>
            </p>
          )}

          <div className="grid sm:grid-cols-[auto_1fr] gap-3 items-start">
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                value={vehiculo.marca}
                onChange={(e) => onVehiculoChange("marca", e.target.value)}
                placeholder="Marca"
                aria-label="Marca del vehículo"
                className="px-3 py-2.5 bg-dark-800/60 border border-white/[0.06] rounded-xl text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-primary-500 outline-none"
              />
              <input
                value={vehiculo.modelo}
                onChange={(e) => onVehiculoChange("modelo", e.target.value)}
                placeholder="Modelo"
                aria-label="Modelo del vehículo"
                className="px-3 py-2.5 bg-dark-800/60 border border-white/[0.06] rounded-xl text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-primary-500 outline-none"
              />
              <input
                value={vehiculo.anio}
                onChange={(e) => onVehiculoChange("anio", e.target.value)}
                placeholder="Año"
                aria-label="Año del vehículo"
                className="px-3 py-2.5 bg-dark-800/60 border border-white/[0.06] rounded-xl text-white text-sm placeholder-gray-500 focus:ring-2 focus:ring-primary-500 outline-none w-24"
              />
            </div>
            <button
              onClick={onBuscar}
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-500 text-white px-5 py-2.5 rounded-xl text-sm font-semibold disabled:opacity-50"
              type="button"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
              {loading ? "Buscando..." : "Buscar"}
            </button>
          </div>

          {error && (
            <div className="flex items-start justify-between gap-3 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
              <p className="text-red-300 text-sm">{error}</p>
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
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md border uppercase tracking-wider text-primary-400 bg-primary-500/10 border-primary-500/20">
                  {resultado.deteccion.categoria}
                </span>
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md border uppercase tracking-wider text-gray-300 bg-gray-500/10 border-gray-500/20">
                  Confianza {confianza}%
                </span>
                {resultado.deteccion.categoriaMapeada && resultado.deteccion.categoriaMapeada !== resultado.deteccion.categoria && (
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md border uppercase tracking-wider text-cyan-300 bg-cyan-500/10 border-cyan-500/20">
                    → {resultado.deteccion.categoriaMapeada}
                  </span>
                )}
              </div>

              {resultado.candidatos.length === 0 ? (
                <div className="text-center py-10 bg-dark-800/30 border border-white/[0.06] rounded-2xl">
                  <PackageSearch size={40} className="text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-300 text-sm">{resultado.nota || "No se encontraron productos para la pieza detectada."}</p>
                </div>
              ) : (
                <>
                  <div className="text-xs text-gray-500">
                    {resultado.compatibilidad.verificadas} de {resultado.candidatos.length} candidatos mostrados verifican compatibilidad
                    {resultado.compatibilidad.vehiculo && (
                      <span> para <span className="text-gray-300">
                        {[resultado.compatibilidad.vehiculo.marca, resultado.compatibilidad.vehiculo.modelo, resultado.compatibilidad.vehiculo.anio].filter(Boolean).join(" ")}
                      </span></span>
                    )}
                    {resultado.compatibilidad.nota ? <p className="mt-1 italic text-gray-600">{resultado.compatibilidad.nota}</p> : null}
                  </div>

                  <div className="grid gap-3">
                    {resultado.candidatos.map((producto) => (
                      <div
                        key={producto.id}
                        className={`bg-dark-800/30 border rounded-xl p-3 transition-all ${
                          seleccionado === producto.id
                            ? "border-primary-500/40 ring-1 ring-primary-500/30"
                            : "border-white/[0.06]"
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
                              <p className="text-sm font-semibold text-white line-clamp-2 group-hover:text-primary-300 transition-colors">{producto.name}</p>
                              <p className="text-xs text-gray-500 mt-0.5">{producto.brand} · {producto.model} · {producto.year}</p>
                              <p className="text-xs text-gray-500">Código: {producto.itemCode}</p>
                              <div className="flex flex-wrap items-center gap-2 mt-2">
                                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border uppercase tracking-wider ${disponibilidadClases(producto.disponibilidad.nivel)}`}>
                                  {producto.disponibilidad.etiqueta}
                                </span>
                                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border uppercase tracking-wider ${
                                  producto.compatibilidad.verificada
                                    ? "text-green-400 bg-green-500/10 border-green-500/20"
                                    : "text-gray-400 bg-gray-500/10 border-gray-500/20"
                                }`} title={producto.compatibilidad.nota}>
                                  {producto.compatibilidad.verificada ? "Compatibilidad verificada" : "Compatibilidad no verificada"}
                                </span>
                                <span className="text-amber-400 text-xs font-semibold ml-auto">Bs. {Number(producto.price1).toFixed(2)}</span>
                              </div>
                            </div>
                          </div>
                          {producto.disponibilidadPorSucursal.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mt-2">
                              {producto.disponibilidadPorSucursal.map((s) => (
                                <span key={s.locationId} className={`text-[10px] px-2 py-0.5 rounded-md border ${disponibilidadClases(s.nivel)}`}>
                                  {s.nombre}: {s.etiqueta}
                                </span>
                              ))}
                            </div>
                          )}
                        </Link>
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
                    ))}
                  </div>
                </>
              )}

              {resultado.entrega.sucursales.length > 0 && (
                <div className="bg-dark-800/30 border border-white/[0.06] rounded-xl p-4">
                  <div className="flex items-center gap-2 text-gray-300 text-sm font-medium mb-3">
                    <Store size={15} className="text-primary-400" />
                    ¿Cómo la recibís?
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3">
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
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Sucursal</label>
                      <select
                        value={entrega.sucursalId ?? ""}
                        onChange={(e) => onCambiarEntrega({ ...entrega, sucursalId: e.target.value ? Number(e.target.value) : null })}
                        aria-label="Sucursal de entrega"
                        className="w-full px-3 py-2.5 bg-dark-900/50 border border-white/[0.06] rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                      >
                        {candidatoSeleccionado ? (
                          sucursalesConStock.length > 0 ? (
                            sucursalesConStock.map((s) => (
                              <option key={s.locationId} value={s.locationId}>{s.nombre}</option>
                            ))
                          ) : (
                            <option value="" disabled>Sin sucursales con stock</option>
                          )
                        ) : (
                          resultado.entrega.sucursales.map((s) => (
                            <option key={s.id} value={s.id}>{s.nombre}</option>
                          ))
                        )}
                      </select>
                      {candidatoSeleccionado && entrega.modalidad === "recoger" && sucursalesConStock.length === 0 && (
                        <p className="text-xs text-red-400 mt-1.5">Ese producto no está disponible para recoger en ninguna sucursal.</p>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 mt-3 flex items-center gap-1.5">
                    <Truck size={13} />
                    {entrega.modalidad === "recoger"
                      ? "Seleccioná la sucursal para reservar la pieza (próximamente)."
                      : "El reparto coordina la entrega a tu dirección (próximamente)."}
                  </p>
                </div>
              )}

              {candidatoSeleccionado && (
                <div className="bg-dark-800/30 border border-white/[0.06] rounded-xl p-4 space-y-3">
                  <div className="flex items-center gap-2 text-gray-300 text-sm font-medium">
                    <ShoppingCart size={15} className="text-primary-400" />
                    Preparar venta: {candidatoSeleccionado.name}
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3 items-end">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Cantidad</label>
                      <input
                        type="number"
                        value={cantidad}
                        min={1}
                        max={99}
                        onChange={(e) => setCantidad(Math.max(1, Math.min(99, Number(e.target.value) || 1)))}
                        aria-label="Cantidad a preparar"
                        className="w-24 px-3 py-2.5 bg-dark-900/50 border border-white/[0.06] rounded-xl text-white text-sm focus:ring-2 focus:ring-primary-500 outline-none"
                      />
                    </div>
                    {entrega.modalidad === "delivery" && (
                      <>
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
                      </>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-xs text-gray-600">El stock se confirma al momento de vender en el punto de venta.</p>
                    <button
                      onClick={prepararVenta}
                      disabled={!puedePrepararVenta}
                      type="button"
                      className="inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-5 py-2.5 rounded-xl text-sm font-semibold transition-all"
                    >
                      <Check size={15} /> Preparar venta
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          {!loading && !error && !resultado && (
            <div className="text-center py-10">
              <Camera size={36} className="text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 text-sm">Tomá una foto de la pieza para buscarla en el catálogo.</p>
              <button onClick={onRepetirFoto} className="mt-4 inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-500 text-white px-5 py-2.5 rounded-xl text-sm font-semibold" type="button">
                <Camera size={16} /> Tomar foto
              </button>
            </div>
          )}

          {!loading && !error && resultado && (
            <div className="flex justify-center">
              <button onClick={onRepetirFoto} className="inline-flex items-center gap-2 text-gray-300 hover:text-white text-sm" type="button">
                <Camera size={16} /> Tomar otra foto
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}