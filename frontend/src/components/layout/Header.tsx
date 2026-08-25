import { useState, useEffect, useCallback } from "react";
import { User, Bell, Menu, CheckCheck, X } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";
import api from "../../services/api";

interface Notification {
  id: number; title: string; message: string; type: string; read: boolean;
  linkUrl?: string; createdAt: string;
}

interface HeaderProps {
  onMenuClick: () => void;
}

export default function Header({ onMenuClick }: HeaderProps) {
  const { user } = useAuthStore();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotifs, setShowNotifs] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      const res = await api.get("/notifications");
      setNotifications(res.data.notifications);
      setUnreadCount(res.data.unreadCount);
    } catch {
      // Silently fail — notifications are non-critical
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  const markAsRead = async (id: number) => {
    try {
      await api.put(`/notifications/${id}/read`);
      setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, read: true } : n));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch { /* ignore */ }
  };

  const markAllRead = async () => {
    try {
      await api.put("/notifications/read-all");
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch { /* ignore */ }
  };

  return (
    <header className="h-16 bg-dark-900/50 border-b border-dark-700/50 flex items-center justify-between px-4 md:px-6 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="p-2 text-gray-400 hover:text-white hover:bg-dark-800 rounded-xl transition-all md:hidden"
        >
          <Menu size={20} />
        </button>
      </div>
      <div className="flex items-center gap-4">
        <div className="relative">
          <button
            onClick={() => setShowNotifs(!showNotifs)}
            className="relative p-2 text-gray-400 hover:text-white hover:bg-dark-800 rounded-xl transition-all"
          >
            <Bell size={20} />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center bg-primary-600 text-white text-[10px] font-bold rounded-full px-1">
                {unreadCount > 99 ? "99+" : unreadCount}
              </span>
            )}
          </button>

          {showNotifs && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowNotifs(false)} />
              <div className="absolute right-0 top-12 z-50 w-80 max-h-96 bg-dark-800 border border-dark-700/50 rounded-2xl shadow-2xl overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b border-dark-700/50">
                  <h4 className="text-white font-medium text-sm">Notificaciones</h4>
                  <div className="flex items-center gap-2">
                    {unreadCount > 0 && (
                      <button onClick={markAllRead} className="text-xs text-primary-400 hover:text-primary-300 transition-colors">
                        <CheckCheck size={14} />
                      </button>
                    )}
                    <button onClick={() => setShowNotifs(false)} className="text-gray-400 hover:text-white transition-colors">
                      <X size={14} />
                    </button>
                  </div>
                </div>
                <div className="overflow-y-auto max-h-80">
                  {notifications.length === 0 ? (
                    <div className="px-4 py-8 text-center text-gray-500 text-sm">Sin notificaciones</div>
                  ) : (
                    notifications.map((n) => (
                      <div
                        key={n.id}
                        onClick={() => !n.read && markAsRead(n.id)}
                        className={`px-4 py-3 border-b border-dark-700/30 cursor-pointer transition-colors ${
                          n.read ? "hover:bg-dark-700/20" : "bg-primary-600/5 hover:bg-primary-600/10"
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          {!n.read && <span className="w-2 h-2 mt-1.5 bg-primary-500 rounded-full flex-shrink-0" />}
                          <div className="flex-1 min-w-0">
                            <p className={`text-xs font-medium ${n.read ? "text-gray-400" : "text-white"}`}>{n.title}</p>
                            <p className="text-xs text-gray-500 mt-0.5 truncate">{n.message}</p>
                            <p className="text-[10px] text-gray-600 mt-1">{new Date(n.createdAt).toLocaleString("es-BO")}</p>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-3 pl-4 border-l border-dark-700/50">
          <div className="w-9 h-9 bg-primary-600/10 border border-primary-600/20 rounded-xl flex items-center justify-center">
            <User size={18} className="text-primary-400" />
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-medium text-white">{user?.name || "Usuario"}</p>
            <p className="text-xs text-gray-500">{user?.role || "Sin rol"}</p>
          </div>
        </div>
      </div>
    </header>
  );
}
