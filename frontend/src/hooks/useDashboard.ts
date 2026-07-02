import { useQuery } from "@tanstack/react-query";

import {
  getDashboardStats,
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
