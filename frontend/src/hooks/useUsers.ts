import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createUser,
  deleteUser,
  listUsers,
  updateUser,
  type UserCreate,
  type UserListParams,
  type UserUpdate,
} from "@/services/users";

const KEY = "users";

export function useUsers(params: UserListParams) {
  return useQuery({
    queryKey: [KEY, params],
    queryFn: () => listUsers(params),
  });
}

function useInvalidateUsers() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

export function useCreateUser() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: (payload: UserCreate) => createUser(payload),
    onSuccess: invalidate,
  });
}

export function useUpdateUser() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UserUpdate }) =>
      updateUser(id, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteUser() {
  const invalidate = useInvalidateUsers();
  return useMutation({
    mutationFn: (id: string) => deleteUser(id),
    onSuccess: invalidate,
  });
}
