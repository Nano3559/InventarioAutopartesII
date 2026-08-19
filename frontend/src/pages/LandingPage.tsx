import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import {
  ShoppingCart,
  Package,
  BarChart3,
  Shield,
  ArrowRight,
  Phone,
  MapPin,
  Clock,
  Wrench,
  Car,
  Truck,
  ChevronRight,
} from "lucide-react";

export default function LandingPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();

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
              <a href="#nosotros" className="hover:text-white transition-colors">Nosotros</a>
              <a href="#servicios" className="hover:text-white transition-colors">Servicios</a>
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

      {/* Hero */}
      <section
        id="inicio"
        className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16"
      >
        <div className="absolute inset-0 bg-hero-gradient" />
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-20 w-72 h-72 bg-primary-500 rounded-full blur-[128px]" />
          <div className="absolute bottom-20 right-20 w-96 h-96 bg-accent rounded-full blur-[128px]" />
        </div>
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="inline-flex items-center gap-2 bg-dark-800/50 border border-dark-600/50 rounded-full px-4 py-1.5 mb-8">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-sm text-gray-400">Tu aliado en repuestos automotrices</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-extrabold text-white mb-6 leading-tight">
            Repuestos y Accesorios
            <br />
            <span className="text-gradient">para tu Vehículo</span>
          </h1>
          <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            La mejor selección de repuestos originales y alternativos para Toyota, Nissan,
            Mazda y más. Stock en almacenes y 3 tiendas a tu disposición.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={handleLogin}
              className="bg-primary-600 hover:bg-primary-700 text-white px-8 py-3.5 rounded-xl text-lg font-semibold transition-all hover:shadow-xl hover:shadow-primary-600/30 flex items-center justify-center gap-2"
            >
              Ir a Login
              <ArrowRight size={20} />
            </button>
            <a
              href="#servicios"
              className="bg-dark-800/50 hover:bg-dark-700/50 border border-dark-600/50 text-white px-8 py-3.5 rounded-xl text-lg font-semibold transition-all flex items-center justify-center gap-2"
            >
              Ver Catálogo
            </a>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-20 max-w-4xl mx-auto">
            {[
              { number: "5,000+", label: "Productos" },
              { number: "7", label: "Ubicaciones" },
              { number: "3", label: "Tiendas" },
              { number: "4", label: "Almacenes" },
            ].map((stat) => (
              <div key={stat.label} className="bg-dark-800/30 border border-dark-700/50 rounded-xl p-4">
                <p className="text-3xl font-bold text-white">{stat.number}</p>
                <p className="text-sm text-gray-400 mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Nosotros */}
      <section id="nosotros" className="py-24 bg-dark-900/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              ¿Quiénes Somos?
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Somos una empresa dedicada a la comercialización de repuestos y accesorios
              para vehículos, con años de experiencia brindando soluciones automotrices.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Package,
                title: "Amplio Inventario",
                desc: "Miles de repuestos para diferentes marcas y modelos de vehículos disponibles en-stock.",
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
                className="bg-dark-800/50 border border-dark-700/50 rounded-2xl p-8 hover:border-primary-600/30 transition-all group"
              >
                <div className="w-12 h-12 bg-primary-600/10 rounded-xl flex items-center justify-center mb-5 group-hover:bg-primary-600/20 transition-colors">
                  <item.icon size={24} className="text-primary-500" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-3">{item.title}</h3>
                <p className="text-gray-400 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Servicios */}
      <section id="servicios" className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Nuestros Servicios
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Ofrecemos una gama completa de servicios para satisfacer todas tus necesidades automotrices.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: Wrench,
                title: "Repuestos Originales",
                desc: "Piezas OEM y alternativas de primeras marcas.",
              },
              {
                icon: ShoppingCart,
                title: "Venta por Mayor",
                desc: "Precios especiales para compras al por mayor.",
              },
              {
                icon: BarChart3,
                title: "Gestión de Stock",
                desc: "Control total del inventario en tiempo real.",
              },
              {
                icon: Car,
                title: "Asesoría Técnica",
                desc: "Te ayudamos a encontrar la pieza correcta.",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="bg-card-gradient border border-dark-700/50 rounded-2xl p-6 hover:border-accent/30 transition-all group text-center"
              >
                <div className="w-14 h-14 bg-accent/10 rounded-xl flex items-center justify-center mb-4 mx-auto group-hover:bg-accent/20 transition-colors">
                  <item.icon size={26} className="text-accent" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contacto */}
      <section id="contacto" className="py-24 bg-dark-900/50">
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
                className="bg-dark-800/50 border border-dark-700/50 rounded-2xl p-8 text-center"
              >
                <div className="w-12 h-12 bg-primary-600/10 rounded-xl flex items-center justify-center mb-5 mx-auto">
                  <item.icon size={22} className="text-primary-500" />
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
      <footer className="border-t border-dark-700/50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <Car size={18} className="text-white" />
            </div>
            <span className="font-semibold text-white">RepuestoPro</span>
          </div>
          <p className="text-gray-500 text-sm">
            &copy; 2026 RepuestoPro. Todos los derechos reservados.
          </p>
          <button
            onClick={handleLogin}
            className="text-primary-500 hover:text-primary-400 text-sm font-medium flex items-center gap-1 transition-colors"
          >
            Acceder al sistema <ChevronRight size={14} />
          </button>
        </div>
      </footer>
    </div>
  );
}
