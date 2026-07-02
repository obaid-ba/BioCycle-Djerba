import { Battery, Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { PageToolbar } from "@/components/common/PageToolbar";
import { Pagination } from "@/components/common/Pagination";
import { RoleGate } from "@/components/common/RoleGate";
import { TableState } from "@/components/common/TableState";
import { BinForm } from "@/components/bins/BinForm";
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
  useBins,
  useCreateBin,
  useDeleteBin,
  useUpdateBin,
} from "@/hooks/useBins";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useHasRole } from "@/hooks/useHasRole";
import { binStatusVariant, humanize } from "@/lib/statusBadge";
import type { BinStatus, SmartBin, SmartBinCreate } from "@/types";

function LevelBar({ value }: { value: number | null }) {
  if (value == null) return <span className="text-muted-foreground">—</span>;
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-primary"
          style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-muted-foreground">
        {value.toFixed(0)}%
      </span>
    </div>
  );
}

export function Bins() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<BinStatus | "">("");
  const debouncedSearch = useDebouncedValue(search, 300);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<SmartBin | null>(null);
  const [deleting, setDeleting] = useState<SmartBin | null>(null);

  const canEdit = useHasRole("admin", "operator");

  const query = useBins({
    page,
    search: debouncedSearch || undefined,
    status: status || undefined,
    sort: "code",
  });
  const createMut = useCreateBin();
  const updateMut = useUpdateBin();
  const deleteMut = useDeleteBin();

  const bins = query.data?.items ?? [];
  const colSpan = 5 + (canEdit ? 1 : 0);

  async function submitForm(payload: SmartBinCreate) {
    if (editing) await updateMut.mutateAsync({ id: editing.id, payload });
    else await createMut.mutateAsync(payload);
  }

  async function confirmDelete() {
    if (!deleting) return;
    await deleteMut.mutateAsync(deleting.id);
    setDeleting(null);
  }

  return (
    <div className="space-y-6">
      <PageToolbar
        title="Smart Bins"
        description="Sensor-equipped bins reporting fill level, weight, and battery."
        search={search}
        onSearchChange={(v) => {
          setSearch(v);
          setPage(1);
        }}
        searchPlaceholder="Search code or name…"
      >
        <Select
          className="w-40"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as BinStatus | "");
            setPage(1);
          }}
        >
          <option value="">All statuses</option>
          <option value="online">Online</option>
          <option value="offline">Offline</option>
          <option value="maintenance">Maintenance</option>
        </Select>
        <RoleGate roles={["admin", "operator"]}>
          <Button
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            <Plus />
            Register bin
          </Button>
        </RoleGate>
      </PageToolbar>

      <Card className="p-2">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Code</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Fill</TableHead>
              <TableHead>Battery</TableHead>
              {canEdit && <TableHead className="text-right">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableState
              colSpan={colSpan}
              isLoading={query.isLoading}
              isError={query.isError}
              isEmpty={bins.length === 0}
              emptyLabel="No bins yet."
              onRetry={() => query.refetch()}
            />
            {!query.isLoading &&
              !query.isError &&
              bins.map((bin) => (
                <TableRow key={bin.id}>
                  <TableCell className="font-medium">
                    {bin.code}
                    {bin.name && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {bin.name}
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {humanize(bin.bin_type)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={binStatusVariant[bin.status]}>
                      {humanize(bin.status)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <LevelBar value={bin.fill_level} />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Battery className="size-3.5" />
                      {bin.battery_level != null
                        ? `${bin.battery_level.toFixed(0)}%`
                        : "—"}
                    </div>
                  </TableCell>
                  {canEdit && (
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => {
                            setEditing(bin);
                            setFormOpen(true);
                          }}
                          aria-label="Edit"
                        >
                          <Pencil />
                        </Button>
                        <RoleGate roles={["admin"]}>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleting(bin)}
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
        <BinForm
          open={formOpen}
          onClose={() => setFormOpen(false)}
          bin={editing}
          onSubmit={submitForm}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title="Delete smart bin"
        description={`Permanently delete bin "${deleting?.code}"? This cannot be undone.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMut.isPending}
      />
    </div>
  );
}
