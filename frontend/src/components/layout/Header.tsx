import { User, Bell } from "lucide-react";
import { useAuthStore } from "../../stores/authStore";

export default function Header() {
  const { user } = useAuthStore();

  return (
    <header className="h-16 bg-dark-900/50 border-b border-dark-700/50 flex items-center justify-between px-6 backdrop-blur-sm">
      <div />
      <div className="flex items-center gap-4">
        <button className="relative p-2 text-gray-400 hover:text-white hover:bg-dark-800 rounded-xl transition-all">
          <Bell size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary-500 rounded-full" />
        </button>
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
