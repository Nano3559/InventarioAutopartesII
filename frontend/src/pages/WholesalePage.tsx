import { TrendingUp } from "lucide-react";

export default function WholesalePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Ventas por Mayor</h1>
        <p className="text-gray-400 text-sm mt-1">Gestión de ventas al por mayor</p>
      </div>
      <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl p-8 text-center">
        <TrendingUp size={48} className="text-gray-600 mx-auto mb-4" />
        <p className="text-gray-400">Módulo de ventas por mayor por implementar</p>
      </div>
    </div>
  );
}
