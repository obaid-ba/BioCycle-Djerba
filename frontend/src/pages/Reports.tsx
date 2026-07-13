import { Download, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";

import { PageToolbar } from "@/components/common/PageToolbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/context/toast";
import { useReportSummary } from "@/hooks/useReports";
import { REQUEST_STATUS_META } from "@/lib/requestStatus";
import { messageFromError } from "@/lib/errors";
import { formatKg } from "@/lib/utils";
import { downloadRequestsCsv } from "@/services/reports";
import type { ReportFilters, RequestStatus } from "@/types";

/** ISO date (yyyy-mm-dd) N days ago / today, for the default period inputs. */
function isoDate(daysAgo = 0): string {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  return d.toISOString().slice(0, 10);
}

const STATUS_ORDER: RequestStatus[] = [
  "pending",
  "accepted",
  "on_the_way",
  "collected",
  "completed",
  "rejected",
];

export function Reports() {
  const [from, setFrom] = useState(isoDate(30));
  const [to, setTo] = useState(isoDate(0));
  const [exporting, setExporting] = useState(false);
  const toast = useToast();

  // Send the day range as full-day ISO bounds.
  const filters = useMemo<ReportFilters>(
    () => ({
      date_from: new Date(`${from}T00:00:00`).toISOString(),
      date_to: new Date(`${to}T23:59:59`).toISOString(),
    }),
    [from, to],
  );

  const summary = useReportSummary(filters);
  const s = summary.data;

  async function onExport() {
    setExporting(true);
    try {
      await downloadRequestsCsv(filters);
      toast.success("CSV exported.");
    } catch (error) {
      toast.error(messageFromError(error, "Export failed."));
    } finally {
      setExporting(false);
    }
  }

  const kpis = s
    ? [
        { label: "Requests", value: String(s.totals.requests) },
        { label: "Declared", value: formatKg(s.totals.declared_weight_kg) },
        { label: "Collected", value: formatKg(s.totals.collected_weight_kg) },
        { label: "Est. methane", value: `${s.totals.estimated_methane_m3.toFixed(0)} m³` },
        { label: "Est. energy", value: `${s.totals.estimated_energy_kwh.toFixed(0)} kWh` },
        { label: "CO₂ saved", value: formatKg(s.totals.estimated_co2_kg) },
        {
          label: "Avg. quality",
          value: s.avg_quality_score != null ? s.avg_quality_score.toFixed(0) : "—",
        },
        {
          label: "Acceptance",
          value: s.acceptance_rate != null ? `${s.acceptance_rate.toFixed(0)}%` : "—",
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      <PageToolbar
        title="Reports"
        description="Period summary and CSV export of collection requests."
      >
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-xs text-muted-foreground">
            From
            <Input
              type="date"
              value={from}
              max={to}
              onChange={(e) => setFrom(e.target.value)}
              className="mt-1 w-40"
            />
          </label>
          <label className="text-xs text-muted-foreground">
            To
            <Input
              type="date"
              value={to}
              min={from}
              max={isoDate(0)}
              onChange={(e) => setTo(e.target.value)}
              className="mt-1 w-40"
            />
          </label>
          <Button onClick={onExport} disabled={exporting}>
            {exporting ? <Loader2 className="animate-spin" /> : <Download />}
            Export CSV
          </Button>
        </div>
      </PageToolbar>

      {/* KPI totals */}
      <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {(kpis.length ? kpis : Array.from({ length: 8 }, (_, i) => ({ label: "", value: "", _i: i }))).map(
          (k, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {k.label || <span className="inline-block h-4 w-20 animate-pulse rounded bg-muted" />}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {summary.isLoading ? (
                  <div className="h-7 w-16 animate-pulse rounded bg-muted" />
                ) : (
                  <div className="text-2xl font-bold tabular-nums">{k.value}</div>
                )}
              </CardContent>
            </Card>
          ),
        )}
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Status breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">By status</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-1.5">
              {STATUS_ORDER.map((st) => (
                <li key={st} className="flex items-center justify-between text-sm">
                  <span>{REQUEST_STATUS_META[st].label}</span>
                  <span className="font-semibold tabular-nums">
                    {s?.status_counts[st] ?? 0}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        {/* Top hotels */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top hotels by methane</CardTitle>
          </CardHeader>
          <CardContent>
            {s && s.top_hotels.length > 0 ? (
              <ol className="space-y-1.5">
                {s.top_hotels.map((h, i) => (
                  <li
                    key={h.hotel_name}
                    className="flex items-center justify-between gap-2 text-sm"
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <span className="w-4 text-center font-semibold text-muted-foreground">
                        {i + 1}
                      </span>
                      <span className="truncate font-medium">{h.hotel_name}</span>
                    </span>
                    <span className="shrink-0 tabular-nums text-muted-foreground">
                      {h.request_count} req ·{" "}
                      <span className="font-semibold text-foreground">
                        {h.total_methane_m3.toFixed(0)} m³
                      </span>
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="py-4 text-center text-sm text-muted-foreground">
                No requests in this period.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
