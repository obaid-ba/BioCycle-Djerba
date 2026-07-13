import { LogOut, Menu } from "lucide-react";

import { ThemeToggle } from "@/components/common/ThemeToggle";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/auth";
import { useRealtimeStatus } from "@/context/realtime";
import { cn } from "@/lib/utils";

interface TopbarProps {
  onOpenMenu: () => void;
}

const roleLabels: Record<string, string> = {
  admin: "Administrator",
  operator: "Operator",
  hotel_manager: "Hotel Manager",
};

export function Topbar({ onOpenMenu }: TopbarProps) {
  const { user, logout } = useAuth();
  const wsStatus = useRealtimeStatus();

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur lg:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={onOpenMenu}
        aria-label="Open navigation"
      >
        <Menu />
      </Button>

      <div className="flex-1" />

      <span
        className="flex items-center gap-1.5 text-xs text-muted-foreground"
        title={`Realtime: ${wsStatus}`}
      >
        <span
          className={cn(
            "size-2 rounded-full",
            wsStatus === "open"
              ? "bg-success"
              : wsStatus === "connecting"
                ? "bg-warning animate-pulse"
                : "bg-muted-foreground/40",
          )}
        />
        <span className="hidden sm:inline">
          {wsStatus === "open" ? "Live" : wsStatus === "connecting" ? "Connecting" : "Offline"}
        </span>
      </span>

      <NotificationBell />

      <ThemeToggle />

      {user && (
        <div className="flex items-center gap-3 border-l pl-3">
          <div className="hidden text-right sm:block">
            <p className="text-sm font-medium leading-tight">{user.full_name}</p>
            <p className="text-xs text-muted-foreground">
              {roleLabels[user.role] ?? user.role}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={logout}
            aria-label="Sign out"
          >
            <LogOut />
          </Button>
        </div>
      )}
    </header>
  );
}
