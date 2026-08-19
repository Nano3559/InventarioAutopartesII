export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-xl shadow-sm border">
          <p className="text-sm text-gray-500">Total Productos</p>
          <p className="text-3xl font-bold mt-1">--</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border">
          <p className="text-sm text-gray-500">Ventas del Día</p>
          <p className="text-3xl font-bold mt-1">--</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border">
          <p className="text-sm text-gray-500">Productos sin Stock</p>
          <p className="text-3xl font-bold mt-1 text-red-500">--</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border">
          <p className="text-sm text-gray-500">Solicitudes Pendientes</p>
          <p className="text-3xl font-bold mt-1 text-yellow-500">--</p>
        </div>
      </div>
    </div>
  );
}
