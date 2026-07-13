import { Plus } from "lucide-react";
import { useState } from "react";

import { NewRequestForm } from "@/components/requests/NewRequestForm";
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
import { useCreateRequest, useRequests } from "@/hooks/useRequests";
import { useToast } from "@/context/toast";
import { messageFromError } from "@/lib/errors";
import { formatDateTime, formatKg } from "@/lib/utils";
import type { CollectionRequestCreate } from "@/types";

/** Hotel-manager view: their own requests, newest first, with a create action. */
export function HotelRequestsView() {
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);

  const toast = useToast();
  const query = useRequests({ page });
  const createMut = useCreateRequest();

  const requests = query.data?.items ?? [];

  async function submit(payload: CollectionRequestCreate) {
    try {
      await createMut.mutateAsync({ payload });
      toast.success("Request submitted. Our AI is scoring it now.");
    } catch (error) {
      // Re-throw so the form surfaces the message inline.
      toast.error(messageFromError(error, "Could not submit the request."));
      throw error;
    }
  }

  return (
    <div className="space-y-6">
      <PageToolbar
        title="Requests"
        description="Declare organic waste for collection and track each request."
      >
        <Button onClick={() => setFormOpen(true)}>
          <Plus />
          New request
        </Button>
      </PageToolbar>

      <Card className="p-2">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Created</TableHead>
              <TableHead>Declared</TableHead>
              <TableHead>AI quality</TableHead>
              <TableHead>Est. methane</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableState
              colSpan={5}
              isLoading={query.isLoading}
              isError={query.isError}
              isEmpty={requests.length === 0}
              emptyLabel="No requests yet. Create your first one."
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
                    {formatKg(r.declared_weight_kg)}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {r.ai_quality_score != null ? r.ai_quality_score.toFixed(0) : "—"}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {r.ai_estimated_methane_m3 != null
                      ? `${r.ai_estimated_methane_m3.toFixed(0)} m³`
                      : "—"}
                  </TableCell>
                  <TableCell>
                    <RequestStatusBadge status={r.status} />
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

      {formOpen && (
        <NewRequestForm
          open={formOpen}
          onClose={() => setFormOpen(false)}
          onSubmit={submit}
        />
      )}
    </div>
  );
}
