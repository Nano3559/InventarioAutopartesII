import { useNavigate } from "react-router-dom";

import {
  Package,
  ArrowRight,
  Phone,
  MapPin,
  Clock,
  Wrench,
  Car,
  Truck,
  Shield,
  ChevronRight,
  Settings,
  Zap,
  Star,
  CircleDollarSign,
} from "lucide-react";

export default function LandingPage() {
  const navigate = useNavigate();
  const handleLogin = () => {
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-dark-950">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-dark-950/80 backdrop-blur-md border-b border-dark-700/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                <Car size={22} className="text-white" />
              </div>
              <span className="text-xl font-bold text-white">RepuestoPro</span>
            </div>
            <div className="hidden md:flex items-center gap-8 text-sm text-gray-400">
              <a href="#inicio" className="hover:text-white transition-colors">Inicio</a>
              <a href="#productos" className="hover:text-white transition-colors">Productos</a>
              <a href="#contacto" className="hover:text-white transition-colors">Contacto</a>
            </div>
            <button
              onClick={handleLogin}
              className="bg-primary-600 hover:bg-primary-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition-all hover:shadow-lg hover:shadow-primary-600/25 flex items-center gap-2"
            >
              Iniciar Sesión
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section id="inicio" className="relative min-h-screen flex items-center overflow-hidden pt-16">
        <div className="absolute inset-0" />
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-20 w-72 h-72 bg-primary-500 rounded-full blur-[128px]" />
          <div className="absolute bottom-20 right-20 w-96 h-96 bg-accent rounded-full blur-[128px]" />
        </div>

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Banner principal */}
          <div className="relative rounded-3xl overflow-hidden border border-white/[0.06] mb-10">
            <div className="absolute inset-0 bg-gradient-to-br from-dark-800/90 via-dark-900/80 to-dark-950/90" />
            <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary-600/10 rounded-full blur-[100px] -translate-y-1/4 translate-x-1/4" />
            <div className="absolute bottom-0 left-0 w-[300px] h-[300px] bg-accent/5 rounded-full blur-[80px] translate-y-1/3 -translate-x-1/4" />

            <div className="relative grid lg:grid-cols-[1fr,auto] gap-12 p-10 md:p-14 items-center">
              <div>
                <div className="flex items-center gap-3 mb-6">
                  <span className="px-3 py-1 bg-primary-500/10 text-primary-400 text-xs font-semibold rounded-full border border-primary-500/20 uppercase tracking-wider">
                    Destacado
                  </span>
                  <span className="px-3 py-1 bg-green-500/10 text-green-400 text-xs font-semibold rounded-full border border-green-500/20">
                    -29% OFF
                  </span>
                </div>

                <h2 className="text-4xl md:text-6xl font-extrabold text-white mb-5 leading-[1.1] tracking-tight">
                  Kit de Frenos
                  <br />
                  <span className="bg-gradient-to-r from-primary-400 via-primary-300 to-accent bg-clip-text text-transparent">
                    Toyota Hilux 2020–2024
                  </span>
                </h2>

                <p className="text-gray-400 text-lg max-w-xl mb-8 leading-relaxed">
                  Balatas, discos y calipers de alta resistencia. Componentes OEM con garantía de fábrica para tu seguridad en cada kilómetro.
                </p>

                <div className="flex flex-wrap items-center gap-6 mb-8">
                  <div className="flex items-baseline gap-3">
                    <span className="text-4xl font-bold text-white">Bs. 850</span>
                    <span className="text-lg text-gray-500 line-through">Bs. 1,200</span>
                  </div>
                  <div className="h-8 w-px bg-white/10 hidden sm:block" />
                  <div className="flex items-center gap-1.5 text-sm text-gray-400">
                    <Star size={14} className="text-amber-400 fill-amber-400" />
                    <span>4.9 / 5.0</span>
                    <span className="text-gray-600">·</span>
                    <span>128 vendidos</span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-4">
                  <button
                    onClick={handleLogin}
                    className="bg-primary-600 hover:bg-primary-500 text-white px-8 py-3.5 rounded-xl text-sm font-semibold transition-all hover:shadow-xl hover:shadow-primary-600/25 flex items-center gap-2.5"
                  >
                    Ver Producto
                    <ArrowRight size={16} />
                  </button>
                  <button
                    onClick={handleLogin}
                    className="bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-gray-300 px-8 py-3.5 rounded-xl text-sm font-semibold transition-all flex items-center gap-2.5"
                  >
                    Ver Catálogo Completo
                  </button>
                </div>
              </div>

              {/* Imagen / Visual del producto */}
              <div className="hidden lg:flex items-center justify-center">
                <div className="relative w-80 h-80">
                  <div className="absolute inset-0 rounded-full border border-white/[0.04]" />
                  <div className="absolute inset-3 rounded-full border border-white/[0.03]" />
                  <div className="absolute inset-6 rounded-full bg-gradient-to-br from-dark-700/80 to-dark-800/60 border border-white/[0.06] flex items-center justify-center backdrop-blur-sm">
                    <Package size={96} className="text-primary-400/50" strokeWidth={1} />
                  </div>
                  <div className="absolute top-8 right-8 w-2 h-2 bg-primary-500/40 rounded-full" />
                  <div className="absolute bottom-12 left-6 w-1.5 h-1.5 bg-accent/30 rounded-full" />
                  <div className="absolute top-1/2 right-0 w-1 h-1 bg-primary-400/20 rounded-full" />
                </div>
              </div>
            </div>
          </div>

          {/* 4 Productos destacados */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
            {[
              {
                icon: Settings,
                name: "Amortiguadores Monroe",
                brand: "Toyota / Nissan",
                price: "Bs. 320",
                oldPrice: "Bs. 450",
                badge: "Más vendido",
                badgeStyle: "text-amber-400 bg-amber-500/10 border-amber-500/20",
                accent: "group-hover:text-amber-400",
              },
              {
                icon: Wrench,
                name: "Filtro de Aceite Mann",
                brand: "Universal",
                price: "Bs. 45",
                oldPrice: null,
                badge: "Disponible",
                badgeStyle: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
                accent: "group-hover:text-emerald-400",
              },
              {
                icon: Zap,
                name: "Pastillas de Freno Brembo",
                brand: "Mazda / Nissan",
                price: "Bs. 280",
                oldPrice: "Bs. 350",
                badge: "Nuevo",
                badgeStyle: "text-blue-400 bg-blue-500/10 border-blue-500/20",
                accent: "group-hover:text-blue-400",
              },
              {
                icon: CircleDollarSign,
                name: "Correa de Distribución",
                brand: "Toyota Hilux",
                price: "Bs. 190",
                oldPrice: null,
                badge: "Recomendado",
                badgeStyle: "text-violet-400 bg-violet-500/10 border-violet-500/20",
                accent: "group-hover:text-violet-400",
              },
            ].map((product) => (
              <div
                key={product.name}
                className="group relative bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5 hover:bg-white/[0.04] hover:border-white/[0.1] transition-all duration-300 cursor-pointer"
              >
                <div className="relative w-full aspect-square bg-dark-800/60 rounded-xl mb-5 flex items-center justify-center overflow-hidden border border-white/[0.03]">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary-600/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <product.icon
                    size={44}
                    strokeWidth={1.2}
                    className={`text-gray-600/60 ${product.accent} transition-colors duration-300 relative z-10`}
                  />
                </div>

                <span className={`inline-flex items-center px-2.5 py-0.5 text-[10px] font-semibold rounded-md border mb-3 uppercase tracking-wider ${product.badgeStyle}`}>
                  {product.badge}
                </span>

                <h3 className="text-sm font-semibold text-white mb-1 leading-snug">{product.name}</h3>
                <p className="text-[11px] text-gray-500 mb-3 tracking-wide">{product.brand}</p>

                <div className="flex items-baseline gap-2">
                  <span className="text-lg font-bold text-white">{product.price}</span>
                  {product.oldPrice && (
                    <span className="text-xs text-gray-500 line-through">{product.oldPrice}</span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-white/[0.04] rounded-2xl overflow-hidden border border-white/[0.06]">
            {[
              { number: "5,000+", label: "Productos" },
              { number: "7", label: "Ubicaciones" },
              { number: "3", label: "Tiendas" },
              { number: "4", label: "Almacenes" },
            ].map((stat) => (
              <div key={stat.label} className="bg-dark-950/60 px-6 py-6 text-center">
                <p className="text-2xl md:text-3xl font-bold text-white mb-1">{stat.number}</p>
                <p className="text-xs text-gray-500 uppercase tracking-wider">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Productos */}
      <section id="productos" className="py-28 bg-dark-950">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              ¿Por qué elegirnos?
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Soluciones integrales para el mantenimiento de tu flota vehicular.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Package,
                title: "Amplio Inventario",
                desc: "Miles de repuestos para diferentes marcas y modelos de vehículos disponibles en stock.",
              },
              {
                icon: Truck,
                title: "Distribución Rápida",
                desc: "4 almacenes y 3 tiendas para garantizar que recibas tu pedido a tiempo.",
              },
              {
                icon: Shield,
                title: "Calidad Garantizada",
                desc: "Trabajamos con los mejores proveedores para ofrecer productos de primera calidad.",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="group bg-white/[0.02] border border-white/[0.06] rounded-2xl p-8 hover:bg-white/[0.04] hover:border-white/[0.1] transition-all duration-300"
              >
                <div className="w-12 h-12 bg-primary-600/10 rounded-xl flex items-center justify-center mb-5 group-hover:bg-primary-600/15 transition-colors">
                  <item.icon size={24} className="text-primary-400" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">{item.title}</h3>
                <p className="text-gray-400 leading-relaxed text-sm">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contacto */}
      <section id="contacto" className="py-24 bg-dark-950">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Contáctanos
            </h2>
            <p className="text-gray-400">Estamos aquí para servirte</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {[
              {
                icon: MapPin,
                title: "Dirección",
                lines: ["Av. Principal #1234", "Cochabamba, Bolivia"],
              },
              {
                icon: Phone,
                title: "Teléfono",
                lines: ["+591 4 1234567", "+591 71234567"],
              },
              {
                icon: Clock,
                title: "Horario",
                lines: ["Lunes a Viernes: 8:30 - 18:00", "Sábados: 8:30 - 13:00"],
              },
            ].map((item) => (
              <div
                key={item.title}
                className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-8 text-center"
              >
                <div className="w-12 h-12 bg-primary-600/10 rounded-xl flex items-center justify-center mb-5 mx-auto">
                  <item.icon size={22} className="text-primary-400" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-3">{item.title}</h3>
                {item.lines.map((line, i) => (
                  <p key={i} className="text-gray-400 text-sm">
                    {line}
                  </p>
                ))}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/[0.06] py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <Car size={18} className="text-white" />
            </div>
            <span className="font-semibold text-white">RepuestoPro</span>
          </div>
          <p className="text-gray-500 text-sm">
            © 2026 RepuestoPro. Todos los derechos reservados.
          </p>
          <button
            onClick={handleLogin}
            className="text-primary-400 hover:text-primary-300 text-sm font-medium flex items-center gap-1 transition-colors"
          >
            Acceder al sistema <ChevronRight size={14} />
          </button>
        </div>
      </footer>
    </div>
  );
}
