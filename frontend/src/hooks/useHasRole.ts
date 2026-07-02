import { useAuth } from "@/context/auth";
import type { UserRole } from "@/types";

/** True when the current user holds one of the given roles. */
export function useHasRole(...roles: UserRole[]): boolean {
  const { user } = useAuth();
  return !!user && roles.includes(user.role);
}
