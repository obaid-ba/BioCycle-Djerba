import { api } from "@/services/api";
import type {
  Alert,
  AlertCreate,
  AlertSeverity,
  AlertStatus,
  Page,
} from "@/types";

export interface AlertListParams {
  page?: number;
  page_size?: number;
  status?: AlertStatus;
  severity?: AlertSeverity;
  sort?: string;
}

export async function listAlerts(params: AlertListParams): Promise<Page<Alert>> {
  const { data } = await api.get<Page<Alert>>("/alerts", { params });
  return data;
}

export async function createAlert(payload: AlertCreate): Promise<Alert> {
  const { data } = await api.post<Alert>("/alerts", payload);
  return data;
}

export async function acknowledgeAlert(id: string): Promise<Alert> {
  const { data } = await api.post<Alert>(`/alerts/${id}/acknowledge`);
  return data;
}

export async function resolveAlert(id: string): Promise<Alert> {
  const { data } = await api.post<Alert>(`/alerts/${id}/resolve`);
  return data;
}

export async function deleteAlert(id: string): Promise<void> {
  await api.delete(`/alerts/${id}`);
}
