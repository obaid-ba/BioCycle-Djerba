import { api } from "@/services/api";
import type {
  DashboardStats,
  HotelRankingRow,
  OperatorRankingRow,
  RequestStats,
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

// ---- Request-centric analytics (current product source of truth) ----

/** GET /dashboard/request-stats — KPIs derived from collection requests. */
export async function getRequestStats(): Promise<RequestStats> {
  const { data } = await api.get<RequestStats>("/dashboard/request-stats");
  return data;
}

/** GET /analytics/hotel-ranking — top hotels by estimated methane. */
export async function getHotelRanking(limit = 10): Promise<HotelRankingRow[]> {
  const { data } = await api.get<HotelRankingRow[]>("/analytics/hotel-ranking", {
    params: { limit },
  });
  return data;
}

/** GET /analytics/operator-ranking — operators by requests handled (admin). */
export async function getOperatorRanking(limit = 10): Promise<OperatorRankingRow[]> {
  const { data } = await api.get<OperatorRankingRow[]>(
    "/analytics/operator-ranking",
    { params: { limit } },
  );
  return data;
}
