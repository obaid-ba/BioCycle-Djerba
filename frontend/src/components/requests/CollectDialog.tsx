import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/common/FormField";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { messageFromError } from "@/lib/errors";
import type { CollectionRequest, RequestTransition } from "@/types";

const schema = z.object({
  collected_weight_kg: z.coerce
    .number()
    .gt(0, "Enter the real collected weight")
    .max(100_000, "That seems too large"),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface CollectDialogProps {
  open: boolean;
  request: CollectionRequest;
  onClose: () => void;
  onSubmit: (payload: RequestTransition) => Promise<unknown>;
}

/**
 * Captures the real weight when an operator marks a request collected. The
 * backend requires collected_weight_kg for this transition, so it's mandatory
 * here too — pre-filled with the declared quantity as a convenient default.
 */
export function CollectDialog({
  open,
  request,
  onClose,
  onSubmit,
}: CollectDialogProps) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      collected_weight_kg: request.declared_weight_kg,
      notes: "",
    },
  });

  async function submit(values: FormValues) {
    try {
      await onSubmit({
        target: "collected",
        collected_weight_kg: values.collected_weight_kg,
        notes: values.notes || null,
      });
      onClose();
    } catch (error) {
      setError("root", { message: messageFromError(error) });
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Confirm collection"
      description={`Declared: ${request.declared_weight_kg} kg. Enter the actual weight collected.`}
    >
      <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
        <FormField
          label="Collected weight (kg)"
          htmlFor="collected_weight_kg"
          error={errors.collected_weight_kg?.message}
        >
          <Input
            id="collected_weight_kg"
            type="number"
            step="0.1"
            min={0}
            autoFocus
            {...register("collected_weight_kg")}
          />
        </FormField>

        <FormField label="Notes (optional)" htmlFor="notes" error={errors.notes?.message}>
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
            Mark collected
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
