import { api } from "@/services/api";
import type {
  DashboardStats,
  TimeseriesBucket,
  TimeseriesGranularity,
  WasteDistribution,
} from "@/types";

/** GET /dashboard/stats — today's KPIs plus live system status. */
export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>("/dashboard/stats");
  return data;
}

/** GET /analytics/waste-distribution — organic vs non-organic split. */
export async function getWasteDistribution(): Promise<WasteDistribution> {
  const { data } = await api.get<WasteDistribution>(
    "/analytics/waste-distribution",
  );
  return data;
}

/** GET /analytics/timeseries — bucketed collection totals. */
export async function getTimeseries(
  granularity: TimeseriesGranularity,
): Promise<TimeseriesBucket[]> {
  const { data } = await api.get<TimeseriesBucket[]>("/analytics/timeseries", {
    params: { granularity },
  });
  return data;
}
