import { Check, CheckCheck, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { AlertForm } from "@/components/alerts/AlertForm";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { PageToolbar } from "@/components/common/PageToolbar";
import { Pagination } from "@/components/common/Pagination";
import { RoleGate } from "@/components/common/RoleGate";
import { TableState } from "@/components/common/TableState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import {
  useAcknowledgeAlert,
  useAlerts,
  useCreateAlert,
  useDeleteAlert,
  useResolveAlert,
} from "@/hooks/useAlerts";
import { useHasRole } from "@/hooks/useHasRole";
import { formatDateTime } from "@/lib/utils";
import {
  alertSeverityVariant,
  alertStatusVariant,
  humanize,
} from "@/lib/statusBadge";
import type { Alert, AlertCreate, AlertSeverity, AlertStatus } from "@/types";

export function Alerts() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<AlertStatus | "">("");
  const [severity, setSeverity] = useState<AlertSeverity | "">("");
  const [formOpen, setFormOpen] = useState(false);
  const [deleting, setDeleting] = useState<Alert | null>(null);

  const canAct = useHasRole("admin", "operator");

  const query = useAlerts({
    page,
    status: status || undefined,
    severity: severity || undefined,
    sort: "-created_at",
  });
  const createMut = useCreateAlert();
  const ackMut = useAcknowledgeAlert();
  const resolveMut = useResolveAlert();
  const deleteMut = useDeleteAlert();

  const alerts = query.data?.items ?? [];
  const colSpan = 5 + (canAct ? 1 : 0);

  async function submitForm(payload: AlertCreate) {
    await createMut.mutateAsync(payload);
  }

  async function confirmDelete() {
    if (!deleting) return;
    await deleteMut.mutateAsync(deleting.id);
    setDeleting(null);
  }

  return (
    <div className="space-y-6">
      <PageToolbar
        title="Alerts"
        description="Operational alerts for full bins, low batteries, and system events."
      >
        <Select
          className="w-36"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as AlertStatus | "");
            setPage(1);
          }}
        >
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
        </Select>
        <Select
          className="w-36"
          value={severity}
          onChange={(e) => {
            setSeverity(e.target.value as AlertSeverity | "");
            setPage(1);
          }}
        >
          <option value="">All severities</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
        </Select>
        <RoleGate roles={["admin", "operator"]}>
          <Button onClick={() => setFormOpen(true)}>
            <Plus />
            Raise alert
          </Button>
        </RoleGate>
      </PageToolbar>

      <Card className="p-2">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Title</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Raised</TableHead>
              {canAct && <TableHead className="text-right">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableState
              colSpan={colSpan}
              isLoading={query.isLoading}
              isError={query.isError}
              isEmpty={alerts.length === 0}
              emptyLabel="No alerts."
              onRetry={() => query.refetch()}
            />
            {!query.isLoading &&
              !query.isError &&
              alerts.map((alert) => (
                <TableRow key={alert.id}>
                  <TableCell className="font-medium">
                    {alert.title}
                    {alert.message && (
                      <p className="text-xs font-normal text-muted-foreground">
                        {alert.message}
                      </p>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {humanize(alert.type)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={alertSeverityVariant[alert.severity]}>
                      {humanize(alert.severity)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={alertStatusVariant[alert.status]}>
                      {humanize(alert.status)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDateTime(alert.created_at)}
                  </TableCell>
                  {canAct && (
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        {alert.status === "open" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => ackMut.mutate(alert.id)}
                            disabled={ackMut.isPending}
                          >
                            <Check />
                            Ack
                          </Button>
                        )}
                        {alert.status !== "resolved" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => resolveMut.mutate(alert.id)}
                            disabled={resolveMut.isPending}
                          >
                            <CheckCheck />
                            Resolve
                          </Button>
                        )}
                        <RoleGate roles={["admin"]}>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleting(alert)}
                            aria-label="Delete"
                          >
                            <Trash2 className="text-destructive" />
                          </Button>
                        </RoleGate>
                      </div>
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

      {formOpen && (
        <AlertForm
          open={formOpen}
          onClose={() => setFormOpen(false)}
          onSubmit={submitForm}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title="Delete alert"
        description={`Permanently delete "${deleting?.title}"? This cannot be undone.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMut.isPending}
      />
    </div>
  );
}
