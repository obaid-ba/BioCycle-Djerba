import { api } from "@/services/api";
import type { Page, User, UserRole } from "@/types";

export interface UserCreate {
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
}

export interface UserUpdate {
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
  password?: string;
}

export interface UserListParams {
  page?: number;
  page_size?: number;
}

export async function listUsers(params: UserListParams): Promise<Page<User>> {
  const { data } = await api.get<Page<User>>("/auth/users", { params });
  return data;
}

export async function createUser(payload: UserCreate): Promise<User> {
  const { data } = await api.post<User>("/auth/users", payload);
  return data;
}

export async function updateUser(id: string, payload: UserUpdate): Promise<User> {
  const { data } = await api.patch<User>(`/auth/users/${id}`, payload);
  return data;
}

export async function deleteUser(id: string): Promise<void> {
  await api.delete(`/auth/users/${id}`);
}
