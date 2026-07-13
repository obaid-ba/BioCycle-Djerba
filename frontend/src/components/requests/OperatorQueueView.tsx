import { useState } from "react";

import { RequestActions } from "@/components/requests/RequestActions";
import { RequestStatusBadge } from "@/components/requests/RequestStatusBadge";
import { PageToolbar } from "@/components/common/PageToolbar";
import { Pagination } from "@/components/common/Pagination";
import { TableState } from "@/components/common/TableState";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useRequests } from "@/hooks/useRequests";
import { formatDateTime, formatKg } from "@/lib/utils";
import type { RequestStatus } from "@/types";

const STATUS_OPTIONS: { value: "" | RequestStatus; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "accepted", label: "Accepted" },
  { value: "on_the_way", label: "On the way" },
  { value: "collected", label: "Collected" },
  { value: "completed", label: "Completed" },
  { value: "rejected", label: "Rejected" },
];

/**
 * Operator/admin view: the collection queue, priority-sorted by the backend
 * (highest AI priority first). Read-only for admins is fine — actions simply
 * post to the same operator endpoints.
 */
export function OperatorQueueView({ readOnly = false }: { readOnly?: boolean }) {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<"" | RequestStatus>("");

  const query = useRequests({
    page,
    status: status || undefined,
  });

  const requests = query.data?.items ?? [];
  const colSpan = readOnly ? 7 : 8;

  return (
    <div className="space-y-6">
      <PageToolbar
        title="Collection queue"
        description="Requests ranked by AI priority. Highest-value pickups first."
      >
        <Select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as "" | RequestStatus);
            setPage(1);
          }}
          className="w-44"
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
      </PageToolbar>

      <Card className="p-2">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Priority</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Declared</TableHead>
              <TableHead>Quality</TableHead>
              <TableHead>Purity</TableHead>
              <TableHead>Est. methane</TableHead>
              <TableHead>Status</TableHead>
              {!readOnly && <TableHead className="text-right">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableState
              colSpan={colSpan}
              isLoading={query.isLoading}
              isError={query.isError}
              isEmpty={requests.length === 0}
              emptyLabel="The queue is empty."
              onRetry={() => query.refetch()}
            />
            {!query.isLoading &&
              !query.isError &&
              requests.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>
                    {r.ai_priority_score != null ? (
                      <Badge variant="default" className="tabular-nums">
                        {r.ai_priority_score.toFixed(0)}
                      </Badge>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell className="whitespace-nowrap font-medium">
                    {formatDateTime(r.created_at)}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {formatKg(r.declared_weight_kg)}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {r.ai_quality_score != null ? r.ai_quality_score.toFixed(0) : "—"}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {r.ai_organic_purity != null
                      ? `${r.ai_organic_purity.toFixed(0)}%`
                      : "—"}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {r.ai_estimated_methane_m3 != null
                      ? `${r.ai_estimated_methane_m3.toFixed(0)} m³`
                      : "—"}
                  </TableCell>
                  <TableCell>
                    <RequestStatusBadge status={r.status} />
                  </TableCell>
                  {!readOnly && (
                    <TableCell className="text-right">
                      <RequestActions request={r} />
                    </TableCell>
                  )}
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>

      {query.data && (
        <Pagination
          page={query.data.page}
          pages={query.data.pages}
          total={query.data.total}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
