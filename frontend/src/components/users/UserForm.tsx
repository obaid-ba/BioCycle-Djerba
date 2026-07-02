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
import type { UserCreate, UserUpdate } from "@/services/users";
import type { User } from "@/types";

// On create, email + password are required; on edit they are absent/optional.
const schema = z.object({
  email: z.string().email("Enter a valid email").optional().or(z.literal("")),
  full_name: z.string().min(1, "Name is required"),
  role: z.enum(["admin", "operator", "hotel_manager"]),
  is_active: z.enum(["true", "false"]),
  password: z
    .string()
    .min(8, "At least 8 characters")
    .optional()
    .or(z.literal("")),
});

type FormValues = z.infer<typeof schema>;

interface UserFormProps {
  open: boolean;
  onClose: () => void;
  user?: User | null;
  onCreate: (payload: UserCreate) => Promise<unknown>;
  onUpdate: (payload: UserUpdate) => Promise<unknown>;
}

export function UserForm({ open, onClose, user, onCreate, onUpdate }: UserFormProps) {
  const editing = !!user;

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: user?.email ?? "",
      full_name: user?.full_name ?? "",
      role: user?.role ?? "hotel_manager",
      is_active: user ? (user.is_active ? "true" : "false") : "true",
      password: "",
    },
  });

  async function submit(values: FormValues) {
    try {
      if (editing) {
        const payload: UserUpdate = {
          full_name: values.full_name,
          role: values.role,
          is_active: values.is_active === "true",
        };
        if (values.password) payload.password = values.password;
        await onUpdate(payload);
      } else {
        if (!values.email) {
          setError("email", { message: "Email is required" });
          return;
        }
        if (!values.password) {
          setError("password", { message: "Password is required" });
          return;
        }
        await onCreate({
          email: values.email,
          full_name: values.full_name,
          password: values.password,
          role: values.role,
        });
      }
      onClose();
    } catch (error) {
      setError("root", { message: messageFromError(error) });
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={editing ? "Edit user" : "Add user"}
      description={
        editing ? "Update this account." : "Create a new platform account."
      }
    >
      <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
        <FormField label="Email" htmlFor="email" error={errors.email?.message}>
          <Input
            id="email"
            type="email"
            {...register("email")}
            disabled={editing}
            placeholder={editing ? undefined : "user@biocycle.tn"}
          />
        </FormField>

        <FormField label="Full name" htmlFor="full_name" error={errors.full_name?.message}>
          <Input id="full_name" {...register("full_name")} />
        </FormField>

        <div className="grid grid-cols-2 gap-3">
          <FormField label="Role" htmlFor="role" error={errors.role?.message}>
            <Select id="role" {...register("role")}>
              <option value="hotel_manager">Hotel Manager</option>
              <option value="operator">Operator</option>
              <option value="admin">Administrator</option>
            </Select>
          </FormField>
          {editing && (
            <FormField label="Status" htmlFor="is_active" error={errors.is_active?.message}>
              <Select id="is_active" {...register("is_active")}>
                <option value="true">Active</option>
                <option value="false">Disabled</option>
              </Select>
            </FormField>
          )}
        </div>

        <FormField
          label={editing ? "New password (optional)" : "Password"}
          htmlFor="password"
          error={errors.password?.message}
        >
          <Input
            id="password"
            type="password"
            {...register("password")}
            placeholder={editing ? "Leave blank to keep current" : "••••••••"}
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
            {editing ? "Save changes" : "Create user"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
