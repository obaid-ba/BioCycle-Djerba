import { Bell, CheckCheck } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  useMarkAllRead,
  useMarkRead,
  useNotifications,
  useUnreadCount,
} from "@/hooks/useNotifications";
import { cn, formatDateTime } from "@/lib/utils";
import type { Notification } from "@/types";

/** Bell + unread badge with a dropdown of recent notifications. */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const unread = useUnreadCount();
  const list = useNotifications({ page_size: 10 });
  const markRead = useMarkRead();
  const markAll = useMarkAllRead();

  const count = unread.data ?? 0;
  const items = list.data?.items ?? [];

  // Close on outside click / Escape.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setOpen((o) => !o)}
        aria-label={`Notifications${count ? ` (${count} unread)` : ""}`}
      >
        <Bell />
        {count > 0 && (
          <span className="absolute right-1 top-1 flex min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold leading-4 text-destructive-foreground">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </Button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border bg-card shadow-lg">
          <div className="flex items-center justify-between border-b px-3 py-2">
            <span className="text-sm font-semibold">Notifications</span>
            {count > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={() => markAll.mutate()}
                disabled={markAll.isPending}
              >
                <CheckCheck className="size-3.5" />
                Mark all read
              </Button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {list.isLoading ? (
              <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                Loading…
              </p>
            ) : items.length === 0 ? (
              <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                No notifications yet.
              </p>
            ) : (
              <ul className="divide-y">
                {items.map((n) => (
                  <NotificationRow
                    key={n.id}
                    n={n}
                    onRead={() => !n.is_read && markRead.mutate(n.id)}
                  />
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function NotificationRow({ n, onRead }: { n: Notification; onRead: () => void }) {
  return (
    <li
      className={cn(
        "cursor-pointer px-3 py-2.5 text-sm transition-colors hover:bg-muted/50",
        !n.is_read && "bg-primary/5",
      )}
      onClick={onRead}
    >
      <div className="flex items-start gap-2">
        {!n.is_read && (
          <span className="mt-1.5 size-2 shrink-0 rounded-full bg-primary" />
        )}
        <div className={cn("min-w-0", n.is_read && "pl-4")}>
          <p className="font-medium">{n.title}</p>
          {n.message && (
            <p className="mt-0.5 text-xs text-muted-foreground">{n.message}</p>
          )}
          <p className="mt-1 text-[11px] text-muted-foreground/70">
            {formatDateTime(n.created_at)}
          </p>
        </div>
      </div>
    </li>
  );
}
