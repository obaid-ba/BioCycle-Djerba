import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/common/FormField";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { messageFromError } from "@/lib/errors";
import type { AlertCreate } from "@/types";

const schema = z.object({
  title: z.string().min(1, "Title is required"),
  severity: z.enum(["info", "warning", "critical"]),
  message: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface AlertFormProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: AlertCreate) => Promise<unknown>;
}

export function AlertForm({ open, onClose, onSubmit }: AlertFormProps) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { title: "", severity: "warning", message: "" },
  });

  async function submit(values: FormValues) {
    const payload: AlertCreate = {
      title: values.title,
      severity: values.severity,
      type: "custom",
      message: values.message || null,
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
      title="Raise alert"
      description="Manually raise an operational alert."
    >
      <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
        <FormField label="Title" htmlFor="title" error={errors.title?.message}>
          <Input id="title" {...register("title")} />
        </FormField>

        <FormField label="Severity" htmlFor="severity" error={errors.severity?.message}>
          <Select id="severity" {...register("severity")}>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </Select>
        </FormField>

        <FormField label="Message" htmlFor="message" error={errors.message?.message}>
          <Input id="message" {...register("message")} />
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
            Raise alert
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
