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
import type { Hotel, HotelCreate } from "@/types";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  city: z.string().min(1, "City is required"),
  country: z.string().min(1, "Country is required"),
  address: z.string().optional(),
  contact_email: z
    .string()
    .email("Enter a valid email")
    .optional()
    .or(z.literal("")),
  contact_phone: z.string().optional(),
  number_of_rooms: z.coerce.number().int().min(0).optional().or(z.nan()),
  status: z.enum(["active", "inactive", "onboarding"]),
});

type FormValues = z.infer<typeof schema>;

interface HotelFormProps {
  open: boolean;
  onClose: () => void;
  hotel?: Hotel | null;
  onSubmit: (payload: HotelCreate) => Promise<unknown>;
}

export function HotelForm({ open, onClose, hotel, onSubmit }: HotelFormProps) {
  const editing = !!hotel;

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: hotel?.name ?? "",
      city: hotel?.city ?? "",
      country: hotel?.country ?? "Tunisia",
      address: hotel?.address ?? "",
      contact_email: hotel?.contact_email ?? "",
      contact_phone: hotel?.contact_phone ?? "",
      number_of_rooms: hotel?.number_of_rooms ?? undefined,
      status: hotel?.status ?? "onboarding",
    },
  });

  async function submit(values: FormValues) {
    const payload: HotelCreate = {
      name: values.name,
      city: values.city,
      country: values.country,
      address: values.address || null,
      contact_email: values.contact_email || null,
      contact_phone: values.contact_phone || null,
      number_of_rooms:
        values.number_of_rooms != null && !Number.isNaN(values.number_of_rooms)
          ? values.number_of_rooms
          : null,
      status: values.status,
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
      title={editing ? "Edit hotel" : "Add hotel"}
      description={
        editing
          ? "Update this hotel's details."
          : "Register a new partner hotel."
      }
    >
      <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
        <FormField label="Name" htmlFor="name" error={errors.name?.message}>
          <Input id="name" {...register("name")} />
        </FormField>

        <div className="grid grid-cols-2 gap-3">
          <FormField label="City" htmlFor="city" error={errors.city?.message}>
            <Input id="city" {...register("city")} />
          </FormField>
          <FormField label="Country" htmlFor="country" error={errors.country?.message}>
            <Input id="country" {...register("country")} />
          </FormField>
        </div>

        <FormField label="Address" htmlFor="address" error={errors.address?.message}>
          <Input id="address" {...register("address")} />
        </FormField>

        <div className="grid grid-cols-2 gap-3">
          <FormField
            label="Contact email"
            htmlFor="contact_email"
            error={errors.contact_email?.message}
          >
            <Input id="contact_email" type="email" {...register("contact_email")} />
          </FormField>
          <FormField
            label="Contact phone"
            htmlFor="contact_phone"
            error={errors.contact_phone?.message}
          >
            <Input id="contact_phone" {...register("contact_phone")} />
          </FormField>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <FormField
            label="Rooms"
            htmlFor="number_of_rooms"
            error={errors.number_of_rooms?.message}
          >
            <Input
              id="number_of_rooms"
              type="number"
              min={0}
              {...register("number_of_rooms")}
            />
          </FormField>
          <FormField label="Status" htmlFor="status" error={errors.status?.message}>
            <Select id="status" {...register("status")}>
              <option value="onboarding">Onboarding</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </Select>
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
            {editing ? "Save changes" : "Create hotel"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
