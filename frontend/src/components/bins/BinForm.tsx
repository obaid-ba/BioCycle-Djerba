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
import type { SmartBin, SmartBinCreate } from "@/types";

const schema = z.object({
  code: z.string().min(1, "Code is required"),
  name: z.string().optional(),
  hotel_id: z.string().uuid("Select a hotel"),
  bin_type: z.enum(["organic", "non_organic", "mixed"]),
  status: z.enum(["online", "offline", "maintenance"]),
  capacity_liters: z.coerce.number().min(0).optional().or(z.nan()),
});

type FormValues = z.infer<typeof schema>;

interface BinFormProps {
  open: boolean;
  onClose: () => void;
  bin?: SmartBin | null;
  onSubmit: (payload: SmartBinCreate) => Promise<unknown>;
}

export function BinForm({ open, onClose, bin, onSubmit }: BinFormProps) {
  const editing = !!bin;
  const { data: hotels = [], isLoading: hotelsLoading } = useHotelOptions();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      code: bin?.code ?? "",
      name: bin?.name ?? "",
      hotel_id: bin?.hotel_id ?? "",
      bin_type: bin?.bin_type ?? "mixed",
      status: bin?.status ?? "offline",
      capacity_liters: bin?.capacity_liters ?? undefined,
    },
  });

  async function submit(values: FormValues) {
    const payload: SmartBinCreate = {
      code: values.code,
      name: values.name || null,
      hotel_id: values.hotel_id,
      bin_type: values.bin_type,
      status: values.status,
      capacity_liters:
        values.capacity_liters != null && !Number.isNaN(values.capacity_liters)
          ? values.capacity_liters
          : null,
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
      title={editing ? "Edit smart bin" : "Register smart bin"}
      description={
        editing ? "Update this bin's details." : "Register a new sensor bin."
      }
    >
      <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Code" htmlFor="code" error={errors.code?.message}>
            <Input id="code" {...register("code")} />
          </FormField>
          <FormField label="Name" htmlFor="name" error={errors.name?.message}>
            <Input id="name" {...register("name")} />
          </FormField>
        </div>

        <FormField label="Hotel" htmlFor="hotel_id" error={errors.hotel_id?.message}>
          <Select id="hotel_id" {...register("hotel_id")} disabled={hotelsLoading}>
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

        <div className="grid grid-cols-3 gap-3">
          <FormField label="Type" htmlFor="bin_type" error={errors.bin_type?.message}>
            <Select id="bin_type" {...register("bin_type")}>
              <option value="mixed">Mixed</option>
              <option value="organic">Organic</option>
              <option value="non_organic">Non-organic</option>
            </Select>
          </FormField>
          <FormField label="Status" htmlFor="status" error={errors.status?.message}>
            <Select id="status" {...register("status")}>
              <option value="offline">Offline</option>
              <option value="online">Online</option>
              <option value="maintenance">Maintenance</option>
            </Select>
          </FormField>
          <FormField
            label="Capacity (L)"
            htmlFor="capacity_liters"
            error={errors.capacity_liters?.message}
          >
            <Input
              id="capacity_liters"
              type="number"
              min={0}
              {...register("capacity_liters")}
            />
          </FormField>
        </div>

        {errors.root && (
          <p className="text-sm text-destructive">{errors.root.message}</p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="animate-spin" />}
            {editing ? "Save changes" : "Register bin"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
