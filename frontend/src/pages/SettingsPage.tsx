import { useState, useEffect, useCallback } from "react";
import {
  Users, Shield, Plus, Pencil, Trash2, X, User, RefreshCw,
} from "lucide-react";
import toast from "react-hot-toast";
import api from "../services/api";

interface UserRecord {
  id: number; name: string; email: string; role: string; roleId: number;
  locationId: number | null; locationName: string;
}

interface Role {
  id: number; name: string; permissions: string[];
}

interface Location {
  id: number; name: string;
}

const ROLE_COLORS: Record<string, string> = {
  ADMIN: "bg-red-500/10 text-red-400 border-red-500/20",
  INVENTARIO: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  TIENDA: "bg-green-500/10 text-green-400 border-green-500/20",
};

const ROLE_LABELS: Record<string, string> = {
  ADMIN: "Administrador",
  INVENTARIO: "Inventario",
  TIENDA: "Tienda",
};

const ROLE_DESCRIPTIONS: Record<string, string> = {
  ADMIN: "Acceso total al sistema",
  INVENTARIO: "Gestión de productos, stock, movimientos, costos, precios",
  TIENDA: "Ventas, devoluciones, solicitudes, reportes",
};

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<"users" | "roles">("users");
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);

  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState<number | null>(null);
  const [userForm, setUserForm] = useState({ name: "", email: "", role: "", password: "", locationId: "" });
  const [saving, setSaving] = useState(false);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [usersRes, rolesRes, locsRes] = await Promise.all([
        api.get("/users"),
        api.get("/users/roles"),
        api.get("/locations"),
      ]);
      setUsers(usersRes.data.users);
      setRoles(rolesRes.data.roles);
      setLocations(locsRes.data.locations || locsRes.data);
    } catch {
      toast.error("Error al cargar datos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const openCreate = () => {
    setEditingUser(null);
    setUserForm({ name: "", email: "", role: "", password: "", locationId: "" });
    setShowUserModal(true);
  };

  const openEdit = (u: UserRecord) => {
    setEditingUser(u.id);
    setUserForm({ name: u.name, email: u.email, role: u.role, password: "", locationId: u.locationId ? String(u.locationId) : "" });
    setShowUserModal(true);
  };

  const saveUser = async () => {
    if (!userForm.name || !userForm.email || !userForm.role) {
      toast.error("Completa todos los campos obligatorios"); return;
    }
    if (!editingUser && !userForm.password) {
      toast.error("La contraseña es obligatoria"); return;
    }
    try {
      setSaving(true);
      const payload: any = {
        name: userForm.name,
        email: userForm.email,
        role: userForm.role,
        locationId: userForm.locationId ? Number(userForm.locationId) : null,
      };
      if (userForm.password) payload.password = userForm.password;

      if (editingUser) {
        await api.put(`/users/${editingUser}`, payload);
        toast.success("Usuario actualizado");
      } else {
        await api.post("/users", payload);
        toast.success("Usuario creado");
      }
      setShowUserModal(false);
      fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  const deleteUser = async (id: number) => {
    try {
      await api.delete(`/users/${id}`);
      toast.success("Usuario eliminado");
      setShowDeleteConfirm(null);
      fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.message || "Error al eliminar");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Configuración</h1>
        <p className="text-gray-400 text-sm mt-1">Gestión de usuarios y permisos</p>
      </div>

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

      {activeTab === "users" && (
        <div className="bg-dark-800/50 border border-dark-700/50 rounded-2xl overflow-hidden">
          <div className="px-4 py-3 border-b border-dark-700/50 flex items-center justify-between">
            <h3 className="text-white font-medium">Usuarios del Sistema ({users.length})</h3>
            <div className="flex items-center gap-2">
              <button onClick={fetchData} className="p-1.5 text-gray-400 hover:text-white rounded-lg transition-all"><RefreshCw size={14} /></button>
              <button onClick={openCreate}
                className="flex items-center gap-1 px-3 py-1.5 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-xs font-medium transition-all">
                <Plus size={14} /> Nuevo Usuario
              </button>
            </div>
          </div>
          {loading ? (
            <div className="flex items-center justify-center h-32"><RefreshCw size={24} className="text-primary-400 animate-spin" /></div>
          ) : (
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
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${ROLE_COLORS[u.role] || "bg-gray-500/10 text-gray-400 border-gray-500/20"}`}>
                          {ROLE_LABELS[u.role] || u.role}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{u.locationName}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          <button onClick={() => openEdit(u)} className="p-1.5 text-gray-400 hover:text-primary-400 hover:bg-primary-500/10 rounded-lg transition-all" title="Editar">
                            <Pencil size={14} />
                          </button>
                          <button onClick={() => setShowDeleteConfirm(u.id)} className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all" title="Eliminar">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "roles" && (
        <div className="space-y-4">
          {roles.map((role) => {
            const count = users.filter((u) => u.role === role.name).length;
            return (
              <div key={role.id} className="bg-dark-800/50 border border-dark-700/50 rounded-2xl p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${ROLE_COLORS[role.name] || ""}`}>
                      <Shield size={18} />
                    </div>
                    <div>
                      <h4 className="text-white font-medium">{ROLE_LABELS[role.name] || role.name}</h4>
                      <p className="text-gray-400 text-xs mt-0.5">{ROLE_DESCRIPTIONS[role.name] || role.name}</p>
                    </div>
                  </div>
                  <span className="text-xs text-gray-500">{count} usuarios</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {role.permissions.length > 0 ? role.permissions.map((p, i) => (
                    <span key={i} className="px-2 py-0.5 bg-dark-700 text-gray-400 rounded text-xs">{p}</span>
                  )) : (
                    <span className="px-2 py-0.5 bg-dark-700 text-gray-500 rounded text-xs">Sin permisos definidos</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Confirm Delete */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-dark-800 border border-dark-700/50 rounded-2xl p-6 w-full max-w-sm text-center">
            <Trash2 size={40} className="text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-white mb-2">¿Eliminar usuario?</h3>
            <p className="text-gray-400 text-sm mb-6">Esta acción no se puede deshacer.</p>
            <div className="flex items-center justify-center gap-3">
              <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2.5 text-sm text-gray-400 hover:text-white transition-colors">Cancelar</button>
              <button onClick={() => deleteUser(showDeleteConfirm)} className="bg-red-600 hover:bg-red-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-all">Eliminar</button>
            </div>
          </div>
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
                  {roles.map((r) => <option key={r.id} value={r.name}>{ROLE_LABELS[r.name] || r.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Ubicación</label>
                <select value={userForm.locationId} onChange={(e) => setUserForm({ ...userForm, locationId: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500">
                  <option value="">Sin ubicación</option>
                  {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Contraseña {editingUser ? "(dejar vacío para no cambiar)" : "*"}</label>
                <input type="password" value={userForm.password} onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-700 rounded-xl text-white text-sm focus:outline-none focus:border-primary-500" />
              </div>
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-dark-700/50">
              <button onClick={() => setShowUserModal(false)}
                className="px-4 py-2 text-gray-400 hover:text-white hover:bg-dark-700 rounded-xl text-sm transition-all">
                Cancelar
              </button>
              <button onClick={saveUser} disabled={saving}
                className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-primary-600/20 disabled:opacity-50">
                {saving ? "Guardando..." : editingUser ? "Guardar Cambios" : "Crear Usuario"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
