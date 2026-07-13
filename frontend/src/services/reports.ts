import { api } from "@/services/api";
import type { ReportFilters, ReportSummary } from "@/types";

export async function getReportSummary(
  filters: ReportFilters,
): Promise<ReportSummary> {
  const { data } = await api.get<ReportSummary>("/reports/summary", {
    params: filters,
  });
  return data;
}

/**
 * Download the CSV export. The endpoint requires a JWT, so we pull the bytes
 * through the authenticated client and trigger a browser download from a blob
 * (a bare <a href> can't send the token).
 */
export async function downloadRequestsCsv(filters: ReportFilters): Promise<void> {
  const resp = await api.get<Blob>("/reports/requests.csv", {
    params: filters,
    responseType: "blob",
  });
  const url = URL.createObjectURL(resp.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = "collection_requests.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
