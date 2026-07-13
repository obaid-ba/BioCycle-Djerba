import { Card, CardContent } from "@/components/ui/card";
import { REQUEST_STATUS_META } from "@/lib/requestStatus";
import type { RequestStatus, RequestStats } from "@/types";

// Display order across the lifecycle.
const ORDER: RequestStatus[] = [
  "pending",
  "accepted",
  "on_the_way",
  "collected",
  "completed",
  "rejected",
];

const DOT: Record<string, string> = {
  default: "bg-primary",
  secondary: "bg-secondary-foreground/40",
  success: "bg-success",
  warning: "bg-warning",
  destructive: "bg-destructive",
  outline: "bg-muted-foreground",
};

/** Small tiles: one per lifecycle status with its live count. */
export function RequestStatusTiles({
  stats,
  loading,
}: {
  stats?: RequestStats;
  loading?: boolean;
}) {
  return (
    <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {ORDER.map((status) => {
        const meta = REQUEST_STATUS_META[status];
        return (
          <Card key={status}>
            <CardContent className="py-4">
              <div className="flex items-center gap-1.5">
                <span className={`size-2 rounded-full ${DOT[meta.variant]}`} />
                <span className="text-xs text-muted-foreground">{meta.label}</span>
              </div>
              {loading ? (
                <div className="mt-1 h-7 w-10 animate-pulse rounded bg-muted" />
              ) : (
                <div className="mt-1 text-2xl font-bold tabular-nums">
                  {stats?.status_counts[status] ?? 0}
                </div>
              )}
            </CardContent>
          </Card>
        );
      })}
    </section>
  );
}
