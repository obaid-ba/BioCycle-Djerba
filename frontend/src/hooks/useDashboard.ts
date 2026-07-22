import { useQuery } from "@tanstack/react-query";

import {
  getDashboardStats,
  getHotelRanking,
  getOperatorRanking,
  getPuritySplit,
  getRequestStats,
  getRequestsTimeseries,
  getTimeseries,
  getWasteDistribution,
} from "@/services/analytics";
import type { TimeseriesGranularity } from "@/types";

/** KPIs + system status. Polls so the live AI/MQTT/WS status stays fresh. */
export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard", "stats"],
    queryFn: getDashboardStats,
    refetchInterval: 30_000,
  });
}

export function useWasteDistribution() {
  return useQuery({
    queryKey: ["analytics", "waste-distribution"],
    queryFn: getWasteDistribution,
  });
}

export function useTimeseries(granularity: TimeseriesGranularity) {
  return useQuery({
    queryKey: ["analytics", "timeseries", granularity],
    queryFn: () => getTimeseries(granularity),
  });
}

/** Feedstock quality split, derived from AI purity scores. */
export function usePuritySplit() {
  return useQuery({
    queryKey: ["analytics", "purity-split"],
    queryFn: getPuritySplit,
  });
}

/** Request-based trend — replaces the legacy waste_collections timeseries. */
export function useRequestsTimeseries(granularity: TimeseriesGranularity) {
  return useQuery({
    queryKey: ["analytics", "requests-timeseries", granularity],
    queryFn: () => getRequestsTimeseries(granularity),
  });
}

/** Request-centric KPIs — the current product's dashboard numbers. */
export function useRequestStats() {
  return useQuery({
    queryKey: ["dashboard", "request-stats"],
    queryFn: getRequestStats,
    refetchInterval: 30_000,
  });
}

export function useHotelRanking(limit = 10) {
  return useQuery({
    queryKey: ["analytics", "hotel-ranking", limit],
    queryFn: () => getHotelRanking(limit),
  });
}

/** Admin-only; enable the query only when the caller passes enabled. */
export function useOperatorRanking(limit = 10, enabled = true) {
  return useQuery({
    queryKey: ["analytics", "operator-ranking", limit],
    queryFn: () => getOperatorRanking(limit),
    enabled,
  });
}
