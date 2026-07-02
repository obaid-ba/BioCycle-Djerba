import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { PageToolbar } from "@/components/common/PageToolbar";
import { Pagination } from "@/components/common/Pagination";
import { TableState } from "@/components/common/TableState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { UserForm } from "@/components/users/UserForm";
import { useAuth } from "@/context/auth";
import { useToast } from "@/context/toast";
import {
  useCreateUser,
  useDeleteUser,
  useUpdateUser,
  useUsers,
} from "@/hooks/useUsers";
import { messageFromError } from "@/lib/errors";
import { formatDateTime } from "@/lib/utils";
import { humanize } from "@/lib/statusBadge";
import type { UserCreate, UserUpdate } from "@/services/users";
import type { User, UserRole } from "@/types";

const roleVariant: Record<UserRole, "default" | "secondary" | "warning"> = {
  admin: "warning",
  operator: "default",
  hotel_manager: "secondary",
};

export function Users() {
  const { user: me } = useAuth();
  const toast = useToast();
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [deleting, setDeleting] = useState<User | null>(null);

  const query = useUsers({ page });
  const createMut = useCreateUser();
  const updateMut = useUpdateUser();
  const deleteMut = useDeleteUser();

  const users = query.data?.items ?? [];

  async function create(payload: UserCreate) {
    await createMut.mutateAsync(payload);
    toast.success("User created.");
  }

  async function update(payload: UserUpdate) {
    if (!editing) return;
    await updateMut.mutateAsync({ id: editing.id, payload });
    toast.success("User updated.");
  }

  async function confirmDelete() {
    if (!deleting) return;
    try {
      await deleteMut.mutateAsync(deleting.id);
      toast.success("User deleted.");
      setDeleting(null);
    } catch (error) {
      toast.error(messageFromError(error, "Could not delete user."));
    }
  }

  return (
    <div className="space-y-6">
      <PageToolbar
        title="Users"
        description="Manage platform accounts and roles."
      >
        <Button
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
        >
          <Plus />
          Add user
        </Button>
      </PageToolbar>

      <Card className="p-2">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableState
              colSpan={6}
              isLoading={query.isLoading}
              isError={query.isError}
              isEmpty={users.length === 0}
              emptyLabel="No users."
              onRetry={() => query.refetch()}
            />
            {!query.isLoading &&
              !query.isError &&
              users.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-medium">
                    {u.full_name}
                    {me?.id === u.id && (
                      <span className="ml-2 text-xs text-muted-foreground">(you)</span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{u.email}</TableCell>
                  <TableCell>
                    <Badge variant={roleVariant[u.role]}>{humanize(u.role)}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={u.is_active ? "success" : "secondary"}>
                      {u.is_active ? "active" : "disabled"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDateTime(u.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setEditing(u);
                          setFormOpen(true);
                        }}
                        aria-label="Edit"
                      >
                        <Pencil />
                      </Button>
                      {/* Backend forbids deleting your own account. */}
                      {me?.id !== u.id && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeleting(u)}
                          aria-label="Delete"
                        >
                          <Trash2 className="text-destructive" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>

      {query.data && (
        <Pagination
          page={query.data.page}
          pages={query.data.pages}
          total={query.data.total}
          onPageChange={setPage}
        />
      )}

      {formOpen && (
        <UserForm
          open={formOpen}
          onClose={() => setFormOpen(false)}
          user={editing}
          onCreate={create}
          onUpdate={update}
        />
      )}

      <ConfirmDialog
        open={!!deleting}
        onClose={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title="Delete user"
        description={`Permanently delete "${deleting?.full_name}"? This cannot be undone.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMut.isPending}
      />
    </div>
  );
}
