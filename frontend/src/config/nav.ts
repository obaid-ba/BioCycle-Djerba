import {
  Bell,
  Building2,
  LayoutDashboard,
  MapPin,
  Trash2,
  Truck,
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
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/hotels", label: "Hotels", icon: Building2 },
  { to: "/bins", label: "Smart Bins", icon: Trash2 },
  { to: "/map", label: "Map", icon: MapPin },
  { to: "/collections", label: "Collections", icon: Truck },
  { to: "/alerts", label: "Alerts", icon: Bell },
  { to: "/users", label: "Users", icon: Users, roles: ["admin"] },
];

export function navItemsForRole(role: UserRole): NavItem[] {
  return navItems.filter((item) => !item.roles || item.roles.includes(role));
}
