import { api } from "@/services/api";
import type {
  Page,
  Prediction,
  WasteCollection,
  WasteCollectionCreate,
  WasteCollectionUpdate,
} from "@/types";

export interface CollectionListParams {
  page?: number;
  page_size?: number;
  hotel_id?: string;
  bin_id?: string;
  date_from?: string;
  date_to?: string;
  sort?: string;
}

export async function listCollections(
  params: CollectionListParams,
): Promise<Page<WasteCollection>> {
  const { data } = await api.get<Page<WasteCollection>>("/collections", { params });
  return data;
}

export async function createCollection(
  payload: WasteCollectionCreate,
): Promise<WasteCollection> {
  const { data } = await api.post<WasteCollection>("/collections", payload);
  return data;
}

export async function updateCollection(
  id: string,
  payload: WasteCollectionUpdate,
): Promise<WasteCollection> {
  const { data } = await api.patch<WasteCollection>(`/collections/${id}`, payload);
  return data;
}

export async function deleteCollection(id: string): Promise<void> {
  await api.delete(`/collections/${id}`);
}

/** Trigger an AI energy prediction for a collection. */
export async function predictCollection(id: string): Promise<Prediction> {
  const { data } = await api.post<Prediction>(`/collections/${id}/predictions`);
  return data;
}

/** Latest prediction for a collection, or null if none exists (404). */
export async function latestPrediction(id: string): Promise<Prediction | null> {
  try {
    const { data } = await api.get<Prediction>(
      `/collections/${id}/predictions/latest`,
    );
    return data;
  } catch {
    return null;
  }
}
