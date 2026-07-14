import { Camera, Leaf, Recycle } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLiveCamera } from "@/hooks/useLiveCamera";
import { cn } from "@/lib/utils";

/**
 * Real-time camera feed from Firebase: what the vision model is detecting right
 * now (organic vs recyclable split, confidence, camera status). Renders nothing
 * when the user has no linked camera (the query 404s) — so it's safe to place on
 * every dashboard.
 */
export function LiveCameraPanel() {
  const { data, isError, isLoading } = useLiveCamera();

  // No linked camera / feed unavailable → hide the panel entirely.
  if (isError || (!data && !isLoading)) return null;

  const online = data?.camera === "online";
  const organic = data?.organic_count ?? 0;
  const recyclable = data?.recyclable_count ?? 0;
  const total = data?.total_detections ?? 0;
  const purity = data?.organic_purity;
  const organicPct = total > 0 ? (organic / total) * 100 : 0;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <Camera className="size-4 text-primary" />
          Live camera
        </CardTitle>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span
            className={cn(
              "size-2 rounded-full",
              online ? "bg-success" : "bg-muted-foreground/40",
            )}
          />
          {online ? "Online" : "Offline"}
          {data?.resolution ? ` · ${data.resolution}` : ""}
          {data?.fps ? ` · ${data.fps} fps` : ""}
        </span>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading && !data ? (
          <div className="h-24 animate-pulse rounded-lg bg-muted" />
        ) : (
          <>
            {/* Organic vs recyclable split bar */}
            <div>
              <div className="mb-1.5 flex items-center justify-between text-sm">
                <span className="flex items-center gap-1.5 text-success">
                  <Leaf className="size-3.5" /> Organic {organic}
                </span>
                <span className="flex items-center gap-1.5 text-warning">
                  Recyclable {recyclable} <Recycle className="size-3.5" />
                </span>
              </div>
              <div className="flex h-3 overflow-hidden rounded-full bg-warning/25">
                <div
                  className="h-full bg-success transition-all"
                  style={{ width: `${organicPct}%` }}
                  aria-label={`${organicPct.toFixed(0)}% organic`}
                />
              </div>
            </div>

            {/* Headline stats */}
            <div className="grid grid-cols-3 gap-3 text-center">
              <Stat
                label="Organic purity"
                value={purity != null ? `${purity.toFixed(1)}%` : "—"}
              />
              <Stat
                label="Confidence"
                value={
                  data?.avg_confidence != null
                    ? `${(data.avg_confidence * 100).toFixed(0)}%`
                    : "—"
                }
              />
              <Stat label="Detected" value={String(total)} />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border p-2.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-lg font-bold tabular-nums">{value}</p>
    </div>
  );
}
