import { Flame, Gauge, Recycle, Zap } from "lucide-react";
import { useState } from "react";

import { LiveCameraPanel } from "@/components/dashboard/LiveCameraPanel";
import { StatCard } from "@/components/dashboard/StatCard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/context/auth";
import { useEstimate } from "@/hooks/useLiveCamera";
import { formatKg } from "@/lib/utils";
import { CONTAINER_WEIGHT_KG } from "@/lib/requestStatus";

/**
 * Hotel-manager dashboard: an interactive estimator. The manager enters a
 * number of containers; the outputs (methane / energy / CO₂ / quality) are
 * computed live from that quantity and the CURRENT camera composition. Plus the
 * live camera panel. No request history / status tiles / rankings here.
 */
export function HotelManagerDashboard() {
  const { user } = useAuth();
  const [containers, setContainers] = useState(3);

  const est = useEstimate(containers);
  const e = est.data;
  const kwh = (v: number) =>
    `${v.toLocaleString(undefined, { maximumFractionDigits: 0 })} kWh`;

  const metrics = [
    {
      label: "Est. Methane",
      value: e ? `${e.estimated_methane_m3.toFixed(0)} m³` : "—",
      icon: Flame,
      hint: "at current purity",
    },
    {
      label: "Est. Energy",
      value: e ? kwh(e.estimated_energy_kwh) : "—",
      icon: Zap,
      hint: "from biogas",
    },
    {
      label: "CO₂ Saved",
      value: formatKg(e?.estimated_co2_kg),
      icon: Recycle,
      hint: "estimated",
    },
    {
      label: "Avg. Quality",
      value: e?.quality_score != null ? e.quality_score.toFixed(0) : "—",
      icon: Gauge,
      hint: "from camera",
    },
  ];

  const weightKg = containers > 0 ? containers * CONTAINER_WEIGHT_KG : 0;

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">
          Welcome back{user ? `, ${user.full_name.split(" ")[0]}` : ""}
        </h1>
        <p className="text-muted-foreground">
          Estimate your waste-to-energy output from the live camera.
        </p>
      </div>

      <LiveCameraPanel />

      {/* Declared waste input */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Declared waste</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-4">
            <label className="text-sm text-muted-foreground">
              Number of containers
              <Input
                type="number"
                min={1}
                step={1}
                value={containers}
                onChange={(ev) => setContainers(Math.max(0, Number(ev.target.value) || 0))}
                className="mt-1 w-40"
              />
            </label>
            <div className="pb-1 text-sm text-muted-foreground">
              ≈ <span className="font-semibold text-foreground">{formatKg(weightKg)}</span>{" "}
              · {CONTAINER_WEIGHT_KG} kg per container
            </div>
          </div>
          {est.isError && (
            <p className="mt-3 text-sm text-muted-foreground">
              No live camera is linked to your hotel yet — estimates are unavailable.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Computed metrics */}
      <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {metrics.map((m) => (
          <StatCard key={m.label} {...m} loading={est.isLoading && !e} />
        ))}
      </section>
    </div>
  );
}
