import { api } from "@/services/api";
import type {
  CollectionRequest,
  CollectionRequestCreate,
  Page,
  RequestDecision,
  RequestPhoto,
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

// --------------------------------------------------------------------------- //
// Photos
// --------------------------------------------------------------------------- //
export async function uploadPhotos(
  requestId: string,
  files: File[],
): Promise<RequestPhoto[]> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  const { data } = await api.post<RequestPhoto[]>(
    `/requests/${requestId}/photos`,
    form,
    // Let the browser set the multipart boundary; override the JSON default.
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return data;
}

export async function deletePhoto(requestId: string, photoId: string): Promise<void> {
  await api.delete(`/requests/${requestId}/photos/${photoId}`);
}

/**
 * Fetch a photo as an object URL. The download endpoint requires a JWT, so we
 * can't point <img src> straight at it — we pull the bytes through the
 * authenticated axios client and wrap them in a blob: URL. Callers must revoke
 * the URL when done to avoid leaking memory.
 */
export async function fetchPhotoObjectUrl(
  requestId: string,
  photoId: string,
): Promise<string> {
  const resp = await api.get<Blob>(`/requests/${requestId}/photos/${photoId}`, {
    responseType: "blob",
  });
  return URL.createObjectURL(resp.data);
}
