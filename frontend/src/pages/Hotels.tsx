import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { PageToolbar } from "@/components/common/PageToolbar";
import { Pagination } from "@/components/common/Pagination";
import { RoleGate } from "@/components/common/RoleGate";
import { TableState } from "@/components/common/TableState";
import { HotelForm } from "@/components/hotels/HotelForm";
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
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useHasRole } from "@/hooks/useHasRole";
import {
  useCreateHotel,
  useDeleteHotel,
  useHotels,
  useUpdateHotel,
} from "@/hooks/useHotels";
import { hotelStatusVariant, humanize } from "@/lib/statusBadge";
import type { Hotel, HotelCreate, HotelStatus } from "@/types";

export function Hotels() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<HotelStatus | "">("");
  const debouncedSearch = useDebouncedValue(search, 300);

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Hotel | null>(null);
  const [deleting, setDeleting] = useState<Hotel | null>(null);

  const canEdit = useHasRole("admin", "operator");

  const query = useHotels({
    page,
    search: debouncedSearch || undefined,
    status: status || undefined,
    sort: "name",
  });
  const createMut = useCreateHotel();
  const updateMut = useUpdateHotel();
  const deleteMut = useDeleteHotel();

  const hotels = query.data?.items ?? [];
  const actionCols = canEdit ? 1 : 0;
  const colSpan = 4 + actionCols;

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }
  function openEdit(hotel: Hotel) {
    setEditing(hotel);
    setFormOpen(true);
  }

  async function submitForm(payload: HotelCreate) {
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
        title="Hotels"
        description="Partner hotels connected to the Djerba biomethanization plant."
        search={search}
        onSearchChange={(v) => {
          setSearch(v);
          setPage(1);
        }}
        searchPlaceholder="Search name or city…"
      >
        <Select
          className="w-40"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as HotelStatus | "");
            setPage(1);
          }}
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="onboarding">Onboarding</option>
          <option value="inactive">Inactive</option>
        </Select>
        <RoleGate roles={["admin", "operator"]}>
          <Button onClick={openCreate}>
            <Plus />
            Add hotel
          </Button>
        </RoleGate>
      </PageToolbar>

      <Card className="p-2">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>City</TableHead>
              <TableHead>Rooms</TableHead>
              <TableHead>Status</TableHead>
              {canEdit && <TableHead className="text-right">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableState
              colSpan={colSpan}
              isLoading={query.isLoading}
              isError={query.isError}
              isEmpty={hotels.length === 0}
              emptyLabel="No hotels yet."
              onRetry={() => query.refetch()}
            />
            {!query.isLoading &&
              !query.isError &&
              hotels.map((hotel) => (
                <TableRow key={hotel.id}>
                  <TableCell className="font-medium">{hotel.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {hotel.city}, {hotel.country}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {hotel.number_of_rooms ?? "—"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={hotelStatusVariant[hotel.status]}>
                      {humanize(hotel.status)}
                    </Badge>
                  </TableCell>
                  {canEdit && (
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => openEdit(hotel)}
                          aria-label="Edit"
                        >
                          <Pencil />
                        </Button>
                        <RoleGate roles={["admin"]}>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleting(hotel)}
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
        <HotelForm
          open={formOpen}
          onClose={() => setFormOpen(false)}
          hotel={editing}
          onSubmit={submitForm}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title="Delete hotel"
        description={`Permanently delete "${deleting?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMut.isPending}
      />
    </div>
  );
}
