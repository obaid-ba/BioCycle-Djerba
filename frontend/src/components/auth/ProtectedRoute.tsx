import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@/context/auth";
import type { UserRole } from "@/types";

interface ProtectedRouteProps {
  children: ReactNode;
  /** When set, the user must hold one of these roles or they are sent home. */
  roles?: UserRole[];
}

/**
 * Gate for authenticated routes. While the session is being restored it shows a
 * spinner; unauthenticated users are redirected to /login (preserving the
 * target so we can return there after sign-in), and role mismatches go home.
 */
export function ProtectedRoute({ children, roles }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (roles && user && !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
