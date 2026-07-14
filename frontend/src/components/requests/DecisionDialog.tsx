import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/common/FormField";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { messageFromError } from "@/lib/errors";
import type { CollectionRequest, RequestDecision } from "@/types";

const schema = z
  .object({
    accept: z.boolean(),
    rejection_reason: z.string().optional(),
    notes: z.string().optional(),
  })
  // Mirror the backend rule: a rejection must carry a reason.
  .refine((v) => v.accept || !!v.rejection_reason?.trim(), {
    path: ["rejection_reason"],
    message: "A reason is required when rejecting",
  });

type FormValues = z.infer<typeof schema>;

interface DecisionDialogProps {
  open: boolean;
  request: CollectionRequest;
  onClose: () => void;
  onSubmit: (payload: RequestDecision) => Promise<unknown>;
}

/** Operator accept/reject dialog. The reason field is required only on reject. */
export function DecisionDialog({
  open,
  request,
  onClose,
  onSubmit,
}: DecisionDialogProps) {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { accept: true, rejection_reason: "", notes: "" },
  });

  const accept = watch("accept");

  async function submit(values: FormValues) {
    try {
      await onSubmit({
        accept: values.accept,
        rejection_reason: values.accept ? null : values.rejection_reason || null,
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
      title="Review request"
      description={`${request.declared_containers} containers (${request.declared_weight_kg} kg) · AI priority ${
        request.ai_priority_score?.toFixed(0) ?? "—"
      }`}
    >
      <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
        {/* Accept / Reject toggle */}
        <div className="flex gap-2">
          <Button
            type="button"
            variant={accept ? "default" : "outline"}
            className="flex-1"
            onClick={() => setValue("accept", true)}
          >
            Accept
          </Button>
          <Button
            type="button"
            variant={!accept ? "destructive" : "outline"}
            className="flex-1"
            onClick={() => setValue("accept", false)}
          >
            Reject
          </Button>
        </div>

        {!accept && (
          <FormField
            label="Rejection reason"
            htmlFor="rejection_reason"
            error={errors.rejection_reason?.message}
          >
            <Input
              id="rejection_reason"
              placeholder="e.g. too contaminated for methanization"
              {...register("rejection_reason")}
            />
          </FormField>
        )}

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
          <Button
            type="submit"
            variant={accept ? "default" : "destructive"}
            disabled={isSubmitting}
          >
            {isSubmitting && <Loader2 className="animate-spin" />}
            {accept ? "Accept request" : "Reject request"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
