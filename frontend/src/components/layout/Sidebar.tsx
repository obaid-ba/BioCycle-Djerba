import { Leaf } from "lucide-react";
import { NavLink } from "react-router-dom";

import { navItemsForRole } from "@/config/nav";
import { useAuth } from "@/context/auth";
import { cn } from "@/lib/utils";

interface SidebarProps {
  /** Called when a nav item is chosen — used to close the mobile drawer. */
  onNavigate?: () => void;
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const { user } = useAuth();
  const items = user ? navItemsForRole(user.role) : [];

  return (
    <div className="flex h-full flex-col bg-background">
      <div className="flex h-16 items-center gap-2.5 border-b px-6">
        <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Leaf className="size-5" />
        </div>
        <div>
          <p className="text-sm font-semibold leading-tight">BioCycle</p>
          <p className="text-xs text-muted-foreground">Djerba</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {items.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )
            }
          >
            <Icon className="size-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
