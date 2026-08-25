import { useState } from "react";
import {
  Users, Shield, Plus, Pencil, Trash2, X, User,
} from "lucide-react";
import toast from "react-hot-toast";

interface UserRecord {
  id: number; name: string; email: string; role: string;
  locationId: number | null; locationName: string;
}

const MOCK_USERS: UserRecord[] = [
  { id: 1, name: "Admin General", email: "admin@inventario.com", role: "ADMIN", locationId: null, locationName: "N/A" },
  { id: 2, name: "Carlos Mendoza", email: "inventario@inventario.com", role: "INVENTARIO", locationId: 1, locationName: "Almacén Central" },
  { id: 3, name: "María García", email: "tienda1@inventario.com", role: "TIENDA", locationId: 3, locationName: "Tienda Centro" },
  { id: 4, name: "Juan López", email: "tienda2@inventario.com", role: "TIENDA", locationId: 4, locationName: "Tienda Norte" },
  { id: 5, name: "Ana Torres", email: "tienda3@inventario.com", role: "TIENDA", locationId: 5, locationName: "Tienda Sur" },
];

const ROLES = [
  { value: "ADMIN", label: "Administrador", description: "Acceso total al sistema" },
  { value: "INVENTARIO", label: "Inventario", description: "Gestión de productos, stock, movimientos, costos, precios" },
  { value: "TIENDA", label: "Tienda", description: "Ventas, devoluciones, solicitudes, reportes" },
];

const ROLE_COLORS: Record<string, string> = {
  ADMIN: "bg-red-500/10 text-red-400 border-red-500/20",
  INVENTARIO: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  TIENDA: "bg-green-500/10 text-green-400 border-green-500/20",
};

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<"users" | "roles">("users");
  const [users, setUsers] = useState<UserRecord[]>(MOCK_USERS);
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState<number | null>(null);
  const [userForm, setUserForm] = useState({ name: "", email: "", role: "", password: "" });

  const openCreate = () => {
    setEditingUser(null);
    setUserForm({ name: "", email: "", role: "", password: "" });
    setShowUserModal(true);
  };

  const openEdit = (u: UserRecord) => {
    setEditingUser(u.id);
    setUserForm({ name: u.name, email: u.email, role: u.role, password: "" });
    setShowUserModal(true);
  };

  const saveUser = () => {
    if (!userForm.name || !userForm.email || !userForm.role) {
      toast.error("Completa todos los campos obligatorios"); return;
    }
    if (editingUser) {
      setUsers((prev) => prev.map((u) => u.id === editingUser ? { ...u, name: userForm.name, email: userForm.email, role: userForm.role } : u));
      toast.success("Usuario actualizado");
    } else {
      if (!userForm.password) { toast.error("La contraseña es obligatoria"); return; }
      setUsers((prev) => [...prev, {
        id: Date.now(), name: userForm.name, email: userForm.email,
        role: userForm.role, locationId: null, locationName: "N/A",
      }]);
      toast.success("Usuario creado");
    }
    setShowUserModal(false);
  };

  const deleteUser = (id: number) => {
    if (id === 1) { toast.error("No se puede eliminar el admin principal"); return; }
    setUsers((prev) => prev.filter((u) => u.id !== id));
    toast.success("Usuario eliminado");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Configuración</h1>
        <p className="text-gray-400 text-sm mt-1">Gestión de usuarios y permisos</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 bg-dark-800/50 border border-dark-700/50 rounded-xl p-1">
        <button onClick={() => setActiveTab("users")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeTab === "users"
              ? "bg-primary-600/20 text-primary-400 border border-primary-600/30"
              : "text-gray-400 hover:text-gray-200 border border-transparent"
          }`}>
          <Users size={16} /> Usuarios
        </button>
        <button onClick={() => setActiveTab("roles")}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            activeTab === "roles"
              ? "bg-primary-600/20 text-primary-400 border border-primary-600/30"
              : "text-gray-400 hover:text-gray-200 border border-transparent"
          }`}>
          <Shield size={16} /> Roles y Permisos
        </button>
      </div>

      {/* Users tab */}
      {activeTab === "users" && (
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-700/50 flex items-center justify-between">
            <h3 className="text-white font-medium">Usuarios del Sistema ({users.length})</h3>
            <button onClick={openCreate}
              className="flex items-center gap-1 px-3 py-1.5 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-xs font-medium transition-all">
              <Plus size={14} /> Nuevo Usuario
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-700/50">
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Nombre</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Email</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Rol</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium">Ubicación</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-dark-700/30 hover:bg-dark-700/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-dark-700 rounded-full flex items-center justify-center">
                          <User size={14} className="text-gray-400" />
                        </div>
                        <span className="text-white font-medium">{u.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-300">{u.email}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${ROLE_COLORS[u.role] || ""}`}>
                        {ROLES.find((r) => r.value === u.role)?.label || u.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{u.locationName}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-1">
                        <button onClick={() => openEdit(u)} className="p-1.5 text-gray-400 hover:text-primary-400 hover:bg-primary-500/10 rounded-lg transition-all" title="Editar">
                          <Pencil size={14} />
                        </button>
                        <button onClick={() => deleteUser(u.id)} className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all" title="Eliminar">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Roles tab */}
      {activeTab === "roles" && (
        <div className="space-y-4">
          {ROLES.map((role) => {
            const count = users.filter((u) => u.role === role.value).length;
            return (
              <div key={role.value} className="bg-dark-800/50 border border-dark-700/50 rounded-2xl p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${ROLE_COLORS[role.value]}`}>
                      <Shield size={18} />
                    </div>
                    <div>
                      <h4 className="text-white font-medium">{role.label}</h4>
                      <p className="text-gray-400 text-xs mt-0.5">{role.description}</p>
                    </div>
                  </div>
                  <span className="text-xs text-gray-500">{count} usuarios</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {role.value === "ADMIN" && (
                    <>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Acceso total</span>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Gestión de usuarios</span>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Configuración</span>
                    </>
                  )}
                  {role.value === "INVENTARIO" && (
                    <>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Inventario</span>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Solicitudes</span>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Movimientos</span>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Costos</span>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Precios</span>
                    </>
                  )}
                  {role.value === "TIENDA" && (
                    <>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Ventas</span>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Ventas por Mayor</span>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Devoluciones</span>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Solicitudes</span>
                      <span className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">Reportes</span>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* User Modal */}
      {showUserModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-dark-900 border border-dark-700/50 rounded-2xl w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-dark-700/50">
              <h3 className="text-lg font-bold text-white">{editingUser ? "Editar Usuario" : "Nuevo Usuario"}</h3>
              <button onClick={() => setShowUserModal(false)} className="p-1.5 text-gray-400 hover:text-white hover:bg-dark-700 rounded-lg transition-all">
                <X size={18} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Nombre *</label>
                <input value={userForm.name} onChange={(e) => setUserForm({ ...userForm, name: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Email *</label>
                <input type="email" value={userForm.email} onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Rol *</label>
                <select value={userForm.role} onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500">
                  <option value="">Seleccionar rol...</option>
                  {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
              {!editingUser && (
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Contraseña *</label>
                  <input type="password" value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-dark-700/50">
              <button onClick={() => setShowUserModal(false)}
                className="px-4 py-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-xl text-sm transition-all">
                Cancelar
              </button>
              <button onClick={saveUser}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-primary-600/20">
                {editingUser ? "Guardar Cambios" : "Crear Usuario"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
