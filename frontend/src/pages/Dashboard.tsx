import {
  AlertTriangle,
  Bell,
  Building2,
  Flame,
  Leaf,
  Recycle,
  Truck,
  Zap,
} from "lucide-react";
import { useState } from "react";

import { CollectionsTrendChart } from "@/components/dashboard/CollectionsTrendChart";
import { StatCard } from "@/components/dashboard/StatCard";
import { SystemStatusBar } from "@/components/dashboard/SystemStatusBar";
import { WasteDistributionChart } from "@/components/dashboard/WasteDistributionChart";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/context/auth";
import {
  useDashboardStats,
  useTimeseries,
  useWasteDistribution,
} from "@/hooks/useDashboard";
import { formatKg } from "@/lib/utils";
import type { TimeseriesGranularity } from "@/types";

export function Dashboard() {
  const { user } = useAuth();
  const [granularity, setGranularity] = useState<TimeseriesGranularity>("day");

  const stats = useDashboardStats();
  const distribution = useWasteDistribution();
  const timeseries = useTimeseries(granularity);

  const s = stats.data;
  const kwh = (v: number) => `${v.toLocaleString(undefined, { maximumFractionDigits: 0 })} kWh`;

  const kpis = [
    {
      label: "Today's Collections",
      value: s ? String(s.today_collections) : "—",
      icon: Truck,
    },
    {
      label: "Organic Waste",
      value: formatKg(s?.organic_waste_kg),
      icon: Leaf,
      hint: "today",
    },
    {
      label: "Predicted Energy",
      value: s ? kwh(s.predicted_energy_kwh) : "—",
      icon: Zap,
      hint: "from biogas",
    },
    {
      label: "Biogas",
      value: s ? `${s.predicted_biogas_m3.toFixed(0)} m³` : "—",
      icon: Flame,
      hint: "estimated",
    },
    {
      label: "CO₂ Saved",
      value: formatKg(s?.co2_saved_kg),
      icon: Recycle,
      hint: "today",
    },
    {
      label: "Hotels Connected",
      value: s ? String(s.hotels_connected) : "—",
      icon: Building2,
    },
    {
      label: "Open Alerts",
      value: s ? String(s.open_alerts) : "—",
      icon: Bell,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">
          Welcome back{user ? `, ${user.full_name.split(" ")[0]}` : ""}
        </h1>
        <p className="text-muted-foreground">
          Live overview of waste-to-energy operations across Djerba.
        </p>
      </div>

      {stats.isError ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <AlertTriangle className="size-6 text-warning" />
            <p className="text-sm text-muted-foreground">
              Could not load dashboard data.
            </p>
            <Button variant="outline" size="sm" onClick={() => stats.refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <SystemStatusBar system={s?.system} loading={stats.isLoading} />

          <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {kpis.map((kpi) => (
              <StatCard key={kpi.label} {...kpi} loading={stats.isLoading} />
            ))}
          </section>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <CollectionsTrendChart
              data={timeseries.data}
              loading={timeseries.isLoading}
              granularity={granularity}
              onGranularityChange={setGranularity}
            />
            <WasteDistributionChart
              data={distribution.data}
              loading={distribution.isLoading}
            />
          </div>
        </>
      )}
    </div>
  );
}
