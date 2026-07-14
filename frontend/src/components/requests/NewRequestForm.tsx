import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/common/FormField";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { messageFromError } from "@/lib/errors";
import { formatKg } from "@/lib/utils";
import { CONTAINER_WEIGHT_KG } from "@/lib/requestStatus";
import type { CollectionRequestCreate } from "@/types";

const schema = z.object({
  declared_containers: z.coerce
    .number()
    .int("Enter a whole number of containers")
    .gt(0, "Enter at least 1 container")
    .max(1000, "That seems too large"),
});

type FormValues = z.infer<typeof schema>;

interface NewRequestFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: CollectionRequestCreate) => Promise<unknown>;
}

/**
 * Hotel-facing form to open a collection request. The hotel declares a number
 * of standard containers; the equivalent weight (containers × 700 kg) is shown
 * live and computed server-side. Photo upload is a separate step.
 */
export function NewRequestForm({ open, onClose, onSubmit }: NewRequestFormProps) {
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { declared_containers: 1 },
  });

  const containers = useWatch({ control, name: "declared_containers" });
  const kg =
    typeof containers === "number" && !Number.isNaN(containers) && containers > 0
      ? containers * CONTAINER_WEIGHT_KG
      : 0;

  async function submit(values: FormValues) {
    try {
      await onSubmit({ declared_containers: values.declared_containers });
      onClose();
    } catch (error) {
      setError("root", { message: messageFromError(error) });
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="New collection request"
      description="Declare the organic waste ready for pickup. Our AI scores it and an operator schedules the collection."
    >
      <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
        <FormField
          label="Number of containers"
          htmlFor="declared_containers"
          error={errors.declared_containers?.message}
        >
          <Input
            id="declared_containers"
            type="number"
            step="1"
            min={1}
            autoFocus
            {...register("declared_containers")}
          />
          <p className="mt-1.5 text-xs text-muted-foreground">
            ≈ {formatKg(kg)} · {CONTAINER_WEIGHT_KG} kg per container
          </p>
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
            Submit request
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
