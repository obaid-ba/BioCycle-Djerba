import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/common/FormField";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useHotelOptions } from "@/hooks/useHotels";
import { messageFromError } from "@/lib/errors";
import type { WasteCollection, WasteCollectionCreate } from "@/types";

const schema = z.object({
  hotel_id: z.string().uuid("Select a hotel"),
  collected_at: z.string().optional(),
  organic_weight_kg: z.coerce.number().min(0, "Must be ≥ 0"),
  non_organic_weight_kg: z.coerce.number().min(0, "Must be ≥ 0"),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

/** ISO string → value for a <input type="datetime-local">. */
function toLocalInput(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

interface CollectionFormProps {
  open: boolean;
  onClose: () => void;
  collection?: WasteCollection | null;
  onSubmit: (payload: WasteCollectionCreate) => Promise<unknown>;
}

export function CollectionForm({
  open,
  onClose,
  collection,
  onSubmit,
}: CollectionFormProps) {
  const editing = !!collection;
  const { data: hotels = [], isLoading: hotelsLoading } = useHotelOptions();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      hotel_id: collection?.hotel_id ?? "",
      collected_at: toLocalInput(collection?.collected_at),
      organic_weight_kg: collection?.organic_weight_kg ?? 0,
      non_organic_weight_kg: collection?.non_organic_weight_kg ?? 0,
      notes: collection?.notes ?? "",
    },
  });

  async function submit(values: FormValues) {
    const payload: WasteCollectionCreate = {
      hotel_id: values.hotel_id,
      collected_at: values.collected_at
        ? new Date(values.collected_at).toISOString()
        : null,
      organic_weight_kg: values.organic_weight_kg,
      non_organic_weight_kg: values.non_organic_weight_kg,
      notes: values.notes || null,
    };
    try {
      await onSubmit(payload);
      onClose();
    } catch (error) {
      setError("root", { message: messageFromError(error) });
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={editing ? "Edit collection" : "Record collection"}
      description={
        editing
          ? "Update this waste collection record."
          : "Log a new waste collection."
      }
    >
      <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
        <FormField label="Hotel" htmlFor="hotel_id" error={errors.hotel_id?.message}>
          <Select
            id="hotel_id"
            {...register("hotel_id")}
            disabled={hotelsLoading || editing}
          >
            <option value="">
              {hotelsLoading ? "Loading hotels…" : "Select a hotel"}
            </option>
            {hotels.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name} — {h.city}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField
          label="Collected at"
          htmlFor="collected_at"
          error={errors.collected_at?.message}
        >
          <Input id="collected_at" type="datetime-local" {...register("collected_at")} />
        </FormField>

        <div className="grid grid-cols-2 gap-3">
          <FormField
            label="Organic (kg)"
            htmlFor="organic_weight_kg"
            error={errors.organic_weight_kg?.message}
          >
            <Input
              id="organic_weight_kg"
              type="number"
              step="0.1"
              min={0}
              {...register("organic_weight_kg")}
            />
          </FormField>
          <FormField
            label="Non-organic (kg)"
            htmlFor="non_organic_weight_kg"
            error={errors.non_organic_weight_kg?.message}
          >
            <Input
              id="non_organic_weight_kg"
              type="number"
              step="0.1"
              min={0}
              {...register("non_organic_weight_kg")}
            />
          </FormField>
        </div>

        <FormField label="Notes" htmlFor="notes" error={errors.notes?.message}>
          <Input id="notes" {...register("notes")} />
        </FormField>

        {errors.root && (
          <p className="text-sm text-destructive">{errors.root.message}</p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="animate-spin" />}
            {editing ? "Save changes" : "Record collection"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
