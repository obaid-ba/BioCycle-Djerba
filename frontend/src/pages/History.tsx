import { ImageIcon } from "lucide-react";
import { useState } from "react";

import { RequestDetailDialog } from "@/components/requests/RequestDetailDialog";
import { RequestStatusBadge } from "@/components/requests/RequestStatusBadge";
import { PageToolbar } from "@/components/common/PageToolbar";
import { Pagination } from "@/components/common/Pagination";
import { TableState } from "@/components/common/TableState";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
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
import type { CollectionRequest } from "@/types";

/**
 * Hotel-manager History: finished requests (completed / rejected). These leave
 * the active Requests page once the operator closes them out.
 */
export function History() {
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<CollectionRequest | null>(null);

  const query = useRequests({ page, terminal: true });
  const requests = query.data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageToolbar
        title="History"
        description="Your completed and rejected requests."
      />

      <Card className="p-2">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Created</TableHead>
              <TableHead>Declared</TableHead>
              <TableHead>Collected</TableHead>
              <TableHead>AI quality</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Details</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableState
              colSpan={6}
              isLoading={query.isLoading}
              isError={query.isError}
              isEmpty={requests.length === 0}
              emptyLabel="No finished requests yet."
              onRetry={() => query.refetch()}
            />
            {!query.isLoading &&
              !query.isError &&
              requests.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">
                    {formatDateTime(r.created_at)}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    <div>
                      {r.declared_containers}{" "}
                      {r.declared_containers === 1 ? "container" : "containers"}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatKg(r.declared_weight_kg)}
                    </div>
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {r.collected_weight_kg != null
                      ? formatKg(r.collected_weight_kg)
                      : "—"}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {r.ai_quality_score != null ? r.ai_quality_score.toFixed(0) : "—"}
                  </TableCell>
                  <TableCell>
                    <RequestStatusBadge status={r.status} />
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => setSelected(r)}>
                      <ImageIcon />
                      View
                    </Button>
                  </TableCell>
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

      {selected && (
        <RequestDetailDialog
          open={!!selected}
          request={selected}
          canEditPhotos={false}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
