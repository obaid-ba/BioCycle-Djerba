import { api } from "@/services/api";
import type {
  CollectionRequest,
  CollectionRequestCreate,
  Page,
  RequestDecision,
  RequestStatus,
  RequestTransition,
} from "@/types";

export interface RequestListParams {
  page?: number;
  page_size?: number;
  status?: RequestStatus;
  hotel_id?: string;
}

export async function listRequests(
  params: RequestListParams,
): Promise<Page<CollectionRequest>> {
  const { data } = await api.get<Page<CollectionRequest>>("/requests", { params });
  return data;
}

export async function getRequest(id: string): Promise<CollectionRequest> {
  const { data } = await api.get<CollectionRequest>(`/requests/${id}`);
  return data;
}

export async function createRequest(
  payload: CollectionRequestCreate,
  hotelId?: string,
): Promise<CollectionRequest> {
  const { data } = await api.post<CollectionRequest>("/requests", payload, {
    // hotel_id is only needed by managers who own more than one hotel.
    params: hotelId ? { hotel_id: hotelId } : undefined,
  });
  return data;
}

export async function decideRequest(
  id: string,
  payload: RequestDecision,
): Promise<CollectionRequest> {
  const { data } = await api.post<CollectionRequest>(
    `/requests/${id}/decision`,
    payload,
  );
  return data;
}

export async function transitionRequest(
  id: string,
  payload: RequestTransition,
): Promise<CollectionRequest> {
  const { data } = await api.post<CollectionRequest>(
    `/requests/${id}/transition`,
    payload,
  );
  return data;
}
