import {
  Building2,
  ClipboardList,
  FileText,
  LayoutDashboard,
  MapPin,
  Users,
  type LucideIcon,
} from "lucide-react";

import type { UserRole } from "@/types";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Roles allowed to see this item. Omit to allow every authenticated user. */
  roles?: UserRole[];
}

/** Single source of truth for the sidebar. Order here is the display order. */
export const navItems: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "hotel_manager"] },
  { to: "/requests", label: "Requests", icon: ClipboardList },
  { to: "/hotels", label: "Hotels", icon: Building2, roles: ["admin"] },
  { to: "/map", label: "Map", icon: MapPin, roles: ["admin"] },
  { to: "/reports", label: "Reports", icon: FileText, roles: ["admin"] },
  { to: "/users", label: "Users", icon: Users, roles: ["admin"] },
];

export function navItemsForRole(role: UserRole): NavItem[] {
  return navItems.filter((item) => !item.roles || item.roles.includes(role));
}

/**
 * The landing route for a role after login (and where role-mismatched
 * redirects send a user). Operators don't have the Dashboard, so they go
 * straight to their collection queue; everyone else lands on the Dashboard.
 */
export function homePathForRole(role: UserRole): string {
  return role === "operator" ? "/requests" : "/";
}
