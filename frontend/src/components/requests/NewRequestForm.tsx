import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/common/FormField";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { messageFromError } from "@/lib/errors";
import type { CollectionRequestCreate } from "@/types";

const schema = z.object({
  declared_weight_kg: z.coerce
    .number()
    .gt(0, "Enter a weight greater than 0")
    .max(100_000, "That seems too large"),
});

type FormValues = z.infer<typeof schema>;

interface NewRequestFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: CollectionRequestCreate) => Promise<unknown>;
}

/**
 * Hotel-facing form to open a collection request. This iteration collects only
 * the declared quantity; photo upload is a later brick (photos are optional at
 * MVP), so nothing here blocks on files.
 */
export function NewRequestForm({ open, onClose, onSubmit }: NewRequestFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { declared_weight_kg: 0 },
  });

  async function submit(values: FormValues) {
    try {
      await onSubmit({ declared_weight_kg: values.declared_weight_kg });
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
          label="Organic waste quantity (kg)"
          htmlFor="declared_weight_kg"
          error={errors.declared_weight_kg?.message}
        >
          <Input
            id="declared_weight_kg"
            type="number"
            step="0.1"
            min={0}
            autoFocus
            {...register("declared_weight_kg")}
          />
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
