import { Bot, Radio, Wifi } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { SystemStatus } from "@/types";

/** Treat these string values (case-insensitive) as healthy. */
const HEALTHY = new Set(["ok", "up", "connected", "online", "healthy"]);

function toVariant(value: string): "success" | "warning" {
  return HEALTHY.has(value.toLowerCase()) ? "success" : "warning";
}

interface SystemStatusBarProps {
  system?: SystemStatus;
  loading?: boolean;
}

export function SystemStatusBar({ system, loading }: SystemStatusBarProps) {
  const items = system
    ? [
        { icon: Bot, label: "AI Service", value: system.ai },
        { icon: Radio, label: "MQTT", value: system.mqtt },
        {
          icon: Wifi,
          label: "WebSocket",
          value:
            system.websocket +
            (system.websocket_connections
              ? ` · ${system.websocket_connections}`
              : ""),
          rawValue: system.websocket,
        },
      ]
    : [];

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-x-6 gap-y-3 py-4">
        <span className="text-sm font-medium text-muted-foreground">
          System status
        </span>
        {loading && (
          <div className="h-5 w-64 animate-pulse rounded bg-muted" />
        )}
        {items.map(({ icon: Icon, label, value, rawValue }) => (
          <div key={label} className="flex items-center gap-2">
            <Icon className="size-4 text-muted-foreground" />
            <span className="text-sm">{label}</span>
            <Badge variant={toVariant(rawValue ?? value)}>{value}</Badge>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
