import { ImagePlus, Loader2 } from "lucide-react";
import { useRef, useState } from "react";

import { PhotoThumbnail } from "@/components/requests/PhotoThumbnail";
import { RequestStatusBadge } from "@/components/requests/RequestStatusBadge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { useDeletePhoto, useUploadPhotos } from "@/hooks/useRequests";
import { useToast } from "@/context/toast";
import { messageFromError } from "@/lib/errors";
import { isTerminal } from "@/lib/requestStatus";
import { formatDateTime, formatKg } from "@/lib/utils";
import type { CollectionRequest } from "@/types";

const ACCEPT = "image/jpeg,image/png,image/webp";
const MAX_PHOTOS = 5;

interface RequestDetailDialogProps {
  open: boolean;
  request: CollectionRequest;
  /** Whether the current user may add/remove photos (hotel owner, non-terminal). */
  canEditPhotos: boolean;
  onClose: () => void;
}

export function RequestDetailDialog({
  open,
  request,
  canEditPhotos,
  onClose,
}: RequestDetailDialogProps) {
  const toast = useToast();
  const uploadMut = useUploadPhotos();
  const deleteMut = useDeletePhoto();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const photos = request.photos;
  const editable = canEditPhotos && !isTerminal(request.status);
  const atLimit = photos.length >= MAX_PHOTOS;

  async function onFilesPicked(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    e.target.value = ""; // allow re-picking the same file
    if (files.length === 0) return;

    if (photos.length + files.length > MAX_PHOTOS) {
      toast.error(`A request can have at most ${MAX_PHOTOS} photos.`);
      return;
    }
    try {
      await uploadMut.mutateAsync({ id: request.id, files });
      toast.success(files.length > 1 ? "Photos uploaded." : "Photo uploaded.");
    } catch (error) {
      toast.error(messageFromError(error, "Upload failed."));
    }
  }

  async function onDelete(photoId: string) {
    setDeletingId(photoId);
    try {
      await deleteMut.mutateAsync({ requestId: request.id, photoId });
      toast.success("Photo removed.");
    } catch (error) {
      toast.error(messageFromError(error, "Could not delete the photo."));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Request details"
      description={`Created ${formatDateTime(request.created_at)}`}
    >
      <div className="space-y-5">
        {/* Summary */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <Field label="Declared" value={formatKg(request.declared_weight_kg)} />
          <Field
            label="Status"
            value={<RequestStatusBadge status={request.status} />}
          />
          <Field
            label="AI quality"
            value={request.ai_quality_score?.toFixed(0) ?? "—"}
          />
          <Field
            label="Distance to plant"
            value={
              request.distance_to_plant_km != null
                ? `${request.distance_to_plant_km.toFixed(1)} km`
                : "—"
            }
          />
          <Field
            label="Est. methane"
            value={
              request.ai_estimated_methane_m3 != null
                ? `${request.ai_estimated_methane_m3.toFixed(0)} m³`
                : "—"
            }
          />
          <Field
            label="Est. energy"
            value={
              request.ai_estimated_energy_kwh != null
                ? `${request.ai_estimated_energy_kwh.toFixed(0)} kWh`
                : "—"
            }
          />
        </div>

        {request.rejection_reason && (
          <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            Rejected: {request.rejection_reason}
          </p>
        )}

        {/* Photos */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium">
              Photos ({photos.length}/{MAX_PHOTOS})
            </h3>
            {editable && (
              <Button
                size="sm"
                variant="outline"
                disabled={atLimit || uploadMut.isPending}
                onClick={() => fileInput.current?.click()}
              >
                {uploadMut.isPending ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <ImagePlus />
                )}
                Add
              </Button>
            )}
            <input
              ref={fileInput}
              type="file"
              accept={ACCEPT}
              multiple
              hidden
              onChange={onFilesPicked}
            />
          </div>

          {photos.length === 0 ? (
            <p className="rounded-md border border-dashed py-6 text-center text-sm text-muted-foreground">
              No photos yet.
            </p>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              {photos.map((p) => (
                <PhotoThumbnail
                  key={p.id}
                  requestId={request.id}
                  photoId={p.id}
                  onDelete={editable ? () => onDelete(p.id) : undefined}
                  deleting={deletingId === p.id}
                />
              ))}
            </div>
          )}
          {atLimit && editable && (
            <p className="text-xs text-muted-foreground">Photo limit reached.</p>
          )}
        </div>

        <div className="flex justify-end pt-1">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md border p-2.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 font-medium tabular-nums">{value}</p>
    </div>
  );
}
