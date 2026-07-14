import {
  AlertTriangle,
  CheckCircle2,
  Flame,
  Gauge,
  Leaf,
  Recycle,
  Truck,
  Zap,
} from "lucide-react";
import { useState } from "react";

import { CollectionsTrendChart } from "@/components/dashboard/CollectionsTrendChart";
import { HotelRankingCard } from "@/components/dashboard/HotelRankingCard";
import { LiveCameraPanel } from "@/components/dashboard/LiveCameraPanel";
import { OperatorRankingCard } from "@/components/dashboard/OperatorRankingCard";
import { RequestStatusTiles } from "@/components/dashboard/RequestStatusTiles";
import { StatCard } from "@/components/dashboard/StatCard";
import { SystemStatusBar } from "@/components/dashboard/SystemStatusBar";
import { WasteDistributionChart } from "@/components/dashboard/WasteDistributionChart";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/context/auth";
import { useHasRole } from "@/hooks/useHasRole";
import {
  useDashboardStats,
  useRequestStats,
  useTimeseries,
  useWasteDistribution,
} from "@/hooks/useDashboard";
import { formatKg } from "@/lib/utils";
import type { TimeseriesGranularity } from "@/types";

export function Dashboard() {
  const { user } = useAuth();
  const isAdmin = useHasRole("admin");
  const [granularity, setGranularity] = useState<TimeseriesGranularity>("day");

  // Request-centric KPIs are the product's source of truth now.
  const reqStats = useRequestStats();
  // System status still comes from the legacy dashboard stats endpoint.
  const stats = useDashboardStats();
  const distribution = useWasteDistribution();
  const timeseries = useTimeseries(granularity);

  const rs = reqStats.data;
  const kwh = (v: number) =>
    `${v.toLocaleString(undefined, { maximumFractionDigits: 0 })} kWh`;

  const kpis = [
    {
      label: "Total Requests",
      value: rs ? String(rs.total_requests) : "—",
      icon: Truck,
    },
    {
      label: "Declared Waste",
      value: formatKg(rs?.declared_weight_kg),
      icon: Leaf,
      hint: "all requests",
    },
    {
      label: "Est. Methane",
      value: rs ? `${rs.estimated_methane_m3.toFixed(0)} m³` : "—",
      icon: Flame,
      hint: "AI estimate",
    },
    {
      label: "Est. Energy",
      value: rs ? kwh(rs.estimated_energy_kwh) : "—",
      icon: Zap,
      hint: "from biogas",
    },
    {
      label: "CO₂ Saved",
      value: formatKg(rs?.estimated_co2_kg),
      icon: Recycle,
      hint: "estimated",
    },
    {
      label: "Avg. Quality",
      value: rs?.avg_quality_score != null ? rs.avg_quality_score.toFixed(0) : "—",
      icon: Gauge,
      hint: "AI score",
    },
    {
      label: "Acceptance Rate",
      value: rs?.acceptance_rate != null ? `${rs.acceptance_rate.toFixed(0)}%` : "—",
      icon: CheckCircle2,
      hint: "of decided",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">
          Welcome back{user ? `, ${user.full_name.split(" ")[0]}` : ""}
        </h1>
        <p className="text-muted-foreground">
          Live overview of organic-waste collection across Djerba.
        </p>
      </div>

      {reqStats.isError ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <AlertTriangle className="size-6 text-warning" />
            <p className="text-sm text-muted-foreground">
              Could not load dashboard data.
            </p>
            <Button variant="outline" size="sm" onClick={() => reqStats.refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <SystemStatusBar system={stats.data?.system} loading={stats.isLoading} />

          {/* Live camera feed — self-hides when the user has no linked camera. */}
          <LiveCameraPanel />

          <RequestStatusTiles stats={rs} loading={reqStats.isLoading} />

          <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {kpis.map((kpi) => (
              <StatCard key={kpi.label} {...kpi} loading={reqStats.isLoading} />
            ))}
          </section>

          {/* Leaderboards */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <HotelRankingCard />
            {isAdmin && <OperatorRankingCard />}
          </div>

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
