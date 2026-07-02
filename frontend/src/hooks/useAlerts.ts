import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  acknowledgeAlert,
  createAlert,
  deleteAlert,
  listAlerts,
  resolveAlert,
  type AlertListParams,
} from "@/services/alerts";
import type { AlertCreate } from "@/types";

const KEY = "alerts";

export function useAlerts(params: AlertListParams) {
  return useQuery({
    queryKey: [KEY, params],
    queryFn: () => listAlerts(params),
  });
}

function useInvalidateAlerts() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: [KEY] });
}

export function useCreateAlert() {
  const invalidate = useInvalidateAlerts();
  return useMutation({
    mutationFn: (payload: AlertCreate) => createAlert(payload),
    onSuccess: invalidate,
  });
}

export function useAcknowledgeAlert() {
  const invalidate = useInvalidateAlerts();
  return useMutation({
    mutationFn: (id: string) => acknowledgeAlert(id),
    onSuccess: invalidate,
  });
}

export function useResolveAlert() {
  const invalidate = useInvalidateAlerts();
  return useMutation({
    mutationFn: (id: string) => resolveAlert(id),
    onSuccess: invalidate,
  });
}

export function useDeleteAlert() {
  const invalidate = useInvalidateAlerts();
  return useMutation({
    mutationFn: (id: string) => deleteAlert(id),
    onSuccess: invalidate,
  });
}
