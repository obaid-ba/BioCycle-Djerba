import { api } from "@/services/api";
import type { Notification, Page } from "@/types";

export interface NotificationListParams {
  page?: number;
  page_size?: number;
  unread?: boolean;
}

export async function listNotifications(
  params: NotificationListParams,
): Promise<Page<Notification>> {
  const { data } = await api.get<Page<Notification>>("/notifications", { params });
  return data;
}

export async function getUnreadCount(): Promise<number> {
  const { data } = await api.get<{ unread: number }>("/notifications/unread-count");
  return data.unread;
}

export async function markNotificationRead(id: string): Promise<Notification> {
  const { data } = await api.post<Notification>(`/notifications/${id}/read`);
  return data;
}

export async function markAllNotificationsRead(): Promise<void> {
  await api.post("/notifications/read-all");
}
