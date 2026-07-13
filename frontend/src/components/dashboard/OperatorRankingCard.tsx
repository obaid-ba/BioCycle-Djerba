import { Award } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useOperatorRanking } from "@/hooks/useDashboard";

/** Leaderboard of operators by requests handled (admin-only view). */
export function OperatorRankingCard() {
  const { data = [], isLoading } = useOperatorRanking(5);

  return (
    <Card>
      <CardHeader className="flex-row items-center gap-2 space-y-0">
        <Award className="size-4 text-primary" />
        <CardTitle className="text-base">Top operators</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-8 animate-pulse rounded bg-muted" />
            ))}
          </div>
        ) : data.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            No decisions recorded yet.
          </p>
        ) : (
          <ol className="space-y-1">
            {data.map((row, i) => (
              <li
                key={row.operator_id}
                className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 text-sm odd:bg-muted/40"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span className="w-4 text-center font-semibold text-muted-foreground">
                    {i + 1}
                  </span>
                  <span className="truncate font-medium">{row.operator_name}</span>
                </span>
                <span className="flex shrink-0 items-center gap-3 tabular-nums text-muted-foreground">
                  <span>{row.completed_count} done</span>
                  <span className="font-semibold text-foreground">
                    {row.handled_count} handled
                  </span>
                </span>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
