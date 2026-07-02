import { Loader2, Pencil, Plus, Sparkles, Trash2 } from "lucide-react";
import { useState } from "react";

import { CollectionForm } from "@/components/collections/CollectionForm";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { PageToolbar } from "@/components/common/PageToolbar";
import { Pagination } from "@/components/common/Pagination";
import { RoleGate } from "@/components/common/RoleGate";
import { TableState } from "@/components/common/TableState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useCollections,
  useCreateCollection,
  useDeleteCollection,
  usePredictCollection,
  useUpdateCollection,
} from "@/hooks/useCollections";
import { useToast } from "@/context/toast";
import { useHasRole } from "@/hooks/useHasRole";
import { messageFromError } from "@/lib/errors";
import { formatDateTime, formatKg } from "@/lib/utils";
import type { Prediction, WasteCollection, WasteCollectionCreate } from "@/types";

export function Collections() {
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<WasteCollection | null>(null);
  const [deleting, setDeleting] = useState<WasteCollection | null>(null);
  const [predicting, setPredicting] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [predictError, setPredictError] = useState<string | null>(null);

  const toast = useToast();
  const canEdit = useHasRole("admin", "operator");

  const query = useCollections({ page, sort: "-collected_at" });
  const createMut = useCreateCollection();
  const updateMut = useUpdateCollection();
  const deleteMut = useDeleteCollection();
  const predictMut = usePredictCollection();

  const collections = query.data?.items ?? [];
  const colSpan = 5 + (canEdit ? 1 : 0);

  async function submitForm(payload: WasteCollectionCreate) {
    if (editing) {
      const { hotel_id: _hotel, ...rest } = payload;
      void _hotel;
      await updateMut.mutateAsync({ id: editing.id, payload: rest });
      toast.success("Collection updated.");
    } else {
      await createMut.mutateAsync(payload);
      toast.success("Collection recorded.");
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    try {
      await deleteMut.mutateAsync(deleting.id);
      toast.success("Collection deleted.");
      setDeleting(null);
    } catch (error) {
      toast.error(messageFromError(error, "Could not delete collection."));
    }
  }

  async function runPredict(id: string) {
    setPredicting(id);
    setPredictError(null);
    try {
      const result = await predictMut.mutateAsync(id);
      setPrediction(result);
    } catch (error) {
      setPredictError(messageFromError(error, "Prediction failed."));
      setPrediction(null);
    } finally {
      setPredicting(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageToolbar
        title="Collections"
        description="Waste collection records and AI energy predictions."
      >
        <RoleGate roles={["admin", "operator"]}>
          <Button
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            <Plus />
            Record collection
          </Button>
        </RoleGate>
      </PageToolbar>

      <Card className="p-2">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Collected</TableHead>
              <TableHead>Organic</TableHead>
              <TableHead>Non-organic</TableHead>
              <TableHead>Total</TableHead>
              <TableHead>Organic %</TableHead>
              {canEdit && <TableHead className="text-right">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableState
              colSpan={colSpan}
              isLoading={query.isLoading}
              isError={query.isError}
              isEmpty={collections.length === 0}
              emptyLabel="No collections recorded."
              onRetry={() => query.refetch()}
            />
            {!query.isLoading &&
              !query.isError &&
              collections.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-medium">
                    {formatDateTime(c.collected_at)}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {formatKg(c.organic_weight_kg)}
                  </TableCell>
                  <TableCell className="tabular-nums">
                    {formatKg(c.non_organic_weight_kg)}
                  </TableCell>
                  <TableCell className="tabular-nums font-medium">
                    {formatKg(c.total_weight_kg)}
                  </TableCell>
                  <TableCell>
                    {c.organic_percentage != null ? (
                      <Badge variant="secondary">
                        {c.organic_percentage.toFixed(0)}%
                      </Badge>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  {canEdit && (
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => runPredict(c.id)}
                          disabled={predicting === c.id}
                        >
                          {predicting === c.id ? (
                            <Loader2 className="animate-spin" />
                          ) : (
                            <Sparkles />
                          )}
                          Predict
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => {
                            setEditing(c);
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
                            onClick={() => setDeleting(c)}
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
        <CollectionForm
          open={formOpen}
          onClose={() => setFormOpen(false)}
          collection={editing}
          onSubmit={submitForm}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title="Delete collection"
        description="Permanently delete this collection record? This cannot be undone."
        confirmLabel="Delete"
        destructive
        loading={deleteMut.isPending}
      />

      {/* Prediction result */}
      <Dialog
        open={!!prediction || !!predictError}
        onClose={() => {
          setPrediction(null);
          setPredictError(null);
        }}
        title="AI energy prediction"
        description="Estimated from the collection's waste composition."
      >
        {predictError ? (
          <p className="text-sm text-destructive">{predictError}</p>
        ) : prediction?.status === "failed" ? (
          <p className="text-sm text-destructive">
            {prediction.error_message ?? "The prediction service returned an error."}
          </p>
        ) : prediction ? (
          <div className="grid grid-cols-3 gap-4">
            <PredictionStat label="Energy" value={`${prediction.predicted_energy_kwh?.toFixed(0) ?? "—"} kWh`} />
            <PredictionStat label="Biogas" value={`${prediction.predicted_biogas_m3?.toFixed(0) ?? "—"} m³`} />
            <PredictionStat label="CO₂ saved" value={formatKg(prediction.co2_saved_kg)} />
          </div>
        ) : null}
      </Dialog>
    </div>
  );
}

function PredictionStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border p-3 text-center">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-bold tabular-nums">{value}</p>
    </div>
  );
}
