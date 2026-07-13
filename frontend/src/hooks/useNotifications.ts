import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getUnreadCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationListParams,
} from "@/services/notifications";

const KEY = "notifications";

export function useNotifications(params: NotificationListParams = {}) {
  return useQuery({
    queryKey: [KEY, params],
    queryFn: () => listNotifications(params),
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: [KEY, "unread-count"],
    queryFn: getUnreadCount,
    // Fallback poll in case a realtime event is missed; realtime keeps it fresh.
    refetchInterval: 60_000,
  });
}

function useInvalidateNotifications() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

export function useMarkRead() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: invalidate,
  });
}

export function useMarkAllRead() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: () => markAllNotificationsRead(),
    onSuccess: invalidate,
  });
}
