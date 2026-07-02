import type { ReactNode } from "react";

import { useAuth } from "@/context/auth";
import type { UserRole } from "@/types";

/** Render children only when the current user holds one of the given roles. */
export function RoleGate({
  roles,
  children,
}: {
  roles: UserRole[];
  children: ReactNode;
}) {
  const { user } = useAuth();
  if (!user || !roles.includes(user.role)) return null;
  return <>{children}</>;
}
