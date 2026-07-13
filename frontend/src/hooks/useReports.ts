import { useQuery } from "@tanstack/react-query";

import { getReportSummary } from "@/services/reports";
import type { ReportFilters } from "@/types";

export function useReportSummary(filters: ReportFilters) {
  return useQuery({
    queryKey: ["reports", "summary", filters],
    queryFn: () => getReportSummary(filters),
  });
}
