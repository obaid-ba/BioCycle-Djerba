import { LogOut, Menu } from "lucide-react";

import { ThemeToggle } from "@/components/common/ThemeToggle";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/auth";

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
