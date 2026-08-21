import { Navigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";

interface RoleRouteProps {
  children: React.ReactNode;
  allowedRoles: string[];
}

export default function RoleRoute({ children, allowedRoles }: RoleRouteProps) {
  const { user, isAuthenticated } = useAuthStore();

  if (!isAuthenticated) return <Navigate to="/login" />;
  if (!user || !allowedRoles.includes(user.role)) return <Navigate to="/panel" />;

  return <>{children}</>;
}
